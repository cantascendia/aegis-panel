"""iplimit disabled state safety net

Revision ID: 44c0b755e487
Revises: a1c4b7f9e201
Create Date: 2026-04-23 00:00:00.000000

Context — this migration exists because revision ``4f7b7c8e9d10``
(``iplimit policy tables``) was mutated after being merged to main:
PR #26 added the ``aegis_iplimit_disabled_state`` table directly to
the already-merged ``4f7b7c8e9d10.upgrade()`` body instead of landing
it in a new revision.

Alembic only tracks the revision id in ``alembic_version`` — it does
not diff content. Any environment that ran ``alembic upgrade head``
between the PR #24 merge and the PR #26 merge now has
``alembic_version.version_num = 4f7b7c8e9d10`` and will NEVER create
the new table, because ``4f7b7c8e9d10`` is already marked done.

This safety net idempotently creates the table for those stuck
environments. Fresh environments (where ``4f7b7c8e9d10`` ran AFTER
the mutation) already have the table, so we skip.

See ``docs/ai-cto/LESSONS.md`` L-015 / L-016 for the full lesson:
an already-merged Alembic revision is immutable; fresh-DB CI
gives false-green on this class of bug.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "44c0b755e487"
down_revision = "a1c4b7f9e201"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "aegis_iplimit_disabled_state" in inspector.get_table_names():
        # Environment ran 4f7b7c8e9d10 AFTER the PR #26 mutation;
        # table already exists. No-op.
        return

    op.create_table(
        "aegis_iplimit_disabled_state",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("disabled_until", sa.Integer(), nullable=False),
        sa.Column("disabled_at", sa.Integer(), nullable=False),
        sa.Column("previous_enabled", sa.Boolean(), nullable=False),
        sa.Column("previous_activated", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    # Intentional no-op.
    #
    # The mutated ``4f7b7c8e9d10.downgrade()`` unconditionally drops
    # ``aegis_iplimit_disabled_state`` (PR #26 changed both upgrade
    # AND downgrade bodies of the already-merged revision). If we
    # also dropped here, downgrading all the way to
    # ``57eba0a293f2`` would try to drop the table twice and fail
    # with "no such table".
    #
    # Cost: downgrading from head to ``a1c4b7f9e201`` and stopping
    # there leaves the table orphaned in the DB. Harmless — no ORM
    # model references it at that point — and downgrade is always
    # a break-glass operation anyway.
    #
    # The correct long-term fix is to not mutate merged revisions;
    # see ``docs/ai-cto/LESSONS.md`` L-015.
    pass
