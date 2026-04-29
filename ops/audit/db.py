"""SQLAlchemy model for the audit log (S-AL).

Single table: ``aegis_audit_events``

Design invariants (see SPEC-audit-log.md):

- **Append-only**: no UPDATE or DELETE paths from application code.
  If a row is wrong, the response is an explanatory follow-up row, not a
  patch — same hygiene as ``aegis_billing_payment_events``.
- **Encrypted at rest**: ``before_state_encrypted`` / ``after_state_encrypted``
  are Fernet ciphertexts (``ops.audit.config.encrypt_state``). The audit log
  itself is only as secret as the key in ``.env``.
- **Retention-aware**: rows older than ``AUDIT_RETENTION_DAYS`` are hard-deleted
  by the daily sweep (``ops.audit.scheduler``). ``AUDIT_RETENTION_DAYS=0``
  means the table is never written to.
- **Actor snapshot**: ``actor_username`` is snapshot-at-write so renaming an
  admin later doesn't erase historical attribution.

Cross-references:
  Alembic migration: ``app/db/migrations/versions/20260429_*_audit_events.py``
  env.py registration: ``import ops.audit.db  # noqa: F401`` in
    ``app/db/extra_models.py`` (LESSONS L-014).
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now_utc_naive() -> datetime:
    """Naive UTC datetime; mirrors billing convention (LESSONS L-009)."""
    return datetime.now(UTC).replace(tzinfo=None)


# ── Result constants (stored verbatim in DB; human-readable on purpose) ──

RESULT_SUCCESS = "success"
RESULT_FAILURE = "failure"
RESULT_DENIED = "denied"

# ── Actor type constants ───────────────────────────────────────────────────

ACTOR_TYPE_SUDO = "sudo_admin"
ACTOR_TYPE_ADMIN = "admin"
ACTOR_TYPE_ANONYMOUS = "anonymous"


class AuditEvent(Base):
    """One immutable row per admin mutating request.

    The ``before_state_encrypted`` column holds the (redacted, encrypted)
    incoming request body — what the admin sent. The ``after_state_encrypted``
    column holds the (redacted, encrypted) response body — what the server
    returned. Both use ``ops.audit.config.{encrypt,decrypt}_state``.

    ``result`` is one of ``"success"`` / ``"failure"`` / ``"denied"``::

        success  HTTP 2xx
        failure  HTTP 4xx that isn't 401/403, plus 5xx
        denied   HTTP 401 or 403

    ``action`` is the route path template (not the actual URL) — e.g.
    ``POST:/api/users/{username}`` so queries aggregate across users.
    """

    __tablename__ = "aegis_audit_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    # ── Actor ─────────────────────────────────────────────────────────────
    actor_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actor_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default=ACTOR_TYPE_ANONYMOUS
    )
    # Snapshot: stores the username at the time of the request so renames
    # don't rewrite history.
    actor_username: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )

    # ── Action ────────────────────────────────────────────────────────────
    action: Mapped[str] = mapped_column(String(256), nullable=False)
    method: Mapped[str] = mapped_column(String(16), nullable=False)
    path: Mapped[str] = mapped_column(String(512), nullable=False)

    # ── Target (optional; set when the path identifies a specific object) ─
    target_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # ── State snapshots (Fernet-encrypted JSON) ───────────────────────────
    before_state_encrypted: Mapped[bytes | None] = mapped_column(
        LargeBinary, nullable=True
    )
    after_state_encrypted: Mapped[bytes | None] = mapped_column(
        LargeBinary, nullable=True
    )

    # ── Outcome ───────────────────────────────────────────────────────────
    result: Mapped[str] = mapped_column(
        String(16), nullable=False, default=RESULT_SUCCESS
    )
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Network context ───────────────────────────────────────────────────
    ip: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # ── Timestamp ─────────────────────────────────────────────────────────
    ts: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_now_utc_naive
    )

    __table_args__ = (
        # Hot queries: "what did actor X do recently?"
        Index("ix_audit_actor_ts", "actor_id", "ts"),
        # Hot queries: "when was plan.update called?"
        Index("ix_audit_action_ts", "action", "ts"),
        # Hot queries: "what happened to user 42?"
        Index("ix_audit_target_ts", "target_type", "target_id", "ts"),
        # Retention sweep: DELETE WHERE ts < cutoff
        Index("ix_audit_ts", "ts"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<AuditEvent id={self.id} actor={self.actor_username!r} "
            f"action={self.action!r} result={self.result} ts={self.ts}>"
        )
