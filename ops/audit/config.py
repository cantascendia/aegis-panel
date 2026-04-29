"""Audit-layer environment + crypto primitives.

Two responsibilities share this module because they share a trust boundary
(the operator's ``.env``):

1. **Retention gate** (``AUDIT_RETENTION_DAYS``) — ``0`` disables all audit
   instrumentation: middleware noop, scheduler noop, endpoints 503. This is
   the D-003 operator kill-switch so a panel in a legally hostile environment
   can clear all evidence with one env-var flip and a restart.

2. **State encryption** (``AUDIT_SECRET_KEY``) — Fernet key used to encrypt
   ``AuditEvent.before_state_encrypted`` / ``after_state_encrypted`` at rest.
   Same primitive as ``BILLING_SECRET_KEY`` (AES-128-CBC + HMAC-SHA256). Key
   lives only in ``.env`` / HSM; if it's not there AND the audit log is enabled
   (AUDIT_RETENTION_DAYS > 0), panel startup fails loud — an unconfigured key
   with encryption requested is worse than a missing key we catch early.

Design notes
------------
- ``AUDIT_SECRET_KEY`` can be the same Fernet key as ``BILLING_SECRET_KEY``
  (same key space, different tables). OPS runbook recommends a separate key
  so an audit-only key rotation doesn't require re-encrypting billing rows.
- Key rotation: ``cryptography.fernet.MultiFernet`` is the drop-in upgrade
  path when needed. Single key for now (same as billing).
- Tests override module state via ``_reload_for_tests()``, same pattern as
  ``ops.billing.config``.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from decouple import config

logger = logging.getLogger(__name__)


class AuditMisconfigured(RuntimeError):
    """Raised when the operator's ``.env`` is inconsistent with the audit
    config (e.g. audit is enabled but ``AUDIT_SECRET_KEY`` is missing)."""


# 0 = fully disabled. Any positive value = max age of rows in days.
AUDIT_RETENTION_DAYS: int = int(config("AUDIT_RETENTION_DAYS", default=90))

_AUDIT_SECRET_KEY: str = config("AUDIT_SECRET_KEY", default="")


def audit_enabled() -> bool:
    """True when AUDIT_RETENTION_DAYS > 0 (the master on/off switch)."""
    return AUDIT_RETENTION_DAYS > 0


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    """Lazily instantiate Fernet; cached per process."""
    if not _AUDIT_SECRET_KEY:
        raise AuditMisconfigured(
            "AUDIT_SECRET_KEY is not configured; cannot encrypt audit event "
            "states. Generate one with:\n"
            "  python -c 'from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())'\n"
            "and place it in .env as AUDIT_SECRET_KEY=...\n"
            "To run without encryption set AUDIT_RETENTION_DAYS=0."
        )
    try:
        return Fernet(_AUDIT_SECRET_KEY.encode())
    except (ValueError, TypeError) as exc:
        raise AuditMisconfigured(
            f"AUDIT_SECRET_KEY is not a valid Fernet key: {exc}. "
            "It must be urlsafe base64 of a 32-byte value."
        ) from exc


def encrypt_state(data: dict[str, Any] | None) -> bytes | None:
    """JSON-encode *data*, then Fernet-encrypt it.

    Returns ``None`` for falsy input. Raises ``AuditMisconfigured`` when
    the key is missing. Call site should wrap in try/except and log; audit
    write failure must NOT block the handler (SPEC §AL.1.7).
    """
    if not data:
        return None
    try:
        raw = json.dumps(data, default=str, ensure_ascii=False).encode("utf-8")
        return _fernet().encrypt(raw)
    except AuditMisconfigured:
        raise
    except Exception as exc:  # pragma: no cover
        raise AuditMisconfigured(f"encrypt_state failed: {exc}") from exc


def decrypt_state(ciphertext: bytes | None) -> dict[str, Any] | None:
    """Decrypt and JSON-parse *ciphertext*. Returns ``None`` for empty input.

    Raises ``AuditMisconfigured`` on key mismatch / corrupted token.
    """
    if not ciphertext:
        return None
    try:
        raw = _fernet().decrypt(ciphertext)
        return json.loads(raw.decode("utf-8"))
    except InvalidToken as exc:
        raise AuditMisconfigured(
            "Failed to decrypt audit state — wrong AUDIT_SECRET_KEY or "
            "corrupted ciphertext."
        ) from exc


def check_audit_key_at_startup() -> None:
    """Fail loud at panel startup when audit is enabled but key is missing.

    Called from ``apply_panel_hardening()`` so operators get a clear error
    on boot rather than a cryptic failure mid-request.

    No-op when ``AUDIT_RETENTION_DAYS == 0``.
    """
    if not audit_enabled():
        return
    if not _AUDIT_SECRET_KEY:
        raise AuditMisconfigured(
            "AUDIT_RETENTION_DAYS is set but AUDIT_SECRET_KEY is missing. "
            "Either set AUDIT_SECRET_KEY (see .env.example) or set "
            "AUDIT_RETENTION_DAYS=0 to disable the audit log."
        )
    # Smoke-test key validity.
    _fernet()


def _reload_for_tests(
    retention_days: int = 90,
    secret_key: str = "",
) -> None:
    """Test-only hook to rewire module state without re-importing."""
    global AUDIT_RETENTION_DAYS, _AUDIT_SECRET_KEY
    AUDIT_RETENTION_DAYS = retention_days
    _AUDIT_SECRET_KEY = secret_key
    _fernet.cache_clear()


__all__ = [
    "AUDIT_RETENTION_DAYS",
    "AuditMisconfigured",
    "audit_enabled",
    "check_audit_key_at_startup",
    "decrypt_state",
    "encrypt_state",
]
