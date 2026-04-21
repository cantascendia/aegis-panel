"""
JWT signing-key resolution.

Why this file changed (Round 1 P0-security):
- Pre-P0 Marzneshin stored the HMAC secret in the `jwt` table. Any
  SQL-injection vulnerability or DB dump therefore exposed the key used
  to sign every admin token in the system.
- P0 fix: prefer a `JWT_SECRET_KEY` environment variable (outside the
  SQL blast radius). Fall back to the in-DB secret only for zero-
  downtime migration — existing operators upgrade without their
  running sessions being invalidated.
- The DB fallback emits a `RuntimeWarning` so monitoring / log audits
  pick it up. The fallback will be removed in v0.2; see
  docs/ai-cto/DECISIONS.md.
"""

from __future__ import annotations

import warnings
from functools import lru_cache

from app.config.env import JWT_SECRET_KEY
from app.db import GetDB, get_jwt_secret_key


class LegacyJWTSecretWarning(RuntimeWarning):
    """Raised when falling back to the in-database JWT secret.

    Distinct subclass so operators can escalate to an error with one
    `warnings.simplefilter("error", LegacyJWTSecretWarning)` line in
    their deployment once they are confident every environment sets
    the env var.
    """


@lru_cache(maxsize=None)
def get_secret_key() -> str:
    """Return the HMAC secret used to sign admin JWTs.

    Resolution order:
      1. ``JWT_SECRET_KEY`` environment variable (preferred).
      2. The ``jwt.secret_key`` row in the database (legacy, deprecated).

    Option 2 emits :class:`LegacyJWTSecretWarning`. The result is
    ``lru_cache``-d: operators must restart the process to pick up a
    rotated secret. A live-rotation path (re-sign all sessions) is a
    v0.2 concern.
    """
    if JWT_SECRET_KEY:
        return JWT_SECRET_KEY

    warnings.warn(
        "JWT_SECRET_KEY is not set in the environment; falling back to "
        "the in-database JWT secret. This is a known P0 hazard: any "
        "SQL-injection or DB dump exposes your signing key. Generate a "
        "secret with `python -c \"import secrets; "
        "print(secrets.token_hex(32))\"` and put it in .env before "
        "upgrading past v0.2.",
        category=LegacyJWTSecretWarning,
        stacklevel=2,
    )
    with GetDB() as db:
        return get_jwt_secret_key(db)
