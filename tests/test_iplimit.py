from __future__ import annotations

import asyncio
import time
from collections.abc import Generator
from datetime import datetime

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import User
from app.models.user import UserExpireStrategy
from hardening.iplimit import task
from hardening.iplimit.allowlist import ip_matches_any_cidr, parse_cidrs
from hardening.iplimit.db import (
    IpLimitConfig,
    IpLimitDisabledState,
    UserIpLimitOverride,
    resolve_policy,
    upsert_disabled_state,
)
from hardening.iplimit.endpoint import (
    IpLimitOverridePatch,
    clear_user_iplimit_disable,
    get_user_iplimit_audit,
    get_user_iplimit_state,
    patch_user_iplimit_override,
)
from hardening.iplimit.events import (
    ConnectionEvent,
    collect_events_from_nodes,
    parse_xray_access_line,
)
from hardening.iplimit.store import (
    ViolationAuditEvent,
    audit_key,
    get_observed_ips,
    push_audit_event,
    read_audit_events,
    set_disabled_until,
    should_emit_violation,
)
from hardening.iplimit.task import process_connection_events


class FakeRedis:
    def __init__(self) -> None:
        self.zsets: dict[str, dict[str, int]] = {}
        self.strings: dict[str, str] = {}
        self.lists: dict[str, list[str]] = {}

    async def zadd(self, key: str, mapping: dict[str, int]) -> None:
        self.zsets.setdefault(key, {}).update(mapping)

    async def zremrangebyscore(
        self, key: str, minimum: int, maximum: int
    ) -> None:
        zset = self.zsets.setdefault(key, {})
        for member, score in list(zset.items()):
            if minimum <= score <= maximum:
                del zset[member]

    async def zrange(self, key: str, start: int, end: int) -> list[str]:
        members = [
            member
            for member, _ in sorted(
                self.zsets.setdefault(key, {}).items(),
                key=lambda item: (item[1], item[0]),
            )
        ]
        if end == -1:
            return members[start:]
        return members[start : end + 1]

    async def get(self, key: str) -> str | None:
        return self.strings.get(key)

    async def set(
        self,
        key: str,
        value: str,
        ex: int | None = None,
        nx: bool = False,
    ) -> bool:
        _ = ex
        if nx and key in self.strings:
            return False
        self.strings[key] = value
        return True

    async def delete(self, key: str) -> None:
        self.strings.pop(key, None)

    async def keys(self, pattern: str) -> list[str]:
        prefix = pattern.removesuffix("*")
        return [key for key in self.strings if key.startswith(prefix)]

    async def lpush(self, key: str, value: str) -> None:
        self.lists.setdefault(key, []).insert(0, value)

    async def ltrim(self, key: str, start: int, end: int) -> None:
        self.lists[key] = self.lists.setdefault(key, [])[start : end + 1]

    async def lrange(self, key: str, start: int, end: int) -> list[str]:
        values = self.lists.setdefault(key, [])
        if end == -1:
            return values[start:]
        return values[start : end + 1]


