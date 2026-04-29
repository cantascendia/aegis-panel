"""Sensitive-field redaction for audit event payloads.

``deep_redact`` walks a JSON-serialisable structure and replaces values whose
key matches ``REDACT_FIELDS`` with the sentinel ``"[REDACTED]"``. This runs
BEFORE Fernet encryption so the ciphertext never contains secrets even in the
event of a key compromise.

Single source of truth: add fields here, nowhere else. The set is intentionally
conservative — when in doubt, redact.
"""

from __future__ import annotations

from typing import Any

# Exact lower-case key names to redact. Comparison is case-insensitive
# (see deep_redact). This list is the SSOT; do not duplicate in tests —
# import REDACT_FIELDS and test against it directly.
REDACT_FIELDS: frozenset[str] = frozenset(
    {
        # ── Credentials ──────────────────────────────────────────────
        "password",
        "password_hash",
        "hashed_password",
        "jwt_secret",
        "secret_key",
        "api_key",
        "api_token",
        "access_token",
        # ── Billing / payment keys ───────────────────────────────────
        "merchant_key",
        "merchant_key_encrypted",
        "billing_secret_key",
        # ── On-chain private material ────────────────────────────────
        "trc20_private_key",
        "private_key",
        "mnemonic",
        "seed_phrase",
        # ── User PII (GDPR pre-reserve) ──────────────────────────────
        "email",
        "phone",
        "real_name",
        "id_card",
        # ── Subscription tokens ──────────────────────────────────────
        "subscription_token",
        "sub_token",
        "subscription_url",
        # ── Panel secrets ────────────────────────────────────────────
        "audit_secret_key",
        "webhook_secret",
    }
)

_SENTINEL = "[REDACTED]"


def deep_redact(obj: Any, *, _depth: int = 0) -> Any:
    """Recursively redact ``REDACT_FIELDS`` keys from *obj*.

    - ``dict``: redact matching keys; recurse into values.
    - ``list`` / ``tuple``: recurse into each element.
    - Scalar: returned as-is.
    - Depth-limited to 20 levels to prevent stack overflow on pathological
      payloads (shouldn't happen in practice but defensively bounded).

    Does NOT mutate the input — returns a new structure.
    """
    if _depth > 20:
        return obj

    if isinstance(obj, dict):
        result: dict[str, Any] = {}
        for k, v in obj.items():
            if isinstance(k, str) and k.lower() in REDACT_FIELDS:
                result[k] = _SENTINEL
            else:
                result[k] = deep_redact(v, _depth=_depth + 1)
        return result

    if isinstance(obj, (list, tuple)):
        redacted = [deep_redact(item, _depth=_depth + 1) for item in obj]
        return type(obj)(redacted)

    return obj


__all__ = ["REDACT_FIELDS", "deep_redact"]
