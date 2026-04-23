"""Base interfaces for billing payment providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class CreateInvoiceResult:
    """Provider response after preparing an invoice for payment."""

    provider_invoice_id: str
    payment_url: str
    extra_payload: dict[str, object]


@dataclass(frozen=True)
class WebhookOutcome:
    """Verified provider webhook mapped into the local invoice model."""

    invoice_id: int
    new_state: str
    provider_event_id: str
    raw: dict[str, str]


class PaymentProviderError(RuntimeError):
    """Base class for provider-level failures."""


class InvalidSignature(PaymentProviderError):
    """Raised when a provider webhook signature does not verify."""


class InvalidProviderPayload(PaymentProviderError):
    """Raised when a provider payload is verified but malformed."""


class UnhandledEventType(PaymentProviderError):
    """Raised for verified provider events this MVP intentionally ignores."""


class UnknownProviderKind(PaymentProviderError):
    """Raised when provider lookup receives an unsupported kind."""


class BasePaymentProvider(ABC):
    """Provider abstraction used by checkout and webhook routes."""

    @abstractmethod
    async def create_invoice(
        self,
        invoice_id: int,
        amount_cny_fen: int,
        subject: str,
        success_url: str,
        cancel_url: str,
    ) -> CreateInvoiceResult:
        """Create or prepare a provider-side invoice."""

    @abstractmethod
    async def handle_webhook(
        self, params: Mapping[str, str], raw_body: bytes
    ) -> WebhookOutcome:
        """Validate and translate a provider webhook."""
