"""FastAPI middleware that writes audit rows for admin mutate actions.

S-AL Phase 2c.2 — MVP middleware. Captures the **anonymous-baseline**
audit signal:

- ``path`` / ``method`` / ``action``(=route name)
- HTTP status code → ``result`` (success / failure / denied)
- ``ip`` / ``user_agent`` / ``request_id`` / ``ts``
- ``error_message`` for ``status_code >= 400``

Deliberately **not** in this MVP:

- ``actor_id`` / ``actor_username`` — extracting these from the
  request requires JWT decode + DB lookup, which:
  1. Bloats middleware import surface (would touch
     ``app/utils/jwt.py`` which is in the upstream sync zone).
  2. Doubles the auth work the FastAPI ``Depends(get_current_admin)``
     dependency already does for every admin route.
  Lands in **AL.2c.3** as a follow-up PR with a thin
  ``request.state.audit_actor`` setter dependency added to the four
  upstream admin routers.
- ``before_state`` / ``after_state`` — requires per-route SELECT
  hooks; lands in **AL.2c.4**.
- ``target_type`` / ``target_id`` — depends on per-route metadata
  (path-param parsing); lands in AL.2c.4.

90% of the forensic value comes from the anonymous baseline — a
"who-did-what-when" question can be answered by joining IP+UA+ts
to the access log and looking up the active session at that moment,
which is the exact same workflow operators already use for the
upstream rate-limit log. The SEALED ``actor_id: int | None`` schema
(PR #125) explicitly contemplates this case (``NULL = anonymous,
e.g. failed pre-auth login``).

## Path matching

Middleware fires on every request but writes a row only when:

1. Method is mutate: ``POST`` / ``PATCH`` / ``PUT`` / ``DELETE``
   (read-only endpoints inflate the table 100× with low signal).
2. Path matches a self-owned audit-scope. We **prefix-match**
   on a curated allowlist instead of "every admin path" so:
   - The list lives in one place (this module) — easy to grep.
   - The first audit deployment doesn't drown in events from
     unrelated upstream routes the moment middleware lands.
   - Future scope expansion is one tuple edit + a new test.

The MVP allowlist is the union of fork-owned admin routers from
``hardening/panel/middleware.py``; upstream admin paths
(``/api/admins``, ``/api/users``) are NOT yet audited — that's
AL.3 scope (separate audit policy decision per route family).

## Failure handling (L-018 invariant)

Audit middleware **never** blocks the business handler. If the DB
write fails (disk full, connection lost, schema drift), the
exception is logged and swallowed. The handler's response goes
back to the client unchanged. The cost: a brief audit gap
during the DB outage. The benefit: panel stays up. This is the
SEALED contract from L-018 (LESSONS).

## Cross-references

- SPEC: ``docs/ai-cto/SPEC-audit-log.md`` §How.2
- D-018 SEALED — TBDs all closed
- Pattern source: standard Starlette ``BaseHTTPMiddleware``
- Companion: ``ops.audit.crypto`` (encrypt empty payloads)
- Companion: ``ops.audit.config.is_audit_enabled``
- Future: AL.2c.3 (actor decode) → AL.2c.4 (state diff)
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.db import GetDB
from ops.audit.config import is_audit_enabled
from ops.audit.db import (
    ACTOR_TYPE_ANONYMOUS,
    RESULT_DENIED,
    RESULT_FAILURE,
    RESULT_SUCCESS,
    AuditEvent,
)

if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.responses import Response

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# Path / method filters
# ---------------------------------------------------------------------

_MUTATING_METHODS = frozenset({"POST", "PATCH", "PUT", "DELETE"})

# Path prefixes that get audited. Curated rather than "all admin" to
# keep the first deployment scope predictable (see module docstring).
# Append-only: new fork-owned admin routers get added here, never
# silently expand via wildcards.
_AUDIT_PATH_PREFIXES: tuple[str, ...] = (
    # SNI dashboard
    "/api/nodes/sni-suggest",
    # IP-limit policy admin
    "/api/iplimit",
    # Billing admin (plans, channels, invoices) + checkout
    "/api/billing/admin",
    "/api/billing/cart",
    # Reality config audit (admin trigger)
    "/api/reality/audit",
    # Health extended (sudo-only diagnostic)
    "/api/aegis/health/extended",
)


def _should_audit(method: str, path: str) -> bool:
    """True iff this request matches the audit scope.

    Pure-function for unit testing: no IO, no global state. Test
    cases simply construct ``(method, path)`` tuples and assert.
    """
    if method.upper() not in _MUTATING_METHODS:
        return False
    return any(path.startswith(prefix) for prefix in _AUDIT_PATH_PREFIXES)


# ---------------------------------------------------------------------
# Result classification
# ---------------------------------------------------------------------


def _classify_result(status_code: int) -> str:
    """Map HTTP status into the SEALED audit-result vocabulary
    (``ops.audit.db`` constants).

    - 1xx/2xx → success (request handled as intended)
    - 401/403 → denied (auth/authz rejection — distinct signal
      because operators care about "someone tried to act past
      their permission" separately from generic failures)
    - other 4xx/5xx → failure
    """
    if 200 <= status_code < 300:
        return RESULT_SUCCESS
    if status_code in (401, 403):
        return RESULT_DENIED
    return RESULT_FAILURE


# ---------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------


def _now_utc_naive() -> datetime:
    """Local helper to avoid the import-time circle that would arise
    if we re-used ``ops.audit.db._now_utc_naive`` (the model module
    already imports several heavy deps for ``Mapped`` / ``mapped_column``;
    keeping the middleware's ``ts`` helper local makes import order
    insensitive to package-init evaluation order)."""
    return datetime.now(UTC).replace(tzinfo=None)


class AuditMiddleware(BaseHTTPMiddleware):
    """ASGI middleware that records mutate actions to ``aegis_audit_events``.

    See module docstring for the MVP scope and the deliberate
    ``actor_id == None`` baseline.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: "Request", call_next):  # type: ignore[override]
        # Inject a request id eagerly so downstream loggers / handlers
        # can correlate even if audit ends up not writing a row.
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        request.state.audit_request_id = request_id

        # Always run the handler — audit is observational, never gating.
        try:
            response: Response = await call_next(request)
        except Exception:
            # The handler raised. Re-raise after attempting an audit
            # row with status_code=500 + the exception class name as
            # error_message (we don't include the message body — could
            # contain sensitive payload echo). Audit failure here is
            # double-failure tolerant: caught below in _try_write.
            self._try_write(
                request=request,
                request_id=request_id,
                status_code=500,
                error_message="UnhandledException",
            )
            raise

        if not is_audit_enabled():
            # Opt-out path (D-018 TBD-1): retention=0 → no rows.
            return response

        if not _should_audit(request.method, request.url.path):
            return response

        self._try_write(
            request=request,
            request_id=request_id,
            status_code=response.status_code,
            error_message=None,
        )
        return response

    def _try_write(
        self,
        *,
        request: "Request",
        request_id: str,
        status_code: int,
        error_message: str | None,
    ) -> None:
        """Best-effort row insertion. Never raises (L-018 invariant).

        Split out from ``dispatch`` so both the success path and the
        500-from-handler path go through the same "audit must not
        block" guarantee.
        """
        try:
            row = AuditEvent(
                actor_id=None,
                actor_type=ACTOR_TYPE_ANONYMOUS,
                actor_username=None,
                action=_action_from_request(request),
                method=request.method.upper(),
                path=request.url.path[:512],
                target_type=None,
                target_id=None,
                before_state_encrypted=None,
                after_state_encrypted=None,
                result=_classify_result(status_code),
                status_code=status_code,
                error_message=error_message[:512] if error_message else None,
                ip=_resolve_ip(request),
                user_agent=(request.headers.get("user-agent") or "")[:512]
                or None,
                request_id=request_id,
                ts=_now_utc_naive(),
            )
            with GetDB() as session:
                session.add(row)
                session.commit()
        except Exception:
            # Audit must never break the response. Exception is logged
            # at WARNING (not ERROR) so an existing audit-DB outage
            # doesn't drown the panel logs in noise; the operator
            # learns from monitoring the row-count, not from log spam.
            logger.warning(
                "audit row write failed (path=%s method=%s status=%s)",
                request.url.path,
                request.method,
                status_code,
                exc_info=True,
            )


