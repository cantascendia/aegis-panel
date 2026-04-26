"""Unit tests for the EPay payment provider adapter."""

from __future__ import annotations

import hashlib
import time
from typing import Any

import pytest

from ops.billing.providers import get_provider
from ops.billing.providers.base import (
    BasePaymentProvider,
    CreateInvoiceResult,
    InvalidSignature,
    UnhandledEventType,
    WebhookOutcome,
)
from ops.billing.providers.epay import (
    EPAY_TRADE_SUCCESS,
    EPayProvider,
    compute_sign,
)

# ---------------------------------------------------------------------
# compute_sign — wire-compatible with SSPanel/Xboard/v2board
# ---------------------------------------------------------------------


def test_compute_sign_matches_reference_fixture() -> None:
    # Reference vector derived from the 易支付 protocol spec + common
    # implementations. Reproducible by hand:
    #   body = "money=10.00&name=Plan&out_trade_no=INV-1-100&pid=123&
    #           return_url=https://x/ok&type=alipay" + "secret"
    params = {
        "pid": "123",
        "type": "alipay",
        "out_trade_no": "INV-1-100",
        "notify_url": "https://x/notify",
        "return_url": "https://x/ok",
        "name": "Plan",
        "money": "10.00",
        "sign_type": "MD5",
    }
    secret = "secret"

    body = (
        "money=10.00"
        "&name=Plan"
        "&notify_url=https://x/notify"
        "&out_trade_no=INV-1-100"
        "&pid=123"
        "&return_url=https://x/ok"
        "&type=alipay"
    ) + secret
    expected = hashlib.md5(body.encode()).hexdigest().lower()

    assert compute_sign(params, secret) == expected


def test_compute_sign_drops_empty_values() -> None:
    # Empty-string fields must NOT participate in the sign body.
    params_with_empty = {"pid": "1", "money": "5.00", "remark": ""}
    params_without = {"pid": "1", "money": "5.00"}

    assert compute_sign(params_with_empty, "k") == compute_sign(
        params_without, "k"
    )


def test_compute_sign_excludes_sign_and_sign_type_themselves() -> None:
    # The sign field is computed; if we include it we'd infinite-loop.
    base = {"pid": "1", "money": "5.00"}
    with_sign_fields = {
        **base,
        "sign": "whatever",
        "sign_type": "MD5",
    }

    assert compute_sign(with_sign_fields, "k") == compute_sign(base, "k")


def test_compute_sign_order_independence() -> None:
    # Same params, inserted in different orders, must sign identically.
    a = {"pid": "1", "money": "5.00", "name": "x"}
    b = {"name": "x", "money": "5.00", "pid": "1"}

    assert compute_sign(a, "k") == compute_sign(b, "k")


# ---------------------------------------------------------------------
# create_invoice — payment URL shape
# ---------------------------------------------------------------------


@pytest.fixture
def epay() -> EPayProvider:
    return EPayProvider(
        channel_code="zpay1",
        merchant_id="1001",
        secret_key="s3cret",
        gateway_url="https://pay.example.com",
        callback_base_url="https://panel.example.com",
    )


@pytest.mark.asyncio
async def test_create_invoice_produces_signed_submit_url(
    epay: EPayProvider,
) -> None:
    result = await epay.create_invoice(
        invoice_id=42,
        amount_cny_fen=8800,
        subject="Pro plan",
        success_url="https://panel.example.com/billing/success",
        cancel_url="https://panel.example.com/billing",
    )

    assert isinstance(result, CreateInvoiceResult)
    assert result.provider_invoice_id.startswith("INV-42-")
    assert result.payment_url.startswith("https://pay.example.com/submit.php?")
    # All required params present
    for required in (
        "pid=1001",
        "money=88.00",
        "type=alipay",
        "sign=",
        "sign_type=MD5",
    ):
        assert (
            required in result.payment_url
        ), f"missing {required} in {result.payment_url}"
    # notify_url baked with channel_code
    assert "notify_url=" in result.payment_url
    assert "zpay1" in result.payment_url


@pytest.mark.asyncio
async def test_create_invoice_money_formatting_integer_math(
    epay: EPayProvider,
) -> None:
    # 9999 fen should be "99.99" — no float drift.
    result = await epay.create_invoice(
        invoice_id=1,
        amount_cny_fen=9999,
        subject="x",
        success_url="https://x/s",
        cancel_url="https://x/c",
    )
    assert "money=99.99" in result.payment_url

    # 100 fen should be "1.00" (not "1.0" or "1")
    result2 = await epay.create_invoice(
        invoice_id=2,
        amount_cny_fen=100,
        subject="x",
        success_url="https://x/s",
        cancel_url="https://x/c",
    )
    assert "money=1.00" in result2.payment_url


