"""
Tests for ``ops.billing.endpoint`` — admin REST.

Mirrors ``tests/test_sni_endpoint.py`` pattern: builds a minimal
FastAPI app locally mounting only the billing router, overrides
``sudo_admin`` + ``get_db`` dependencies with test doubles, runs
TestClient against it.

Scratch SQLite in-memory engine with billing tables only — same
scoping as ``test_billing_db.py`` / ``test_billing_states.py`` to
avoid upstream-DDL compat issues.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from ops.billing.db import (
    INVOICE_STATE_APPLIED,
    INVOICE_STATE_AWAITING_PAYMENT,
    INVOICE_STATE_CANCELLED,
    INVOICE_STATE_CREATED,
    INVOICE_STATE_PAID,
    INVOICE_STATE_PENDING,
    Invoice,
    PaymentEvent,
    Plan,
)

# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------


@pytest.fixture
def billing_engine():
    """Fresh SQLite with billing tables only."""
    billing_tables = [
        Base.metadata.tables[name]
        for name in (
            "aegis_billing_plans",
            "aegis_billing_channels",
            "aegis_billing_invoices",
            "aegis_billing_invoice_lines",
            "aegis_billing_payment_events",
        )
    ]
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=billing_tables)
    yield engine
    engine.dispose()


@pytest.fixture
def fake_sudo_admin() -> Any:
    class _A:
        username = "test-sudo"
        is_sudo = True
        enabled = True

    return _A()


@pytest.fixture
def app_with_billing(billing_engine, fake_sudo_admin):
    from app.dependencies import get_db, sudo_admin
    from ops.billing.endpoint import router as billing_router

    app = FastAPI()
    app.include_router(billing_router)

    def _db_override():
        with Session(billing_engine) as s:
            yield s

    def _admin_override():
        return fake_sudo_admin

    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[sudo_admin] = _admin_override
    return app


@pytest.fixture
def client(app_with_billing) -> TestClient:
    return TestClient(app_with_billing)


def _seed_invoice(
    engine,
    state: str = INVOICE_STATE_CREATED,
    provider: str = "trc20",
    user_id: int = 1,
) -> int:
    """Insert a minimal invoice and return its id."""
    now = datetime(2026, 4, 22, 12, 0, 0)
    with Session(engine) as s:
        inv = Invoice(
            user_id=user_id,
            total_cny_fen=5000,
            state=state,
            provider=provider,
            created_at=now,
            expires_at=now + timedelta(minutes=30),
        )
        s.add(inv)
        s.commit()
        return inv.id


# ---------------------------------------------------------------------
# Auth gate
# ---------------------------------------------------------------------


def test_auth_401_without_token(app_with_billing):
    """Real sudo_admin dep (not overridden) → 401 when no token."""
    from app.dependencies import sudo_admin

    app_with_billing.dependency_overrides.pop(sudo_admin, None)
    with TestClient(app_with_billing) as c:
        r = c.get("/api/billing/admin/plans")
    assert r.status_code == 401


def test_auth_403_for_non_sudo(app_with_billing):
    from app.dependencies import sudo_admin

    def _non_sudo():
        raise HTTPException(status_code=403, detail="Access Denied")

    app_with_billing.dependency_overrides[sudo_admin] = _non_sudo
    with TestClient(app_with_billing) as c:
        r = c.get("/api/billing/admin/plans")
    assert r.status_code == 403


# ---------------------------------------------------------------------
# Plan CRUD
# ---------------------------------------------------------------------


def test_list_plans_empty(client):
    r = client.get("/api/billing/admin/plans")
    assert r.status_code == 200
    assert r.json() == []


def test_create_fixed_plan_happy(client):
    r = client.post(
        "/api/billing/admin/plans",
        json={
            "operator_code": "starter-30",
            "display_name_en": "Starter 30/30",
            "kind": "fixed",
            "data_limit_gb": 30,
            "duration_days": 30,
            "price_cny_fen": 5000,
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["operator_code"] == "starter-30"
    assert body["kind"] == "fixed"
    assert body["enabled"] is True


def test_create_plan_duplicate_operator_code_conflicts(client):
    payload = {
        "operator_code": "starter-30",
        "display_name_en": "Starter",
        "kind": "fixed",
        "data_limit_gb": 30,
        "duration_days": 30,
        "price_cny_fen": 5000,
    }
    client.post("/api/billing/admin/plans", json=payload)
    r = client.post("/api/billing/admin/plans", json=payload)
    assert r.status_code == 409


def test_create_plan_fixed_missing_both_dims_422(client):
    r = client.post(
        "/api/billing/admin/plans",
        json={
            "operator_code": "bad-fixed",
            "display_name_en": "Bad",
            "kind": "fixed",
            "price_cny_fen": 100,
        },
    )
    assert r.status_code == 422
    # Pydantic surfaces the field-level error
    assert "must specify at least one" in r.text


def test_create_flex_traffic_with_days_set_422(client):
    r = client.post(
        "/api/billing/admin/plans",
        json={
            "operator_code": "bad-flex",
            "display_name_en": "Bad",
            "kind": "flexible_traffic",
            "data_limit_gb": 1,
            "duration_days": 7,  # illegal for flex_traffic
            "price_cny_fen": 50,
        },
    )
    assert r.status_code == 422
    assert "must NOT set duration_days" in r.text


def test_patch_plan_updates_price_and_disables(client):
    r = client.post(
        "/api/billing/admin/plans",
        json={
            "operator_code": "p1",
            "display_name_en": "P1",
            "kind": "fixed",
            "data_limit_gb": 10,
            "duration_days": 30,
            "price_cny_fen": 3000,
        },
    )
    pid = r.json()["id"]
    r2 = client.patch(
        f"/api/billing/admin/plans/{pid}",
        json={"price_cny_fen": 2500, "enabled": False},
    )
    assert r2.status_code == 200
    body = r2.json()
    assert body["price_cny_fen"] == 2500
    assert body["enabled"] is False


def test_patch_nonexistent_plan_404(client):
    r = client.patch(
        "/api/billing/admin/plans/999999", json={"enabled": False}
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------
# Channel CRUD
# ---------------------------------------------------------------------


def test_create_channel_happy(client):
    r = client.post(
        "/api/billing/admin/channels",
        json={
            "channel_code": "zpay1",
            "display_name": "ZPay Main",
            "gateway_url": "https://zpay.example/submit",
            "merchant_id": "M1234",
            "secret_key": "superseecret",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["channel_code"] == "zpay1"
    # secret_key MUST NOT leak in responses
    assert "secret_key" not in body


def test_patch_channel_rotates_secret_key(client):
    created = client.post(
        "/api/billing/admin/channels",
        json={
            "channel_code": "z1",
            "display_name": "Z1",
            "gateway_url": "https://z.example",
            "merchant_id": "M",
            "secret_key": "old_key",
        },
    ).json()
    r = client.patch(
        f"/api/billing/admin/channels/{created['id']}",
        json={"secret_key": "rotated_key", "enabled": True},
    )
    assert r.status_code == 200
    assert r.json()["enabled"] is True
    # Response still doesn't echo the secret back
    assert "secret_key" not in r.json()


# ---------------------------------------------------------------------
# Invoice list + actions
# ---------------------------------------------------------------------


def test_list_invoices_empty(client):
    r = client.get("/api/billing/admin/invoices")
    assert r.status_code == 200
    assert r.json() == []


def test_list_invoices_filters_by_state(client, billing_engine):
    _seed_invoice(billing_engine, state=INVOICE_STATE_CREATED)
    _seed_invoice(billing_engine, state=INVOICE_STATE_AWAITING_PAYMENT)

    r = client.get(
        "/api/billing/admin/invoices",
        params={"state": INVOICE_STATE_AWAITING_PAYMENT},
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["state"] == INVOICE_STATE_AWAITING_PAYMENT


def test_get_invoice_404(client):
    r = client.get("/api/billing/admin/invoices/99999")
    assert r.status_code == 404


def test_apply_manual_created_to_applied_chain(client, billing_engine):
    inv_id = _seed_invoice(billing_engine, state=INVOICE_STATE_CREATED)
    r = client.post(
        f"/api/billing/admin/invoices/{inv_id}/apply_manual",
        json={"note": "VIP granted by operator"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["state"] == INVOICE_STATE_APPLIED
    # Audit rows record the admin_manual event chain
    events = client.get(f"/api/billing/admin/invoices/{inv_id}/events").json()
    types = [e["event_type"] for e in events]
    assert any("admin_manual:to_pending" in t for t in types)
    assert any("admin_manual:to_paid" in t for t in types)
    assert any("admin_manual:to_applied" in t for t in types)
    # Note is preserved on at least one event
    assert any(e["note"] == "VIP granted by operator" for e in events)


def test_apply_manual_from_awaiting_payment_skips_pending(
    client, billing_engine
):
    inv_id = _seed_invoice(
        billing_engine, state=INVOICE_STATE_AWAITING_PAYMENT
    )
    r = client.post(
        f"/api/billing/admin/invoices/{inv_id}/apply_manual",
        json={"note": "manual override"},
    )
    assert r.status_code == 200
    assert r.json()["state"] == INVOICE_STATE_APPLIED


def test_apply_manual_rejected_on_terminal(client, billing_engine):
    inv_id = _seed_invoice(billing_engine, state=INVOICE_STATE_APPLIED)
    r = client.post(
        f"/api/billing/admin/invoices/{inv_id}/apply_manual",
        json={"note": "trying double apply"},
    )
    assert r.status_code == 409


def test_apply_manual_requires_note(client, billing_engine):
    inv_id = _seed_invoice(billing_engine, state=INVOICE_STATE_CREATED)
    r = client.post(
        f"/api/billing/admin/invoices/{inv_id}/apply_manual",
        json={},  # missing required note
    )
    assert r.status_code == 422


def test_cancel_from_pending_happy(client, billing_engine):
    inv_id = _seed_invoice(billing_engine, state=INVOICE_STATE_PENDING)
    r = client.post(
        f"/api/billing/admin/invoices/{inv_id}/cancel",
        json={"note": "user requested refund"},
    )
    assert r.status_code == 200
    assert r.json()["state"] == INVOICE_STATE_CANCELLED


def test_cancel_rejected_on_terminal(client, billing_engine):
    inv_id = _seed_invoice(billing_engine, state=INVOICE_STATE_APPLIED)
    r = client.post(
        f"/api/billing/admin/invoices/{inv_id}/cancel",
        json={"note": "too late"},
    )
    assert r.status_code == 409


def test_events_endpoint_returns_chronological(client, billing_engine):
    inv_id = _seed_invoice(billing_engine, state=INVOICE_STATE_PENDING)
    client.post(
        f"/api/billing/admin/invoices/{inv_id}/apply_manual",
        json={"note": "x"},
    )
    events = client.get(f"/api/billing/admin/invoices/{inv_id}/events").json()
    # At least paid + applied events
    assert len(events) >= 2
    # Chronologically ordered (or at least non-decreasing created_at)
    times = [e["created_at"] for e in events]
    assert times == sorted(times)


# Silence unused-import lint
_ = PaymentEvent
_ = Plan
