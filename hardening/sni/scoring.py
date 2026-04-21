"""
Candidate scoring.

Pure functions. No I/O, no globals. The selector hands in results
from checks.py; we return a float score and a ranking-stable sort
order.
"""

from __future__ import annotations

from hardening.sni.candidate import CheckResults


def score_candidate(
    checks: CheckResults,
    *,
    same_datacenter: bool = False,
) -> float:
    """Return a 0.0..1.2-ish float; sort descending for ranking.

    Base rule: a candidate that fails ANY hard indicator scores 0.
    Above that, start at 1.0 and adjust:

      + 0.1 same datacenter (subnet match inside the same ASN)
      + 0.1 OCSP stapling observed
      - 0.2 TLS handshake RTT > 200ms (cross-ocean penalty)
      - 0.1 Set-Cookie on the root response (suggests session state
            -- more auditable logs of proxy traffic)

    The `Set-Cookie` penalty isn't wired yet (we'd need a GET, not a
    HEAD, to observe it reliably). Leaving the branch as a TODO so
    the scoring surface is ready when follow-up adds it.
    """
    if not checks.all_hard_pass:
        return 0.0

    score = 1.0
    if same_datacenter:
        score += 0.1
    if checks.ocsp_stapling:
        score += 0.1
    if checks.rtt_ms is not None and checks.rtt_ms > 200:
        score -= 0.2
    return round(score, 3)
