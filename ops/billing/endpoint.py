"""
Admin REST API for the billing layer.

Mounted by ``hardening.panel.middleware.apply_panel_hardening``
under ``/api/billing/admin/*``. Every route is gated by
``SudoAdminDep``; no user-facing routes live here yet (A.4 will
add them in ``/api/billing/cart``, ``/api/billing/invoices/me``,
etc.).

Endpoints:

  GET   /api/billing/admin/plans                   list all plans
  POST  /api/billing/admin/plans                   create plan
  PATCH /api/billing/admin/plans/{id}              update/disable
  GET   /api/billing/admin/channels                list payment channels
  POST  /api/billing/admin/channels                create EPay channel
  PATCH /api/billing/admin/channels/{id}           update/disable
  GET   /api/billing/admin/invoices                list w/ filters
  GET   /api/billing/admin/invoices/{id}           one invoice + lines
  GET   /api/billing/admin/invoices/{id}/events    audit trail
  POST  /api/billing/admin/invoices/{id}/apply_manual   emergency activate
  POST  /api/billing/admin/invoices/{id}/cancel    mark cancelled

No DELETE routes — plans and channels are disabled via PATCH;
invoices are cancelled via the explicit action endpoint. The
PaymentEvent audit log survives everything.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Body, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.dependencies import DBDep, SudoAdminDep
from ops.billing.db import (
    INVOICE_STATE_AWAITING_PAYMENT,
    INVOICE_STATE_CANCELLED,
    INVOICE_STATE_CREATED,
    INVOICE_STATE_PAID,
    INVOICE_STATE_PENDING,
    Invoice,
    PaymentChannel,
    PaymentEvent,
    Plan,
)
from ops.billing.schemas import (
    ChannelIn,
    ChannelOut,
    ChannelPatch,
    InvoiceAdminActionIn,
    InvoiceOut,
    PaymentEventOut,
    PlanIn,
    PlanOut,
    PlanPatch,
)
from ops.billing.states import (
    InvoiceStateError,
    is_terminal,
    transition,
)

router = APIRouter(prefix="/api/billing/admin", tags=["Billing Admin"])


# ---------------------------------------------------------------------
# Plan CRUD
# ---------------------------------------------------------------------


@router.get("/plans", response_model=list[PlanOut])
def list_plans(
    db: DBDep,
    admin: SudoAdminDep,  # noqa: ARG001  # auth gate
    include_disabled: bool = Query(default=True),
) -> list[Plan]:
    """List plans. Admin sees disabled by default (differs from the
    future user endpoint, which will filter to enabled-only)."""
    stmt = select(Plan).order_by(Plan.sort_order, Plan.id)
    if not include_disabled:
        stmt = stmt.where(Plan.enabled.is_(True))
    return list(db.execute(stmt).scalars().all())


@router.post(
    "/plans", response_model=PlanOut, status_code=status.HTTP_201_CREATED
)
def create_plan(
    body: Annotated[PlanIn, Body()],
    db: DBDep,
    admin: SudoAdminDep,  # noqa: ARG001
) -> Plan:
    existing = db.execute(
        select(Plan).where(Plan.operator_code == body.operator_code)
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=f"operator_code {body.operator_code!r} already exists",
        )
    plan = Plan(**body.model_dump())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.patch("/plans/{plan_id}", response_model=PlanOut)
def update_plan(
    plan_id: int,
    body: Annotated[PlanPatch, Body()],
    db: DBDep,
    admin: SudoAdminDep,  # noqa: ARG001
) -> Plan:
    plan = db.get(Plan, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="plan not found")

    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(plan, field, value)
    db.commit()
    db.refresh(plan)
    return plan


# ---------------------------------------------------------------------
# PaymentChannel CRUD
# ---------------------------------------------------------------------


@router.get("/channels", response_model=list[ChannelOut])
def list_channels(
    db: DBDep,
    admin: SudoAdminDep,  # noqa: ARG001
) -> list[PaymentChannel]:
    """List payment channels. Disabled entries included so admin
    can re-enable after fixing credentials."""
    stmt = select(PaymentChannel).order_by(
        PaymentChannel.priority.desc(), PaymentChannel.id
    )
    return list(db.execute(stmt).scalars().all())


@router.post(
    "/channels",
    response_model=ChannelOut,
    status_code=status.HTTP_201_CREATED,
)
def create_channel(
    body: Annotated[ChannelIn, Body()],
    db: DBDep,
    admin: SudoAdminDep,  # noqa: ARG001
) -> PaymentChannel:
    existing = db.execute(
        select(PaymentChannel).where(
            PaymentChannel.channel_code == body.channel_code
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=f"channel_code {body.channel_code!r} already exists",
        )

    # Prefer the new ``merchant_key`` field; fall back to the legacy
    # ``secret_key`` alias. Encrypt before persist; legacy plaintext
    # column is no longer written by new rows.
    plaintext_key = body.merchant_key or body.secret_key or ""
    channel = PaymentChannel(
        channel_code=body.channel_code,
        display_name=body.display_name,
        kind=body.kind,
        gateway_url=body.gateway_url,
        merchant_id=body.merchant_id,
        enabled=body.enabled,
        priority=body.priority,
    )
    _apply_channel_secret(channel, plaintext_key)
    _apply_extra_config(channel, body.extra_config)
    db.add(channel)
    db.commit()
    db.refresh(channel)
    return channel


@router.patch("/channels/{channel_id}", response_model=ChannelOut)
def update_channel(
    channel_id: int,
    body: Annotated[ChannelPatch, Body()],
    db: DBDep,
    admin: SudoAdminDep,  # noqa: ARG001
) -> PaymentChannel:
    channel = db.get(PaymentChannel, channel_id)
    if channel is None:
        raise HTTPException(status_code=404, detail="channel not found")

    updates = body.model_dump(exclude_unset=True)
    new_plaintext_key = updates.pop("merchant_key", None)
    legacy_secret_key = updates.pop("secret_key", None)
    extra_config = updates.pop("extra_config", None)

    for field, value in updates.items():
        setattr(channel, field, value)

    if new_plaintext_key is not None or legacy_secret_key is not None:
        _apply_channel_secret(
            channel, new_plaintext_key or legacy_secret_key or ""
        )
    if extra_config is not None:
        _apply_extra_config(channel, body.extra_config)

    db.commit()
    db.refresh(channel)
    return channel


def _apply_channel_secret(channel: PaymentChannel, plaintext: str) -> None:
    """Fernet-encrypt ``plaintext`` and write to
    ``merchant_key_encrypted``; clear the legacy plaintext column.

    Empty ``plaintext`` means "clear the credential" — both columns
    land on None, and the channel effectively becomes unusable until
    re-credentialed.
    """
    from ops.billing.config import BillingMisconfigured, encrypt_merchant_key

    if not plaintext:
        channel.merchant_key_encrypted = None
        channel.secret_key = None
        return
    try:
        channel.merchant_key_encrypted = encrypt_merchant_key(plaintext)
    except BillingMisconfigured as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Billing encryption key is not configured. Set "
                "BILLING_SECRET_KEY in the panel environment before "
                "creating payment channels."
            ),
        ) from exc
    channel.secret_key = None


def _apply_extra_config(channel: PaymentChannel, extra: Any) -> None:
    if extra is None:
        return
    # ``extra`` is a ChannelExtraConfig Pydantic model — dump to dict,
    # drop None values so stored JSON stays compact.
    payload = (
        extra.model_dump(exclude_none=True)
        if hasattr(extra, "model_dump")
        else dict(extra)
    )
    channel.extra_config_json = payload or None


# ---------------------------------------------------------------------
# Invoice read + admin actions
# ---------------------------------------------------------------------


@router.get("/invoices", response_model=list[InvoiceOut])
def list_invoices(
    db: DBDep,
    admin: SudoAdminDep,  # noqa: ARG001
    state: str | None = Query(default=None),
    user_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[Invoice]:
    stmt = (
        select(Invoice)
        .options(selectinload(Invoice.lines))
        .order_by(Invoice.id.desc())
        .limit(limit)
        .offset(offset)
    )
    if state is not None:
        stmt = stmt.where(Invoice.state == state)
    if user_id is not None:
        stmt = stmt.where(Invoice.user_id == user_id)
    return list(db.execute(stmt).scalars().all())


@router.get("/invoices/{invoice_id}", response_model=InvoiceOut)
def get_invoice(
    invoice_id: int,
    db: DBDep,
    admin: SudoAdminDep,  # noqa: ARG001
) -> Invoice:
    stmt = (
        select(Invoice)
        .options(selectinload(Invoice.lines))
        .where(Invoice.id == invoice_id)
    )
    invoice = db.execute(stmt).scalar_one_or_none()
    if invoice is None:
        raise HTTPException(status_code=404, detail="invoice not found")
    return invoice


@router.get(
    "/invoices/{invoice_id}/events",
    response_model=list[PaymentEventOut],
)
def list_invoice_events(
    invoice_id: int,
    db: DBDep,
    admin: SudoAdminDep,  # noqa: ARG001
) -> list[PaymentEvent]:
    """Audit trail for one invoice, chronological."""
    if db.get(Invoice, invoice_id) is None:
        raise HTTPException(status_code=404, detail="invoice not found")
    stmt = (
        select(PaymentEvent)
        .where(PaymentEvent.invoice_id == invoice_id)
        .order_by(PaymentEvent.created_at, PaymentEvent.id)
    )
    return list(db.execute(stmt).scalars().all())


@router.post(
    "/invoices/{invoice_id}/apply_manual",
    response_model=InvoiceOut,
)
def apply_manual(
    invoice_id: int,
    body: Annotated[InvoiceAdminActionIn, Body()],
    db: DBDep,
    admin: SudoAdminDep,
) -> Invoice:
    """Emergency bypass of normal payment flow.

    Transitions the invoice through ``paid`` and then calls
    :func:`ops.billing.scheduler.apply_invoice_grant` to mutate
    ``User.data_limit`` / ``User.expire_date`` and land
    ``state=applied`` in one synchronous request — the admin doesn't
    have to wait for the A.5 scheduler tick (~30s) for the user to
    actually receive their grant.

    This mirrors the scheduler's own ``apply_paid_invoices`` path, so
    EPay-webhook / TRC20-poller / admin-manual all converge on a
    single grant-application code path. Channel-agnostic by design;
    do not branch on ``invoice.provider`` here.

    Audit rows written (in order):
    - ``admin_manual:to_pending`` (if invoice was ``created``)
    - ``admin_manual:to_paid``    (the admin override leg)
    - ``state_applied``           (written by ``apply_invoice_grant``;
      payload includes user_id + before/after data_limit/expire deltas)

    Failure modes:
    - 409 when invoice is already terminal (``applied``, ``cancelled``,
      ``expired``, ``failed``).
    - 409 when the grant cannot be applied (user hard-deleted, plan
      removed, cart no longer valid). The invoice remains in
      ``paid`` for operator follow-up; ``apply_paid_invoices``
      scheduler will continue retrying on each tick if the
      underlying state is fixable, otherwise an operator must cancel
      and refund.
    """
    # Local import to avoid an endpoint↔scheduler import cycle at
    # module load (scheduler imports trc20_poller which imports the
    # FastAPI router lifespan code path).
    from ops.billing.scheduler import ApplierSkip, apply_invoice_grant

    invoice = _require_invoice(db, invoice_id)
    if is_terminal(invoice.state):
        raise HTTPException(
            status_code=409,
            detail=(
                f"invoice already terminal ({invoice.state}); "
                "cannot apply_manual"
            ),
        )

    try:
        # Route: <any non-terminal> → paid → (apply grant) → applied.
        # The state machine allows pending→paid as an admin emergency
        # path (see ops.billing.states.ALLOWED_TRANSITIONS). For
        # ``created`` we hop through ``pending`` first.
        if invoice.state == INVOICE_STATE_CREATED:
            transition(
                db,
                invoice,
                INVOICE_STATE_PENDING,
                event_type="admin_manual:to_pending",
                payload={"admin_username": admin.username},
                note=body.note,
            )
        if invoice.state in (
            INVOICE_STATE_PENDING,
            INVOICE_STATE_AWAITING_PAYMENT,
        ):
            transition(
                db,
                invoice,
                INVOICE_STATE_PAID,
                event_type="admin_manual:to_paid",
                payload={"admin_username": admin.username},
                note=body.note,
            )
        # invoice.state should now be ``paid``; defensive guard so a
        # future state-machine change that diverts the path produces
        # a clear 409 instead of a confusing helper-internal error.
        if invoice.state != INVOICE_STATE_PAID:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"invoice in unexpected state {invoice.state!r} "
                    "after admin_manual transition chain; cannot apply"
                ),
            )

        # Single source of truth for the grant + paid→applied flip.
        # Same helper the A.5 scheduler uses for paid invoices.
        apply_invoice_grant(db, invoice, now=None)
    except InvoiceStateError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e)) from e
    except ApplierSkip as e:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=(
                f"cannot apply grant for invoice {invoice_id}: "
                f"{e.reason}: {e}"
            ),
        ) from e

    db.commit()
    db.refresh(invoice)
    return invoice


@router.post("/invoices/{invoice_id}/cancel", response_model=InvoiceOut)
def cancel_invoice(
    invoice_id: int,
    body: Annotated[InvoiceAdminActionIn, Body()],
    db: DBDep,
    admin: SudoAdminDep,
) -> Invoice:
    """Mark invoice as cancelled. Only works on non-terminal
    states; already-applied / already-expired / already-failed
    invoices cannot be retroactively cancelled (their audit log
    is the source of truth)."""
    invoice = _require_invoice(db, invoice_id)
    if is_terminal(invoice.state):
        raise HTTPException(
            status_code=409,
            detail=(
                f"invoice already terminal ({invoice.state}); " "cannot cancel"
            ),
        )
    try:
        transition(
            db,
            invoice,
            INVOICE_STATE_CANCELLED,
            event_type="admin_cancel",
            payload={"admin_username": admin.username},
            note=body.note,
        )
    except InvoiceStateError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e)) from e
    db.commit()
    db.refresh(invoice)
    return invoice


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


def _require_invoice(db: Session, invoice_id: int) -> Invoice:
    invoice = db.get(Invoice, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="invoice not found")
    return invoice


__all__ = ["router"]
