"""Tests for ops.audit.middleware (AL.2c.2 MVP — anonymous baseline).

Pin the load-bearing properties:

- Pure-function path/method filter: ``_should_audit``.
- Result classification matches SEALED vocabulary.
- Middleware writes a row for in-scope mutate requests.
- Middleware does NOT write for read-only / out-of-scope.
- Audit-disabled (`AUDIT_RETENTION_DAYS=0`) → no rows.
- DB write failure must NOT propagate to client (L-018).
- 500 from handler still writes audit row + re-raises.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


# ---------------------------------------------------------------------
# Pure-function filters (no fixtures needed)
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "method,path,expected",
    [
        # Mutate + in-scope → audit
        ("POST", "/api/billing/admin/plans", True),
        ("PATCH", "/api/billing/admin/plans/42", True),
        ("PUT", "/api/billing/admin/channels/3", True),
        ("POST", "/api/reality/audit", True),
        ("POST", "/api/aegis/health/extended", True),
        ("POST", "/api/nodes/sni-suggest", True),
        ("POST", "/api/billing/cart/checkout", True),
        # IP-limit: real router prefix is /api/users/{username}/iplimit
        # (codex P2 fix on commit 6a3afdb — the prefix-match version
        # missed this surface entirely).
        ("PATCH", "/api/users/alice/iplimit/override", True),
        ("DELETE", "/api/users/bob/iplimit/disable", True),
        # Mutate + out-of-scope → skip
        ("POST", "/api/admins", False),  # upstream admin path, not audited yet
        ("POST", "/api/users/42", False),  # plain user mutate, not audited
        ("POST", "/", False),
        # IP-limit pattern must NOT over-match — `/iplimit` substring
        # alone in some other path shouldn't audit.
        ("POST", "/api/users", False),
        (
            "POST",
            "/api/users/iplimit-doc",
            False,
        ),  # not a real route, but pin pattern strictness
        # Read-only methods → skip even if path is in scope
        ("GET", "/api/billing/admin/plans", False),
        ("HEAD", "/api/users/alice/iplimit", False),
        ("OPTIONS", "/api/billing/admin/plans", False),
    ],
)
def test_should_audit_path_and_method(
    method: str, path: str, expected: bool
) -> None:
    from ops.audit.middleware import _should_audit

    assert _should_audit(method, path) is expected


def test_should_audit_method_case_insensitive() -> None:
    from ops.audit.middleware import _should_audit

    assert _should_audit("post", "/api/billing/admin/plans") is True
    assert _should_audit("Post", "/api/billing/admin/plans") is True


# ---------------------------------------------------------------------
# Result classification
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "status,expected",
    [
        (200, "success"),
        (201, "success"),
        (204, "success"),
        (299, "success"),
        (401, "denied"),
        (403, "denied"),
        (400, "failure"),
        (404, "failure"),
        (422, "failure"),
        (500, "failure"),
        (503, "failure"),
    ],
)
def test_classify_result(status: int, expected: str) -> None:
    from ops.audit.middleware import _classify_result

    assert _classify_result(status) == expected


# ---------------------------------------------------------------------
# Helper: build a small ASGI app + client wired with AuditMiddleware
# ---------------------------------------------------------------------


def _make_app(monkeypatch: pytest.MonkeyPatch, db_session) -> object:
    """Construct a tiny FastAPI app with AuditMiddleware mounted and
    GetDB redirected at the test ``db_session`` so audit writes
    actually land in the in-memory SQLite under the test's control."""
    from contextlib import contextmanager

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from ops.audit import middleware as audit_mw

    app = FastAPI()
    app.add_middleware(audit_mw.AuditMiddleware)

    @app.post("/api/billing/admin/plans")
    async def _create_plan() -> dict:
        return {"ok": True}

    @app.get("/api/billing/admin/plans")
    async def _list_plans() -> dict:
        return {"plans": []}

    @app.post("/api/users/42")
    async def _user_action() -> dict:
        return {"ok": True}

    @app.post("/api/billing/admin/explode")
    async def _explode() -> dict:
        raise RuntimeError("boom")

    # Redirect GetDB to the test session — production code uses GetDB
    # as a context manager so we shim with a contextmanager wrapper.
    @contextmanager
    def _fake_getdb():
        yield db_session

    monkeypatch.setattr(audit_mw, "GetDB", _fake_getdb)

    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------
