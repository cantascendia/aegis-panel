"""billing a22 webhook fields

Revision ID: c3d2e1f4a5b6
Revises: b2f1c3d4e5a6
Create Date: 2026-04-23 12:00:00.000000

Adds the A.2.2 schema deltas on top of the A.1 billing tables:

- ``aegis_billing_channels.merchant_key_encrypted`` — LargeBinary,
  nullable. Fernet ciphertext of the 码商-issued secret, written by
  ``ops.billing.endpoint.create_channel`` and decrypted by the
  provider factory. Nullable so existing plaintext rows that pre-
  date A.2.2 aren't broken on migrate.
- ``aegis_billing_channels.extra_config_json`` — JSON, nullable.
  Holds per-channel protocol knobs (``sign_body_mode``,
  ``allowed_ips``) that don't warrant their own column.
- ``aegis_billing_channels.secret_key`` — made nullable. New rows
  post-A.2.2 write ``merchant_key_encrypted`` instead; the legacy
  plaintext column stays populated on pre-existing rows until an
  operator rotates credentials through the admin UI.

This is a pure additive / widening migration — no data loss, no
column drops. Downgrade drops the two new columns; the secret_key
tightening back to NOT NULL is omitted because we can't safely
re-tighten without guaranteeing encrypted rows got backfilled.
"""

import sqlalchemy as sa
from alembic import op

revision = "c3d2e1f4a5b6"
down_revision = "b2f1c3d4e5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "aegis_billing_channels",
        sa.Column(
            "merchant_key_encrypted", sa.LargeBinary(), nullable=True
        ),
    )
    op.add_column(
        "aegis_billing_channels",
        sa.Column("extra_config_json", sa.JSON(), nullable=True),
    )
    # SQLite batch mode needed to alter nullability; op.alter_column
    # is a no-op on SQLite without it. For PG/MySQL the plain form
    # works, so we branch on dialect.
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("aegis_billing_channels") as batch_op:
            batch_op.alter_column(
                "secret_key",
                existing_type=sa.String(length=256),
                nullable=True,
            )
    else:
        op.alter_column(
            "aegis_billing_channels",
            "secret_key",
            existing_type=sa.String(length=256),
            nullable=True,
        )


def downgrade() -> None:
    op.drop_column("aegis_billing_channels", "extra_config_json")
    op.drop_column("aegis_billing_channels", "merchant_key_encrypted")
    # secret_key nullability intentionally left loose on downgrade —
    # re-tightening risks rejecting rows that the A.2.2 code path
    # already migrated off the legacy column.
