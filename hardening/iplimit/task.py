"""Scheduled IP limiter detector task."""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app import marznode
from app.cache.redis import RedisDisabled, get_redis, is_redis_configured
from app.db import GetDB, crud
from app.db.models import User
from app.models.user import User as MarznodeUser
from app.notification.telegram import send_message
from hardening.iplimit.config import (
    IPLIMIT_AUDIT_LIMIT,
    IPLIMIT_LOG_READ_LIMIT,
    IPLIMIT_LOG_READ_TIMEOUT_SECONDS,
)
from hardening.iplimit.db import (
    clear_disabled_state,
    get_disabled_state,
    list_disabled_states,
    resolve_policies,
    upsert_disabled_state,
)
from hardening.iplimit.events import ConnectionEvent, collect_events_from_nodes
from hardening.iplimit.store import (
    ViolationAuditEvent,
    clear_disabled_until,
    get_observed_ips,
    observe_events,
    push_audit_event,
    set_disabled_until,
    should_emit_violation,
)

logger = logging.getLogger(__name__)

_redis_disabled_notice_logged = False
_tz_warning_logged = False


async def run_iplimit_poll() -> None:
    """Poll Marznode access events and enforce IP limit policies."""

    _warn_if_panel_timezone_not_utc()
    redis = _get_configured_redis()
    if redis is None:
        return

    now_ts = int(time.time())
    with GetDB() as db:
        await _restore_or_retry_disables(db, redis, now_ts=now_ts)
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

    user_ids = list(events_by_user)
    users = _load_users_by_ids(db, user_ids)
    policies = resolve_policies(db, list(users))

    violations: list[ViolationAuditEvent] = []
    for user_id, _user_events in events_by_user.items():
        user = users.get(user_id)
        if not user or user.removed:
            continue
        policy = policies[user_id]
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
            _disable_user(
                db,
                user,
                disabled_until=disabled_until,
                disabled_at=now_ts,
            )
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


def _load_users_by_ids(db: Session, user_ids: list[int]) -> dict[int, User]:
    if not user_ids:
        return {}
    users = db.query(User).filter(User.id.in_(user_ids)).all()
    return {user.id: user for user in users}


def _disable_user(
    db: Session, user: User, *, disabled_until: int, disabled_at: int
) -> None:
    if not user.enabled and not user.activated:
        return
    state = get_disabled_state(db, user.id)
    previous_enabled = state.previous_enabled if state else user.enabled
    previous_activated = state.previous_activated if state else user.activated
    upsert_disabled_state(
        db,
        user_id=user.id,
        disabled_until=disabled_until,
        disabled_at=disabled_at,
        previous_enabled=previous_enabled,
        previous_activated=previous_activated,
        reason="iplimit_violation",
    )
    user.enabled = False
    user.activated = False
    db.commit()
    _schedule_user_update(user, remove=True)
    logger.info("iplimit disabled user %s", user.username)


async def _restore_or_retry_disables(
    db: Session, redis: object, *, now_ts: int
) -> None:
    for state in list_disabled_states(db):
        user = crud.get_user_by_id(db, state.user_id)
        if not user or user.removed:
            clear_disabled_state(db, state.user_id)
            await clear_disabled_until(redis, state.user_id)
            db.commit()
            continue

        if state.disabled_until > now_ts:
            if not user.enabled:
                _schedule_user_update(user, remove=True)
            continue

        await clear_iplimit_disable(db, redis, user, now_ts=now_ts)


async def clear_iplimit_disable(
    db: Session, redis: object | None, user: User, *, now_ts: int
) -> bool:
    """Clear limiter-owned disable state and restore when policy gates allow."""

    state = get_disabled_state(db, user.id)
    if redis is not None:
        await clear_disabled_until(redis, user.id)
    if state is None:
        return False

    should_restore = (
        state.previous_enabled and not user.enabled and _can_enable_now(user)
    )
    clear_disabled_state(db, user.id)
    if should_restore:
        user.enabled = True
        user.activated = state.previous_activated
        logger.info("iplimit re-enabled user %s", user.username)
    db.commit()
    if should_restore and user.is_active and user.activated:
        _schedule_user_update(user)
    return should_restore


async def clear_if_expired(
    redis: object, user_id: int, *, now_ts: int
) -> int | None:
    from hardening.iplimit.store import get_disabled_until

    disabled_until = await get_disabled_until(redis, user_id)
    if disabled_until is None or disabled_until > now_ts:
        return None
    await clear_disabled_until(redis, user_id)
    return disabled_until


def _can_enable_now(user: User) -> bool:
    return (
        not user.removed and not user.expired and not user.data_limit_reached
    )


def _schedule_user_update(user: User, *, remove: bool = False) -> None:
    node_inbounds: dict[int, list[str]] = defaultdict(list)
    if remove:
        for inbound in user.inbounds:
            node_inbounds[inbound.node_id]
    else:
        for inbound in user.inbounds:
            node_inbounds[inbound.node_id].append(inbound.tag)

    payload = MarznodeUser.model_validate(user)
    for node_id, tags in node_inbounds.items():
        node = marznode.nodes.get(node_id)
        if node is None:
            continue
        update_task = asyncio.ensure_future(
            node.update_user(user=payload, inbounds=tags)
        )
        update_task.add_done_callback(
            lambda done, node_id=node_id, username=user.username: (
                _log_update_failure(done, node_id=node_id, username=username)
            )
        )


def _log_update_failure(
    done: asyncio.Future, *, node_id: int, username: str
) -> None:
    try:
        done.result()
    except Exception:
        logger.exception(
            "iplimit failed to push user %s update to node %s",
            username,
            node_id,
        )


def _warn_if_panel_timezone_not_utc() -> None:
    global _tz_warning_logged
    if _tz_warning_logged:
        return
    _tz_warning_logged = True
    if time.timezone != 0:
        logger.warning(
            "iplimit: panel container TZ is not UTC; confirm all marznode "
            "containers match or events may be silently dropped"
        )


async def _send_warning(event: ViolationAuditEvent) -> None:
    ips = ", ".join(event.ip_list)
    await send_message(
        "IP limit warning\n"
        f"User: {event.username}\n"
        f"Distinct IPs: {event.count}\n"
        f"IPs: {ips}"
    )
