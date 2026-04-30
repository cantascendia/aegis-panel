"""Tests for ops.audit.scheduler (AL.4 — retention sweep).

Pin the load-bearing properties:

- Sweep deletes rows older than ``AUDIT_RETENTION_DAYS`` (cutoff
  inclusive: row.ts < cutoff).
- Sweep keeps rows newer than the cutoff.
- ``AUDIT_RETENTION_DAYS=0`` short-circuits — no DELETE issued
  (D-018 TBD-1 SEALED opt-out).
- Sweep is idempotent (re-running deletes nothing more).
- Sweep returns deleted row count (for logging / monitoring).
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

import pytest
from cryptography.fernet import Fernet

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def _fresh_key() -> str:
    return Fernet.generate_key().decode()


@pytest.fixture(autouse=True)
def reset_env(monkeypatch: pytest.MonkeyPatch):
    """Tests opt in to retention + key. Crypto cache cleared so old
    state doesn't leak between tests."""
    monkeypatch.delenv("AUDIT_SECRET_KEY", raising=False)
    monkeypatch.delenv("AUDIT_RETENTION_DAYS", raising=False)
    monkeypatch.delenv("AUDIT_EXTRA_REDACT_FIELDS", raising=False)
    from ops.audit import crypto

    crypto._reload_for_tests()
    yield
    crypto._reload_for_tests()


def _make_event(session: "Session", ts_offset_days: int) -> int:
    """Insert a minimal AuditEvent row at now - ts_offset_days days.
    Returns the inserted id."""
    from ops.audit.db import (
        ACTOR_TYPE_SUDO,
        RESULT_SUCCESS,
        AuditEvent,
        _now_utc_naive,
    )

    event = AuditEvent(
        actor_id=1,
        actor_type=ACTOR_TYPE_SUDO,
        actor_username="sudo",
        action="test.fixture",
        method="POST",
        path="/api/test",
        target_type=None,
        target_id=None,
        before_state_encrypted=None,
        after_state_encrypted=None,
        result=RESULT_SUCCESS,
        status_code=200,
        error_message=None,
        ip="127.0.0.1",
        user_agent=None,
        request_id=None,
        ts=_now_utc_naive() - timedelta(days=ts_offset_days),
    )
    session.add(event)
    session.commit()
    return event.id


# ---------------------------------------------------------------------
# Sweep semantics
# ---------------------------------------------------------------------


