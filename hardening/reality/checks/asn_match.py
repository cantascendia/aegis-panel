"""
asn_match — verify the Reality SNI's IP shares an ASN with the VPS.

Reality's threat model: a passive observer doing TCP-handshake-then-
TLS-handshake on the panel's IP must see the same ASN they'd see if
they hand-shook with the **real** SNI host. If our VPS is on
DigitalOcean (AS14061) but ``www.example.com`` resolves to a Cloudflare
IP (AS13335), the mismatch is detectable: the observer sees a
DigitalOcean-routed peer claiming to be the Cloudflare-fronted
``www.example.com``. SNI ASN ≠ VPS ASN = compromised disguise.

This check requires two pieces of data:
- the VPS's egress IP (caller passes it in; loader knows from xray
  config or env)
- the SNI's resolved IP and ASN (live lookup via the existing
  ``hardening.sni.asn`` Team Cymru WHOIS path)

For the unit test path, ``vps_asn`` is passed in directly so tests
don't need to monkey-patch a VPS-side resolver. Production callers
will pre-resolve VPS ASN in the loader.

DNS resolution + WHOIS happen via :mod:`hardening.sni.asn`, which
already has an LRU cache and returns the same ``ASNInfo`` shape we
need; this check is a thin wrapper that compares numbers and packages
the result as a Finding.
"""

from __future__ import annotations

import asyncio
import socket

from hardening.reality.models import Finding, RealityTarget


def check_asn_match(target: RealityTarget, vps_asn: int) -> Finding:
    """Return a Finding scoring SNI/VPS ASN alignment.

    Inputs:
    - ``target.sni``: hostname to resolve
    - ``vps_asn``: VPS egress ASN (caller-supplied; loader populates)

    Behavior:
    - Same ASN → 0 penalty (the goal state)
    - DNS or WHOIS failure → warning, -10 (we couldn't verify;
      operator should investigate before trusting)
    - SNI ASN known but mismatched → critical, -35
    """
    sni = target.sni.strip().rstrip(".")

    try:
        sni_ip = socket.gethostbyname(sni)
    except (socket.gaierror, OSError) as exc:
        return Finding(
            check="asn_match",
            ok=False,
            severity="warning",
            score_delta=-10,
            evidence=f"DNS lookup for SNI {sni!r} failed: {exc}",
            remediation=(
                "Verify SNI resolves from the panel host's network; check "
                "for DNS leakage or split-horizon issues"
            ),
            data={"sni_ip": None, "sni_asn": None, "vps_asn": vps_asn},
        )

    try:
        from hardening.sni.asn import ASNLookupError, lookup_asn

        info = asyncio.run(lookup_asn(sni_ip))
    except ASNLookupError as exc:
        return Finding(
            check="asn_match",
            ok=False,
            severity="warning",
            score_delta=-10,
            evidence=f"WHOIS lookup for SNI {sni!r} ({sni_ip}) failed: {exc}",
            remediation=(
                "Check Team Cymru reachability; manually confirm SNI's ASN "
                "via `whois` and operator's panel-side ASN before trusting"
            ),
            data={"sni_ip": sni_ip, "sni_asn": None, "vps_asn": vps_asn},
        )

    if info.asn == vps_asn:
        return Finding(
            check="asn_match",
            ok=True,
            severity="info",
            score_delta=0,
            evidence=(f"SNI {sni!r} ASN {info.asn} matches VPS ASN {vps_asn}"),
            remediation="",
            data={"sni_ip": sni_ip, "sni_asn": info.asn, "vps_asn": vps_asn},
        )

    return Finding(
        check="asn_match",
        ok=False,
        severity="critical",
        score_delta=-35,
        evidence=(
            f"SNI {sni!r} on AS{info.asn} ({info.country}) ≠ "
            f"VPS AS{vps_asn} — passive observer can detect mismatch"
        ),
        remediation=(
            "Pick an SNI hosted on the VPS's ASN. Use "
            "hardening/sni/selector to find regional alternatives that "
            "share the VPS network's BGP origin"
        ),
        data={
            "sni_ip": sni_ip,
            "sni_asn": info.asn,
            "sni_country": info.country,
            "vps_asn": vps_asn,
        },
    )


__all__ = ["check_asn_match"]
