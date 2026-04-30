"""Pydantic schemas for the audit-log REST endpoint (AL.3).

Two response shapes:
- ``AuditEventSummary`` — list rows; no decrypted payloads (cheap to
  page through hundreds of rows).
- ``AuditEventDetail`` — single row; ``before_state`` / ``after_state``
  decrypted on demand. Endpoint enforces sudo-only access for this
  shape so cleartext payloads only flow to operators with the
  encryption key path.

State-diff fields are typed as ``Any | None`` (after JSON decode)
because the audit table stores arbitrary JSON-serialisable shapes;
constraining the schema would defeat the "captures whatever the
handler returned" design.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditEventSummary(BaseModel):
    """List-row shape — no decrypted payloads."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_id: int | None
    actor_type: str
    actor_username: str | None
    action: str
    method: str
    path: str
    target_type: str | None
    target_id: str | None
    result: str
    status_code: int
    error_message: str | None
    ip: str
    user_agent: str | None
    request_id: str | None
    ts: datetime


class AuditEventDetail(AuditEventSummary):
    """Detail shape — extends summary with decrypted state diffs.

    ``before_state`` / ``after_state`` are populated by the endpoint
    after Fernet-decrypting the encrypted columns. Either may be
    ``None`` when no state was captured (CREATE has no before;
    DELETE has no after; AL.2c.2 MVP rows have neither because the
    middleware doesn't yet capture state — AL.2c.4).
    """

    before_state: Any | None = None
    after_state: Any | None = None


class AuditEventListResponse(BaseModel):
    """List endpoint response — items + a cursor for the next page.

    Cursor pagination (not offset) so deletions during paging don't
    skip rows. Cursor = the smallest ``id`` of the current page;
    next request asks for ``id < cursor``.
    """

    items: list[AuditEventSummary]
    next_cursor: int | None = None
    total_returned: int
