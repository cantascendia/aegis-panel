"""
Tests for ``ops.billing.grants`` — grant-application math.

Pure logic over a duck-typed user, so we use ``SimpleNamespace``
instead of dragging in SQLAlchemy + the ``users`` table. Each case
pins one rule from the module docstring.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace

from app.models.user import UserExpireStrategy
from ops.billing.grants import _BYTES_PER_GB, apply_grant_to_user
from ops.billing.pricing import UserGrant


def _user(
    *,
    data_limit: int | None = None,
    expire_strategy: UserExpireStrategy = UserExpireStrategy.NEVER,
    expire_date: datetime | None = None,
    usage_duration: int | None = None,
    activation_deadline: datetime | None = None,
) -> SimpleNamespace:
    """Build a stand-in for a SQLAlchemy ``User`` row with just the
    fields ``apply_grant_to_user`` reads/writes."""
    return SimpleNamespace(
        data_limit=data_limit,
        expire_strategy=expire_strategy,
        expire_date=expire_date,
        usage_duration=usage_duration,
        activation_deadline=activation_deadline,
    )


_NOW = datetime(2026, 5, 1, 12, 0, 0)


# --------------------------------------------------------------------------
# data_limit (bytes-additive)
# --------------------------------------------------------------------------


def test_grant_adds_gb_to_existing_data_limit() -> None:
    user = _user(data_limit=10 * _BYTES_PER_GB)
    grant = UserGrant(data_limit_gb_delta=5, duration_days_delta=0)

    apply_grant_to_user(user, grant, now=_NOW)

    assert user.data_limit == 15 * _BYTES_PER_GB


def test_grant_treats_null_data_limit_as_zero_baseline() -> None:
    """A previously-unlimited user (NULL data_limit) receiving a 5GB
    grant becomes limited to exactly 5GB. Operator policy keeps
    flexible-traffic addons off unlimited users; module docstring
    documents the trade."""
    user = _user(data_limit=None)
    grant = UserGrant(data_limit_gb_delta=5, duration_days_delta=0)

    apply_grant_to_user(user, grant, now=_NOW)

    assert user.data_limit == 5 * _BYTES_PER_GB


def test_grant_with_zero_gb_leaves_data_limit_untouched() -> None:
    user = _user(data_limit=42 * _BYTES_PER_GB)
    grant = UserGrant(data_limit_gb_delta=0, duration_days_delta=30)

    apply_grant_to_user(user, grant, now=_NOW)

    assert user.data_limit == 42 * _BYTES_PER_GB


# --------------------------------------------------------------------------
# expire_date / expire_strategy policy
# --------------------------------------------------------------------------


def test_grant_extends_fixed_date_user_from_existing_expiry() -> None:
    """Future expire_date: extend by ``days``."""
    future = _NOW + timedelta(days=10)
    user = _user(
        expire_strategy=UserExpireStrategy.FIXED_DATE, expire_date=future
    )
    grant = UserGrant(data_limit_gb_delta=0, duration_days_delta=30)

    apply_grant_to_user(user, grant, now=_NOW)

    assert user.expire_date == future + timedelta(days=30)
    assert user.expire_strategy == UserExpireStrategy.FIXED_DATE


def test_grant_extends_lapsed_fixed_date_user_from_now_not_past() -> None:
    """User whose plan expired yesterday + buys a 30d renewal today
    should land 30 days from NOW, not 30 days from the lapsed date.
    Without the ``max(now, expire_date)`` guard the first ~24h would
    already be in the past — module docstring §"FIXED_DATE"."""
    lapsed = _NOW - timedelta(days=2)
    user = _user(
        expire_strategy=UserExpireStrategy.FIXED_DATE, expire_date=lapsed
    )
    grant = UserGrant(data_limit_gb_delta=0, duration_days_delta=30)

    apply_grant_to_user(user, grant, now=_NOW)

    assert user.expire_date == _NOW + timedelta(days=30)


def test_grant_promotes_never_user_to_fixed_date() -> None:
    """NEVER → FIXED_DATE anchored at ``now + days``."""
    user = _user(expire_strategy=UserExpireStrategy.NEVER, expire_date=None)
    grant = UserGrant(data_limit_gb_delta=0, duration_days_delta=30)

    apply_grant_to_user(user, grant, now=_NOW)

    assert user.expire_strategy == UserExpireStrategy.FIXED_DATE
    assert user.expire_date == _NOW + timedelta(days=30)


def test_grant_promotes_start_on_first_use_user_to_fixed_date() -> None:
    """START_ON_FIRST_USE → FIXED_DATE anchored at ``now`` once paid.
    Documented in module docstring as the policy."""
    user = _user(
        expire_strategy=UserExpireStrategy.START_ON_FIRST_USE,
        expire_date=None,
        usage_duration=86400 * 7,
        activation_deadline=_NOW + timedelta(days=30),
    )
    grant = UserGrant(data_limit_gb_delta=0, duration_days_delta=30)

    apply_grant_to_user(user, grant, now=_NOW)

    assert user.expire_strategy == UserExpireStrategy.FIXED_DATE
    assert user.expire_date == _NOW + timedelta(days=30)
    # Stale START_ON_FIRST_USE-only fields cleared so admin UI shows
    # consistent state.
    assert user.usage_duration is None
    assert user.activation_deadline is None


def test_grant_with_zero_days_does_not_flip_strategy() -> None:
    """A pure data top-up shouldn't promote NEVER → FIXED_DATE."""
    user = _user(expire_strategy=UserExpireStrategy.NEVER)
    grant = UserGrant(data_limit_gb_delta=10, duration_days_delta=0)

    apply_grant_to_user(user, grant, now=_NOW)

    assert user.expire_strategy == UserExpireStrategy.NEVER
    assert user.expire_date is None


