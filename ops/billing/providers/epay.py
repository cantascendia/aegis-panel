"""易支付(EPay)protocol adapter.

Implements the generic 易支付 protocol used across the Chinese
airport market. Reference implementations live in SSPanel, Xboard,
and v2board; the wire format is stable across most 码商 aggregators
(~70% of vendors use the "plain" sign body format supported here).

A.2.1 ships only the plain sign mode. Dialect variants(``&key=``
body prefix, wxpay route, HMAC-SHA256 sign) are a future follow-up
once an actual 码商 surfaces the need — `OPS-epay-vendor-guide.md`
will document each variant observed in production.

Wire contract summary
---------------------

**Create invoice**(``submit.php``):

Required form fields, sorted by key ascii ascending, MD5-signed::

    pid             = merchant_id
    type            = "alipay"      (A.2.1 fixed; wxpay later)
    out_trade_no    = "INV-{invoice_id}-{ts_sec}"
    notify_url      = "{callback_base}/api/billing/webhook/epay/{channel_code}"
    return_url      = success_url
    name            = subject
    money           = "{amount_fen / 100:.2f}"
    sign            = md5(<sorted kv body> + secret_key).lower()
    sign_type       = "MD5"

**Webhook callback**: 码商 POSTs back with the same field set plus::

    trade_no        = 码商's own order id(our dedup key)
    trade_status    = "TRADE_SUCCESS" | "TRADE_FAIL" | ...

Signature verification uses the same algorithm, excluding ``sign``
and ``sign_type`` themselves.
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Mapping

from ops.billing.providers.base import (
    BasePaymentProvider,
    CreateInvoiceResult,
    InvalidSignature,
    UnhandledEventType,
    WebhookOutcome,
)

EPAY_TRADE_SUCCESS = "TRADE_SUCCESS"

# Keys excluded from signature computation(per protocol). Any other
# key present in the request participates.
_SIGN_EXCLUDED_KEYS = frozenset({"sign", "sign_type"})

# Sign-body dialects. ~70% of 码商 use "plain"; the rest prepend the
# literal string "&key=" before the secret. Channel rows pick via
# ``extra_config_json["sign_body_mode"]``.
SIGN_BODY_MODE_PLAIN = "plain"
SIGN_BODY_MODE_WITH_KEY_PREFIX = "with_key_prefix"
SIGN_BODY_MODES = (SIGN_BODY_MODE_PLAIN, SIGN_BODY_MODE_WITH_KEY_PREFIX)


class EPayProvider(BasePaymentProvider):
    """Generic 易支付 adapter. One instance per :class:`PaymentChannel`."""

    kind = "epay"

    def __init__(
        self,
        *,
        channel_code: str,
        merchant_id: str,
        secret_key: str,
        gateway_url: str,
        callback_base_url: str,
        sign_body_mode: str = SIGN_BODY_MODE_PLAIN,
    ) -> None:
        if sign_body_mode not in SIGN_BODY_MODES:
            raise ValueError(
                f"sign_body_mode must be one of {SIGN_BODY_MODES}, "
                f"got {sign_body_mode!r}"
            )
        self._channel_code = channel_code
        self._merchant_id = merchant_id
        self._secret_key = secret_key
        self._gateway_url = gateway_url.rstrip("/")
        self._callback_base_url = callback_base_url.rstrip("/")
        self._sign_body_mode = sign_body_mode

    async def create_invoice(
        self,
        invoice_id: int,
        amount_cny_fen: int,
        subject: str,
        success_url: str,
        cancel_url: str,
    ) -> CreateInvoiceResult:
        # ``cancel_url`` is unused by EPay proper — it redirects through
        # ``return_url`` on both success and cancel, and user state is
        # resolved by webhook. Keeping the parameter in the interface
        # for future providers that need it.
        _ = cancel_url

        out_trade_no = _build_out_trade_no(invoice_id)
        notify_url = (
            f"{self._callback_base_url}/api/billing/webhook/epay/"
            f"{self._channel_code}"
        )
        money = _format_money_from_fen(amount_cny_fen)

        params: dict[str, str] = {
            "pid": self._merchant_id,
            "type": "alipay",
            "out_trade_no": out_trade_no,
            "notify_url": notify_url,
            "return_url": success_url,
            "name": subject,
            "money": money,
            "sign_type": "MD5",
        }
        params["sign"] = compute_sign(
            params, self._secret_key, sign_body_mode=self._sign_body_mode
        )

        query = _urlencode_sorted(params)
        payment_url = f"{self._gateway_url}/submit.php?{query}"

        return CreateInvoiceResult(
            provider_invoice_id=out_trade_no,
            payment_url=payment_url,
            extra_payload={
                "channel_code": self._channel_code,
                "notify_url": notify_url,
                "money": money,
            },
        )

    async def handle_webhook(
        self,
        params: Mapping[str, str],
        raw_body: bytes,
    ) -> WebhookOutcome:
        # EPay webhooks arrive as application/x-www-form-urlencoded.
        # We treat ``params`` as the canonical view;``raw_body`` is
        # captured in case a 码商 ever switches to JSON and we need to
        # diff formats.
        _ = raw_body

        received_sign = params.get("sign")
        if not received_sign:
            raise InvalidSignature("webhook missing sign field")

        expected = compute_sign(
            params, self._secret_key, sign_body_mode=self._sign_body_mode
        )
        # Constant-time comparison — sign is 32 hex chars, minimal cost.
        if not _constant_time_equals(received_sign, expected):
            raise InvalidSignature(
                f"webhook sign mismatch for channel {self._channel_code!r}"
            )

        trade_status = params.get("trade_status")
        if trade_status != EPAY_TRADE_SUCCESS:
            raise UnhandledEventType(
                f"trade_status {trade_status!r} not actionable"
            )

        out_trade_no = params.get("out_trade_no")
        if not out_trade_no:
            raise InvalidSignature("webhook missing out_trade_no")

        invoice_id = _parse_invoice_id(out_trade_no)

        trade_no = params.get("trade_no")
        if not trade_no:
            # Some 码商 use ``trade_id`` or similar; surface the failure
            # explicitly rather than silently deduping on empty strings.
            raise InvalidSignature("webhook missing trade_no")

        return WebhookOutcome(
            invoice_id=invoice_id,
            new_state="paid",
            provider_event_id=trade_no,
            raw=dict(params),
        )


# ---------------------------------------------------------------------
# Helpers(module-level so tests can import + fuzz them directly)
# ---------------------------------------------------------------------


def compute_sign(
    params: Mapping[str, str],
    secret_key: str,
    *,
    sign_body_mode: str = SIGN_BODY_MODE_PLAIN,
) -> str:
    """Compute the 易支付 MD5 signature.

    Algorithm(common core across SSPanel / Xboard / v2board):

    1. Exclude ``sign`` and ``sign_type``; drop empty-string values.
    2. Sort remaining keys ascending.
    3. Join as ``k1=v1&k2=v2&...``.
    4. Append secret. Two wire dialects observed:

       - ``plain`` (default, ~70%): ``body + secret_key``
       - ``with_key_prefix``: ``body + "&key=" + secret_key``

       Dialect is per-channel (``PaymentChannel.extra_config_json
       ["sign_body_mode"]``); the provider passes it through here.
    5. MD5 hexdigest, lowercase.
    """

    filtered = {
        k: v
        for k, v in params.items()
        if k not in _SIGN_EXCLUDED_KEYS and v != ""
    }
    sorted_items = sorted(filtered.items())
    body = "&".join(f"{k}={v}" for k, v in sorted_items)
    if sign_body_mode == SIGN_BODY_MODE_WITH_KEY_PREFIX:
        body += f"&key={secret_key}"
    else:
        body += secret_key
    return hashlib.md5(body.encode("utf-8")).hexdigest().lower()


def _build_out_trade_no(invoice_id: int) -> str:
    # Timestamp suffix defeats duplicate out_trade_no when a user
    # retries checkout on a stale invoice that the 码商 already saw.
    # Panel-side dedup is invoice_id; 码商-side dedup is out_trade_no
    # so we need both to be unique per attempt.
    return f"INV-{invoice_id}-{int(time.time())}"


def _parse_invoice_id(out_trade_no: str) -> int:
    parts = out_trade_no.split("-")
    if len(parts) < 2 or parts[0] != "INV":
        raise InvalidSignature(
            f"out_trade_no {out_trade_no!r} does not match INV-<id>-<ts>"
        )
    try:
        return int(parts[1])
    except ValueError as exc:
        raise InvalidSignature(
            f"out_trade_no {out_trade_no!r} has non-integer invoice id"
        ) from exc


def _format_money_from_fen(amount_cny_fen: int) -> str:
    if amount_cny_fen < 0:
        raise ValueError("amount_cny_fen must be non-negative")
    # Two-decimal CNY string, required by the protocol.
    # Integer math to avoid float drift on amounts like 9999 fen.
    yuan, fen = divmod(amount_cny_fen, 100)
    return f"{yuan}.{fen:02d}"


def _urlencode_sorted(params: Mapping[str, str]) -> str:
    from urllib.parse import quote

    return "&".join(
        f"{k}={quote(str(v), safe='')}" for k, v in sorted(params.items())
    )


def _constant_time_equals(a: str, b: str) -> bool:
    # hashlib doesn't give us compare_digest at module scope without
    # hmac; use hmac's since both sides are short hex strings.
    import hmac

    return hmac.compare_digest(a, b)
