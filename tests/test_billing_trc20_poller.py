"""
Tests for ``ops.billing.trc20_poller`` — DB integration of TRC20
matching → state transition.

Same SQLite-in-memory pattern as ``test_billing_scheduler.py``: spin
up billing tables + ``users`` + the upstream relations User loads
eagerly, then exercise the poller's inner sync function with
hand-built ``Trc20Transfer`` lists.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import User
from app.models.user import UserDataUsageResetStrategy, UserExpireStrategy
from ops.billing.db import (
    INVOICE_STATE_AWAITING_PAYMENT,
    INVOICE_STATE_PAID,
    PROVIDER_TRC20,
    Invoice,
    PaymentEvent,
)
from ops.billing.trc20_matcher import Trc20Transfer
from ops.billing.trc20_poller import _poll_trc20_invoices_inner

_NOW = datetime(2026, 5, 1, 12, 0, 0)
_WINDOW = timedelta(minutes=30)


@pytest.fixture
def session() -> Session:
    needed = [
        Base.metadata.tables[name]
        for name in (
            "aegis_billing_plans",
            "aegis_billing_channels",
            "aegis_billing_invoices",
            "aegis_billing_invoice_lines",
            "aegis_billing_payment_events",
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


def _make_user(session: Session) -> User:
    user = User(
        username="alice",
        key="kalice",
        activated=True,
        enabled=True,
        removed=False,
        data_limit_reset_strategy=UserDataUsageResetStrategy.no_reset,
        expire_strategy=UserExpireStrategy.NEVER,
        ip_limit=-1,
        used_traffic=0,
        lifetime_used_traffic=0,
        created_at=_NOW,
    )
    session.add(user)
    session.flush()
    return user


def _make_trc20_invoice(
    session: Session,
    *,
    user_id: int,
    memo: str = "ABCDEFGH",
    expected_amount_millis: int = 1223,
    state: str = INVOICE_STATE_AWAITING_PAYMENT,
    created_at: datetime | None = None,
) -> Invoice:
    inv = Invoice(
        user_id=user_id,
        total_cny_fen=880,
        state=state,
        provider=PROVIDER_TRC20,
        provider_invoice_id=memo,
        payment_url=None,
        trc20_memo=memo,
        trc20_expected_amount_millis=expected_amount_millis,
        created_at=created_at or _NOW,
        paid_at=None,
        applied_at=None,
        expires_at=(created_at or _NOW) + _WINDOW,
    )
    session.add(inv)
    session.flush()
    return inv


def _transfer(
    *,
    tx_hash: str = "tx-001",
    amount_millis: int = 1223,
    memo: str | None = "ABCDEFGH",
    timestamp: datetime | None = None,
    confirmed: bool = True,
    block_number: int = 100,
) -> Trc20Transfer:
    return Trc20Transfer(
        tx_hash=tx_hash,
        amount_millis=amount_millis,
        memo=memo,
        timestamp=timestamp or _NOW + timedelta(minutes=5),
        confirmed=confirmed,
        block_number=block_number,
    )


# --------------------------------------------------------------------------
# Happy paths
# --------------------------------------------------------------------------


def test_poller_marks_memo_matched_invoice_paid(session) -> None:
    user = _make_user(session)
    inv = _make_trc20_invoice(session, user_id=user.id, memo="ABCDEFGH")
    session.commit()

    transfers = [_transfer(memo="ABCDEFGH")]
    count = _poll_trc20_invoices_inner(
        session,
        transfers,
        payment_window=_WINDOW,
        min_confirmations=1,
        now=_NOW + timedelta(minutes=10),
    )

    assert count == 1
    session.refresh(inv)
    assert inv.state == INVOICE_STATE_PAID
    assert inv.paid_at is not None


def test_poller_marks_amount_matched_invoice_paid(session) -> None:
    """Mobile-wallet path: no memo on tx, amount + window match."""
    user = _make_user(session)
    inv = _make_trc20_invoice(
        session, user_id=user.id, expected_amount_millis=1223
    )
    session.commit()

    transfers = [_transfer(memo=None, amount_millis=1223)]
    count = _poll_trc20_invoices_inner(
        session,
        transfers,
        payment_window=_WINDOW,
        min_confirmations=1,
        now=_NOW + timedelta(minutes=10),
    )

    assert count == 1
    session.refresh(inv)
    assert inv.state == INVOICE_STATE_PAID


def test_poller_records_match_metadata_in_payment_event(session) -> None:
    user = _make_user(session)
    inv = _make_trc20_invoice(session, user_id=user.id)
    session.commit()

    transfers = [_transfer(tx_hash="0xdeadbeef", memo="ABCDEFGH")]
    _poll_trc20_invoices_inner(
        session,
        transfers,
        payment_window=_WINDOW,
        min_confirmations=1,
        now=_NOW + timedelta(minutes=10),
    )

    events = (
        session.query(PaymentEvent)
        .filter(
            PaymentEvent.invoice_id == inv.id,
            PaymentEvent.event_type == "state_paid",
        )
        .all()
    )
    assert len(events) == 1
    payload = events[0].payload_json
    assert payload["tx_hash"] == "0xdeadbeef"
    assert payload["matched_via"] == "memo"
    assert payload["amount_millis"] == 1223


# --------------------------------------------------------------------------
# Skip cases
# --------------------------------------------------------------------------


def test_poller_skips_invoices_outside_payment_window(session) -> None:
    """Invoice past payment window is the reaper's responsibility,
    not the poller's."""
    user = _make_user(session)
    old = _NOW - timedelta(minutes=60)  # created an hour ago
    inv = _make_trc20_invoice(session, user_id=user.id, created_at=old)
    session.commit()

    transfers = [_transfer(memo="ABCDEFGH")]
    count = _poll_trc20_invoices_inner(
        session,
        transfers,
        payment_window=_WINDOW,
        min_confirmations=1,
        now=_NOW,
    )

    assert count == 0
    session.refresh(inv)
    assert inv.state == INVOICE_STATE_AWAITING_PAYMENT


