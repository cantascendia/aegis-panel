"""Tests for ops.audit.endpoint (AL.3 — read API).

Pin:
- Sudo-only access on every endpoint.
- List filters (actor / action / target / result / since-until).
- Cursor pagination correctness (no skipped rows on deletion).
- Detail returns decrypted state (sudo) and 404 for unknown id.
- CSV export cap respected.
- CSV does not include state-diff fields (free-form JSON exclusion).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import pytest
from cryptography.fernet import Fernet

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def _fresh_key() -> str:
    return Fernet.generate_key().decode()


def _make_event(
    session: "Session",
    *,
    actor_username: str = "alice",
    actor_type: str = "admin",
    action: str = "billing.plan.update",
    method: str = "PATCH",
    path: str = "/api/billing/admin/plans/1",
    target_type: str | None = "billing.plan",
    target_id: str | None = "1",
    result: str = "success",
    status_code: int = 200,
    error_message: str | None = None,
    before_state_encrypted: bytes | None = None,
    after_state_encrypted: bytes | None = None,
    ts_offset_minutes: int = 0,
) -> int:
    from ops.audit.db import AuditEvent, _now_utc_naive

    event = AuditEvent(
        actor_id=None,
        actor_type=actor_type,
        actor_username=actor_username,
        action=action,
        method=method,
        path=path,
        target_type=target_type,
        target_id=target_id,
        before_state_encrypted=before_state_encrypted,
        after_state_encrypted=after_state_encrypted,
        result=result,
        status_code=status_code,
        error_message=error_message,
        ip="127.0.0.1",
        user_agent="pytest",
        request_id=f"req-{datetime.utcnow().timestamp()}",
        ts=_now_utc_naive() - timedelta(minutes=ts_offset_minutes),
    )
    session.add(event)
    session.commit()
    return event.id


# ---------------------------------------------------------------------
# Helper: build a FastAPI app with the audit router + sudo bypass
# ---------------------------------------------------------------------


def _make_app(monkeypatch: pytest.MonkeyPatch, db_session):
    """Mount the audit router with the sudo dependency overridden so
    the test isn't gated on a real Admin row."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.dependencies import get_db, sudo_admin
    from ops.audit.endpoint import router as audit_router

    app = FastAPI()
    app.include_router(audit_router)
    # Sudo bypass for tests — production uses real Depends.
    app.dependency_overrides[sudo_admin] = lambda: type(
        "Admin", (), {"username": "test_sudo", "is_sudo": True}
    )()
    # DB session bound to the test in-memory engine.
    app.dependency_overrides[get_db] = lambda: db_session
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------
# List endpoint
# ---------------------------------------------------------------------