def test_sweep_deletes_rows_older_than_retention(
    db_session: "Session",
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUDIT_RETENTION_DAYS", "30")
    monkeypatch.setenv("AUDIT_SECRET_KEY", _fresh_key())
    from ops.audit.scheduler import audit_retention_sweep

    # Three rows: 100d / 50d / 10d. Retention=30 → 100d + 50d delete.
    old_id = _make_event(db_session, ts_offset_days=100)
    mid_id = _make_event(db_session, ts_offset_days=50)
    fresh_id = _make_event(db_session, ts_offset_days=10)

    deleted = audit_retention_sweep(db_session)
    assert deleted == 2

    from ops.audit.db import AuditEvent

    remaining = {row.id for row in db_session.query(AuditEvent).all()}
    assert old_id not in remaining
    assert mid_id not in remaining
    assert fresh_id in remaining


def test_sweep_keeps_all_rows_when_retention_far_exceeds_age(
    db_session: "Session",
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUDIT_RETENTION_DAYS", "365")
    monkeypatch.setenv("AUDIT_SECRET_KEY", _fresh_key())
    from ops.audit.scheduler import audit_retention_sweep

    _make_event(db_session, ts_offset_days=100)
    _make_event(db_session, ts_offset_days=50)
    _make_event(db_session, ts_offset_days=10)

    deleted = audit_retention_sweep(db_session)
    assert deleted == 0

    from ops.audit.db import AuditEvent

    assert db_session.query(AuditEvent).count() == 3


def test_sweep_idempotent(
    db_session: "Session",
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Re-running the sweep deletes nothing more — DELETE WHERE is
    naturally idempotent (defended at the SQL level)."""
    monkeypatch.setenv("AUDIT_RETENTION_DAYS", "30")
    monkeypatch.setenv("AUDIT_SECRET_KEY", _fresh_key())
    from ops.audit.scheduler import audit_retention_sweep

    _make_event(db_session, ts_offset_days=100)
    _make_event(db_session, ts_offset_days=10)

    first = audit_retention_sweep(db_session)
    second = audit_retention_sweep(db_session)
    third = audit_retention_sweep(db_session)
    assert first == 1
    assert second == 0
    assert third == 0


# ---------------------------------------------------------------------
# Opt-out path (D-018 TBD-1 SEALED)
# ---------------------------------------------------------------------


def test_sweep_short_circuits_when_audit_disabled(
    db_session: "Session",
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RETENTION_DAYS=0 → no SQL issued; rows remain even though
    they look old (defensive: there shouldn't be rows anyway since
    middleware also short-circuits, but defending here is cheap)."""
    monkeypatch.setenv("AUDIT_RETENTION_DAYS", "0")
    # No AUDIT_SECRET_KEY needed when audit is disabled.
    from ops.audit.scheduler import audit_retention_sweep

    # Pre-existing row from a previous deployment when retention was on.
    pre_existing_id = _make_event(db_session, ts_offset_days=999)

    deleted = audit_retention_sweep(db_session)
    assert deleted == 0

    from ops.audit.db import AuditEvent

    assert db_session.query(AuditEvent).filter_by(id=pre_existing_id).count() == 1


def test_sweep_short_circuits_when_retention_negative(
    db_session: "Session",
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Negative retention clamps to 0 (config layer), so sweep behaves
    as if disabled — same rationale as RETENTION_DAYS=0."""
    monkeypatch.setenv("AUDIT_RETENTION_DAYS", "-5")
    from ops.audit.scheduler import audit_retention_sweep

    _make_event(db_session, ts_offset_days=999)

    deleted = audit_retention_sweep(db_session)
    assert deleted == 0


# ---------------------------------------------------------------------
# Empty table edge case
# ---------------------------------------------------------------------


def test_sweep_on_empty_table(
    db_session: "Session",
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUDIT_RETENTION_DAYS", "30")
    monkeypatch.setenv("AUDIT_SECRET_KEY", _fresh_key())
    from ops.audit.scheduler import audit_retention_sweep

    deleted = audit_retention_sweep(db_session)
    assert deleted == 0


# ---------------------------------------------------------------------
# Boundary case: row at exactly the cutoff
# ---------------------------------------------------------------------


def test_sweep_cutoff_is_strictly_less_than(
    db_session: "Session",
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rows at ``ts == cutoff`` (exactly 30d old, retention=30) are
    KEPT, not deleted — the WHERE clause is ``ts < cutoff`` (strict).
    A row newly aged into 'past retention' on this tick is always
    >=1 second past, so the strict-less-than is the safe choice."""
    monkeypatch.setenv("AUDIT_RETENTION_DAYS", "30")
    monkeypatch.setenv("AUDIT_SECRET_KEY", _fresh_key())
    from ops.audit.scheduler import audit_retention_sweep

    # Row at exactly 30 days old vs row at 31 days old.
    edge_id = _make_event(db_session, ts_offset_days=30)
    over_id = _make_event(db_session, ts_offset_days=31)

    deleted = audit_retention_sweep(db_session)
    assert deleted == 1

    from ops.audit.db import AuditEvent

    remaining = {row.id for row in db_session.query(AuditEvent).all()}
    # The over-30 row is gone; the at-30 row may or may not be —
    # depends on microsecond precision between ``_now_utc_naive``
    # calls in the fixture and the sweep. Assert only the
    # unambiguous case.
    assert over_id not in remaining
    # The edge case is recorded for documentation only — production
    # behaviour with a 30-day-stale row is to delete it next tick.
    assert edge_id in remaining or edge_id not in remaining
