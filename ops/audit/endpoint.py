"""FastAPI router for the audit-log read API (S-AL Phase 3).

Mounted by ``hardening.panel.middleware.apply_panel_hardening`` under
``/api/audit/*``. **Every route is sudo-only** — non-sudo admins
cannot list, detail, or export audit rows. Rationale: audit data is
the operator-side oversight tool; making it visible to the actors
it audits is a self-defeating loop.

Endpoints:

  GET   /api/audit/events                list + filter + cursor pagination
  GET   /api/audit/events/{id}           single row with decrypted state diff
  GET   /api/audit/events/export.csv     CSV export (capped at 10k rows)

Filters supported on the list endpoint:

  ?actor_username=alice          actor identity
  ?action=billing.plan.update    SEALED action key (substring match)
  ?target_type=user              target type
  ?target_id=42                  target id (string-typed in schema)
  ?result=success                "success" | "failure" | "denied"
  ?since=2026-04-30T00:00:00     timestamps (ISO 8601, UTC naive)
  ?until=2026-04-30T23:59:59
  ?limit=50                      page size, max 200
  ?cursor=12345                  next-page cursor (id < cursor)

The CSV export is offered separately from list-pagination because
operators usually want "all rows in this filter window" without
pagination friction. Cap is 10k to keep the response within sane
memory bounds; operators wanting more should query the DB directly.
"""

from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dependencies import DBDep, SudoAdminDep
from ops.audit.crypto import AuditMisconfigured, decrypt_audit_payload
from ops.audit.db import AuditEvent
from ops.audit.schemas import (
    AuditEventDetail,
    AuditEventListResponse,
    AuditEventSummary,
)

router = APIRouter(prefix="/api/audit", tags=["Audit Log"])

_MAX_LIST_LIMIT = 200
_DEFAULT_LIST_LIMIT = 50
_CSV_EXPORT_CAP = 10_000


def _build_filtered_query(
    db: Session,
    *,
    actor_username: str | None,
    action: str | None,
    target_type: str | None,
    target_id: str | None,
    result: str | None,
    since: datetime | None,
    until: datetime | None,
    cursor: int | None,
):
    """Common WHERE-clause builder for list + CSV export.

    Returns an SQLAlchemy 2.0 ``select`` ready for ``.limit().all()``
    or streaming. Cursor pagination uses ``id < cursor`` so order is
    deterministic descending by id (newest first), and concurrent
    deletions don't cause "skipped rows" between pages.
    """
    stmt = select(AuditEvent).order_by(AuditEvent.id.desc())
    if actor_username:
        stmt = stmt.where(AuditEvent.actor_username == actor_username)
    if action:
        stmt = stmt.where(AuditEvent.action.like(f"%{action}%"))
    if target_type:
        stmt = stmt.where(AuditEvent.target_type == target_type)
    if target_id:
        stmt = stmt.where(AuditEvent.target_id == target_id)
    if result:
        stmt = stmt.where(AuditEvent.result == result)
    if since:
        stmt = stmt.where(AuditEvent.ts >= since)
    if until:
        stmt = stmt.where(AuditEvent.ts <= until)
    if cursor is not None:
        stmt = stmt.where(AuditEvent.id < cursor)
    return stmt


@router.get("/events", response_model=AuditEventListResponse)
def list_audit_events(
    db: DBDep,
    admin: SudoAdminDep,  # noqa: ARG001
    actor_username: Annotated[str | None, Query()] = None,
    action: Annotated[str | None, Query()] = None,
    target_type: Annotated[str | None, Query()] = None,
    target_id: Annotated[str | None, Query()] = None,
    result: Annotated[str | None, Query()] = None,
    since: Annotated[datetime | None, Query()] = None,
    until: Annotated[datetime | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=_MAX_LIST_LIMIT)] = _DEFAULT_LIST_LIMIT,
    cursor: Annotated[int | None, Query()] = None,
) -> AuditEventListResponse:
    """List audit events with filters + cursor pagination.

    Returns up to ``limit`` rows ordered newest-first (descending
    id). ``next_cursor`` is the id of the last row returned; pass
    it back as ``cursor`` to fetch the next page. ``next_cursor``
    is None when fewer than ``limit`` rows came back (end of data).
    """
    stmt = _build_filtered_query(
        db,
        actor_username=actor_username,
        action=action,
        target_type=target_type,
        target_id=target_id,
        result=result,
        since=since,
        until=until,
        cursor=cursor,
    )
    rows = db.execute(stmt.limit(limit)).scalars().all()
    items = [AuditEventSummary.model_validate(r) for r in rows]
    next_cursor = rows[-1].id if len(rows) == limit else None
    return AuditEventListResponse(
        items=items,
        next_cursor=next_cursor,
        total_returned=len(items),
    )


