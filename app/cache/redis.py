"""
Optional Redis 7 client.

Contract (per docs/ai-cto/SPEC-postgres-redis.md):

- Importing this module is always safe; it does not open a connection.
- `is_redis_configured()` returns whether `REDIS_URL` is set.
- `get_redis()` returns a shared async client when configured, else
  raises :class:`RedisDisabled` with an actionable message.
- Connection is lazy: the first `get_redis()` call instantiates the
  client. Subsequent calls return the cached instance.
- Connection errors surface **on first use** of the returned client,
  not at `get_redis()` time. This preserves the "startup must not
  crash if Redis is unreachable" property: the panel starts, logs a
  warning when something tries to use Redis, and continues serving
  non-Redis paths.

This PR introduces the client without any caller. The first consumer
lands in the admin-rate-limit PR.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.config.env import REDIS_POOL_SIZE, REDIS_URL

if TYPE_CHECKING:
    from redis.asyncio import Redis


class RedisDisabled(RuntimeError):
    """Raised by `get_redis()` when `REDIS_URL` is not configured.

    Callers that *require* Redis (e.g. rate limiting) should catch
    this and fail loud — silently degrading to in-process state would
    defeat the whole point of a shared counter. Callers that can
    degrade gracefully (e.g. opportunistic caching) should check
    `is_redis_configured()` first and skip the code path.
    """


_client: Redis | None = None


def is_redis_configured() -> bool:
    """True iff `REDIS_URL` is set in env.

    Does not open a connection — safe to call at startup time.
    """
    return bool(REDIS_URL)


def get_redis() -> Redis:
    """Return the shared async Redis client.

    Raises :class:`RedisDisabled` if `REDIS_URL` is unset.

    The first call imports the `redis` package and constructs the
    client with a connection pool of size `REDIS_POOL_SIZE`. The
    actual TCP connection is established lazily by the client on
    first command — network failures surface there, not here.
    """
    global _client

    if not REDIS_URL:
        raise RedisDisabled(
            "REDIS_URL is not set. This feature requires Redis 7. "
            "Start the optional compose profile "
            "(`docker compose --profile redis up -d`) or set REDIS_URL "
            "in .env to an existing Redis instance."
        )

    if _client is None:
        # Deferred import so the `redis` package isn't mandatory for
        # deployments that don't use it. Listed in requirements.txt
        # regardless, so this is belt-and-suspenders.
        from redis.asyncio import Redis as AsyncRedis
        from redis.asyncio.connection import ConnectionPool

        pool = ConnectionPool.from_url(
            REDIS_URL,
            max_connections=REDIS_POOL_SIZE,
            decode_responses=True,
        )
        _client = AsyncRedis.from_pool(pool)

    return _client


async def close_redis() -> None:
    """Release the shared client's connection pool.

    Call from the FastAPI lifespan shutdown hook once the
    rate-limiter (or any Redis consumer) is wired up. Harmless no-op
    if no client was ever constructed.
    """
    global _client

    if _client is not None:
        await _client.aclose()
        _client = None
