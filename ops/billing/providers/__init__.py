"""Payment provider factory."""

from __future__ import annotations

from ops.billing.providers.base import BasePaymentProvider, UnknownProviderKind
from ops.billing.providers.epay import EPayConfig, EPayProvider


def get_provider(kind: str, **kwargs: object) -> BasePaymentProvider:
    """Return a provider adapter for a channel kind."""

    if kind == "epay":
        return EPayProvider(EPayConfig(**kwargs))
    raise UnknownProviderKind(f"unsupported billing provider kind {kind!r}")


__all__ = [
    "BasePaymentProvider",
    "EPayConfig",
    "EPayProvider",
    "UnknownProviderKind",
    "get_provider",
]
