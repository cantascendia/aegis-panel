"""
SQLAlchemy models for the billing layer.

Tables (all ``aegis_billing_*`` prefix, matching the
``aegis_iplimit_*`` precedent):

- ``aegis_billing_plans`` — operator-configured products (fixed plan
  or flexible-unit addon)
- ``aegis_billing_channels`` — runtime-configured payment channels
  (each row is one 码商's EPay credentials; TRC20 is a single
  implicit channel tracked in env, not a DB row)
- ``aegis_billing_invoices`` — user orders, each carrying its state
  machine state, provider, and provider-specific correlation fields
- ``aegis_billing_invoice_lines`` — what was actually purchased per
  invoice; multiple lines aggregate into one payment
- ``aegis_billing_payment_events`` — immutable audit log; every
  webhook, every transition, every admin action gets one row

Design invariants (see SPEC-billing-mvp.md):

- Money is stored as **integer fen** (1/100 CNY). Never Decimal,
  never float. USD or USDT equivalents are computed at provider
  time with the rate snapshot logged in ``PaymentEvent``.
- ``Invoice.state`` transitions are enforced by
  ``ops.billing.states.transition`` (landing in A.1.2); this module
  only declares the column, not the state machine logic.
- i18n: plan display names live in ``display_name_i18n`` (JSON
  column); UI prefers current locale, falls back to
  ``display_name_en``.

Cross-references:
- Alembic migration: ``app/db/migrations/versions/20260422_*_billing_tables.py``
- env.py registration: ``import ops.billing.db  # noqa: F401`` line,
  required so ``Base.metadata`` sees these models (LESSONS L-014).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# ---------------------------------------------------------------------
# Constants — validated at the application layer, not via DB CHECK
# (we deliberately keep constraints out of DB to let the state machine
# evolve without migrations).
# ---------------------------------------------------------------------

PLAN_KIND_FIXED = "fixed"
PLAN_KIND_FLEXIBLE_TRAFFIC = "flexible_traffic"
PLAN_KIND_FLEXIBLE_DURATION = "flexible_duration"
PLAN_KINDS = (
    PLAN_KIND_FIXED,
    PLAN_KIND_FLEXIBLE_TRAFFIC,
    PLAN_KIND_FLEXIBLE_DURATION,
)

INVOICE_STATE_CREATED = "created"
INVOICE_STATE_PENDING = "pending"
INVOICE_STATE_AWAITING_PAYMENT = "awaiting_payment"
INVOICE_STATE_PAID = "paid"
INVOICE_STATE_APPLIED = "applied"
INVOICE_STATE_EXPIRED = "expired"
INVOICE_STATE_CANCELLED = "cancelled"
INVOICE_STATE_FAILED = "failed"
INVOICE_STATES = (
    INVOICE_STATE_CREATED,
    INVOICE_STATE_PENDING,
    INVOICE_STATE_AWAITING_PAYMENT,
    INVOICE_STATE_PAID,
    INVOICE_STATE_APPLIED,
    INVOICE_STATE_EXPIRED,
    INVOICE_STATE_CANCELLED,
    INVOICE_STATE_FAILED,
)

PROVIDER_MANUAL_ADMIN = "manual_admin"
PROVIDER_TRC20 = "trc20"
# EPay providers are prefixed ``epay:<channel_code>`` since there can
# be multiple 码商 configured at once. Helper in states.py (A.1.2).


# ---------------------------------------------------------------------
# Plan — operator's product catalog
# ---------------------------------------------------------------------


class Plan(Base):
    """A purchasable product.

    Three shapes via ``kind``:

    - ``fixed`` — single unit carrying (data_limit_gb + duration_days +
      price_cny_fen). Quantity on an invoice line is always 1.
    - ``flexible_traffic`` — unit priced per GB; invoice line quantity
      = number of extra GB. ``duration_days`` MUST be NULL.
    - ``flexible_duration`` — unit priced per day; invoice line
      quantity = number of extra days. ``data_limit_gb`` MUST be NULL.

    The ``fixed`` vs ``flexible_*`` distinction is what
    ``ops.billing.pricing.compute_user_grant`` uses to aggregate
    multi-line carts correctly.
    """

    __tablename__ = "aegis_billing_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    operator_code: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False
    )
    display_name_en: Mapped[str] = mapped_column(String(128), nullable=False)
    display_name_i18n: Mapped[dict[str, str]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    # Nullable because flexible-* plans use only one dimension.
    data_limit_gb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Integer fen (1/100 CNY). 880 = ¥8.80.
    price_cny_fen: Mapped[int] = mapped_column(Integer, nullable=False)
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    __table_args__ = (
        Index("ix_billing_plans_enabled_sort", "enabled", "sort_order"),
    )

    def __repr__(self) -> str:  # pragma: no cover — repr only
        return (
            f"<Plan id={self.id} code={self.operator_code!r} "
            f"kind={self.kind} fen={self.price_cny_fen}>"
        )


# ---------------------------------------------------------------------
# PaymentChannel — admin-configurable 码商 credentials
# ---------------------------------------------------------------------


class PaymentChannel(Base):
    """One configured EPay channel (one 码商).

    TRC20 is NOT represented here — it's a singleton tracked via
    ``BILLING_TRC20_*`` env vars. Only EPay needs DB rows because
    (a) multiple 码商 are active simultaneously for redundancy, and
    (b) credentials change without restart when an operator switches
    vendors (see OPS-epay-vendor-guide.md).

    ``merchant_key_encrypted`` holds the 码商-issued secret at rest,
    Fernet-encrypted under ``BILLING_SECRET_KEY`` (see
    ``ops.billing.config``). The legacy ``secret_key`` column is kept
    nullable for rows predating A.2.2's encryption addition and for
    dev/test environments that opt out of configuring a Fernet key;
    :meth:`merchant_key` resolves one or the other transparently.

    ``extra_config_json`` holds per-channel protocol knobs that don't
    merit their own column:

    - ``sign_body_mode``: ``"plain"`` (default) or ``"with_key_prefix"``
      — some 码商 dialects use ``body + "&key=" + secret`` instead of
      ``body + secret`` when computing the MD5 sign
    - ``allowed_ips``: list of IPv4/IPv6 literals or CIDRs that webhook
      POSTs must originate from (double防线 besides MD5 verify)
    """

    __tablename__ = "aegis_billing_channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Short identifier embedded in the webhook URL path, e.g.
    # "/api/billing/webhook/epay/zpay1". Must be URL-safe.
    channel_code: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False
    )
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    # "epay" is the only kind for now; leaves room for a future
    # "nowpayments" / "btcpay" etc. without a new table.
    kind: Mapped[str] = mapped_column(
        String(32), nullable=False, default="epay"
    )
    gateway_url: Mapped[str] = mapped_column(String(512), nullable=False)
    merchant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    # Legacy plaintext key — nullable after A.2.2. New rows write to
    # ``merchant_key_encrypted`` instead. Admin UI no longer displays
    # or accepts this column; present only for backward-compat reads.
    secret_key: Mapped[str | None] = mapped_column(String(256), nullable=True)
    # Fernet ciphertext of the 码商 secret. Decrypt via
    # ``ops.billing.config.decrypt_merchant_key`` or the
    # :meth:`merchant_key` convenience property.
    merchant_key_encrypted: Mapped[bytes | None] = mapped_column(
        LargeBinary, nullable=True
    )
    # Free-form JSON carrier for low-volume knobs. See class docstring
    # for the keys currently consumed.
    extra_config_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    # Higher priority shows first in the user checkout UI when
    # multiple channels are enabled. Failover doesn't automatically
    # switch; the operator disables a dead channel and priority on
    # the remaining ones determines what the user sees next.
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    __table_args__ = (
        Index("ix_billing_channels_enabled_priority", "enabled", "priority"),
    )

    @property
    def merchant_key(self) -> str:
        """Plaintext 码商 secret, decrypted on-access.

        Prefers the encrypted column; falls back to the legacy plain
        ``secret_key`` when the encrypted one is empty. Dev / test
        environments without ``BILLING_SECRET_KEY`` configured land on
        the fallback path so test fixtures don't need the Fernet key.

        Production code paths that require encryption
        (``apply_panel_hardening`` boot check, OPS-epay-vendor-guide)
        can assert ``merchant_key_encrypted`` is non-empty; this
        property stays lenient so it's safe to read from any row.
        """

        from ops.billing.config import decrypt_merchant_key

        if self.merchant_key_encrypted:
            return decrypt_merchant_key(self.merchant_key_encrypted)
        return self.secret_key or ""

    def get_extra_config(self, key: str, default: Any = None) -> Any:
        """Read a key from ``extra_config_json`` with a default.

        Centralizes the None-guard so handlers don't scatter
        ``(self.extra_config_json or {}).get(...)`` boilerplate.
        """
        if not self.extra_config_json:
            return default
        return self.extra_config_json.get(key, default)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<PaymentChannel id={self.id} code={self.channel_code!r} "
            f"enabled={self.enabled}>"
        )


# ---------------------------------------------------------------------
# Invoice + InvoiceLine
# ---------------------------------------------------------------------


class Invoice(Base):
    """A user's order.

    Carries the payment state machine; transitions are enforced by
    ``ops.billing.states.transition`` (A.1.2) — the model itself
    does not validate ``state`` transitions.

    ``provider`` uses a namespace scheme:
    - ``trc20`` — self-polled TRC20 USDT
    - ``epay:<channel_code>`` — one specific 码商
    - ``manual_admin`` — operator directly activated without payment
      (emergency / VIP / refund-correction)
    """

    __tablename__ = "aegis_billing_invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    total_cny_fen: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(
        String(32), nullable=False, default=INVOICE_STATE_CREATED
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_invoice_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    payment_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # TRC20-specific correlation fields. NULL for other providers.
    trc20_memo: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # USDT stored as 1/1000 (millis) — USDT has 6 decimals on-chain,
    # 3 is plenty for operator-scale granularity and avoids float.
    trc20_expected_amount_millis: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    applied_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    # Hard deadline for payment. Past this, ``reap_expired_invoices``
    # flips the state to ``expired``. Default 30 minutes from
    # creation — set at insert time by the caller.
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    lines: Mapped[list[InvoiceLine]] = relationship(
        "InvoiceLine",
        back_populates="invoice",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_billing_invoices_state_expires", "state", "expires_at"),
        Index("ix_billing_invoices_user_state", "user_id", "state"),
        # Unique (provider, provider_invoice_id) de-duplicates webhook
        # replays; see ops.billing.states.transition in A.1.2.
        UniqueConstraint(
            "provider",
            "provider_invoice_id",
            name="uq_billing_invoices_provider_corr",
        ),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<Invoice id={self.id} user={self.user_id} "
            f"state={self.state} fen={self.total_cny_fen}>"
        )


class InvoiceLine(Base):
    """One line item on an invoice; references a Plan + quantity.

    ``unit_price_fen_at_purchase`` locks the price at cart-create
    time so a later operator price change doesn't retroactively
    rewrite the user's invoice.
    """

    __tablename__ = "aegis_billing_invoice_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("aegis_billing_invoices.id", ondelete="CASCADE"),
        nullable=False,
    )
    plan_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("aegis_billing_plans.id"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price_fen_at_purchase: Mapped[int] = mapped_column(
        Integer, nullable=False
    )

    invoice: Mapped[Invoice] = relationship("Invoice", back_populates="lines")

    __table_args__ = (Index("ix_billing_lines_invoice", "invoice_id"),)


# ---------------------------------------------------------------------
# PaymentEvent — immutable audit log
# ---------------------------------------------------------------------


class PaymentEvent(Base):
    """Append-only audit row. One per webhook, per transition, per
    admin action.

    Intentionally **no UPDATE and no DELETE paths** from application
    code. If a row is wrong, the correct remedy is another row
    recording the correction (classic accounting hygiene).
    """

    __tablename__ = "aegis_billing_payment_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("aegis_billing_invoices.id"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    # JSON blob so new event types can add fields without a migration.
    # Read-side code should be defensive; we don't validate shape here.
    payload_json: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    # Free-text note — used when event_type == "admin_manual" to
    # record the operator's justification. Optional for other types.
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    __table_args__ = (
        Index(
            "ix_billing_events_invoice_created",
            "invoice_id",
            "created_at",
        ),
    )
