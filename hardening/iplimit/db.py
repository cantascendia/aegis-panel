"""SQLAlchemy models and helpers for IP limiter policy state."""

from __future__ import annotations

from typing import Literal

from sqlalchemy import ForeignKey, Integer, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.db.base import Base
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

    base = get_global_config(db)
    policy = IpLimitPolicy(
        max_concurrent_ips=(
            base.max_concurrent_ips
            if base
            else IpLimitPolicy().max_concurrent_ips
        ),
        window_seconds=(
            base.window_seconds if base else IpLimitPolicy().window_seconds
        ),
        violation_action=_normalize_action(
            base.violation_action if base else IpLimitPolicy().violation_action
        ),
        disable_duration_seconds=(
            base.disable_duration_seconds
            if base
            else IpLimitPolicy().disable_duration_seconds
        ),
    )

    override = get_user_override(db, user_id)
    if not override:
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
    )


def upsert_user_override(
    db: Session,
    user_id: int,
    max_concurrent_ips: int | None,
    window_seconds: int | None,
    violation_action: ActionValue | None,
) -> UserIpLimitOverride:
    """Create or replace a user's nullable override fields."""

    override = get_user_override(db, user_id)
    if override is None:
        override = UserIpLimitOverride(user_id=user_id)
        db.add(override)

    override.max_concurrent_ips = max_concurrent_ips
    override.window_seconds = window_seconds
    override.violation_action = violation_action
    db.commit()
    db.refresh(override)
    return override


def _normalize_action(value: str) -> ViolationAction:
    if value == "disable":
        return "disable"
    return "warn"
