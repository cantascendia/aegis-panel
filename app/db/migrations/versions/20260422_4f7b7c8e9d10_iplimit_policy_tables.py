"""iplimit policy tables

Revision ID: 4f7b7c8e9d10
Revises: 57eba0a293f2
Create Date: 2026-04-22 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "4f7b7c8e9d10"
down_revision = "57eba0a293f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "aegis_iplimit_config",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "max_concurrent_ips",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column("window_seconds", sa.Integer(), nullable=False),
        sa.Column(
            "violation_action",
            sa.String(length=16),
            nullable=False,
        ),
        sa.Column(
            "disable_duration_seconds",
            sa.Integer(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "aegis_iplimit_override",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("max_concurrent_ips", sa.Integer(), nullable=True),
        sa.Column("window_seconds", sa.Integer(), nullable=True),
        sa.Column(
            "violation_action",
            sa.String(length=16),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.bulk_insert(
        sa.table(
            "aegis_iplimit_config",
            sa.column("id", sa.Integer()),
            sa.column("max_concurrent_ips", sa.Integer()),
            sa.column("window_seconds", sa.Integer()),
            sa.column("violation_action", sa.String()),
            sa.column("disable_duration_seconds", sa.Integer()),
        ),
        [
            {
                "id": 1,
                "max_concurrent_ips": 3,
                "window_seconds": 300,
                "violation_action": "warn",
                "disable_duration_seconds": 3600,
            }
        ],
    )


def downgrade() -> None:
    op.drop_table("aegis_iplimit_override")
    op.drop_table("aegis_iplimit_config")

