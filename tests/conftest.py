"""
Shared pytest fixtures.

Scope of this file (Round 1 — scaffolding):
- Provide the *contract* for the fixtures the test suite is going to rely on
  (`db_session`, `app`, `client`, `mock_marznode`) so subsequent PRs can fill
  each in without negotiating the shape again.
- Give enough glue that a trivial test (`tests/test_smoke.py`) can run today
  against an in-memory SQLite and catch import-time regressions.

Non-goals for now:
- Full transaction isolation per test (savepoints/rollback) — done in the
  P0-security PR where auth tests actually need it.
- Marznode gRPC mocking — stubbed, real doubles land when iplimit work starts.
- Factory Boy / model factories — introduced when we have >3 model-touching
  tests so the abstraction pays for itself.
"""

from __future__ import annotations

import os

# CRITICAL: set JWT_SECRET_KEY at conftest module-import time, BEFORE
# any test module imports `app.config.env` (which captures the env var
# at import time into a module-level constant). Doing this in a
# session-scoped autouse fixture is too late — the constant is already
# bound to "" and ``get_secret_key`` falls back to the DB-backed
# legacy path which queries the ``jwt`` table.
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-not-for-prod")

from collections.abc import Generator, Iterator  # noqa: E402
from typing import TYPE_CHECKING  # noqa: E402

import pytest  # noqa: E402

# Type-only imports. `from __future__ import annotations` makes every
# annotation a lazy string, so names imported here never need to exist
# at runtime — they do not trigger real fastapi/sqlalchemy imports until
# a tool (mypy, pyright) resolves them.
if TYPE_CHECKING:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session


# ---------------------------------------------------------------------------
# Environment hygiene: force tests off any developer .env values that could
# reach production systems by accident (SQLALCHEMY_DATABASE_URL pointing at a
# real Postgres, webhook URLs, Telegram tokens, etc.).
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session", autouse=True)
def _isolated_env() -> Iterator[None]:
    """Scrub env vars that must never leak into tests.

    Autouse + session scope: applied once before any other fixture resolves.
    """
    dangerous = [
        "SQLALCHEMY_DATABASE_URL",
        "WEBHOOK_ADDRESS",
        "WEBHOOK_SECRET",
        "TELEGRAM_API_TOKEN",
        "DISCORD_WEBHOOK_URL",
    ]
    saved: dict[str, str] = {}
    for key in dangerous:
        if key in os.environ:
            saved[key] = os.environ.pop(key)

    # Point the app at an ephemeral in-memory SQLite unless a test overrides.
    os.environ.setdefault("SQLALCHEMY_DATABASE_URL", "sqlite:///:memory:")

    # JWT_SECRET_KEY is pinned at conftest module-import time (see top
    # of file) so ``app.config.env`` captures it. Tests that need a
    # different value should monkeypatch and call ``get_secret_key.cache_clear()``.

    # Billing encryption + public URL. Production panels supply these
    # via .env; tests mirror that contract so the channel create/patch
    # and webhook paths exercise real Fernet + URL construction.
    from cryptography.fernet import Fernet

    from ops.billing import config as billing_config

    # In tests, FastAPI's TestClient sends requests with peer
    # 127.0.0.1; trusting that lets the existing X-Forwarded-For
    # tests exercise the "behind a trusted proxy" path. A dedicated
    # spoofing test (test_webhook_ip_allowlist_ignores_spoofed_xff_when_peer_untrusted)
    # overrides this back to "" to verify the "no trusted proxy"
    # path rejects the same request.
    billing_config._reload_for_tests(
        secret_key=Fernet.generate_key().decode(),
        public_base_url="https://panel.test",
        trusted_proxies="127.0.0.1/32,::1/128",
    )

    yield

    for key, value in saved.items():
        os.environ[key] = value


# ---------------------------------------------------------------------------
# Database fixture — stub.
# Real implementation lands in the P0-security PR where admin/user tests
# need a populated schema. For now we expose the name so imports don't break.
# ---------------------------------------------------------------------------


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Per-test SQLAlchemy session bound to a fresh in-memory SQLite.

    Each test gets its own throw-away DB:
    - New ``StaticPool`` engine (single-connection so multiple
      ``Session`` objects in one test see the same in-memory schema).
    - ``Base.metadata.create_all`` to materialise upstream tables AND
      every fork-owned model registered via ``app.db.extra_models``
      (LESSONS L-014 — that aggregator is the single registration
      point so this fixture doesn't need to know about new modules).
    - Yielded session is committed-as-you-go (no transaction wrapper);
      teardown drops the engine so the next test starts clean.

    AL.4 unblock: the original Round-1 ``pytest.skip`` was a stub
    (TODO P0-security PR never landed because tests didn't need DB
    until billing). AL.4 retention sweep tests are the first concrete
    consumer; codex review on the AL.4 PR (REVIEW-QUEUE.md, commit
    49c7c7c) flagged the stub as a P2.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    # Import the audit ORM module so AuditEvent is registered on
    # Base.metadata. We deliberately do NOT import the upstream model
    # aggregator here: a few upstream columns (e.g.
    # ``admins.subscription_url_prefix`` with ``default=""``) emit DDL
    # that SQLite rejects as ``DEFAULT  NOT NULL`` (empty literal,
    # syntax error). Fixing that belongs in upstream and is out of
    # scope for AL.4. Tests using db_session today only need the
    # audit table; future fork modules should append their tables to
    # the explicit list rather than going back to a full
    # ``create_all`` of the whole metadata.
    from app.db.base import Base
    from app.db.models import JWT  # upstream model — needed by audit JWT
    from ops.audit.db import AuditEvent

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Materialise just the tables our audit-log tests touch:
    # - aegis_audit_events: target table for inserts/queries.
    # - jwt: ``app.utils.auth.create_admin_token`` reads/writes the
    #   shared admin JWT secret here on first call (single-row table),
    #   so AL.2c.3 actor-decode tests need it to mint tokens.
    Base.metadata.create_all(
        engine, tables=[AuditEvent.__table__, JWT.__table__]
    )
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


# ---------------------------------------------------------------------------
# FastAPI app + HTTP client fixtures — stub.
# ---------------------------------------------------------------------------


@pytest.fixture
def app() -> FastAPI:
    """The ASGI application under test.

    TODO(round-1): import `app.marzneshin` and return the app factory output,
    overriding dependencies (DB, marznode) with test doubles.
    """
    pytest.skip("app fixture not implemented yet (round-1 follow-up)")


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    """Synchronous HTTP test client. Async tests should use httpx.AsyncClient."""
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Marznode gRPC double — stub.
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_marznode() -> Iterator[object]:
    """Fake Marznode client so tests don't need a real data-plane node.

    TODO(round-1, iplimit PR): concrete fake implementing the subset of
    `app/marznode/*` gRPC surface that the control plane calls.
    """
    pytest.skip(
        "mock_marznode fixture not implemented yet (round-1 follow-up)"
    )
    yield  # type: ignore[misc]
