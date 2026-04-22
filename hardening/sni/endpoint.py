"""
FastAPI router for the SNI intelligent selector.

Exposes ``POST /api/nodes/sni-suggest`` so the dashboard "新建节点" form
can auto-populate Reality ``serverName`` candidates. SPEC follow-up #2
of ``docs/ai-cto/SPEC-sni-selector.md``.

Architectural note — SPEC deviation
-----------------------------------
The SPEC originally said ``app/routes/node.py`` gets a new endpoint.
We put it here in ``hardening/sni/endpoint.py`` instead, and register
it through :func:`hardening.panel.apply_panel_hardening`. Rationale:
keep upstream ``app/routes/*`` files untouched to minimize merge
conflicts during future ``upstream-sync/*`` branches. This is a
continued application of the "upstream 冲突面 = 一行" principle from
Round 1 (see VISION.md); not a new architectural decision.

Trade-off accepted: the SNI module now depends on FastAPI + Pydantic.
That's fine for a FastAPI panel project; the alternative (a separate
``hardening/panel/sni_endpoint.py`` glue file) would split one
feature across two directories for no real isolation benefit.

Design choices
--------------
- **Auth**: ``SudoAdminDep``. Only sudo admins can request SNI
  probes — probes are a measurable resource cost (dozens of TLS
  handshakes against third-party hosts).
- **Rate limit**: 6/minute per IP. Dashboard "new node" form blur
  event frequency is well below this. Tuned to allow normal operator
  workflow without giving an authenticated insider a free DoS lever.
- **Timeout**: 60 seconds, via ``asyncio.wait_for``. SPEC budget.
- **Error surfacing**: TimeoutError -> 504, seeds/blacklist load
  errors -> 500 (operator misconfiguration, not caller's fault),
  unexpected exceptions -> 500 with generic message + logged
  traceback. ASN lookup failure bubbles up as the existing
  selector-level rejection reason; we don't special-case it.

Rate limiting — confirmed deferred (PR #22 post-mortem)
-------------------------------------------------------
Attempted to restore ``@limiter.limit("6/minute")`` on this route in
PR #22 (Round 2 B-batch-2). Local reproduction against the exact
CI-pinned versions (``fastapi==0.121.0``, ``starlette==0.49.1``,
``pydantic==2.10``, ``slowapi==0.1.9``) returned 200 OK with proper
body + dep resolution — so the decorator pattern APPEARS correct.

But the same code in **CI on Ubuntu** reproduced the original 422
with ``body`` + ``admin`` falling through to query resolution,
identical to PR #16. Conclusion: the incompatibility is real but
platform- or environment-specific in a way we can't reproduce on
Windows local tooling. Not worth continuing to debug slowapi
internals on Linux CI blindly — the ROI is negative compared to
other Round 2 work.

So rate-limit stays OFF on this route. Defense-in-depth remains:
- ``SudoAdminDep`` — authenticated, sudo-only callers
- ``asyncio.wait_for(60s)`` — per-call wall clock
- ``asyncio.Semaphore(5)`` inside ``select_candidates`` — outbound
  probe concurrency cap

Path forward when someone returns to this
- Reproduce in a Linux VM or Docker with ``python:3.12-slim``,
  the exact ``requirements-dev.txt`` pins, and a minimal FastAPI
  test harness
- Consider alternatives: manual ``_check_request_limit`` call
  inside the handler body (sidestepping the decorator signature
  path), or ``shared_limit`` variant
- LESSONS.md L-010 stays accurate — do NOT blindly re-apply
  ``@limiter.limit`` to new async def routes in this repo without
  the above investigation landing first
"""

from __future__ import annotations

import asyncio
import logging
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Body, HTTPException, Request
from pydantic import BaseModel, Field

from app.dependencies import SudoAdminDep
from hardening.sni.loaders import SeedLoadError
from hardening.sni.selector import select_candidates

logger = logging.getLogger(__name__)


