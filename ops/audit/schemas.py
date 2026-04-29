"""Pydantic schemas for the audit log REST API (S-AL AL.2).

Two levels of detail:
- ``AuditEventRow`` — list/export view; no decryption (before/after omitted).
- ``AuditEventDetail`` — single-event view; decrypted before/after included
  (sudo-admin only).

Query parameter model ``AuditEventFilter`` drives the ``GET /api/audit/events``
filtering interface.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditEventRow(BaseModel):
    """Audit event as returned in list/export endpoints (no decryption)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_id: int | None = None
    actor_type: str
    actor_username: str | None = None
    action: str
    method: str
    path: str
    target_type: str | None = None
    target_id: str | None = None
    result: str
    status_code: int
    error_message: str | None = None
    ip: str
    user_agent: str | None = None
    request_id: str | None = None
    ts: datetime


class AuditEventDetail(AuditEventRow):
    """Single audit event with decrypted state (sudo-admin only)."""

    before_state: dict[str, Any] | None = None
    after_state: dict[str, Any] | None = None


class AuditEventFilter(BaseModel):
    """Query parameters for ``GET /api/audit/events``."""

    actor_id: int | None = None
    actor_username: str | None = None
    actor_type: str | None = None
    action: str | None = None
    result: str | None = None
    target_type: str | None = None
    target_id: str | None = None
    # Inclusive date range (naive UTC).
    ts_from: datetime | None = None
    ts_to: datetime | None = None
    # Cursor-based pagination: return rows with id < cursor, newest-first.
    before_id: int | None = None
    limit: int = 50


class AuditStatsResponse(BaseModel):
    """Response for ``GET /api/audit/stats``."""

    total_7d: int
    by_result: dict[str, int]
    by_actor_type: dict[str, int]
    top_actions: list[dict[str, Any]]
