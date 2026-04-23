"""EPay provider adapter.

This module implements the common SSPanel/Xboard-style EPay protocol:
MD5-signed submit parameters and MD5-signed asynchronous webhook
callbacks.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlencode

from ops.billing.db import INVOICE_STATE_PAID
from ops.billing.providers.base import (
    BasePaymentProvider,
    CreateInvoiceResult,
    InvalidProviderPayload,
    InvalidSignature,
    UnhandledEventType,
    WebhookOutcome,
)

SignBodyMode = Literal["plain", "with_key_prefix"]

_INVOICE_ID_RE = re.compile(r"^INV-(?P<invoice_id>\d+)-\d+$")


@dataclass(frozen=True)
class EPayConfig:
    """Runtime configuration for one EPay channel."""

    channel_code: str
    gateway_url: str
    merchant_id: str
    merchant_key: str
    public_base_url: str
    payment_method: str = "alipay"
    sign_body_mode: SignBodyMode = "plain"


class EPayProvider(BasePaymentProvider):
    """Adapter for common EPay-compatible payment gateways."""

    def __init__(self, config: EPayConfig) -> None:
        self._config = config

    async def create_invoice(
        self,
        invoice_id: int,
        amount_cny_fen: int,
        subject: str,
        success_url: str,
        cancel_url: str,
    ) -> CreateInvoiceResult:
        _ = cancel_url
        out_trade_no = f"INV-{invoice_id}-{int(time.time())}"
        params = {
            "pid": self._config.merchant_id,
            "type": self._config.payment_method,
            "out_trade_no": out_trade_no,
            "notify_url": _join_url(
                self._config.public_base_url,
                f"/api/billing/webhook/epay/{self._config.channel_code}",
            ),
            "return_url": success_url,
            "name": subject,
            "money": _format_money(amount_cny_fen),
            "sign_type": "MD5",
        }
        params["sign"] = compute_epay_sign(
            params,
            self._config.merchant_key,
            sign_body_mode=self._config.sign_body_mode,
        )
        payment_url = _join_url(self._config.gateway_url, "/submit.php")
        payment_url = f"{payment_url}?{urlencode(params)}"
        return CreateInvoiceResult(
            provider_invoice_id=out_trade_no,
            payment_url=payment_url,
            extra_payload={
                "provider": f"epay:{self._config.channel_code}",
                "out_trade_no": out_trade_no,
                "submit_params": dict(params),
            },
        )

    async def handle_webhook(
        self, params: Mapping[str, str], raw_body: bytes
    ) -> WebhookOutcome:
        _ = raw_body
        payload = {key: str(value) for key, value in params.items()}
        received_sign = payload.get("sign")
        if not received_sign:
            raise InvalidSignature("missing EPay sign")

        computed_sign = compute_epay_sign(
            payload,
            self._config.merchant_key,
            sign_body_mode=self._config.sign_body_mode,
        )
        if not hmac.compare_digest(received_sign.lower(), computed_sign):
            raise InvalidSignature("invalid EPay sign")

        trade_status = payload.get("trade_status")
        if trade_status != "TRADE_SUCCESS":
            raise UnhandledEventType(f"unhandled EPay status {trade_status!r}")

        out_trade_no = payload.get("out_trade_no")
        if not out_trade_no:
            raise InvalidProviderPayload("missing out_trade_no")
        invoice_id = parse_epay_invoice_id(out_trade_no)
        provider_event_id = payload.get("trade_no") or out_trade_no
        return WebhookOutcome(
            invoice_id=invoice_id,
            new_state=INVOICE_STATE_PAID,
            provider_event_id=provider_event_id,
            raw=payload,
        )


def compute_epay_sign(
    params: Mapping[str, str],
    merchant_key: str,
    *,
    sign_body_mode: SignBodyMode = "plain",
) -> str:
    """Compute EPay MD5 signature over sorted non-empty parameters."""

    filtered = {
        key: str(value)
        for key, value in params.items()
        if key not in ("sign", "sign_type") and str(value) != ""
    }
    body = "&".join(
        f"{key}={value}" for key, value in sorted(filtered.items())
    )
    if sign_body_mode == "plain":
        body = f"{body}&{merchant_key}" if body else merchant_key
    elif sign_body_mode == "with_key_prefix":
        body = f"{body}&key={merchant_key}" if body else f"key={merchant_key}"
    else:
        raise ValueError(f"unsupported EPay sign body mode {sign_body_mode!r}")
    return hashlib.md5(body.encode("utf-8")).hexdigest().lower()


def parse_epay_invoice_id(out_trade_no: str) -> int:
    match = _INVOICE_ID_RE.match(out_trade_no)
    if not match:
        raise InvalidProviderPayload(f"invalid out_trade_no {out_trade_no!r}")
    return int(match.group("invoice_id"))


def _format_money(amount_cny_fen: int) -> str:
    if amount_cny_fen <= 0:
        raise ValueError("amount_cny_fen must be positive")
    return f"{amount_cny_fen / 100:.2f}"


def _join_url(base: str, path: str) -> str:
    return f"{base.rstrip('/')}/{path.lstrip('/')}"


__all__ = [
    "EPayConfig",
    "EPayProvider",
    "SignBodyMode",
    "compute_epay_sign",
    "parse_epay_invoice_id",
]
