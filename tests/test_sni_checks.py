"""
Tests for hardening/sni/checks.py — the six hard indicators.

Each hard indicator has at least one positive and one negative test,
per SPEC acceptance criteria. We never hit the real network:

- check_blacklist is pure; no mocks needed.
- check_no_redirect uses aioresponses via a lightweight fake session.
- check_same_asn monkeypatches socket.gethostbyname + the cached
  ASN lookup.
- probe_tls is tested by monkeypatching _probe_tls_sync (the real
  ssl/socket code lives in _probe_tls_sync; probe_tls itself is
  just a thread-off wrapper, so we test them separately).
"""

from __future__ import annotations

import socket
from contextlib import asynccontextmanager
from typing import Any

import pytest

from hardening.sni import asn as asn_module
from hardening.sni import checks as checks_module
from hardening.sni.candidate import CheckResults
from hardening.sni.checks import (
    TLSProbe,
    _contains_x25519,
    check_blacklist,
    check_no_redirect,
    check_same_asn,
)

# --------------------------------------------------------------------------
# 1. Blacklist
# --------------------------------------------------------------------------


def test_blacklist_rejects_known_bad() -> None:
    assert check_blacklist("speedtest.net", {"speedtest.net"}) is False


def test_blacklist_accepts_unknown_host() -> None:
    assert check_blacklist("www.microsoft.com", {"speedtest.net"}) is True


def test_blacklist_is_exact_match_only() -> None:
    """Subdomain of a blocked host is NOT auto-blocked. See checks.py docstring."""
    assert check_blacklist("static.speedtest.net", {"speedtest.net"}) is True


# --------------------------------------------------------------------------
# 2. No-redirect
# --------------------------------------------------------------------------


class _FakeResp:
    def __init__(self, status: int, location: str | None = None) -> None:
        self.status = status
        self.headers = {"Location": location} if location else {}

    async def __aenter__(self) -> _FakeResp:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        return None


class _FakeSession:
    """Minimal aiohttp.ClientSession substitute for HEAD-only tests."""

    def __init__(self, resp: _FakeResp) -> None:
        self._resp = resp

    def head(self, *args: Any, **kwargs: Any) -> _FakeResp:
        return self._resp


@pytest.mark.asyncio
async def test_no_redirect_on_200_is_ok() -> None:
    session = _FakeSession(_FakeResp(200))
    assert await check_no_redirect("example.com", session) is True  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_no_redirect_301_same_host_is_ok() -> None:
    """A 301 to the same hostname on a different path is fine for Reality."""
    session = _FakeSession(_FakeResp(301, "https://example.com/en/"))
    assert await check_no_redirect("example.com", session) is True  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_no_redirect_301_different_host_fails() -> None:
    session = _FakeSession(_FakeResp(301, "https://www.example.com/"))
    assert await check_no_redirect("example.com", session) is False  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_no_redirect_301_without_location_is_ok() -> None:
    """Pathological: server says '301' but omits Location. Not a real redirect."""
    session = _FakeSession(_FakeResp(301, None))
    assert await check_no_redirect("example.com", session) is True  # type: ignore[arg-type]


# --------------------------------------------------------------------------
# 3. Same-ASN
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_same_asn_matches(monkeypatch) -> None:
    asn_module._cached_lookup.cache_clear()
    monkeypatch.setattr(socket, "gethostbyname", lambda host: "1.2.3.4")

    async def fake_lookup(ip: str):
        return asn_module.ASNInfo(
            asn=14061,
            country="US",
            bgp_prefix="1.2.3.0/24",
            registry="arin",
            allocated="",
            org="DigitalOcean",
        )

    monkeypatch.setattr(checks_module, "lookup_asn", fake_lookup)
    assert await check_same_asn("somehost.example", 14061) is True
    asn_module._cached_lookup.cache_clear()


