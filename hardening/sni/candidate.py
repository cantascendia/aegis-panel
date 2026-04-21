"""
Dataclasses for the SNI selector output.

Kept in a leaf module with zero non-stdlib imports so the rest of the
package (and tests) can reference these shapes without triggering
network / YAML / aiohttp imports.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class CheckResults:
    """Outcome of the six hard indicators plus optional soft signals.

    Each hard indicator is a ``bool`` (pass/fail). Soft signals are
    captured as-is for scoring; they never fail the candidate.
    """

    blacklist_ok: bool
    no_redirect: bool
    same_asn: bool
    tls13_ok: bool
    alpn_h2_ok: bool
    x25519_ok: bool
    # Soft signals:
    ocsp_stapling: bool = False
    rtt_ms: int | None = None

    @property
    def all_hard_pass(self) -> bool:
        return (
            self.blacklist_ok
            and self.no_redirect
            and self.same_asn
            and self.tls13_ok
            and self.alpn_h2_ok
            and self.x25519_ok
        )


@dataclass(frozen=True)
class Candidate:
    """One SNI candidate after probing."""

    host: str
    score: float
    checks: CheckResults
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # asdict() emits nested CheckResults as a plain dict — good for JSON.
        return d


@dataclass(frozen=True)
class Rejection:
    """A seed host that didn't make the final list, with a human reason."""

    host: str
    reason: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class SelectorResult:
    """Top-level JSON the CLI / API endpoint returns."""

    vps_ip: str
    vps_asn: int | None
    vps_country: str | None
    probed_at: str  # ISO-8601 UTC
    elapsed_seconds: float
    candidates: list[Candidate] = field(default_factory=list)
    rejected: list[Rejection] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "vps_ip": self.vps_ip,
            "vps_asn": self.vps_asn,
            "vps_country": self.vps_country,
            "probed_at": self.probed_at,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "candidates": [c.to_dict() for c in self.candidates],
            "rejected": [r.to_dict() for r in self.rejected],
        }
