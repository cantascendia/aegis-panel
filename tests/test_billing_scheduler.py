"""
Tests for ``ops.billing.scheduler`` — both periodic jobs.

Both ``_reap_expired_invoices_inner`` and ``_apply_paid_invoices_inner``
are exercised through their factored-out sync entry points, so we
don't need to spin up APScheduler / asyncio just to test the logic.
The async ``run_*`` wrappers are thin GetDB-shells; pinned by
``test_install_billing_scheduler_is_idempotent`` for the mounting
side.

Test DB: SQLite in-memory with billing tables + ``users`` table from
upstream. We need ``users`` here (unlike test_billing_states.py which
only tests state transitions) because the applier resolves
``Invoice.user_id`` to a real ``User`` row.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import User
from app.models.user import UserDataUsageResetStrategy, UserExpireStrategy
from ops.billing.db import (
    INVOICE_STATE_APPLIED,
    INVOICE_STATE_AWAITING_PAYMENT,
    INVOICE_STATE_CREATED,
    INVOICE_STATE_EXPIRED,
    INVOICE_STATE_PAID,
    INVOICE_STATE_PENDING,
    PLAN_KIND_FIXED,
    PLAN_KIND_FLEXIBLE_DURATION,
    Invoice,
    InvoiceLine,
    PaymentEvent,
    Plan,
)
from ops.billing.grants import _BYTES_PER_GB
from ops.billing.scheduler import (
    _apply_paid_invoices_inner,
    _reap_expired_invoices_inner,
    install_billing_scheduler,
)

_NOW = datetime(2026, 5, 1, 12, 0, 0)


# --------------------------------------------------------------------------
# Fixture: scratch DB with billing tables + the upstream users table.
# --------------------------------------------------------------------------


@pytest.fixture
def session() -> Session:
    """Fresh SQLite in-memory engine. Creates only the tables we need
    so foreign-key targets exist without booting all of upstream.
    """
    needed = [
        Base.metadata.tables[name]
        for name in (
            "aegis_billing_plans",
            "aegis_billing_channels",
            "aegis_billing_invoices",
            "aegis_billing_invoice_lines",
            "aegis_billing_payment_events",
            # User eagerly joins services / inbounds via lazy="joined"
            # relationships; the OUTER JOIN must resolve even when
            # the link tables are empty, or SQLAlchemy raises on every
            # User load. Cheaper to create the empty tables here than
            # to override loader options on every scheduler query.
            "users",
            "services",
            "users_services",
            "inbounds",
            "inbounds_services",
        )
    ]
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=needed)
    with Session(engine) as s:
        yield s


# --------------------------------------------------------------------------
# Builders
# --------------------------------------------------------------------------


def _make_user(
    session: Session,
    *,
    username: str = "alice",
    data_limit: int | None = None,
    expire_strategy: UserExpireStrategy = UserExpireStrategy.NEVER,
    expire_date: datetime | None = None,
) -> User:
    user = User(
        username=username,
        key="k" + username,
        activated=True,
        enabled=True,
        removed=False,
        data_limit=data_limit,
        data_limit_reset_strategy=UserDataUsageResetStrategy.no_reset,
        expire_strategy=expire_strategy,
        expire_date=expire_date,
        ip_limit=-1,
        used_traffic=0,
        lifetime_used_traffic=0,
        created_at=_NOW,
    )
    session.add(user)
    session.flush()
    return user


def _make_plan(
    session: Session,
    *,
    code: str = "p-30d-50gb",
    kind: str = PLAN_KIND_FIXED,
    data_limit_gb: int | None = 50,
    duration_days: int | None = 30,
    price_cny_fen: int = 1500,
) -> Plan:
    plan = Plan(
        operator_code=code,
        display_name_en=code,
        display_name_i18n={},
        kind=kind,
        data_limit_gb=data_limit_gb,
        duration_days=duration_days,
        price_cny_fen=price_cny_fen,
        enabled=True,
        sort_order=0,
        created_at=_NOW,
    )
    session.add(plan)
    session.flush()
    return plan


def _make_invoice(
    session: Session,
    *,
    user_id: int,
    state: str,
    expires_at: datetime,
    lines: list[tuple[int, int]] = (),  # (plan_id, quantity)
) -> Invoice:
    inv = Invoice(
        user_id=user_id,
        total_cny_fen=1500,
        state=state,
        provider="trc20",
        provider_invoice_id=None,
        payment_url=None,
        trc20_memo=None,
        trc20_expected_amount_millis=None,
        created_at=_NOW,
        paid_at=_NOW if state == INVOICE_STATE_PAID else None,
        applied_at=None,
        expires_at=expires_at,
    )
    session.add(inv)
    session.flush()
    for plan_id, qty in lines:
        session.add(
            InvoiceLine(
                invoice_id=inv.id,
                plan_id=plan_id,
                quantity=qty,
                unit_price_fen_at_purchase=1500,
            )
        )
    session.flush()
    return inv


# --------------------------------------------------------------------------
# Reaper: ``awaiting_payment`` past ``expires_at`` → ``expired``
# --------------------------------------------------------------------------


def test_reap_flips_expired_awaiting_payment_to_expired(session) -> None:
    user = _make_user(session)
    inv = _make_invoice(
        session,
        user_id=user.id,
        state=INVOICE_STATE_AWAITING_PAYMENT,
        expires_at=_NOW - timedelta(minutes=5),
    )
    session.commit()

    count = _reap_expired_invoices_inner(session, now=_NOW)

    assert count == 1
    session.refresh(inv)
    assert inv.state == INVOICE_STATE_EXPIRED


def test_reap_writes_payment_event_for_audit(session) -> None:
    user = _make_user(session)
    inv = _make_invoice(
        session,
        user_id=user.id,
        state=INVOICE_STATE_AWAITING_PAYMENT,
        expires_at=_NOW - timedelta(minutes=5),
    )
    session.commit()

    _reap_expired_invoices_inner(session, now=_NOW)

    events = (
        session.query(PaymentEvent)
        .filter(PaymentEvent.invoice_id == inv.id)
        .all()
    )
    types = [e.event_type for e in events]
    assert "reaper_expired" in types


def test_reap_skips_invoices_still_within_payment_window(session) -> None:
    """An invoice whose ``expires_at`` is still in the future must
    remain in ``awaiting_payment`` — the reaper is exclusively for
    past-due rows."""
    user = _make_user(session)
    inv = _make_invoice(
        session,
        user_id=user.id,
        state=INVOICE_STATE_AWAITING_PAYMENT,
        expires_at=_NOW + timedelta(minutes=15),
    )
    session.commit()

    count = _reap_expired_invoices_inner(session, now=_NOW)

    assert count == 0
    session.refresh(inv)
    assert inv.state == INVOICE_STATE_AWAITING_PAYMENT


def test_reap_ignores_paid_invoices_even_past_deadline(session) -> None:
    """A ``paid`` invoice whose payment deadline elapsed (e.g. user paid
    in the last second of the window) must NOT be expired by the
    reaper. The reaper queries on state, not expires_at alone."""
    user = _make_user(session)
    inv = _make_invoice(
        session,
        user_id=user.id,
        state=INVOICE_STATE_PAID,
        expires_at=_NOW - timedelta(minutes=10),
    )
    session.commit()

    count = _reap_expired_invoices_inner(session, now=_NOW)

    assert count == 0
    session.refresh(inv)
    assert inv.state == INVOICE_STATE_PAID


def test_reap_handles_multiple_expired_invoices_in_one_tick(session) -> None:
    user = _make_user(session)
    for i in range(3):
        _make_invoice(
            session,
            user_id=user.id,
            state=INVOICE_STATE_AWAITING_PAYMENT,
            expires_at=_NOW - timedelta(minutes=5 + i),
        )
    session.commit()

    count = _reap_expired_invoices_inner(session, now=_NOW)

    assert count == 3


def test_reap_idempotent_on_second_run(session) -> None:
    """Running the reaper twice should not flip the same row twice."""
    user = _make_user(session)
    _make_invoice(
        session,
        user_id=user.id,
        state=INVOICE_STATE_AWAITING_PAYMENT,
        expires_at=_NOW - timedelta(minutes=5),
    )
    session.commit()

    first = _reap_expired_invoices_inner(session, now=_NOW)
    second = _reap_expired_invoices_inner(session, now=_NOW)

    assert first == 1
    assert second == 0


# --------------------------------------------------------------------------
# Applier: ``paid`` → ``applied`` + extend user
# --------------------------------------------------------------------------


def test_apply_extends_user_expire_and_data_limit(session) -> None:
    user = _make_user(session, expire_strategy=UserExpireStrategy.NEVER)
    plan = _make_plan(session)  # 50 GB / 30 days fixed
    inv = _make_invoice(
        session,
        user_id=user.id,
        state=INVOICE_STATE_PAID,
        expires_at=_NOW + timedelta(minutes=30),
        lines=[(plan.id, 1)],
    )
    session.commit()

    count = _apply_paid_invoices_inner(session, now=_NOW)

    assert count == 1
    session.refresh(inv)
    session.refresh(user)
    assert inv.state == INVOICE_STATE_APPLIED
    assert inv.applied_at == _NOW
    assert user.data_limit == 50 * _BYTES_PER_GB
    assert user.expire_strategy == UserExpireStrategy.FIXED_DATE
    assert user.expire_date == _NOW + timedelta(days=30)


def test_apply_writes_audit_event_with_grant_snapshot(session) -> None:
    user = _make_user(session)
    plan = _make_plan(session)
    inv = _make_invoice(
        session,
        user_id=user.id,
        state=INVOICE_STATE_PAID,
        expires_at=_NOW + timedelta(minutes=30),
        lines=[(plan.id, 1)],
    )
    session.commit()

    _apply_paid_invoices_inner(session, now=_NOW)

    events = (
        session.query(PaymentEvent)
        .filter(
            PaymentEvent.invoice_id == inv.id,
            PaymentEvent.event_type == "state_applied",
        )
        .all()
    )
    assert len(events) == 1
    payload = events[0].payload_json
    assert payload["user_id"] == user.id
    assert payload["grant_gb_delta"] == 50
    assert payload["grant_days_delta"] == 30
    assert payload["expire_strategy_before"] == "never"
    assert payload["expire_strategy_after"] == "fixed_date"


def test_apply_skips_non_paid_invoices(session) -> None:
    """Only ``paid`` rows should be picked up. Anything else is
    invisible to the applier."""
    user = _make_user(session)
    plan = _make_plan(session)
    for state in (
        INVOICE_STATE_CREATED,
        INVOICE_STATE_PENDING,
        INVOICE_STATE_AWAITING_PAYMENT,
        INVOICE_STATE_APPLIED,
        INVOICE_STATE_EXPIRED,
    ):
        _make_invoice(
            session,
            user_id=user.id,
            state=state,
            expires_at=_NOW + timedelta(minutes=30),
            lines=[(plan.id, 1)],
        )
    session.commit()

    count = _apply_paid_invoices_inner(session, now=_NOW)

    assert count == 0


def test_apply_idempotent_via_state_machine_guard(session) -> None:
    """Running the applier a second time over the same paid invoice
    must NOT double-grant. The state-machine guard
    (``paid → applied`` is one-way) is what keeps us safe; this test
    pins that guarantee."""
    user = _make_user(session)
    plan = _make_plan(session)
    _make_invoice(
        session,
        user_id=user.id,
        state=INVOICE_STATE_PAID,
        expires_at=_NOW + timedelta(minutes=30),
        lines=[(plan.id, 1)],
    )
    session.commit()

    first = _apply_paid_invoices_inner(session, now=_NOW)
    session.refresh(user)
    expire_after_first = user.expire_date
    data_after_first = user.data_limit
    second = _apply_paid_invoices_inner(session, now=_NOW)
    session.refresh(user)

    assert first == 1
    assert second == 0
    assert user.expire_date == expire_after_first
    assert user.data_limit == data_after_first


def test_apply_skips_invoice_when_user_was_deleted(session) -> None:
    """Applier finds ``Invoice.user_id`` resolves to None — log + skip,
    leave invoice in ``paid`` for operator attention. Pure SQLite
    doesn't enforce FK by default so we can simulate by inserting an
    invoice with a non-existent user_id."""
    plan = _make_plan(session)
    inv = _make_invoice(
        session,
        user_id=99999,  # never inserted
        state=INVOICE_STATE_PAID,
        expires_at=_NOW + timedelta(minutes=30),
        lines=[(plan.id, 1)],
    )
    session.commit()

    count = _apply_paid_invoices_inner(session, now=_NOW)

    assert count == 0
    session.refresh(inv)
    assert inv.state == INVOICE_STATE_PAID  # left for operator


def test_apply_skips_invoice_with_missing_plan(session) -> None:
    """If a plan was hard-deleted under our feet, the applier skips
    rather than crashing the whole sweep."""
    user = _make_user(session)
    plan = _make_plan(session)
    inv = _make_invoice(
        session,
        user_id=user.id,
        state=INVOICE_STATE_PAID,
        expires_at=_NOW + timedelta(minutes=30),
        lines=[(plan.id, 1)],
    )
    # Hard-delete the plan AFTER the invoice references it.
    session.delete(plan)
    session.commit()

    count = _apply_paid_invoices_inner(session, now=_NOW)

    assert count == 0
    session.refresh(inv)
    assert inv.state == INVOICE_STATE_PAID


def test_apply_handles_flexible_duration_quantity(session) -> None:
    """Flexible-duration plan with quantity=14 should grant 14 days."""
    user = _make_user(session)
    plan = _make_plan(
        session,
        code="addon-1d",
        kind=PLAN_KIND_FLEXIBLE_DURATION,
        data_limit_gb=None,
        duration_days=1,
        price_cny_fen=20,
    )
    _make_invoice(
        session,
        user_id=user.id,
        state=INVOICE_STATE_PAID,
        expires_at=_NOW + timedelta(minutes=30),
        lines=[(plan.id, 14)],
    )
    session.commit()

    _apply_paid_invoices_inner(session, now=_NOW)
    session.refresh(user)

    assert user.expire_date == _NOW + timedelta(days=14)


# --------------------------------------------------------------------------
# Installer
# --------------------------------------------------------------------------


def test_install_billing_scheduler_is_idempotent() -> None:
    """Repeated installs must not stack lifespans or jobs."""
    app = MagicMock()
    app.state = MagicMock()
    app.state.billing_scheduler_installed = False
    app.router = MagicMock()

    install_billing_scheduler(app)
    # Mark "as installed" the way real flag would behave.
    assert app.state.billing_scheduler_installed is True

    # A second call: must early-return without touching app.router again.
    pre_lifespan = app.router.lifespan_context
    install_billing_scheduler(app)
    assert app.router.lifespan_context is pre_lifespan
