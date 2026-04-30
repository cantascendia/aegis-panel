"""Fernet symmetric encryption for audit-log state diffs.

Mirrors the proven ``ops.billing.config`` Fernet pattern (A.2.1, PR #46
— operator already familiar with the env-var + key-generation flow)
so the audit module isn't a new operational surface; only the env-var
name (``AUDIT_SECRET_KEY``) and the JSON-serialisation step differ.

## Why Fernet (not custom AES wrapping)

Fernet = AES-128-CBC + HMAC-SHA256 in one well-vetted primitive
(``cryptography`` library standard). Three concrete properties matter
for audit:

1. **Authenticated.** HMAC catches ciphertext tampering; an operator
   who corrupts a row in raw SQL gets ``InvalidToken``, not a silent
   wrong decrypt. Audit reads must trust their inputs.
2. **Versioned.** Fernet token format prepends a version byte, so
   a future migration to a stronger primitive can land via
   ``MultiFernet`` (rotation) without re-encrypting historical rows.
3. **Time-bounded.** Each token carries a creation timestamp; we
   don't enforce TTL here (retention sweep is a separate concern at
   the row level), but the field exists if a future audit-key
   rotation policy needs it.

## Key management

- ``AUDIT_SECRET_KEY`` env var, urlsafe base64 32-byte Fernet key.
- Operators generate with: ``python -c 'from cryptography.fernet
  import Fernet; print(Fernet.generate_key().decode())'``.
- **May reuse** ``BILLING_SECRET_KEY`` (set both env vars to the same
  value) — operationally simpler. **May use a separate key** —
  cryptographically cleaner; compromising one doesn't compromise the
  other audit/billing rows. Operator decides; SPEC §How.3 documents
  both paths.
- **Missing key fail-loud:** AL.2c (middleware) wires this so panel
  startup checks the env var when ``AUDIT_RETENTION_DAYS > 0``
  (audit not opt-out) and refuses to boot if the key is absent.
  This module raises ``AuditMisconfigured`` lazily on first
  encrypt/decrypt call so unit tests don't need full env config.

## Payload shape

State diffs are JSON-serialisable Python ``dict`` / ``list`` /
scalar — ``redact_payload`` already returns this shape. We
``json.dumps`` first (sort_keys for deterministic ciphertext when
the same input encrypts twice — useful in test fixtures), encode
UTF-8, then Fernet-encrypt. Decryption reverses both steps.

The redact step **must** happen before encryption (the encrypted
ciphertext is plain bytes to the encryption layer; if a secret slips
through, the decryption key holder gets it back unchanged).
``encrypt_audit_payload`` enforces this: it always calls
``redact_payload`` first. Callers cannot bypass redaction without
touching this module — minimising the chance of accidental leak.

## Cross-references

- SPEC: ``docs/ai-cto/SPEC-audit-log.md`` §How.3 (隐私 / 加密)
- Pattern source: ``ops/billing/config.py`` _fernet/encrypt/decrypt
- Companion: ``ops/audit/redact.py`` (always invoked before encrypt)
- Future consumer: ``ops/audit/middleware.py`` (AL.2c)
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from decouple import config

from ops.audit.redact import redact_payload

logger = logging.getLogger(__name__)


class AuditMisconfigured(RuntimeError):
    """Raised when ``AUDIT_SECRET_KEY`` is missing, malformed, or
    cannot decrypt an existing token. Mirrors
    ``ops.billing.config.BillingMisconfigured`` for op familiarity.

    Callers should NOT swallow this — it indicates either a startup
    misconfig (panel should not boot) or a key-rotation accident
    that needs operator attention. The retention sweep handles the
    "old key, decrypt fails" case at row-evict time, not here.
    """


_AUDIT_SECRET_KEY: str = config("AUDIT_SECRET_KEY", default="")


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    """Lazily instantiate the Fernet cipher.

    ``lru_cache`` keeps one instance per-process so every audit row
    reuses it (Fernet construction is cheap but not free). Split from
    module load so tests can monkeypatch ``_AUDIT_SECRET_KEY`` and
    call ``_fernet.cache_clear()``.
    """
    if not _AUDIT_SECRET_KEY:
        raise AuditMisconfigured(
            "AUDIT_SECRET_KEY is not configured; cannot encrypt or "
            "decrypt audit-log state diffs. Generate one with "
            "`python -c 'from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())'` and place it in "
            ".env as AUDIT_SECRET_KEY=... (may reuse BILLING_SECRET_KEY "
            "value, or set a separate key per SPEC §How.3)."
        )
    try:
        return Fernet(_AUDIT_SECRET_KEY.encode())
    except (ValueError, TypeError) as exc:
        raise AuditMisconfigured(
            f"AUDIT_SECRET_KEY is not a valid Fernet key: {exc}. "
            f"Expected urlsafe base64-encoded 32-byte value. "
            f"Regenerate with `python -c 'from cryptography.fernet "
            f"import Fernet; print(Fernet.generate_key().decode())'`."
        ) from exc


def is_configured() -> bool:
    """Return True if a Fernet key is set, False otherwise.

    Used by AL.2c middleware to decide whether to skip audit writes
    when ``AUDIT_RETENTION_DAYS > 0`` but no key — that combination
    must fail-loud at startup, not silently drop events. (Middleware
    calls ``_fernet()`` once at startup to surface the
    ``AuditMisconfigured`` exception in the boot logs.)
    """
    return bool(_AUDIT_SECRET_KEY)


def encrypt_audit_payload(payload: Any | None) -> bytes:
    """Redact then Fernet-encrypt a state-diff payload.

    Empty / None input → ``b""`` (zero-byte ciphertext means
    "no state captured" — saves token overhead on rows that have
    no before-state, e.g. CREATE actions, or no after-state, e.g.
    DELETE actions).

    The redact step is non-bypassable: any caller of this function
    gets the ``BASE | EXTRAS`` redaction guarantee for free, even if
    they forget to call ``redact_payload`` themselves. This is the
    load-bearing safety property — if a future caller path skips
    encrypt and writes raw bytes, they bypass redaction too, which
    is why the AL.2c middleware contract pins encrypt as the only
    legitimate write path.

    JSON serialisation uses ``sort_keys=True`` so the same input
    produces the same plaintext bytes — useful for fixtures and for
    detecting "my redact set changed" diff via ciphertext-equality.
    Fernet itself randomises the IV so two calls with identical
    plaintext still produce different ciphertext (forward secrecy
    against ciphertext correlation).
    """
    if payload is None:
        return b""
    redacted = redact_payload(payload)
    if redacted == {} or redacted == []:
        # Empty containers are "captured but empty" — preserve the
        # signal so audit readers can distinguish "no state" (None
        # → b"") from "empty state" (e.g. delete-all bulk action).
        pass
    plaintext = json.dumps(redacted, sort_keys=True, ensure_ascii=False)
    return _fernet().encrypt(plaintext.encode("utf-8"))


def decrypt_audit_payload(ciphertext: bytes | None) -> Any | None:
    """Decrypt and JSON-decode an audit-log state diff.

    Empty / None input → ``None`` (the encrypt-side convention for
    "no state captured").

    Raises ``AuditMisconfigured`` on:
    - Missing / malformed ``AUDIT_SECRET_KEY`` (re-raised from
      ``_fernet()``).
    - Tampered or corrupted ciphertext (``InvalidToken`` from Fernet).
    - Wrong key (key rotated since the row was written and the old
      key isn't kept in a ``MultiFernet`` rotation list — also
      ``InvalidToken``; the message hint mentions rotation).

    The retention sweep should never call this — it deletes by ``ts``
    range, not by content — so a key-rotation incident does not
    block retention.
    """
    if not ciphertext:
        return None
    try:
        plaintext = _fernet().decrypt(ciphertext)
    except InvalidToken as exc:
        raise AuditMisconfigured(
            "Failed to decrypt audit payload — wrong key or "
            "corrupted ciphertext. Verify AUDIT_SECRET_KEY matches "
            "the value used when this row was written. If keys were "
            "rotated, wrap them in cryptography.fernet.MultiFernet "
            "and update this module."
        ) from exc
    return json.loads(plaintext.decode("utf-8"))


def _reload_for_tests() -> None:
    """Test hook — re-read ``AUDIT_SECRET_KEY`` env and clear the
    Fernet cache. Mirrors ``ops.billing.config._reload_for_tests``.

    Production code MUST NOT call this. It exists only so unit tests
    can flip the env via ``monkeypatch.setenv`` and have the next
    ``encrypt_audit_payload`` pick up the new value.
    """
    global _AUDIT_SECRET_KEY
    _AUDIT_SECRET_KEY = config("AUDIT_SECRET_KEY", default="")
    _fernet.cache_clear()
