"""
Reality 配置审计器(R.1 core).

差异化 #2 / 部分,差异化 #3 前置(健康度仪表盘的 read 层会复用
本模块的输出 schema)。

Public API for R.1 (R.2 cli + R.3 endpoint land in follow-up PRs):

- :class:`RealityTarget` / :class:`Finding` / :class:`TargetResult`
  / :class:`Report` / :class:`ReportSummary` — dataclasses
- :mod:`hardening.reality.checks` — five pure-function checks
- :func:`hardening.reality.scoring.score_target` — aggregation
- :func:`hardening.reality.scoring.grade_for` — grade mapping
- :func:`hardening.reality.report.render_json` /
  :func:`hardening.reality.report.render_markdown` — output renderers

Pipeline (composed in R.2 cli + R.3 endpoint):

    target = loader.from_db_row(row) | loader.from_xray_config(j)
    findings = [check_*(target, ...) for check_* in CHECKS]
    score = score_target(findings)
    grade = grade_for(score)
    target_result = TargetResult(target.host, target.sni, target.port,
                                 score, grade, findings)
    # ...repeat for each target...
    report = Report(schema_version="1.0", audited_at=..., ...)
    print(render_json(report))
    sys.stderr.write(render_markdown(report))
    sys.exit(grade_to_exit_code(grade))
"""

from __future__ import annotations

from hardening.reality.models import (
    Finding,
    RealityTarget,
    Report,
    ReportSummary,
    TargetResult,
)
from hardening.reality.report import render_json, render_markdown
from hardening.reality.scoring import (
    grade_for,
    grade_to_exit_code,
    score_target,
)

__all__ = [
    "Finding",
    "RealityTarget",
    "Report",
    "ReportSummary",
    "TargetResult",
    "grade_for",
    "grade_to_exit_code",
    "render_json",
    "render_markdown",
    "score_target",
]
