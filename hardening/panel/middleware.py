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

from hardening.panel.rate_limit import limiter
from hardening.sni.endpoint import router as sni_router

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

    # Self-owned routers. Order matters only if prefixes overlap with
    # upstream — they don't (upstream ``app/routes/node.py`` mounts
    # under ``/nodes``; ours is ``/api/nodes/sni-suggest``).
    app.include_router(sni_router)
