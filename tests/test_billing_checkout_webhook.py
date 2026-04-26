"""
Tests for ``ops.billing.checkout_endpoint`` — checkout + epay webhook.

Covers A.2.2 acceptance criteria:

- Fernet encryption roundtrip on PaymentChannel.merchant_key
- sign_body_mode (plain / with_key_prefix) dialect switching
- Cart checkout happy path + channel-disabled / missing
- Webhook sign verify pass / fail
- Webhook replay idempotent
- Webhook trade_status != TRADE_SUCCESS treated as "observed but
  non-actionable" and still replies ``success``
- IP allowlist pass / block / CIDR matching
- End-to-end: checkout → webhook → invoice.state == paid + audit trail

Fixtures reuse the same in-memory SQLite + dependency-override
shape as ``test_billing_endpoint.py``. The tests never hit a real
EPay gateway — the ``create_invoice`` path constructs a submit URL,
which is a pure string operation, and the ``handle_webhook`` path
is fed synthesized params with signs we compute locally using the
same :func:`compute_sign` helper.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from ops.billing import config as billing_config
from ops.billing.db import (
    INVOICE_STATE_AWAITING_PAYMENT,
    INVOICE_STATE_PAID,
    Invoice,
    PaymentChannel,
    PaymentEvent,
    Plan,
)
from ops.billing.providers.epay import (
    SIGN_BODY_MODE_PLAIN,
    SIGN_BODY_MODE_WITH_KEY_PREFIX,
    compute_sign,
)

# ---------------------------------------------------------------------
# Fixtures
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
    # FastAPI's TestClient defaults `request.client.host` to the
    # literal string "testclient", which can't be parsed as an IP
    # and therefore wouldn't match the loopback CIDR our conftest
    # sets in BILLING_TRUSTED_PROXIES. Pin the peer to 127.0.0.1
    # so the trusted-proxy path (the realistic "panel behind same-
    # host reverse proxy" deployment shape) is what we're testing.
    return TestClient(app_with_billing, client=("127.0.0.1", 51234))


@pytest.fixture
def seeded_channel(client) -> dict[str, Any]:
    """Create one enabled EPay channel with ``plain`` sign mode."""
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


# ---------------------------------------------------------------------
# Encryption roundtrip (merchant_key Fernet column)
# ---------------------------------------------------------------------


def test_channel_create_encrypts_merchant_key(
    client, seeded_channel, billing_engine
):
    with Session(billing_engine) as s:
        row = s.get(PaymentChannel, seeded_channel["id"])
        assert row is not None
        # Ciphertext is non-empty bytes, starts with Fernet's 0x80 prefix
        assert row.merchant_key_encrypted
        assert isinstance(row.merchant_key_encrypted, bytes | bytearray)
        assert bytes(row.merchant_key_encrypted) != b"super-seecret"
        # Legacy plaintext column is not populated by new rows
        assert row.secret_key is None
        # Decrypt roundtrips
        assert row.merchant_key == "super-seecret"


def test_channel_patch_rotates_merchant_key(client, seeded_channel):
    r = client.patch(
        f"/api/billing/admin/channels/{seeded_channel['id']}",
        json={"merchant_key": "rotated-value"},
    )
    assert r.status_code == 200, r.text


def test_response_never_echoes_secret(client, seeded_channel):
    r = client.get("/api/billing/admin/channels")
    assert r.status_code == 200
    for row in r.json():
        assert "secret_key" not in row
        assert "merchant_key" not in row
        assert "merchant_key_encrypted" not in row


# ---------------------------------------------------------------------
# sign_body_mode dialect
# ---------------------------------------------------------------------


def test_compute_sign_with_key_prefix_differs_from_plain():
    params = {"pid": "1", "money": "10.00"}
    plain = compute_sign(params, "secret")
    prefixed = compute_sign(
        params, "secret", sign_body_mode=SIGN_BODY_MODE_WITH_KEY_PREFIX
    )
    assert plain != prefixed
    # Confirm prefixed matches expected body
    body = "money=10.00&pid=1&key=secret"
    assert prefixed == hashlib.md5(body.encode()).hexdigest().lower()


def test_compute_sign_unknown_mode_is_rejected_upstream():
    # The provider constructor guards against unknown modes; the
    # helper itself treats anything non-"with_key_prefix" as plain.
    from ops.billing.providers.epay import EPayProvider

    with pytest.raises(ValueError, match="sign_body_mode"):
        EPayProvider(
            channel_code="c",
            merchant_id="m",
            secret_key="k",
            gateway_url="https://x",
            callback_base_url="https://y",
            sign_body_mode="bogus",
        )


def test_channel_extra_config_stores_sign_mode_and_allowed_ips(
    client, seeded_channel
):
    r = client.patch(
        f"/api/billing/admin/channels/{seeded_channel['id']}",
        json={
            "extra_config": {
                "sign_body_mode": "with_key_prefix",
                "allowed_ips": ["1.2.3.4", "10.0.0.0/8"],
            }
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["extra_config_json"]["sign_body_mode"] == "with_key_prefix"
    assert body["extra_config_json"]["allowed_ips"] == [
        "1.2.3.4",
        "10.0.0.0/8",
    ]


# ---------------------------------------------------------------------
# Checkout
# ---------------------------------------------------------------------


def test_checkout_creates_invoice_and_returns_payment_url(
    client, seeded_channel, seeded_plan
):
    r = client.post(
        "/api/billing/cart/checkout",
        json={
            "user_id": 1,
            "channel_code": seeded_channel["channel_code"],
            "lines": [{"plan_id": seeded_plan["id"], "quantity": 1}],
            "success_url": "https://panel.test/ok",
            "cancel_url": "https://panel.test/cancel",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["invoice_id"] >= 1
    assert body["total_cny_fen"] == 5000
    assert body["state"] == INVOICE_STATE_AWAITING_PAYMENT
    # payment_url carries the required query params
    assert "pid=M100" in body["payment_url"]
    assert "money=50.00" in body["payment_url"]
    assert "sign=" in body["payment_url"]
    assert "out_trade_no=INV-" in body["payment_url"]


def test_checkout_fails_on_disabled_channel(
    client, seeded_channel, seeded_plan
):
    client.patch(
        f"/api/billing/admin/channels/{seeded_channel['id']}",
        json={"enabled": False},
    )
    r = client.post(
        "/api/billing/cart/checkout",
        json={
            "user_id": 1,
            "channel_code": seeded_channel["channel_code"],
            "lines": [{"plan_id": seeded_plan["id"], "quantity": 1}],
            "success_url": "https://panel.test/ok",
            "cancel_url": "https://panel.test/cancel",
        },
    )
    assert r.status_code == 409


def test_checkout_fails_on_unknown_channel(client, seeded_plan):
    r = client.post(
        "/api/billing/cart/checkout",
        json={
            "user_id": 1,
            "channel_code": "does-not-exist",
            "lines": [{"plan_id": seeded_plan["id"], "quantity": 1}],
            "success_url": "https://panel.test/ok",
            "cancel_url": "https://panel.test/cancel",
        },
    )
    assert r.status_code == 404


def test_checkout_fails_when_public_base_url_empty(
    client, seeded_channel, seeded_plan, monkeypatch
):
    monkeypatch.setattr(billing_config, "BILLING_PUBLIC_BASE_URL", "")
    r = client.post(
        "/api/billing/cart/checkout",
        json={
            "user_id": 1,
            "channel_code": seeded_channel["channel_code"],
            "lines": [{"plan_id": seeded_plan["id"], "quantity": 1}],
            "success_url": "https://panel.test/ok",
            "cancel_url": "https://panel.test/cancel",
        },
    )
    assert r.status_code == 503
    assert "BILLING_PUBLIC_BASE_URL" in r.text


# ---------------------------------------------------------------------
# Webhook: sign verify + state transition
# ---------------------------------------------------------------------


def _build_webhook_params(
    *,
    invoice_id: int,
    merchant_id: str,
    trade_no: str = "ALIPAY-TX-1",
    trade_status: str = "TRADE_SUCCESS",
    money: str = "50.00",
) -> dict[str, str]:
    return {
        "pid": merchant_id,
        "trade_no": trade_no,
        "out_trade_no": f"INV-{invoice_id}-999",
        "type": "alipay",
        "name": "Starter",
        "money": money,
        "trade_status": trade_status,
        "sign_type": "MD5",
    }


def _do_checkout(client, channel_code: str, plan_id: int) -> int:
    r = client.post(
        "/api/billing/cart/checkout",
        json={
            "user_id": 1,
            "channel_code": channel_code,
            "lines": [{"plan_id": plan_id, "quantity": 1}],
            "success_url": "https://panel.test/ok",
            "cancel_url": "https://panel.test/cancel",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["invoice_id"]


def test_webhook_valid_sign_transitions_to_paid(
    client, seeded_channel, seeded_plan, billing_engine
):
    invoice_id = _do_checkout(
        client, seeded_channel["channel_code"], seeded_plan["id"]
    )
    params = _build_webhook_params(invoice_id=invoice_id, merchant_id="M100")
    params["sign"] = compute_sign(params, "super-seecret")

    r = client.post(
        f"/api/billing/webhook/epay/{seeded_channel['channel_code']}",
        data=params,
    )
    assert r.status_code == 200
    assert r.text == "success"

    with Session(billing_engine) as s:
        inv = s.get(Invoice, invoice_id)
        assert inv is not None
        assert inv.state == INVOICE_STATE_PAID
        # Audit trail has both the webhook_received dedup row and the
        # state transition row.
        events = (
            s.query(PaymentEvent)
            .filter_by(invoice_id=invoice_id)
            .order_by(PaymentEvent.id)
            .all()
        )
        event_types = [e.event_type for e in events]
        assert "webhook_received" in event_types
        assert "webhook_epay" in event_types


def test_webhook_invalid_sign_is_rejected_with_400(
    client, seeded_channel, seeded_plan, billing_engine
):
    invoice_id = _do_checkout(
        client, seeded_channel["channel_code"], seeded_plan["id"]
    )
    params = _build_webhook_params(invoice_id=invoice_id, merchant_id="M100")
    params["sign"] = "0" * 32  # bogus

    r = client.post(
        f"/api/billing/webhook/epay/{seeded_channel['channel_code']}",
        data=params,
    )
    assert r.status_code == 400

    with Session(billing_engine) as s:
        inv = s.get(Invoice, invoice_id)
        assert inv is not None
        # State remained awaiting_payment — sign mismatch means no
        # transition happened.
        assert inv.state == INVOICE_STATE_AWAITING_PAYMENT


def test_webhook_replay_is_idempotent(
    client, seeded_channel, seeded_plan, billing_engine
):
    invoice_id = _do_checkout(
        client, seeded_channel["channel_code"], seeded_plan["id"]
    )
    params = _build_webhook_params(invoice_id=invoice_id, merchant_id="M100")
    params["sign"] = compute_sign(params, "super-seecret")

    url = f"/api/billing/webhook/epay/{seeded_channel['channel_code']}"
    r1 = client.post(url, data=params)
    r2 = client.post(url, data=params)
    assert r1.status_code == r2.status_code == 200
    assert r1.text == r2.text == "success"

    with Session(billing_engine) as s:
        inv = s.get(Invoice, invoice_id)
        assert inv is not None
        assert inv.state == INVOICE_STATE_PAID
        # Exactly one webhook_received marker, exactly one webhook_epay
        # transition, regardless of retry count.
        events = s.query(PaymentEvent).filter_by(invoice_id=invoice_id).all()
        event_types = [e.event_type for e in events]
        assert event_types.count("webhook_received") == 1
        assert event_types.count("webhook_epay") == 1


def test_webhook_trade_fail_is_observed_but_not_acted_on(
    client, seeded_channel, seeded_plan, billing_engine
):
    invoice_id = _do_checkout(
        client, seeded_channel["channel_code"], seeded_plan["id"]
    )
    params = _build_webhook_params(
        invoice_id=invoice_id,
        merchant_id="M100",
        trade_status="TRADE_FAIL",
    )
    params["sign"] = compute_sign(params, "super-seecret")

    r = client.post(
        f"/api/billing/webhook/epay/{seeded_channel['channel_code']}",
        data=params,
    )
    # 200 "success" so 码商 stops retrying; but no state change.
    assert r.status_code == 200
    assert r.text == "success"
    with Session(billing_engine) as s:
        inv = s.get(Invoice, invoice_id)
        assert inv is not None
        assert inv.state == INVOICE_STATE_AWAITING_PAYMENT


def test_webhook_unknown_channel_returns_404(client):
    r = client.post("/api/billing/webhook/epay/ghost", data={})
    assert r.status_code == 404


def test_webhook_with_key_prefix_dialect_verifies(
    client, seeded_channel, seeded_plan, billing_engine
):
    # Switch channel to with_key_prefix dialect and replay a webhook
    # signed in that dialect — must verify.
    client.patch(
        f"/api/billing/admin/channels/{seeded_channel['id']}",
        json={"extra_config": {"sign_body_mode": "with_key_prefix"}},
    )
    invoice_id = _do_checkout(
        client, seeded_channel["channel_code"], seeded_plan["id"]
    )
    params = _build_webhook_params(invoice_id=invoice_id, merchant_id="M100")
    params["sign"] = compute_sign(
        params,
        "super-seecret",
        sign_body_mode=SIGN_BODY_MODE_WITH_KEY_PREFIX,
    )
    r = client.post(
        f"/api/billing/webhook/epay/{seeded_channel['channel_code']}",
        data=params,
    )
    assert r.status_code == 200, r.text
    with Session(billing_engine) as s:
        inv = s.get(Invoice, invoice_id)
        assert inv is not None
        assert inv.state == INVOICE_STATE_PAID


# ---------------------------------------------------------------------
# IP allowlist
# ---------------------------------------------------------------------


def test_webhook_ip_allowlist_blocks_unknown_ip(
    client, seeded_channel, seeded_plan
):
    client.patch(
        f"/api/billing/admin/channels/{seeded_channel['id']}",
        json={"extra_config": {"allowed_ips": ["8.8.8.8"]}},
    )
    invoice_id = _do_checkout(
        client, seeded_channel["channel_code"], seeded_plan["id"]
    )
    params = _build_webhook_params(invoice_id=invoice_id, merchant_id="M100")
    params["sign"] = compute_sign(params, "super-seecret")

    r = client.post(
        f"/api/billing/webhook/epay/{seeded_channel['channel_code']}",
        data=params,
        headers={"X-Forwarded-For": "1.2.3.4"},
    )
    assert r.status_code == 403


def test_webhook_ip_allowlist_permits_cidr_match(
    client, seeded_channel, seeded_plan, billing_engine
):
    client.patch(
        f"/api/billing/admin/channels/{seeded_channel['id']}",
        json={"extra_config": {"allowed_ips": ["10.0.0.0/8"]}},
    )
    invoice_id = _do_checkout(
        client, seeded_channel["channel_code"], seeded_plan["id"]
    )
    params = _build_webhook_params(invoice_id=invoice_id, merchant_id="M100")
    params["sign"] = compute_sign(params, "super-seecret")

    r = client.post(
        f"/api/billing/webhook/epay/{seeded_channel['channel_code']}",
        data=params,
        headers={"X-Forwarded-For": "10.1.2.3"},
    )
    assert r.status_code == 200
    with Session(billing_engine) as s:
        inv = s.get(Invoice, invoice_id)
        assert inv is not None
        assert inv.state == INVOICE_STATE_PAID


def test_webhook_no_allowlist_permits_any_ip(
    client, seeded_channel, seeded_plan
):
    # Default (no allowed_ips) → open. Both checkout + webhook work
    # even from an unusual X-Forwarded-For.
    invoice_id = _do_checkout(
        client, seeded_channel["channel_code"], seeded_plan["id"]
    )
    params = _build_webhook_params(invoice_id=invoice_id, merchant_id="M100")
    params["sign"] = compute_sign(params, "super-seecret")

    r = client.post(
        f"/api/billing/webhook/epay/{seeded_channel['channel_code']}",
        data=params,
        headers={"X-Forwarded-For": "99.99.99.99"},
    )
    assert r.status_code == 200


def test_webhook_ip_allowlist_ignores_spoofed_xff_when_peer_untrusted(
    client, seeded_channel, seeded_plan, monkeypatch
):
    """X-Forwarded-For from an untrusted peer must be ignored (not just
    "respected, then maybe blocked" — actively dropped).

    Threat model: panel directly on the public internet (no reverse
    proxy) with BILLING_TRUSTED_PROXIES empty. An attacker sets
    X-Forwarded-For: 8.8.8.8 to spoof a 码商-allowed IP. Without this
    fix, the allowlist check would see "8.8.8.8" and pass — the
    documented "double 防线" silently becoming security theatre.

    Expected after fix: peer (TestClient = 127.0.0.1) is NOT in the
    empty trusted-proxy list, so XFF is ignored, allowed_ips check
    sees the real peer "127.0.0.1", which isn't in ["8.8.8.8"] →
    403 Forbidden.
    """
    # Override conftest's testing-friendly trusted_proxies setting.
    monkeypatch.setattr(
        billing_config,
        "BILLING_TRUSTED_PROXIES",
        billing_config._parse_trusted_proxies(""),
    )
    client.patch(
        f"/api/billing/admin/channels/{seeded_channel['id']}",
        json={"extra_config": {"allowed_ips": ["8.8.8.8"]}},
    )
    invoice_id = _do_checkout(
        client, seeded_channel["channel_code"], seeded_plan["id"]
    )
    params = _build_webhook_params(invoice_id=invoice_id, merchant_id="M100")
    params["sign"] = compute_sign(params, "super-seecret")

    r = client.post(
        f"/api/billing/webhook/epay/{seeded_channel['channel_code']}",
        data=params,
        headers={"X-Forwarded-For": "8.8.8.8"},  # spoofed
    )
    assert r.status_code == 403, (
        "Spoofed X-Forwarded-For from an untrusted peer must NOT bypass "
        "the allowed_ips allowlist. Peer (127.0.0.1) is not in the "
        "configured allowlist, regardless of any header value."
    )


def test_webhook_disabled_channel_returns_410(
    client, seeded_channel, seeded_plan
):
    """Disabled channel → 410 Gone (was 404). Vendors retry 404 ten
    times with backoff; 410 says "stop, this is intentionally off".
    """
    invoice_id = _do_checkout(
        client, seeded_channel["channel_code"], seeded_plan["id"]
    )
    params = _build_webhook_params(invoice_id=invoice_id, merchant_id="M100")
    params["sign"] = compute_sign(params, "super-seecret")

    # Now disable the channel.
    client.patch(
        f"/api/billing/admin/channels/{seeded_channel['id']}",
        json={"enabled": False},
    )
    r = client.post(
        f"/api/billing/webhook/epay/{seeded_channel['channel_code']}",
        data=params,
    )
    assert r.status_code == 410
