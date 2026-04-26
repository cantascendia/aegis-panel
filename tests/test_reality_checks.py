"""
Tests for hardening/reality/checks/* — the five pure-function checks.

SPEC requirement: each check has ≥3 unit tests covering happy / bad /
edge. We pin score_delta values so the SPEC's scoring table can't
silently drift.

`asn_match` is the only check with I/O (DNS + WHOIS). We monkey-patch
both. No live network calls anywhere in the suite.
"""

from __future__ import annotations

import socket
from typing import Any

import pytest

from hardening.reality.checks import (
    check_asn_match,
    check_port_canonical,
    check_shortid_compliance,
    check_sni_coldness,
    check_timeout_config,
)
from hardening.reality.models import RealityTarget


def _target(**kw: Any) -> RealityTarget:
    defaults: dict[str, Any] = dict(
        host="h",
        sni="example.com",
        port=2053,
        public_key="k",
        short_ids=["aabb"],
        fingerprint="chrome",
        conn_idle=120,
        xver=1,
        spider_x="/x",
        source="db",
    )
    defaults.update(kw)
    return RealityTarget(**defaults)


# --------------------------------------------------------------------------
# sni_coldness
# --------------------------------------------------------------------------


def test_sni_coldness_top100_critical() -> None:
    """www.google.com is rank 2 in the bundled list → critical -30."""
    f = check_sni_coldness(_target(sni="www.google.com"))
    assert f.ok is False
    assert f.severity == "critical"
    assert f.score_delta == -30
    assert f.data["tier"] == "top-100"


def test_sni_coldness_top1000_warning() -> None:
    """quora.com is rank 320 in our bundled list → warning -10."""
    f = check_sni_coldness(_target(sni="quora.com"))
    assert f.ok is False
    assert f.severity == "warning"
    assert f.score_delta == -10
    assert f.data["tier"] == "top-1000"


def test_sni_coldness_unknown_host_info_zero() -> None:
    """Random regional CDN → not in list → 0 score_delta."""
    f = check_sni_coldness(_target(sni="static.naver.net"))
    assert f.ok is True
    assert f.score_delta == 0
    assert f.data["rank"] is None


def test_sni_coldness_normalizes_case_and_trailing_dot() -> None:
    """Loader edge case: SNI may come with mixed case or a trailing dot."""
    f = check_sni_coldness(_target(sni="WWW.GOOGLE.COM."))
    assert f.severity == "critical", "case + trailing dot should normalize"


# --------------------------------------------------------------------------
# asn_match (monkey-patched I/O)
# --------------------------------------------------------------------------


def test_asn_match_same_asn_passes(monkeypatch) -> None:
    from hardening.sni import asn as sni_asn

    sni_asn._cached_lookup.cache_clear()
    monkeypatch.setattr(socket, "gethostbyname", lambda h: "1.2.3.4")

    async def _fake(ip):  # noqa: D401, ARG001
        return sni_asn.ASNInfo(
            asn=14061,
            country="US",
            bgp_prefix="1.2.3.0/24",
            registry="arin",
            allocated="",
            org="DIGITALOCEAN",
        )

    monkeypatch.setattr(sni_asn, "lookup_asn", _fake)

    f = check_asn_match(_target(sni="some.example.com"), vps_asn=14061)
    assert f.ok is True
    assert f.score_delta == 0
    sni_asn._cached_lookup.cache_clear()


def test_asn_match_different_asn_critical(monkeypatch) -> None:
    from hardening.sni import asn as sni_asn

    sni_asn._cached_lookup.cache_clear()
    monkeypatch.setattr(socket, "gethostbyname", lambda h: "1.2.3.4")

    async def _fake(ip):  # noqa: D401, ARG001
        return sni_asn.ASNInfo(
            asn=13335,
            country="US",
            bgp_prefix="1.2.3.0/24",
            registry="arin",
            allocated="",
            org="CLOUDFLARENET",
        )

    monkeypatch.setattr(sni_asn, "lookup_asn", _fake)

    f = check_asn_match(_target(sni="x.cloudflare.com"), vps_asn=14061)
    assert f.ok is False
    assert f.severity == "critical"
    assert f.score_delta == -35
    assert f.data["sni_asn"] == 13335
    assert f.data["vps_asn"] == 14061
    sni_asn._cached_lookup.cache_clear()


