"""APScheduler integration for audit-log retention sweep (AL.4).

One periodic job runs inside the panel process (matches the
``ops.billing.scheduler`` / ``hardening.iplimit.scheduler`` pattern):

- ``run_audit_retention_sweep`` — hard-deletes rows older than
  ``AUDIT_RETENTION_DAYS`` days. Cron schedule 03:00 UTC daily
  (per SPEC §How.4 — off-peak so the bulk DELETE doesn't compete
  with admin requests).

## Why retention is daily-cron, not interval

The reaper and applier in ``ops.billing.scheduler`` use ``interval``
because they need to react to user-driven state changes within
seconds. Audit retention is the opposite: there's nothing time-
critical about "delete a row that's now 91 days old" — running it
once a day is fine, off-peak is preferable, and a cron schedule
avoids 24×60 wakeups that all do nothing in a typical shop.

## Why hard delete, not soft delete

Soft delete (a ``deleted_at`` column) defeats the point of
retention. The legal-tension scenario in D-003 is "operator can
prove audit data is gone" — a soft-delete row is, to a forensics
investigator, still recoverable. Hard delete = ``DELETE FROM`` =
the row is overwritten as the page is reused, which is the closest
RDBMS equivalent to "destroyed".

For the very-paranoid operator,
``OPS-audit-log-runbook.md`` (lands in AL.4 final PR) documents the
``VACUUM FULL`` follow-up that physically reclaims the storage.

## Idempotence

The DELETE statement is naturally idempotent: re-running it deletes
nothing (rows from the first pass are already gone). Two scheduler
instances racing (impossible with ``coalesce=True`` + ``max_instances=1``,
but defence-in-depth) would each delete a partition of "rows older
than threshold" — the union is the same. No transaction lock needed.

## Opt-out path (D-018 TBD-1 SEALED)

When ``AUDIT_RETENTION_DAYS=0`` (audit disabled entirely):
- ``is_audit_enabled()`` returns False
- The job body short-circuits before issuing any SQL
- No DELETE runs (defensive: there are no rows to begin with)

This keeps the same cron registered in all configs, so flipping
``AUDIT_RETENTION_DAYS`` from 0→90 doesn't require a panel restart.

## Cross-references

- SPEC: ``docs/ai-cto/SPEC-audit-log.md`` §How.4 (retention sweep)
- D-018 TBD-1 SEALED — opt-out via env, no dashboard wipe button
- Pattern source: ``ops/billing/scheduler.py`` (A.5 reaper / applier)
- Lifespan wiring: ``apply_panel_hardening`` in AL.2c final PR
  (not here — keeps this PR's blast radius small).
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import TYPE_CHECKING

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.db import GetDB
from ops.audit.config import is_audit_enabled, retention_days
from ops.audit.db import AuditEvent, _now_utc_naive

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# Sweep job
# ---------------------------------------------------------------------


def audit_retention_sweep(session: Session) -> int:
    """DELETE rows older than ``AUDIT_RETENTION_DAYS`` days.

    Returns the number of rows deleted (for logging / tests). Tests
    pass a session; production code goes through
    ``run_audit_retention_sweep`` which manages ``GetDB``.

    Short-circuits to 0 when audit is disabled (``RETENTION_DAYS=0``);
    the schedule still fires but does nothing — see module docstring
    for why this is preferable to conditionally registering the job.
    """
    if not is_audit_enabled():
        return 0
    days = retention_days()
    cutoff = _now_utc_naive() - timedelta(days=days)
    result = session.execute(delete(AuditEvent).where(AuditEvent.ts < cutoff))
    session.commit()
    deleted = result.rowcount or 0
    if deleted:
        logger.info(
            "audit retention sweep deleted %d rows "
            "(cutoff=%s, retention=%dd)",
            deleted,
            cutoff.isoformat(),
            days,
        )
    return deleted


async def run_audit_retention_sweep() -> None:
    """APScheduler entry point — manages its own DB session.

    Async-def required by ``AsyncIOScheduler`` even though the
    underlying SQLAlchemy operations are sync (matches the
    ``ops.billing.scheduler`` async-with-sync-body pattern).

    Failures don't crash the scheduler — caught + logged so the next
    daily fire still runs. A persistent failure (DB unreachable for
    days) surfaces in startup logs / monitoring without taking the
    panel down. Audit being briefly out-of-retention is a far less
    bad outcome than panel-wide downtime.
    """
    try:
        with GetDB() as session:
            audit_retention_sweep(session)
    except Exception:
        logger.exception("audit retention sweep failed")


# ---------------------------------------------------------------------
# Lifespan wiring
# ---------------------------------------------------------------------


def install_audit_scheduler(app: FastAPI) -> None:
    """Wire the audit retention sweep into the FastAPI app's lifespan.

    One job: ``aegis-audit-retention-sweep`` — daily at 03:00 UTC.

    Same shape as ``ops.billing.scheduler.install_billing_scheduler``
    and ``hardening.iplimit.scheduler.install_iplimit_scheduler``: we
    wrap ``router.lifespan_context`` so upstream's custom lifespan
    keeps composing without a panel-wide refactor.

    Idempotent — second call is a no-op (matches the
    ``apply_panel_hardening`` "called once but defend anyway"
    contract). Tests and AL.2c integration both call this; the
    state flag prevents double-registration.

    NOTE: This function is NOT yet called from
    ``app/marzneshin.py``. The lifespan hook lands in the AL.2c
    middleware-wiring PR alongside ``AuditMiddleware`` registration —
    keeping THIS PR's blast radius to one new module + one test
    file. Until AL.2c lands, the sweep does not run; behaviour is
    "audit rows accumulate per retention setting but never get
    swept" which is benign at <2k rows / day.
    """
    if getattr(app.state, "audit_scheduler_installed", False):
        return

    original_lifespan = app.router.lifespan_context
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        run_audit_retention_sweep,
        "cron",
        hour=3,
        minute=0,
        coalesce=True,
        max_instances=1,
        id="aegis-audit-retention-sweep",
        replace_existing=True,
    )

    @asynccontextmanager
    async def lifespan_with_audit(app_: FastAPI):
        async with original_lifespan(app_):
            scheduler.start()
            logger.info(
                "audit scheduler started "
                "(retention=%dd, cron=03:00 UTC daily)",
                retention_days(),
            )
            try:
                yield
            finally:
                scheduler.shutdown(wait=False)

    app.router.lifespan_context = lifespan_with_audit
    app.state.audit_scheduler_installed = True
