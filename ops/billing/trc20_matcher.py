"""TRC20 transfer → invoice matching, pure logic.

The poller fetches recent transfers to the receive address, then asks
this module "does any of these match an open invoice?" Two strategies
in priority order:

1. **Memo match** — the user's wallet included our 8-char memo in the
   tx ``data`` field. O(1) match, unambiguous, our preferred path.
2. **Amount + window match** — the wallet stripped the memo (most
   mobile wallets do). We fall back to ``(exact USDT amount, within
   payment window)``. Concurrent invoices are disambiguated by a
   per-invoice **cents-dither**: two open invoices for the same plan
   add ``invoice_id % 1000`` USDT-millis to the expected amount, so
   they have distinct totals at the millis-precision level.

Why pure functions
------------------
The poller's I/O (Tronscan client + DB) is in ``trc20_poller.py``.
Matching is the part most likely to change as we observe production
wallets and add edge cases. Keeping it pure means we can pile on
unit tests without spinning up async + HTTP + DB.

Why no proximity / partial match
--------------------------------
"User paid 9.99 instead of 10.00" → reject with no match. The user
must pay the exact amount we quoted. Auto-correcting under-pays
opens "loyal user pays a few cents short, gets the same plan" abuse;
auto-correcting over-pays makes the operator owe refunds. Hard
rejection forces the user to re-send if they undershot — annoying
but not insolvable, and the audit trail stays clean.

The cents-dither makes "exact amount" robust to concurrent invoices
without lossy fuzzy matching: invoice 100 expects 5000 millis, invoice
101 expects 5001 millis (5000 + 101%1000), invoice 200 expects 5200
millis. A single tx can map to **at most one** invoice.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from ops.billing.providers.trc20 import is_valid_memo


@dataclass(frozen=True)
class Trc20Transfer:
    """Normalised TRC20 transfer record from the Tronscan client.

    Fields chosen so the matcher needs no chain-vendor specifics —
    every field below is recoverable from any TRC20 indexer (Tronscan,
    Trongrid, your own node).

    Amounts are integer USDT-millis (1/1000 USDT) to match
    :func:`ops.billing.pricing.convert_fen_to_usdt_millis`'s output
    shape — any integer arithmetic mismatch between provider/poller
    surfaces here at compile time, not at production runtime.
    """

    tx_hash: str
    amount_millis: int
    memo: (
        str | None
    )  # decoded from tx ``data`` field; None if absent / unparseable
    timestamp: datetime  # tx confirmation time, UTC naive
    confirmed: bool
    block_number: int


@dataclass(frozen=True)
class CandidateInvoice:
    """The invoice-side projection the matcher needs.

    Built by the poller from :class:`ops.billing.db.Invoice` rows; we
    take a small dataclass instead of the SQLAlchemy row to keep this
    module testable without any DB import.
    """

    invoice_id: int
    memo: str
    expected_amount_millis: int
    created_at: datetime


def add_cents_dither(amount_millis: int, invoice_id: int) -> int:
    """Add a per-invoice unique offset so concurrent invoices have
    distinct totals at the millis-precision level.

    ``invoice_id % 1000`` gives us 1000 distinct dither values; with
    typical operator volume (≤ a few open invoices per minute) that's
    far more than enough collision avoidance. Bigger moduli give more
    headroom but inflate the user-paid amount; 1000 millis = 1 USDT
    cent, the minimum perceptible.

    Caller responsibility: ``provider.create_invoice`` calls this to
    compute ``trc20_expected_amount_millis``; the matcher uses the
    *dithered* value to compare against incoming txs.
    """
    if invoice_id <= 0:
        raise ValueError(f"invoice_id must be positive, got {invoice_id}")
    if amount_millis < 0:
        raise ValueError(f"amount_millis must be >= 0, got {amount_millis}")
    return amount_millis + (invoice_id % 1000)


def find_matching_transfer(
    transfers: list[Trc20Transfer],
    invoice: CandidateInvoice,
    *,
    payment_window: timedelta,
    min_confirmations_satisfied: bool,
) -> Trc20Transfer | None:
    """Return the single transfer that matches this invoice, or ``None``.

    The poller calls this once per open invoice with the list of
    recently-fetched transfers. ``payment_window`` is the operator's
    ``BILLING_TRC20_PAYMENT_WINDOW_MINUTES`` (default 30 min) — we
    refuse to match a tx that arrived outside this window after invoice
    creation, even if amount + memo align, because such a stale match
    could indicate an attacker reusing a memo from an expired invoice.

    ``min_confirmations_satisfied`` is the caller's job to compute (it
    needs the current block height); we just gate on the boolean.

    Strategy:
    1. Memo match: if any transfer has ``memo == invoice.memo``,
       prefer it. Memo collision is cryptographically improbable
       (HMAC-SHA256), so a memo match is canonical.
    2. Amount + window match: if no memo match, look for a transfer
       with ``amount_millis == invoice.expected_amount_millis`` and
       ``timestamp`` within the payment window from invoice creation.

    Returns the matched transfer, or ``None``.
    """
    if not min_confirmations_satisfied:
        return None
    if not transfers:
        return None

    deadline = invoice.created_at + payment_window

    # Strategy 1: memo match.
    for t in transfers:
        if not t.confirmed:
            continue
        if t.memo is None or not is_valid_memo(t.memo):
            continue
        if t.memo == invoice.memo:
            # Memo-matched txs still respect the payment window — a
            # memo from a long-expired invoice should not retroactively
            # close a fresh one (extremely rare given salting, but
            # cheap to guard).
            if invoice.created_at <= t.timestamp <= deadline:
                return t

    # Strategy 2: amount + window match.
    for t in transfers:
        if not t.confirmed:
            continue
        if t.amount_millis != invoice.expected_amount_millis:
            continue
        if invoice.created_at <= t.timestamp <= deadline:
            return t

    return None


__all__ = [
    "CandidateInvoice",
    "Trc20Transfer",
    "add_cents_dither",
    "find_matching_transfer",
]