@pytest.mark.asyncio
async def test_create_invoice_rejects_negative_amount(
    epay: EPayProvider,
) -> None:
    with pytest.raises(ValueError, match="non-negative"):
        await epay.create_invoice(
            invoice_id=1,
            amount_cny_fen=-100,
            subject="x",
            success_url="https://x/s",
            cancel_url="https://x/c",
        )


# ---------------------------------------------------------------------
# handle_webhook — verification + parsing
# ---------------------------------------------------------------------


def _sign_payload(params: dict[str, str], secret: str) -> dict[str, str]:
    """Helper: produce a webhook-shaped payload with valid sign."""
    signed = dict(params)
    signed["sign"] = compute_sign(signed, secret)
    signed.setdefault("sign_type", "MD5")
    return signed


@pytest.mark.asyncio
async def test_webhook_accepts_trade_success_and_returns_outcome(
    epay: EPayProvider,
) -> None:
    params = _sign_payload(
        {
            "pid": "1001",
            "trade_no": "TRADE-XYZ-999",
            "out_trade_no": "INV-42-1700000000",
            "type": "alipay",
            "name": "Pro plan",
            "money": "88.00",
            "trade_status": EPAY_TRADE_SUCCESS,
        },
        "s3cret",
    )

    outcome = await epay.handle_webhook(params, raw_body=b"")

    assert isinstance(outcome, WebhookOutcome)
    assert outcome.invoice_id == 42
    assert outcome.new_state == "paid"
    assert outcome.provider_event_id == "TRADE-XYZ-999"
    assert outcome.raw["trade_status"] == EPAY_TRADE_SUCCESS


@pytest.mark.asyncio
async def test_webhook_rejects_bad_signature(epay: EPayProvider) -> None:
    params = _sign_payload(
        {
            "pid": "1001",
            "trade_no": "T1",
            "out_trade_no": "INV-1-1",
            "money": "10.00",
            "trade_status": EPAY_TRADE_SUCCESS,
        },
        "s3cret",
    )
    # Tamper with money after signing
    params["money"] = "0.01"

    with pytest.raises(InvalidSignature):
        await epay.handle_webhook(params, raw_body=b"")


@pytest.mark.asyncio
async def test_webhook_missing_sign_field_rejected(
    epay: EPayProvider,
) -> None:
    params = {
        "pid": "1001",
        "trade_no": "T1",
        "out_trade_no": "INV-1-1",
        "trade_status": EPAY_TRADE_SUCCESS,
    }  # no 'sign'

    with pytest.raises(InvalidSignature, match="missing sign"):
        await epay.handle_webhook(params, raw_body=b"")


@pytest.mark.asyncio
async def test_webhook_trade_fail_raises_unhandled_not_invalid(
    epay: EPayProvider,
) -> None:
    # This path distinguishes "bad signature = reject"
    # from "we understand but ignore".
    params = _sign_payload(
        {
            "pid": "1001",
            "trade_no": "T1",
            "out_trade_no": "INV-1-1",
            "money": "10.00",
            "trade_status": "TRADE_FAIL",
        },
        "s3cret",
    )

    with pytest.raises(UnhandledEventType):
        await epay.handle_webhook(params, raw_body=b"")


@pytest.mark.asyncio
async def test_webhook_missing_trade_no_rejected(epay: EPayProvider) -> None:
    params = _sign_payload(
        {
            "pid": "1001",
            "out_trade_no": "INV-1-1",
            "money": "10.00",
            "trade_status": EPAY_TRADE_SUCCESS,
            # no trade_no — some 码商 might swap fields; we reject.
        },
        "s3cret",
    )

    with pytest.raises(InvalidSignature, match="trade_no"):
        await epay.handle_webhook(params, raw_body=b"")


@pytest.mark.asyncio
async def test_webhook_malformed_out_trade_no_rejected(
    epay: EPayProvider,
) -> None:
    params = _sign_payload(
        {
            "pid": "1001",
            "trade_no": "T1",
            "out_trade_no": "garbage-not-INV-prefixed",
            "money": "10.00",
            "trade_status": EPAY_TRADE_SUCCESS,
        },
        "s3cret",
    )

    with pytest.raises(InvalidSignature, match="INV-"):
        await epay.handle_webhook(params, raw_body=b"")


