"""
port_canonical — penalize 443 (and other "loud") ports for Reality.

443 is the highest-volume HTTPS port on the public internet, which
means it's the highest-priority probe target for DPI / GFW engines.
Reality's purpose is to look like normal HTTPS, so picking a port
where normal HTTPS already gets aggressive scrutiny works against
the tool.

Cloudflare's documented HTTPS-alternate ports — 2053, 2083, 2087, 2096
— look like first-class Cloudflare-fronted traffic to passive
observers (lots of CF-protected sites use these for the exact same
"low-attention HTTPS" reason). That's the recommended set per the
compass artifact.

Port categorization comes from ``seeds/standard_ports.json`` so
operators can tweak the policy via a PR rather than a code edit.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from hardening.reality.models import Finding, RealityTarget

_PORTS_PATH = Path(__file__).parent.parent / "seeds" / "standard_ports.json"


@lru_cache(maxsize=1)
def _load_port_policy() -> dict[str, list[int]]:
    return json.loads(_PORTS_PATH.read_text(encoding="utf-8"))


def check_port_canonical(target: RealityTarget) -> Finding:
    """Return a Finding categorizing the port choice.

    -15 if port ∈ critical (443),
    -5  if port ∈ warning (80, 8443),
    0   if port ∈ recommended (2053/2083/2087/2096) or any other
        non-standard high port (>= 1024 not in critical/warning).
    """
    policy = _load_port_policy()
    port = target.port

    if port in policy.get("critical", []):
        return Finding(
            check="port_canonical",
            ok=False,
            severity="critical",
            score_delta=-15,
            evidence=(
                f"Port {port} is the highest-attention HTTPS port; "
                "Reality on 443 sits in the same probe queue as every "
                "other HTTPS server"
            ),
            remediation=(
                "Switch to a Cloudflare HTTPS-alternate: 2053, 2083, 2087, "
                "or 2096. These look like CF-fronted traffic and dodge the "
                "443 probe queue"
            ),
            data={"port": port, "tier": "critical"},
        )

    if port in policy.get("warning", []):
        return Finding(
            check="port_canonical",
            ok=False,
            severity="warning",
            score_delta=-5,
            evidence=(
                f"Port {port} draws attention (alternate HTTP/HTTPS port "
                "frequently scanned by service-fingerprinting tools)"
            ),
            remediation="Prefer 2053/2083/2087/2096 for Reality endpoints",
            data={"port": port, "tier": "warning"},
        )

    if port in policy.get("recommended", []):
        return Finding(
            check="port_canonical",
            ok=True,
            severity="info",
            score_delta=0,
            evidence=f"Port {port} is a recommended Cloudflare-alternate",
            remediation="",
            data={"port": port, "tier": "recommended"},
        )

    return Finding(
        check="port_canonical",
        ok=True,
        severity="info",
        score_delta=0,
        evidence=(
            f"Port {port} is non-standard but not in the bundled hot list"
        ),
        remediation="",
        data={"port": port, "tier": "other"},
    )


__all__ = ["check_port_canonical"]
