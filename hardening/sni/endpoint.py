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

Rate limiting — restored (Round 2 B-batch)
------------------------------------------
Previously removed in PR #16 (third push) when slowapi's
``@limiter.limit`` + ``async def`` combo appeared to mangle
FastAPI's signature introspection (every request returned 422
with body/admin seen as query params). Post-mortem via local
reproduction against CI-pinned fastapi 0.121 + starlette 0.49 +
slowapi 0.1.9 shows the pattern actually works correctly when
``body`` is explicitly ``Annotated[..., Body()]``. The PR #16
second-push failure was likely environmental or caused by a
subtle stale-bytecode issue that went away on the restoration
commit. LESSONS.md L-010 is updated accordingly.

Current rate-limit behaviour
- ``@limiter.limit(SNI_SUGGEST_RATE_LIMIT)`` installed; 6/min per
  remote IP when ``RATE_LIMIT_ENABLED=true``, no-op when disabled
- Still gated by ``SudoAdminDep`` (first line of defense)
- Still bounded by ``asyncio.wait_for(60s)`` and the
  ``Semaphore(5)`` inside ``select_candidates``
- Behind reverse proxies, operators must also configure Uvicorn
  ``--forwarded-allow-ips`` (or a future TrustedProxyMiddleware)
  for ``get_remote_address`` to see the real client IP
"""

from __future__ import annotations

import asyncio
import logging
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Body, HTTPException, Request
from pydantic import BaseModel, Field

from app.dependencies import SudoAdminDep
from hardening.panel.rate_limit import limiter
from hardening.sni.loaders import SeedLoadError
from hardening.sni.selector import select_candidates

logger = logging.getLogger(__name__)


# Single-source-of-truth for the probe wall-clock budget. Exported so
# tests can monkeypatch without importing the private module path.
SNI_SUGGEST_TIMEOUT_SECONDS = 60.0

# Rate limit label. Fixed-window per remote IP (see
# hardening/panel/rate_limit.limiter). 6/min = one every 10 s — above
# any realistic dashboard blur-event cadence but cheap enough to
# disarm casual probing abuse.
SNI_SUGGEST_RATE_LIMIT = "6/minute"


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
@limiter.limit(SNI_SUGGEST_RATE_LIMIT)
async def sni_suggest(
    request: Request,  # noqa: ARG001  # required by slowapi rate-limit decorator
    body: Annotated[SniSuggestRequest, Body()],
    admin: SudoAdminDep,
) -> dict[str, Any]:
    """Probe + rank SNI candidates. Sudo-admin only, rate-limited."""
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
    "SNI_SUGGEST_RATE_LIMIT",
]