# ---------------------------------------------------------------------
# get_provider factory
# ---------------------------------------------------------------------


class _StubChannel:
    """Minimal stand-in for PaymentChannel in factory tests."""

    def __init__(self, **kw: Any) -> None:
        self.channel_code = kw.get("channel_code", "zpay1")
        self.merchant_id = kw.get("merchant_id", "1001")
        self.secret_key = kw.get("secret_key", "s3cret")
        self.merchant_key_encrypted = kw.get("merchant_key_encrypted", None)
        self.gateway_url = kw.get("gateway_url", "https://pay.example.com")
        self.extra_config_json = kw.get("extra_config_json", None)

    @property
    def merchant_key(self) -> str:
        # Stub mirrors PaymentChannel.merchant_key: prefer the
        # (normally encrypted) column, fall back to plaintext.
        return self.secret_key or ""

    def get_extra_config(self, key: str, default: Any = None) -> Any:
        if not self.extra_config_json:
            return default
        return self.extra_config_json.get(key, default)


def test_get_provider_returns_epay_for_epay_kind() -> None:
    provider = get_provider(
        "epay",
        _StubChannel(),
        callback_base_url="https://panel.example.com",
    )
    assert isinstance(provider, EPayProvider)
    assert isinstance(provider, BasePaymentProvider)
    assert provider.kind == "epay"


def test_get_provider_epay_requires_channel() -> None:
    with pytest.raises(ValueError, match="requires a PaymentChannel"):
        get_provider("epay", None, callback_base_url="https://x")


def test_get_provider_epay_requires_callback_base() -> None:
    with pytest.raises(ValueError, match="callback_base_url"):
        get_provider("epay", _StubChannel())


def test_get_provider_trc20_disabled_raises_misconfigured() -> None:
    # As of A.3.1, the TRC20 provider exists but defaults to disabled.
    # Calling it without configuration must surface that loudly so an
    # operator who set kind="trc20" on a channel without env config
    # sees the gap at provider construction time, not at first checkout.
    from ops.billing.trc20_config import Trc20Misconfigured, _reload_for_tests

    _reload_for_tests(enabled=False)
    with pytest.raises(Trc20Misconfigured, match="not enabled"):
        get_provider("trc20")


def test_get_provider_unknown_kind_raises() -> None:
    with pytest.raises(ValueError, match="unknown payment provider kind"):
        get_provider("stripe")


# ---------------------------------------------------------------------
# Round-trip: create_invoice -> handle_webhook with faked 码商
# ---------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_invoice_then_webhook_round_trip(
    epay: EPayProvider,
) -> None:
    """Simulate the full flow: panel → 码商 submit → 码商 webhook → panel.

    The "码商" in this test is just us re-signing the payload we'd
    have sent. This pins the interop: the sign we computed on
    create_invoice would verify on handle_webhook if echoed back.
    """
    # 1. Panel creates an invoice
    _ = time.time  # kept for clarity
    result = await epay.create_invoice(
        invoice_id=77,
        amount_cny_fen=35_00,
        subject="Starter plan",
        success_url="https://panel.example.com/billing/success",
        cancel_url="https://panel.example.com/billing",
    )

    # 2. Extract the submitted params by parsing the URL the user was
    #    redirected to (in practice the 码商 receives these).
    from urllib.parse import parse_qs, urlsplit

    submitted = {
        k: v[0]
        for k, v in parse_qs(urlsplit(result.payment_url).query).items()
    }

    # 3. The 码商 would echo most params back + add trade_no,
    #    trade_status. We simulate that here.
    webhook_params = dict(submitted)
    webhook_params["trade_no"] = "TRADE-ABC-12345"
    webhook_params["trade_status"] = EPAY_TRADE_SUCCESS
    # Drop original sign, re-sign with 码商's key (which is our secret).
    webhook_params.pop("sign", None)
    webhook_params["sign"] = compute_sign(webhook_params, "s3cret")

    # 4. Webhook arrives, we verify + parse
    outcome = await epay.handle_webhook(webhook_params, raw_body=b"")

    assert outcome.invoice_id == 77
    assert outcome.provider_event_id == "TRADE-ABC-12345"
    assert outcome.new_state == "paid"
