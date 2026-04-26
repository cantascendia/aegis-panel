"""
Invoice state machine + transition helper.

Enforces the SPEC-billing-mvp.md state diagram:

    created → pending → awaiting_payment → paid → applied
                │            │
                └ cancelled  ├ expired
                             ├ cancelled
                             └ (admin override) paid

    Terminal states: applied, expired, cancelled, failed
    pending can also jump to failed (provider.create_invoice error)

The ``transition`` function is the SINGLE writable path to
``Invoice.state``. Route handlers, webhooks, schedulers, and admin
actions all go through it. Illegal transitions raise
``InvoiceStateError`` BEFORE any side effect, and every successful
transition writes an immutable ``PaymentEvent`` audit row.

Idempotency is the headline property:
- Webhooks often retry on timeout. The ``provider_event_id`` on
  ``record_webhook_seen`` de-duplicates: re-delivery of the same
  payload is a no-op.
- ``apply_paid_invoices`` re-runs after a crash won't double-grant:
  the ``paid → applied`` transition is rejected if state is already
  ``applied``.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

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
    _now_utc_naive,
)


class InvoiceStateError(RuntimeError):
    """Raised when a state transition is illegal. Carries typed
    ``.reason`` so REST handlers can map to 409 / 422 without
    string-matching the message."""

    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason


# Allowed transitions: {from_state: {valid next states}}
#
# Terminal states (applied / expired / cancelled / failed) have an
# empty set; nothing flows out. If the operator needs to "re-open"
# an expired invoice, they issue a refund + create a fresh one;
# we never mutate the audit trail.
ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    INVOICE_STATE_CREATED: frozenset(
        {INVOICE_STATE_PENDING, INVOICE_STATE_CANCELLED}
    ),
    INVOICE_STATE_PENDING: frozenset(
        {
            INVOICE_STATE_AWAITING_PAYMENT,
            INVOICE_STATE_FAILED,
            INVOICE_STATE_CANCELLED,
            # Admin emergency: jump past payment via manual_apply,
            # which goes pending → paid then scheduler picks up.
            INVOICE_STATE_PAID,
        }
    ),
    INVOICE_STATE_AWAITING_PAYMENT: frozenset(
        {
            INVOICE_STATE_PAID,
            INVOICE_STATE_EXPIRED,
            INVOICE_STATE_CANCELLED,
        }
    ),
    INVOICE_STATE_PAID: frozenset({INVOICE_STATE_APPLIED}),
    # Terminals — empty sets.
    INVOICE_STATE_APPLIED: frozenset(),
    INVOICE_STATE_EXPIRED: frozenset(),
    INVOICE_STATE_CANCELLED: frozenset(),
    INVOICE_STATE_FAILED: frozenset(),
}


TERMINAL_STATES: frozenset[str] = frozenset(
    {
        INVOICE_STATE_APPLIED,
        INVOICE_STATE_EXPIRED,
        INVOICE_STATE_CANCELLED,
        INVOICE_STATE_FAILED,
    }
)


def is_terminal(state: str) -> bool:
    """True if the state cannot transition further."""
    return state in TERMINAL_STATES


def is_allowed_transition(from_state: str, to_state: str) -> bool:
    """Check legality WITHOUT touching the DB. Useful in UI layers
    that want to enable/disable a button before firing the mutation."""
    return to_state in ALLOWED_TRANSITIONS.get(from_state, frozenset())


def transition(
    session: Session,
    invoice: Invoice,
    to_state: str,
    *,
    event_type: str,
    payload: dict[str, Any] | None = None,
    note: str | None = None,
    now: datetime | None = None,
) -> Invoice:
    """Atomically move ``invoice.state`` to ``to_state`` and record
    a ``PaymentEvent`` row describing why.

    Both state update and event insert happen in the caller's
    transaction; the caller ``session.commit()``s after. If commit
    fails, both get rolled back together — no half-written state.

    Side effects beyond state:
    - ``paid_at`` timestamp set when moving to ``paid``
    - ``applied_at`` set when moving to ``applied``

    Parameters:
    - ``event_type``: short identifier for the PaymentEvent row,
      e.g. ``"webhook_received"`` / ``"state_paid"`` /
      ``"admin_manual"`` / ``"reaper_expired"``
    - ``payload``: arbitrary JSON-compatible dict stored on the
      event. Free shape — read-side code defensively handles missing
      keys. Common fields: ``tx_hash`` (TRC20), ``provider_event_id``
      (webhook dedup), ``admin_username`` (manual transitions)
    - ``note``: human-readable free text, used for admin_manual
      justifications
    - ``now``: timestamp injection for tests. Defaults to
      ``_now_utc_naive()`` (naive UTC, matches column shape)
    """
    now = now or _now_utc_naive()
    payload = payload or {}

    if invoice.state == to_state:
        # Idempotent: re-applying same state is a no-op, not an
        # error. Callers doing retry-on-error shouldn't have to
        # special-case "maybe we already did this". We still write
        # a PaymentEvent so the audit log shows the duplicate
        # attempt — forensics value.
        _write_event(
            session,
            invoice.id,
            event_type=f"{event_type}:noop_same_state",
            payload=payload,
            note=note,
            now=now,
        )
        return invoice

    if to_state not in ALLOWED_TRANSITIONS.get(invoice.state, frozenset()):
        raise InvoiceStateError(
            "illegal_transition",
            f"Invoice {invoice.id}: cannot move "
            f"{invoice.state!r} → {to_state!r}. Allowed next: "
            f"{sorted(ALLOWED_TRANSITIONS.get(invoice.state, frozenset()))}",
        )

    previous_state = invoice.state
    invoice.state = to_state

    # Timestamp hooks — stored on the invoice row itself for fast
    # queries (admin "all paid in last 24h" shouldn't join
    # PaymentEvent).
    if to_state == INVOICE_STATE_PAID:
        invoice.paid_at = now
    elif to_state == INVOICE_STATE_APPLIED:
        invoice.applied_at = now

    _write_event(
        session,
        invoice.id,
        event_type=event_type,
        payload={
            **payload,
            "from_state": previous_state,
            "to_state": to_state,
        },
        note=note,
        now=now,
    )

    return invoice


# ---------------------------------------------------------------------
# Webhook replay dedup
# ---------------------------------------------------------------------


def webhook_fingerprint(provider: str, payload: dict[str, Any]) -> str:
    """Compute a deterministic fingerprint of a webhook payload for
    replay detection.

    SHA-256 of (provider + canonicalized JSON). Canonicalization:
    ``sort_keys=True`` + ``separators=(",", ":")`` so the same
    semantic payload always hashes to the same id regardless of
    ordering in transit.

    Used by ``record_webhook_seen`` as the event's ``payload_json
    ["provider_event_id"]``. When the same webhook arrives twice
    (common: provider retries on our 502), the second call to
    ``record_webhook_seen`` detects the prior matching event and
    returns ``False`` to tell the caller "already handled, skip".
    """
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(f"{provider}|{canonical}".encode()).hexdigest()


def record_webhook_seen(
    session: Session,
    invoice_id: int,
    provider: str,
    payload: dict[str, Any],
    *,
    now: datetime | None = None,
) -> bool:
    """Return True if this is the first time we're seeing this
    webhook for this invoice; False if we've already recorded it.

    Writes a ``PaymentEvent`` row with
    ``event_type="webhook_received"`` and
    ``payload_json["provider_event_id"] = <fingerprint>``. On a
    replay, does NOT write a duplicate row — keeps the audit log
    clean of provider-retry noise.

    Caller pattern:

        if not record_webhook_seen(session, invoice.id, "nowpayments", body):
            return  # replay, no-op

        transition(session, invoice, "paid", event_type="state_paid",
                   payload={...})
        session.commit()
    """
    now = now or _now_utc_naive()
    fingerprint = webhook_fingerprint(provider, payload)

    # Check prior events for this invoice + provider with the same
    # fingerprint. We do this in-Python instead of a JSON-path SQL
    # query so it works identically on SQLite and PostgreSQL (the
    # PG 16 CI job would otherwise need a dialect-specific filter).
    prior = (
        session.query(PaymentEvent)
        .filter(
            PaymentEvent.invoice_id == invoice_id,
            PaymentEvent.event_type == "webhook_received",
        )
        .all()
    )
    for ev in prior:
        if ev.payload_json.get("provider_event_id") == fingerprint:
            return False

    _write_event(
        session,
        invoice_id,
        event_type="webhook_received",
        payload={"provider_event_id": fingerprint, "provider": provider},
        note=None,
        now=now,
    )
    return True


# ---------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------


def _write_event(
    session: Session,
    invoice_id: int,
    *,
    event_type: str,
    payload: dict[str, Any],
    note: str | None,
    now: datetime,
) -> PaymentEvent:
    """Create and add a PaymentEvent. Caller owns the transaction."""
    ev = PaymentEvent(
        invoice_id=invoice_id,
        event_type=event_type,
        payload_json=payload,
        note=note,
        created_at=now,
    )
    session.add(ev)
    return ev


__all__ = [
    "ALLOWED_TRANSITIONS",
    "InvoiceStateError",
    "TERMINAL_STATES",
    "is_allowed_transition",
    "is_terminal",
    "record_webhook_seen",
    "transition",
    "webhook_fingerprint",
]