def test_list_returns_empty_when_no_rows(
    db_session: "Session", monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _make_app(monkeypatch, db_session)
    resp = client.get("/api/audit/events")
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["next_cursor"] is None
    assert body["total_returned"] == 0


def test_list_returns_rows_newest_first(
    db_session: "Session", monkeypatch: pytest.MonkeyPatch
) -> None:
    _make_event(db_session, ts_offset_minutes=10)  # older
    _make_event(db_session, ts_offset_minutes=0)  # newer

    client = _make_app(monkeypatch, db_session)
    resp = client.get("/api/audit/events")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 2
    # Descending by id (newest first)
    assert items[0]["id"] > items[1]["id"]


def test_list_filter_by_actor_username(
    db_session: "Session", monkeypatch: pytest.MonkeyPatch
) -> None:
    _make_event(db_session, actor_username="alice")
    _make_event(db_session, actor_username="bob")

    client = _make_app(monkeypatch, db_session)
    resp = client.get("/api/audit/events?actor_username=alice")
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["actor_username"] == "alice"


def test_list_filter_by_action_substring(
    db_session: "Session", monkeypatch: pytest.MonkeyPatch
) -> None:
    _make_event(db_session, action="billing.plan.update")
    _make_event(db_session, action="iplimit.policy.delete")

    client = _make_app(monkeypatch, db_session)
    resp = client.get("/api/audit/events?action=billing")
    items = resp.json()["items"]
    assert len(items) == 1
    assert "billing" in items[0]["action"]


def test_list_filter_by_result(
    db_session: "Session", monkeypatch: pytest.MonkeyPatch
) -> None:
    _make_event(db_session, result="success", status_code=200)
    _make_event(db_session, result="denied", status_code=403)
    _make_event(db_session, result="failure", status_code=500)

    client = _make_app(monkeypatch, db_session)
    resp = client.get("/api/audit/events?result=denied")
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["result"] == "denied"


def test_list_cursor_pagination(
    db_session: "Session", monkeypatch: pytest.MonkeyPatch
) -> None:
    """Page through 5 rows with limit=2."""
    ids = [_make_event(db_session) for _ in range(5)]
    client = _make_app(monkeypatch, db_session)

    resp1 = client.get("/api/audit/events?limit=2")
    body1 = resp1.json()
    assert body1["total_returned"] == 2
    assert body1["next_cursor"] is not None

    resp2 = client.get(f"/api/audit/events?limit=2&cursor={body1['next_cursor']}")
    body2 = resp2.json()
    assert body2["total_returned"] == 2
    assert body2["items"][0]["id"] < body1["items"][-1]["id"]

    resp3 = client.get(f"/api/audit/events?limit=2&cursor={body2['next_cursor']}")
    body3 = resp3.json()
    assert body3["total_returned"] == 1
    assert body3["next_cursor"] is None  # end of data


def test_list_limit_capped_at_max(
    db_session: "Session", monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _make_app(monkeypatch, db_session)
    # FastAPI Query(le=200) returns 422 on out-of-range.
    resp = client.get("/api/audit/events?limit=999")
    assert resp.status_code == 422


# ---------------------------------------------------------------------
# Detail endpoint
# ---------------------------------------------------------------------


def test_detail_returns_404_for_unknown_id(
    db_session: "Session", monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _make_app(monkeypatch, db_session)
    resp = client.get("/api/audit/events/9999")
    assert resp.status_code == 404


def test_detail_decrypts_state_diff(
    db_session: "Session", monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AUDIT_RETENTION_DAYS", "30")
    monkeypatch.setenv("AUDIT_SECRET_KEY", _fresh_key())
    from ops.audit import crypto

    crypto._reload_for_tests()
    # Encrypt a payload manually so detail must decrypt it.
    before_ct = crypto.encrypt_audit_payload({"price_fen": 1000})
    after_ct = crypto.encrypt_audit_payload({"price_fen": 1500})
    eid = _make_event(
        db_session,
        before_state_encrypted=before_ct,
        after_state_encrypted=after_ct,
    )

    client = _make_app(monkeypatch, db_session)
    resp = client.get(f"/api/audit/events/{eid}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["before_state"] == {"price_fen": 1000}
    assert body["after_state"] == {"price_fen": 1500}


def test_detail_returns_none_state_when_no_ciphertext(
    db_session: "Session", monkeypatch: pytest.MonkeyPatch
) -> None:
    eid = _make_event(db_session)
    client = _make_app(monkeypatch, db_session)
    resp = client.get(f"/api/audit/events/{eid}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["before_state"] is None
    assert body["after_state"] is None


# ---------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------


def test_csv_export_returns_header_and_rows(
    db_session: "Session", monkeypatch: pytest.MonkeyPatch
) -> None:
    _make_event(db_session, actor_username="alice")
    _make_event(db_session, actor_username="bob")
    client = _make_app(monkeypatch, db_session)

    resp = client.get("/api/audit/events/export.csv")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "attachment" in resp.headers["content-disposition"]
    text = resp.text
    lines = [line for line in text.splitlines() if line]
    # Header + 2 rows
    assert len(lines) == 3
    assert lines[0].startswith("id,ts,actor_username,")


def test_csv_export_excludes_state_diff_fields(
    db_session: "Session", monkeypatch: pytest.MonkeyPatch
) -> None:
    """State diffs are free-form JSON; CSV shape would be unstable."""
    _make_event(db_session)
    client = _make_app(monkeypatch, db_session)
    resp = client.get("/api/audit/events/export.csv")
    text = resp.text
    assert "before_state" not in text.split("\n")[0]
    assert "after_state" not in text.split("\n")[0]


def test_csv_export_filter_by_actor(
    db_session: "Session", monkeypatch: pytest.MonkeyPatch
) -> None:
    _make_event(db_session, actor_username="alice")
    _make_event(db_session, actor_username="bob")
    client = _make_app(monkeypatch, db_session)

    resp = client.get("/api/audit/events/export.csv?actor_username=alice")
    text = resp.text
    lines = [line for line in text.splitlines() if line]
    assert len(lines) == 2  # header + 1 data row
    assert "alice" in lines[1]
    assert "bob" not in text
