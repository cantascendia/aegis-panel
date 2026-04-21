"""
Tests for the optional Redis client.

Scope: prove the "optional" contract — importing the module is safe,
`is_redis_configured()` reports the right thing, and `get_redis()`
degrades predictably.

Out of scope: any test that needs a live Redis. Those belong in a
future CI matrix that runs the compose `redis` profile; doing it here
would turn a 2-second unit test into a container pull.
"""

from __future__ import annotations

import pytest


def test_package_import_never_touches_network() -> None:
    """`import app.cache` must be safe at startup even if Redis is down.

    If this fails, any import cycle or eager connection attempt
    has crept in — back it out before it causes a startup crash
    in production.
    """
    import app.cache  # noqa: F401


def test_is_redis_configured_false_when_url_unset(monkeypatch) -> None:
    from app.cache import redis as cache_redis

    monkeypatch.setattr(cache_redis, "REDIS_URL", "")
    cache_redis._client = None

    assert cache_redis.is_redis_configured() is False


def test_is_redis_configured_true_when_url_set(monkeypatch) -> None:
    from app.cache import redis as cache_redis

    monkeypatch.setattr(cache_redis, "REDIS_URL", "redis://127.0.0.1:6379/0")
    cache_redis._client = None

    assert cache_redis.is_redis_configured() is True


def test_get_redis_raises_redisdisabled_when_unset(monkeypatch) -> None:
    """Consumers that *require* Redis get a typed, actionable error."""
    from app.cache import redis as cache_redis

    monkeypatch.setattr(cache_redis, "REDIS_URL", "")
    cache_redis._client = None

    with pytest.raises(cache_redis.RedisDisabled) as exc_info:
        cache_redis.get_redis()

    # The error message must name the env var and point at the fix.
    # If someone "helpfully" rewrites this to a generic RuntimeError,
    # the test catches it.
    message = str(exc_info.value)
    assert "REDIS_URL" in message
    assert "compose" in message.lower() or ".env" in message


def test_get_redis_builds_pool_lazily(monkeypatch) -> None:
    """First call constructs the client without actually connecting.

    We never import `redis.asyncio` unless REDIS_URL is set, so this
    also implicitly guards against the `redis` package becoming a
    hard import-time dependency.
    """
    from app.cache import redis as cache_redis

    monkeypatch.setattr(cache_redis, "REDIS_URL", "redis://127.0.0.1:6379/0")
    monkeypatch.setattr(cache_redis, "REDIS_POOL_SIZE", 5)
    cache_redis._client = None

    client = cache_redis.get_redis()
    assert client is not None

    # Same call returns the same cached client (the sentinel for
    # "we're actually using a singleton pool, not reconstructing").
    assert cache_redis.get_redis() is client

    # Cleanup so session-scoped state doesn't leak into later tests.
    cache_redis._client = None
