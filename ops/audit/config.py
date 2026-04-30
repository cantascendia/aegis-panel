"""Audit-log configuration and startup validation.

Holds the operator-facing knobs that decide whether audit is on at
all and how long rows live. Two design decisions worth pinning here
because they don't fit cleanly into ``crypto.py`` or ``middleware.py``:

1. **``AUDIT_RETENTION_DAYS == 0`` is a hard opt-out.** Operator with
   D-003 legal-tension concerns who chooses zero retention gets:
   - middleware skips DB write entirely (no events ever recorded)
   - retention sweep skips the DELETE statement (defensive: there
     are no rows anyway)
   - startup check tolerates a missing ``AUDIT_SECRET_KEY``
     (logically: nothing to encrypt → no key needed)
   This is how D-018 TBD-1 SEALED ("no dashboard wipe button") gets
   its ergonomic exit ramp: operator who wants no audit just sets
   ``AUDIT_RETENTION_DAYS=0`` instead of building a wipe UI.

2. **``AUDIT_RETENTION_DAYS > 0`` requires a key — fail-loud at
   boot.** The combination "audit is on" + "no encryption key" is
   never legitimate. Surfacing it in startup logs / health checks
   beats discovering it during a live admin POST when the audit
   write fails partway through.

Both decisions live behind ``validate_startup()``, called once from
``app/marzneshin.py`` via ``apply_panel_hardening()`` (AL.2c
middleware wiring PR).

Cross-references:
- SPEC: ``docs/ai-cto/SPEC-audit-log.md`` §How.4 (retention sweep)
- Decision: D-018 TBD-1 SEALED (no wipe button → opt-out via env)
- Companion: ``ops/audit/crypto.py`` (consumes the validation)
"""

from __future__ import annotations

import logging

from decouple import config

from ops.audit import crypto

logger = logging.getLogger(__name__)


# Re-export the crypto module's exception so ``from ops.audit.config
# import AuditMisconfigured`` works — single error type for the whole
# audit subsystem (boot-validation + lazy-fail share one class so
# ``except RuntimeError`` / ``except AuditMisconfigured`` both work).
AuditMisconfigured = crypto.AuditMisconfigured


# ---------------------------------------------------------------------
# Retention
# ---------------------------------------------------------------------

# Default 90 days per SPEC §"估算膨胀面" — at >200-user scale, ~9k
# rows / ~18 MB on PostgreSQL 16, no partitioning needed.
DEFAULT_RETENTION_DAYS = 90


def retention_days() -> int:
    """Return ``AUDIT_RETENTION_DAYS`` as a non-negative int.

    Re-read on every call (no module-level cache) so test code can
    monkeypatch the env between test cases without reload helpers.
    The cost is one ``decouple.config`` lookup per audit event,
    which is negligible against the surrounding DB write.

    Negative values clamp to 0 (defensive: misconfigured ``-1`` =
    "audit off", not "audit on with weird retention"). Non-int
    values raise ``ValueError`` from ``int()`` — fail-loud rather
    than silently accept ``"forever"`` and never delete.
    """
    raw = config("AUDIT_RETENTION_DAYS", default=str(DEFAULT_RETENTION_DAYS))
    days = int(raw)
    return max(0, days)


def is_audit_enabled() -> bool:
    """Return True iff retention > 0.

    Used by middleware (skip DB write when False) and retention
    scheduler (skip DELETE when False). Keeping the predicate in
    one place means flipping the meaning of "0 = off" later requires
    one edit, not three.
    """
    return retention_days() > 0


# ---------------------------------------------------------------------
# Startup validation
# ---------------------------------------------------------------------


def validate_startup() -> None:
    """Boot-time check: if audit is enabled, key must be valid.

    Called from ``apply_panel_hardening(app)`` in AL.2c middleware
    wiring PR. Raises :class:`AuditMisconfigured` (which the boot
    sequence converts to a startup abort) if:

    - ``AUDIT_RETENTION_DAYS > 0`` AND
    - ``AUDIT_SECRET_KEY`` is missing OR malformed

    On the happy path, also instantiates the Fernet cipher once so
    the lru_cache is warm before the first request — pre-paying the
    one-time construction cost out of the request hot path.

    On the opt-out path (``AUDIT_RETENTION_DAYS=0``):
    - logs an INFO line so operators can see audit is intentionally
      disabled (vs accidentally — a concrete signal in the boot log
      beats silence for D-003-conscious deployments)
    - skips the key check entirely (no encryption needed)
    - returns without raising

    Idempotent: safe to call multiple times. The Fernet cache make
    repeat calls cheap.
    """
    if not is_audit_enabled():
        logger.info(
            "Audit log disabled (AUDIT_RETENTION_DAYS=0). No events "
            "will be recorded; AUDIT_SECRET_KEY check skipped. "
            "(Set AUDIT_RETENTION_DAYS>0 to enable.)"
        )
        return

    days = retention_days()
    if not crypto.is_configured():
        raise AuditMisconfigured(
            f"Audit log is enabled (AUDIT_RETENTION_DAYS={days}) but "
            f"AUDIT_SECRET_KEY is not set. Generate a Fernet key with "
            f"`python -c 'from cryptography.fernet import Fernet; "
            f"print(Fernet.generate_key().decode())'` and place it in "
            f".env, OR set AUDIT_RETENTION_DAYS=0 to disable audit "
            f"entirely. Refusing to boot to avoid silent event-drop."
        )
    # Warm the Fernet cache — surfaces malformed-key errors here at
    # boot rather than in the first audit write. The encryption call
    # itself does nothing useful with the result; it just primes the
    # lru_cache and validates the key format.
    crypto._fernet()
    logger.info(
        "Audit log enabled (retention=%s days, key configured). "
        "Middleware wiring is AL.2c PR — config validates clean.",
        days,
    )
