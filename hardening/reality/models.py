"""
Dataclasses for the Reality audit pipeline (R.1).

Three layers, each consumed by a separate module:

- :class:`RealityTarget` — what the loader produces. One per InboundHost
  (or one per xray ``inbounds[]`` entry). The audit treats each target
  independently.
- :class:`Finding` — what each check returns. A Reality config is
  scored by aggregating findings across all checks for one target.
- :class:`Report` — the top-level CLI / REST output. Wraps a list of
  per-target results plus a summary roll-up.

Pure dataclasses, ``frozen=True`` where input-only, ``slots=True`` to
keep these cheap to copy in scoring loops.

The shape here is the **published v1.0 schema**. Adding fields = OK
(consumers must tolerate unknown keys per the JSON contract); renaming
or removing fields = schema bump (``schema_version`` 1.x → 2.x). See
``SPEC-reality-audit.md#Output schema``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


@dataclass(frozen=True, slots=True)
class RealityTarget:
    """One Reality endpoint to audit.

    Source-agnostic: the loader (R.2) populates this from either
    panel DB ``InboundHost`` rows or a parsed xray config JSON. The
    ``source`` discriminator survives into the report so an operator
    inspecting findings knows whether DB and config drift.

    Fields with ``None`` mean "loader couldn't read this from the
    source" — checks that depend on a missing field emit a
    ``Finding`` with ``ok=False, severity="warning"`` rather than
    crashing. Distinct from "field present but bad value".
    """

    host: str
    sni: str
    port: int
    public_key: str
    short_ids: list[str]
    fingerprint: str
    conn_idle: int | None
    xver: int | None
    spider_x: str | None
    source: Literal["db", "config"]


@dataclass(frozen=True, slots=True)
class Finding:
    """One audit observation about a single target.

    ``score_delta`` is non-positive: 0 = no penalty, negative = penalty.
    Aggregation in :func:`hardening.reality.scoring.score_target` sums
    deltas onto a 100-point baseline.

    ``data`` is for machine-readable fields the consumer (dashboard,
    log analyzer) might want without parsing the human strings —
    e.g. ``{"asn": 14061, "tranco_rank": 87}``.
    """

    check: str
    ok: bool
    severity: Literal["critical", "warning", "info"]
    score_delta: int
    evidence: str
    remediation: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class TargetResult:
    """One target's scored audit result. Embeds findings list."""

    host: str
    sni: str
    port: int
    score: int
    grade: Literal["green", "yellow", "red"]
    findings: list[Finding]


@dataclass(frozen=True, slots=True)
class ReportSummary:
    """Top-level roll-up over all audited targets."""

    total: int
    green: int
    yellow: int
    red: int
    worst_score: int


@dataclass(frozen=True, slots=True)
class Report:
    """Full audit output. JSON-serializable via :func:`to_dict`."""

    schema_version: str
    audited_at: str  # ISO-8601 UTC; injected by caller for byte-determinism
    source: Literal["db", "config"]
    targets: list[TargetResult]
    summary: ReportSummary

    def to_dict(self) -> dict[str, Any]:
        """Serialize to the published v1.0 JSON schema.

        Manual conversion (rather than ``dataclasses.asdict``) so we
        can guarantee key order — important for the byte-deterministic
        diff property in the SPEC's acceptance criteria.
        """
        return {
            "schema_version": self.schema_version,
            "audited_at": self.audited_at,
            "source": self.source,
            "targets": [
                {
                    "host": t.host,
                    "sni": t.sni,
                    "port": t.port,
                    "score": t.score,
                    "grade": t.grade,
                    "findings": [asdict(f) for f in t.findings],
                }
                for t in self.targets
            ],
            "summary": asdict(self.summary),
        }


__all__ = [
    "Finding",
    "RealityTarget",
    "Report",
    "ReportSummary",
    "TargetResult",
]
