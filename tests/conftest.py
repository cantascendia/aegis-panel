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
from collections.abc import Generator, Iterator
from typing import TYPE_CHECKING

import pytest

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

    # Billing encryption + public URL. Production panels supply these
    # via .env; tests mirror that contract so the channel create/patch
    # and webhook paths exercise real Fernet + URL construction.
    from cryptography.fernet import Fernet

    from ops.billing import config as billing_config

    billing_config._reload_for_tests(
        secret_key=Fernet.generate_key().decode(),
        public_base_url="https://panel.test",
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
    """Per-test SQLAlchemy session bound to an in-memory SQLite.

    TODO(round-1, P0-security PR): wire this to `app.db.Session` with a
    transaction+rollback wrapper so tests never leak state.
    """
    pytest.skip("db_session fixture not implemented yet (round-1 follow-up)")
    yield  # type: ignore[misc]  # unreachable, satisfies generator contract


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
