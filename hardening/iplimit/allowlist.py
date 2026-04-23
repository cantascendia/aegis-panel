"""CIDR allowlist helpers for IP limiter observations."""

from __future__ import annotations

import ipaddress
from collections.abc import Sequence

IpNetwork = ipaddress.IPv4Network | ipaddress.IPv6Network


def parse_cidrs(text: str) -> list[IpNetwork]:
    """Parse newline-separated CIDRs, ignoring blank lines."""

    networks: list[IpNetwork] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        candidate = raw_line.strip()
        if not candidate:
            continue
        try:
            networks.append(ipaddress.ip_network(candidate, strict=False))
        except ValueError as exc:
            raise ValueError(
                f"invalid CIDR on line {line_number}: {candidate}"
            ) from exc
    return networks


def ip_matches_any_cidr(ip: str, cidrs: Sequence[IpNetwork]) -> bool:
    """Return whether an IP address belongs to any allowlisted network."""

    try:
        address = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(
        address.version == network.version and address in network
        for network in cidrs
    )


def merge_cidr_texts(*values: str | None) -> str:
    """Merge allowlist text blocks while preserving first-seen order."""

    merged: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not value:
            continue
        for raw_line in value.splitlines():
            candidate = raw_line.strip()
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            merged.append(candidate)
    return "\n".join(merged)