def test_asn_match_dns_failure_warning(monkeypatch) -> None:
    def _bad(host):
        raise socket.gaierror("nope")

    monkeypatch.setattr(socket, "gethostbyname", _bad)

    f = check_asn_match(_target(sni="never.example"), vps_asn=14061)
    assert f.severity == "warning"
    assert f.score_delta == -10


# --------------------------------------------------------------------------
# port_canonical
# --------------------------------------------------------------------------


def test_port_canonical_443_critical() -> None:
    f = check_port_canonical(_target(port=443))
    assert f.severity == "critical"
    assert f.score_delta == -15


def test_port_canonical_8443_warning() -> None:
    f = check_port_canonical(_target(port=8443))
    assert f.severity == "warning"
    assert f.score_delta == -5


def test_port_canonical_recommended_zero() -> None:
    for port in (2053, 2083, 2087, 2096):
        f = check_port_canonical(_target(port=port))
        assert f.score_delta == 0
        assert f.data["tier"] == "recommended"


def test_port_canonical_other_high_port_zero() -> None:
    f = check_port_canonical(_target(port=49872))
    assert f.score_delta == 0
    assert f.data["tier"] == "other"


# --------------------------------------------------------------------------
# shortid_compliance
# --------------------------------------------------------------------------


def test_shortid_compliance_empty_list_ok() -> None:
    f = check_shortid_compliance(_target(short_ids=[]))
    assert f.ok is True
    assert f.score_delta == 0


def test_shortid_compliance_normal_set_ok() -> None:
    f = check_shortid_compliance(
        _target(short_ids=["aabb", "ccdd", "eeff", "1234"])
    )
    assert f.ok is True
    assert f.score_delta == 0


def test_shortid_compliance_non_hex_critical() -> None:
    f = check_shortid_compliance(_target(short_ids=["aabb", "ZZ"]))
    assert f.severity == "critical"
    assert f.score_delta == -25
    assert f.data["illegal_count"] == 1


def test_shortid_compliance_too_long_critical() -> None:
    f = check_shortid_compliance(_target(short_ids=["a" * 17]))
    assert f.severity == "critical"


def test_shortid_compliance_all_zeros_critical() -> None:
    f = check_shortid_compliance(_target(short_ids=["0000"]))
    assert f.severity == "critical"
    assert f.score_delta == -25


def test_shortid_compliance_duplicates_critical() -> None:
    f = check_shortid_compliance(_target(short_ids=["aabb", "ccdd", "aabb"]))
    assert f.severity == "critical"
    assert "aabb" in f.data["duplicates"]


def test_shortid_compliance_short_length_warning() -> None:
    """Length < 4 is a warning (low entropy), not critical."""
    f = check_shortid_compliance(_target(short_ids=["aa", "bb"]))
    assert f.severity == "warning"
    assert f.score_delta == -5


def test_shortid_compliance_too_many_warning() -> None:
    # range(1, 11) avoids "0000" which would trip the all-zeros critical
    # check ahead of the count check (worst-case-wins ordering).
    f = check_shortid_compliance(
        _target(short_ids=[f"{i:04x}" for i in range(1, 11)])
    )
    assert f.severity == "warning"


# --------------------------------------------------------------------------
# timeout_config
# --------------------------------------------------------------------------


def test_timeout_config_unset_critical() -> None:
    f = check_timeout_config(_target(conn_idle=None))
    assert f.severity == "critical"
    assert f.score_delta == -15


def test_timeout_config_too_long_critical() -> None:
    f = check_timeout_config(_target(conn_idle=600))
    assert f.severity == "critical"


def test_timeout_config_warning_band() -> None:
    """120 < ci ≤ 300 → warning -5."""
    f = check_timeout_config(_target(conn_idle=240))
    assert f.severity == "warning"
    assert f.score_delta == -5


def test_timeout_config_at_120_is_recommended() -> None:
    f = check_timeout_config(_target(conn_idle=120))
    assert f.ok is True
    assert f.score_delta == 0


def test_timeout_config_at_300_boundary_is_warning() -> None:
    """ci = 300 sits inside the warning band (≤300)."""
    f = check_timeout_config(_target(conn_idle=300))
    assert f.severity == "warning"


def test_timeout_config_at_301_is_critical() -> None:
    f = check_timeout_config(_target(conn_idle=301))
    assert f.severity == "critical"
