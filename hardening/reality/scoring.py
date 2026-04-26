"""
Per-target score aggregation and grade mapping.

Pure functions, no I/O. Inputs are :class:`Finding` lists from the
checks layer; outputs are int score + grade label. Score baseline is
100; deltas (always ≤ 0) sum down. Grade thresholds match the
SPEC-locked CLI exit codes (≥70 green / 60–69 yellow / <60 red).
"""

from __future__ import annotations

from typing import Literal

from hardening.reality.models import Finding

_BASELINE = 100
_FLOOR = 0

# SPEC-locked grade boundaries. The CLI's exit-code contract matches:
# green → 0, yellow → 1, red → 2.
_GREEN_MIN = 70
_YELLOW_MIN = 60


def score_target(findings: list[Finding]) -> int:
    """Sum score deltas onto the 100-point baseline, floored at 0.

    ``Finding.score_delta`` is non-positive by contract. We don't
    enforce that here (checks are the contract owners), but the
    floor prevents a buggy check returning a positive delta from
    inflating the score above 100 in some pathological combination —
    flooring at the baseline preserves the upper bound too.
    """
    total = _BASELINE + sum(f.score_delta for f in findings)
    if total < _FLOOR:
        return _FLOOR
    if total > _BASELINE:
        return _BASELINE
    return total


def grade_for(score: int) -> Literal["green", "yellow", "red"]:
    """Map a 0-100 score to a coarse grade label.

    Boundaries match SPEC and the CLI exit-code contract. Inclusive
    on both ends of the yellow band so e.g. 70 is green and 60 is
    yellow.
    """
    if score >= _GREEN_MIN:
        return "green"
    if score >= _YELLOW_MIN:
        return "yellow"
    return "red"


def grade_to_exit_code(grade: Literal["green", "yellow", "red"]) -> int:
    """CLI exit-code contract: 0 green / 1 yellow / 2 red."""
    return {"green": 0, "yellow": 1, "red": 2}[grade]


__all__ = [
    "grade_for",
    "grade_to_exit_code",
    "score_target",
]
