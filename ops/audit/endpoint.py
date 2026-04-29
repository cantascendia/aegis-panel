"""Audit log REST API endpoints (S-AL AL.2).

Mounted by ``hardening.panel.middleware.apply_panel_hardening`` under the
existing router mechanism.

Routes
------
  GET   /api/audit/events                  list + filter (sudo-admin)
  GET   /api/audit/events/{id}             single event with decryption (sudo-admin)
  GET   /api/audit/events/export.csv       CSV dump, max 10 000 rows (sudo-admin)
  GET   /api/audit/stats                   7-day summary (sudo-admin)
  GET   /api/audit/me/events               own events, no decryption (any admin)

Access
------
- All routes: ``AUDIT_RETENTION_DAYS == 0`` → 503.
- ``/api/audit/events*`` + ``/api/audit/stats``: sudo-admin only.
- ``/api/audit/me/events``: any authenticated admin (own rows only).
"""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.dependencies import AdminDep, DBDep, SudoAdminDep
from app.models.admin import Admin
from ops.audit.config import AuditMisconfigured, audit_enabled, decrypt_state
from ops.audit.db import AuditEvent
from ops.audit.schemas import (
    AuditEventDetail,
    AuditEventFilter,
    AuditEventRow,
    AuditStatsResponse,
)

router = APIRouter(prefix="/api/audit", tags=["audit"])

_MAX_EXPORT_ROWS = 10_000
_MAX_LIST_LIMIT = 200


def _require_audit_enabled() -> None:
    """Raise 503 when audit log is globally disabled."""
    if not audit_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Audit log is disabled (AUDIT_RETENTION_DAYS=0). "
                "Set AUDIT_RETENTION_DAYS > 0 to enable."
            ),
        )


def _build_query(db: Session, f: AuditEventFilter, *, actor_id_override: int | None = None):
    """Apply filter parameters to a ``AuditEvent`` query."""
    q = db.query(AuditEvent)

    if actor_id_override is not None:
        q = q.filter(AuditEvent.actor_id == actor_id_override)
    elif f.actor_id is not None:
        q = q.filter(AuditEvent.actor_id == f.actor_id)

    if f.actor_username:
        q = q.filter(AuditEvent.actor_username == f.actor_username)
    if f.actor_type:
        q = q.filter(AuditEvent.actor_type == f.actor_type)
    if f.action:
        q = q.filter(AuditEvent.action.contains(f.action))
    if f.result:
        q = q.filter(AuditEvent.result == f.result)
    if f.target_type:
        q = q.filter(AuditEvent.target_type == f.target_type)
    if f.target_id:
        q = q.filter(AuditEvent.target_id == f.target_id)
    if f.ts_from:
        q = q.filter(AuditEvent.ts >= f.ts_from)
    if f.ts_to:
        q = q.filter(AuditEvent.ts <= f.ts_to)
    if f.before_id is not None:
        q = q.filter(AuditEvent.id < f.before_id)

    return q.order_by(AuditEvent.id.desc())


# ── List ──────────────────────────────────────────────────────────────────


@router.get("/events", response_model=list[AuditEventRow])
def list_audit_events(
    db: DBDep,
    admin: SudoAdminDep,
    actor_id: int | None = Query(None),
    actor_username: str | None = Query(None),
    actor_type: str | None = Query(None),
    action: str | None = Query(None),
    result: str | None = Query(None),
    target_type: str | None = Query(None),
    target_id: str | None = Query(None),
    ts_from: datetime | None = Query(None),
    ts_to: datetime | None = Query(None),
    before_id: int | None = Query(None),
    limit: int = Query(50, ge=1, le=_MAX_LIST_LIMIT),
) -> list[AuditEvent]:
    _require_audit_enabled()
    f = AuditEventFilter(
        actor_id=actor_id,
        actor_username=actor_username,
        actor_type=actor_type,
        action=action,
        result=result,
        target_type=target_type,
        target_id=target_id,
        ts_from=ts_from,
        ts_to=ts_to,
        before_id=before_id,
        limit=limit,
    )
    return _build_query(db, f).limit(limit).all()


# ── Detail ────────────────────────────────────────────────────────────────