@pytest.fixture
def db() -> Generator[Session, None, None]:
    import hardening.iplimit.db  # noqa: F401

    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE services (
                    id INTEGER PRIMARY KEY,
                    name VARCHAR(64)
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE users_services (
                    user_id INTEGER NOT NULL,
                    service_id INTEGER NOT NULL,
                    PRIMARY KEY (user_id, service_id)
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY,
                    username VARCHAR(32) UNIQUE,
                    key VARCHAR(64) UNIQUE,
                    activated BOOLEAN NOT NULL DEFAULT 1,
                    enabled BOOLEAN NOT NULL DEFAULT 1,
                    removed BOOLEAN NOT NULL DEFAULT 0,
                    used_traffic BIGINT,
                    lifetime_used_traffic BIGINT NOT NULL DEFAULT 0,
                    traffic_reset_at DATETIME,
                    data_limit BIGINT,
                    data_limit_reset_strategy VARCHAR(32),
                    ip_limit INTEGER NOT NULL DEFAULT -1,
                    settings VARCHAR(1024),
                    expire_strategy VARCHAR(32) NOT NULL,
                    expire_date DATETIME,
                    usage_duration BIGINT,
                    activation_deadline DATETIME,
                    admin_id INTEGER,
                    sub_updated_at DATETIME,
                    sub_last_user_agent VARCHAR(512),
                    sub_revoked_at DATETIME,
                    created_at DATETIME,
                    note VARCHAR(500),
                    online_at DATETIME,
                    edit_at DATETIME
                )
                """
            )
        )
    IpLimitConfig.__table__.create(engine)
    UserIpLimitOverride.__table__.create(engine)
    IpLimitDisabledState.__table__.create(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def add_user(db: Session, username: str = "alice") -> User:
    user = User(
        username=username,
        key=f"{username}-key",
        expire_strategy=UserExpireStrategy.NEVER,
        enabled=True,
        activated=True,
        removed=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def add_config(
    db: Session,
    *,
    max_concurrent_ips: int = 2,
    window_seconds: int = 300,
    violation_action: str = "warn",
    disable_duration_seconds: int = 60,
) -> None:
    db.add(
        IpLimitConfig(
            id=1,
            max_concurrent_ips=max_concurrent_ips,
            window_seconds=window_seconds,
            violation_action=violation_action,
            disable_duration_seconds=disable_duration_seconds,
        )
    )
    db.commit()


def test_parse_xray_access_line_extracts_known_user_ip() -> None:
    expected_ts = int(
        time.mktime(
            datetime.strptime(
                "2026/04/22 01:02:03", "%Y/%m/%d %H:%M:%S"
            ).timetuple()
        )
    )
    line = (
        "2026/04/22 01:02:03 from tcp:203.0.113.9:51234 "
        "accepted tcp:example.com:443 email: alice"
    )

    event = parse_xray_access_line(line, {"alice": 10})

    assert event == ConnectionEvent(
        user_id=10,
        username="alice",
        source_ip="203.0.113.9",
        observed_at=expected_ts,
    )


def test_parse_xray_access_line_ignores_unknown_user() -> None:
    line = "from tcp:203.0.113.9:51234 accepted tcp:x:443 email: bob"

    assert parse_xray_access_line(line, {"alice": 10}) is None


def test_parse_xray_access_line_ignores_malformed_ip() -> None:
    line = "from tcp:not-an-ip:51234 accepted tcp:x:443 email: alice"

    assert parse_xray_access_line(line, {"alice": 10}) is None


def test_parse_cidrs_accepts_ipv4_ipv6_mixed() -> None:
    networks = parse_cidrs("203.0.113.0/24\n2001:db8::/32\n")

    assert [str(network) for network in networks] == [
        "203.0.113.0/24",
        "2001:db8::/32",
    ]


def test_parse_cidrs_rejects_invalid_cidr() -> None:
    with pytest.raises(ValueError, match="invalid CIDR"):
        parse_cidrs("203.0.113.0/24\nnot-a-cidr")


def test_ip_matches_allowlist_ipv4() -> None:
    assert ip_matches_any_cidr("203.0.113.9", parse_cidrs("203.0.113.0/24"))


def test_ip_matches_allowlist_ipv6() -> None:
    assert ip_matches_any_cidr("2001:db8::9", parse_cidrs("2001:db8::/32"))


def test_ip_outside_allowlist_not_matched() -> None:
    assert not ip_matches_any_cidr(
        "198.51.100.9", parse_cidrs("203.0.113.0/24")
    )


def test_event_parser_skips_allowlisted_ip() -> None:
    line = "from tcp:203.0.113.9:51234 accepted tcp:x:443 email: alice"

    assert (
        parse_xray_access_line(
            line,
            {"alice": 10},
            {"alice": parse_cidrs("203.0.113.0/24")},
        )
        is None
    )


@pytest.mark.asyncio
async def test_collect_events_from_nodes_is_bounded() -> None:
    class FakeNode:
        async def get_logs(self, name: str, include_buffer: bool):
            assert name == "xray"
            assert include_buffer is True
            yield "from tcp:203.0.113.1:1 accepted tcp:x:443 email: alice"
            yield "from tcp:203.0.113.2:2 accepted tcp:x:443 email: alice"

    events = await collect_events_from_nodes(
        {1: FakeNode()},
        {"alice": 7},
        max_lines_per_node=1,
        read_timeout_seconds=1,
    )

    assert events == [
        ConnectionEvent(user_id=7, username="alice", source_ip="203.0.113.1")
    ]


@pytest.mark.asyncio
async def test_buffer_replay_does_not_disable_with_stale_log_timestamp(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = add_user(db)
    add_config(
        db,
        max_concurrent_ips=1,
        window_seconds=300,
        violation_action="disable",
    )
    redis = FakeRedis()
    pushes: list[bool] = []
    log_ts = int(
        time.mktime(
            datetime.strptime(
                "2026/04/22 01:02:03", "%Y/%m/%d %H:%M:%S"
            ).timetuple()
        )
    )

    class FakeNode:
        async def get_logs(self, name: str, include_buffer: bool):
            assert name == "xray"
            assert include_buffer is True
            yield (
                "2026/04/22 01:02:03 from tcp:203.0.113.1:1 "
                "accepted tcp:x:443 email: alice"
            )
            yield (
                "2026/04/22 01:02:03 from tcp:203.0.113.2:2 "
                "accepted tcp:x:443 email: alice"
            )

    monkeypatch.setattr(
        task,
        "_schedule_user_update",
        lambda user, remove=False: pushes.append(remove),
    )

    for _ in range(2):
        events = await collect_events_from_nodes(
            {1: FakeNode()},
            {user.username: user.id},
            max_lines_per_node=10,
            read_timeout_seconds=1,
        )
        violations = await process_connection_events(
            db,
            redis,
            events,
            now_ts=log_ts + 301,
            audit_limit=10,
        )
        assert violations == []

    db.refresh(user)
    assert user.enabled is True
    assert pushes == []


@pytest.mark.asyncio
async def test_window_based_concurrent_ip_counting(db: Session) -> None:
    user = add_user(db)
    add_config(db, max_concurrent_ips=99, window_seconds=10)
    redis = FakeRedis()

    await process_connection_events(
        db,
        redis,
        [
            ConnectionEvent(user.id, user.username, "203.0.113.1"),
            ConnectionEvent(user.id, user.username, "203.0.113.2"),
        ],
        now_ts=100,
        audit_limit=10,
    )
    await process_connection_events(
        db,
        redis,
        [ConnectionEvent(user.id, user.username, "203.0.113.3")],
        now_ts=111,
        audit_limit=10,
    )

    observed = await get_observed_ips(
        redis, user.id, now_ts=111, window_seconds=10
    )

    assert observed == ["203.0.113.3"]


@pytest.mark.asyncio
async def test_warn_action_writes_audit_and_alerts_once(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = add_user(db)
    add_config(db, max_concurrent_ips=1, violation_action="warn")
    redis = FakeRedis()
    alerts: list[str] = []

    async def fake_warning(event) -> None:
        alerts.append(event.username)

    monkeypatch.setattr(task, "_send_warning", fake_warning)
    events = [
        ConnectionEvent(user.id, user.username, "203.0.113.1"),
        ConnectionEvent(user.id, user.username, "203.0.113.2"),
    ]

    first = await process_connection_events(
        db, redis, events, now_ts=100, audit_limit=10
    )
    second = await process_connection_events(
        db, redis, events, now_ts=101, audit_limit=10
    )

    assert len(first) == 1
    assert second == []
    assert alerts == ["alice"]
    assert len(redis.lists[audit_key(user.id)]) == 1


@pytest.mark.asyncio
async def test_disable_action_marks_user_disabled(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = add_user(db)
    add_config(
        db,
        max_concurrent_ips=1,
        violation_action="disable",
        disable_duration_seconds=120,
    )
    redis = FakeRedis()
    pushed: list[bool] = []

    def fake_schedule_user_update(user, remove: bool = False) -> None:
        _ = user
        pushed.append(remove)

    monkeypatch.setattr(
        task, "_schedule_user_update", fake_schedule_user_update
    )

    violations = await process_connection_events(
        db,
        redis,
        [
            ConnectionEvent(user.id, user.username, "203.0.113.1"),
            ConnectionEvent(user.id, user.username, "203.0.113.2"),
        ],
        now_ts=100,
        audit_limit=10,
    )

    db.refresh(user)
    assert violations[0].action == "disable"
    assert user.enabled is False
    assert user.activated is False
    assert pushed == [True]
    assert redis.strings[f"aegis:iplimit:violation:{user.id}"] == "220"


@pytest.mark.asyncio
async def test_disable_action_is_idempotent_for_same_ip_set(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = add_user(db)
    add_config(db, max_concurrent_ips=1, violation_action="disable")
    redis = FakeRedis()
    pushes: list[bool] = []

    def fake_schedule_user_update(user, remove: bool = False) -> None:
        _ = user
        pushes.append(remove)

    monkeypatch.setattr(
        task, "_schedule_user_update", fake_schedule_user_update
    )
    events = [
        ConnectionEvent(user.id, user.username, "203.0.113.1"),
        ConnectionEvent(user.id, user.username, "203.0.113.2"),
    ]

    first = await process_connection_events(
        db, redis, events, now_ts=100, audit_limit=10
    )
    second = await process_connection_events(
        db, redis, events, now_ts=101, audit_limit=10
    )

    assert len(first) == 1
    assert second == []
    assert pushes == [True]


def test_redis_disabled_skip_logs_once(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    import logging

    caplog.set_level(logging.INFO, logger="hardening.iplimit.task")
    monkeypatch.setattr(task, "_redis_disabled_notice_logged", False)
    monkeypatch.setattr(task, "is_redis_configured", lambda: False)

    first = task._get_configured_redis()
    second = task._get_configured_redis()

    assert first is None
    assert second is None
    assert caplog.text.count("iplimit disabled") == 1


def test_user_override_falls_back_to_global_config(db: Session) -> None:
    user = add_user(db)
    add_config(
        db,
        max_concurrent_ips=4,
        window_seconds=600,
        violation_action="disable",
        disable_duration_seconds=1800,
    )
    db.add(
        UserIpLimitOverride(
            user_id=user.id,
            max_concurrent_ips=2,
            window_seconds=None,
            violation_action=None,
        )
    )
    db.commit()

    policy = resolve_policy(db, user.id)

    assert policy.max_concurrent_ips == 2
    assert policy.window_seconds == 600
    assert policy.violation_action == "disable"
    assert policy.disable_duration_seconds == 1800


def test_override_allowlist_merges_with_global(db: Session) -> None:
    user = add_user(db)
    db.add(
        IpLimitConfig(
            id=1,
            max_concurrent_ips=4,
            window_seconds=600,
            violation_action="warn",
            disable_duration_seconds=1800,
            ip_allowlist_cidrs="203.0.113.0/24",
        )
    )
    db.add(
        UserIpLimitOverride(
            user_id=user.id,
            ip_allowlist_cidrs="2001:db8::/32",
        )
    )
    db.commit()

    networks = parse_cidrs(resolve_policy(db, user.id).ip_allowlist_cidrs)

    assert ip_matches_any_cidr("203.0.113.9", networks)
    assert ip_matches_any_cidr("2001:db8::9", networks)


@pytest.mark.asyncio
async def test_audit_list_is_capped_and_read_newest_first() -> None:
    redis = FakeRedis()
    await push_audit_event(
        redis,
        ViolationAuditEvent(1, "alice", ["203.0.113.1"], 1, "warn", 100),
        audit_limit=2,
    )
    await push_audit_event(
        redis,
        ViolationAuditEvent(1, "alice", ["203.0.113.2"], 1, "warn", 101),
        audit_limit=2,
    )
    await push_audit_event(
        redis,
        ViolationAuditEvent(1, "alice", ["203.0.113.3"], 1, "warn", 102),
        audit_limit=2,
    )

    events = await read_audit_events(redis, 1, limit=10)

    assert [event.ts for event in events] == [102, 101]


@pytest.mark.asyncio
async def test_expired_disable_key_is_cleared() -> None:
    redis = FakeRedis()
    await set_disabled_until(redis, 1, 99)

    expired_at = await task.clear_if_expired(redis, 1, now_ts=100)

    assert expired_at == 99
    assert "aegis:iplimit:violation:1" not in redis.strings


@pytest.mark.asyncio
async def test_restore_skips_user_disabled_by_other_means(
    db: Session,
) -> None:
    user = add_user(db)
    user.enabled = False
    user.activated = False
    db.commit()
    redis = FakeRedis()
    await set_disabled_until(redis, user.id, 99)

    await task._restore_or_retry_disables(db, redis, now_ts=100)

    db.refresh(user)
    assert user.enabled is False
    assert user.activated is False


@pytest.mark.asyncio
async def test_restore_clears_owned_disable_but_respects_data_gate(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = add_user(db)
    user.enabled = False
    user.activated = False
    user.used_traffic = 10
    user.data_limit = 1
    upsert_disabled_state(
        db,
        user_id=user.id,
        disabled_until=99,
        disabled_at=50,
        previous_enabled=True,
        previous_activated=True,
        reason="iplimit_violation",
    )
    db.commit()
    redis = FakeRedis()
    pushes: list[bool] = []
    monkeypatch.setattr(
        task,
        "_schedule_user_update",
        lambda user, remove=False: pushes.append(remove),
    )

    await task._restore_or_retry_disables(db, redis, now_ts=100)

    db.refresh(user)
    assert user.enabled is False
    assert user.activated is False
    assert pushes == []


@pytest.mark.asyncio
async def test_concurrent_should_emit_violation_only_one_wins() -> None:
    redis = FakeRedis()

    results = await asyncio.gather(
        should_emit_violation(
            redis,
            user_id=1,
            ip_list=["203.0.113.1", "203.0.113.2"],
            action="disable",
            window_seconds=300,
        ),
        should_emit_violation(
            redis,
            user_id=1,
            ip_list=["203.0.113.2", "203.0.113.1"],
            action="disable",
            window_seconds=300,
        ),
    )

    assert sorted(results) == [False, True]


@pytest.mark.asyncio
async def test_patch_override_endpoint_persists_nullable_fields(
    db: Session,
) -> None:
    user = add_user(db)

    response = await patch_user_iplimit_override(
        user.username,
        IpLimitOverridePatch(
            max_concurrent_ips=8,
            window_seconds=None,
            violation_action="warn",
            ip_allowlist_cidrs="",
        ),
        db,
        object(),
    )

    assert response.max_concurrent_ips == 8
    assert response.window_seconds is None
    assert response.violation_action == "warn"
    assert response.ip_allowlist_cidrs == ""


@pytest.mark.asyncio
async def test_state_endpoint_returns_sql_policy_when_redis_disabled(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = add_user(db)
    add_config(db, max_concurrent_ips=5)
    monkeypatch.setattr(
        "hardening.iplimit.endpoint.is_redis_configured", lambda: False
    )

    response = await get_user_iplimit_state(user.username, db, object())

    assert response.redis_configured is False
    assert response.observed_ips == []
    assert response.config.max_concurrent_ips == 5


@pytest.mark.asyncio
async def test_audit_endpoint_returns_empty_when_redis_disabled(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = add_user(db)
    monkeypatch.setattr(
        "hardening.iplimit.endpoint.is_redis_configured", lambda: False
    )

    response = await get_user_iplimit_audit(user.username, db, object())

    assert response.redis_configured is False
    assert response.events == []


@pytest.mark.asyncio
async def test_clear_disable_endpoint_restores_owned_disable(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = add_user(db)
    user.enabled = False
    user.activated = False
    upsert_disabled_state(
        db,
        user_id=user.id,
        disabled_until=200,
        disabled_at=100,
        previous_enabled=True,
        previous_activated=True,
        reason="iplimit_violation",
    )
    db.commit()
    redis = FakeRedis()
    await set_disabled_until(redis, user.id, 200)
    monkeypatch.setattr(
        "hardening.iplimit.endpoint.is_redis_configured", lambda: True
    )
    monkeypatch.setattr("hardening.iplimit.endpoint.get_redis", lambda: redis)
    monkeypatch.setattr(
        task, "_schedule_user_update", lambda user, remove=False: None
    )

    response = await clear_user_iplimit_disable(user.username, db, object())

    db.refresh(user)
    assert user.enabled is True
    assert user.activated is True
    assert response.disabled_until is None
    assert f"aegis:iplimit:violation:{user.id}" not in redis.strings
