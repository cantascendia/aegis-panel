"""audit-log Phase 1: aegis_audit_events table

Revision ID: d4e5f6a7b8c9
Revises: c3d2e1f4a5b6
Create Date: 2026-04-30 12:00:00.000000

S-AL Phase 1 (audit-log MVP) — single append-only table for the
panel-wide audit trail. Powers operator追责 / 客诉举证 / RBAC
actor-role 联动.

Design notes honored here vs the model (``ops/audit/db.py``):

- **Append-only.** No UPDATE / DELETE paths from app code; only the
  retention sweep (AL.4) ever issues DELETE.
- **No FK to admins.id.** ``actor_id`` is a soft reference; we keep
  ``actor_username`` as a snapshot column so admin renames /
  deletions do not corrupt the historical record.
- **No FK from / to billing.payment_events** (D-018 TBD-3 SEALED) —
  billing remains autonomous; cross-table queries use
  ``(invoice_id, ts)`` ranges.
- **Naive UTC timestamps** matching the ``ops/billing/db.py``
  precedent — wall-clock UTC without tzinfo, zero noise on Alembic
  autogenerate.
- **Indexes** mirror ``__table_args__``:
  - ``ix_audit_actor_ts`` — actor history lookup
  - ``ix_audit_action_ts`` — action history lookup
  - ``ix_audit_target_ts`` — target history lookup
  - column-level index on ``ts`` (drives retention sweep DELETE)
- **No DB CHECK** on enum-like ``result`` / ``actor_type`` columns —
  vocabulary lives in ``ops/audit/db.py`` constants so it can evolve
  without migrations (same convention as ``ops.billing.states``).

LESSONS L-015 invariant: this revision will never be mutated after
merge. Schema changes get a new revision.
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
        sa.Column("id", sa.BigInteger(), primary_key=True),
        # Actor
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("actor_type", sa.String(length=16), nullable=False),
        sa.Column("actor_username", sa.String(length=64), nullable=True),
        # Action
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("method", sa.String(length=8), nullable=False),
        sa.Column("path", sa.String(length=512), nullable=False),
        # Target
        sa.Column("target_type", sa.String(length=64), nullable=True),
        sa.Column("target_id", sa.String(length=96), nullable=True),
        # State diff (Fernet-encrypted by AL.2 middleware)
        sa.Column("before_state_encrypted", sa.LargeBinary(), nullable=True),
        sa.Column("after_state_encrypted", sa.LargeBinary(), nullable=True),
        # Result
        sa.Column("result", sa.String(length=16), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.String(length=512), nullable=True),
        # Context
        sa.Column("ip", sa.String(length=45), nullable=False),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        # ts: naive UTC, indexed (drives retention sweep)
        sa.Column("ts", sa.DateTime(), nullable=False),
    )
    # Composite indexes from the model's __table_args__.
    op.create_index(
        "ix_audit_actor_ts",
        "aegis_audit_events",
        ["actor_id", "ts"],
    )
    op.create_index(
        "ix_audit_action_ts",
        "aegis_audit_events",
        ["action", "ts"],
    )
    op.create_index(
        "ix_audit_target_ts",
        "aegis_audit_events",
        ["target_type", "target_id", "ts"],
    )
    # Column-level index on ts (matches ``index=True`` in the model;
    # named to mirror the Alembic-autogenerate convention).
    op.create_index(
        "ix_aegis_audit_events_ts",
        "aegis_audit_events",
        ["ts"],
    )


def downgrade() -> None:
    op.drop_index("ix_aegis_audit_events_ts", table_name="aegis_audit_events")
    op.drop_index("ix_audit_target_ts", table_name="aegis_audit_events")
    op.drop_index("ix_audit_action_ts", table_name="aegis_audit_events")
    op.drop_index("ix_audit_actor_ts", table_name="aegis_audit_events")
    op.drop_table("aegis_audit_events")
