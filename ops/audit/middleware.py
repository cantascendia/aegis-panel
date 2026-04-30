"""FastAPI middleware that writes audit rows for admin mutate actions.

S-AL Phase 2c.2/2c.3 — middleware with **JWT-based actor decode**:

- ``path`` / ``method`` / ``action``(=route name)
- HTTP status code → ``result`` (success / failure / denied)
- ``actor_id`` (None — no DB query) / ``actor_username`` /
  ``actor_type`` from JWT ``sub`` and ``access`` claims (AL.2c.3)
- ``ip`` (D-012 trusted-proxy gated) / ``user_agent`` /
  ``request_id`` / ``ts``
- ``error_message`` for ``status_code >= 400``

Why **JWT decode, not DB lookup**:

The token is the source of truth that the request's ``sudo_admin``
dependency would itself trust — pyjwt verification covers the
"actor is who they claim" guarantee. Going to the DB to resolve
``actor_id`` doubles the cost of every audit-eligible request and
adds a third place admin-rename history can drift.
``actor_username`` is the SEALED snapshot field (PR #125) that
makes admin renames non-destructive to the audit trail; pairing
it with the JWT ``access`` claim (``"admin"`` or ``"sudo"``) gives
us the actor_type without a join.

Failure modes for actor decode:
- No ``Authorization`` header → anonymous (pre-auth failures, e.g.
  failed login attempts; SEALED schema explicitly contemplates this).
- Malformed / expired / invalid-signature token → anonymous (pyjwt's
  ``InvalidTokenError`` is swallowed in ``get_admin_payload``;
  caller gets ``None``).
- Valid token without ``access ∈ {"admin", "sudo"}`` → anonymous
  (defensive against future token shapes; today the validator in
  ``app.utils.auth.get_admin_payload`` rejects these).

Deliberately **not** here:

- ``before_state`` / ``after_state`` — requires per-route SELECT
  hooks; lands in **AL.2c.4**.
- ``target_type`` / ``target_id`` — depends on per-route metadata
  (path-param parsing); lands in AL.2c.4.
- ``actor_id`` (DB-resolved) — opportunistic enhancement; the
  JWT-only path is sufficient for the current forensic workflow
  (operators search by username, not numeric id).

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

import ipaddress
import logging
import re as _re
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from decouple import config as decouple_config
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.db import GetDB
from app.utils.auth import get_admin_payload
from ops.audit.config import is_audit_enabled
from ops.audit.db import (
    ACTOR_TYPE_ADMIN,
    ACTOR_TYPE_ANONYMOUS,
    ACTOR_TYPE_SUDO,
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

# Path patterns (regex) that get audited. Curated rather than "all
# admin" to keep the first deployment scope predictable (see module
# docstring). Append-only: new fork-owned admin routers get added
# here, never silently expand via broader wildcards.
#
# Why regex over prefix-match (codex review P2 on commit 6a3afdb):
# the IP-limit router is mounted at ``/api/users`` and exposes
# ``PATCH /api/users/{username}/iplimit/override`` —
# a literal-prefix list ``/api/iplimit`` MISSES it. We keep the list
# precise (one regex per fork-owned mutate surface) so future router
# moves trigger an explicit edit, not a silent miss.

_AUDIT_PATH_PATTERNS: tuple[_re.Pattern[str], ...] = (
    # SNI dashboard
    _re.compile(r"^/api/nodes/sni-suggest(?:/|$)"),
    # IP-limit policy admin (mounted on user object — codex P2 fix)
    _re.compile(r"^/api/users/[^/]+/iplimit(?:/|$)"),
    # Billing admin (plans, channels, invoices) + checkout
    _re.compile(r"^/api/billing/admin(?:/|$)"),
    _re.compile(r"^/api/billing/cart(?:/|$)"),
    # Reality config audit (admin trigger)
    _re.compile(r"^/api/reality/audit(?:/|$)"),
    # Health extended (sudo-only diagnostic)
    _re.compile(r"^/api/aegis/health/extended(?:/|$)"),
)


def _should_audit(method: str, path: str) -> bool:
    """True iff this request matches the audit scope.

    Pure-function for unit testing: no IO, no global state. Test
    cases simply construct ``(method, path)`` tuples and assert.
    """
    if method.upper() not in _MUTATING_METHODS:
        return False
    return any(pattern.match(path) for pattern in _AUDIT_PATH_PATTERNS)


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

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        # Inject a request id eagerly so downstream loggers / handlers
        # can correlate even if audit ends up not writing a row.
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        request.state.audit_request_id = request_id

        # Always run the handler — audit is observational, never gating.
        try:
            response: Response = await call_next(request)
        except Exception:
            # The handler raised. Re-raise unconditionally; only WRITE
            # an audit row if the request would have been audited on
            # success — opt-out + scope rules apply equally to the
            # exception path (codex review P2 on commit 6a3afdb:
            # without this guard, RETENTION=0 deployments still
            # persisted rows for failing requests, and out-of-scope
            # paths got logged on exception).
            if is_audit_enabled() and _should_audit(
                request.method, request.url.path
            ):
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
        request: Request,
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
            actor_type, actor_username = _resolve_actor(request)
            row = AuditEvent(
                # ``actor_id`` stays None — JWT-only path; resolving the
                # numeric id needs a DB lookup the audit-write critical
                # path can't afford. Operators search by username.
                actor_id=None,
                actor_type=actor_type,
                actor_username=actor_username,
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


def _action_from_request(request: Request) -> str:
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


def _resolve_ip(request: Request) -> str:
    """Client IP resolution with D-012 trusted-proxy gate.

    Decision logic (mirrors ``ops.billing.checkout_endpoint``):

    1. If ``request.client`` is None (broken ASGI server) → ``"unknown"``.
    2. If transport peer is in ``AUDIT_TRUSTED_PROXIES`` AND
       ``X-Forwarded-For`` is set → return XFF leftmost token (the
       real client). This is the panel-behind-Nginx / panel-behind-CF
       case.
    3. Otherwise → return transport peer (the safe default;
       attacker can spoof XFF only if our env trusts their peer,
       which is the operator's choice).

    Per-feature env (D-012) — does NOT reuse ``BILLING_TRUSTED_PROXIES``.
    Operators may set them to the same value, but cross-feature
    coupling here would be a sneaky source of "I changed billing
    config and now audit IPs are wrong" incidents.
    """
    if request.client is None:
        return "unknown"
    peer = request.client.host
    xff = request.headers.get("x-forwarded-for")
    if xff and _peer_is_trusted_proxy(peer):
        # Leftmost XFF token is the original client per RFC 7239.
        # Strip whitespace, cap to ipv6-max-len.
        first = xff.split(",", 1)[0].strip()
        if first:
            return first[:45]
    return peer[:45]


# ---------------------------------------------------------------------
# AUDIT_TRUSTED_PROXIES env (D-012 per-feature pattern)
# ---------------------------------------------------------------------


def _parse_trusted_proxies(
    raw: str,
) -> tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]:
    """Parse comma-separated CIDR list. Bad entries are dropped with a
    warning rather than crashing boot — same shape as
    ``ops.billing.config._parse_trusted_proxies``.
    """
    if not raw:
        return ()
    parsed: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        try:
            parsed.append(ipaddress.ip_network(entry, strict=False))
        except ValueError:
            logger.warning(
                "AUDIT_TRUSTED_PROXIES dropped invalid CIDR %r", entry
            )
    return tuple(parsed)


_AUDIT_TRUSTED_PROXIES: tuple[
    ipaddress.IPv4Network | ipaddress.IPv6Network, ...
] = _parse_trusted_proxies(
    decouple_config("AUDIT_TRUSTED_PROXIES", default="")
)


def _peer_is_trusted_proxy(peer_ip: str) -> bool:
    """True iff ``peer_ip`` falls within ``AUDIT_TRUSTED_PROXIES``."""
    if not _AUDIT_TRUSTED_PROXIES:
        return False
    try:
        peer = ipaddress.ip_address(peer_ip)
    except ValueError:
        return False
    return any(peer in cidr for cidr in _AUDIT_TRUSTED_PROXIES)


def _reload_trusted_proxies_for_tests() -> None:
    """Test hook — re-read AUDIT_TRUSTED_PROXIES env. Production
    code MUST NOT call this. Mirrors the billing reload pattern."""
    global _AUDIT_TRUSTED_PROXIES
    _AUDIT_TRUSTED_PROXIES = _parse_trusted_proxies(
        decouple_config("AUDIT_TRUSTED_PROXIES", default="")
    )


# ---------------------------------------------------------------------
# Actor extraction (AL.2c.3 — JWT decode, no DB lookup)
# ---------------------------------------------------------------------


def _resolve_actor(request: Request) -> tuple[str, str | None]:
    """Decode the bearer token and return ``(actor_type, actor_username)``.

    - No ``Authorization`` header / not Bearer → ``(ANONYMOUS, None)``
    - Malformed / expired / invalid-signature → ``(ANONYMOUS, None)``
      (``get_admin_payload`` swallows ``InvalidTokenError`` and
      returns ``None``).
    - Valid admin token → ``("admin", username)``
    - Valid sudo token → ``("sudo_admin", username)``

    Pure function: no DB, no IO, no global state — fast enough to
    run on every audit-eligible request without a perf budget hit.
    """
    auth = request.headers.get("authorization")
    if not auth:
        return ACTOR_TYPE_ANONYMOUS, None
    parts = auth.split(maxsplit=1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return ACTOR_TYPE_ANONYMOUS, None
    payload = get_admin_payload(parts[1])
    if not payload:
        return ACTOR_TYPE_ANONYMOUS, None
    actor_type = (
        ACTOR_TYPE_SUDO if payload.get("is_sudo") else ACTOR_TYPE_ADMIN
    )
    return actor_type, payload.get("username")