@router.get("/events/{event_id}", response_model=AuditEventDetail)
def get_audit_event(
    event_id: int,
    db: DBDep,
    admin: SudoAdminDep,
) -> AuditEventDetail:
    _require_audit_enabled()
    event = db.query(AuditEvent).filter(AuditEvent.id == event_id).one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Audit event not found")

    # Decrypt before/after state for sudo-admin.
    try:
        before_state = decrypt_state(event.before_state_encrypted)
        after_state = decrypt_state(event.after_state_encrypted)
    except AuditMisconfigured as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cannot decrypt audit state: {exc}",
        ) from exc

    return AuditEventDetail(
        id=event.id,
        actor_id=event.actor_id,
        actor_type=event.actor_type,
        actor_username=event.actor_username,
        action=event.action,
        method=event.method,
        path=event.path,
        target_type=event.target_type,
        target_id=event.target_id,
        result=event.result,
        status_code=event.status_code,
        error_message=event.error_message,
        ip=event.ip,
        user_agent=event.user_agent,
        request_id=event.request_id,
        ts=event.ts,
        before_state=before_state,
        after_state=after_state,
    )


# ── CSV export ────────────────────────────────────────────────────────────


@router.get("/events/export.csv")
def export_audit_events_csv(
    db: DBDep,
    admin: SudoAdminDep,
    actor_id: int | None = Query(None),
    actor_username: str | None = Query(None),
    actor_type: str | None = Query(None),
    action: str | None = Query(None),
    result: str | None = Query(None),
    ts_from: datetime | None = Query(None),
    ts_to: datetime | None = Query(None),
):
    _require_audit_enabled()
    f = AuditEventFilter(
        actor_id=actor_id,
        actor_username=actor_username,
        actor_type=actor_type,
        action=action,
        result=result,
        ts_from=ts_from,
        ts_to=ts_to,
        limit=_MAX_EXPORT_ROWS,
    )
    events: list[AuditEvent] = _build_query(db, f).limit(_MAX_EXPORT_ROWS).all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "id", "ts", "actor_id", "actor_type", "actor_username",
            "method", "action", "path", "target_type", "target_id",
            "result", "status_code", "error_message", "ip", "user_agent",
        ]
    )
    for e in events:
        writer.writerow(
            [
                e.id, e.ts.isoformat(), e.actor_id, e.actor_type,
                e.actor_username, e.method, e.action, e.path,
                e.target_type, e.target_id, e.result, e.status_code,
                e.error_message, e.ip, e.user_agent,
            ]
        )

    buf.seek(0)
    filename = f"audit-events-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Stats ─────────────────────────────────────────────────────────────────


@router.get("/stats", response_model=AuditStatsResponse)
def get_audit_stats(db: DBDep, admin: SudoAdminDep) -> AuditStatsResponse:
    _require_audit_enabled()
    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=7)

    total_7d: int = (
        db.query(func.count(AuditEvent.id))
        .filter(AuditEvent.ts >= cutoff)
        .scalar()
        or 0
    )

    by_result_rows = (
        db.query(AuditEvent.result, func.count(AuditEvent.id))
        .filter(AuditEvent.ts >= cutoff)
        .group_by(AuditEvent.result)
        .all()
    )
    by_result = {r: c for r, c in by_result_rows}

    by_actor_type_rows = (
        db.query(AuditEvent.actor_type, func.count(AuditEvent.id))
        .filter(AuditEvent.ts >= cutoff)
        .group_by(AuditEvent.actor_type)
        .all()
    )
    by_actor_type = {t: c for t, c in by_actor_type_rows}

    top_actions_rows = (
        db.query(AuditEvent.action, func.count(AuditEvent.id).label("cnt"))
        .filter(AuditEvent.ts >= cutoff)
        .group_by(AuditEvent.action)
        .order_by(func.count(AuditEvent.id).desc())
        .limit(10)
        .all()
    )
    top_actions = [{"action": a, "count": c} for a, c in top_actions_rows]

    return AuditStatsResponse(
        total_7d=total_7d,
        by_result=by_result,
        by_actor_type=by_actor_type,
        top_actions=top_actions,
    )


# ── Own events (any admin) ────────────────────────────────────────────────


@router.get("/me/events", response_model=list[AuditEventRow])
def list_my_audit_events(
    db: DBDep,
    admin: AdminDep,
    before_id: int | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
) -> list[AuditEvent]:
    """Any authenticated admin can view their own audit history.

    No decryption: before/after states are intentionally omitted to
    prevent a self-deanonymisation vector (an admin cannot decrypt their
    own before/after state — that privilege is sudo-admin only per SPEC).
    """
    _require_audit_enabled()
    f = AuditEventFilter(before_id=before_id, limit=limit)

    # Resolve admin's numeric ID.
    from app.db import GetDB, get_admin as db_get_admin

    actor_id: int | None = None
    with GetDB() as _db:
        row = db_get_admin(_db, admin.username)
        if row:
            actor_id = row.id

    if actor_id is None:
        return []

    return _build_query(db, f, actor_id_override=actor_id).limit(limit).all()


__all__ = ["router"]
