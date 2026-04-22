"""
Smoke tests for ``ops.billing.db`` — validates that:

1. The module imports without side effects beyond SQLAlchemy
   metadata registration (A.1.2+ will add behavior tests on the
   state machine + pricing once those modules exist).
2. All five tables are registered on the shared ``Base.metadata``
   under the expected names.
3. ``Base.metadata.create_all()`` on an in-memory SQLite succeeds —
   catches dialect errors in column types or indexes before the
   Alembic migration even runs.
4. Composite indexes enumerated in the SPEC are actually present.
5. The FK cascade on ``invoice_lines.invoice_id`` is declared.

These run under both SQLite (existing CI job) and PostgreSQL 16
(PR #23's dual-DB job) — passing on both means the Alembic
migration pattern is compatible with both dialects before we
actually use the tables.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, inspect


def test_module_imports_cleanly():
    """Sanity: importing the module doesn't error or side-effect
    beyond table registration."""
    import ops.billing.db as billing_db  # noqa: F401


def test_all_five_tables_registered():
    """Each SPEC-declared table name is present on Base.metadata."""
    import ops.billing.db  # noqa: F401  # side-effect: register models
    from app.db.base import Base

    expected = {
        "aegis_billing_plans",
        "aegis_billing_channels",
        "aegis_billing_invoices",
        "aegis_billing_invoice_lines",
        "aegis_billing_payment_events",
    }
    actual = set(Base.metadata.tables.keys())
    missing = expected - actual
    assert not missing, (
        f"billing tables missing from metadata: {sorted(missing)}. "
        "Check ops/billing/db.py imports a shared Base and that "
        "env.py (or an aggregator) registers the module."
    )


def test_create_all_on_sqlite_in_memory():
    """``create_all`` on a fresh SQLite works; catches column/dialect
    errors before the Alembic migration runs."""
    # Use an isolated Base so we don't collide with other tests that
    # may have already created tables on the shared engine. We
    # re-declare our five tables here via the module's classes by
    # inheriting from the shared Base but creating a scratch engine.
    import ops.billing.db  # noqa: F401
    from app.db.base import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    for name in (
        "aegis_billing_plans",
        "aegis_billing_channels",
        "aegis_billing_invoices",
        "aegis_billing_invoice_lines",
        "aegis_billing_payment_events",
    ):
        assert (
            name in table_names
        ), f"create_all didn't materialize {name} on SQLite"


def test_invoice_composite_indexes_declared():
    """The two composite indexes on invoices are part of metadata."""
    import ops.billing.db  # noqa: F401
    from app.db.base import Base

    tbl = Base.metadata.tables["aegis_billing_invoices"]
    index_names = {ix.name for ix in tbl.indexes}
    assert "ix_billing_invoices_state_expires" in index_names
    assert "ix_billing_invoices_user_state" in index_names


def test_invoices_provider_correlation_unique_constraint():
    """Webhook replay safety: (provider, provider_invoice_id) is
    unique so double-processing the same remote invoice is a hard
    DB violation, not a silent re-apply."""
    import ops.billing.db  # noqa: F401
    from app.db.base import Base

    tbl = Base.metadata.tables["aegis_billing_invoices"]
    unique_cols = [
        frozenset(c.name for c in uc.columns)
        for uc in tbl.constraints
        if uc.__class__.__name__ == "UniqueConstraint"
    ]
    assert frozenset({"provider", "provider_invoice_id"}) in unique_cols


def test_invoice_line_cascade_on_invoice_delete():
    """Deleting an invoice (admin cancel, not a normal user path)
    cascades to its lines — otherwise we'd leak orphan rows."""
    import ops.billing.db  # noqa: F401
    from app.db.base import Base

    tbl = Base.metadata.tables["aegis_billing_invoice_lines"]
    fk = next(
        iter(
            fk
            for fk in tbl.foreign_keys
            if fk.column.table.name == "aegis_billing_invoices"
        )
    )
    assert fk.ondelete == "CASCADE", (
        "invoice_lines.invoice_id FK must be ON DELETE CASCADE "
        "so cleaning a test/canceled invoice doesn't leave orphan "
        "line rows."
    )


def test_payment_events_has_no_cascade_from_invoices():
    """Audit log survives invoice deletion. If a cascade ever sneaks
    in, we'd silently lose forensic records — block that now."""
    import ops.billing.db  # noqa: F401
    from app.db.base import Base

    tbl = Base.metadata.tables["aegis_billing_payment_events"]
    for fk in tbl.foreign_keys:
        if fk.column.table.name == "aegis_billing_invoices":
            assert fk.ondelete in (None, ""), (
                "payment_events.invoice_id must NOT cascade on delete. "
                "Audit log is append-only and survives everything."
            )


def test_plan_kinds_constants_match_spec():
    """The plan kind constants in db.py match what SPEC committed to.
    Guards against typos that'd break admin-form validation in A.1.3."""
    from ops.billing import db as billing_db

    assert billing_db.PLAN_KIND_FIXED == "fixed"
    assert billing_db.PLAN_KIND_FLEXIBLE_TRAFFIC == "flexible_traffic"
    assert billing_db.PLAN_KIND_FLEXIBLE_DURATION == "flexible_duration"
    assert set(billing_db.PLAN_KINDS) == {
        "fixed",
        "flexible_traffic",
        "flexible_duration",
    }


def test_invoice_state_constants_cover_spec_states():
    """The 8 states enumerated in SPEC all have matching constants —
    ops.billing.states (A.1.2) will rely on these for its transition
    table."""
    from ops.billing import db as billing_db

    required = {
        "created",
        "pending",
        "awaiting_payment",
        "paid",
        "applied",
        "expired",
        "cancelled",
        "failed",
    }
    assert set(billing_db.INVOICE_STATES) == required


# Avoid import-time guard for unused symbol warnings.
_ = pytest
