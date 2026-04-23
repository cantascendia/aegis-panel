"""FastAPI endpoints for the IP limiter dashboard surface."""

from __future__ import annotations

import time
from typing import Annotated, Literal

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel, Field

from app.cache.redis import get_redis, is_redis_configured
from app.db import crud
from app.dependencies import DBDep, SudoAdminDep
from hardening.iplimit.config import IPLIMIT_AUDIT_LIMIT
from hardening.iplimit.db import (
    get_disabled_state,
    get_user_override,
    resolve_policy,
    upsert_user_override,
)
from hardening.iplimit.store import (
    get_disabled_until,
    get_observed_ips,
    read_audit_events,
)
from hardening.iplimit.task import clear_iplimit_disable

router = APIRouter(prefix="/api/users", tags=["IP Limit"])


class IpLimitConfigResponse(BaseModel):
    max_concurrent_ips: int
    window_seconds: int
    violation_action: Literal["warn", "disable"]
    disable_duration_seconds: int


class IpLimitOverrideResponse(BaseModel):
    max_concurrent_ips: int | None
    window_seconds: int | None
    violation_action: Literal["warn", "disable"] | None


class IpLimitOwnedDisableResponse(BaseModel):
    disabled_at: int
    disabled_until: int
    reason: str
    can_clear: bool


class IpLimitStateResponse(BaseModel):
    username: str
    redis_configured: bool
    observed_ips: list[str]
    observed_count: int
    disabled_until: int | None
    owned_disable: IpLimitOwnedDisableResponse | None
    config: IpLimitConfigResponse
    override: IpLimitOverrideResponse | None


class IpLimitOverridePatch(BaseModel):
    max_concurrent_ips: int | None = Field(None, ge=1, le=128)
    window_seconds: int | None = Field(None, ge=30, le=86400)
    violation_action: Literal["warn", "disable"] | None = None


class IpLimitAuditEventResponse(BaseModel):
    user_id: int
    username: str
    ip_list: list[str]
    count: int
    action: Literal["warn", "disable"]
    ts: int


class IpLimitAuditResponse(BaseModel):
    username: str
    redis_configured: bool
    events: list[IpLimitAuditEventResponse]


@router.get("/{username}/iplimit", response_model=IpLimitStateResponse)
async def get_user_iplimit_state(
    username: str, db: DBDep, admin: SudoAdminDep
) -> IpLimitStateResponse:
    _ = admin
    user = _get_user_or_404(db, username)
    policy = resolve_policy(db, user.id)
    override = get_user_override(db, user.id)

    observed_ips: list[str] = []
    disabled_until: int | None = None
    redis_configured = is_redis_configured()
    if redis_configured:
        redis = get_redis()
        now_ts = int(time.time())
        observed_ips = await get_observed_ips(
            redis,
            user.id,
            now_ts=now_ts,
            window_seconds=policy.window_seconds,
        )
        disabled_until = await get_disabled_until(redis, user.id)
    state = get_disabled_state(db, user.id)
    if disabled_until is None and state is not None:
        disabled_until = state.disabled_until

    return IpLimitStateResponse(
        username=user.username,
        redis_configured=redis_configured,
        observed_ips=observed_ips,
        observed_count=len(observed_ips),
        disabled_until=disabled_until,
        owned_disable=(
            IpLimitOwnedDisableResponse(
                disabled_at=state.disabled_at,
                disabled_until=state.disabled_until,
                reason=state.reason,
                can_clear=True,
            )
            if state
            else None
        ),
        config=IpLimitConfigResponse(**policy.__dict__),
        override=(
            IpLimitOverrideResponse(
                max_concurrent_ips=override.max_concurrent_ips,
                window_seconds=override.window_seconds,
                violation_action=override.violation_action,
            )
            if override
            else None
        ),
    )


@router.patch(
    "/{username}/iplimit/override",
    response_model=IpLimitOverrideResponse,
)
async def patch_user_iplimit_override(
    username: str,
    body: Annotated[IpLimitOverridePatch, Body()],
    db: DBDep,
    admin: SudoAdminDep,
) -> IpLimitOverrideResponse:
    _ = admin
    user = _get_user_or_404(db, username)
    override = upsert_user_override(
        db,
        user.id,
        max_concurrent_ips=body.max_concurrent_ips,
        window_seconds=body.window_seconds,
        violation_action=body.violation_action,
    )
    return IpLimitOverrideResponse(
        max_concurrent_ips=override.max_concurrent_ips,
        window_seconds=override.window_seconds,
        violation_action=override.violation_action,
    )


@router.delete(
    "/{username}/iplimit/disable", response_model=IpLimitStateResponse
)
async def clear_user_iplimit_disable(
    username: str, db: DBDep, admin: SudoAdminDep
) -> IpLimitStateResponse:
    _ = admin
    user = _get_user_or_404(db, username)
    redis = get_redis() if is_redis_configured() else None
    await clear_iplimit_disable(db, redis, user, now_ts=int(time.time()))
    return await get_user_iplimit_state(username, db, admin)


@router.get("/{username}/iplimit/audit", response_model=IpLimitAuditResponse)
async def get_user_iplimit_audit(
    username: str, db: DBDep, admin: SudoAdminDep
) -> IpLimitAuditResponse:
    _ = admin
    user = _get_user_or_404(db, username)
    redis_configured = is_redis_configured()
    events: list[IpLimitAuditEventResponse] = []
    if redis_configured:
        redis = get_redis()
        events = [
            IpLimitAuditEventResponse(**event.__dict__)
            for event in await read_audit_events(
                redis, user.id, limit=IPLIMIT_AUDIT_LIMIT
            )
        ]
    return IpLimitAuditResponse(
        username=user.username,
        redis_configured=redis_configured,
        events=events,
    )


def _get_user_or_404(db: DBDep, username: str):
    user = crud.get_user(db, username)
    if not user or user.removed:
        raise HTTPException(status_code=404, detail="User not found")
    return user
