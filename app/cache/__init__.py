"""
Optional shared-state substrate.

This package currently exposes one integration — Redis — used (or to
be used) by rate-limiting, hot-query caching, and task coordination.
Importing from this package must never fail if the backing service is
absent; see docs/ai-cto/SPEC-postgres-redis.md for the contract.
"""

from __future__ import annotations

from app.cache.redis import RedisDisabled, get_redis, is_redis_configured

__all__ = ["RedisDisabled", "get_redis", "is_redis_configured"]
