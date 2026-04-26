"""TRC20 invoice poller — APScheduler task body.

Run every ``BILLING_TRC20_POLL_INTERVAL`` seconds (default 30s) by
:func:`ops.billing.scheduler.install_billing_scheduler`. One tick:

1. Find ``awaiting_payment`` invoices with ``provider == "trc20"``
   whose payment window has not yet elapsed.
2. Fetch recent confirmed transfers to our receive address from
   Tronscan (one HTTP call covering all open invoices).
3. Match each invoice against the transfer set
   (:mod:`ops.billing.trc20_matcher`).
4. For matches, transition the invoice ``awaiting_payment → paid`` —
   the A.5 ``apply_paid_invoices`` job picks it up next tick to
   actually grant the user.

Design choices
--------------
- **One Tronscan call per tick**, not per invoice. Avoids the
  N-invoices × pollers-per-minute fan-out that would burn rate-limit
  quota during a busy day.
- **Idempotency**: each :class:`Trc20Transfer` carries a unique
  ``tx_hash``. The state-machine guard rejects repeated
  ``awaiting_payment → paid`` on an already-paid invoice. We record
  the ``tx_hash`` on the ``state_paid`` :class:`PaymentEvent` so a
  re-poll over the same set of transfers (after a crash) cannot
  double-pay.
- **No commit-per-poll-cycle batch**: if 5 of 100 open invoices match,
  we commit each one independently. A single corrupted state row
  shouldn't block the others.
- **Fail-loud-but-don't-crash on Tronscan failure**: we log + skip
  the tick. The next 30-s tick re-tries; persistent failure surfaces
  as repeated log entries every interval.
- **MIN_CONFIRMATIONS gate**: applied via the matcher's
  ``min_confirmations_satisfied`` flag, computed from the highest
  block_number returned vs. each transfer's block_number. Default 1
  is permissive (Tron block-time ≈ 3s); set higher for paranoia.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from sqlalchemy.orm import Session

from ops.billing.db import (
    INVOICE_STATE_AWAITING_PAYMENT,
    INVOICE_STATE_PAID,
    PROVIDER_TRC20,
    Invoice,
    _now_utc_naive,
)
from ops.billing.states import InvoiceStateError, transition
from ops.billing.trc20_matcher import (
    CandidateInvoice,
    Trc20Transfer,
    find_matching_transfer,
)

logger = logging.getLogger(__name__)


def _candidate_from_invoice(inv: Invoice) -> CandidateInvoice | None:
    """Project a DB row to the matcher's input shape.

    Returns ``None`` if the invoice is missing TRC20-required fields
    (memo / expected amount). Should never happen in practice — the
    provider sets both at create_invoice — but we defend against
    drift between provider and DB.
    """
    if not inv.trc20_memo or inv.trc20_expected_amount_millis is None:
        logger.warning(
            "trc20 poller: invoice %s missing trc20_memo / expected amount; "
            "skipping. Likely indicates a provider/DB drift.",
            inv.id,
        )
        return None
    return CandidateInvoice(
        invoice_id=inv.id,
        memo=inv.trc20_memo,
        expected_amount_millis=inv.trc20_expected_amount_millis,
        created_at=inv.created_at,
    )


def _confirmations_for(
    transfer: Trc20Transfer,
    *,
    head_block: int,
    min_confirmations: int,
) -> bool:
    """True iff ``transfer.block_number`` is at least ``min_confirmations``
    blocks behind the chain head.

    ``head_block`` is the maximum ``block_number`` we observed in this
    tick's response. Approximating "head" by "max in response" is a
    1-block-stale view of the chain, which is fine: the next tick will
    update if the user paid right at the head.
    """
    if not transfer.confirmed:
        return False
    return (head_block - transfer.block_number) >= (min_confirmations - 1)


def _poll_trc20_invoices_inner(
    db: Session,
    transfers: list[Trc20Transfer],
    *,
    payment_window: timedelta,
    min_confirmations: int,
    now=None,
) -> int:
    """Body of the poller, factored out so tests don't need
    APScheduler or aiohttp. Returns the number of invoices flipped to
    paid this tick.

    Caller passes ``transfers`` already fetched from Tronscan; in
    production this is :meth:`TronscanClient.list_recent_transfers`
    output. Tests pass a hand-built list.
    """
    now = now or _now_utc_naive()

    # Fetch open TRC20 invoices in one query. We only consider
    # ``awaiting_payment`` — ``pending`` invoices haven't yet shown
    # the user a memo, so a tx couldn't possibly arrive for them.
    candidates = (
        db.query(Invoice)
        .filter(
            Invoice.state == INVOICE_STATE_AWAITING_PAYMENT,
            Invoice.provider == PROVIDER_TRC20,
        )
        .order_by(Invoice.id.asc())
        .all()
    )
    if not candidates:
        return 0

    head_block = max((t.block_number for t in transfers), default=0)
    paid_count = 0

    for inv in candidates:
        # Stop polling past the payment window — A.5 reaper is
        # responsible for flipping these to expired.
        if (now - inv.created_at) > payment_window:
            continue

        match_input = _candidate_from_invoice(inv)
        if match_input is None:
            continue

        # Confirmations are computed per-transfer; the matcher only
        # gets a boolean "should I consider txs at all". For each
        # candidate inv, we compute whether ANY tx in scope satisfies
        # confirmations and let the matcher pick the right tx
        # (memo > amount).
        confirmed_in_scope = [
            t
            for t in transfers
            if _confirmations_for(
                t,
                head_block=head_block,
                min_confirmations=min_confirmations,
            )
        ]
        match = find_matching_transfer(
            confirmed_in_scope,
            match_input,
            payment_window=payment_window,
            min_confirmations_satisfied=True,
        )
        if match is None:
            continue

        try:
            transition(
                db,
                inv,
                INVOICE_STATE_PAID,
                event_type="state_paid",
                payload={
                    "tx_hash": match.tx_hash,
                    "amount_millis": match.amount_millis,
                    "block_number": match.block_number,
                    "matched_via": (
                        "memo" if match.memo == inv.trc20_memo else "amount"
                    ),
                },
                note="trc20 poller observed matching on-chain tx",
                now=now,
            )
            db.commit()
            paid_count += 1
        except InvoiceStateError as exc:
            db.rollback()
            logger.info(
                "trc20 poller: invoice %s skipped (state race): %s",
                inv.id,
                exc.reason,
            )
        except Exception:  # pragma: no cover — defensive
            db.rollback()
            logger.exception(
                "trc20 poller: invoice %s failed to mark paid", inv.id
            )

    if paid_count:
        logger.info("trc20 poller marked %s invoice(s) paid", paid_count)
    return paid_count


async def run_poll_trc20_invoices() -> int:
    """APScheduler entry point. Owns the DB session + Tronscan client
    lifecycle.

    Skipped when ``BILLING_TRC20_ENABLED=False`` — no point spending
    a Tronscan call per tick when the provider isn't even visible to
    checkout. We still run the SQL query (cheap) so accidentally-
    enabled invoices don't dangle silently after operator disables
    TRC20 mid-cycle.
    """
    from app.db import GetDB
    from ops.billing.trc20_client import Trc20ClientError, TronscanClient
    from ops.billing.trc20_config import (
        BILLING_TRC20_ENABLED,
        BILLING_TRC20_MIN_CONFIRMATIONS,
        BILLING_TRC20_PAYMENT_WINDOW_MINUTES,
        BILLING_TRC20_RECEIVE_ADDRESS,
    )

    if not BILLING_TRC20_ENABLED:
        return 0

    transfers: list[Trc20Transfer] = []
    try:
        async with TronscanClient.from_env() as client:
            transfers = await client.list_recent_transfers(
                to_address=BILLING_TRC20_RECEIVE_ADDRESS
            )
    except Trc20ClientError as exc:
        logger.warning(
            "trc20 poller: tronscan fetch failed, skipping: %s", exc
        )
        return 0

    payment_window = timedelta(minutes=BILLING_TRC20_PAYMENT_WINDOW_MINUTES)
    with GetDB() as db:
        return _poll_trc20_invoices_inner(
            db,
            transfers,
            payment_window=payment_window,
            min_confirmations=BILLING_TRC20_MIN_CONFIRMATIONS,
        )


__all__ = [
    "run_poll_trc20_invoices",
]
