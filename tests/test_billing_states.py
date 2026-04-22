"""
Tests for ``ops.billing.states`` — state machine + webhook dedup.

Uses a scratch SQLite in-memory DB + the billing tables only (same
scoping trick as test_billing_db.py). No upstream tables are
created, so FK to users.id is declared-but-not-enforced (SQLite
default). This keeps the tests fast and hermetic.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from ops.billing.db import (
    INVOICE_STATE_APPLIED,
    INVOICE_STATE_AWAITING_PAYMENT,
    INVOICE_STATE_CANCELLED,
    INVOICE_STATE_CREATED,
    INVOICE_STATE_EXPIRED,
    INVOICE_STATE_FAILED,
    INVOICE_STATE_PAID,
    INVOICE_STATE_PENDING,
    Invoice,
    PaymentEvent,
)
from ops.billing.states import (
    InvoiceStateError,
    is_allowed_transition,
    is_terminal,
    record_webhook_seen,
    transition,
    webhook_fingerprint,
)

# ---------------------------------------------------------------------
# Fixtures — scratch DB with only billing tables
# ---------------------------------------------------------------------


@pytest.fixture
def session() -> Session:
    """Fresh SQLite in-memory engine, billing tables only."""
    billing_tables = [
        Base.metadata.tables[name]
        for name in (
            "aegis_billing_plans",
            "aegis_billing_channels",
            "aegis_billing_invoices",
            "aegis_billing_invoice_lines",
            "aegis_billing_payment_events",
        )
    ]
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=billing_tables)
    with Session(engine) as s:
        yield s


def _make_invoice(
    session: Session,
    state: str = INVOICE_STATE_CREATED,
    provider: str = "trc20",
    provider_invoice_id: str | None = None,
) -> Invoice:
    """Insert a minimal invoice and return it with a real DB id."""
    now = datetime(2026, 4, 22, 12, 0, 0)
    inv = Invoice(
        user_id=1,
        total_cny_fen=5000,
        state=state,
        provider=provider,
        provider_invoice_id=provider_invoice_id,
        payment_url=None,
        trc20_memo=None,
        trc20_expected_amount_millis=None,
        created_at=now,
        paid_at=None,
        applied_at=None,
        expires_at=now + timedelta(minutes=30),
    )
    session.add(inv)
    session.flush()  # get inv.id without committing
    return inv


# ---------------------------------------------------------------------
# Static helpers
# ---------------------------------------------------------------------


def test_is_terminal_recognizes_all_four():
    assert is_terminal(INVOICE_STATE_APPLIED)
    assert is_terminal(INVOICE_STATE_EXPIRED)
    assert is_terminal(INVOICE_STATE_CANCELLED)
    assert is_terminal(INVOICE_STATE_FAILED)
    assert not is_terminal(INVOICE_STATE_CREATED)
    assert not is_terminal(INVOICE_STATE_PAID)


def test_is_allowed_transition_positive_paths():
    assert is_allowed_transition(INVOICE_STATE_CREATED, INVOICE_STATE_PENDING)
    assert is_allowed_transition(
        INVOICE_STATE_PENDING, INVOICE_STATE_AWAITING_PAYMENT
    )
    assert is_allowed_transition(
        INVOICE_STATE_AWAITING_PAYMENT, INVOICE_STATE_PAID
    )
    assert is_allowed_transition(INVOICE_STATE_PAID, INVOICE_STATE_APPLIED)


def test_is_allowed_transition_admin_override_pending_to_paid():
    """Admin emergency skip past payment is valid."""
    assert is_allowed_transition(INVOICE_STATE_PENDING, INVOICE_STATE_PAID)


def test_is_allowed_transition_rejects_terminal_exits():
    """Once applied, can't go anywhere."""
    for next_state in (
        INVOICE_STATE_CREATED,
        INVOICE_STATE_PAID,
        INVOICE_STATE_CANCELLED,
    ):
        assert not is_allowed_transition(INVOICE_STATE_APPLIED, next_state)


def test_is_allowed_transition_rejects_bad_skip():
    """Can't skip awaiting_payment without going through it."""
    assert not is_allowed_transition(INVOICE_STATE_CREATED, INVOICE_STATE_PAID)


# ---------------------------------------------------------------------
# transition() — happy paths
# ---------------------------------------------------------------------


def test_transition_created_to_pending_writes_event(session):
    inv = _make_invoice(session, state=INVOICE_STATE_CREATED)
    transition(
        session,
        inv,
        INVOICE_STATE_PENDING,
        event_type="checkout",
        payload={"user_action": "clicked_checkout"},
    )
    session.flush()
    assert inv.state == INVOICE_STATE_PENDING

    events = (
        session.query(PaymentEvent)
        .filter(PaymentEvent.invoice_id == inv.id)
        .all()
    )
    assert len(events) == 1
    ev = events[0]
    assert ev.event_type == "checkout"
    assert ev.payload_json["from_state"] == INVOICE_STATE_CREATED
    assert ev.payload_json["to_state"] == INVOICE_STATE_PENDING
    assert ev.payload_json["user_action"] == "clicked_checkout"


def test_transition_to_paid_sets_paid_at(session):
    inv = _make_invoice(session, state=INVOICE_STATE_AWAITING_PAYMENT)
    now = datetime(2026, 4, 22, 14, 0, 0)
    transition(
        session,
        inv,
        INVOICE_STATE_PAID,
        event_type="state_paid",
        payload={"tx_hash": "deadbeef"},
        now=now,
    )
    assert inv.paid_at == now
    assert inv.applied_at is None


