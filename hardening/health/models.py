"""Dataclasses for the health endpoint payloads.

Frozen + slots for the same reasons as ``hardening/reality/models.py``:
small payloads, no mutation after construction, low overhead. The
``to_dict`` helpers shape the JSON response so the endpoint module
doesn't sprinkle dict-construction logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

# A subsystem is one of these statuses. Order matters for severity:
# "ok" is normal; "degraded" is "works but something off" (e.g.
# scheduler installed but TRC20 disabled by config); "down" is "this
# subsystem cannot do its job" (e.g. DB unreachable).
HealthStatus = Literal["ok", "degraded", "down"]


@dataclass(frozen=True, slots=True)
class SubsystemHealth:
    """Per-subsystem probe outcome.

    ``name`` is a stable identifier suitable for Prometheus labels
    (lowercase, no spaces). ``status`` is the tri-state above.
    ``message`` is operator-facing detail — should fit one line.
    ``details`` is free-form structured data the operator's monitoring
    system can pivot on (key-value pairs only, no nested complexity).
    """

    name: str
    status: HealthStatus
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "details": dict(self.details),
        }


@dataclass(frozen=True, slots=True)
class HealthReport:
    """Top-level health envelope returned by ``/api/aegis/health/extended``.

    ``status`` is the worst status across subsystems: "down" if any
    subsystem is down, else "degraded" if any is degraded, else "ok".
    Operators can alert on the top-level status without parsing
    individual rows.

    ``version`` reflects the deployed panel version (read from the
    package metadata at startup). ``uptime_seconds`` is the wall clock
    since the FastAPI process began handling requests — useful for
    spotting unexpected restarts.
    """

    status: HealthStatus
    version: str
    uptime_seconds: int
    subsystems: list[SubsystemHealth]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "version": self.version,
            "uptime_seconds": self.uptime_seconds,
            "subsystems": [s.to_dict() for s in self.subsystems],
        }


def aggregate_status(subsystems: list[SubsystemHealth]) -> HealthStatus:
    """Worst-of aggregation. Empty list → "ok" (nothing to be unhealthy)."""
    if any(s.status == "down" for s in subsystems):
        return "down"
    if any(s.status == "degraded" for s in subsystems):
        return "degraded"
    return "ok"


__all__ = [
    "HealthReport",
    "HealthStatus",
    "SubsystemHealth",
    "aggregate_status",
]
