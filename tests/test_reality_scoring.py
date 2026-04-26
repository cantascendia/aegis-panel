"""
Tests for hardening/reality/scoring.py — score arithmetic + grade mapping.

The boundaries are SPEC-locked (CLI exit code contract depends on them):
≥70 = green / 60-69 = yellow / <60 = red. Pinning each transition.
"""

from __future__ import annotations

from hardening.reality.models import Finding
from hardening.reality.scoring import (
    grade_for,
    grade_to_exit_code,
    score_target,
)


def _f(delta: int) -> Finding:
    return Finding(
        check="x",
        ok=delta == 0,
        severity="info" if delta == 0 else "warning",
        score_delta=delta,
        evidence="",
        remediation="",
    )


def test_score_baseline_when_no_findings() -> None:
    assert score_target([]) == 100


def test_score_subtracts_negative_deltas() -> None:
    assert score_target([_f(-30), _f(-15)]) == 55


def test_score_floors_at_zero() -> None:
    assert score_target([_f(-50), _f(-50), _f(-50)]) == 0


def test_score_caps_at_baseline_against_buggy_positive_delta() -> None:
    """Buggy check returning positive delta must not push past 100."""
    assert score_target([_f(+50)]) == 100


def test_grade_green_at_70() -> None:
    """SPEC: ≥70 is green; 70 itself sits on the green side."""
    assert grade_for(70) == "green"
    assert grade_for(100) == "green"


def test_grade_yellow_at_60_and_69() -> None:
    """60-69 inclusive is yellow."""
    assert grade_for(69) == "yellow"
    assert grade_for(60) == "yellow"


def test_grade_red_below_60() -> None:
    assert grade_for(59) == "red"
    assert grade_for(0) == "red"


def test_grade_to_exit_code_matches_cli_contract() -> None:
    """CLI: green→0, yellow→1, red→2."""
    assert grade_to_exit_code("green") == 0
    assert grade_to_exit_code("yellow") == 1
    assert grade_to_exit_code("red") == 2