def test_transition_to_applied_sets_applied_at(session):
    inv = _make_invoice(session, state=INVOICE_STATE_PAID)
    now = datetime(2026, 4, 22, 14, 5, 0)
    transition(
        session,
        inv,
        INVOICE_STATE_APPLIED,
        event_type="grant_applied",
        now=now,
    )
    assert inv.applied_at == now


def test_transition_same_state_is_idempotent_noop(session):
    """Re-applying the current state writes a noop audit row and
    does NOT error. Lets retry-on-error callers be naive."""
    inv = _make_invoice(session, state=INVOICE_STATE_PAID)
    transition(
        session,
        inv,
        INVOICE_STATE_PAID,  # same as current
        event_type="state_paid",
    )
    session.flush()
    events = (
        session.query(PaymentEvent)
        .filter(PaymentEvent.invoice_id == inv.id)
        .all()
    )
    # The noop still writes ONE event (for forensics), but with
    # the ":noop_same_state" suffix.
    assert len(events) == 1
    assert events[0].event_type.endswith(":noop_same_state")


# ---------------------------------------------------------------------
# transition() — illegal moves
# ---------------------------------------------------------------------


def test_transition_illegal_raises_before_side_effects(session):
    inv = _make_invoice(session, state=INVOICE_STATE_CREATED)
    with pytest.raises(InvoiceStateError) as exc:
        transition(
            session,
            inv,
            INVOICE_STATE_APPLIED,  # can't skip from created
            event_type="bad",
        )
    assert exc.value.reason == "illegal_transition"
    assert inv.state == INVOICE_STATE_CREATED  # unchanged
    # No PaymentEvent was written either
    assert session.query(PaymentEvent).count() == 0


def test_transition_from_terminal_state_rejected(session):
    inv = _make_invoice(session, state=INVOICE_STATE_APPLIED)
    with pytest.raises(InvoiceStateError) as exc:
        transition(
            session,
            inv,
            INVOICE_STATE_CANCELLED,
            event_type="admin_cancel",
        )
    assert exc.value.reason == "illegal_transition"


# ---------------------------------------------------------------------
# webhook_fingerprint + record_webhook_seen
# ---------------------------------------------------------------------


def test_fingerprint_deterministic_across_key_order():
    """Same semantic payload → same fingerprint regardless of dict
    ordering. Critical for replay detection."""
    a = webhook_fingerprint(
        "nowpayments",
        {"amount": 100, "order_id": "abc", "status": "paid"},
    )
    b = webhook_fingerprint(
        "nowpayments",
        {"status": "paid", "order_id": "abc", "amount": 100},
    )
    assert a == b


def test_fingerprint_differs_by_provider():
    a = webhook_fingerprint("nowpayments", {"x": 1})
    b = webhook_fingerprint("epay:zpay1", {"x": 1})
    assert a != b


def test_record_webhook_seen_first_time_returns_true(session):
    inv = _make_invoice(session, state=INVOICE_STATE_AWAITING_PAYMENT)
    assert record_webhook_seen(
        session, inv.id, "nowpayments", {"order": "1", "amount": 100}
    )
    session.flush()
    events = (
        session.query(PaymentEvent)
        .filter(PaymentEvent.invoice_id == inv.id)
        .all()
    )
    assert len(events) == 1
    assert events[0].event_type == "webhook_received"


def test_record_webhook_seen_replay_returns_false(session):
    """Second call with same payload is detected → returns False
    and does NOT write a duplicate event."""
    inv = _make_invoice(session, state=INVOICE_STATE_AWAITING_PAYMENT)
    payload = {"order": "1", "amount": 100}
    first = record_webhook_seen(session, inv.id, "nowpayments", payload)
    session.flush()
    second = record_webhook_seen(session, inv.id, "nowpayments", payload)
    session.flush()

    assert first is True
    assert second is False
    # Only one event row despite two calls
    assert (
        session.query(PaymentEvent)
        .filter(PaymentEvent.invoice_id == inv.id)
        .count()
        == 1
    )


def test_record_webhook_seen_different_payload_not_deduped(session):
    """Different semantic payload = genuinely different event,
    both get recorded."""
    inv = _make_invoice(session, state=INVOICE_STATE_AWAITING_PAYMENT)
    assert record_webhook_seen(
        session, inv.id, "nowpayments", {"order": "1", "amount": 100}
    )
    assert record_webhook_seen(
        session, inv.id, "nowpayments", {"order": "1", "amount": 200}
    )
    session.flush()
    assert (
        session.query(PaymentEvent)
        .filter(PaymentEvent.invoice_id == inv.id)
        .count()
        == 2
    )


def test_record_webhook_seen_isolated_per_invoice(session):
    """Same payload for different invoices is not deduped across
    invoices — each invoice has its own replay window."""
    inv_a = _make_invoice(
        session,
        state=INVOICE_STATE_AWAITING_PAYMENT,
        provider_invoice_id="a",
    )
    inv_b = _make_invoice(
        session,
        state=INVOICE_STATE_AWAITING_PAYMENT,
        provider_invoice_id="b",
    )
    payload = {"amount": 100}
    assert record_webhook_seen(session, inv_a.id, "nowpayments", payload)
    assert record_webhook_seen(session, inv_b.id, "nowpayments", payload)
    session.flush()
    assert session.query(PaymentEvent).count() == 2
