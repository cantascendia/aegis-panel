"""iplimit allowlist cidrs

Revision ID: b2f1c3d4e5a6
Revises: 44c0b755e487
Create Date: 2026-04-24 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "b2f1c3d4e5a6"
down_revision = "44c0b755e487"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "aegis_iplimit_config",
        sa.Column("ip_allowlist_cidrs", sa.Text(), nullable=True),
    )
    op.add_column(
        "aegis_iplimit_override",
        sa.Column("ip_allowlist_cidrs", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("aegis_iplimit_override", "ip_allowlist_cidrs")
    op.drop_column("aegis_iplimit_config", "ip_allowlist_cidrs")
