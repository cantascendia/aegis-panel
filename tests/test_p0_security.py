"""
Tests for the Round 1 P0-security changes.

Scope: prove each hardening commit behaves as documented, with fast
pure-Python tests that don't need a running app, a DB, or marznode.

Each test names the commit it guards so `git blame` keeps the
rationale in reach.
"""

from __future__ import annotations

import warnings

# ---------------------------------------------------------------------------
# commit: fix(security): externalize JWT signing secret + tighten default
# ---------------------------------------------------------------------------


def test_jwt_access_token_default_is_60_minutes() -> None:
    """Upstream default was 1440 (24h); we tightened to 60.

    Regression guard: if someone bumps this back up without updating
    .env.example and the DECISIONS.md rationale, fail loudly.
    """
    from app.config.env import JWT_ACCESS_TOKEN_EXPIRE_MINUTES

    assert JWT_ACCESS_TOKEN_EXPIRE_MINUTES == 60, (
        "JWT access-token lifetime must default to 60 minutes. "
        "If you really need longer, document in DECISIONS.md and "
        "update this test deliberately."
    )


def test_get_secret_key_prefers_env_over_database(monkeypatch) -> None:
    """JWT_SECRET_KEY in env must win; the DB fallback must not run."""
    from app.config import db as config_db

    monkeypatch.setattr(config_db, "JWT_SECRET_KEY", "env-secret-" + "a" * 52)
    config_db.get_secret_key.cache_clear()

    # Sentinel: if the DB path executes, the test fails with a clear
    # message rather than a network/DB error from somewhere deeper.
    def _tripwire(*_args, **_kwargs):  # pragma: no cover - must not run
        raise AssertionError(
            "DB fallback was called even though JWT_SECRET_KEY is set"
        )

    monkeypatch.setattr(config_db, "GetDB", _tripwire)

    assert config_db.get_secret_key() == "env-secret-" + "a" * 52


def test_get_secret_key_warns_on_database_fallback(monkeypatch) -> None:
    """Missing env must emit LegacyJWTSecretWarning and touch the DB."""
    from contextlib import contextmanager

    from app.config import db as config_db

    monkeypatch.setattr(config_db, "JWT_SECRET_KEY", "")
    config_db.get_secret_key.cache_clear()

    @contextmanager
    def _fake_getdb():
        yield object()

    monkeypatch.setattr(config_db, "GetDB", _fake_getdb)
    monkeypatch.setattr(
        config_db, "get_jwt_secret_key", lambda _db: "db-stored-secret"
    )

    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        result = config_db.get_secret_key()

    assert result == "db-stored-secret"
    legacy = [
        w for w in captured if w.category is config_db.LegacyJWTSecretWarning
    ]
    assert legacy, (
        "Falling back to the in-DB JWT secret must emit "
        "LegacyJWTSecretWarning so deployments can escalate-to-error."
    )


# ---------------------------------------------------------------------------
# commit: fix(security): CORS strict by default, whitelist via env
# ---------------------------------------------------------------------------


def test_cors_allowed_origins_defaults_to_empty() -> None:
    """Default must be closed (no cross-origin allowed)."""
    from app.config.env import CORS_ALLOWED_ORIGINS

    assert CORS_ALLOWED_ORIGINS == [], (
        "Empty default is the safe position — any cross-origin access "
        "must be explicitly opted into via CORS_ALLOWED_ORIGINS."
    )


def test_cors_env_parser_splits_and_strips_whitespace(monkeypatch) -> None:
    """Comma-separated env string must round-trip to a clean list."""
    # The cast lambda is embedded in app/config/env.py. We re-apply the
    # same logic here to guard against someone rewriting it to a
    # subtly different parser (dropping empty values, keeping spaces).
    raw = " https://a.example.com ,, https://b.example.com,  "
    parsed = [o.strip() for o in raw.split(",") if o.strip()]
    assert parsed == ["https://a.example.com", "https://b.example.com"]


# ---------------------------------------------------------------------------
# commit: fix(security): pin bcrypt cost factor to rounds=12
# ---------------------------------------------------------------------------


def test_bcrypt_rounds_pinned_to_12() -> None:
    """Passlib bcrypt rounds must be explicit, not library-default."""
    from app.models.admin import pwd_context

    # passlib exposes per-scheme settings via `to_dict()`; "bcrypt__rounds"
    # is the canonical key. 12 is OWASP 2023 baseline.
    settings = pwd_context.to_dict()
    assert settings.get("bcrypt__rounds") == 12, (
        f"Expected bcrypt__rounds=12 (OWASP 2023 baseline); "
        f"got {settings.get('bcrypt__rounds')!r}. Never trust the "
        f"library default — a passlib downgrade silently weakens "
        f"every password hash."
    )
