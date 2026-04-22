"""Scheduled IP limiter detector task."""

from __future__ import annotations

import logging
import time
from collections import defaultdict

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app import marznode
from app.cache.redis import RedisDisabled, get_redis, is_redis_configured
from app.db import GetDB, crud
from app.db.models import User
from app.marznode import operations as marznode_operations
from app.notification.telegram import send_message
from hardening.iplimit.config import (
    IPLIMIT_AUDIT_LIMIT,
    IPLIMIT_LOG_READ_LIMIT,
    IPLIMIT_LOG_READ_TIMEOUT_SECONDS,
)
from hardening.iplimit.db import resolve_policy
from hardening.iplimit.events import ConnectionEvent, collect_events_from_nodes
from hardening.iplimit.store import (
    ViolationAuditEvent,
    clear_disabled_until,
    get_observed_ips,
    list_disabled_user_ids,
    observe_events,
    push_audit_event,
    set_disabled_until,
    should_emit_violation,
)

logger = logging.getLogger(__name__)

_redis_disabled_notice_logged = False


async def run_iplimit_poll() -> None:
    """Poll Marznode access events and enforce IP limit policies."""

    redis = _get_configured_redis()
    if redis is None:
        return

    now_ts = int(time.time())
    with GetDB() as db:
        await _restore_expired_disables(db, redis, now_ts=now_ts)
        users = _list_enabled_users(db)
        username_to_id = {user.username: user.id for user in users}

        events = await collect_events_from_nodes(
            marznode.nodes,
            username_to_id,
            max_lines_per_node=IPLIMIT_LOG_READ_LIMIT,
            read_timeout_seconds=IPLIMIT_LOG_READ_TIMEOUT_SECONDS,
        )
        await process_connection_events(
            db,
            redis,
            events,
            now_ts=now_ts,
            audit_limit=IPLIMIT_AUDIT_LIMIT,
        )


async def process_connection_events(
    db: Session,
    redis: object,
    events: list[ConnectionEvent],
    *,
    now_ts: int,
    audit_limit: int,
) -> list[ViolationAuditEvent]:
    """Process already-collected events.

    Split out for tests so CI never needs real Marznode or Redis.
    """

    await observe_events(redis, events, now_ts=now_ts)
    events_by_user: dict[int, list[ConnectionEvent]] = defaultdict(list)
    for event in events:
        events_by_user[event.user_id].append(event)

    violations: list[ViolationAuditEvent] = []
    for user_id, _user_events in events_by_user.items():
        user = crud.get_user_by_id(db, user_id)
        if not user or user.removed:
            continue
        policy = resolve_policy(db, user_id)
        observed_ips = await get_observed_ips(
            redis,
            user_id,
            now_ts=now_ts,
            window_seconds=policy.window_seconds,
        )
        if len(observed_ips) <= policy.max_concurrent_ips:
            continue

        event = ViolationAuditEvent(
            user_id=user_id,
            username=user.username,
            ip_list=sorted(observed_ips),
            count=len(observed_ips),
            action=policy.violation_action,
            ts=now_ts,
        )
        emitted = await should_emit_violation(
            redis,
            user_id=user_id,
            ip_list=event.ip_list,
            action=event.action,
            window_seconds=policy.window_seconds,
        )
        if not emitted:
            continue

        await push_audit_event(redis, event, audit_limit=audit_limit)
        if policy.violation_action == "disable":
            disabled_until = now_ts + policy.disable_duration_seconds
            await set_disabled_until(redis, user_id, disabled_until)
            _disable_user(db, user)
        else:
            await _send_warning(event)
        violations.append(event)

    return violations


def _get_configured_redis() -> object | None:
    global _redis_disabled_notice_logged

    if not is_redis_configured():
        if not _redis_disabled_notice_logged:
            logger.info("iplimit disabled: REDIS_URL is not configured")
            _redis_disabled_notice_logged = True
        return None

    try:
        return get_redis()
    except RedisDisabled:
        if not _redis_disabled_notice_logged:
            logger.info("iplimit disabled: Redis client unavailable")
            _redis_disabled_notice_logged = True
        return None


def _list_enabled_users(db: Session) -> list[User]:
    return (
        db.query(User)
        .filter(User.removed == sa.false())
        .filter(User.enabled == sa.true())
        .all()
    )


def _disable_user(db: Session, user: User) -> None:
    if not user.enabled and not user.activated:
        return
    user.enabled = False
    user.activated = False
    db.commit()
    marznode_operations.update_user(user, remove=True)
    logger.info("iplimit disabled user %s", user.username)


async def _restore_expired_disables(
    db: Session, redis: object, *, now_ts: int
) -> None:
    for user_id in await list_disabled_user_ids(redis):
        disabled_until = await clear_if_expired(redis, user_id, now_ts=now_ts)
        if disabled_until is None:
            continue
        user = crud.get_user_by_id(db, user_id)
        if not user or user.removed:
            continue
        if not user.enabled:
            user.enabled = True
            if user.is_active:
                user.activated = True
                marznode_operations.update_user(user)
            db.commit()
            logger.info("iplimit re-enabled user %s", user.username)


async def clear_if_expired(
    redis: object, user_id: int, *, now_ts: int
) -> int | None:
    from hardening.iplimit.store import get_disabled_until

    disabled_until = await get_disabled_until(redis, user_id)
    if disabled_until is None or disabled_until > now_ts:
        return None
    await clear_disabled_until(redis, user_id)
    return disabled_until


async def _send_warning(event: ViolationAuditEvent) -> None:
    ips = ", ".join(event.ip_list)
    await send_message(
        "IP limit warning\n"
        f"User: {event.username}\n"
        f"Distinct IPs: {event.count}\n"
        f"IPs: {ips}"
    )
