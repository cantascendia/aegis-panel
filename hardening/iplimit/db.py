"""SQLAlchemy models and helpers for IP limiter policy state."""

from __future__ import annotations

from typing import Literal

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.db.base import Base
from hardening.iplimit.allowlist import merge_cidr_texts, parse_cidrs
from hardening.iplimit.policy import IpLimitPolicy, ViolationAction

ActionValue = Literal["warn", "disable"]


class IpLimitConfig(Base):
    """Global default IP limiter policy."""

    __tablename__ = "aegis_iplimit_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    max_concurrent_ips: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3
    )
    window_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, default=300
    )
    violation_action: Mapped[str] = mapped_column(
        String(16), nullable=False, default="warn"
    )
    disable_duration_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3600
    )
    ip_allowlist_cidrs: Mapped[str | None] = mapped_column(Text, nullable=True)


class IpLimitDisabledState(Base):
    """Rows owned by the IP limiter for temporary disable recovery."""

    __tablename__ = "aegis_iplimit_disabled_state"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), primary_key=True
    )
    disabled_until: Mapped[int] = mapped_column(Integer, nullable=False)
    disabled_at: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    previous_activated: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    reason: Mapped[str] = mapped_column(String(64), nullable=False)


class UserIpLimitOverride(Base):
    """Nullable per-user policy override.

    ``NULL`` means inherit the corresponding value from
    :class:`IpLimitConfig`.
    """

    __tablename__ = "aegis_iplimit_override"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), primary_key=True
    )
    max_concurrent_ips: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    window_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    violation_action: Mapped[str | None] = mapped_column(
        String(16), nullable=True
    )
    ip_allowlist_cidrs: Mapped[str | None] = mapped_column(Text, nullable=True)


def get_global_config(db: Session) -> IpLimitConfig | None:
    """Return the first global config row, if present."""

    return db.execute(
        select(IpLimitConfig).order_by(IpLimitConfig.id)
    ).scalar()


def get_user_override(db: Session, user_id: int) -> UserIpLimitOverride | None:
    """Return a user's override row, if present."""

    return db.get(UserIpLimitOverride, user_id)


def resolve_policy(db: Session, user_id: int) -> IpLimitPolicy:
    """Resolve effective policy for one user."""

    base = _policy_from_config(get_global_config(db))
    return _apply_override(base, get_user_override(db, user_id))


def resolve_policies(
    db: Session, user_ids: list[int]
) -> dict[int, IpLimitPolicy]:
    """Resolve effective policies for a batch of users."""

    if not user_ids:
        return {}

    base = _policy_from_config(get_global_config(db))
    overrides = {
        override.user_id: override
        for override in db.execute(
            select(UserIpLimitOverride).where(
                UserIpLimitOverride.user_id.in_(user_ids)
            )
        ).scalars()
    }
    return {
        user_id: _apply_override(base, overrides.get(user_id))
        for user_id in user_ids
    }


def upsert_user_override(
    db: Session,
    user_id: int,
    max_concurrent_ips: int | None,
    window_seconds: int | None,
    violation_action: ActionValue | None,
    ip_allowlist_cidrs: str | None = None,
) -> UserIpLimitOverride:
    """Create or replace a user's nullable override fields."""

    if ip_allowlist_cidrs is not None:
        parse_cidrs(ip_allowlist_cidrs)

    override = get_user_override(db, user_id)
    if override is None:
        override = UserIpLimitOverride(user_id=user_id)
        db.add(override)

    override.max_concurrent_ips = max_concurrent_ips
    override.window_seconds = window_seconds
    override.violation_action = violation_action
    override.ip_allowlist_cidrs = ip_allowlist_cidrs
    db.commit()
    db.refresh(override)
    return override


def get_disabled_state(
    db: Session, user_id: int
) -> IpLimitDisabledState | None:
    return db.get(IpLimitDisabledState, user_id)


def list_disabled_states(db: Session) -> list[IpLimitDisabledState]:
    return list(db.execute(select(IpLimitDisabledState)).scalars())


def upsert_disabled_state(
    db: Session,
    *,
    user_id: int,
    disabled_until: int,
    disabled_at: int,
    previous_enabled: bool,
    previous_activated: bool,
    reason: str,
) -> IpLimitDisabledState:
    state = get_disabled_state(db, user_id)
    if state is None:
        state = IpLimitDisabledState(user_id=user_id)
        db.add(state)

    state.disabled_until = disabled_until
    state.disabled_at = disabled_at
    state.previous_enabled = previous_enabled
    state.previous_activated = previous_activated
    state.reason = reason
    return state


def clear_disabled_state(db: Session, user_id: int) -> None:
    state = get_disabled_state(db, user_id)
    if state is not None:
        db.delete(state)


def _policy_from_config(config: IpLimitConfig | None) -> IpLimitPolicy:
    default = IpLimitPolicy()
    if config is None:
        return default
    return IpLimitPolicy(
        max_concurrent_ips=config.max_concurrent_ips,
        window_seconds=config.window_seconds,
        violation_action=_normalize_action(config.violation_action),
        disable_duration_seconds=config.disable_duration_seconds,
        ip_allowlist_cidrs=config.ip_allowlist_cidrs or "",
    )


def _apply_override(
    policy: IpLimitPolicy, override: UserIpLimitOverride | None
) -> IpLimitPolicy:
    if override is None:
        return policy
    return IpLimitPolicy(
        max_concurrent_ips=(
            override.max_concurrent_ips
            if override.max_concurrent_ips is not None
            else policy.max_concurrent_ips
        ),
        window_seconds=(
            override.window_seconds
            if override.window_seconds is not None
            else policy.window_seconds
        ),
        violation_action=_normalize_action(
            override.violation_action
            if override.violation_action is not None
            else policy.violation_action
        ),
        disable_duration_seconds=policy.disable_duration_seconds,
        ip_allowlist_cidrs=merge_cidr_texts(
            policy.ip_allowlist_cidrs, override.ip_allowlist_cidrs
        ),
    )


def _normalize_action(value: str) -> ViolationAction:
    if value == "disable":
        return "disable"
    return "warn"
