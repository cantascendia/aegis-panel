"""Billing-layer environment + crypto primitives.

Two small responsibilities live here together because they share a
trust boundary (the operator's ``.env``):

1. **Public URL** (``BILLING_PUBLIC_BASE_URL``) — external origin that
   EPay 码商 will POST webhooks back to. Must be a fully-qualified
   origin the 码商 can reach from the public internet; ``127.0.0.1``
   will be silently accepted in dev but obviously makes webhooks
   unreachable.

2. **Merchant-key encryption** (``BILLING_SECRET_KEY``) — symmetric
   Fernet key used to encrypt each ``PaymentChannel.merchant_key``
   at rest. Fernet gives us AES-128-CBC + HMAC-SHA256 in one well-
   vetted primitive; this is the same pattern the rest of the Python
   crypto ecosystem defaults to.

Design decisions
----------------

- **Fernet key format**: urlsafe base64-encoded 32-byte value, the
  format :class:`cryptography.fernet.Fernet` consumes directly. Ops
  generates one with ``python -c 'from cryptography.fernet import
  Fernet; print(Fernet.generate_key().decode())'`` and pastes into
  ``.env``.
- **Fail-loud on missing key when encrypted data is present**: a
  channel with a non-empty ``merchant_key_encrypted`` column but no
  ``BILLING_SECRET_KEY`` in env would silently fall back to the
  legacy plaintext column — tempting but dangerous. We raise
  :class:`BillingMisconfigured` instead so it shows up in startup
  logs / health checks, not during a live webhook.
- **No key rotation helper in A.2.2**: one key per deploy for now.
  When multiple operators ever need rotation,
  ``cryptography.fernet.MultiFernet`` is the drop-in replacement;
  ``OPS-epay-vendor-guide.md`` documents the upgrade path.
"""

from __future__ import annotations

from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from decouple import config


class BillingMisconfigured(RuntimeError):
    """Raised at encrypt/decrypt time when the operator's
    ``.env`` is inconsistent with DB state (e.g. encrypted data
    exists but the key is missing or wrong)."""


BILLING_PUBLIC_BASE_URL: str = config("BILLING_PUBLIC_BASE_URL", default="")
# Empty means "EPay disabled" — ``checkout`` returns 503 with a
# clear message rather than generating an unreachable notify_url.

_BILLING_SECRET_KEY: str = config("BILLING_SECRET_KEY", default="")


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    """Lazily instantiate the Fernet cipher. ``lru_cache`` keeps
    this per-process so every encrypt/decrypt reuses one instance.

    Split from module load because tests rewrite ``_BILLING_SECRET_KEY``
    in-process via monkeypatch; exposing ``reset_cache`` on the
    returned function is the standard pattern."""

    if not _BILLING_SECRET_KEY:
        raise BillingMisconfigured(
            "BILLING_SECRET_KEY is not configured; cannot encrypt or "
            "decrypt payment channel merchant keys. Generate one with "
            "`python -c 'from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())'` and place it in "
            ".env as BILLING_SECRET_KEY=..."
        )
    try:
        return Fernet(_BILLING_SECRET_KEY.encode())
    except (ValueError, TypeError) as exc:
        raise BillingMisconfigured(
            f"BILLING_SECRET_KEY is not a valid Fernet key: {exc}. "
            "It must be urlsafe base64 of a 32-byte value."
        ) from exc


def encrypt_merchant_key(plaintext: str) -> bytes:
    """Encrypt a merchant key for at-rest storage.

    Empty input → ``b""`` (no ciphertext, no token overhead). This
    lets the DB column stay NULL/empty for rows that have no
    credential set yet (e.g. a channel being provisioned).
    """
    if not plaintext:
        return b""
    return _fernet().encrypt(plaintext.encode("utf-8"))


def decrypt_merchant_key(ciphertext: bytes | None) -> str:
    """Decrypt a merchant key. ``None`` / empty → ``""``.

    Raises :class:`BillingMisconfigured` when the token is malformed,
    the signature check fails, or the key has been rotated without a
    migration. Callers should not swallow this — it almost always
    indicates a deployment bug worth paging on.
    """
    if not ciphertext:
        return ""
    try:
        return _fernet().decrypt(ciphertext).decode("utf-8")
    except InvalidToken as exc:
        raise BillingMisconfigured(
            "Failed to decrypt merchant_key_encrypted — wrong key "
            "or corrupted ciphertext. Check that BILLING_SECRET_KEY "
            "matches the one the row was encrypted with."
        ) from exc


def _reload_for_tests(secret_key: str, public_base_url: str = "") -> None:
    """Test-only hook to rewire module state without re-importing.

    Not part of the public API; production code never calls this.
    Used by ``tests/test_billing_crypto.py`` and checkout/webhook
    fixtures to isolate Fernet keys between cases.
    """
    global _BILLING_SECRET_KEY, BILLING_PUBLIC_BASE_URL
    _BILLING_SECRET_KEY = secret_key
    BILLING_PUBLIC_BASE_URL = public_base_url
    _fernet.cache_clear()


__all__ = [
    "BILLING_PUBLIC_BASE_URL",
    "BillingMisconfigured",
    "decrypt_merchant_key",
    "encrypt_merchant_key",
]
