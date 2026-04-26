"""Aegis health endpoint — public liveness + sudo-admin subsystem detail.

Provides two endpoints, registered via ``apply_panel_hardening``:

- ``GET /api/aegis/health`` — public, lightweight, returns
  ``{"status": "ok"}`` for reverse-proxy / load-balancer liveness
  probes. **No DB call**, no subsystem status — just "the FastAPI
  process is up". This is the only safe public health endpoint;
  anything more would either leak panel state (recon vector) or be
  DoS-able from the public internet.

- ``GET /api/aegis/health/extended`` — sudo-admin gated, returns
  per-subsystem health: DB connectivity, billing scheduler installed,
  TRC20 enabled+configured, iplimit registered, reality seeds load,
  panel version + uptime. Used by operator monitoring (Prometheus
  scrape via authenticated token, Telegram alerts via cron).

Path prefix is ``/api/aegis`` (not ``/api`` plain) to keep upstream
冲突面 = 一行: upstream may add its own ``/api/health`` later, our
namespace is segregated under ``/api/aegis/*`` and won't collide.
"""

from __future__ import annotations

from hardening.health.endpoint import router

__all__ = ["router"]