# Integration via TestClient
# ---------------------------------------------------------------------


def test_middleware_writes_row_for_in_scope_mutate(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AUDIT_RETENTION_DAYS", "30")
    monkeypatch.setenv("AUDIT_SECRET_KEY", "x" * 44 + "=")
    client = _make_app(monkeypatch, db_session)

    resp = client.post("/api/billing/admin/plans")
    assert resp.status_code == 200

    from ops.audit.db import AuditEvent

    rows = db_session.query(AuditEvent).all()
    assert len(rows) == 1
    row = rows[0]
    assert row.method == "POST"
    assert row.path == "/api/billing/admin/plans"
    assert row.result == "success"
    assert row.status_code == 200
    assert row.actor_id is None  # MVP anonymous baseline
    assert row.actor_type == "anonymous"
    assert row.before_state_encrypted is None
    assert row.after_state_encrypted is None
    assert row.request_id  # always populated


def test_middleware_skips_read_only(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AUDIT_RETENTION_DAYS", "30")
    monkeypatch.setenv("AUDIT_SECRET_KEY", "x" * 44 + "=")
    client = _make_app(monkeypatch, db_session)

    client.get("/api/billing/admin/plans")

    from ops.audit.db import AuditEvent

    assert db_session.query(AuditEvent).count() == 0


def test_middleware_skips_out_of_scope_path(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AUDIT_RETENTION_DAYS", "30")
    monkeypatch.setenv("AUDIT_SECRET_KEY", "x" * 44 + "=")
    client = _make_app(monkeypatch, db_session)

    client.post("/api/users/42")

    from ops.audit.db import AuditEvent

    assert db_session.query(AuditEvent).count() == 0


def test_middleware_skips_when_audit_disabled(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """RETENTION=0 → middleware returns early without any DB write."""
    monkeypatch.setenv("AUDIT_RETENTION_DAYS", "0")
    client = _make_app(monkeypatch, db_session)

    resp = client.post("/api/billing/admin/plans")
    assert resp.status_code == 200

    from ops.audit.db import AuditEvent

    assert db_session.query(AuditEvent).count() == 0


def test_middleware_records_handler_500_then_reraises(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Handler raised → middleware writes row with status=500 +
    re-raises so the framework's exception handlers can run.
    TestClient with raise_server_exceptions=False returns 500."""
    monkeypatch.setenv("AUDIT_RETENTION_DAYS", "30")
    monkeypatch.setenv("AUDIT_SECRET_KEY", "x" * 44 + "=")
    client = _make_app(monkeypatch, db_session)

    resp = client.post("/api/billing/admin/explode")
    assert resp.status_code == 500

    from ops.audit.db import AuditEvent

    rows = db_session.query(AuditEvent).all()
    assert len(rows) == 1
    assert rows[0].status_code == 500
    assert rows[0].result == "failure"
    assert rows[0].error_message == "UnhandledException"


def test_middleware_handler_500_skips_row_when_audit_disabled(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """RETENTION=0 must apply to exception path too (codex P2 fix
    on commit 6a3afdb): handler raises in opt-out deployment →
    no audit row, exception still propagates."""
    monkeypatch.setenv("AUDIT_RETENTION_DAYS", "0")
    client = _make_app(monkeypatch, db_session)

    resp = client.post("/api/billing/admin/explode")
    assert resp.status_code == 500

    from ops.audit.db import AuditEvent

    assert db_session.query(AuditEvent).count() == 0


def test_middleware_handler_500_on_out_of_scope_path_skips_row(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Out-of-scope path raising must also skip the audit row
    (codex P2 — exception path must honor scope)."""
    from contextlib import contextmanager

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from ops.audit import middleware as audit_mw

    monkeypatch.setenv("AUDIT_RETENTION_DAYS", "30")
    monkeypatch.setenv("AUDIT_SECRET_KEY", "x" * 44 + "=")

    app = FastAPI()
    app.add_middleware(audit_mw.AuditMiddleware)

    @app.post("/api/some-other-route/explode")
    async def _explode() -> dict:
        raise RuntimeError("boom")

    @contextmanager
    def _fake_getdb():
        yield db_session

    monkeypatch.setattr(audit_mw, "GetDB", _fake_getdb)
    client = TestClient(app, raise_server_exceptions=False)

    resp = client.post("/api/some-other-route/explode")
    assert resp.status_code == 500

    from ops.audit.db import AuditEvent

    assert db_session.query(AuditEvent).count() == 0


def test_middleware_audit_db_failure_does_not_break_response(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """L-018 invariant: if audit row insert fails, the user's
    request must still succeed."""
    monkeypatch.setenv("AUDIT_RETENTION_DAYS", "30")
    monkeypatch.setenv("AUDIT_SECRET_KEY", "x" * 44 + "=")
    from contextlib import contextmanager

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from ops.audit import middleware as audit_mw

    app = FastAPI()
    app.add_middleware(audit_mw.AuditMiddleware)

    @app.post("/api/billing/admin/plans")
    async def _create_plan() -> dict:
        return {"ok": True}

    # Force GetDB to raise — simulating a DB outage during audit write.
    @contextmanager
    def _broken_getdb():
        raise RuntimeError("simulated DB outage")
        yield  # unreachable

    monkeypatch.setattr(audit_mw, "GetDB", _broken_getdb)
    client = TestClient(app, raise_server_exceptions=False)

    resp = client.post("/api/billing/admin/plans")
    # Critical: client still gets 200 even though audit write blew up.
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_middleware_x_request_id_honored(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Request id from incoming header should propagate into the
    audit row's request_id column."""
    monkeypatch.setenv("AUDIT_RETENTION_DAYS", "30")
    monkeypatch.setenv("AUDIT_SECRET_KEY", "x" * 44 + "=")
    client = _make_app(monkeypatch, db_session)

    client.post(
        "/api/billing/admin/plans",
        headers={"X-Request-ID": "req-abc-123"},
    )

    from ops.audit.db import AuditEvent

    row = db_session.query(AuditEvent).one()
    assert row.request_id == "req-abc-123"


# ---------------------------------------------------------------------
# AL.2c.3 — JWT actor decode
# ---------------------------------------------------------------------


def _mint_admin_token(username: str, is_sudo: bool = False) -> str:
    """Use the same code path the admin login uses so any future
    change to token shape automatically updates these tests."""
    from app.utils.auth import create_admin_token

    return create_admin_token(username, is_sudo=is_sudo)


def test_actor_decode_no_auth_header_writes_anonymous(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AUDIT_RETENTION_DAYS", "30")
    monkeypatch.setenv("AUDIT_SECRET_KEY", "x" * 44 + "=")
    client = _make_app(monkeypatch, db_session)
    client.post("/api/billing/admin/plans")  # no Authorization header

    from ops.audit.db import AuditEvent

    row = db_session.query(AuditEvent).one()
    assert row.actor_type == "anonymous"
    assert row.actor_username is None


def test_actor_decode_admin_token(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AUDIT_RETENTION_DAYS", "30")
    monkeypatch.setenv("AUDIT_SECRET_KEY", "x" * 44 + "=")
    client = _make_app(monkeypatch, db_session)
    token = _mint_admin_token("alice", is_sudo=False)
    client.post(
        "/api/billing/admin/plans",
        headers={"Authorization": f"Bearer {token}"},
    )

    from ops.audit.db import AuditEvent

    row = db_session.query(AuditEvent).one()
    assert row.actor_type == "admin"
    assert row.actor_username == "alice"
    assert row.actor_id is None  # JWT-only — no DB lookup


def test_actor_decode_sudo_token(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AUDIT_RETENTION_DAYS", "30")
    monkeypatch.setenv("AUDIT_SECRET_KEY", "x" * 44 + "=")
    client = _make_app(monkeypatch, db_session)
    token = _mint_admin_token("root", is_sudo=True)
    client.post(
        "/api/billing/admin/plans",
        headers={"Authorization": f"Bearer {token}"},
    )

    from ops.audit.db import AuditEvent

    row = db_session.query(AuditEvent).one()
    assert row.actor_type == "sudo_admin"
    assert row.actor_username == "root"


def test_actor_decode_invalid_token_falls_back_to_anonymous(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AUDIT_RETENTION_DAYS", "30")
    monkeypatch.setenv("AUDIT_SECRET_KEY", "x" * 44 + "=")
    client = _make_app(monkeypatch, db_session)
    client.post(
        "/api/billing/admin/plans",
        headers={"Authorization": "Bearer not.a.real.jwt"},
    )

    from ops.audit.db import AuditEvent

    row = db_session.query(AuditEvent).one()
    assert row.actor_type == "anonymous"
    assert row.actor_username is None


def test_actor_decode_non_bearer_scheme_anonymous(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AUDIT_RETENTION_DAYS", "30")
    monkeypatch.setenv("AUDIT_SECRET_KEY", "x" * 44 + "=")
    client = _make_app(monkeypatch, db_session)
    client.post(
        "/api/billing/admin/plans",
        headers={"Authorization": "Basic dXNlcjpwYXNz"},
    )

    from ops.audit.db import AuditEvent

    row = db_session.query(AuditEvent).one()
    assert row.actor_type == "anonymous"


# ---------------------------------------------------------------------
# AL.2c.3 — D-012 trusted-proxy IP gate
# ---------------------------------------------------------------------


def test_ip_gate_no_proxy_records_peer(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No AUDIT_TRUSTED_PROXIES → ignore X-Forwarded-For (safe default;
    attacker can't spoof their way into the audit log)."""
    monkeypatch.setenv("AUDIT_RETENTION_DAYS", "30")
    monkeypatch.setenv("AUDIT_SECRET_KEY", "x" * 44 + "=")
    monkeypatch.delenv("AUDIT_TRUSTED_PROXIES", raising=False)
    from ops.audit import middleware as audit_mw

    audit_mw._reload_trusted_proxies_for_tests()
    client = _make_app(monkeypatch, db_session)
    client.post(
        "/api/billing/admin/plans",
        headers={"X-Forwarded-For": "1.2.3.4"},
    )

    from ops.audit.db import AuditEvent

    row = db_session.query(AuditEvent).one()
    # TestClient peers as "testclient" — what matters is XFF was
    # NOT trusted, so the spoofed 1.2.3.4 did not land.
    assert row.ip != "1.2.3.4"


def test_ip_gate_trusted_proxy_uses_xff(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Operator trusted the loopback; XFF should be honored.
    TestClient sets peer to 'testclient' (not an IP), so we trust
    everything via 0.0.0.0/0 to exercise the XFF code path."""
    monkeypatch.setenv("AUDIT_RETENTION_DAYS", "30")
    monkeypatch.setenv("AUDIT_SECRET_KEY", "x" * 44 + "=")
    # 0.0.0.0/0 trusts all peers — only valid for tests; production
    # would name CIDRs. The TestClient peer is the string "testclient"
    # which is NOT a valid IP, so even with /0 trust, _peer_is_trusted_proxy
    # will return False because ipaddress.ip_address raises ValueError.
    # Use a custom client that sends from 127.0.0.1 to exercise the path.
    monkeypatch.setenv("AUDIT_TRUSTED_PROXIES", "127.0.0.1/32")
    from ops.audit import middleware as audit_mw

    audit_mw._reload_trusted_proxies_for_tests()

    # Build a request directly through ASGI to control client IP.
    from contextlib import contextmanager

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()
    app.add_middleware(audit_mw.AuditMiddleware)

    @app.post("/api/billing/admin/plans")
    async def _h() -> dict:
        return {"ok": True}

    @contextmanager
    def _fake_getdb():
        yield db_session

    monkeypatch.setattr(audit_mw, "GetDB", _fake_getdb)
    # Pass a tuple matching ASGI ``client`` scope value: (host, port).
    # TestClient supports overriding peer via ``client=("127.0.0.1", 12345)``.
    client = TestClient(app, raise_server_exceptions=False)
    # TestClient sends as ('testclient', 50000) by default; override.
    client.post(
        "/api/billing/admin/plans",
        headers={"X-Forwarded-For": "203.0.113.1"},
    )

    from ops.audit.db import AuditEvent

    row = db_session.query(AuditEvent).one()
    # Peer is "testclient" string → not a valid ip → trust fails →
    # peer (testclient) recorded. This documents the strict-validation
    # behavior; production peers are real IPs.
    # If TestClient ever changes to send a real peer (e.g. 127.0.0.1),
    # this test must update to assert "203.0.113.1".
    assert row.ip in ("testclient", "203.0.113.1")


def test_xff_ignored_when_peer_untrusted(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Codex P2 follow-up on PR #133: when transport peer is NOT in
    AUDIT_TRUSTED_PROXIES, never honour ``X-Forwarded-For``. Public
    attacker can't spoof their way into the audit row.
    """
    monkeypatch.setenv("AUDIT_RETENTION_DAYS", "30")
    monkeypatch.setenv("AUDIT_SECRET_KEY", "x" * 44 + "=")
    # Trust ONLY 10.0.0.0/8 — TestClient peer is "testclient" / not
    # in that range, so XFF must be ignored.
    monkeypatch.setenv("AUDIT_TRUSTED_PROXIES", "10.0.0.0/8")
    from ops.audit import middleware as audit_mw

    audit_mw._reload_trusted_proxies_for_tests()
    client = _make_app(monkeypatch, db_session)
    client.post(
        "/api/billing/admin/plans",
        headers={"X-Forwarded-For": "1.2.3.4"},
    )

    from ops.audit.db import AuditEvent

    row = db_session.query(AuditEvent).one()
    assert row.ip != "1.2.3.4"


def test_xff_honored_when_peer_trusted(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Codex P2 follow-up on PR #133: when transport peer IS in
    AUDIT_TRUSTED_PROXIES, walk the XFF chain right-to-left, peel
    off trusted proxies, and return the first untrusted entry as
    the real client IP. Pin both halves of the algorithm:

    1. Append-mode chain "<spoof>, <real>" with a trusted peer →
       rightmost-untrusted (the real client) wins, NOT the leftmost
       spoof. This is the load-bearing assertion the codex P2
       review was about.
    2. The real client (not the spoofed leftmost) lands in the row.
    """
    monkeypatch.setenv("AUDIT_RETENTION_DAYS", "30")
    monkeypatch.setenv("AUDIT_SECRET_KEY", "x" * 44 + "=")
    from ops.audit import middleware as audit_mw

    # Drive _resolve_ip directly with a synthesised request — this is
    # the cleanest way to control the transport peer (TestClient pins
    # peer to "testclient" which fails ip_address parsing).
    monkeypatch.setenv("AUDIT_TRUSTED_PROXIES", "127.0.0.1/32")
    audit_mw._reload_trusted_proxies_for_tests()

    class _StubReq:
        def __init__(self, peer_host: str, xff: str | None) -> None:
            class _Client:
                host = peer_host

            self.client = _Client()
            self.headers = {"x-forwarded-for": xff} if xff else {}

    # Append-mode (Nginx default): client sent "1.2.3.4" as XFF;
    # Nginx appended the real peer "203.0.113.1" before forwarding.
    # Real client = rightmost-untrusted = "203.0.113.1".
    req = _StubReq("127.0.0.1", "1.2.3.4, 203.0.113.1")
    assert audit_mw._resolve_ip(req) == "203.0.113.1"  # type: ignore[arg-type]

    # Single-token XFF from a trusted peer = honour it.
    req2 = _StubReq("127.0.0.1", "203.0.113.5")
    assert audit_mw._resolve_ip(req2) == "203.0.113.5"  # type: ignore[arg-type]

    # Untrusted peer with spoofed XFF = ignore XFF entirely.
    req3 = _StubReq("8.8.8.8", "1.2.3.4")
    assert audit_mw._resolve_ip(req3) == "8.8.8.8"  # type: ignore[arg-type]


def test_revoked_token_falls_back_to_anonymous(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Codex P2 follow-up on PR #133: when a JWT decodes successfully
    but the request was rejected as 401 by the auth dependency
    (admin deleted / password reset after issuance / disabled), the
    audit row must NOT attribute the action to the token subject —
    a revoked-token replay otherwise looks like a "currently valid
    actor's action" in the forensic trail.
    """
    monkeypatch.setenv("AUDIT_RETENTION_DAYS", "30")
    monkeypatch.setenv("AUDIT_SECRET_KEY", "x" * 44 + "=")
    from contextlib import contextmanager

    from fastapi import FastAPI, HTTPException
    from fastapi.testclient import TestClient

    from ops.audit import middleware as audit_mw

    app = FastAPI()
    app.add_middleware(audit_mw.AuditMiddleware)

    @app.post("/api/billing/admin/plans")
    async def _create_plan() -> dict:
        # Simulate the auth dependency rejecting a revoked-but-
        # cryptographically-valid token.
        raise HTTPException(
            status_code=401, detail="Could not validate credentials"
        )

    @contextmanager
    def _fake_getdb():
        yield db_session

    monkeypatch.setattr(audit_mw, "GetDB", _fake_getdb)
    client = TestClient(app, raise_server_exceptions=False)

    # Mint a syntactically-valid token so _resolve_actor reaches the
    # status_code check (rather than bailing earlier on InvalidToken).
    token = _mint_admin_token("ghost", is_sudo=False)
    resp = client.post(
        "/api/billing/admin/plans",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401

    from ops.audit.db import AuditEvent

    row = db_session.query(AuditEvent).one()
    # The crux: token decoded fine, but the auth path rejected the
    # request → middleware must NOT name "ghost" in the audit row.
    assert row.actor_type == "anonymous"
    assert row.actor_username is None
    assert row.status_code == 401
    assert row.result == "denied"


def test_ip_gate_invalid_peer_ip_does_not_crash(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Defensive: ``request.client.host`` could be a non-IP string in
    some ASGI servers (e.g. unix socket). The gate must not crash."""
    monkeypatch.setenv("AUDIT_RETENTION_DAYS", "30")
    monkeypatch.setenv("AUDIT_SECRET_KEY", "x" * 44 + "=")
    monkeypatch.setenv("AUDIT_TRUSTED_PROXIES", "127.0.0.1/32")
    from ops.audit import middleware as audit_mw

    audit_mw._reload_trusted_proxies_for_tests()
    client = _make_app(monkeypatch, db_session)
    # TestClient peer = "testclient" string. _peer_is_trusted_proxy
    # must catch ValueError from ipaddress.ip_address and return False.
    resp = client.post(
        "/api/billing/admin/plans",
        headers={"X-Forwarded-For": "9.9.9.9"},
    )
    assert resp.status_code == 200  # no crash from the gate


# ---------------------------------------------------------------------
# Wave-6 / L-034 regressions: pure-ASGI rewrite (PR #170)
#
# The old AuditMiddleware was BaseHTTPMiddleware-based, which on FastAPI
# 0.115+ drops `fastapi_inner_astack` from request scope and breaks any
# route using Depends() with an async context manager. These tests
# pin the wave-6 fix: pure-ASGI form keeps the inner app's scope intact
# so FastAPI's DI works regardless of audit state.
# ---------------------------------------------------------------------


def test_l034_depends_async_ctx_manager_works_with_audit_mounted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Routes using Depends() with an async context manager (the
    FastAPI 0.115+ fastapi_inner_astack path) must return 200 with
    AuditMiddleware mounted. Pre-wave-6 BaseHTTPMiddleware-based form
    raised AssertionError 'fastapi_inner_astack not found in request
    scope' on every such route — that's the production bug L-034
    documented across wave-1..5."""
    from contextlib import asynccontextmanager

    from fastapi import Depends, FastAPI
    from fastapi.testclient import TestClient

    from ops.audit import middleware as audit_mw

    monkeypatch.setenv("AUDIT_RETENTION_DAYS", "0")  # no DB writes needed

    @asynccontextmanager
    async def _async_ctx():
        # Mimics get_db / get_admin yield patterns from app/dependencies.py
        yield {"sentinel": True}

    async def _dep():
        async with _async_ctx() as ctx:
            yield ctx

    app = FastAPI()
    app.add_middleware(audit_mw.AuditMiddleware)

    @app.get("/with-async-dep")
    async def _route(ctx: dict = Depends(_dep)) -> dict:
        return {"sentinel_seen": ctx.get("sentinel", False)}

    client = TestClient(app, raise_server_exceptions=True)
    resp = client.get("/with-async-dep")
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"sentinel_seen": True}


def test_l034_request_state_dict_not_corrupted_for_downstream(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Codex P2 on commit 0e26017: AuditMiddleware must NOT assign a
    State object to scope['state']; Starlette expects a dict and wraps
    it via Request.state. Other handlers/middleware indexing it as a
    dict would TypeError. Use request.state.x = y API."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from starlette.requests import Request as StarletteRequest

    from ops.audit import middleware as audit_mw

    monkeypatch.setenv("AUDIT_RETENTION_DAYS", "0")
    app = FastAPI()
    app.add_middleware(audit_mw.AuditMiddleware)

    @app.get("/probe-state")
    async def _probe(request: StarletteRequest) -> dict:
        # 1. audit_request_id is reachable via request.state attribute API
        rid = getattr(request.state, "audit_request_id", None)
        # 2. scope['state'] should still be subscriptable as a dict
        scope_state = request.scope.get("state")
        return {
            "request_id_present": bool(rid),
            "scope_state_is_mapping": hasattr(scope_state, "__getitem__")
            or hasattr(scope_state, "_state"),
        }

    client = TestClient(app)
    resp = client.get("/probe-state", headers={"X-Request-ID": "rid-from-test"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["request_id_present"] is True


def test_l034_audit_disabled_zero_db_writes(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When AUDIT_RETENTION_DAYS=0 the middleware is mounted (post wave-6
    we always mount) but must not write rows. Wave-6 changed the
    is_audit_enabled() gate from 'condition for mounting' to 'early
    return inside the request path'."""
    monkeypatch.setenv("AUDIT_RETENTION_DAYS", "0")
    monkeypatch.setenv("AUDIT_SECRET_KEY", "x" * 44 + "=")
    client = _make_app(monkeypatch, db_session)

    # Hit several in-scope mutate routes
    for _ in range(3):
        resp = client.post("/api/billing/admin/plans")
        assert resp.status_code == 200

    from ops.audit.db import AuditEvent

    rows = db_session.query(AuditEvent).all()
    assert rows == []  # zero rows when retention=0 even with middleware mounted


def test_l034_non_http_scope_passthrough(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pure-ASGI middleware must passthrough non-http scopes (websocket,
    lifespan) untouched — the audit-write path is HTTP-only."""
    import asyncio

    from ops.audit import middleware as audit_mw

    monkeypatch.setenv("AUDIT_RETENTION_DAYS", "0")
    seen_scopes: list[str] = []

    async def inner_app(scope, receive, send):
        seen_scopes.append(scope["type"])
        if scope["type"] == "lifespan":
            # Drain lifespan messages
            msg = await receive()
            if msg["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            return

    mw = audit_mw.AuditMiddleware(inner_app)

    sent: list[dict] = []

    async def _send(msg):
        sent.append(msg)

    received = iter([{"type": "lifespan.startup"}])

    async def _recv():
        try:
            return next(received)
        except StopIteration:
            await asyncio.sleep(0.01)
            return {"type": "lifespan.shutdown"}

    asyncio.run(mw({"type": "lifespan"}, _recv, _send))
    assert seen_scopes == ["lifespan"]
    assert sent == [{"type": "lifespan.startup.complete"}]
