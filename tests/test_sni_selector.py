"""
Integration-ish tests for the SNI selector orchestrator + scoring.

We mock every network touchpoint:
- ASN lookup (vps + per-seed via check_same_asn)
- HTTP HEAD for redirect check
- TLS probe

Then call `select_candidates` end-to-end with a fake seed list.
Also a golden-schema test so the JSON output format can't drift
silently.
"""

from __future__ import annotations

import json
import socket
from typing import Any

import pytest

from hardening.sni import asn as asn_module
from hardening.sni import checks as checks_module
from hardening.sni import selector as selector_module
from hardening.sni.asn import ASNInfo
from hardening.sni.candidate import CheckResults
from hardening.sni.checks import TLSProbe
from hardening.sni.scoring import score_candidate

# --------------------------------------------------------------------------
# Scoring
# --------------------------------------------------------------------------


def _all_pass_checks(**overrides: Any) -> CheckResults:
    defaults: dict[str, Any] = dict(
        blacklist_ok=True,
        no_redirect=True,
        same_asn=True,
        tls13_ok=True,
        alpn_h2_ok=True,
        x25519_ok=True,
        ocsp_stapling=False,
        rtt_ms=50,
    )
    defaults.update(overrides)
    return CheckResults(**defaults)


def test_score_zero_when_any_hard_fail() -> None:
    r = _all_pass_checks(x25519_ok=False)
    assert score_candidate(r) == 0.0


def test_score_base_is_1_0_on_all_pass() -> None:
    r = _all_pass_checks()
    assert score_candidate(r) == 1.0


def test_score_bonus_same_datacenter() -> None:
    r = _all_pass_checks()
    assert score_candidate(r, same_datacenter=True) == 1.1


def test_score_bonus_ocsp_stapling() -> None:
    r = _all_pass_checks(ocsp_stapling=True)
    assert score_candidate(r) == 1.1


def test_score_penalty_high_rtt() -> None:
    r = _all_pass_checks(rtt_ms=500)
    assert score_candidate(r) == 0.8


def test_score_combined_bonus_and_penalty() -> None:
    # Same-DC bonus +0.1, OCSP +0.1, high-RTT -0.2 => 1.0
    r = _all_pass_checks(ocsp_stapling=True, rtt_ms=500)
    assert score_candidate(r, same_datacenter=True) == 1.0


# --------------------------------------------------------------------------
# Orchestrator (select_candidates)
# --------------------------------------------------------------------------


@pytest.fixture
def fake_environment(monkeypatch):
    """Set up a deterministic mock for every network touchpoint."""
    asn_module._cached_lookup.cache_clear()

    async def fake_lookup_asn(ip: str) -> ASNInfo:
        return ASNInfo(
            asn=14061,
            country="US",
            bgp_prefix=f"{ip}/24",
            registry="arin",
            allocated="",
            org="DIGITALOCEAN",
        )

    monkeypatch.setattr(selector_module, "lookup_asn", fake_lookup_asn)
    monkeypatch.setattr(checks_module, "lookup_asn", fake_lookup_asn)

    # gethostbyname -> some IP; the ASN check then returns same ASN
    # via fake_lookup_asn.
    monkeypatch.setattr(socket, "gethostbyname", lambda h: "1.2.3.4")

    # HEAD never redirects.
    from tests.test_sni_checks import _FakeResp, _FakeSession

    session_instance = _FakeSession(_FakeResp(200))

    class _FakeClientSession:
        async def __aenter__(self):
            return session_instance

        async def __aexit__(self, *exc):
            return None

        def head(self, *a, **kw):
            return session_instance.head(*a, **kw)

    monkeypatch.setattr(
        selector_module.aiohttp, "ClientSession", _FakeClientSession
    )

    # TLS probe: return all-pass.
    monkeypatch.setattr(
        checks_module,
        "_probe_tls_sync",
        lambda host, timeout: TLSProbe(
            tls13_ok=True,
            alpn_h2_ok=True,
            x25519_ok=True,
            ocsp_stapling=True,
            rtt_ms=40,
        ),
    )

    # Shrink the seeds to a tiny deterministic list so the test is fast.
    monkeypatch.setattr(
        selector_module,
        "load_seeds",
        lambda region: [
            {"host": "www.microsoft.com", "category": "cdn", "notes": ""},
            {"host": "www.apple.com", "category": "cdn", "notes": ""},
            {"host": "speedtest.net", "category": "banned", "notes": ""},
        ],
    )
    monkeypatch.setattr(
        selector_module,
        "load_blacklist",
        lambda: {"speedtest.net"},
    )
    yield
    asn_module._cached_lookup.cache_clear()


@pytest.mark.asyncio
async def test_select_candidates_happy_path(fake_environment) -> None:
    result = await selector_module.select_candidates(
        vps_ip="1.2.3.4",
        count=5,
        region="auto",
    )
    # The 2 non-blacklisted seeds survived and scored > 0.
    assert len(result.candidates) == 2
    # speedtest.net was blacklist-rejected early.
    assert any(
        r.host == "speedtest.net" and "blacklist" in r.reason
        for r in result.rejected
    )
    # VPS ASN came through from the mock.
    assert result.vps_asn == 14061


@pytest.mark.asyncio
async def test_select_candidates_respects_count_cap(fake_environment) -> None:
    result = await selector_module.select_candidates(
        vps_ip="1.2.3.4",
        count=1,
        region="auto",
    )
    assert len(result.candidates) == 1


@pytest.mark.asyncio
async def test_output_json_schema_golden(fake_environment) -> None:
    """Guard against accidental JSON schema drift.

    If the keys / types change, bump this test intentionally — do NOT
    silently adjust to match the new shape. Consumers (dashboard, CLI
    pipelines) read this schema.
    """
    result = await selector_module.select_candidates(
        vps_ip="1.2.3.4",
        count=2,
        region="auto",
    )
    as_dict = result.to_dict()
    as_json = json.dumps(as_dict)  # must be JSON-serializable end-to-end

    # Top-level shape
    assert set(as_dict.keys()) == {
        "vps_ip",
        "vps_asn",
        "vps_country",
        "probed_at",
        "elapsed_seconds",
        "candidates",
        "rejected",
    }

    # Candidate shape
    assert as_dict["candidates"], "fake env should always produce candidates"
    c = as_dict["candidates"][0]
    assert set(c.keys()) == {"host", "score", "checks", "notes"}
    assert set(c["checks"].keys()) == {
        "blacklist_ok",
        "no_redirect",
        "same_asn",
        "tls13_ok",
        "alpn_h2_ok",
        "x25519_ok",
        "ocsp_stapling",
        "rtt_ms",
    }

    # Rejection shape
    r = as_dict["rejected"][0]
    assert set(r.keys()) == {"host", "reason"}

    # Final sanity: round-trip through JSON.
    reparsed = json.loads(as_json)
    assert reparsed["vps_ip"] == "1.2.3.4"
