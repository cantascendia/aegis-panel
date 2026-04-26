"""
Reality audit CLI (R.2).

Wires loader → checks → scoring → report into a single command-line
entry point. Two source modes:

    python -m hardening.reality.cli --config /path/to/xray.json [--vps-asn N]
    python -m hardening.reality.cli --from-db                    [--vps-asn N]

The ``--from-db`` path only works when the panel package is
importable (i.e. you're running this from the panel host's venv).
``--config`` is the offline / portable mode — pass any xray config
JSON file.

Output:

- stdout: JSON report (machine-readable; pipe to jq / dashboard)
- stderr: human-readable Markdown summary (operator visual)
- exit code: 0 (worst grade green) / 1 (yellow) / 2 (red)
- ``--out <dir>``: also writes ``report.json`` + ``report.md`` to the
  directory; doesn't replace stdout/stderr output

``--vps-asn`` is required when any check needs ASN comparison
(``asn_match``). If omitted, ``asn_match`` falls back to a "warning,
unknown ASN" finding rather than crashing — operator can still see
the rest of the audit.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from hardening.reality.checks import (
    check_port_canonical,
    check_shortid_compliance,
    check_sni_coldness,
    check_timeout_config,
)
from hardening.reality.loader import from_xray_config
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

_SCHEMA_VERSION = "1.0"


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    targets = _load_targets(args)

    audited_at = args.audited_at or datetime.now(UTC).isoformat(
        timespec="seconds"
    ).replace("+00:00", "Z")
    report = _audit_targets(
        targets,
        vps_asn=args.vps_asn,
        audited_at=audited_at,
        source=args.source,
    )

    json_text = render_json(report)
    md_text = render_markdown(report)

    if args.format in ("json", "both"):
        print(json_text)
    if args.format in ("md", "both"):
        print(md_text, file=sys.stderr)

    if args.out:
        out_dir = Path(args.out)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "report.json").write_text(
            json_text + "\n", encoding="utf-8"
        )
        (out_dir / "report.md").write_text(md_text + "\n", encoding="utf-8")

    worst_grade = _worst_grade(report)
    return grade_to_exit_code(worst_grade)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m hardening.reality.cli",
        description="Audit Reality configuration against the compass-五件套 checklist.",
    )
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument(
        "--config",
        type=Path,
        help="Path to an xray server config JSON file.",
    )
    src.add_argument(
        "--from-db",
        action="store_true",
        help=(
            "Read InboundHost rows from the panel DB (requires panel "
            "venv + SQLALCHEMY_DATABASE_URL configured)."
        ),
    )
    parser.add_argument(
        "--vps-asn",
        type=int,
        default=None,
        help=(
            "VPS egress ASN. Enables the asn_match check. "
            "Omit to skip ASN matching (asn_match returns a warning)."
        ),
    )
    parser.add_argument(
        "--format",
        choices=("json", "md", "both"),
        default="both",
        help="Output format. Default: both (JSON to stdout, MD to stderr).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Optional directory for report.json + report.md side files.",
    )
    parser.add_argument(
        "--audited-at",
        default=None,
        help=argparse.SUPPRESS,  # test-only; injects a fixed timestamp
    )
    return parser


def _load_targets(args: argparse.Namespace) -> list[RealityTarget]:
    if args.config:
        config = json.loads(Path(args.config).read_text(encoding="utf-8"))
        # Tag the source onto args so the report knows where it came from.
        args.source = "config"
        return from_xray_config(config)

    # --from-db path: import lazily so users running --config don't pay
    # the cost of importing app.* (and hitting the DB env requirement).
    args.source = "db"
    from app.db import GetDB
    from app.db.models import InboundHost
    from hardening.reality.loader import from_db_rows

    with GetDB() as db:
        rows = list(db.query(InboundHost).all())
        return from_db_rows(rows)


def _audit_targets(
    targets: list[RealityTarget],
    *,
    vps_asn: int | None,
    audited_at: str,
    source: str,
) -> Report:
    target_results: list[TargetResult] = []
    for target in targets:
        findings: list[Finding] = [
            check_sni_coldness(target),
            check_port_canonical(target),
            check_shortid_compliance(target),
            check_timeout_config(target),
            _maybe_asn_check(target, vps_asn),
        ]
        score = score_target(findings)
        grade = grade_for(score)
        target_results.append(
            TargetResult(
                host=target.host,
                sni=target.sni,
                port=target.port,
                score=score,
                grade=grade,
                findings=findings,
            )
        )

    summary = _summarize(target_results)
    return Report(
        schema_version=_SCHEMA_VERSION,
        audited_at=audited_at,
        source=source,  # type: ignore[arg-type]
        targets=target_results,
        summary=summary,
    )


def _maybe_asn_check(target: RealityTarget, vps_asn: int | None) -> Finding:
    """Wrap asn_match so missing --vps-asn yields a clean warning."""
    if vps_asn is None:
        return Finding(
            check="asn_match",
            ok=False,
            severity="warning",
            score_delta=-10,
            evidence="VPS ASN not provided to CLI (--vps-asn omitted)",
            remediation=(
                "Re-run with --vps-asn <N>. Find your VPS's ASN via "
                "`whois <vps-egress-ip>` or by querying Team Cymru."
            ),
            data={"vps_asn": None},
        )
    # Real ASN check uses async DNS+WHOIS; wrap with asyncio.run.
    from hardening.reality.checks.asn_match import check_asn_match

    return _run_sync(lambda: check_asn_match(target, vps_asn))


def _run_sync(fn: Any) -> Any:
    """Invoke a function that may itself call asyncio.run.

    The asn_match check uses asyncio.run internally for the WHOIS path.
    Calling that directly from a sync entry point is fine; this helper
    just centralizes the call site.
    """
    return fn()


def _summarize(target_results: list[TargetResult]) -> ReportSummary:
    g = sum(1 for t in target_results if t.grade == "green")
    y = sum(1 for t in target_results if t.grade == "yellow")
    r = sum(1 for t in target_results if t.grade == "red")
    worst = min((t.score for t in target_results), default=100)
    return ReportSummary(
        total=len(target_results),
        green=g,
        yellow=y,
        red=r,
        worst_score=worst,
    )


def _worst_grade(report: Report) -> str:
    """Pick the worst grade across all targets for the CLI exit code.

    With no targets, exit 0 (vacuously green) — letting an empty
    config look "fine" is friendlier than crashing the CLI.
    """
    if not report.targets:
        return "green"
    if any(t.grade == "red" for t in report.targets):
        return "red"
    if any(t.grade == "yellow" for t in report.targets):
        return "yellow"
    return "green"


if __name__ == "__main__":
    raise SystemExit(main())


# `asyncio` is imported but only referenced by the asn_match check
# transitively. Keep it explicit so static analysis can't strip the
# import — losing it would make a future asyncio.run call land in a
# fresh event-loop policy.
_ = asyncio
