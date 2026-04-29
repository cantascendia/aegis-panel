"""APScheduler retention sweep for the audit log (S-AL AL.2).

One daily job runs at 03:00 UTC and hard-deletes ``AuditEvent`` rows older
than ``AUDIT_RETENTION_DAYS``.

Behaviour
---------
- ``AUDIT_RETENTION_DAYS == 0``: job registered but body is a no-op.
  This way toggling the env var at runtime via ``_reload_for_tests`` still
  picks up the change without restarting the scheduler.
- Soft deletes are intentionally NOT used — if an operator needs to wipe
  fast (D-003 legal scenario), ``TRUNCATE aegis_audit_events`` is the
  documented path (OPS-audit-log-runbook.md §1).
- ``coalesce=True`` + ``max_instances=1``: prevent pile-up on slow DB.
- Idempotent installer: repeated calls are no-ops (same contract as
  ``ops.billing.scheduler.install_billing_scheduler``).
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session

from app.db import GetDB
from ops.audit.config import AUDIT_RETENTION_DAYS
from ops.audit.db import AuditEvent

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger(__name__)

# Run once per day at 03:00 UTC — quiet hour, low query contention.
_SWEEP_HOUR_UTC = 3


def _sweep_old_events_inner(db: Session, *, now: datetime | None = None) -> int:
    """Delete rows older than ``AUDIT_RETENTION_DAYS``. Returns deleted count.

    Factored out for testing without APScheduler.
    """
    # Import here so tests can monkeypatch AUDIT_RETENTION_DAYS via
    # ``ops.audit.config._reload_for_tests`` and have it reflected.
    from ops.audit.config import AUDIT_RETENTION_DAYS as _days

    if _days <= 0:
        return 0

    now = now or datetime.now(UTC).replace(tzinfo=None)
    cutoff = now - timedelta(days=_days)

    deleted = (
        db.query(AuditEvent)
        .filter(AuditEvent.ts < cutoff)
        .delete(synchronize_session=False)
    )
    if deleted:
        db.commit()
        logger.info("audit retention sweep: deleted %d row(s) older than %s", deleted, cutoff.date())
    return deleted


async def run_audit_retention_sweep() -> int:
    """APScheduler entry point. Owns the DB session lifecycle."""
    with GetDB() as db:
        return _sweep_old_events_inner(db)


def install_audit_scheduler(app: "FastAPI") -> None:
    """Wire the retention sweep into the FastAPI app's lifespan.

    Same shape as ``ops.billing.scheduler.install_billing_scheduler`` —
    wraps the existing ``router.lifespan_context`` so upstream lifespan
    keeps composing without a panel-wide refactor.

    Idempotent: second call is a no-op.
    """
    if getattr(app.state, "audit_scheduler_installed", False):
        return

    original_lifespan = app.router.lifespan_context
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        run_audit_retention_sweep,
        "cron",
        hour=_SWEEP_HOUR_UTC,
        minute=0,
        coalesce=True,
        max_instances=1,
        id="aegis-audit-retention-sweep",
        replace_existing=True,
    )

    @asynccontextmanager
    async def lifespan_with_audit(app_: "FastAPI"):
        async with original_lifespan(app_):
            scheduler.start()
            logger.info(
                "audit retention scheduler started "
                "(daily sweep at %02d:00 UTC, retention=%d days)",
                _SWEEP_HOUR_UTC,
                AUDIT_RETENTION_DAYS,
            )
            try:
                yield
            finally:
                scheduler.shutdown(wait=False)
                logger.info("audit retention scheduler stopped")

    app.router.lifespan_context = lifespan_with_audit
    app.state.audit_scheduler = scheduler
    app.state.audit_scheduler_installed = True


__all__ = [
    "install_audit_scheduler",
    "run_audit_retention_sweep",
]