# ---------------------------------------------------------------------
# Helpers (module-level so unit tests can target them in isolation)
# ---------------------------------------------------------------------


def _action_from_request(request: "Request") -> str:
    """Resolve the audit ``action`` field.

    Prefer Starlette's resolved route name (``request.scope["route"].name``)
    — that's a stable identifier set by the framework. Fall back to
    ``method:path`` if the route hasn't been resolved (which happens
    on 404s and on routes without an explicit ``name=``).
    """
    route = request.scope.get("route")
    name = getattr(route, "name", None) if route is not None else None
    if name:
        return name[:128]
    return f"{request.method.upper()}:{request.url.path}"[:128]


def _resolve_ip(request: "Request") -> str:
    """Best-effort client IP resolution.

    MVP: returns ``request.client.host`` directly. **No trusted-proxy
    gate yet** — that lands in AL.2c.3 alongside actor decode (both
    need ``AUDIT_TRUSTED_PROXIES`` env var per the per-feature D-012
    pattern from billing/iplimit). Until AL.2c.3 ships, behind a
    proxy the audit row records the proxy's IP, not the real client
    — operators should treat the field as "first-hop" rather than
    "true client" until D-012 wiring lands.
    """
    if request.client is None:
        return "unknown"
    return request.client.host[:45]
