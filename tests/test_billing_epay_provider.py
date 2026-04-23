from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest

from ops.billing.db import INVOICE_STATE_PAID
from ops.billing.providers import EPayProvider, get_provider
from ops.billing.providers.base import (
    InvalidProviderPayload,
    InvalidSignature,
    UnhandledEventType,
    UnknownProviderKind,
)
from ops.billing.providers.epay import (
    EPayConfig,
    compute_epay_sign,
    parse_epay_invoice_id,
)


def _provider(sign_body_mode: str = "plain") -> EPayProvider:
    return EPayProvider(
        EPayConfig(
            channel_code="zpay1",
            gateway_url="https://pay.example.test/",
            merchant_id="1001",
            merchant_key="secret",
            public_base_url="https://panel.example.test/",
            sign_body_mode=sign_body_mode,  # type: ignore[arg-type]
        )
    )


def test_epay_sign_matches_plain_reference() -> None:
    params = {
        "money": "88.00",
        "name": "Invoice #1",
        "notify_url": "https://panel.example.test/notify",
        "out_trade_no": "INV-1-1713772800",
        "pid": "1001",
        "return_url": "https://panel.example.test/ok",
        "sign": "ignored",
        "sign_type": "MD5",
        "type": "alipay",
        "empty": "",
    }

    assert (
        compute_epay_sign(params, "secret")
        == "69d4c75c148f65e035f2edf128d2feeb"
    )


def test_epay_sign_supports_key_prefix_reference() -> None:
    params = {
        "pid": "1001",
        "type": "alipay",
        "out_trade_no": "INV-1-1713772800",
        "money": "88.00",
    }

    assert (
        compute_epay_sign(params, "secret", sign_body_mode="with_key_prefix")
        == "f9886f703572bd8a66132ad57e706e3d"
    )


def test_epay_sign_rejects_unknown_mode() -> None:
    with pytest.raises(ValueError, match="unsupported EPay sign body mode"):
        compute_epay_sign(
            {"pid": "1001"},
            "secret",
            sign_body_mode="unknown",  # type: ignore[arg-type]
        )


@pytest.mark.asyncio
async def test_epay_create_invoice_url_has_required_params(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("ops.billing.providers.epay.time.time", lambda: 1234)

    result = await _provider().create_invoice(
        invoice_id=42,
        amount_cny_fen=880,
        subject="Starter plan",
        success_url="https://panel.example.test/success",
        cancel_url="https://panel.example.test/cancel",
    )

    parsed = urlparse(result.payment_url)
    params = {key: value[0] for key, value in parse_qs(parsed.query).items()}
    assert result.provider_invoice_id == "INV-42-1234"
    assert parsed.geturl().startswith("https://pay.example.test/submit.php?")
    assert params["pid"] == "1001"
    assert params["type"] == "alipay"
    assert params["out_trade_no"] == "INV-42-1234"
    assert params["money"] == "8.80"
    assert (
        params["notify_url"]
        == "https://panel.example.test/api/billing/webhook/epay/zpay1"
    )
    assert params["return_url"] == "https://panel.example.test/success"
    assert params["sign_type"] == "MD5"
    assert params["sign"] == compute_epay_sign(params, "secret")


@pytest.mark.asyncio
async def test_epay_create_invoice_rejects_zero_amount() -> None:
    with pytest.raises(ValueError, match="amount_cny_fen must be positive"):
        await _provider().create_invoice(
            invoice_id=42,
            amount_cny_fen=0,
            subject="Starter plan",
            success_url="https://panel.example.test/success",
            cancel_url="https://panel.example.test/cancel",
        )


@pytest.mark.asyncio
async def test_epay_webhook_valid_success_returns_paid_outcome() -> None:
    payload = {
        "pid": "1001",
        "trade_no": "REMOTE-123",
        "out_trade_no": "INV-42-1234",
        "trade_status": "TRADE_SUCCESS",
        "money": "8.80",
    }
    payload["sign"] = compute_epay_sign(payload, "secret")
    payload["sign_type"] = "MD5"

    outcome = await _provider().handle_webhook(payload, b"")

    assert outcome.invoice_id == 42
    assert outcome.new_state == INVOICE_STATE_PAID
    assert outcome.provider_event_id == "REMOTE-123"
    assert outcome.raw["out_trade_no"] == "INV-42-1234"


@pytest.mark.asyncio
async def test_epay_webhook_invalid_sign_raises() -> None:
    payload = {
        "pid": "1001",
        "out_trade_no": "INV-42-1234",
        "trade_status": "TRADE_SUCCESS",
        "sign": "bad",
    }

    with pytest.raises(InvalidSignature):
        await _provider().handle_webhook(payload, b"")


@pytest.mark.asyncio
async def test_epay_webhook_trade_fail_is_unhandled() -> None:
    payload = {
        "pid": "1001",
        "out_trade_no": "INV-42-1234",
        "trade_status": "TRADE_FAIL",
    }
    payload["sign"] = compute_epay_sign(payload, "secret")

    with pytest.raises(UnhandledEventType):
        await _provider().handle_webhook(payload, b"")


def test_parse_epay_invoice_id_rejects_malformed_value() -> None:
    with pytest.raises(InvalidProviderPayload):
        parse_epay_invoice_id("ORDER-42")


def test_get_provider_returns_epay_adapter() -> None:
    provider = get_provider(
        "epay",
        channel_code="zpay1",
        gateway_url="https://pay.example.test",
        merchant_id="1001",
        merchant_key="secret",
        public_base_url="https://panel.example.test",
    )

    assert isinstance(provider, EPayProvider)


def test_get_provider_rejects_unknown_kind() -> None:
    with pytest.raises(UnknownProviderKind):
        get_provider("stripe")
