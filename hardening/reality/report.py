"""
JSON + Markdown rendering for the Reality audit report.

Two render functions, each consuming a :class:`Report`:

- :func:`render_json` — schema-stable JSON for machine consumption
  (dashboard / log analyzer / ``--out report.json`` CLI flag).
  Byte-deterministic given fixed ``audited_at``.
- :func:`render_markdown` — human-friendly summary the operator
  reads. Tables + per-target sections + compass-artifact checklist
  cross-reference at the bottom.

The compass checklist at the bottom of the markdown is a maintenance
cue: if a check (sni_coldness / asn_match / port_canonical /
shortid_compliance / timeout_config) shows up as "covered" but is
missing in the report, something silently regressed. Operators can
visually scan that block instead of grepping JSON.
"""

from __future__ import annotations

import json

from hardening.reality.models import Finding, Report

# Compass-artifact 五件套 -> check name mapping. Update if SPEC adds
# new checks; this is the human-side traceability matrix.
_COMPASS_CHECKLIST: list[tuple[str, str]] = [
    ("冷门 SNI", "sni_coldness"),
    ("同 ASN", "asn_match"),
    ("非标端口", "port_canonical"),
    ("shortId 合规", "shortid_compliance"),
    ("短 connIdle", "timeout_config"),
]

_GRADE_EMOJI = {"green": "🟢", "yellow": "🟡", "red": "🔴"}


def render_json(report: Report, *, indent: int = 2) -> str:
    """Render the JSON shape per SPEC v1.0.

    ``ensure_ascii=False`` so emoji and CJK in evidence strings round-
    trip cleanly. ``sort_keys=False`` because :meth:`Report.to_dict`
    already emits keys in the SPEC's prescribed order.
    """
    return json.dumps(
        report.to_dict(),
        indent=indent,
        ensure_ascii=False,
        sort_keys=False,
    )


def render_markdown(report: Report) -> str:
    """Render a human-readable Markdown summary.

    Sections (per SPEC):
    1. Title + generation metadata
    2. Summary table (total / green / yellow / red / worst score)
    3. Per-target section with check checkmarks + remediation
    4. Compass checklist at the bottom
    """
    lines: list[str] = []

    lines.append("# Reality Audit Report")
    lines.append(f"_Generated: {report.audited_at} | Source: {report.source}_")
    lines.append("")

    s = report.summary
    lines.append("## Summary")
    lines.append("")
    lines.append("| Total | Green | Yellow | Red | Worst |")
    lines.append("|---|---|---|---|---|")
    lines.append(
        f"| {s.total} | {s.green} | {s.yellow} | {s.red} | {s.worst_score} |"
    )
    lines.append("")

    if not report.targets:
        lines.append("_No Reality targets were audited._")
        lines.append("")
    else:
        lines.append("## Per-target")
        lines.append("")
        for t in report.targets:
            emoji = _GRADE_EMOJI.get(t.grade, "?")
            lines.append(
                f"### {t.host} (port {t.port}, score: {t.score} {emoji})"
            )
            lines.append("")
            for f in t.findings:
                lines.extend(_render_finding_lines(f))
            lines.append("")

    lines.append("## Compass 五件套 checklist")
    lines.append("")
    seen_checks = {f.check for t in report.targets for f in t.findings}
    for label, check_name in _COMPASS_CHECKLIST:
        marker = "[x]" if check_name in seen_checks else "[ ]"
        lines.append(f"- {marker} {label} (`{check_name}`)")
    lines.append("")

    return "\n".join(lines)


def _render_finding_lines(f: Finding) -> list[str]:
    """One Finding -> 1-2 markdown bullet lines (with optional fix line)."""
    if f.severity == "info" and f.ok:
        prefix = "✅"
    elif f.severity == "critical":
        prefix = "🚨"
    elif f.severity == "warning":
        prefix = "⚠️"
    else:
        prefix = "•"

    delta_str = f" ({f.score_delta})" if f.score_delta != 0 else ""
    bullets = [f"- {prefix} `{f.check}` — {f.evidence}{delta_str}"]
    if f.remediation:
        bullets.append(f"  - Remediation: {f.remediation}")
    return bullets


__all__ = ["render_json", "render_markdown"]
