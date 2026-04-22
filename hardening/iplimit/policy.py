"""Policy resolution primitives for IP concurrency limits."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ViolationAction = Literal["warn", "disable"]


@dataclass(frozen=True)
class IpLimitPolicy:
    """Effective per-user IP limiter policy."""

    max_concurrent_ips: int = 3
    window_seconds: int = 300
    violation_action: ViolationAction = "warn"
    disable_duration_seconds: int = 3600
