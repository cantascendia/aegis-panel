"""
APScheduler integration for the billing layer (A.5).

Two periodic jobs run inside the panel process, both feature-owned (no
edits to ``app/tasks/``):

- ``reap_expired_invoices`` — flips invoices stuck in
  ``awaiting_payment`` past their ``expires_at`` to ``expired``. The
  user-displayed countdown becomes truthful: a 30-min payment window
  the user missed shows as expired in the UI within ``BILLING_REAP_INTERVAL``
  seconds, instead of dangling forever. Without this, the only thing
  that retired an awaiting_payment invoice was the webhook arriving;
  abandoned carts would clutter the admin "open invoices" view forever.

- ``apply_paid_invoices`` — picks up invoices in ``paid`` state and
  applies their grant (subscription extension + extra GB) to the user
  row, then transitions to ``applied``. Webhook handlers deliberately
  stop at ``paid`` so the user-facing mutation runs in a single place
  with one well-tested code path; the scheduler is that single place.

Both jobs follow the same hardening pattern as
``hardening/iplimit/scheduler.py``:

- ``AsyncIOScheduler`` started inside a ``lifespan`` wrapper so
  upstream's custom lifespan composition keeps working.
- ``coalesce=True`` + ``max_instances=1`` to avoid pile-up when a job
  takes longer than its interval (e.g. WHOIS hung, DB locked).
- Idempotent installer: repeated calls are no-ops, matching the
  ``apply_panel_hardening`` "called exactly once but defend anyway"
  contract.
- One commit per invoice, not per batch. A poison row (e.g. user
  deleted out from under a paid invoice) shouldn't poison the entire
  sweep — log + skip + carry on, audit row records the failure.

Crash-safety
------------
Both jobs are crash-safe by virtue of the state machine:
- The reaper transitions ``awaiting_payment → expired`` atomically; a
  crash mid-batch leaves processed rows in ``expired`` and unprocessed
  rows in ``awaiting_payment``, picked up next tick.
- The applier transitions ``paid → applied`` AFTER mutating the User
  row; if the commit fails after the User mutation but before the
  state flip, the next tick re-runs the User mutation **and the
  state-machine guard rejects double-apply**. The User-side mutation
  must therefore be idempotent on the second pass — see
  ``ops.billing.grants.apply_grant_to_user`` for why we structure the
  mutation as additive deltas (a re-run would double-grant) and rely
  on the state-machine guard rather than per-mutation idempotency.

  Concretely: ``apply_grant_to_user`` is NOT idempotent on its own.
  We commit ``user mutation + invoice transition + payment event`` in
  ONE transaction so the all-or-nothing guarantee comes from the DB,
  not from re-application safety. A crash before commit rolls all of
  it back; a crash after commit means the ``paid → applied``
  transition already landed and the next tick sees ``applied`` and
  skips.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import TYPE_CHECKING

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from decouple import config
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import GetDB
from app.db.models import User
from ops.billing.db import (
    INVOICE_STATE_AWAITING_PAYMENT,
    INVOICE_STATE_PAID,
    Invoice,
    InvoiceLine,
    Plan,
    _now_utc_naive,
)
from ops.billing.grants import apply_grant_to_user
from ops.billing.pricing import (
    CartLine,
    InvalidCart,
    compute_user_grant,
)
from ops.billing.states import (
    INVOICE_STATE_APPLIED,
    INVOICE_STATE_EXPIRED,
    InvoiceStateError,
    transition,
)

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# Tunables (env-configurable for ops who want longer / shorter ticks)
# ---------------------------------------------------------------------

# How often to sweep awaiting_payment invoices for expiry. 60s gives
# the user-facing countdown a tolerable jitter — at most one minute of
# "expired but still says pending" before the UI catches up. Lower
# bounds are bounded by DB load: this query uses
# ix_billing_invoices_state_expires so it's cheap, but per-row commit
# does N round-trips per tick.
BILLING_REAP_INTERVAL: int = int(config("BILLING_REAP_INTERVAL", default=60))

# How often to sweep paid invoices for grant application. 30s is the
# "user paid → user sees their plan" SLA we promise. The webhook itself
# transitions ``awaiting_payment → paid`` synchronously in milliseconds;
# this is just the additional "paid → applied" leg. Faster ticks
# improve UX during peak payment hours but cost a query per tick of
# nothing-to-do work outside those hours.
BILLING_APPLY_INTERVAL: int = int(config("BILLING_APPLY_INTERVAL", default=30))

# Cap on how many invoices a single tick processes. Prevents a backlog
# from monopolising a tick and blowing past the next tick's
# max_instances guard. 200 = ~2-3s of DB work even on cold cache;
# anything larger and we'd want to break into batches anyway.
_BATCH_LIMIT = 200


# ---------------------------------------------------------------------
# Job 1: reap_expired_invoices
# ---------------------------------------------------------------------


def _reap_expired_invoices_inner(db: Session, *, now=None) -> int:
    """Body of the reaper, factored out for unit-testing without
    APScheduler. Returns the number of invoices flipped to expired.

    Uses ``GetDB`` upstream; tests pass their own session. ``now`` is
    injected for time-travel tests; default is ``_now_utc_naive()``.
    """
    now = now or _now_utc_naive()

    # SELECT only what we need. The (state, expires_at) composite
    # index makes this a range scan over expired rows — no full
    # table scan even with millions of historical paid/applied rows.
    candidates = (
        db.query(Invoice)
        .filter(
            Invoice.state == INVOICE_STATE_AWAITING_PAYMENT,
            Invoice.expires_at < now,
        )
        .order_by(Invoice.id.asc())
        .limit(_BATCH_LIMIT)
        .all()
    )

    expired_count = 0
    for invoice in candidates:
        try:
            transition(
                db,
                invoice,
                INVOICE_STATE_EXPIRED,
                event_type="reaper_expired",
                payload={
                    "expires_at": invoice.expires_at.isoformat(),
                    "reaped_at": now.isoformat(),
                },
                note="auto-expired by A.5 scheduler past payment window",
                now=now,
            )
            db.commit()
            expired_count += 1
        except InvoiceStateError as exc:
            # State changed under us between SELECT and UPDATE (e.g.
            # webhook landed paid). Roll back the failed transition
            # but don't kill the sweep; the row simply isn't ours to
            # expire any more.
            db.rollback()
            logger.info(
                "reaper: invoice %s skipped (state race): %s",
                invoice.id,
                exc.reason,
            )
        except Exception:  # pragma: no cover — defensive
            db.rollback()
            logger.exception("reaper: invoice %s failed to expire", invoice.id)

    if expired_count:
        logger.info("billing reaper expired %s invoice(s)", expired_count)
    return expired_count


async def run_reap_expired_invoices() -> int:
    """APScheduler entry point. Owns the DB session lifecycle."""
    with GetDB() as db:
        return _reap_expired_invoices_inner(db)


# ---------------------------------------------------------------------
# Job 2: apply_paid_invoices
# ---------------------------------------------------------------------


def _apply_paid_invoices_inner(db: Session, *, now=None) -> int:
    """Body of the applier; testable without APScheduler. Returns the
    number of invoices successfully applied."""
    now = now or _now_utc_naive()

    # Identify candidate IDs first (cheap, lock-free). We lock each
    # row individually inside the loop so a long-running grant
    # application doesn't hold a lock across the whole batch.
    candidate_ids = (
        db.query(Invoice.id)
        .filter(Invoice.state == INVOICE_STATE_PAID)
        .order_by(Invoice.id.asc())
        .limit(_BATCH_LIMIT)
        .all()
    )

    applied_count = 0
    for (invoice_id,) in candidate_ids:
        # Re-fetch with row-level lock + ``SKIP LOCKED`` so:
        #   - ``apply_manual`` holding a FOR UPDATE on the same row
        #     causes us to skip it this tick (it'll move to applied
        #     before the next tick, and we won't see it again).
        #   - Two scheduler instances (e.g. blue/green deploy) don't
        #     contend on the same row.
        # SQLite's pool ignores the lock clauses but serialises
        # writes anyway; PostgreSQL (production) honours them.
        invoice = db.execute(
            select(Invoice)
            .where(
                Invoice.id == invoice_id,
                Invoice.state == INVOICE_STATE_PAID,
            )
            .with_for_update(skip_locked=True)
        ).scalar_one_or_none()
        if invoice is None:
            # Either another worker / apply_manual claimed it, or its
            # state changed between the candidate scan and the lock
            # attempt. Either way, not ours to apply this tick.
            continue
        try:
            apply_invoice_grant(db, invoice, now=now)
            db.commit()
            applied_count += 1
        except InvoiceStateError as exc:
            db.rollback()
            logger.info(
                "applier: invoice %s skipped (state race): %s",
                invoice.id,
                exc.reason,
            )
        except ApplierSkip as exc:
            db.rollback()
            logger.warning(
                "applier: invoice %s skipped (%s): %s",
                invoice.id,
                exc.reason,
                exc,
            )
        except Exception:  # pragma: no cover — defensive
            db.rollback()
            logger.exception("applier: invoice %s failed to apply", invoice.id)

    if applied_count:
        logger.info("billing applier applied %s invoice(s)", applied_count)
    return applied_count


class ApplierSkip(RuntimeError):
    """Raised when an individual invoice can't be applied for a
    business reason (e.g. user deleted, plan removed). Caller logs +
    rolls back; the invoice stays in ``paid`` for an operator to
    investigate via the audit log.

    Carries ``.reason`` for log-grep ergonomics.

    Public (was ``_ApplierSkip``): ``apply_invoice_grant`` is now also
    called from the admin ``apply_manual`` endpoint, which needs to
    catch this to translate into an HTTP 409.
    """

    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason


# Backwards-compat alias for any callers (tests, ad-hoc scripts) that
# imported the private name from before A.5 → apply_manual integration.
_ApplierSkip = ApplierSkip


def apply_invoice_grant(
    db: Session, invoice: Invoice, *, now: datetime | None = None
) -> None:
    """Apply one paid invoice's grant to its user, then transition to
    ``applied``. Caller owns commit/rollback.

    This is the **single source of truth** for "paid invoice → user
    quota mutation + state=applied". Used by:

    - ``_apply_paid_invoices_inner`` — the A.5 scheduler tick
      (``state=paid`` → grant → ``state=applied``).
    - ``apply_manual`` admin endpoint — synchronous emergency flow
      after the admin has just transitioned ``→ paid``.

    Channel-agnostic: only the ``paid → applied`` leg lives here, so
    EPay (webhook → paid) and TRC20 (poller → paid) and admin manual
    all share one code path. Don't add channel-specific branches.

    Pre-condition: ``invoice.state == 'paid'``. Caller is responsible
    for getting it there via :func:`ops.billing.states.transition`.

    Raises:
        ApplierSkip: business-level skip reasons (user gone, plan
            gone, cart no longer valid). The invoice remains in
            ``paid`` for operator attention.
        InvoiceStateError: state changed under us mid-flight (race),
            or pre-condition violated (caller passed a non-paid row).
    """
    now = now or _now_utc_naive()
    # Resolve user.
    user = db.query(User).filter(User.id == invoice.user_id).one_or_none()
    if user is None:
        raise ApplierSkip(
            "user_missing",
            f"Invoice {invoice.id} references user {invoice.user_id} "
            f"which is missing. Did the admin hard-delete?",
        )

    # Materialise lines + plans into the (CartLine, plans) shape that
    # ``compute_user_grant`` consumes. Doing this here rather than in
    # pricing.py keeps pricing.py I/O-free.
    line_rows: list[InvoiceLine] = list(invoice.lines)
    if not line_rows:
        raise ApplierSkip(
            "no_lines",
            f"Invoice {invoice.id} has no lines; cannot derive grant",
        )

    plan_ids = {ln.plan_id for ln in line_rows}
    plans_rows: list[Plan] = db.query(Plan).filter(Plan.id.in_(plan_ids)).all()
    plans = {p.id: p for p in plans_rows}
    missing = plan_ids - plans.keys()
    if missing:
        raise ApplierSkip(
            "plan_missing",
            f"Invoice {invoice.id} references plans {sorted(missing)} "
            f"that no longer exist; operator must reissue or refund",
        )

    cart_lines = [
        CartLine(plan_id=ln.plan_id, quantity=ln.quantity) for ln in line_rows
    ]

    try:
        grant = compute_user_grant(cart_lines, plans)
    except InvalidCart as exc:
        raise ApplierSkip(
            f"invalid_cart:{exc.reason}",
            f"Invoice {invoice.id} cart no longer valid: {exc}",
        ) from exc

    applied = apply_grant_to_user(user, grant, now=now)

    # Transition to applied LAST so a failure above leaves the invoice
    # in ``paid`` for retry. The state-machine guard prevents
    # double-apply if we've already landed once.
    transition(
        db,
        invoice,
        INVOICE_STATE_APPLIED,
        event_type="state_applied",
        payload={
            "user_id": user.id,
            "grant_gb_delta": applied.grant_gb_delta,
            "grant_days_delta": applied.grant_days_delta,
            "data_limit_bytes_before": applied.data_limit_bytes_before,
            "data_limit_bytes_after": applied.data_limit_bytes_after,
            "expire_strategy_before": applied.expire_strategy_before,
            "expire_strategy_after": applied.expire_strategy_after,
            # Datetimes serialise to isoformat for round-trip stability
            # in the JSON payload column. ``None`` stays ``None``.
            "expire_date_before": (
                applied.expire_date_before.isoformat()
                if applied.expire_date_before
                else None
            ),
            "expire_date_after": (
                applied.expire_date_after.isoformat()
                if applied.expire_date_after
                else None
            ),
        },
        now=now,
    )


async def run_apply_paid_invoices() -> int:
    """APScheduler entry point. Owns the DB session lifecycle."""
    with GetDB() as db:
        return _apply_paid_invoices_inner(db)


# ---------------------------------------------------------------------
# APScheduler installer
# ---------------------------------------------------------------------


def install_billing_scheduler(app: FastAPI) -> None:
    """Wire the billing scheduler jobs into the FastAPI app's lifespan.

    Three jobs:
    - ``aegis-billing-reap`` — A.5 reaper (awaiting_payment → expired)
    - ``aegis-billing-apply`` — A.5 applier (paid → applied + grant)
    - ``aegis-billing-trc20-poll`` — A.3 poller (Tronscan → paid)

    The TRC20 job is added unconditionally, but its body short-circuits
    when ``BILLING_TRC20_ENABLED`` is False. We do this rather than
    skipping ``add_job`` because env state is read at startup and
    flipping ``BILLING_TRC20_ENABLED`` at runtime (via
    ``_reload_for_tests``) wouldn't activate the job otherwise.

    Same shape as :func:`hardening.iplimit.scheduler.install_iplimit_scheduler`:
    we wrap the existing ``router.lifespan_context`` so upstream's
    custom lifespan keeps composing without a panel-wide refactor.

    Idempotent — second call is a no-op (panel-startup defence; in
    practice ``apply_panel_hardening`` calls this exactly once).
    """
    if getattr(app.state, "billing_scheduler_installed", False):
        return

    # Local import dodges a top-level cycle: trc20_poller imports the
    # client which transitively imports trc20_config which imports
    # providers/__init__.py which imports providers/trc20.py — all OK,
    # but keeping the heavy import here avoids paying the cost at
    # `import ops.billing.scheduler` for non-billing test paths.
    from ops.billing.trc20_config import BILLING_TRC20_POLL_INTERVAL
    from ops.billing.trc20_poller import run_poll_trc20_invoices

    original_lifespan = app.router.lifespan_context
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        run_reap_expired_invoices,
        "interval",
        seconds=BILLING_REAP_INTERVAL,
        coalesce=True,
        max_instances=1,
        id="aegis-billing-reap",
        replace_existing=True,
    )
    scheduler.add_job(
        run_apply_paid_invoices,
        "interval",
        seconds=BILLING_APPLY_INTERVAL,
        coalesce=True,
        max_instances=1,
        id="aegis-billing-apply",
        replace_existing=True,
    )
    scheduler.add_job(
        run_poll_trc20_invoices,
        "interval",
        seconds=BILLING_TRC20_POLL_INTERVAL,
        coalesce=True,
        max_instances=1,
        id="aegis-billing-trc20-poll",
        replace_existing=True,
    )

    @asynccontextmanager
    async def lifespan_with_billing(app_: FastAPI):
        async with original_lifespan(app_):
            scheduler.start()
            logger.info(
                "billing scheduler started "
                "reap_interval=%ss apply_interval=%ss "
                "trc20_poll_interval=%ss",
                BILLING_REAP_INTERVAL,
                BILLING_APPLY_INTERVAL,
                BILLING_TRC20_POLL_INTERVAL,
            )
            try:
                yield
            finally:
                scheduler.shutdown(wait=False)
                logger.info("billing scheduler stopped")

    app.router.lifespan_context = lifespan_with_billing
    app.state.billing_scheduler = scheduler
    app.state.billing_scheduler_installed = True


__all__ = [
    "BILLING_APPLY_INTERVAL",
    "BILLING_REAP_INTERVAL",
    "ApplierSkip",
    "apply_invoice_grant",
    "install_billing_scheduler",
    "run_apply_paid_invoices",
    "run_reap_expired_invoices",
]
