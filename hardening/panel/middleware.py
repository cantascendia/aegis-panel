"""
Glue layer — install hardening middleware / handlers / routes on the
FastAPI app.

Exposing a single function (`apply_panel_hardening`) keeps the diff
against upstream `app/marzneshin.py` to one line. Everything else
lives here and never collides with upstream merges.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from hardening.health.endpoint import router as health_router
from hardening.iplimit.endpoint import router as iplimit_router
from hardening.iplimit.scheduler import install_iplimit_scheduler
from hardening.panel.rate_limit import limiter
from hardening.reality.endpoint import router as reality_router
from hardening.sni.endpoint import router as sni_router
from ops.audit.config import (
    is_audit_enabled,
    validate_startup as validate_audit_startup,
)
from ops.audit.endpoint import router as audit_router
from ops.audit.middleware import AuditMiddleware
from ops.audit.scheduler import install_audit_scheduler
from ops.billing.checkout_endpoint import (
    checkout_router as billing_checkout_router,
)
from ops.billing.endpoint import router as billing_admin_router
from ops.billing.scheduler import install_billing_scheduler

if TYPE_CHECKING:
    from fastapi import FastAPI


def apply_panel_hardening(app: FastAPI) -> None:
    """Install rate limiting + self-owned routes on `app`.

    Idempotent-ish: calling twice would register the exception
    handler twice, which is harmless but wasteful. In practice this
    is invoked exactly once from the app factory.

    What this wires up today:
    - Attaches the shared `limiter` to `app.state.limiter` — slowapi
      decorators look it up there at request time.
    - Registers the 429 handler so RateLimitExceeded surfaces as a
      clean JSON response with Retry-After.
    - Adds SlowAPIMiddleware so the limiter actually runs on every
      request (not only decorated routes — the middleware is what
      hooks into the request lifecycle).
    - Includes self-owned routers that don't belong in upstream
      ``app/routes/*``. Currently: ``hardening/sni/endpoint.py``
      (``POST /api/nodes/sni-suggest``). This keeps upstream-sync
      diffs on ``app/routes/*`` at zero.

    What it deliberately does not do:
    - Touch CORS, JWT, or any other middleware owned by upstream.
      If we ever need ordering control vs upstream middleware, we
      negotiate that here rather than editing `app/marzneshin.py`.
    """
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    # AuditMiddleware (AL.2c.2 MVP — anonymous baseline). Mount AFTER
    # SlowAPI so rate-limit rejections are captured in the audit row
    # (status=429 → result=failure). See SPEC §How.2 ordering:
    # rate-limit → trusted-proxy → audit → router.
    #
    # 2026-05-01 production cutover (L-034): AuditMiddleware extends
    # starlette.BaseHTTPMiddleware, which is incompatible with FastAPI
    # 0.115+ dependency injection — it drops `fastapi_inner_astack`
    # from request scope, triggering AssertionError on any route that
    # uses Depends() with an async context manager (e.g. GET /api/users
    # → 500 "fastapi_inner_astack not found in request scope"). Only
    # attaching when audit is actually enabled keeps the panel
    # functional in retention=0 deployments. v0.4 rewrites this as a
    # pure-ASGI middleware (callable taking scope/receive/send) which
    # does not corrupt request scope.
    if is_audit_enabled():
        app.add_middleware(AuditMiddleware)

    # Self-owned routers. Order matters only if prefixes overlap with
    # upstream — they don't (upstream ``app/routes/node.py`` mounts
    # under ``/nodes``; ours is ``/api/nodes/sni-suggest``).
    app.include_router(sni_router)
    app.include_router(iplimit_router)
    app.include_router(billing_admin_router)
    app.include_router(billing_checkout_router)
    app.include_router(reality_router)
    app.include_router(health_router)
    app.include_router(audit_router)
    install_iplimit_scheduler(app)
    install_billing_scheduler(app)
    # Audit log (S-AL Phase 4 retention sweep). validate_startup runs
    # FIRST so panel boot fails loudly if AUDIT_RETENTION_DAYS > 0
    # but AUDIT_SECRET_KEY is missing/malformed (D-018 contract);
    # only after validate_startup does install_audit_scheduler add
    # the daily 03:00 UTC sweep job. AuditMiddleware (AL.2c.2) wires
    # in this same block in a future PR.
    validate_audit_startup()
    install_audit_scheduler(app)
