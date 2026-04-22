"""billing MVP tables

Revision ID: a1c4b7f9e201
Revises: 4f7b7c8e9d10
Create Date: 2026-04-22 15:45:00.000000

Adds the 5 tables that back ``ops/billing/db.py``:

  aegis_billing_plans          operator-configured products
  aegis_billing_channels       码商 (EPay) credentials, runtime-editable
  aegis_billing_invoices       user orders + state machine + provider corr
  aegis_billing_invoice_lines  cart line items per invoice
  aegis_billing_payment_events immutable audit log

Design notes honored here vs the model:
- Money columns are plain Integer (fen / USDT-millis). No DB-level
  CHECK constraints on state enums — state validity lives in
  ops.billing.states (A.1.2) so transitions can evolve without
  schema churn.
- Composite indexes from the model's __table_args__ are created
  explicitly here (``ix_billing_invoices_state_expires`` etc.).
- Plan JSON column is ``sa.JSON`` — maps to JSONB on PostgreSQL
  and TEXT-with-JSON-coercion on SQLite. Both work with
  SQLAlchemy's JSON type on SQLAlchemy 2.0.
- ``on_delete="CASCADE"`` on invoice_lines.invoice_id so an admin
  wiping a bad test invoice doesn't leave dangling lines.
  PaymentEvent intentionally has NO cascade — audit log must
  survive invoice deletion (which is anyway not supported via app
  code; admins only ``cancel``, never delete).
"""

import sqlalchemy as sa
from alembic import op

revision = "a1c4b7f9e201"
down_revision = "4f7b7c8e9d10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -----------------------------------------------------------------
    # aegis_billing_plans
    # -----------------------------------------------------------------
    op.create_table(
        "aegis_billing_plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("operator_code", sa.String(length=64), nullable=False),
        sa.Column(
            "display_name_en", sa.String(length=128), nullable=False
        ),
        sa.Column("display_name_i18n", sa.JSON(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("data_limit_gb", sa.Integer(), nullable=True),
        sa.Column("duration_days", sa.Integer(), nullable=True),
        sa.Column("price_cny_fen", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "operator_code", name="uq_billing_plans_operator_code"
        ),
    )
    op.create_index(
        "ix_billing_plans_enabled_sort",
        "aegis_billing_plans",
        ["enabled", "sort_order"],
    )

    # -----------------------------------------------------------------
    # aegis_billing_channels
    # -----------------------------------------------------------------
    op.create_table(
        "aegis_billing_channels",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("channel_code", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("gateway_url", sa.String(length=512), nullable=False),
        sa.Column("merchant_id", sa.String(length=128), nullable=False),
        sa.Column("secret_key", sa.String(length=256), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "channel_code", name="uq_billing_channels_channel_code"
        ),
    )
    op.create_index(
        "ix_billing_channels_enabled_priority",
        "aegis_billing_channels",
        ["enabled", "priority"],
    )

    # -----------------------------------------------------------------
    # aegis_billing_invoices
    # -----------------------------------------------------------------
    op.create_table(
        "aegis_billing_invoices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("total_cny_fen", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column(
            "provider_invoice_id", sa.String(length=128), nullable=True
        ),
        sa.Column("payment_url", sa.String(length=512), nullable=True),
        sa.Column("trc20_memo", sa.String(length=64), nullable=True),
        sa.Column(
            "trc20_expected_amount_millis", sa.Integer(), nullable=True
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
        sa.Column("applied_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider",
            "provider_invoice_id",
            name="uq_billing_invoices_provider_corr",
        ),
    )
    op.create_index(
        "ix_billing_invoices_state_expires",
        "aegis_billing_invoices",
        ["state", "expires_at"],
    )
    op.create_index(
        "ix_billing_invoices_user_state",
        "aegis_billing_invoices",
        ["user_id", "state"],
    )

    # -----------------------------------------------------------------
    # aegis_billing_invoice_lines
    # -----------------------------------------------------------------
    op.create_table(
        "aegis_billing_invoice_lines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column(
            "unit_price_fen_at_purchase",
            sa.Integer(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["invoice_id"],
            ["aegis_billing_invoices.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["plan_id"], ["aegis_billing_plans.id"]
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_billing_lines_invoice",
        "aegis_billing_invoice_lines",
        ["invoice_id"],
    )

    # -----------------------------------------------------------------
    # aegis_billing_payment_events
    # -----------------------------------------------------------------
    op.create_table(
        "aegis_billing_payment_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["invoice_id"], ["aegis_billing_invoices.id"]
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_billing_events_invoice_created",
        "aegis_billing_payment_events",
        ["invoice_id", "created_at"],
    )


def downgrade() -> None:
    # Drop in reverse dependency order: events + lines (FK to invoices)
    # first, then invoices, then the two free-standing tables.
    op.drop_index(
        "ix_billing_events_invoice_created",
        table_name="aegis_billing_payment_events",
    )
    op.drop_table("aegis_billing_payment_events")

    op.drop_index(
        "ix_billing_lines_invoice",
        table_name="aegis_billing_invoice_lines",
    )
    op.drop_table("aegis_billing_invoice_lines")

    op.drop_index(
        "ix_billing_invoices_user_state",
        table_name="aegis_billing_invoices",
    )
    op.drop_index(
        "ix_billing_invoices_state_expires",
        table_name="aegis_billing_invoices",
    )
    op.drop_table("aegis_billing_invoices")

    op.drop_index(
        "ix_billing_channels_enabled_priority",
        table_name="aegis_billing_channels",
    )
    op.drop_table("aegis_billing_channels")

    op.drop_index(
        "ix_billing_plans_enabled_sort",
        table_name="aegis_billing_plans",
    )
    op.drop_table("aegis_billing_plans")
