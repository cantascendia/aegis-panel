"""
Tests for hardening/reality/cli.py — CLI contract + golden fixtures.

The two key contracts the SPEC nails down:

1. **Exit codes** — 0 worst-grade-green, 1 yellow, 2 red.
2. **JSON output is byte-deterministic** given a fixed `--audited-at`
   (the hidden test-only arg). We freeze a known timestamp and assert
   the output schema + content shape against the fixture.

Tests use ``--config`` mode exclusively (zero DB dep). The two
fixtures `tests/fixtures/reality_{perfect,broken}.json` exercise
the full pipeline: loader → checks → scoring → report → CLI.
"""

from __future__ import annotations

import json
import socket
from pathlib import Path
from typing import Any

import pytest

from hardening.reality.cli import main

_FIXTURES_DIR = Path(__file__).parent / "fixtures"
_PERFECT = str(_FIXTURES_DIR / "reality_perfect.json")
_BROKEN = str(_FIXTURES_DIR / "reality_broken.json")


def _patch_asn_lookup_to_match(monkeypatch, vps_asn: int) -> None:
    """Make asn_match see "same ASN" without hitting the network.

    Patches both DNS and ``hardening.sni.asn.lookup_asn`` so the
    asn_match check short-circuits to ok=True with the supplied ASN.
    """
    from hardening.sni import asn as sni_asn

    sni_asn._cached_lookup.cache_clear()
    monkeypatch.setattr(socket, "gethostbyname", lambda h: "1.2.3.4")

    async def _fake(ip: str) -> Any:
        return sni_asn.ASNInfo(
            asn=vps_asn,
            country="JP",
            bgp_prefix="1.2.3.0/24",
            registry="apnic",
            allocated="",
            org="NAVER",
        )

    monkeypatch.setattr(sni_asn, "lookup_asn", _fake)


# Pytest's built-in ``capsys`` fixture is the canonical way to capture
# CLI stdout/stderr. We tried hand-rolling a StringIO swap and learned
# pytest's capture machinery sits above print() in the call chain —
# our monkeypatch ran but pytest's intercept got the bytes first.
# capsys.readouterr() returns the already-captured output and is the
# only reliable approach.


# --------------------------------------------------------------------------
# Golden fixture: perfect config
# --------------------------------------------------------------------------


def test_cli_perfect_config_exits_zero(monkeypatch, capsys) -> None:
    _patch_asn_lookup_to_match(monkeypatch, vps_asn=23576)  # NAVER ASN

    rc = main(
        [
            "--config",
            _PERFECT,
            "--vps-asn",
            "23576",
            "--format",
            "json",
            "--audited-at",
            "2026-04-26T00:00:00Z",
        ]
    )
    assert rc == 0  # green grade

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["schema_version"] == "1.0"
    assert data["audited_at"] == "2026-04-26T00:00:00Z"
    assert data["source"] == "config"
    assert len(data["targets"]) == 1
    t = data["targets"][0]
    assert (
        t["score"] >= 90
    ), f"perfect config should score ≥90, got {t['score']}"
    assert t["grade"] == "green"


def test_cli_perfect_config_byte_deterministic(monkeypatch, capsys) -> None:
    """Same input → identical bytes. Required for diff-friendly reports."""
    _patch_asn_lookup_to_match(monkeypatch, vps_asn=23576)

    def _run() -> str:
        main(
            [
                "--config",
                _PERFECT,
                "--vps-asn",
                "23576",
                "--format",
                "json",
                "--audited-at",
                "2026-04-26T00:00:00Z",
            ]
        )
        return capsys.readouterr().out

    a = _run()
    b = _run()
    assert a == b


# --------------------------------------------------------------------------
# Golden fixture: broken config
# --------------------------------------------------------------------------


def test_cli_broken_config_exits_red(capsys) -> None:
    rc = main(
        [
            "--config",
            _BROKEN,
            # No --vps-asn → asn_match warning (-10) layered on top of the
            # other criticals. Score drops further.
            "--format",
            "json",
            "--audited-at",
            "2026-04-26T00:00:00Z",
        ]
    )
    assert rc == 2  # red grade

    data = json.loads(capsys.readouterr().out)
    t = data["targets"][0]
    assert t["score"] < 60, f"broken config should score <60, got {t['score']}"
    assert t["grade"] == "red"


# --------------------------------------------------------------------------
# CLI flag handling
# --------------------------------------------------------------------------


def test_cli_format_md_only_writes_to_stderr(capsys) -> None:
    rc = main(
        [
            "--config",
            _PERFECT,
            "--format",
            "md",
            "--audited-at",
            "2026-04-26T00:00:00Z",
        ]
    )
    # Without --vps-asn the perfect config drops to yellow due to asn_match
    # warning. That's exit code 1 — confirms graceful degradation.
    assert rc in (0, 1)
    captured = capsys.readouterr()
    assert captured.out == ""  # no JSON
    assert "# Reality Audit Report" in captured.err


def test_cli_format_both_writes_both_streams(capsys) -> None:
    main(
        [
            "--config",
            _PERFECT,
            "--format",
            "both",
            "--audited-at",
            "2026-04-26T00:00:00Z",
        ]
    )
    captured = capsys.readouterr()
    assert "schema_version" in captured.out
    assert "# Reality Audit Report" in captured.err


def test_cli_out_dir_writes_both_files(tmp_path, capsys) -> None:
    out_dir = tmp_path / "report"
    rc = main(
        [
            "--config",
            _PERFECT,
            "--format",
            "json",
            "--out",
            str(out_dir),
            "--audited-at",
            "2026-04-26T00:00:00Z",
        ]
    )
    capsys.readouterr()  # drain
    # rc shape varies by --vps-asn presence; just check non-2 (not red).
    assert rc != 2
    assert (out_dir / "report.json").exists()
    assert (out_dir / "report.md").exists()
    parsed = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
    assert parsed["schema_version"] == "1.0"


def test_cli_requires_source_arg() -> None:
    """Either --config or --from-db must be provided."""
    with pytest.raises(SystemExit):
        main([])


def test_cli_summary_counts_match_targets(capsys) -> None:
    main(
        [
            "--config",
            _BROKEN,
            "--format",
            "json",
            "--audited-at",
            "2026-04-26T00:00:00Z",
        ]
    )
    data = json.loads(capsys.readouterr().out)
    s = data["summary"]
    assert s["total"] == 1
    assert s["red"] == 1
    assert s["green"] + s["yellow"] == 0
