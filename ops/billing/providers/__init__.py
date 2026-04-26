"""Payment provider adapters for the billing layer.

This subpackage hosts :class:`BasePaymentProvider` and concrete
implementations. Providers are stateless and configuration-driven:
construct one per :class:`ops.billing.db.PaymentChannel` row or per
global provider kind (TRC20 is singleton, tracked via env vars).

Public surface:

- :func:`get_provider` — factory resolving ``(kind, channel_row)``
  to an instance. Used by REST handlers and schedulers.
- :class:`BasePaymentProvider`, :class:`CreateInvoiceResult`,
  :class:`WebhookOutcome` — re-exported from :mod:`.base` for
  convenience.
- :class:`EPayProvider` — re-exported from :mod:`.epay`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ops.billing.providers.base import (
    BasePaymentProvider,
    CreateInvoiceResult,
    InvalidSignature,
    UnhandledEventType,
    WebhookOutcome,
)
from ops.billing.providers.epay import EPayProvider

if TYPE_CHECKING:
    from ops.billing.db import PaymentChannel


def get_provider(
    kind: str,
    channel: PaymentChannel | None = None,
    *,
    callback_base_url: str | None = None,
) -> BasePaymentProvider:
    """Resolve a concrete provider for a payment channel kind.

    ``kind`` is the namespace used throughout the billing layer
    (``"epay"`` / ``"trc20"``). For ``"epay"``, ``channel`` is
    required — it carries the merchant credentials. For ``"trc20"``,
    ``channel`` is ignored (provider is a singleton tracked via env
    vars; see future ``Trc20Provider`` in A.3.1).

    ``callback_base_url`` is the fully-qualified origin EPay-style
    providers embed in ``notify_url``. Must be supplied when
    creating EPay invoices; unused for TRC20.

    Raises :class:`ValueError` for unknown kinds or missing required
    arguments.
    """

    if kind == "epay":
        if channel is None:
            raise ValueError("epay provider requires a PaymentChannel row")
        if callback_base_url is None:
            raise ValueError(
                "epay provider requires callback_base_url for notify_url"
            )
        from ops.billing.providers.epay import SIGN_BODY_MODE_PLAIN

        sign_body_mode = channel.get_extra_config(
            "sign_body_mode", SIGN_BODY_MODE_PLAIN
        )
        return EPayProvider(
            channel_code=channel.channel_code,
            merchant_id=channel.merchant_id,
            secret_key=channel.merchant_key,
            gateway_url=channel.gateway_url,
            callback_base_url=callback_base_url,
            sign_body_mode=sign_body_mode,
        )

    if kind == "trc20":
        raise NotImplementedError(
            "trc20 provider lands in A.3.1; use env-driven singleton"
        )

    raise ValueError(f"unknown payment provider kind: {kind!r}")


__all__ = [
    "BasePaymentProvider",
    "CreateInvoiceResult",
    "EPayProvider",
    "InvalidSignature",
    "UnhandledEventType",
    "WebhookOutcome",
    "get_provider",
]
