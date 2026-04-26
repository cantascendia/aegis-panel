"""
Tests for hardening/reality/report.py — JSON / Markdown rendering.

Two SPEC-locked properties:

- ``render_json`` is **byte-deterministic** given fixed inputs (the
  diff property). We don't compare full output bytes against a
  golden — that's R.2's CLI test territory — but we do verify the
  same input renders identically twice.
- ``render_markdown`` includes the compass-五件套 checklist; running
  through every check name should yield "[x]" markers for any
  check that appeared in any target's findings.
"""

from __future__ import annotations

import json

from hardening.reality.models import (
    Finding,
    Report,
    ReportSummary,
    TargetResult,
)
from hardening.reality.report import render_json, render_markdown


def _make_report(*, with_findings: bool = True) -> Report:
    findings = (
        [
            Finding(
                check="sni_coldness",
                ok=True,
                severity="info",
                score_delta=0,
                evidence="not in top-1k",
                remediation="",
                data={"rank": None},
            ),
            Finding(
                check="port_canonical",
                ok=False,
                severity="critical",
                score_delta=-15,
                evidence="port 443 critical",
                remediation="switch to 2083",
                data={"port": 443, "tier": "critical"},
            ),
        ]
        if with_findings
        else []
    )
    target = TargetResult(
        host="jp1.example.com",
        sni="www.lovelive-anime.jp",
        port=443,
        score=85,
        grade="green",
        findings=findings,
    )
    return Report(
        schema_version="1.0",
        audited_at="2026-04-26T12:00:00Z",
        source="db",
        targets=[target] if findings else [],
        summary=ReportSummary(
            total=1 if findings else 0,
            green=1 if findings else 0,
            yellow=0,
            red=0,
            worst_score=85 if findings else 100,
        ),
    )


def test_render_json_is_byte_deterministic() -> None:
    """Same input → identical bytes. Required for diff-friendly reports."""
    r = _make_report()
    assert render_json(r) == render_json(r)


def test_render_json_round_trips() -> None:
    """Output must be valid JSON parseable back to dict."""
    r = _make_report()
    parsed = json.loads(render_json(r))
    assert parsed["schema_version"] == "1.0"
    assert parsed["audited_at"] == "2026-04-26T12:00:00Z"
    assert parsed["targets"][0]["score"] == 85


def test_render_markdown_has_summary_table() -> None:
    md = render_markdown(_make_report())
    assert "## Summary" in md
    assert "| Total | Green | Yellow | Red | Worst |" in md


def test_render_markdown_lists_compass_checklist_with_seen_checks() -> None:
    """Checks that appeared in findings get [x]; absent checks get [ ]."""
    md = render_markdown(_make_report())
    # We only put sni_coldness + port_canonical in findings, so those
    # two should be checked off; the other three should be unchecked.
    assert "[x] 冷门 SNI (`sni_coldness`)" in md
    assert "[x] 非标端口 (`port_canonical`)" in md
    assert "[ ] 同 ASN (`asn_match`)" in md
    assert "[ ] shortId 合规 (`shortid_compliance`)" in md
    assert "[ ] 短 connIdle (`timeout_config`)" in md


def test_render_markdown_handles_empty_targets() -> None:
    md = render_markdown(_make_report(with_findings=False))
    assert "No Reality targets were audited" in md
    # Compass checklist still rendered even when targets empty
    assert "## Compass 五件套 checklist" in md


def test_render_markdown_emits_remediation_for_critical_findings() -> None:
    md = render_markdown(_make_report())
    assert "Remediation: switch to 2083" in md
