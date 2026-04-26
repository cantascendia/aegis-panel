"""
FastAPI router for the Reality config auditor (R.3).

Exposes ``POST /api/reality/audit`` so the dashboard "Reality 审计"
page (R.4) can request a report on demand. SPEC follow-up #3 of
``docs/ai-cto/SPEC-reality-audit.md``.

Same architectural choices as the SNI endpoint
----------------------------------------------
- **Lives under `hardening/reality/`** rather than `app/routes/*` to
  preserve the "upstream 冲突面 = 一行" principle (Round 1 / D-009).
  Registered via :func:`hardening.panel.apply_panel_hardening`'s
  one-line `include_router` so the upstream-sync diff stays trivial.
- **Auth**: ``SudoAdminDep``. Only sudo admins can request audits.
  Reading panel DB rows + invoking checks is read-only but exposes
  Reality config details (public keys, shortIds) that are sensitive.
- **No rate limit decorator**: same slowapi async-def 422 issue
  documented in `hardening/sni/endpoint.py` and ``LESSONS.md#L-010``.
  Auth gate + sub-second pure-CPU runtime mean abuse risk is
  bounded; if abuse becomes an issue, defer-to-later mitigation per
  L-010's three options.
- **Timeout**: 60 seconds via ``asyncio.wait_for``. The audit itself
  is sync but `asn_match` triggers async DNS+WHOIS internally; total
  budget mirrors the CLI default.

Body contract
-------------
Two source modes, mutex via the ``source`` discriminator:

- ``{"source": "db", "vps_asn": <int|null>}`` — read panel `InboundHost`
  rows. Same path as `--from-db` in the CLI.
- ``{"source": "config", "config": {<xray-config-json>}, "vps_asn": <int|null>}``
  — caller passes an arbitrary xray config dict. Useful for dry-run
  audits before the operator commits the config.

``vps_asn`` is optional in both modes; when omitted, ``asn_match``
returns a warning (graceful degradation, same as CLI).

Returns the SPEC v1.0 :class:`Report` schema as JSON.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.dependencies import SudoAdminDep
from hardening.reality.checks import (
    check_port_canonical,
    check_shortid_compliance,
    check_sni_coldness,
    check_timeout_config,
)
from hardening.reality.checks.asn_match import check_asn_match
from hardening.reality.loader import from_db_rows, from_xray_config
from hardening.reality.models import (
    Finding,
    RealityTarget,
    Report,
    ReportSummary,
    TargetResult,
)
from hardening.reality.scoring import grade_for, score_target

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reality", tags=["Reality Audit"])

_AUDIT_TIMEOUT_SECONDS = 60.0
_SCHEMA_VERSION = "1.0"


class AuditRequest(BaseModel):
    """Body for ``POST /api/reality/audit``.

    ``source == "db"`` reads panel rows; ``source == "config"`` reads
    the supplied dict. ``config`` is required when source is "config",
    forbidden otherwise (validator enforces).
    """

    model_config = ConfigDict(extra="forbid")

    source: Literal["db", "config"] = Field(
        default="db",
        description="Where to read Reality targets from.",
    )
    config: dict[str, Any] | None = Field(
        default=None,
        description=(
            "An xray server config dict. Required when source='config', "
            "must be omitted when source='db'."
        ),
    )
    vps_asn: int | None = Field(
        default=None,
        ge=1,
        description=(
            "VPS egress ASN. Enables the asn_match check. Omit for "
            "graceful degradation (asn_match returns a warning)."
        ),
    )


@router.post("/audit", response_model=None)
async def audit(
    body: Annotated[AuditRequest, Body()],
    admin: SudoAdminDep,  # noqa: ARG001  # auth gate
) -> dict[str, Any]:
    """Run a Reality audit and return the v1.0 Report JSON.

    See module docstring for body contract. Errors:

    - 400 if body shape inconsistent with `source`
    - 504 if the audit exceeds 60s (likely WHOIS hangs)
    - 500 on loader / unexpected internal failure
    """
    if body.source == "config" and body.config is None:
        raise HTTPException(
            status_code=400,
            detail="source='config' requires a 'config' body field",
        )
    if body.source == "db" and body.config is not None:
        raise HTTPException(
            status_code=400,
            detail="source='db' must not include a 'config' body field",
        )

    try:
        report = await asyncio.wait_for(
            _run_audit(body), timeout=_AUDIT_TIMEOUT_SECONDS
        )
    except TimeoutError as exc:
        logger.warning(
            "reality audit timed out after %ss", _AUDIT_TIMEOUT_SECONDS
        )
        raise HTTPException(
            status_code=504,
            detail=(
                f"Reality audit exceeded {_AUDIT_TIMEOUT_SECONDS:.0f}s budget. "
                "Likely cause: ASN WHOIS lookups hanging. Retry, or omit "
                "vps_asn to skip ASN matching."
            ),
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("reality audit failed unexpectedly")
        raise HTTPException(
            status_code=500,
            detail="Reality audit failed; see panel logs for details.",
        ) from exc

    return report.to_dict()


async def _run_audit(body: AuditRequest) -> Report:
    """Body of the audit; isolated so wait_for can wrap it cleanly."""
    targets = _load_targets(body)
    audited_at = (
        datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    )

    target_results: list[TargetResult] = []
    for target in targets:
        findings: list[Finding] = [
            check_sni_coldness(target),
            check_port_canonical(target),
            check_shortid_compliance(target),
            check_timeout_config(target),
            await _maybe_asn_check_async(target, body.vps_asn),
        ]
        score = score_target(findings)
        grade = grade_for(score)
        target_results.append(
            TargetResult(
                host=target.host,
                sni=target.sni,
                port=target.port,
                score=score,
                grade=grade,
                findings=findings,
            )
        )

    summary = _summarize(target_results)
    return Report(
        schema_version=_SCHEMA_VERSION,
        audited_at=audited_at,
        source=body.source,
        targets=target_results,
        summary=summary,
    )


def _load_targets(body: AuditRequest) -> list[RealityTarget]:
    """Resolve the configured source to a list of targets."""
    if body.source == "config":
        # `body.config` non-None enforced earlier.
        assert body.config is not None
        return from_xray_config(body.config)

    # `source == "db"`: lazy import so test paths that only exercise
    # source='config' don't need the panel DB import chain.
    from app.db import GetDB
    from app.db.models import InboundHost

    with GetDB() as db:
        rows = list(db.query(InboundHost).all())
        return from_db_rows(rows)


async def _maybe_asn_check_async(
    target: RealityTarget, vps_asn: int | None
) -> Finding:
    """Wrap asn_match so missing vps_asn yields a clean warning.

    ``check_asn_match`` is sync but internally calls ``asyncio.run`` to
    drive the WHOIS lookup. We're already inside FastAPI's running event
    loop here, so calling it directly raises ``RuntimeError: asyncio.run()
    cannot be called from a running event loop``. Offload to a worker
    thread, which gets its own loop — clean reuse of the existing sync
    check without rewriting it as async.
    """
    if vps_asn is None:
        return Finding(
            check="asn_match",
            ok=False,
            severity="warning",
            score_delta=-10,
            evidence="VPS ASN not provided in request body (vps_asn omitted)",
            remediation=(
                "Send 'vps_asn' in the request body. Find your VPS's "
                "ASN via `whois <vps-egress-ip>` or Team Cymru."
            ),
            data={"vps_asn": None},
        )
    return await asyncio.to_thread(check_asn_match, target, vps_asn)


def _summarize(target_results: list[TargetResult]) -> ReportSummary:
    g = sum(1 for t in target_results if t.grade == "green")
    y = sum(1 for t in target_results if t.grade == "yellow")
    r = sum(1 for t in target_results if t.grade == "red")
    worst = min((t.score for t in target_results), default=100)
    return ReportSummary(
        total=len(target_results),
        green=g,
        yellow=y,
        red=r,
        worst_score=worst,
    )


__all__ = ["router"]
