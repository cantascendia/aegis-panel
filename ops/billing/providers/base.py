"""Abstract payment provider contract.

Every concrete provider(EPay adapter, TRC20 poller stub, future
BTCPay / NOWPayments / Stripe) implements this interface. The REST
layer and schedulers only touch providers through it.

Two return dataclasses define the provider's side of the handshake:

- :class:`CreateInvoiceResult` — what :meth:`BasePaymentProvider.
  create_invoice` promises back to the checkout handler.
- :class:`WebhookOutcome` — what :meth:`BasePaymentProvider.
  handle_webhook` promises back to the webhook handler, including
  the ``provider_event_id`` used for
  :func:`ops.billing.states.record_webhook_seen` dedup.

Two exceptions mark the two expected failure modes so handlers can
distinguish "signature forged / request malformed"(reject the
caller)from "we understand but ignore this event type"(accept and
noop).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True)
class CreateInvoiceResult:
    """Outcome of :meth:`BasePaymentProvider.create_invoice`.

    Attributes:
        provider_invoice_id: the opaque identifier the provider will
            echo back in webhooks / poll results. For EPay this is
            the ``out_trade_no`` we sent. For TRC20 this is the
            unique memo we allocated.
        payment_url: where to send the user. For EPay this is the
            external gateway URL; for TRC20 this is an in-panel
            route that renders a QR + address + memo.
        extra_payload: anything provider-specific worth preserving
            in :class:`ops.billing.db.PaymentEvent.payload_json`
            for forensics. Not interpreted by the REST layer.
    """

    provider_invoice_id: str
    payment_url: str
    extra_payload: dict = field(default_factory=dict)


@dataclass(frozen=True)
class WebhookOutcome:
    """Outcome of :meth:`BasePaymentProvider.handle_webhook`.

    Attributes:
        invoice_id: the local panel invoice primary key, recovered
            from the provider's echo.
        new_state: the state the webhook wants to move the invoice
            to (typically ``"paid"``; providers may also signal
            ``"failed"`` for terminal negatives).
        provider_event_id: the dedup key for
            :func:`ops.billing.states.record_webhook_seen`. Must be
            stable across retries of the same underlying event — for
            EPay use the 码商's ``trade_no``; for TRC20 use the tx
            hash.
        raw: the verbatim webhook payload, entered into the audit
            log ``PaymentEvent.payload_json``. Not interpreted.
    """

    invoice_id: int
    new_state: str
    provider_event_id: str
    raw: dict


class InvalidSignature(Exception):
    """Webhook signature did not verify.

    Route handlers should translate this to HTTP 400. Never treat
    it as a noop — it indicates either a misconfigured
    ``secret_key`` or an attacker probing the endpoint.
    """


class UnhandledEventType(Exception):
    """Webhook was well-formed but describes an event we don't act on.

    Example: EPay's ``trade_status=TRADE_FAIL`` when our state
    machine only transitions on ``TRADE_SUCCESS``. Route handlers
    should respond 200 with the provider's expected
    acknowledgement string (``"success"`` for 易支付) so the
    provider does not keep retrying.
    """


class BasePaymentProvider(ABC):
    """Abstract adapter every concrete provider implements."""

    kind: str  # subclasses set this; also exposed for diagnostics.

    @abstractmethod
    async def create_invoice(
        self,
        invoice_id: int,
        amount_cny_fen: int,
        subject: str,
        success_url: str,
        cancel_url: str,
    ) -> CreateInvoiceResult:
        """Begin a payment flow.

        Called from ``POST /api/billing/cart/checkout`` right after
        the :class:`ops.billing.db.Invoice` row is created in state
        ``pending``. Must be idempotent on its own side: retrying
        with the same ``invoice_id`` should produce the same
        ``provider_invoice_id`` (subclasses that call third-party
        APIs are allowed to open a new third-party invoice each
        retry, but the dedup key must be derivable from
        ``invoice_id``).
        """

    @abstractmethod
    async def handle_webhook(
        self,
        params: Mapping[str, str],
        raw_body: bytes,
    ) -> WebhookOutcome:
        """Parse + verify an incoming webhook.

        Raises:
            InvalidSignature: the caller could not prove knowledge of
                the shared secret.
            UnhandledEventType: well-formed but not a state-changing
                event.
        """