def test_poller_ignores_non_trc20_invoices(session) -> None:
    """An EPay invoice in awaiting_payment must not be touched by
    the trc20 poller."""
    user = _make_user(session)
    inv = Invoice(
        user_id=user.id,
        total_cny_fen=880,
        state=INVOICE_STATE_AWAITING_PAYMENT,
        provider="epay:test",
        provider_invoice_id="EPAY-1",
        created_at=_NOW,
        paid_at=None,
        applied_at=None,
        expires_at=_NOW + _WINDOW,
    )
    session.add(inv)
    session.commit()

    count = _poll_trc20_invoices_inner(
        session,
        [_transfer()],
        payment_window=_WINDOW,
        min_confirmations=1,
        now=_NOW + timedelta(minutes=5),
    )

    assert count == 0


def test_poller_idempotent_on_second_run(session) -> None:
    """Same transfers re-fed: state-machine guard prevents double-pay."""
    user = _make_user(session)
    _make_trc20_invoice(session, user_id=user.id)
    session.commit()

    transfers = [_transfer(memo="ABCDEFGH")]
    first = _poll_trc20_invoices_inner(
        session,
        transfers,
        payment_window=_WINDOW,
        min_confirmations=1,
        now=_NOW + timedelta(minutes=5),
    )
    second = _poll_trc20_invoices_inner(
        session,
        transfers,
        payment_window=_WINDOW,
        min_confirmations=1,
        now=_NOW + timedelta(minutes=5),
    )

    assert first == 1
    assert second == 0


def test_poller_skips_invoice_missing_trc20_fields(session) -> None:
    """Defence-in-depth: an awaiting_payment trc20 invoice with NULL
    memo / amount is corrupt; we skip with a warning, not crash."""
    user = _make_user(session)
    inv = Invoice(
        user_id=user.id,
        total_cny_fen=880,
        state=INVOICE_STATE_AWAITING_PAYMENT,
        provider=PROVIDER_TRC20,
        provider_invoice_id=None,
        trc20_memo=None,  # corrupt
        trc20_expected_amount_millis=None,
        created_at=_NOW,
        paid_at=None,
        applied_at=None,
        expires_at=_NOW + _WINDOW,
    )
    session.add(inv)
    session.commit()

    count = _poll_trc20_invoices_inner(
        session,
        [_transfer()],
        payment_window=_WINDOW,
        min_confirmations=1,
        now=_NOW + timedelta(minutes=5),
    )

    assert count == 0
    session.refresh(inv)
    assert inv.state == INVOICE_STATE_AWAITING_PAYMENT


def test_poller_handles_no_open_invoices_no_transfers(session) -> None:
    """Empty case: no SELECT result, no work, return 0."""
    count = _poll_trc20_invoices_inner(
        session,
        [],
        payment_window=_WINDOW,
        min_confirmations=1,
        now=_NOW,
    )
    assert count == 0


def test_poller_handles_open_invoices_no_transfers(session) -> None:
    """No tx delivered yet — invoice stays awaiting_payment."""
    user = _make_user(session)
    inv = _make_trc20_invoice(session, user_id=user.id)
    session.commit()

    count = _poll_trc20_invoices_inner(
        session,
        [],
        payment_window=_WINDOW,
        min_confirmations=1,
        now=_NOW + timedelta(minutes=5),
    )

    assert count == 0
    session.refresh(inv)
    assert inv.state == INVOICE_STATE_AWAITING_PAYMENT


# --------------------------------------------------------------------------
# Confirmations gate
# --------------------------------------------------------------------------


def test_poller_respects_min_confirmations_threshold(session) -> None:
    """min_confirmations=3 with all transfers at the head block
    means none have ≥ 3 confirmations behind. No payment lands."""
    user = _make_user(session)
    inv = _make_trc20_invoice(session, user_id=user.id)
    session.commit()

    transfers = [
        _transfer(memo="ABCDEFGH", block_number=100),
    ]
    count = _poll_trc20_invoices_inner(
        session,
        transfers,
        payment_window=_WINDOW,
        min_confirmations=3,
        now=_NOW + timedelta(minutes=5),
    )

    assert count == 0
    session.refresh(inv)
    assert inv.state == INVOICE_STATE_AWAITING_PAYMENT


def test_poller_with_deeper_confirmations_marks_paid(session) -> None:
    """When the chain has moved past the tx by 2+ blocks, min=3 satisfied."""
    user = _make_user(session)
    inv = _make_trc20_invoice(session, user_id=user.id)
    session.commit()

    transfers = [
        _transfer(memo="ABCDEFGH", block_number=100),
        # newer txs at higher block numbers move the head
        _transfer(
            tx_hash="other",
            memo=None,
            amount_millis=42,
            block_number=103,
        ),
    ]
    count = _poll_trc20_invoices_inner(
        session,
        transfers,
        payment_window=_WINDOW,
        min_confirmations=3,
        now=_NOW + timedelta(minutes=5),
    )

    assert count == 1
    session.refresh(inv)
    assert inv.state == INVOICE_STATE_PAID
