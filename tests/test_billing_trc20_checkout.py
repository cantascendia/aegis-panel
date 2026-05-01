"""
Tests for TRC20 cart/checkout fall-through fix (v0.4.0 hot-fix).

Bug context (discovered 2026-05-01 in nilou.cc production after
Phase A.2 wired ``.env`` + 4 plans):

``POST /api/billing/cart/checkout`` with ``channel_code == "trc20"``
returned 404 because the handler looked up a ``PaymentChannel`` row
(none exists for TRC20 by design — see ``ops/billing/db.py``
``PaymentChannel`` docstring "TRC20 is NOT represented here").

This module exercises the new branch:

- happy path: TRC20 checkout returns invoice + memo + amount.
- skips ``BILLING_PUBLIC_BASE_URL`` gate (EPay-only requirement).
- 503 when ``BILLING_TRC20_ENABLED=false`` regardless of body.
- ``Invoice.provider`` field is ``"trc20"`` (not ``"epay:trc20"``)
  so the poller's ``Invoice.provider == PROVIDER_TRC20`` filter
  picks it up.

EPay path is regression-protected by the existing
``test_billing_checkout_webhook.py`` suite; we only spot-check here
that the EPay branch still works when both knobs are configured.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from ops.billing import config as billing_config
from ops.billing import trc20_config
from ops.billing.db import (
    INVOICE_STATE_AWAITING_PAYMENT,
    Invoice,
)


# ---------------------------------------------------------------------
# Fixtures (parallel structure to test_billing_checkout_webhook.py;
# kept in this module so fix lands as a single self-contained file).
# ---------------------------------------------------------------------


@pytest.fixture
def billing_engine():
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
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
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
    from ops.billing.checkout_endpoint import checkout_router
    from ops.billing.endpoint import router as admin_router

    app = FastAPI()
    app.include_router(admin_router)
    app.include_router(checkout_router)

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
    return TestClient(app_with_billing, client=("127.0.0.1", 51234))


@pytest.fixture
def trc20_enabled(monkeypatch: pytest.MonkeyPatch):
    """Wire env-driven TRC20 config so ``get_trc20_provider()``
    returns a real provider. Reverts at fixture teardown by clearing
    the module-level lru_cache so subsequent tests get a clean slate.
    """
    trc20_config._reload_for_tests(
        enabled=True,
        receive_address="TXyz1234567890abcdefghijklmnopqrstuvw",
        rate_fen_per_usdt=720,
        memo_salt="test-memo-salt",
    )
    yield
    trc20_config._reload_for_tests(enabled=False)


@pytest.fixture
def seeded_plan(client) -> dict[str, Any]:
    r = client.post(
        "/api/billing/admin/plans",
        json={
            "operator_code": "starter-30",
            "display_name_en": "Starter 30d/30GB",
            "kind": "fixed",
            "data_limit_gb": 30,
            "duration_days": 30,
            "price_cny_fen": 5000,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture
def seeded_epay_channel(client) -> dict[str, Any]:
    """Used only by the EPay regression test."""
    r = client.post(
        "/api/billing/admin/channels",
        json={
            "channel_code": "zpay_test",
            "display_name": "ZPay Test",
            "gateway_url": "https://pay.test",
            "merchant_id": "M100",
            "merchant_key": "super-seecret",
            "enabled": True,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


# ---------------------------------------------------------------------
# Happy path: TRC20 checkout returns memo + amount + receive_address
# ---------------------------------------------------------------------


def test_trc20_checkout_returns_memo_and_amount(
    client, trc20_enabled, seeded_plan, billing_engine
):
    """Pre-fix this returned 404 because the handler unconditionally
    looked up a PaymentChannel row.  After fix it should:

    - return 201
    - response carries memo, expected_amount_millis, receive_address
    - invoice.state == awaiting_payment
    - invoice.provider == "trc20" (not "epay:trc20")
    - invoice.trc20_memo / trc20_expected_amount_millis populated
    """
    r = client.post(
        "/api/billing/cart/checkout",
        json={
            "user_id": 1,
            "channel_code": "trc20",
            "lines": [{"plan_id": seeded_plan["id"], "quantity": 1}],
            "success_url": "https://panel.test/ok",
            "cancel_url": "https://panel.test/cancel",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()

    assert body["state"] == INVOICE_STATE_AWAITING_PAYMENT
    assert body["total_cny_fen"] == 5000
    # in-panel TRC20 detail route
    assert body["payment_url"].startswith("/billing/trc20/")
    # memo: 8 chars from safe alphabet (no 0/O/I/L/1)
    assert body["trc20_memo"] is not None
    assert len(body["trc20_memo"]) == 8
    assert all(ch not in body["trc20_memo"] for ch in "0OIL1")
    # 5000 fen / 720 fen/USDT = 6.9444... USDT → ceil(6944.44) = 6945
    # millis. Pinned by ops.billing.pricing.convert_fen_to_usdt_millis
    # (operator-favouring round-up).
    assert body["trc20_expected_amount_millis"] == 6945
    assert body["trc20_receive_address"] == (
        "TXyz1234567890abcdefghijklmnopqrstuvw"
    )

    with Session(billing_engine) as s:
        inv = s.get(Invoice, body["invoice_id"])
        assert inv is not None
        assert inv.provider == "trc20"
        assert inv.trc20_memo == body["trc20_memo"]
        assert (
            inv.trc20_expected_amount_millis
            == body["trc20_expected_amount_millis"]
        )


# ---------------------------------------------------------------------
# Skip BILLING_PUBLIC_BASE_URL gate (EPay-only — TRC20 has no webhook)
# ---------------------------------------------------------------------


def test_trc20_checkout_skips_public_base_url_check(
    client, trc20_enabled, seeded_plan, monkeypatch
):
    """TRC20 has no webhook callback (poller-only). The
    ``BILLING_PUBLIC_BASE_URL`` gate must NOT apply — EPay-specific.

    Pre-fix: blank ``BILLING_PUBLIC_BASE_URL`` 503'd ALL checkouts.
    Post-fix: TRC20 ignores it.
    """
    monkeypatch.setattr(billing_config, "BILLING_PUBLIC_BASE_URL", "")
    r = client.post(
        "/api/billing/cart/checkout",
        json={
            "user_id": 1,
            "channel_code": "trc20",
            "lines": [{"plan_id": seeded_plan["id"], "quantity": 1}],
            "success_url": "https://panel.test/ok",
            "cancel_url": "https://panel.test/cancel",
        },
    )
    assert r.status_code == 201, r.text


# ---------------------------------------------------------------------
# 503 when BILLING_TRC20_ENABLED=false
# ---------------------------------------------------------------------


def test_trc20_checkout_503_when_partially_configured(client, seeded_plan):
    """Codex P2 review: ``BILLING_TRC20_ENABLED=true`` + a missing
    supporting env var (e.g. ``RECEIVE_ADDRESS``) used to surface as
    an unhandled 500 because ``get_provider("trc20")`` raised
    ``Trc20Misconfigured`` outside any except block.

    Post-fix: catch ``Trc20Misconfigured`` BEFORE writing the invoice
    row and translate to 503 with the missing-vars list. The "no DB
    write on misconfig" invariant matches the
    ``BILLING_TRC20_ENABLED=false`` branch.
    """
    trc20_config._reload_for_tests(
        enabled=True,
        receive_address="",  # gap → triggers Trc20Misconfigured
        rate_fen_per_usdt=720,
        memo_salt="test-memo-salt",
    )
    try:
        r = client.post(
            "/api/billing/cart/checkout",
            json={
                "user_id": 1,
                "channel_code": "trc20",
                "lines": [{"plan_id": seeded_plan["id"], "quantity": 1}],
                "success_url": "https://panel.test/ok",
                "cancel_url": "https://panel.test/cancel",
            },
        )
        assert r.status_code == 503, r.text
        # Body must name the missing env var so the operator can act
        assert "BILLING_TRC20_RECEIVE_ADDRESS" in r.text
    finally:
        trc20_config._reload_for_tests(enabled=False)


def test_trc20_checkout_503_when_disabled(client, seeded_plan):
    """Default fixture state is ``BILLING_TRC20_ENABLED=false``
    (no ``trc20_enabled`` fixture used). Operator hasn't opted in →
    fail-loud 503 with an actionable message, NOT a silent 404.
    """
    # Defensive reset — make sure no other test left it on.
    trc20_config._reload_for_tests(enabled=False)

    r = client.post(
        "/api/billing/cart/checkout",
        json={
            "user_id": 1,
            "channel_code": "trc20",
            "lines": [{"plan_id": seeded_plan["id"], "quantity": 1}],
            "success_url": "https://panel.test/ok",
            "cancel_url": "https://panel.test/cancel",
        },
    )
    assert r.status_code == 503
    assert "BILLING_TRC20_ENABLED" in r.text


# ---------------------------------------------------------------------
# Invoice.provider field shape — pre-fix bug #2
# ---------------------------------------------------------------------


def test_trc20_invoice_provider_field_is_not_epay_prefixed(
    client, trc20_enabled, seeded_plan, billing_engine
):
    """Pre-fix the handler hardcoded ``provider=f"epay:{channel_code}"``
    which mislabeled TRC20 invoices as ``"epay:trc20"`` and broke the
    poller's ``Invoice.provider == "trc20"`` filter.

    Regression guard: row's ``provider`` MUST be the bare ``"trc20"``
    constant (matches ``ops.billing.db.PROVIDER_TRC20``).
    """
    r = client.post(
        "/api/billing/cart/checkout",
        json={
            "user_id": 1,
            "channel_code": "trc20",
            "lines": [{"plan_id": seeded_plan["id"], "quantity": 1}],
            "success_url": "https://panel.test/ok",
            "cancel_url": "https://panel.test/cancel",
        },
    )
    assert r.status_code == 201, r.text
    invoice_id = r.json()["invoice_id"]

    with Session(billing_engine) as s:
        inv = s.get(Invoice, invoice_id)
        assert inv is not None
        assert inv.provider == "trc20"
        assert not inv.provider.startswith("epay:")


# ---------------------------------------------------------------------
# EPay regression: existing path still works untouched
# ---------------------------------------------------------------------


def test_epay_checkout_unchanged_when_trc20_branch_added(
    client, seeded_epay_channel, seeded_plan
):
    """Sanity check: the new ``is_trc20`` branch must not perturb the
    EPay path. We only assert the contract stays — full EPay coverage
    lives in ``test_billing_checkout_webhook.py``.
    """
    r = client.post(
        "/api/billing/cart/checkout",
        json={
            "user_id": 1,
            "channel_code": seeded_epay_channel["channel_code"],
            "lines": [{"plan_id": seeded_plan["id"], "quantity": 1}],
            "success_url": "https://panel.test/ok",
            "cancel_url": "https://panel.test/cancel",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    # EPay path: payment_url is the 码商 redirect, not an in-panel route
    assert body["payment_url"].startswith("https://pay.test")
    # TRC20-conv fields stay None for EPay invoices
    assert body["trc20_memo"] is None
    assert body["trc20_expected_amount_millis"] is None
    assert body["trc20_receive_address"] is None
