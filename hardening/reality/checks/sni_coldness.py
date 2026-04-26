"""
sni_coldness — penalize Reality serverNames that sit on hot domain rankings.

Reasoning per ``compass_artifact_*.md``: GFW (and other DPI engines)
preferentially probe popular CDN endpoints. Picking ``www.google.com``
or ``cloudflare.com`` as the Reality SNI puts the node in the same
metadata bucket as legitimate Google traffic — high baseline volume
hides nothing because the operator doesn't actually serve Google
content. Cold but plausible SNIs (regional CDN tails) attract less
attention.

Loader: top-N rank list bundled at
``hardening/reality/seeds/top1k.json``. Module loads the JSON once
into an LRU cache; subsequent checks use the in-memory dict for
O(1) lookup. Refresh procedure documented in
``seeds/update_top1k.py`` and the ops runbook.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from hardening.reality.models import Finding, RealityTarget

_TOP1K_PATH = Path(__file__).parent.parent / "seeds" / "top1k.json"


@lru_cache(maxsize=1)
def _load_rank_index() -> dict[str, int]:
    """Parse ``top1k.json`` into a ``{host: rank}`` dict."""
    data = json.loads(_TOP1K_PATH.read_text(encoding="utf-8"))
    return {entry["host"]: entry["rank"] for entry in data["entries"]}


def check_sni_coldness(target: RealityTarget) -> Finding:
    """Return a Finding scoring SNI's GFW-attention risk by rank.

    -30 if rank ≤ 100 (huge target — refuse to recommend),
    -10 if rank ≤ 1000 (warning, still risky),
    0 otherwise (cold enough; this is the desired state).
    """
    rank_index = _load_rank_index()
    sni = target.sni.lower().strip().rstrip(".")

    rank = rank_index.get(sni)

    if rank is None:
        return Finding(
            check="sni_coldness",
            ok=True,
            severity="info",
            score_delta=0,
            evidence=f"SNI {target.sni!r} not in bundled top-1k list",
            remediation="",
            data={"rank": None},
        )

    if rank <= 100:
        return Finding(
            check="sni_coldness",
            ok=False,
            severity="critical",
            score_delta=-30,
            evidence=(
                f"SNI {target.sni!r} ranks {rank} in top-1k — high-traffic "
                "domain, likely on GFW probing whitelist"
            ),
            remediation=(
                "Pick a colder regional CDN tail (e.g. www.lovelive-anime.jp, "
                "static.naver.net) or use hardening/sni/selector to find "
                "candidates that pass TLS/H2/X25519 probes"
            ),
            data={"rank": rank, "tier": "top-100"},
        )

    return Finding(
        check="sni_coldness",
        ok=False,
        severity="warning",
        score_delta=-10,
        evidence=(
            f"SNI {target.sni!r} ranks {rank} (top-1000) — moderately popular"
        ),
        remediation=(
            "Consider a less-trafficked SNI; use hardening/sni/selector for "
            "ASN-aligned regional alternatives"
        ),
        data={"rank": rank, "tier": "top-1000"},
    )


__all__ = ["check_sni_coldness"]
