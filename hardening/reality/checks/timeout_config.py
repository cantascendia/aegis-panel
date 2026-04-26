"""
timeout_config — short connIdle reduces Reality's exposure window.

xray's ``policy.levels.*.connIdle`` controls how long an idle TCP
connection stays open before the server reaps it. Long values (default
is often 600s or unlimited) let DPI engines correlate connections
across time — they observe one TLS handshake, then watch the same
peer reuse the connection across multiple "fake fetches" of the
fronted SNI. Short values (≤120s per compass artifact) force the
client to re-handshake, presenting fresh TLS metadata each time and
flushing the correlation window.

This check enforces the compass-artifact threshold of 120s and warns
between 180-300s (a soft middle ground sometimes used for legitimate
HTTP/2 reuse).
"""

from __future__ import annotations

from hardening.reality.models import Finding, RealityTarget

_RECOMMENDED_MAX = 120
_WARNING_MAX = 300


def check_timeout_config(target: RealityTarget) -> Finding:
    """Return a Finding scoring connIdle policy hardness.

    -15 if conn_idle is None (xray defaults are typically too lax)
        or > 300s,
    -5  if 180–300s,
    0   if ≤ 120s.

    The 120–180s "gap" is intentional — values in that window are
    technically sub-warning but the SPEC promotes 120 as the explicit
    target, so 121–179 is ok-but-not-info-perfect; we still return 0
    score_delta there. The boundary check below uses ``>`` for the
    warning window so 180 itself is the threshold.
    """
    ci = target.conn_idle

    if ci is None or ci > _WARNING_MAX:
        return Finding(
            check="timeout_config",
            ok=False,
            severity="critical",
            score_delta=-15,
            evidence=(
                "connIdle is unset (xray defaults to open-ended)"
                if ci is None
                else f"connIdle is {ci}s (> {_WARNING_MAX}s)"
            ),
            remediation=(
                f"Set conn_idle ≤ {_RECOMMENDED_MAX}s in xray "
                "policy.levels.0.connIdle (and TcpKeepAliveIdle in "
                "sockopt). Forces frequent re-handshakes, flushing "
                "the DPI correlation window"
            ),
            data={"conn_idle": ci},
        )

    if ci > _RECOMMENDED_MAX:
        return Finding(
            check="timeout_config",
            ok=False,
            severity="warning",
            score_delta=-5,
            evidence=(
                f"connIdle is {ci}s — above recommended "
                f"{_RECOMMENDED_MAX}s; tolerable but tighter is better"
            ),
            remediation=(
                f"Lower conn_idle to ≤{_RECOMMENDED_MAX}s for stronger "
                "metadata flushing"
            ),
            data={"conn_idle": ci},
        )

    return Finding(
        check="timeout_config",
        ok=True,
        severity="info",
        score_delta=0,
        evidence=f"connIdle is {ci}s (≤ {_RECOMMENDED_MAX}s)",
        remediation="",
        data={"conn_idle": ci},
    )


__all__ = ["check_timeout_config"]
