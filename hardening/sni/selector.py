"""
SNI selector orchestrator + CLI.

Per docs/ai-cto/SPEC-sni-selector.md:
- Async orchestrator `select_candidates(vps_ip, count, region)`
- CLI entry via `python -m hardening.sni.selector --ip 1.2.3.4 ...`
- Concurrency capped at 5 simultaneous probes (we don't want to
  look like a scanner to any one target)
- Total wall-clock budget: 30s for --count 10 from a 40-entry seed
- Zero network calls in tests — every external point is mockable
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import aiohttp

from hardening.sni.asn import ASNInfo, ASNLookupError, lookup_asn
from hardening.sni.candidate import (
    Candidate,
    CheckResults,
    Rejection,
    SelectorResult,
)
from hardening.sni.checks import (
    TLSProbe,
    check_blacklist,
    check_no_redirect,
    check_same_asn,
    probe_tls,
)
from hardening.sni.loaders import load_blacklist, load_seeds
from hardening.sni.scoring import score_candidate

if TYPE_CHECKING:
    from collections.abc import Awaitable


_DEFAULT_CONCURRENCY = 5
_DEFAULT_TIMEOUT_SECONDS = 30
_SEED_PROBE_TIMEOUT = 5.0


async def select_candidates(
    vps_ip: str,
    count: int = 10,
    region: str = "auto",
    *,
    concurrency: int = _DEFAULT_CONCURRENCY,
    overall_timeout: float = _DEFAULT_TIMEOUT_SECONDS,
) -> SelectorResult:
    """Probe and rank SNI candidates for a VPS.

    Errors:
    - raises `ASNLookupError` if the VPS ASN cannot be determined;
      without an ASN the same-ASN indicator can't run and every
      candidate would score 0. Fail-loud is better.
    - other per-seed probe failures are caught and land as entries
      in `SelectorResult.rejected` with a human reason.
    """
    start = time.monotonic()
    probed_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    blacklist = load_blacklist()
    seeds = load_seeds(region)

    # VPS ASN is a hard prerequisite — if Cymru can't answer, we bail.
    try:
        vps_info: ASNInfo = await lookup_asn(vps_ip)
    except ASNLookupError:
        raise  # re-raise; CLI turns into exit 2 with message

    # Filter blacklist upfront so we don't waste TLS probes on banned hosts.
    fast_rejections: list[Rejection] = []
    survivors: list[dict[str, str]] = []
    for seed in seeds:
        if not check_blacklist(seed["host"], blacklist):
            fast_rejections.append(
                Rejection(
                    host=seed["host"],
                    reason="blacklist: known-bad SNI per hardening/sni/blacklist.yaml",
                )
            )
        else:
            survivors.append(seed)

    sem = asyncio.Semaphore(concurrency)
    async with aiohttp.ClientSession() as session:
        coros = [
            _probe_one(sem, session, seed, vps_info) for seed in survivors
        ]
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*coros, return_exceptions=True),
                timeout=overall_timeout,
            )
        except TimeoutError:
            results = []  # partial-result handling not wired; fail loud.

    candidates: list[Candidate] = []
    probe_rejections: list[Rejection] = []
    for seed, outcome in zip(survivors, results, strict=False):
        if isinstance(outcome, Exception):
            probe_rejections.append(
                Rejection(
                    host=seed["host"],
                    reason=f"probe error: {type(outcome).__name__}: {outcome}",
                )
            )
            continue
        checks, score = outcome  # type: ignore[misc]
        if score == 0.0:
            probe_rejections.append(
                Rejection(
                    host=seed["host"],
                    reason=_failure_reason(checks),
                )
            )
            continue
        candidates.append(
            Candidate(
                host=seed["host"],
                score=score,
                checks=checks,
                notes=seed.get("notes", ""),
            )
        )

    candidates.sort(key=lambda c: c.score, reverse=True)

    return SelectorResult(
        vps_ip=vps_ip,
        vps_asn=vps_info.asn,
        vps_country=vps_info.country,
        probed_at=probed_at,
        elapsed_seconds=time.monotonic() - start,
        candidates=candidates[:count],
        rejected=fast_rejections + probe_rejections,
    )


async def _probe_one(
    sem: asyncio.Semaphore,
    session: aiohttp.ClientSession,
    seed: dict[str, str],
    vps_info: ASNInfo,
) -> tuple[CheckResults, float]:
    """Run the probe pipeline for one seed. Returns (checks, score)."""
    async with sem:
        host = seed["host"]
        # Cheap-first short-circuit is already done in select_candidates
        # (blacklist filtered before we called _probe_one). Remaining
        # indicators run concurrently per-host because they target
        # different endpoints (HTTP :443 for redirect, WHOIS for ASN,
        # :443 TLS probe for 4-6).
        no_redirect_task: Awaitable[bool] = check_no_redirect(
            host, session, timeout=_SEED_PROBE_TIMEOUT
        )
        same_asn_task: Awaitable[bool] = check_same_asn(host, vps_info.asn)
        tls_task: Awaitable[TLSProbe] = probe_tls(
            host, timeout=_SEED_PROBE_TIMEOUT
        )
        no_redirect, same_asn, tls = await asyncio.gather(
            no_redirect_task, same_asn_task, tls_task
        )

    checks = CheckResults(
        blacklist_ok=True,  # already filtered upstream
        no_redirect=no_redirect,
        same_asn=same_asn,
        tls13_ok=tls.tls13_ok,
        alpn_h2_ok=tls.alpn_h2_ok,
        x25519_ok=tls.x25519_ok,
        ocsp_stapling=tls.ocsp_stapling,
        rtt_ms=tls.rtt_ms,
    )
    score = score_candidate(checks)
    return checks, score


def _failure_reason(checks: CheckResults) -> str:
    """Human-readable reason a zero-score candidate was rejected."""
    if not checks.no_redirect:
        return "HTTP 301/302 redirects to a different hostname"
    if not checks.tls13_ok:
        return "TLS 1.3 handshake failed"
    if not checks.alpn_h2_ok:
        return "ALPN did not negotiate h2"
    if not checks.x25519_ok:
        return "X25519 not in negotiated groups (or unknown)"
    if not checks.same_asn:
        return "resolves to an IP in a different ASN than the VPS"
    return "failed one or more hard indicators"


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m hardening.sni.selector",
        description="Pick Reality `serverName` candidates for a VPS.",
    )
    parser.add_argument(
        "--ip",
        required=True,
        help="VPS public egress IP (required; we don't guess from local "
        "interface because the VPS is usually remote).",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=10,
        help="Top N candidates to return (default 10).",
    )
    parser.add_argument(
        "--region",
        default="auto",
        choices=("auto", "global", "jp", "kr", "us", "eu"),
        help="Region seed list to use. 'auto' uses only global seeds.",
    )
    args = parser.parse_args(argv)

    try:
        result = asyncio.run(
            select_candidates(
                vps_ip=args.ip,
                count=args.count,
                region=args.region,
            )
        )
    except ASNLookupError as exc:
        print(f"error: could not determine VPS ASN: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))

    # exit 1 if zero candidates survived; makes shell pipelines catch
    # "tool ran but nothing to use" as distinct from tool crashing.
    return 0 if result.candidates else 1


if __name__ == "__main__":
    raise SystemExit(main())
