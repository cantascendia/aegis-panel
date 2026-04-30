"""Sensitive-field redaction for audit-log payloads.

Recursively walks a JSON-serialisable payload (dict / list / scalar)
and replaces any value whose key matches the redact set with the
string ``"<REDACTED>"``. Used by the AL.2 middleware *before* Fernet
encryption so encrypted ciphertext never carries secrets that an
operator with the audit decryption key could later read.

## Design (D-018 TBD-2 SEALED 2026-04-30)

**Mixed scheme** — base list hardcoded ``frozenset()`` + ``.env``
``AUDIT_EXTRA_REDACT_FIELDS`` *union* (never override). Rationale:

- **Base list is non-negotiable.** A misconfigured ``.env`` cannot
  cause secrets like ``password`` / ``trc20_private_key`` /
  ``merchant_key`` to leak into audit rows. The base set is held in a
  ``frozenset`` so callers can't mutate it at runtime either.
- **Extras give market flexibility.** EU operators add ``email,phone``
  for GDPR; CN operators don't need to. Done via ``.env`` so changing
  the redact policy doesn't require a code PR + redeploy.
- **Final set = ``BASE | EXTRAS``** — always a superset of base.

## Why ``"<REDACTED>"`` (not hash)

Hashes look like deterministic identifiers — an audit reader could
compare two redacted hashes and infer "these two events touched the
same password". That re-leaks the very thing redaction protects
against. The string ``"<REDACTED>"`` removes all signal.

## Matching rules

- **Case-insensitive on key.** ``"Password"`` and ``"PASSWORD"`` and
  ``"password"`` all redact. (``frozenset`` is built lowercased; key
  lookups lowercase the candidate.)
- **No partial / prefix matching.** ``"password"`` redacts but
  ``"password_strength_score"`` does NOT — too noisy if every key
  containing ``"key"`` got nuked. Operators wanting prefix coverage
  add the explicit field names to ``AUDIT_EXTRA_REDACT_FIELDS``.
- **Nested dicts and lists are walked.** Any dict at any depth gets
  the same key check; lists are walked element-wise.
- **Non-dict / non-list values pass through unchanged.** Strings,
  numbers, bools, None — all preserved.

## Cross-references

- SPEC: ``docs/ai-cto/SPEC-audit-log.md`` §How.3 (隐私 / 加密)
- Decision: D-018 TBD-2 SEALED
- Companion (still pending AL.2): ``ops/audit/crypto.py`` (Fernet
  wrapper) + ``ops/audit/middleware.py`` (the consumer).
"""

from __future__ import annotations

import os
from typing import Any

# ---------------------------------------------------------------------
# Sealed base list (D-018 TBD-2). Held in a ``frozenset`` so:
#   1. Lookups are O(1).
#   2. Any code path trying ``BASE_REDACT_FIELDS.add(...)`` raises
#      AttributeError at import time of the offending module — easy
#      to spot in CI.
# All keys are lowercase; the redact function lowercases candidates
# before lookup.
# ---------------------------------------------------------------------

BASE_REDACT_FIELDS: frozenset[str] = frozenset(
    {
        # Auth / API credentials.
        # ``hashed_password`` is the actual column name on
        # ``app.db.models.Admin`` (PR #125 audit codex review 2026-04-30
        # P2 — verified by ``grep "hashed_password" app/db/models.py``).
        # ``password_hash`` retained as belt-and-braces alias.
        "password",
        "passwd",
        "hashed_password",
        "password_hash",
        "jwt",
        "jwt_secret",
        "secret_key",
        "api_key",
        "api_token",
        # ``key`` is the actual column on ``app.db.models.User`` (a
        # 16-hex bearer token — per ``UserResponse``, anyone with the
        # value gets that user's traffic). Adding it here costs us
        # some over-match noise on generic ``{"key": ..., "value": ...}``
        # config dicts, but secrets > ergonomics. Operators wanting
        # narrower behavior can rename their config keys (e.g.
        # ``"setting"`` instead of ``"key"``) — the redactor is a
        # secret guarantee, not a convenience layer.
        "key",
        # Merchant / payment-channel credentials
        "merchant_key",
        "merchant_key_encrypted",
        "cf_token",
        # On-chain / wallet secrets
        "trc20_private_key",
        "private_key",
        "mnemonic",
        # Subscription URLs and tokens that act as bearer credentials.
        # ``subscription_url`` is the actual UserResponse field
        # (codex review P2 — anyone with the full URL gets the user's
        # traffic).
        "subscription_url",
        "subscription_token",
        "sub_token",
    }
)

REDACTED_PLACEHOLDER = "<REDACTED>"

_ENV_EXTRAS_VAR = "AUDIT_EXTRA_REDACT_FIELDS"


def _env_extras() -> frozenset[str]:
    """Read ``.env`` extras as a lowercase set.

    Format: comma-separated field names, e.g.
    ``AUDIT_EXTRA_REDACT_FIELDS=email,phone,real_name``.

    Empty / unset env var → empty set. Whitespace per item is stripped;
    empty items (``"a,,b"``) are dropped silently.

    Re-read on every call so test code can monkeypatch the env without
    needing to reload the module. The cost is one tiny dict lookup +
    string split; the function fires once per audit event.
    """
    raw = os.environ.get(_ENV_EXTRAS_VAR, "")
    if not raw:
        return frozenset()
    return frozenset(
        part.strip().lower() for part in raw.split(",") if part.strip()
    )


def effective_redact_set() -> frozenset[str]:
    """Return ``BASE | EXTRAS`` — always a superset of the base list.

    Callers should treat this as the authoritative set for the lifetime
    of the request. Note: the union is *fresh* each call so env-var
    edits between requests take effect immediately (operator-friendly;
    no panel restart required to extend the redact list).
    """
    return BASE_REDACT_FIELDS | _env_extras()


def redact_payload(payload: Any) -> Any:
    """Return a redacted deep copy of ``payload``.

    The input is **not** mutated — callers can keep using the raw
    payload afterwards (e.g. to send the real ``after_state`` back to
    the user while persisting only the redacted copy in the audit row).

    See the module docstring for matching rules.
    """
    redact = effective_redact_set()
    return _walk(payload, redact)


def _walk(value: Any, redact: frozenset[str]) -> Any:
    """Recursively walk ``value`` and redact dict keys in ``redact``."""
    if isinstance(value, dict):
        return {
            key: (
                REDACTED_PLACEHOLDER
                if isinstance(key, str) and key.lower() in redact
                else _walk(inner, redact)
            )
            for key, inner in value.items()
        }
    if isinstance(value, list):
        return [_walk(item, redact) for item in value]
    if isinstance(value, tuple):
        # Tuples shouldn't appear in JSON payloads, but if a caller
        # passes one we preserve type (tests rely on this for
        # round-tripping fixture data).
        return tuple(_walk(item, redact) for item in value)
    # Scalars (str / int / float / bool / None / bytes / etc.) pass
    # through. We deliberately do NOT redact strings that *look like*
    # secrets ("eyJhbGciOi..." style JWTs etc.) — that's a separate
    # heuristic detector, not the field-name redactor.
    return value
