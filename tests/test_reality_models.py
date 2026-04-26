"""
Tests for hardening/reality/models.py — dataclass shape + JSON schema.

Schema-stability is a SPEC acceptance criterion ("schema_version not
changing across R.1-R.3, additive only"). The tests here pin the
v1.0 key set so a silent rename / drop in models.py would surface
loud.
"""

from __future__ import annotations

from hardening.reality.models import (
    Finding,
    RealityTarget,
    Report,
    ReportSummary,
    TargetResult,
)


def _sample_target() -> RealityTarget:
    return RealityTarget(
        host="jp1.example.com",
        sni="www.lovelive-anime.jp",
        port=2083,
        public_key="dXg-key-base64-32",
        short_ids=["aabb", "ccdd"],
        fingerprint="chrome",
        conn_idle=120,
        xver=1,
        spider_x="/some/path",
        source="db",
    )


def _sample_finding(check: str = "sni_coldness") -> Finding:
    return Finding(
        check=check,
        ok=True,
        severity="info",
        score_delta=0,
        evidence="cold",
        remediation="",
        data={"rank": None},
    )


def test_realitytarget_is_frozen() -> None:
    """Loader output must be immutable so check functions can't
    accidentally mutate inputs and create cross-target leakage."""
    import dataclasses

    t = _sample_target()
    try:
        t.sni = "new.example.com"  # type: ignore[misc]
    except dataclasses.FrozenInstanceError:
        return
    raise AssertionError("RealityTarget should be frozen=True")


def test_finding_data_default_is_empty_dict_not_shared() -> None:
    """Each Finding gets its own empty dict — no aliasing trap."""
    f1 = Finding(
        check="x",
        ok=True,
        severity="info",
        score_delta=0,
        evidence="",
        remediation="",
    )
    f2 = Finding(
        check="y",
        ok=True,
        severity="info",
        score_delta=0,
        evidence="",
        remediation="",
    )
    assert f1.data == {}
    assert f2.data == {}
    assert f1.data is not f2.data


def test_report_to_dict_emits_v1_0_top_level_keys() -> None:
    """Pin the SPEC v1.0 top-level key set."""
    r = Report(
        schema_version="1.0",
        audited_at="2026-04-26T00:00:00Z",
        source="db",
        targets=[],
        summary=ReportSummary(
            total=0, green=0, yellow=0, red=0, worst_score=100
        ),
    )
    d = r.to_dict()
    assert set(d.keys()) == {
        "schema_version",
        "audited_at",
        "source",
        "targets",
        "summary",
    }


def test_report_to_dict_target_subkeys_match_spec() -> None:
    target = TargetResult(
        host="h1",
        sni="example.com",
        port=2053,
        score=85,
        grade="green",
        findings=[_sample_finding()],
    )
    r = Report(
        schema_version="1.0",
        audited_at="2026-04-26T00:00:00Z",
        source="db",
        targets=[target],
        summary=ReportSummary(
            total=1, green=1, yellow=0, red=0, worst_score=85
        ),
    )
    d = r.to_dict()
    t = d["targets"][0]
    assert set(t.keys()) == {
        "host",
        "sni",
        "port",
        "score",
        "grade",
        "findings",
    }
    f = t["findings"][0]
    assert set(f.keys()) == {
        "check",
        "ok",
        "severity",
        "score_delta",
        "evidence",
        "remediation",
        "data",
    }


def test_report_summary_fields() -> None:
    s = ReportSummary(total=5, green=3, yellow=1, red=1, worst_score=42)
    assert (s.total, s.green, s.yellow, s.red, s.worst_score) == (
        5,
        3,
        1,
        1,
        42,
    )
