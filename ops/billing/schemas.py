"""
Pydantic request/response schemas for the billing admin REST API.

Kept separate from ``ops.billing.db`` so the transport layer can
evolve (adding/removing user-exposed fields) without touching the
DB model — and vice versa. FastAPI consumes these for automatic
validation + OpenAPI schema generation.

Three families:

- ``*In`` — request bodies for create/patch
- ``*Out`` — response bodies, flattened / safe-for-public (e.g.
  ``PaymentChannelOut`` omits ``secret_key``)
- ``*Patch`` — partial-update request bodies (all fields optional)

Validation invariants mirror ``ops.billing.pricing.validate_cart_line``
semantics for Plan kind rules, so the admin cannot persist a plan
that would immediately fail cart validation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ops.billing.db import (
    INVOICE_STATES,
    PLAN_KIND_FIXED,
    PLAN_KIND_FLEXIBLE_DURATION,
    PLAN_KIND_FLEXIBLE_TRAFFIC,
    PLAN_KINDS,
)

# ---------------------------------------------------------------------
# Plan
# ---------------------------------------------------------------------


class PlanIn(BaseModel):
    """Request body for ``POST /admin/plans``."""

    model_config = ConfigDict(extra="forbid")

    operator_code: str = Field(..., min_length=1, max_length=64)
    display_name_en: str = Field(..., min_length=1, max_length=128)
    display_name_i18n: dict[str, str] = Field(default_factory=dict)
    kind: Literal["fixed", "flexible_traffic", "flexible_duration"] = Field(
        ...
    )
    data_limit_gb: int | None = Field(default=None, ge=0)
    duration_days: int | None = Field(default=None, ge=0)
    price_cny_fen: int = Field(..., ge=0)
    enabled: bool = Field(default=True)
    sort_order: int = Field(default=0)

    @model_validator(mode="after")
    def _enforce_kind_invariants(self) -> PlanIn:
        # Same rules as ops.billing.pricing.validate_cart_line, but
        # enforced at creation time so bad plans never land in the DB.
        if self.kind == PLAN_KIND_FIXED:
            if self.data_limit_gb is None and self.duration_days is None:
                raise ValueError(
                    "fixed plan must specify at least one of "
                    "data_limit_gb / duration_days"
                )
        elif self.kind == PLAN_KIND_FLEXIBLE_TRAFFIC:
            if self.data_limit_gb is None:
                raise ValueError(
                    "flexible_traffic plan must set data_limit_gb "
                    "(per-unit GB)"
                )
            if self.duration_days is not None:
                raise ValueError(
                    "flexible_traffic plan must NOT set "
                    "duration_days (use flexible_duration instead)"
                )
        elif self.kind == PLAN_KIND_FLEXIBLE_DURATION:
            if self.duration_days is None:
                raise ValueError(
                    "flexible_duration plan must set duration_days "
                    "(per-unit days)"
                )
            if self.data_limit_gb is not None:
                raise ValueError(
                    "flexible_duration plan must NOT set "
                    "data_limit_gb (use flexible_traffic instead)"
                )
        return self


class PlanPatch(BaseModel):
    """Request body for ``PATCH /admin/plans/{id}``.

    All fields optional. ``kind`` is NOT patchable — changing kind
    on an existing plan would retroactively break all InvoiceLines
    referencing it. If operator needs a different kind, disable the
    old plan and create a new one.
    """

    model_config = ConfigDict(extra="forbid")

    display_name_en: str | None = Field(
        default=None, min_length=1, max_length=128
    )
    display_name_i18n: dict[str, str] | None = None
    data_limit_gb: int | None = Field(default=None, ge=0)
    duration_days: int | None = Field(default=None, ge=0)
    price_cny_fen: int | None = Field(default=None, ge=0)
    enabled: bool | None = None
    sort_order: int | None = None


class PlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    operator_code: str
    display_name_en: str
    display_name_i18n: dict[str, str]
    kind: str
    data_limit_gb: int | None
    duration_days: int | None
    price_cny_fen: int
    enabled: bool
    sort_order: int
    created_at: datetime


# ---------------------------------------------------------------------
# PaymentChannel
# ---------------------------------------------------------------------


class ChannelExtraConfig(BaseModel):
    """Structured view of the ``PaymentChannel.extra_config_json``
    blob. Both fields optional so partial payloads are valid."""

    model_config = ConfigDict(extra="forbid")

    sign_body_mode: Literal["plain", "with_key_prefix"] | None = None
    allowed_ips: list[str] | None = None


class ChannelIn(BaseModel):
    """Request body for ``POST /admin/channels``. Creates one 码商
    instance.

    ``merchant_key`` is the 码商-issued secret in plaintext; the
    handler Fernet-encrypts before persist. The legacy ``secret_key``
    alias is still accepted for one release to keep older clients /
    fixtures functional."""

    model_config = ConfigDict(extra="forbid")

    channel_code: str = Field(..., min_length=1, max_length=64)
    display_name: str = Field(..., min_length=1, max_length=128)
    kind: Literal["epay"] = Field(default="epay")
    gateway_url: str = Field(..., min_length=1, max_length=512)
    merchant_id: str = Field(..., min_length=1, max_length=128)
    merchant_key: str | None = Field(default=None, max_length=256)
    secret_key: str | None = Field(default=None, max_length=256)
    enabled: bool = Field(default=False)
    priority: int = Field(default=0)
    extra_config: ChannelExtraConfig | None = None

    @model_validator(mode="after")
    def _require_some_key(self) -> ChannelIn:
        if not (self.merchant_key or self.secret_key):
            raise ValueError(
                "create channel requires merchant_key "
                "(secret_key accepted as legacy alias)"
            )
        return self


class ChannelPatch(BaseModel):
    """Request body for ``PATCH /admin/channels/{id}``."""

    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(
        default=None, min_length=1, max_length=128
    )
    gateway_url: str | None = Field(default=None, min_length=1, max_length=512)
    merchant_id: str | None = Field(default=None, min_length=1, max_length=128)
    merchant_key: str | None = Field(default=None, max_length=256)
    secret_key: str | None = Field(default=None, max_length=256)
    enabled: bool | None = None
    priority: int | None = None
    extra_config: ChannelExtraConfig | None = None


class ChannelOut(BaseModel):
    """Admin-facing response. **Omits the merchant secret** (both
    encrypted and plaintext columns). Write-only once configured; if
    admin needs to rotate, they PATCH a new ``merchant_key``."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    channel_code: str
    display_name: str
    kind: str
    gateway_url: str
    merchant_id: str
    enabled: bool
    priority: int
    extra_config_json: dict[str, Any] | None = None
    created_at: datetime


