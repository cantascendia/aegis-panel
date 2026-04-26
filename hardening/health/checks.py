"""Per-subsystem health probes.

Each probe is a small async function returning a :class:`SubsystemHealth`.
Callers (the endpoint) gather them concurrently and aggregate.

Design rules
------------
- **Probes are read-only**. No DB writes, no state mutation. Re-running
  them under load shouldn't surprise anyone.
- **Probes are bounded-time**. We wrap each in a small timeout so a
  single slow subsystem (e.g. WHOIS hung) cannot block the whole
  health response. The endpoint's outer ``asyncio.wait_for`` is the
  ultimate cap; per-probe timeouts let the user see *which* subsystem
  is slow instead of getting a single 504.
- **Probes don't raise** — they catch exceptions internally and report
  ``status="down"`` with the exception class as the message. The
  endpoint must always be able to render *some* report; raising would
  defeat the purpose of a health probe.
- **Probes use the same data sources as the runtime**. We do not
  re-implement DB connectivity in a "test" path — we use the same
  ``GetDB()`` the rest of the panel uses. Otherwise a probe could
  pass while the real subsystem is down.

The probes intentionally cover only **self-developed subsystems** here.
Upstream Marzneshin probably has its own health checks (or will); we
don't try to second-guess them.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from hardening.health.models import SubsystemHealth

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger(__name__)

# Per-probe wall-time cap. WHOIS / DNS subsystem can hang indefinitely
# under bad network conditions; we'd rather report "timed out" than
# block the operator's monitoring tick.
_PROBE_TIMEOUT_SECONDS = 5.0


async def probe_db() -> SubsystemHealth:
    """SELECT 1 on the panel DB. Verifies the connection pool is alive.

    Reports "down" if anything raises (connection refused, auth fail,
    DB-level error). Reports "ok" otherwise — a 1ms query is the only
    thing this probe can be confident about.
    """
    try:
        from sqlalchemy import text

        from app.db import GetDB

        async def _check() -> None:
            with GetDB() as db:
                db.execute(text("SELECT 1")).scalar()

        await asyncio.wait_for(_check(), timeout=_PROBE_TIMEOUT_SECONDS)
        return SubsystemHealth(
            name="db",
            status="ok",
            message="SELECT 1 succeeded",
        )
    except TimeoutError:
        return SubsystemHealth(
            name="db",
            status="down",
            message=f"SELECT 1 exceeded {_PROBE_TIMEOUT_SECONDS}s",
        )
    except Exception as exc:  # noqa: BLE001 — health probe must not raise
        logger.warning("db health probe failed: %s", exc)
        return SubsystemHealth(
            name="db",
            status="down",
            message=f"{type(exc).__name__}: {exc}",
        )


def probe_billing_scheduler(app: FastAPI) -> SubsystemHealth:
    """Verify the billing scheduler installed itself + jobs registered.

    Sync because we just inspect ``app.state``. Sentinel attributes set
    by ``ops.billing.scheduler.install_billing_scheduler``; absence
    means the lifespan wrap never ran (panel boot failed silently or
    apply_panel_hardening was bypassed).
    """
    if not getattr(app.state, "billing_scheduler_installed", False):
        return SubsystemHealth(
            name="billing_scheduler",
            status="down",
            message="install_billing_scheduler did not run",
        )
    scheduler = getattr(app.state, "billing_scheduler", None)
    if scheduler is None:
        return SubsystemHealth(
            name="billing_scheduler",
            status="down",
            message="app.state.billing_scheduler is None",
        )
    job_ids = sorted(j.id for j in scheduler.get_jobs())
    expected = {
        "aegis-billing-reap",
        "aegis-billing-apply",
        "aegis-billing-trc20-poll",
    }
    missing = expected - set(job_ids)
    if missing:
        return SubsystemHealth(
            name="billing_scheduler",
            status="degraded",
            message=f"jobs missing: {sorted(missing)}",
            details={"jobs": job_ids},
        )
    return SubsystemHealth(
        name="billing_scheduler",
        status="ok",
        message=f"{len(job_ids)} jobs registered",
        details={"jobs": job_ids},
    )


def probe_trc20() -> SubsystemHealth:
    """Verify TRC20 provider is configured (or explicitly disabled).

    Three possible states:
    - ``ENABLED=false`` (default) → "ok" with note "disabled by env"
    - ``ENABLED=true`` + valid config → "ok" with receive address summary
    - ``ENABLED=true`` + missing required env → "down" with the
      specific missing variable name surfaced
    """
    try:
        from ops.billing.trc20_config import (
            BILLING_TRC20_ENABLED,
            BILLING_TRC20_RECEIVE_ADDRESS,
            Trc20Misconfigured,
            get_trc20_provider,
        )

        if not BILLING_TRC20_ENABLED:
            return SubsystemHealth(
                name="trc20",
                status="ok",
                message="disabled by BILLING_TRC20_ENABLED",
                details={"enabled": False},
            )
        try:
            get_trc20_provider()
        except Trc20Misconfigured as exc:
            return SubsystemHealth(
                name="trc20",
                status="down",
                message=str(exc),
                details={"enabled": True, "configured": False},
            )
        # Mask the address so logs/metrics don't leak the full receive
        # address (it's public on chain, but adding "via this panel" is
        # one more pivot for an attacker building a target list).
        masked = (
            BILLING_TRC20_RECEIVE_ADDRESS[:6]
            + "…"
            + BILLING_TRC20_RECEIVE_ADDRESS[-4:]
        )
        return SubsystemHealth(
            name="trc20",
            status="ok",
            message="provider configured and ready",
            details={"enabled": True, "configured": True, "address": masked},
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("trc20 health probe failed: %s", exc)
        return SubsystemHealth(
            name="trc20",
            status="down",
            message=f"{type(exc).__name__}: {exc}",
        )


def probe_iplimit_scheduler(app: FastAPI) -> SubsystemHealth:
    """Verify the IP limiter scheduler installed.

    Sentinel + scheduler shape match the same pattern as
    :func:`probe_billing_scheduler`.
    """
    if not getattr(app.state, "iplimit_scheduler_installed", False):
        return SubsystemHealth(
            name="iplimit_scheduler",
            status="down",
            message="install_iplimit_scheduler did not run",
        )
    scheduler = getattr(app.state, "iplimit_scheduler", None)
    if scheduler is None:
        return SubsystemHealth(
            name="iplimit_scheduler",
            status="down",
            message="app.state.iplimit_scheduler is None",
        )
    job_ids = sorted(j.id for j in scheduler.get_jobs())
    if "aegis-iplimit-poll" not in job_ids:
        return SubsystemHealth(
            name="iplimit_scheduler",
            status="degraded",
            message="poll job not registered",
            details={"jobs": job_ids},
        )
    return SubsystemHealth(
        name="iplimit_scheduler",
        status="ok",
        message=f"{len(job_ids)} jobs registered",
        details={"jobs": job_ids},
    )


def probe_reality_seeds() -> SubsystemHealth:
    """Verify Reality audit seeds load without error.

    A panel where ``hardening/reality/seeds/top1k.json`` got truncated
    or lost would surface as audit reports with all targets scoring
    incorrectly. This probe catches the corruption at deploy time.
    """
    try:
        from hardening.reality.checks.sni_coldness import _load_rank_index

        rank_index = _load_rank_index()
        return SubsystemHealth(
            name="reality_seeds",
            status="ok",
            message=f"{len(rank_index)} top1k entries loaded",
            details={"count": len(rank_index)},
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("reality seeds health probe failed: %s", exc)
        return SubsystemHealth(
            name="reality_seeds",
            status="down",
            message=f"{type(exc).__name__}: {exc}",
        )


def probe_sni_seeds() -> SubsystemHealth:
    """Verify SNI selector seeds + blacklist load."""
    try:
        from hardening.sni.loaders import load_seeds

        seeds = load_seeds("auto")
        if not seeds:
            return SubsystemHealth(
                name="sni_seeds",
                status="degraded",
                message="seeds loaded but list is empty",
            )
        return SubsystemHealth(
            name="sni_seeds",
            status="ok",
            message=f"{len(seeds)} candidates loaded",
            details={"count": len(seeds)},
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("sni seeds health probe failed: %s", exc)
        return SubsystemHealth(
            name="sni_seeds",
            status="down",
            message=f"{type(exc).__name__}: {exc}",
        )


__all__ = [
    "probe_billing_scheduler",
    "probe_db",
    "probe_iplimit_scheduler",
    "probe_reality_seeds",
    "probe_sni_seeds",
    "probe_trc20",
]
