"""FastAPI router for health checks.

Two endpoints:

- ``GET /api/aegis/health`` (public) — minimal liveness. Used by
  reverse proxy / load balancer / Kubernetes-style probes. Returns
  a fixed JSON ``{"status": "ok"}`` and HTTP 200.
- ``GET /api/aegis/health/extended`` (sudo-admin) — per-subsystem
  detail. Used by operator monitoring (Prometheus, Telegram alerts,
  manual checks). Returns the :class:`HealthReport` schema.

Path prefix ``/api/aegis`` keeps us off the unprefixed ``/api/health``
slot — upstream Marzneshin or any caller-provided WSGI/ASGI mount may
already serve a health endpoint there. Segregating to ``/api/aegis/*``
preserves the project's "upstream 冲突面 = 一行" invariant.

Same architectural decisions as ``hardening/sni/endpoint.py`` and
``hardening/reality/endpoint.py``:

- **No slowapi decorator**: the public endpoint is a constant string
  return so DoS exposure is bounded by FastAPI's own request handling
  (no DB call, no compute). The extended endpoint is sudo-admin gated.
- **Lives under hardening/** rather than ``app/routes/*`` to keep the
  one-line ``include_router`` invariant in
  ``hardening/panel/middleware.py``.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from fastapi import APIRouter, Request

from app.dependencies import SudoAdminDep
from hardening.health.checks import (
    probe_billing_scheduler,
    probe_db,
    probe_iplimit_scheduler,
    probe_reality_seeds,
    probe_sni_seeds,
    probe_trc20,
)
from hardening.health.models import HealthReport, aggregate_status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/aegis", tags=["Health"])

# Captured at module load for the uptime calculation. Not perfectly
# the FastAPI lifespan-start time, but close enough — within a few
# seconds of the panel boot, which is precision the operator cares
# about.
_PROCESS_START_MONOTONIC = time.monotonic()


def _panel_version() -> str:
    """Read the deployed panel version. Falls back to 'unknown' if the
    upstream package metadata moves under us — health endpoint must
    never raise."""
    try:
        from app import __version__

        return __version__
    except Exception:  # noqa: BLE001
        return "unknown"


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe. Public. Always 200 + ``{"status": "ok"}``.

    Why so minimal:
    - **No DB call**: load balancers hit liveness probes every few
      seconds; a DB call would multiply DB load by N proxies.
    - **No subsystem detail**: leaking ``"trc20: configured"`` to an
      anonymous caller is recon-level information about the panel's
      operator decisions. The extended endpoint covers that, behind
      sudo-admin auth.
    - **No version**: same recon argument; admin who needs the version
      sees it on ``/health/extended``.
    """
    return {"status": "ok"}


@router.get("/health/extended", response_model=None)
async def health_extended(
    request: Request,
    admin: SudoAdminDep,  # noqa: ARG001 — auth gate
) -> dict[str, Any]:
    """Sudo-admin gated. Returns per-subsystem :class:`HealthReport`.

    Probes are run concurrently — total response time is
    ``max(probe_times)``, not the sum. With per-probe 5s caps, the
    worst case is ~5s; the typical case is sub-second.

    The report's top-level ``status`` is the worst-of across
    subsystems, so operators can alert on a single field.
    """
    app = request.app

    async def _scheduler_probe(name: str, fn) -> Any:
        # The scheduler probes are sync (pure ``app.state`` reads); wrap
        # in to_thread so they don't block. Cheap.
        return await asyncio.to_thread(fn, app)

    async def _sync_probe(fn) -> Any:
        return await asyncio.to_thread(fn)

    results = await asyncio.gather(
        probe_db(),
        _scheduler_probe("billing", probe_billing_scheduler),
        _scheduler_probe("iplimit", probe_iplimit_scheduler),
        _sync_probe(probe_trc20),
        _sync_probe(probe_reality_seeds),
        _sync_probe(probe_sni_seeds),
    )
    # Stable ordering for client diff-friendliness — operators piping
    # this through `jq` shouldn't see fields jiggling between calls.
    results.sort(key=lambda s: s.name)

    uptime = max(0, int(time.monotonic() - _PROCESS_START_MONOTONIC))
    report = HealthReport(
        status=aggregate_status(results),
        version=_panel_version(),
        uptime_seconds=uptime,
        subsystems=list(results),
    )
    return report.to_dict()


__all__ = ["router"]
