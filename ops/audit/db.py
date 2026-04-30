"""SQLAlchemy model for the panel-wide audit log.

Single table ``aegis_audit_events`` (append-only). One row per admin
mutate action (POST / PATCH / PUT / DELETE on sudo-or-admin paths).

Design invariants (see ``docs/ai-cto/SPEC-audit-log.md`` / D-018):

- **Append-only.** No UPDATE path from application code. The only
  legitimate DELETE path is the retention sweep scheduler task
  (hard delete by ``ts < now() - AUDIT_RETENTION_DAYS days``).
- **Encrypted state diff.** ``before_state`` / ``after_state``
  serialise to JSON, get redacted via the SEALED base list
  (``frozenset({"jwt", "password", "passwd", "merchant_key",
  "trc20_private_key", "cf_token", "secret_key", "api_key",
  "private_key"})`` — see D-018 TBD-2) plus ``.env``
  ``AUDIT_EXTRA_REDACT_FIELDS`` union, then Fernet-encrypt with the
  same key path as ``BILLING_SECRET_KEY``. Encryption / redaction
  helpers land in AL.2 (middleware PR), not here.
- **Naive UTC timestamps**, matching the ``ops/billing/db.py``
  precedent — wall-clock UTC without tzinfo, so every Alembic
  autogenerate diff stays at zero noise.
- **No FK to admins.id.** ``actor_id`` is a soft reference; we keep
  ``actor_username`` as a snapshot so admin renames / deletes don't
  destroy historical attribution.
- **No FK from billing.payment_events** (D-018 TBD-3): billing
  remains autonomous; cross-table joins use ``(invoice_id, ts)``
  range queries on the dashboard side.

Cross-references:
- Alembic migration: ``app/db/migrations/versions/20260430_*_audit_events_table.py``
- env.py registration: via ``app/db/extra_models.py`` aggregator
  (LESSONS L-014 — never edit env.py directly).
- SPEC: ``docs/ai-cto/SPEC-audit-log.md`` §How.1 (this file is the
  Python instantiation of the table sketched in the SPEC).
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
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now_utc_naive() -> datetime:
    """Naive UTC ``datetime`` for the ``ts`` column default.

    Matches the ``ops/billing/db.py`` helper (LESSONS L-009) so audit
    timestamps line up byte-for-byte with billing event timestamps —
    important for ``(invoice_id, ts)`` range joins from the dashboard
    (D-018 TBD-3 rejected the FK; range query is the substitute).
    """
    return datetime.now(UTC).replace(tzinfo=None)


# ---------------------------------------------------------------------
# Result enum (validated at application layer; no DB CHECK so the
# state vocabulary can evolve without migrations — same convention as
# ops.billing.states).
# ---------------------------------------------------------------------

RESULT_SUCCESS = "success"
RESULT_FAILURE = "failure"
RESULT_DENIED = "denied"  # 403 from RBAC / sudo gate

ACTOR_TYPE_SUDO = "sudo_admin"
ACTOR_TYPE_ADMIN = "admin"
ACTOR_TYPE_ANONYMOUS = "anonymous"  # pre-auth failures (login attempts etc.)


# ---------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------


class AuditEvent(Base):
    """Append-only audit row. One per admin mutate action.

    Intentionally **no UPDATE and no DELETE paths** from application
    code. The TTL sweep is the only legitimate delete path (hard
    delete via dedicated scheduler task — lands in AL.4).
    """

    __tablename__ = "aegis_audit_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    # — Actor —
    # NULL = anonymous (e.g. failed pre-auth login); otherwise the
    # admin's id, but soft-referenced (no FK) so admin deletion does
    # not cascade-wipe history.
    actor_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actor_type: Mapped[str] = mapped_column(String(16))
    # Snapshot at write time so renames / deletions don't corrupt the
    # historical record.
    actor_username: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # — Action —
    # ``action`` is the route name (``request.scope["route"].name``)
    # or, when unavailable, a synthesised ``method:path_template``.
    action: Mapped[str] = mapped_column(String(128))
    method: Mapped[str] = mapped_column(String(8))
    path: Mapped[str] = mapped_column(String(512))

    # — Target —
    # Optional because not every action has a single target (e.g. bulk
    # endpoints, ``POST /api/billing/cart/checkout``).
    target_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # String form — keeps int / UUID / composite keys uniform without
    # multiple typed columns.
    target_id: Mapped[str | None] = mapped_column(String(96), nullable=True)

    # — State diff (Fernet-encrypted by AL.2 middleware) —
    # Both nullable: a 4xx denied request never produced an after
    # state; a CREATE never had a before state.
    before_state_encrypted: Mapped[bytes | None] = mapped_column(
        LargeBinary, nullable=True
    )
    after_state_encrypted: Mapped[bytes | None] = mapped_column(
        LargeBinary, nullable=True
    )

    # — Result —
    result: Mapped[str] = mapped_column(String(16))
    status_code: Mapped[int] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # — Context —
    # ``ip`` is the gated client IP (post-D-012 trusted-proxy filter).
    ip: Mapped[str] = mapped_column(String(45))  # IPv6 max 45 chars
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # FastAPI middleware injects a request id for log correlation;
    # nullable because pre-middleware code paths (rare) won't have it.
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Naive UTC, matches billing convention.
    ts: Mapped[datetime] = mapped_column(DateTime, default=_now_utc_naive, index=True)

    __table_args__ = (
        # Actor lookup: "show me everything sudo did this week".
        Index("ix_audit_actor_ts", "actor_id", "ts"),
        # Action lookup: "show me every billing.plan.update event".
        Index("ix_audit_action_ts", "action", "ts"),
        # Target lookup: "show me everything that touched user 42".
        Index("ix_audit_target_ts", "target_type", "target_id", "ts"),
        # Note: bare ``ts`` index is created via ``index=True`` on the
        # column above (drives the retention sweep DELETE).
    )