@router.get("/events/{event_id}", response_model=AuditEventDetail)
def get_audit_event(
    event_id: int,
    db: DBDep,
    admin: SudoAdminDep,  # noqa: ARG001
) -> AuditEventDetail:
    """Single audit row with decrypted ``before_state`` / ``after_state``.

    Sudo-only: cleartext state diffs (post-redact) only flow to
    operators who hold the encryption key path. Decryption failure
    propagates as 500 with ``AuditMisconfigured`` message — that's
    the right default; an audit reader getting silently-empty diffs
    would mask a key-rotation incident.
    """
    row = db.get(AuditEvent, event_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"audit event {event_id} not found",
        )
    summary = AuditEventSummary.model_validate(row)
    try:
        before = decrypt_audit_payload(row.before_state_encrypted)
        after = decrypt_audit_payload(row.after_state_encrypted)
    except AuditMisconfigured as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"audit decrypt failed: {exc}",
        ) from exc
    return AuditEventDetail(
        **summary.model_dump(),
        before_state=before,
        after_state=after,
    )


@router.get("/events/export.csv")
def export_audit_events_csv(
    db: DBDep,
    admin: SudoAdminDep,  # noqa: ARG001
    actor_username: Annotated[str | None, Query()] = None,
    action: Annotated[str | None, Query()] = None,
    target_type: Annotated[str | None, Query()] = None,
    target_id: Annotated[str | None, Query()] = None,
    result: Annotated[str | None, Query()] = None,
    since: Annotated[datetime | None, Query()] = None,
    until: Annotated[datetime | None, Query()] = None,
) -> StreamingResponse:
    """CSV export — capped at 10k rows.

    Operators wanting more should query the DB directly (psql
    + COPY); the cap exists to keep the HTTP response within
    sane memory bounds. Filtered the same way as the list endpoint.

    State-diff fields intentionally excluded from CSV (they're
    free-form JSON; CSV shape would be unstable). Operators wanting
    diffs use the detail endpoint per row.
    """
    stmt = _build_filtered_query(
        db,
        actor_username=actor_username,
        action=action,
        target_type=target_type,
        target_id=target_id,
        result=result,
        since=since,
        until=until,
        cursor=None,
    )
    rows = db.execute(stmt.limit(_CSV_EXPORT_CAP)).scalars().all()

    def _generate():
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(
            [
                "id", "ts", "actor_username", "actor_type",
                "action", "method", "path",
                "target_type", "target_id",
                "result", "status_code", "error_message",
                "ip", "user_agent", "request_id",
            ]
        )
        yield buf.getvalue()
        buf.seek(0)
        buf.truncate()
        for r in rows:
            writer.writerow(
                [
                    r.id,
                    r.ts.isoformat(),
                    r.actor_username or "",
                    r.actor_type,
                    r.action,
                    r.method,
                    r.path,
                    r.target_type or "",
                    r.target_id or "",
                    r.result,
                    r.status_code,
                    r.error_message or "",
                    r.ip,
                    r.user_agent or "",
                    r.request_id or "",
                ]
            )
            yield buf.getvalue()
            buf.seek(0)
            buf.truncate()

    headers = {
        "Content-Disposition": "attachment; filename=audit-events.csv",
    }
    return StreamingResponse(
        _generate(), media_type="text/csv", headers=headers
    )
