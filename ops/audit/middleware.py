"""FastAPI/Starlette middleware for automatic admin-operation auditing (S-AL).

Design contract
---------------
- Intercepts all **mutating** (POST / PATCH / PUT / DELETE) requests to
  ``/api/`` paths.
- Skips webhook callbacks (``/webhook/``), subscription paths (``/sub/``
  or ``/subscription``), and health-check paths.
- Extracts actor from the Bearer JWT in the ``Authorization`` header.
- Captures the **incoming request body** as ``before_state``
  (what the admin sent → "what was requested").
- Captures the **outgoing response body** as ``after_state``
  (what the server returned → "what changed").
- Both payloads are deep-redacted and Fernet-encrypted before storage.
- Writes the ``AuditEvent`` row **after** the response is ready so the
  handler is never blocked on audit I/O. If the write fails it is logged
  and silently dropped — it must NEVER propagate to the caller (AL.1.7).
- **Master kill-switch**: ``AUDIT_RETENTION_DAYS=0`` makes the middleware
  a complete noop — no CPU, no DB, no body buffering.
- Body capture is size-limited (``_MAX_BODY_BYTES``) to prevent memory
  pressure on large uploads; oversized bodies are marked "[BODY TOO LARGE]".

Middleware ordering (apply_panel_hardening):
  rate-limit → trusted-proxy → **audit** → router

The audit middleware sits after rate-limit so throttled requests still
produce a ``result=denied`` audit row, and before the router so all
upstream routes are covered.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from ops.audit.config import (
    AuditMisconfigured,
    audit_enabled,
    encrypt_state,
)
from ops.audit.db import (
    ACTOR_TYPE_ADMIN,
    ACTOR_TYPE_ANONYMOUS,
    ACTOR_TYPE_SUDO,
    RESULT_DENIED,
    RESULT_FAILURE,
    RESULT_SUCCESS,
    AuditEvent,
    _now_utc_naive,
)
from ops.audit.redact import deep_redact

logger = logging.getLogger(__name__)

# ── Tunables ──────────────────────────────────────────────────────────────

# Body bytes captured per request. 64 KB is generous for REST payloads;
# oversized bodies (file upload) are replaced with a sentinel string.
_MAX_BODY_BYTES = 64 * 1024  # 64 KB

# Paths whose URL contains any of these substrings are excluded from
# auditing even if they use a mutating method.
_EXCLUDE_PATH_RE = re.compile(
    r"/webhook/"  # external callbacks (EPay, TRC20, etc.)
    r"|/subscription"  # user subscription download
    r"|/health"  # health-check probes
    r"|/docs"  # Swagger UI
    r"|/openapi",  # OpenAPI spec
    re.IGNORECASE,
)

_MUTATING_METHODS = frozenset({"POST", "PATCH", "PUT", "DELETE"})


# ── Actor extraction ──────────────────────────────────────────────────────


def _extract_actor(
    request: Request,
) -> tuple[int | None, str, str | None]:
    """Return ``(actor_id, actor_type, actor_username)`` from the JWT.

    Deliberately tolerant: returns ``(None, "anonymous", None)`` on any
    JWT error so audit rows are still written for unauthenticated probes.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None, ACTOR_TYPE_ANONYMOUS, None

    token = auth_header[len("Bearer ") :]
    try:
        from app.utils.auth import get_admin_payload
        from app.db import GetDB, get_admin

        payload = get_admin_payload(token)
        if not payload:
            return None, ACTOR_TYPE_ANONYMOUS, None

        username: str = payload["username"]
        actor_type = ACTOR_TYPE_SUDO if payload.get("is_sudo") else ACTOR_TYPE_ADMIN

        # Resolve numeric ID from DB (best-effort; skip if DB is unreachable).
        actor_id: int | None = None
        try:
            with GetDB() as db:
                admin = get_admin(db, username)
                if admin:
                    actor_id = admin.id
        except Exception:  # pragma: no cover
            pass

        return actor_id, actor_type, username

    except Exception:  # pragma: no cover
        return None, ACTOR_TYPE_ANONYMOUS, None


# ── Body helpers ─────────────────────────────────────────────────────────


def _parse_json_body(raw: bytes) -> dict[str, Any] | None:
    """Try to parse *raw* as JSON. Returns ``None`` on failure."""
    if not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8", errors="replace"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def _result_from_status(status_code: int) -> str:
    if status_code in (401, 403):
        return RESULT_DENIED
    if status_code >= 400:
        return RESULT_FAILURE
    return RESULT_SUCCESS


# ── Audit writer ──────────────────────────────────────────────────────────


