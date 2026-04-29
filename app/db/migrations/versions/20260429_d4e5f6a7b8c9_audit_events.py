"""audit events table (S-AL)

Revision ID: d4e5f6a7b8c9
Revises: c3d2e1f4a5b6
Create Date: 2026-04-29 00:00:00.000000

Adds ``aegis_audit_events`` — the append-only admin operation audit log.

Design notes:
- ``id`` is BigInteger (autoincrement) rather than plain Integer; at
  100 ops/day the Int32 limit won't be hit in any reasonable timeframe,
  but BigInteger is the right default for an audit table that may grow
  faster in high-throughput forks.
- ``before_state_encrypted`` / ``after_state_encrypted`` are LargeBinary;
  Fernet tokens are typically ~100-200 bytes overhead over the plaintext,
  fitting comfortably in a single DB page.
- No FK from ``actor_id`` to ``admins.id`` — audit rows must survive admin
  deletion (hard-delete of an admin should not cascade-delete their audit
  history). We snapshot ``actor_username`` at write time for the same
  reason.
- Four composite indexes mirror the query patterns in SPEC-audit-log.md:
  actor+ts, action+ts, target+ts, ts-only (for retention sweep).
- ``DOWN`` drops the table; the migration is reversible for dev/test
  workflows. Production operators should treat a downgrade as unusual and
  verify the data is backed up before running.
"""

import sqlalchemy as sa
from alembic import op

revision = "d4e5f6a7b8c9"
down_revision = "c3d2e1f4a5b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "aegis_audit_events",
        sa.Column("id", sa.BigInteger(), nullable=False, autoincrement=True),
        # Actor
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("actor_type", sa.String(length=32), nullable=False),
        sa.Column("actor_username", sa.String(length=128), nullable=True),
        # Action
        sa.Column("action", sa.String(length=256), nullable=False),
        sa.Column("method", sa.String(length=16), nullable=False),
        sa.Column("path", sa.String(length=512), nullable=False),
        # Target
        sa.Column("target_type", sa.String(length=64), nullable=True),
        sa.Column("target_id", sa.String(length=64), nullable=True),
        # State snapshots (Fernet-encrypted JSON)
        sa.Column("before_state_encrypted", sa.LargeBinary(), nullable=True),
        sa.Column("after_state_encrypted", sa.LargeBinary(), nullable=True),
        # Outcome
        sa.Column("result", sa.String(length=16), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        # Network context
        sa.Column("ip", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        # Timestamp
        sa.Column("ts", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Actor + time — "what did admin X do this week?"
    op.create_index("ix_audit_actor_ts", "aegis_audit_events", ["actor_id", "ts"])

    # Action + time — "when was this route called?"
    op.create_index("ix_audit_action_ts", "aegis_audit_events", ["action", "ts"])

    # Target + time — "what happened to user/plan 42?"
    op.create_index(
        "ix_audit_target_ts",
        "aegis_audit_events",
        ["target_type", "target_id", "ts"],
    )

    # Timestamp-only — used by retention sweep (DELETE WHERE ts < cutoff).
    op.create_index("ix_audit_ts", "aegis_audit_events", ["ts"])


def downgrade() -> None:
    op.drop_index("ix_audit_ts", table_name="aegis_audit_events")
    op.drop_index("ix_audit_target_ts", table_name="aegis_audit_events")
    op.drop_index("ix_audit_action_ts", table_name="aegis_audit_events")
    op.drop_index("ix_audit_actor_ts", table_name="aegis_audit_events")
    op.drop_table("aegis_audit_events")
