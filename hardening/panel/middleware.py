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

# SlowAPIMiddleware imported but currently NOT mounted — see add_middleware
# block below for the FastAPI scope-incompatibility rationale (L-034).
# Kept around so re-enabling is a one-line change once slowapi ships pure
# ASGI middleware.
from slowapi.middleware import SlowAPIMiddleware  # noqa: F401
from starlette.staticfiles import StaticFiles as _StaticFiles

from app.routes.customer import router as customer_router
from hardening.health.endpoint import router as health_router
from hardening.iplimit.endpoint import router as iplimit_router
from hardening.iplimit.scheduler import install_iplimit_scheduler
from hardening.panel.rate_limit import limiter
from hardening.reality.endpoint import router as reality_router
from hardening.sni.endpoint import router as sni_router
from ops.audit.config import validate_startup as validate_audit_startup
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


class _SPAStaticFiles(_StaticFiles):
    """StaticFiles subclass that falls back to index.html on 404.

    Required for the customer-portal SPA at /portal/ — without this,
    typing `https://nilou.cc/portal/login` (a route name the SPA
    handles client-side) returns 404 from Starlette because no
    `dist/login` file exists. Returning index.html lets React boot
    and the in-page router resolve the path.

    Why subclass instead of a separate catch-all route: app.mount()
    swallows all sub-paths, so adding an exception_handler or
    @app.get("/portal/{path:path}") doesn't intercept them. Overriding
    `get_response` is the only hook that runs for already-mounted
    sub-paths.

    The fallback ONLY fires on 404 (not 403, not 500), and ONLY for
    GET-shaped lookups (StaticFiles only serves GET/HEAD anyway).
    Asset 404s (e.g. `/portal/missing-image.png`) will incorrectly
    return index.html — acceptable trade-off because the alternative
    requires hand-rolling routing + lookup, and the user-visible
    impact of a broken image asset is the same either way (image
    fails to render). All real assets ship at `/portal/assets/*` and
    `/portal/static/*` per Vite's base config; misses there are bugs.
    """

    async def get_response(self, path: str, scope):
        # Only fall back for the SPA shell itself, not for assets/.
        from starlette.exceptions import HTTPException as _HTTPEx

        try:
            return await super().get_response(path, scope)
        except _HTTPEx as exc:
            if exc.status_code != 404:
                raise
            # Don't paper over genuine missing assets — only fall back
            # for routes that *look* like SPA paths (no file extension).
            if "." in path.rsplit("/", 1)[-1]:
                raise
            return await super().get_response("index.html", scope)


def _mount_customer_portal(app: FastAPI) -> None:
    """Mount customer-portal SPA at /portal/ + redirect / → /portal/.

    Fork-only (D-018, wave-11 P1 PR #240). Vite base in
    customer-portal/vite.config.js is `/portal/`, so the build outputs
    asset paths like `/portal/static/...` — they only resolve when
    panel mounts `customer-portal/dist` under `/portal`.

    Requires CI to have run `pnpm build` before docker build (see
    .github/workflows/package.yml). Dist is absent in dev (DEBUG mode)
    so we guard with isdir() and silently skip.

    Root redirect: registered BEFORE upstream `@app.get("/")` in
    marzneshin.py because apply_panel_hardening() fires first; first-
    registered route wins in Starlette routing, so the upstream
    3D-scene `home_page()` becomes unreachable. Dashboard is still
    accessible at the randomized `DASHBOARD_PATH`.

    SPA fallback: uses `_SPAStaticFiles` so unknown paths under
    /portal/ (e.g. /portal/login from the hash router) serve
    index.html and the in-page router resolves them.
    """
    import os

    from starlette.responses import RedirectResponse

    if not os.path.isdir("customer-portal/dist"):
        return

    @app.get("/", include_in_schema=False)
    def _root_to_portal() -> RedirectResponse:
        return RedirectResponse(url="/portal/", status_code=307)

    app.mount(
        "/portal",
        _SPAStaticFiles(directory="customer-portal/dist", html=True),
        name="customer-portal",
    )


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
    # SlowAPIMiddleware deliberately NOT mounted (L-034): it extends
    # starlette.BaseHTTPMiddleware which is incompatible with FastAPI 0.115+
    # dependency injection — `fastapi_inner_astack` is dropped from request
    # scope, breaking any route that uses Depends() with an async context
    # manager (e.g. GET /api/users → 500). Decorated routes
    # (`@limiter.limit(...)`) do NOT need this middleware to function — the
    # decorator inspects request directly and applies limits per-route.
    # Application-wide rate limiting (every request) is intentionally
    # deferred until slowapi rewrites as pure ASGI middleware OR we replace
    # with a different limiter (e.g. starlette-limiter).
    # app.add_middleware(SlowAPIMiddleware)
    # AuditMiddleware (AL.2c.2 MVP — anonymous baseline). Mount AFTER
    # SlowAPI so rate-limit rejections are captured in the audit row
    # (status=429 → result=failure). See SPEC §How.2 ordering:
    # rate-limit → trusted-proxy → audit → router.
    #
    # AuditMiddleware (rewritten to pure ASGI in wave-6 PR #170 / L-034
    # closure): always mount. The pure-ASGI form does NOT corrupt
    # request scope, so FastAPI's DI works regardless of audit state.
    # When AUDIT_RETENTION_DAYS=0 the middleware is a thin no-op (early
    # return after request_id injection), so the perf cost is one
    # function call per request — negligible.
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
    # Customer-side endpoints (Track B, .claude/rules/forbidden-paths.md):
    # /api/customers/sub-login, /me. JWT scoped access="customer" so these
    # tokens cannot pass admin auth and admin tokens cannot pass these.
    app.include_router(customer_router)
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

    _mount_customer_portal(app)
