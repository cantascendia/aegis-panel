"""
Tests for the ``apply_manual`` admin endpoint's grant-application
integration (P0 production hot-fix).

Wave-9 R3 operator self-test discovered: ``apply_manual`` set
``invoice.state=applied`` and wrote audit rows but did NOT mutate
``User.data_limit`` / ``User.expire_date`` — the user got nothing.
The fix: ``apply_manual`` now calls
:func:`ops.billing.scheduler.apply_invoice_grant` inline, mirroring
the A.5 scheduler path.

These tests are deliberately separate from
``test_billing_endpoint.py`` so the production-bug regression suite
is easy to grep / re-run and so the file-level docstring documents
*why* this lives in its own module.

Test scope:

- ``apply_manual`` MUST mutate ``User.data_limit`` and
  ``User.expire_date`` synchronously (the bug).
- ``apply_manual`` MUST write a ``state_applied`` event whose
  payload records before/after deltas (audit-trail parity with
  scheduler).
- Already-terminal invoices MUST be rejected with HTTP 409 (no
  silent double-apply).
- Calling ``apply_manual`` twice MUST not double-grant — the second
  call sees the first transition's ``applied`` state and raises
  the terminal-state guard (defence in depth on top of the state
  machine).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import User
from app.models.user import UserDataUsageResetStrategy, UserExpireStrategy
from ops.billing.db import (
    INVOICE_STATE_APPLIED,
    INVOICE_STATE_AWAITING_PAYMENT,
    PLAN_KIND_FIXED,
    Invoice,
    InvoiceLine,
    PaymentEvent,
    Plan,
)
from ops.billing.grants import _BYTES_PER_GB

_NOW_REF = datetime(2026, 5, 1, 12, 0, 0)


# --------------------------------------------------------------------------
# Fixtures — mirror test_billing_endpoint.py + test_billing_scheduler.py
# --------------------------------------------------------------------------


@pytest.fixture
def billing_engine():
    """Fresh SQLite with billing + users tables."""
    needed = [
        Base.metadata.tables[name]
        for name in (
            "aegis_billing_plans",
            "aegis_billing_channels",
            "aegis_billing_invoices",
            "aegis_billing_invoice_lines",
            "aegis_billing_payment_events",
            "users",
            "services",
            "users_services",
            "inbounds",
            "inbounds_services",
            # Needed when a test deletes a User to force ApplierSkip;
            # SQLAlchemy cascades through node_user_usages.
            "node_user_usages",
            "nodes",
        )
    ]
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=needed)
    yield engine
    engine.dispose()


@pytest.fixture
def fake_sudo_admin() -> Any:
    class _A:
        username = "test-sudo"
        is_sudo = True
        enabled = True

    return _A()


@pytest.fixture
def app_with_billing(billing_engine, fake_sudo_admin):
    from app.dependencies import get_db, sudo_admin
    from ops.billing.endpoint import router as billing_router

    app = FastAPI()
    app.include_router(billing_router)

    def _db_override():
        with Session(billing_engine) as s:
            yield s

    def _admin_override():
        return fake_sudo_admin

    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[sudo_admin] = _admin_override
    return app


@pytest.fixture
def client(app_with_billing) -> TestClient:
    return TestClient(app_with_billing)


def _seed(
    engine,
    *,
    state: str = INVOICE_STATE_AWAITING_PAYMENT,
    user_data_limit: int | None = 50 * _BYTES_PER_GB,
    plan_data_limit_gb: int = 100,
    plan_duration_days: int = 30,
) -> tuple[int, int]:
    """Insert User + Plan + Invoice + Line. Returns (invoice_id, user_id)."""
    with Session(engine) as s:
        user = User(
            username="nilou_trial01",
            key="knilou",
            activated=True,
            enabled=True,
            removed=False,
            data_limit=user_data_limit,
            data_limit_reset_strategy=UserDataUsageResetStrategy.no_reset,
            expire_strategy=UserExpireStrategy.NEVER,
            expire_date=None,
            ip_limit=-1,
            used_traffic=0,
            lifetime_used_traffic=0,
            created_at=_NOW_REF,
        )
        s.add(user)
        s.flush()

        plan = Plan(
            operator_code="m1",
            display_name_en="m1",
            display_name_i18n={},
            kind=PLAN_KIND_FIXED,
            data_limit_gb=plan_data_limit_gb,
            duration_days=plan_duration_days,
            price_cny_fen=3000,
            enabled=True,
            sort_order=0,
            created_at=_NOW_REF,
        )
        s.add(plan)
        s.flush()

        inv = Invoice(
            user_id=user.id,
            total_cny_fen=3000,
            state=state,
            provider="trc20",
            created_at=_NOW_REF,
            expires_at=_NOW_REF + timedelta(minutes=30),
        )
        s.add(inv)
        s.flush()
        s.add(
            InvoiceLine(
                invoice_id=inv.id,
                plan_id=plan.id,
                quantity=1,
                unit_price_fen_at_purchase=3000,
            )
        )
        s.commit()
        return inv.id, user.id


# --------------------------------------------------------------------------
# The four contracts
# --------------------------------------------------------------------------


def test_apply_manual_applies_grant_immediately(client, billing_engine):
    """The headline regression: post-apply_manual, the User row must
    actually carry the new data_limit and expire_date.

    Production reproduction: m1 plan = 100 GB / 30 days; user starts
    at 50 GB / NEVER-expire; after apply_manual user must show
    150 GB and expire_date ≈ now + 30 days.
    """
    invoice_id, user_id = _seed(billing_engine)

    r = client.post(
        f"/api/billing/admin/invoices/{invoice_id}/apply_manual",
        json={"note": "operator manual grant for nilou_trial01"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["state"] == INVOICE_STATE_APPLIED

    with Session(billing_engine) as s:
        user = s.get(User, user_id)
        assert user is not None
        # 50 GB baseline + 100 GB grant = 150 GB
        expected_bytes = (50 + 100) * _BYTES_PER_GB
        assert (
            user.data_limit == expected_bytes
        ), f"data_limit not extended: {user.data_limit} != {expected_bytes}"
        # Expire strategy promoted from NEVER → FIXED_DATE; date in
        # the future (~30 days from "now"). We don't pin the exact
        # timestamp because apply_manual uses _now_utc_naive().
        assert user.expire_strategy == UserExpireStrategy.FIXED_DATE
        assert user.expire_date is not None
        # At least 29 days out (loose lower bound — accounts for any
        # clock drift between fixture and helper invocation). Both
        # sides naive UTC to match the column shape (see
        # ops.billing.db._now_utc_naive).
        from datetime import UTC

        now_naive = datetime.now(UTC).replace(tzinfo=None)
        delta = user.expire_date - now_naive
        assert delta > timedelta(days=29), f"expire_date too close: {delta}"


def test_apply_manual_writes_state_applied_event_with_grant_payload(
    client, billing_engine
):
    """The audit trail must record the grant deltas, just like the
    A.5 scheduler does — same ``state_applied`` event_type + same
    payload shape. This guarantees admins reading the audit log
    can't tell the difference between scheduler-applied and
    manually-applied grants.
    """
    invoice_id, user_id = _seed(billing_engine)

    r = client.post(
        f"/api/billing/admin/invoices/{invoice_id}/apply_manual",
        json={"note": "audit-trail check"},
    )
    assert r.status_code == 200, r.text

    with Session(billing_engine) as s:
        events = (
            s.query(PaymentEvent)
            .filter(PaymentEvent.invoice_id == invoice_id)
            .order_by(PaymentEvent.id)
            .all()
        )
        types = [e.event_type for e in events]
        # Full chain: → paid (admin manual) → applied (grant helper)
        assert "admin_manual:to_paid" in types
        assert "state_applied" in types

        applied_event = next(
            e for e in events if e.event_type == "state_applied"
        )
        payload = applied_event.payload_json
        assert payload["user_id"] == user_id
        assert payload["grant_gb_delta"] == 100
        assert payload["grant_days_delta"] == 30
        # Before / after data_limit deltas
        assert payload["data_limit_bytes_before"] == 50 * _BYTES_PER_GB
        assert payload["data_limit_bytes_after"] == 150 * _BYTES_PER_GB


def test_apply_manual_terminal_invoice_returns_409(client, billing_engine):
    """An already-applied invoice must NOT be re-processed: 409 on
    the endpoint, no extra grant on the user row, no extra event
    written. Defence against an admin double-clicking the button.
    """
    invoice_id, user_id = _seed(billing_engine)

    # First apply: success.
    r1 = client.post(
        f"/api/billing/admin/invoices/{invoice_id}/apply_manual",
        json={"note": "first apply"},
    )
    assert r1.status_code == 200

    # Snapshot the user row + event count after the legitimate apply.
    with Session(billing_engine) as s:
        user_after_first = s.get(User, user_id)
        assert user_after_first is not None
        first_data_limit = user_after_first.data_limit
        first_event_count = (
            s.query(PaymentEvent)
            .filter(PaymentEvent.invoice_id == invoice_id)
            .count()
        )

    # Second apply: the invoice is now ``applied`` (terminal). Must 409.
    r2 = client.post(
        f"/api/billing/admin/invoices/{invoice_id}/apply_manual",
        json={"note": "double-click defence"},
    )
    assert r2.status_code == 409, r2.text

    # User row + audit log unchanged by the rejected second call.
    with Session(billing_engine) as s:
        user_after_second = s.get(User, user_id)
        assert user_after_second is not None
        assert (
            user_after_second.data_limit == first_data_limit
        ), "double-apply leaked through the terminal-state guard"
        second_event_count = (
            s.query(PaymentEvent)
            .filter(PaymentEvent.invoice_id == invoice_id)
            .count()
        )
        assert (
            second_event_count == first_event_count
        ), "rejected double-apply still wrote audit rows"


def test_apply_manual_failed_grant_leaves_invoice_in_paid(
    client, billing_engine
):
    """When the operator confirms payment but the grant cannot be
    applied (e.g. user was hard-deleted between checkout and admin
    intervention), the invoice MUST land in ``paid`` — not be rolled
    back to ``awaiting_payment``. Otherwise the A.5 scheduler won't
    retry once the underlying issue is fixed, and the reaper might
    auto-expire a payment that the operator manually verified.

    P2 finding from codex cross-review on the initial fix.
    """
    invoice_id, user_id = _seed(billing_engine)

    # Hard-delete the user to force ApplierSkip("user_missing").
    with Session(billing_engine) as s:
        user = s.get(User, user_id)
        s.delete(user)
        s.commit()

    r = client.post(
        f"/api/billing/admin/invoices/{invoice_id}/apply_manual",
        json={"note": "operator confirmed payment, user race"},
    )
    assert r.status_code == 409, r.text
    assert "user_missing" in r.json()["detail"]

    # Critical: invoice is in ``paid``, NOT rolled back to
    # awaiting_payment. The ``admin_manual:to_paid`` event survives.
    with Session(billing_engine) as s:
        inv = s.get(Invoice, invoice_id)
        assert inv is not None
        assert inv.state == "paid", (
            f"invoice rolled back to {inv.state!r}; operator's payment "
            "confirmation lost"
        )
        types = [
            e.event_type
            for e in s.query(PaymentEvent)
            .filter(PaymentEvent.invoice_id == invoice_id)
            .all()
        ]
        assert "admin_manual:to_paid" in types


def test_apply_manual_idempotent_against_double_call(client, billing_engine):
    """Stronger statement: even if two operators race the button at
    the same moment, the user can only be granted ONCE. Test by
    invoking apply_manual twice in quick succession and asserting
    the user row was extended only once.

    The first call should succeed (200) and the second must fail
    with 409 — never both succeed.
    """
    invoice_id, user_id = _seed(billing_engine)

    responses = [
        client.post(
            f"/api/billing/admin/invoices/{invoice_id}/apply_manual",
            json={"note": f"call {i}"},
        )
        for i in range(2)
    ]
    success = [r for r in responses if r.status_code == 200]
    rejected = [r for r in responses if r.status_code == 409]
    assert len(success) == 1, [r.status_code for r in responses]
    assert len(rejected) == 1, [r.status_code for r in responses]

    # Single grant only: 50 GB + 100 GB == 150 GB (NOT 250 GB).
    with Session(billing_engine) as s:
        user = s.get(User, user_id)
        assert user is not None
        assert user.data_limit == 150 * _BYTES_PER_GB