# ---------------------------------------------------------------------
# Invoice + read-only admin views
# ---------------------------------------------------------------------


class InvoiceLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plan_id: int
    quantity: int
    unit_price_fen_at_purchase: int


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    total_cny_fen: int
    state: str
    provider: str
    provider_invoice_id: str | None
    payment_url: str | None
    trc20_memo: str | None
    trc20_expected_amount_millis: int | None
    created_at: datetime
    paid_at: datetime | None
    applied_at: datetime | None
    expires_at: datetime
    lines: list[InvoiceLineOut] = Field(default_factory=list)


class InvoiceAdminActionIn(BaseModel):
    """Body for ``POST /admin/invoices/{id}/apply_manual`` and
    ``POST /admin/invoices/{id}/cancel``. Note is mandatory —
    audit trail demands a reason for every admin state change."""

    model_config = ConfigDict(extra="forbid")

    note: str = Field(..., min_length=1, max_length=512)


class InvoiceListQuery(BaseModel):
    """Query-param bundle for ``GET /admin/invoices``."""

    model_config = ConfigDict(extra="forbid")

    state: str | None = None
    user_id: int | None = None
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _validate_state(self) -> InvoiceListQuery:
        if self.state is not None and self.state not in INVOICE_STATES:
            raise ValueError(
                f"state must be one of {INVOICE_STATES}, got {self.state!r}"
            )
        return self


class PaymentEventOut(BaseModel):
    """Admin-facing audit row view. Useful alongside InvoiceOut when
    diagnosing a stuck invoice."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_id: int
    event_type: str
    payload_json: dict[str, Any]
    note: str | None
    created_at: datetime


class CheckoutLineIn(BaseModel):
    """One cart line as the caller sends it. Resolves to an
    ``InvoiceLine`` row at persist time."""

    model_config = ConfigDict(extra="forbid")

    plan_id: int = Field(..., ge=1)
    quantity: int = Field(default=1, ge=1)


class CheckoutIn(BaseModel):
    """Body for ``POST /api/billing/cart/checkout``. Admin-initiated
    order creation on behalf of a user — A.4 adds the user-self-serve
    sibling route under a separate auth dep."""

    model_config = ConfigDict(extra="forbid")

    user_id: int = Field(..., ge=1)
    channel_code: str = Field(..., min_length=1, max_length=64)
    lines: list[CheckoutLineIn] = Field(..., min_length=1, max_length=32)
    success_url: str = Field(..., min_length=1, max_length=512)
    cancel_url: str = Field(..., min_length=1, max_length=512)
    subject: str | None = Field(default=None, max_length=128)


class CheckoutOut(BaseModel):
    """Response from checkout.

    For EPay channels ``payment_url`` is the 码商-hosted redirect URL
    the client should 302 the browser to.

    For TRC20 ``payment_url`` is an in-panel route
    (``/billing/trc20/<id>``) that renders memo + receive_address +
    QR + countdown. The TRC20-specific fields below are also returned
    inline so a client that wants to skip a follow-up fetch (e.g.
    embed the memo straight into a toast / clipboard helper) can.
    All TRC20 fields are ``None`` for EPay invoices, preserving
    backward compatibility with v0.4.0 EPay clients.
    """

    model_config = ConfigDict(from_attributes=True)

    invoice_id: int
    total_cny_fen: int
    payment_url: str
    provider_invoice_id: str
    state: str
    expires_at: datetime
    # TRC20 conveniences. Optional; populated only when the cart
    # checked out against ``channel_code == "trc20"``.
    trc20_memo: str | None = Field(default=None)
    trc20_expected_amount_millis: int | None = Field(default=None)
    trc20_receive_address: str | None = Field(default=None)


__all__ = [
    "ChannelExtraConfig",
    "ChannelIn",
    "ChannelOut",
    "ChannelPatch",
    "CheckoutIn",
    "CheckoutLineIn",
    "CheckoutOut",
    "InvoiceAdminActionIn",
    "InvoiceLineOut",
    "InvoiceListQuery",
    "InvoiceOut",
    "PaymentEventOut",
    "PlanIn",
    "PlanOut",
    "PlanPatch",
    "PLAN_KINDS",
]
