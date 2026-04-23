"""Redis persistence for IP limiter runtime state."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass

from hardening.iplimit.events import ConnectionEvent

KEY_PREFIX = "aegis:iplimit"


@dataclass(frozen=True)
class ViolationAuditEvent:
    """Persisted audit event for a policy violation."""

    user_id: int
    username: str
    ip_list: list[str]
    count: int
    action: str
    ts: int


def observed_key(user_id: int) -> str:
    return f"{KEY_PREFIX}:observed:{user_id}"


def violation_key(user_id: int) -> str:
    return f"{KEY_PREFIX}:violation:{user_id}"


def audit_key(user_id: int) -> str:
    return f"{KEY_PREFIX}:audit:{user_id}"


def dedupe_key(user_id: int) -> str:
    return f"{KEY_PREFIX}:dedupe:{user_id}"


async def observe_events(
    redis: object,
    events: Iterable[ConnectionEvent],
    *,
    now_ts: int,
) -> None:
    """Upsert last-seen timestamps for source IP observations."""

    for event in events:
        score = event.observed_at if event.observed_at is not None else now_ts
        await redis.zadd(observed_key(event.user_id), {event.source_ip: score})


async def get_observed_ips(
    redis: object,
    user_id: int,
    *,
    now_ts: int,
    window_seconds: int,
) -> list[str]:
    """Return distinct IPs still inside a user's rolling window."""

    key = observed_key(user_id)
    cutoff = now_ts - window_seconds
    await redis.zremrangebyscore(key, 0, cutoff)
    return list(await redis.zrange(key, 0, -1))


async def get_disabled_until(redis: object, user_id: int) -> int | None:
    value = await redis.get(violation_key(user_id))
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


async def set_disabled_until(
    redis: object, user_id: int, disabled_until_ts: int
) -> None:
    await redis.set(violation_key(user_id), str(disabled_until_ts))


async def clear_disabled_until(redis: object, user_id: int) -> None:
    await redis.delete(violation_key(user_id))


async def list_disabled_user_ids(redis: object) -> list[int]:
    user_ids: list[int] = []
    async for key in redis.scan_iter(
        match=f"{KEY_PREFIX}:violation:*", count=500
    ):
        try:
            user_ids.append(
                int(_redis_key_to_text(key).rsplit(":", maxsplit=1)[1])
            )
        except (IndexError, UnicodeDecodeError, ValueError):
            continue
    return user_ids


async def push_audit_event(
    redis: object,
    event: ViolationAuditEvent,
    *,
    audit_limit: int,
) -> None:
    key = audit_key(event.user_id)
    await redis.lpush(key, json.dumps(asdict(event), sort_keys=True))
    await redis.ltrim(key, 0, audit_limit - 1)


async def read_audit_events(
    redis: object, user_id: int, *, limit: int
) -> list[ViolationAuditEvent]:
    rows = await redis.lrange(audit_key(user_id), 0, limit - 1)
    events: list[ViolationAuditEvent] = []
    for row in rows:
        try:
            payload = json.loads(row)
            events.append(ViolationAuditEvent(**payload))
        except (TypeError, ValueError):
            continue
    return events


async def should_emit_violation(
    redis: object,
    *,
    user_id: int,
    ip_list: Sequence[str],
    action: str,
    window_seconds: int,
) -> bool:
    """Return True once per unchanged violation fingerprint."""

    fingerprint = _fingerprint(ip_list, action)
    key = f"{dedupe_key(user_id)}:{fingerprint}"
    return bool(await redis.set(key, fingerprint, nx=True, ex=window_seconds))


def _fingerprint(ip_list: Sequence[str], action: str) -> str:
    digest = hashlib.sha256()
    digest.update(action.encode())
    for ip in sorted(ip_list):
        digest.update(b"\0")
        digest.update(ip.encode())
    return digest.hexdigest()


def _redis_key_to_text(key: object) -> str:
    if isinstance(key, bytes):
        return key.decode()
    return str(key)