def _write_audit_event_sync(
    *,
    actor_id: int | None,
    actor_type: str,
    actor_username: str | None,
    action: str,
    method: str,
    path: str,
    before_body: dict[str, Any] | None,
    after_body: dict[str, Any] | None,
    status_code: int,
    result: str,
    error_message: str | None,
    ip: str,
    user_agent: str | None,
    request_id: str | None,
) -> None:
    """Synchronous DB write; called via ``run_in_executor`` from async context."""
    from app.db import GetDB

    try:
        before_enc = encrypt_state(deep_redact(before_body) if before_body else None)
        after_enc = encrypt_state(deep_redact(after_body) if after_body else None)
    except AuditMisconfigured:
        # Key missing despite check_audit_key_at_startup — log and skip.
        logger.error(
            "audit: AUDIT_SECRET_KEY missing; cannot encrypt state for %s %s",
            method,
            path,
        )
        return

    event = AuditEvent(
        actor_id=actor_id,
        actor_type=actor_type,
        actor_username=actor_username,
        action=action,
        method=method,
        path=path,
        before_state_encrypted=before_enc,
        after_state_encrypted=after_enc,
        result=result,
        status_code=status_code,
        error_message=error_message,
        ip=ip,
        user_agent=user_agent,
        request_id=request_id,
        ts=_now_utc_naive(),
    )

    with GetDB() as db:
        db.add(event)
        db.commit()


async def _write_audit_event_async(**kwargs: Any) -> None:
    """Non-blocking wrapper around ``_write_audit_event_sync``.

    Runs the sync DB call in a thread-pool executor so the event loop is
    not blocked. Any exception here is swallowed + logged — audit write
    failure must NEVER propagate to the HTTP caller (AL.1.7).
    """
    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: _write_audit_event_sync(**kwargs))
    except Exception:
        logger.exception(
            "audit: failed to write event for %s %s",
            kwargs.get("method"),
            kwargs.get("path"),
        )


# ── Middleware ────────────────────────────────────────────────────────────


class AuditMiddleware(BaseHTTPMiddleware):
    """Intercepts mutating admin requests and writes ``AuditEvent`` rows.

    Noop when ``AUDIT_RETENTION_DAYS == 0``.
    """

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        # Master kill-switch.
        if not audit_enabled():
            return await call_next(request)

        method = request.method.upper()

        # Only mutating methods are interesting.
        if method not in _MUTATING_METHODS:
            return await call_next(request)

        path = request.url.path

        # Skip non-API paths and explicitly excluded patterns.
        if not path.startswith("/api/") or _EXCLUDE_PATH_RE.search(path):
            return await call_next(request)

        # ── Before: capture request body ─────────────────────────────────
        try:
            raw_req = await request.body()
            if len(raw_req) > _MAX_BODY_BYTES:
                before_body: dict[str, Any] | None = {
                    "__audit__": "[BODY TOO LARGE]",
                    "size_bytes": len(raw_req),
                }
            else:
                before_body = _parse_json_body(raw_req)
        except Exception:
            before_body = None

        # ── Extract actor from JWT ────────────────────────────────────────
        actor_id, actor_type, actor_username = _extract_actor(request)

        # ── Call the actual handler ───────────────────────────────────────
        response = await call_next(request)
        status_code = response.status_code

        # ── After: capture response body (JSON only, size-limited) ───────
        after_body: dict[str, Any] | None = None
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                chunks: list[bytes] = []
                async for chunk in response.body_iterator:
                    chunks.append(chunk)
                    if sum(len(c) for c in chunks) > _MAX_BODY_BYTES:
                        chunks = []
                        after_body = {
                            "__audit__": "[BODY TOO LARGE]",
                            "status_code": status_code,
                        }
                        break
                else:
                    raw_resp = b"".join(chunks)
                    after_body = _parse_json_body(raw_resp)
                    chunks = [raw_resp]

                # Rebuild response so the body can still be read by the client.
                response = Response(
                    content=b"".join(chunks) if chunks else b"",
                    status_code=status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type,
                )
            except Exception:
                pass  # body capture failure is non-fatal

        # ── Derive route-template action (more stable than raw path) ──────
        route = request.scope.get("route")
        route_path = getattr(route, "path", path) if route else path
        action = f"{method}:{route_path}"

        # ── Derive result + error message ─────────────────────────────────
        result = _result_from_status(status_code)
        error_message: str | None = None
        if result != RESULT_SUCCESS and isinstance(after_body, dict):
            error_message = str(after_body.get("detail") or "")[:512] or None

        # ── Client IP ─────────────────────────────────────────────────────
        ip = ""
        if request.client:
            ip = request.client.host

        # ── Fire-and-forget async write ───────────────────────────────────
        asyncio.ensure_future(
            _write_audit_event_async(
                actor_id=actor_id,
                actor_type=actor_type,
                actor_username=actor_username,
                action=action,
                method=method,
                path=path,
                before_body=before_body,
                after_body=after_body,
                status_code=status_code,
                result=result,
                error_message=error_message,
                ip=ip,
                user_agent=request.headers.get("user-agent"),
                request_id=request.headers.get("x-request-id"),
            )
        )

        return response


__all__ = ["AuditMiddleware"]
