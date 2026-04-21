"""
Admin-login rate limiter.

AUDIT.md section 4 finding P0-2: `/api/admins/token` has no protection
against distributed password brute force. One attacker script can
iterate a username list at wire speed.

Design
------
- Backend: slowapi -> `limits` -> Redis (`REDIS_URL`). In-process
  fallback in multi-worker deployments would silently let each
  worker's counter drift, defeating the point. So: Redis is a hard
  dependency when the feature is on.
- Key function: client IP (`get_remote_address`). Behind a reverse
  proxy this requires trusting `X-Forwarded-For`; documented in
  DEVELOPMENT.md.
- Disabled by default (`RATE_LIMIT_ENABLED=false`) so existing
  deployments aren't surprised by 429s on upgrade. Operators enable
  via `.env` after confirming Redis is reachable.
- The `Limiter` instance is always constructed (with `enabled=` set
  appropriately) so the `@limiter.limit(...)` decorator on route
  functions binds at import time without conditional branching.

Fail-loud
---------
If `RATE_LIMIT_ENABLED=true` but `REDIS_URL` is unset, importing this
module raises :class:`RateLimitMisconfigured`. Panel startup fails
early and noisily — silently running with broken rate limits is a
worse outcome than a clean refusal to start.
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config.env import (
    RATE_LIMIT_ADMIN_LOGIN,
    RATE_LIMIT_ENABLED,
    REDIS_URL,
)


class RateLimitMisconfigured(RuntimeError):
    """Raised at import time when rate limiting is enabled without Redis.

    Catching this and continuing would defeat the point: without a
    shared counter, every worker brute-forces in parallel and the
    attacker simply scales out.
    """


def _build_limiter() -> Limiter:
    if RATE_LIMIT_ENABLED and not REDIS_URL:
        raise RateLimitMisconfigured(
            "RATE_LIMIT_ENABLED=true requires REDIS_URL to be set. "
            "Rate limiting without a shared Redis counter is worse "
            "than no rate limiting — it creates a false sense of "
            "security while each worker counts independently. Either "
            "set REDIS_URL (and start Redis via `docker compose "
            "--profile redis up -d`), or set RATE_LIMIT_ENABLED=false."
        )

    # slowapi is built on top of `limits`. Storage URIs:
    #   redis://host:port/db  (production)
    #   memory://              (disabled mode placeholder — counters
    #                          that are never read because enabled=False)
    storage_uri = REDIS_URL if RATE_LIMIT_ENABLED else "memory://"

    return Limiter(
        key_func=get_remote_address,
        storage_uri=storage_uri,
        enabled=RATE_LIMIT_ENABLED,
        # `default_limits` would apply to *every* route. We only limit
        # what we explicitly decorate — route-level opt-in is easier
        # to audit than global deny-with-carve-outs.
        default_limits=[],
        # Fixed window is cheaper than moving window and good enough
        # for coarse login brute-force protection. Switch to
        # "moving-window" later if the UX of boundary-effect retries
        # becomes a complaint.
        strategy="fixed-window",
    )


# Module-level singleton. Decorators on routes bind to this at import
# time, so it must exist even when rate limiting is disabled.
limiter = _build_limiter()


# Re-exported so callers that only need the *label* (not the Limiter
# object) can import one symbol instead of two.
ADMIN_LOGIN_LIMIT: str = RATE_LIMIT_ADMIN_LOGIN