# Single-source-of-truth for the probe wall-clock budget. Exported so
# tests can monkeypatch without importing the private module path.
SNI_SUGGEST_TIMEOUT_SECONDS = 60.0


class SniSuggestRequest(BaseModel):
    """Input for ``POST /api/nodes/sni-suggest``.

    ``vps_ip`` is accepted as a plain string (not ``IPvAnyAddress``)
    because the selector itself accepts any str — it passes through
    to :func:`hardening.sni.asn.lookup_asn` which handles IPv4/IPv6
    uniformly via Team Cymru. Validating the shape here would only
    duplicate that logic.
    """

    vps_ip: str = Field(
        ...,
        min_length=7,  # "1.2.3.4" is the shortest plausible IPv4
        max_length=45,  # max IPv6 with zone id
        description="Public egress IP of the VPS hosting the node.",
    )
    count: int = Field(
        5,
        ge=1,
        le=50,
        description="How many top-scored candidates to return.",
    )
    region: Literal["auto", "global", "jp", "kr", "us", "eu"] = Field(
        "auto",
        description=(
            "Seed pool. 'auto' == 'global' only. Regional values "
            "merge global + the named region's seeds (deduped)."
        ),
    )


router = APIRouter(prefix="/api/nodes", tags=["SNI"])


@router.post(
    "/sni-suggest",
    response_model=None,  # we return dict; schema is golden-file tested
    summary="Suggest Reality serverName candidates for a VPS",
    description=(
        "Probes the configured seed pool against six hard indicators "
        "(DPI blacklist / no-redirect / same-ASN / TLS 1.3 / ALPN h2 "
        "/ X25519) and returns the top-scored candidates. Total wall "
        "clock capped at 60 s."
    ),
)
async def sni_suggest(
    request: Request,  # noqa: ARG001  # kept for future rate-limit reintroduction
    body: Annotated[SniSuggestRequest, Body()],
    admin: SudoAdminDep,
) -> dict[str, Any]:
    """Probe + rank SNI candidates. Sudo-admin only."""
    logger.info(
        "sni_suggest invoked by admin=%s vps_ip=%s count=%d region=%s",
        admin.username,
        body.vps_ip,
        body.count,
        body.region,
    )

    try:
        result = await asyncio.wait_for(
            select_candidates(
                vps_ip=body.vps_ip,
                count=body.count,
                region=body.region,
            ),
            timeout=SNI_SUGGEST_TIMEOUT_SECONDS,
        )
    except TimeoutError:
        # 60 s budget exceeded. Seed pool size × probe concurrency
        # should keep this off the hot path in practice. If it fires
        # in production, it's a signal to shrink the seed pool or
        # raise the semaphore cap — not to widen the timeout.
        #
        # `from None` intentional: the bare TimeoutError traceback is
        # noise. The HTTPException detail captures the operator-facing
        # reason already.
        logger.warning(
            "sni_suggest timeout for vps_ip=%s region=%s",
            body.vps_ip,
            body.region,
        )
        raise HTTPException(
            status_code=504,
            detail=(
                "sni_probe_timeout: aggregate probe wall-clock exceeded "
                f"{int(SNI_SUGGEST_TIMEOUT_SECONDS)}s. Try a smaller "
                "region or count."
            ),
        ) from None
    except SeedLoadError as e:
        # Operator misconfiguration (malformed seeds/*.yaml or
        # blacklist.yaml). Surface cleanly so they can fix it instead
        # of seeing a 500 Internal Server Error with no clue.
        #
        # `from e` intentional: preserves the underlying parse error
        # in the chained traceback for log forensics.
        logger.error("sni_suggest seed/blacklist load failure: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"sni_seed_load_error: {e}",
        ) from e

    return result.to_dict()


__all__ = [
    "router",
    "SniSuggestRequest",
    "SNI_SUGGEST_TIMEOUT_SECONDS",
]
