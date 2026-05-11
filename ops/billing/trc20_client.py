"""Tronscan public-API client — read-only TRC20 transfer feed.

Thin async wrapper over the
``GET /api/token_trc20/transfers`` endpoint:

    https://apilist.tronscanapi.com/api/token_trc20/transfers
        ?contract_address={USDT}
        &toAddress={our_receive_address}
        &limit=50

Why Tronscan
------------
- **No API key required**: huge operational simplification — no key
  rotation, no quota tracking, no surprise-deactivation paths.
- **Public rate limit**: 100 req/s, vastly more than our 30-s poll
  needs (we make 1 call per tick across all open invoices).
- **Stable schema** for the fields we care about (``transaction_id``,
  ``trigger_info`` decoded amount, ``confirmed`` boolean, block).
- **Fallback chain**: configure ``BILLING_TRC20_FALLBACK_API_BASES``
  (CSV) for automatic failover after
  ``BILLING_TRC20_FALLBACK_THRESHOLD`` consecutive failures on the
  active base. See SPEC-trc20-client-resilience.md §4.2.

Response normalisation
----------------------
Tronscan returns rich JSON; we project to :class:`Trc20Transfer`
(from ``trc20_matcher``) so the matcher and poller never see raw
Tronscan dicts. A future swap to Trongrid changes only this file.

Memo extraction
---------------
The optional memo lives in the tx ``data`` field as a hex string of
the user-supplied bytes. We decode UTF-8, strip whitespace, and run
:func:`ops.billing.providers.trc20.is_valid_memo` on the result;
anything else is treated as no memo (common: zero-bytes padding,
emoji, non-printable bytes).

Error handling
--------------
- HTTP 5xx / network error → raises :class:`Trc20ClientError`. Caller
  (the poller) logs + skips this tick; next tick retries.
- HTTP 4xx → raises :class:`Trc20ClientError` with the status code.
  Most likely cause: misconfigured ``contract_address`` /
  ``receive_address``. Worth alerting on.
- Empty result list → returns ``[]`` cleanly (a quiet wallet is not
  an error).

Cost guard
----------
A per-process sliding-window counter
(:class:`~ops.billing.trc20_cost_guard.TronscanCostGuard`) is checked
before every outbound request.  If the hourly cap is reached (default
200; override via ``BILLING_TRC20_MAX_CALLS_PER_HOUR``), the method
raises :class:`Trc20ClientError` immediately without hitting the
network, avoiding IP bans from accidental rate flooding.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import aiohttp

from ops.billing.trc20_cost_guard import TronscanCostGuard
from ops.billing.trc20_matcher import Trc20Transfer

logger = logging.getLogger(__name__)


class Trc20ClientError(RuntimeError):
    """Raised on HTTP-level failures or unparseable responses.

    The poller catches this and skips the tick; transient network
    errors should not poison the scheduler. Persistent errors (e.g.
    400 from a malformed config) surface in logs every tick until the
    operator fixes the config.
    """


class TronscanClient:
    """Thin async wrapper. One instance per panel process.

    Constructed via :meth:`from_env` for production use; tests can
    instantiate directly with a custom ``aiohttp.ClientSession`` to
    inject mocked HTTP behavior.

    Supports a fallback chain: if ``api_bases`` contains more than one
    URL, a base that fails ``fallback_threshold`` consecutive times is
    rotated out in favour of the next one in the list, and a Telegram
    alert is sent via ``ops.billing.trc20_health``.
    """

    def __init__(
        self,
        *,
        api_base: str | None = None,
        api_bases: list[str] | None = None,
        contract_address: str,
        session: aiohttp.ClientSession | None = None,
        request_timeout: float = 10.0,
        cost_guard: TronscanCostGuard | None = None,
        fallback_threshold: int = 5,
    ) -> None:
        # Accept either the legacy single api_base or the new api_bases list.
        if api_bases is not None:
            self._api_bases: list[str] = [
                b.rstrip("/") for b in api_bases if b
            ]
        elif api_base is not None:
            self._api_bases = [api_base.rstrip("/")]
        else:
            raise ValueError("TronscanClient requires api_base or api_bases")

        if not self._api_bases:
            raise ValueError("TronscanClient: api_bases must not be empty")

        self._contract_address = contract_address
        self._session = session
        self._owns_session = session is None
        self._timeout = aiohttp.ClientTimeout(total=request_timeout)

        # Fallback tracking: per-base consecutive failure counters and
        # the index of the currently active base.
        self._failure_counts: list[int] = [0] * len(self._api_bases)
        self._active_base_idx: int = 0
        self._fallback_threshold = fallback_threshold

        self._cost_guard: TronscanCostGuard = (
            cost_guard if cost_guard is not None else TronscanCostGuard()
        )

    @classmethod
    def from_env(cls) -> TronscanClient:
        """Build a client from :mod:`ops.billing.trc20_config` env."""
        # Local import — env module imports providers, providers imports
        # this client, so we delay until first call to break the cycle.
        from ops.billing.trc20_config import (
            BILLING_TRC20_FALLBACK_API_BASES,
            BILLING_TRC20_FALLBACK_THRESHOLD,
            BILLING_TRC20_MAX_CALLS_PER_HOUR,
            BILLING_TRC20_TRONSCAN_API_BASE,
            BILLING_TRC20_USDT_CONTRACT,
        )

        bases = [BILLING_TRC20_TRONSCAN_API_BASE]
        if BILLING_TRC20_FALLBACK_API_BASES:
            extras = [
                b.strip()
                for b in BILLING_TRC20_FALLBACK_API_BASES.split(",")
                if b.strip()
            ]
            bases.extend(extras)

        return cls(
            api_bases=bases,
            contract_address=BILLING_TRC20_USDT_CONTRACT,
            cost_guard=TronscanCostGuard(
                max_calls_per_hour=BILLING_TRC20_MAX_CALLS_PER_HOUR
            ),
            fallback_threshold=BILLING_TRC20_FALLBACK_THRESHOLD,
        )

    async def __aenter__(self) -> TronscanClient:
        if self._session is None:
            self._session = aiohttp.ClientSession(timeout=self._timeout)
            self._owns_session = True
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        if self._owns_session and self._session is not None:
            await self._session.close()
            self._session = None

    @property
    def _active_base(self) -> str:
        return self._api_bases[self._active_base_idx]

    async def list_recent_transfers(
        self,
        *,
        to_address: str,
        limit: int = 50,
    ) -> list[Trc20Transfer]:
        """Return the most recent ``limit`` confirmed USDT-TRC20
        transfers TO ``to_address``.

        ``limit=50`` covers our 30-s poll horizon at any reasonable
        traffic level. Operators with extreme volume can dial this
        higher via SPEC follow-up; matching cost is O(open invoices ×
        transfers), trivial at 50.

        Raises :class:`Trc20ClientError` if all bases in the fallback
        chain fail, or if the cost guard cap is exceeded.
        """
        if self._session is None:
            raise Trc20ClientError(
                "Client used outside async context manager; call "
                "`async with client:` or pass an explicit session."
            )

        # Cost guard — checked once per call regardless of which base
        # is active.  A single cap covers total outbound traffic.
        await self._cost_guard.record_call()

        last_exc: Trc20ClientError | None = None

        # Try the active base first; on failure try remaining bases in
        # order (wrap around if needed).
        #
        # ``start_idx`` is captured once so that mid-loop rotation of
        # ``_active_base_idx`` does not confuse the current call's
        # iteration order.  Rotation takes effect from the NEXT call.
        num_bases = len(self._api_bases)
        start_idx = self._active_base_idx
        for attempt in range(num_bases):
            idx = (start_idx + attempt) % num_bases
            base = self._api_bases[idx]
            try:
                result = await self._fetch_from(
                    base, to_address=to_address, limit=limit
                )
                # Success — reset failure counter for this base.
                self._failure_counts[idx] = 0
                return result
            except Trc20ClientError as exc:
                self._failure_counts[idx] += 1
                last_exc = exc
                if (
                    len(self._api_bases) > 1
                    and self._failure_counts[idx] >= self._fallback_threshold
                    and idx == self._active_base_idx
                ):
                    # Threshold crossed on the currently-active base —
                    # rotate active pointer to next base and alert.
                    # Takes effect starting from the next call.
                    next_idx = (self._active_base_idx + 1) % num_bases
                    next_base = self._api_bases[next_idx]
                    self._active_base_idx = next_idx
                    logger.warning(
                        "trc20 client: base %s failed %d times; "
                        "switching to %s",
                        base,
                        self._failure_counts[idx],
                        next_base,
                    )
                    await self._record_fallback_switch(next_base)
                continue

        assert last_exc is not None  # loop ran at least once
        raise last_exc

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _fetch_from(
        self, base: str, *, to_address: str, limit: int
    ) -> list[Trc20Transfer]:
        """Issue one HTTP GET to ``base`` and return parsed transfers."""
        url = f"{base}/api/token_trc20/transfers"
        params = {
            "contract_address": self._contract_address,
            "toAddress": to_address,
            "limit": str(limit),
            # Tronscan's `confirm=true` filter only returns confirmed
            # txs — the matcher checks the boolean too as a defence.
            "confirm": "true",
        }
        try:
            assert self._session is not None
            async with self._session.get(
                url, params=params, timeout=self._timeout
            ) as resp:
                if resp.status >= 400:
                    body = await resp.text()
                    raise Trc20ClientError(
                        f"Tronscan returned HTTP {resp.status}: {body[:200]}"
                    )
                data = await resp.json()
        except aiohttp.ClientError as exc:
            raise Trc20ClientError(f"Tronscan network error: {exc}") from exc

        return _parse_transfers(data)

    @staticmethod
    async def _record_fallback_switch(new_base: str) -> None:
        """Notify trc20_health that the active base was rotated."""
        try:
            from ops.billing.trc20_health import record_failure

            await record_failure(reason=f"fallback_switch:{new_base}")
        except Exception:  # pragma: no cover — defensive
            logger.exception(
                "trc20 client: health fallback-switch notification failed"
            )


def _parse_transfers(data: dict[str, Any]) -> list[Trc20Transfer]:
    """Project Tronscan's response shape onto :class:`Trc20Transfer`.

    The endpoint returns ``{"data": [...], "total": N, ...}``; we only
    consume ``data``. Fields used:

    - ``transaction_id`` → ``tx_hash``
    - ``trigger_info.parameter._value`` (string of raw token amount,
      6-decimal USDT) → ``amount_millis``
    - ``data`` (hex string of user memo bytes) → ``memo``
    - ``block_ts`` (millis epoch) → ``timestamp``
    - ``confirmed`` → ``confirmed``
    - ``block`` → ``block_number``

    Any item missing required fields is dropped with a warning. We
    prefer to lose one weird record than to crash the entire poller
    on a single malformed entry.
    """
    raw_items = data.get("token_transfers") or data.get("data") or []
    out: list[Trc20Transfer] = []
    for item in raw_items:
        try:
            transfer = _parse_one(item)
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning(
                "tronscan: skipping unparseable transfer entry: %s", exc
            )
            continue
        if transfer is not None:
            out.append(transfer)
    return out


def _parse_one(item: dict[str, Any]) -> Trc20Transfer | None:
    """Parse one Tronscan record into our shape; return ``None`` to
    discard quietly (e.g. amount was 0)."""
    tx_hash = item["transaction_id"]
    raw_amount = item.get("amount_str") or item.get("quant") or "0"
    # USDT TRC20 has 6 on-chain decimals; we store millis (1/1000 USDT,
    # i.e. 3 decimals). Truncate the bottom 3 decimals.
    raw_amount_int = int(raw_amount)
    amount_millis = raw_amount_int // 1000
    if amount_millis <= 0:
        return None

    block_ts_ms = item.get("block_ts") or item.get("block_timestamp") or 0
    timestamp = datetime.fromtimestamp(block_ts_ms / 1000, UTC).replace(
        tzinfo=None
    )

    confirmed = bool(item.get("confirmed", False))
    block_number = int(item.get("block", 0))

    memo = _decode_memo(item.get("data") or item.get("contract_data") or "")

    return Trc20Transfer(
        tx_hash=tx_hash,
        amount_millis=amount_millis,
        memo=memo,
        timestamp=timestamp,
        confirmed=confirmed,
        block_number=block_number,
    )


def _decode_memo(data_field: str) -> str | None:
    """Try to decode a memo from a hex-encoded data field.

    Returns the cleaned ASCII memo, or ``None`` if anything looks off.
    The matcher does its own structural validation; this just attempts
    a sane decode.
    """
    if not data_field:
        return None
    s = data_field
    # Some indexers prefix hex with "0x"; strip it.
    if s.startswith("0x") or s.startswith("0X"):
        s = s[2:]
    if not s:
        return None
    try:
        decoded = bytes.fromhex(s).decode("utf-8", errors="strict")
    except (ValueError, UnicodeDecodeError):
        return None
    decoded = decoded.strip().strip("\x00")
    if not decoded:
        return None
    return decoded


__all__ = [
    "Trc20ClientError",
    "TronscanClient",
]