# --------------------------------------------------------------------------
# AppliedGrant snapshot
# --------------------------------------------------------------------------


def test_applied_grant_records_before_and_after_for_audit() -> None:
    user = _user(
        data_limit=10 * _BYTES_PER_GB,
        expire_strategy=UserExpireStrategy.FIXED_DATE,
        expire_date=_NOW + timedelta(days=10),
    )
    grant = UserGrant(data_limit_gb_delta=5, duration_days_delta=30)

    applied = apply_grant_to_user(user, grant, now=_NOW)

    assert applied.data_limit_bytes_before == 10 * _BYTES_PER_GB
    assert applied.data_limit_bytes_after == 15 * _BYTES_PER_GB
    assert applied.expire_strategy_before == "fixed_date"
    assert applied.expire_strategy_after == "fixed_date"
    assert applied.grant_gb_delta == 5
    assert applied.grant_days_delta == 30


def test_applied_grant_records_strategy_flip() -> None:
    user = _user(expire_strategy=UserExpireStrategy.NEVER)
    grant = UserGrant(data_limit_gb_delta=0, duration_days_delta=30)

    applied = apply_grant_to_user(user, grant, now=_NOW)

    assert applied.expire_strategy_before == "never"
    assert applied.expire_strategy_after == "fixed_date"
    assert applied.expire_date_before is None
    assert applied.expire_date_after == _NOW + timedelta(days=30)


def test_applied_grant_for_zero_zero_grant_records_unchanged_state() -> None:
    """Even a no-op grant produces an AppliedGrant — the audit log
    needs to show "applied with nothing to add" so the reader knows
    the apply attempt happened (e.g. a free-trial line)."""
    user = _user(
        data_limit=42 * _BYTES_PER_GB,
        expire_strategy=UserExpireStrategy.FIXED_DATE,
        expire_date=_NOW + timedelta(days=5),
    )
    grant = UserGrant(data_limit_gb_delta=0, duration_days_delta=0)

    applied = apply_grant_to_user(user, grant, now=_NOW)

    assert applied.data_limit_bytes_before == applied.data_limit_bytes_after
    assert applied.expire_date_before == applied.expire_date_after
    assert applied.grant_gb_delta == 0
    assert applied.grant_days_delta == 0