@pytest.mark.asyncio
async def test_same_asn_mismatch(monkeypatch) -> None:
    asn_module._cached_lookup.cache_clear()
    monkeypatch.setattr(socket, "gethostbyname", lambda host: "8.8.8.8")

    async def fake_lookup(ip: str):
        return asn_module.ASNInfo(
            asn=15169,
            country="US",
            bgp_prefix="8.8.8.0/24",
            registry="arin",
            allocated="",
            org="GOOGLE",
        )

    monkeypatch.setattr(checks_module, "lookup_asn", fake_lookup)
    assert await check_same_asn("somehost.example", 14061) is False
    asn_module._cached_lookup.cache_clear()


@pytest.mark.asyncio
async def test_same_asn_dns_fail(monkeypatch) -> None:
    """DNS failure => not same ASN. Not a program crash."""

    def fake_gethostbyname(host: str) -> str:
        raise socket.gaierror("dns nope")

    monkeypatch.setattr(socket, "gethostbyname", fake_gethostbyname)
    assert await check_same_asn("never.resolve.example", 14061) is False


# --------------------------------------------------------------------------
# 4-6. TLS handshake (via the TLSProbe helper)
# --------------------------------------------------------------------------


def test_contains_x25519_positive() -> None:
    assert _contains_x25519(["X25519"]) is True
    assert _contains_x25519(["x25519"]) is True
    assert _contains_x25519(["x25519_kyber768"]) is True


def test_contains_x25519_negative() -> None:
    assert _contains_x25519([]) is False
    assert _contains_x25519(["P-256"]) is False


@pytest.mark.asyncio
async def test_probe_tls_happy_path(monkeypatch) -> None:
    """Mock the sync helper so we can test the async wrapper."""
    fake = TLSProbe(
        tls13_ok=True,
        alpn_h2_ok=True,
        x25519_ok=True,
        ocsp_stapling=True,
        rtt_ms=45,
    )

    def fake_sync(host: str, timeout: float) -> TLSProbe:
        assert host == "www.microsoft.com"
        return fake

    monkeypatch.setattr(checks_module, "_probe_tls_sync", fake_sync)
    result = await checks_module.probe_tls("www.microsoft.com")
    assert result == fake


@pytest.mark.asyncio
async def test_probe_tls_handshake_failure_surfaces_as_all_false(
    monkeypatch,
) -> None:
    fail = TLSProbe(
        tls13_ok=False,
        alpn_h2_ok=False,
        x25519_ok=False,
        ocsp_stapling=False,
        rtt_ms=None,
    )
    monkeypatch.setattr(
        checks_module,
        "_probe_tls_sync",
        lambda host, timeout: fail,
    )
    result = await checks_module.probe_tls("dead.example")
    assert result.tls13_ok is False
    assert result.rtt_ms is None


# --------------------------------------------------------------------------
# CheckResults.all_hard_pass sanity
# --------------------------------------------------------------------------


def test_check_results_all_hard_pass_true_when_all_six_true() -> None:
    r = CheckResults(
        blacklist_ok=True,
        no_redirect=True,
        same_asn=True,
        tls13_ok=True,
        alpn_h2_ok=True,
        x25519_ok=True,
    )
    assert r.all_hard_pass is True


def test_check_results_all_hard_pass_false_on_any_miss() -> None:
    # Flip each indicator once, confirm all_hard_pass flips with it.
    base = CheckResults(
        blacklist_ok=True,
        no_redirect=True,
        same_asn=True,
        tls13_ok=True,
        alpn_h2_ok=True,
        x25519_ok=True,
    )
    from dataclasses import replace

    for field in (
        "blacklist_ok",
        "no_redirect",
        "same_asn",
        "tls13_ok",
        "alpn_h2_ok",
        "x25519_ok",
    ):
        r = replace(base, **{field: False})
        assert r.all_hard_pass is False, f"{field} should fail all_hard_pass"


@asynccontextmanager
async def _unused() -> Any:
    yield None
