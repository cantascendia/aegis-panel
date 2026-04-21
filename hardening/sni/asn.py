"""
ASN + country lookup via Team Cymru WHOIS (port 43).

Why Team Cymru:
- Free, no API key, no signup.
- Returns ASN + country + allocation date in one query.
- Well-documented and stable since ~2008.

We use the TCP WHOIS protocol (port 43) rather than their DNS mode
because:
- No new DNS library dependency needed (stdlib socket is enough).
- The verbose bulk-mode response is easier to parse deterministically.

Rejected alternatives:
- MaxMind GeoLite2 — free but requires license signup + recurring
  DB update; ops overhead for zero MVP accuracy gain.
- IPinfo / IP2Proxy — paid for the good data.
- RIPE/ARIN WHOIS — authoritative but rate-limited and slow; kept
  mentally as a fallback but not implemented in MVP.
"""

from __future__ import annotations

import asyncio
import socket
from dataclasses import dataclass
from functools import lru_cache


class ASNLookupError(RuntimeError):
    """WHOIS timed out, returned garbage, or didn't know the IP."""


@dataclass(frozen=True)
class ASNInfo:
    asn: int
    country: str  # ISO 2-letter, may be "ZZ" if unknown
    bgp_prefix: str  # e.g. "1.2.3.0/24"
    registry: str  # e.g. "arin" / "ripencc"
    allocated: str  # ISO date, may be empty
    org: str  # free-text org name


_CYMRU_HOST = "whois.cymru.com"
_CYMRU_PORT = 43
_TIMEOUT_SECONDS = 5.0


def _whois_sync(ip: str) -> str:
    """Blocking TCP WHOIS query. Called via asyncio.to_thread."""
    query = f"begin\nverbose\n{ip}\nend\n".encode()
    with socket.create_connection(
        (_CYMRU_HOST, _CYMRU_PORT), timeout=_TIMEOUT_SECONDS
    ) as s:
        s.sendall(query)
        chunks: list[bytes] = []
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            chunks.append(chunk)
    return b"".join(chunks).decode("utf-8", errors="replace")


def _parse(response: str, ip: str) -> ASNInfo:
    """Parse Team Cymru's bulk-verbose response.

    Format (tab-separated, header line ends with 'UTC'):
      AS      | IP          | BGP Prefix | CC | Registry | Allocated | AS Name
      15169   | 8.8.8.8     | 8.8.8.0/24 | US | arin     | 1992-12-01 | GOOGLE, US

    The first line is a human-readable header ending in 'UTC'. Each
    subsequent non-empty line is a record. In single-IP queries there's
    exactly one record; in bulk mode one per input. We assume one.
    """
    data_lines = [
        ln
        for ln in response.splitlines()
        if ln and not ln.lower().startswith("bulk") and "UTC" not in ln
    ]
    if not data_lines:
        raise ASNLookupError(
            f"Team Cymru returned no data for {ip}: {response!r}"
        )
    row = [col.strip() for col in data_lines[0].split("|")]
    if len(row) < 7:
        raise ASNLookupError(f"malformed Cymru row for {ip}: {row!r}")
    try:
        asn = int(row[0]) if row[0].isdigit() else 0
    except ValueError as exc:
        raise ASNLookupError(
            f"non-numeric ASN in Cymru row: {row[0]!r}"
        ) from exc
    if asn == 0:
        raise ASNLookupError(f"Team Cymru has no ASN for {ip}")
    return ASNInfo(
        asn=asn,
        country=row[3] or "ZZ",
        bgp_prefix=row[2],
        registry=row[4],
        allocated=row[5],
        org=row[6],
    )


@lru_cache(maxsize=1024)
def _cached_lookup(ip: str) -> ASNInfo:
    """Sync cached version. Use `lookup_asn` from async code."""
    response = _whois_sync(ip)
    return _parse(response, ip)


async def lookup_asn(ip: str) -> ASNInfo:
    """Look up ASN + country + BGP prefix for an IP.

    Runs the blocking socket call in the default thread pool so the
    event loop stays responsive while we wait on Cymru.
    """
    return await asyncio.to_thread(_cached_lookup, ip)
