"""
shortid_compliance — Reality short_ids must be hex, deduped, non-zero, ≤8.

xray/Reality requires each shortId to:
- be hex characters only ([0-9a-f], lowercase preferred)
- be 0-16 chars long (0 = use default; 16 = max in protocol)
- not collide with another shortId on the same host (collisions break
  per-shortId routing if the operator uses different shortIds to
  identify clients)
- not be all zeros (a "" empty default is fine; "0000" is a malformed
  attempt at meaningful traffic which actually behaves identically to
  empty — confusing and wrong)

Recommended count: ≤ 8 shortIds per inbound. More than that is
operationally noisy without protocol benefit.
"""

from __future__ import annotations

import re

from hardening.reality.models import Finding, RealityTarget

_HEX_RE = re.compile(r"^[0-9a-f]*$")
_MAX_RECOMMENDED_COUNT = 8
_MIN_LENGTH_FOR_NONEMPTY = 4


def check_shortid_compliance(target: RealityTarget) -> Finding:
    """Return a Finding categorizing shortId-set health.

    Worst-case wins: if any shortId is illegal we report critical
    even if other shortIds are fine. If shape is OK but count is
    high or lengths are short, we surface as warning.
    """
    short_ids = target.short_ids or []

    if not short_ids:
        # An entirely-empty shortIds list is xray's "single default"
        # mode. Legal but worth flagging if the operator meant to
        # configure per-client routing.
        return Finding(
            check="shortid_compliance",
            ok=True,
            severity="info",
            score_delta=0,
            evidence="shortIds list is empty (xray default mode)",
            remediation="",
            data={"count": 0},
        )

    illegal: list[str] = []
    for sid in short_ids:
        if not isinstance(sid, str):
            illegal.append(repr(sid))
            continue
        if len(sid) > 16:
            illegal.append(f"{sid!r} (too long, max 16)")
            continue
        if not _HEX_RE.match(sid):
            illegal.append(f"{sid!r} (non-hex character)")
            continue
        if sid and set(sid) == {"0"}:
            illegal.append(f"{sid!r} (all-zeros)")

    if illegal:
        return Finding(
            check="shortid_compliance",
            ok=False,
            severity="critical",
            score_delta=-25,
            evidence=(
                f"shortIds violate the hex/length/non-zero rule: "
                f"{', '.join(illegal[:5])}"
                + ("..." if len(illegal) > 5 else "")
            ),
            remediation=(
                "Each shortId must match [0-9a-f]{0,16} and not be all-zero. "
                "Regenerate via xray's helper: `xray uuid` then truncate to "
                "an even hex length, or use the panel's auto-generator"
            ),
            data={"count": len(short_ids), "illegal_count": len(illegal)},
        )

    duplicates = [s for s in short_ids if short_ids.count(s) > 1]
    if duplicates:
        return Finding(
            check="shortid_compliance",
            ok=False,
            severity="critical",
            score_delta=-25,
            evidence=(
                "shortIds contain duplicates " f"({sorted(set(duplicates))!r})"
            ),
            remediation=(
                "shortIds must be unique within an inbound; deduplicate or "
                "regenerate"
            ),
            data={
                "count": len(short_ids),
                "duplicates": sorted(set(duplicates)),
            },
        )

    short_or_overgrown = (
        any(0 < len(s) < _MIN_LENGTH_FOR_NONEMPTY for s in short_ids)
        or len(short_ids) > _MAX_RECOMMENDED_COUNT
    )
    if short_or_overgrown:
        return Finding(
            check="shortid_compliance",
            ok=False,
            severity="warning",
            score_delta=-5,
            evidence=(
                f"shortIds: {len(short_ids)} entries, "
                f"min len {min((len(s) for s in short_ids if s), default=0)}; "
                f"recommend ≤{_MAX_RECOMMENDED_COUNT} entries, length ≥"
                f"{_MIN_LENGTH_FOR_NONEMPTY}"
            ),
            remediation=(
                "Trim to ≤8 entries; regenerate any short (<4 hex char) "
                "ids — short shortIds reduce per-client routing entropy"
            ),
            data={"count": len(short_ids)},
        )

    return Finding(
        check="shortid_compliance",
        ok=True,
        severity="info",
        score_delta=0,
        evidence=f"{len(short_ids)} shortIds, all hex, deduped, non-zero",
        remediation="",
        data={"count": len(short_ids)},
    )


__all__ = ["check_shortid_compliance"]
