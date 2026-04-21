"""
Tests for hardening/sni/asn.py — Team Cymru WHOIS parser.

We only test the parsing layer (which is deterministic) and the
`_cached_lookup` entry point with a monkeypatched `_whois_sync`
so we never actually hit the network.
"""

from __future__ import annotations

import pytest

from hardening.sni import asn as asn_module
from hardening.sni.asn import ASNInfo, ASNLookupError, _parse

_REAL_CYMRU_RESPONSE = (
    "Bulk mode; whois.cymru.com [2026-04-22 12:00:00 UTC]\n"
    "15169   | 8.8.8.8          | 8.8.8.0/24       | US | arin     "
    "| 1992-12-01 | GOOGLE, US\n"
)


def test_parse_happy_path() -> None:
    info = _parse(_REAL_CYMRU_RESPONSE, "8.8.8.8")
    assert info.asn == 15169
    assert info.country == "US"
    assert info.bgp_prefix == "8.8.8.0/24"
    assert info.registry == "arin"
    assert info.org == "GOOGLE, US"


def test_parse_empty_response_raises() -> None:
    with pytest.raises(ASNLookupError, match="no data"):
        _parse("", "1.2.3.4")


def test_parse_header_only_response_raises() -> None:
    """A Cymru response with only the UTC header and no data rows."""
    with pytest.raises(ASNLookupError, match="no data"):
        _parse(
            "Bulk mode; whois.cymru.com [2026-04-22 12:00:00 UTC]\n",
            "1.2.3.4",
        )


def test_parse_malformed_row_raises() -> None:
    bad = (
        "Bulk mode; whois.cymru.com [2026-04-22 12:00:00 UTC]\n"
        "not-enough | columns\n"
    )
    with pytest.raises(ASNLookupError, match="malformed"):
        _parse(bad, "1.2.3.4")


def test_parse_na_asn_raises() -> None:
    """Cymru returns 'NA' for IPs with no ASN allocation."""
    na_response = (
        "Bulk mode; whois.cymru.com [2026-04-22 12:00:00 UTC]\n"
        "NA      | 203.0.113.1      | NA               | ZZ | NA       "
        "| NA         | NA\n"
    )
    with pytest.raises(ASNLookupError, match="no ASN"):
        _parse(na_response, "203.0.113.1")


@pytest.mark.asyncio
async def test_lookup_asn_uses_sync_helper(monkeypatch) -> None:
    """End-to-end async path with a mocked sync whois."""
    # Clear the LRU cache so a prior test's real lookup (if any)
    # doesn't short-circuit our mock.
    asn_module._cached_lookup.cache_clear()

    def fake_whois(ip: str) -> str:
        assert ip == "1.2.3.4"
        return _REAL_CYMRU_RESPONSE

    monkeypatch.setattr(asn_module, "_whois_sync", fake_whois)

    result = await asn_module.lookup_asn("1.2.3.4")
    assert isinstance(result, ASNInfo)
    assert result.asn == 15169

    # Clean up so subsequent tests don't see the cached entry.
    asn_module._cached_lookup.cache_clear()
