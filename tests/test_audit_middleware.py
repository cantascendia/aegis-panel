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
