"""Per-process TRC20 API call counter with sliding-window cost cap.

Design (SPEC-trc20-client-resilience.md §4.1)
----------------------------------------------
The Tronscan public endpoint allows ~100 req/s (360 000/h), but a
misconfig (``POLL_INTERVAL=1s``) or a forgotten mock in tests can
silently exhaust that quota and trigger an IP ban. This module provides
a cheap in-process guard:

- **Sliding window** — a :class:`collections.deque` of call timestamps
  (UTC). Each :meth:`TronscanCostGuard.record_call` evicts timestamps
  older than 1 hour, then checks the remaining count against the cap.
- **Soft cap default = 200/h** — leaves a 1 800× headroom over normal
  production traffic (~120/h at 30-s poll) while catching obvious
  misconfiguration early enough to generate an alert before the IP is
  actually banned.
- **asyncio.Lock** — safe for concurrent ticks in a single event loop.
  Not inter-process (each worker process gets its own counter); that is
  intentional — per-process independence avoids distributed state while
  still catching the most common failure mode (single-process misconfig).
- **Metrics** — :meth:`emit_metrics` returns a dict suitable for
  inclusion in the Prometheus textfile snapshot written by
  ``ops.billing.trc20_health``.

The guard is **not** a rate limiter (it does not sleep); it raises
:class:`ops.billing.trc20_client.Trc20ClientError` so the existing
poller error path (log + skip tick) handles it identically to a network
failure.
"""

from __future__ import annotations

import asyncio
import collections
import logging
from datetime import UTC, datetime, timedelta

logger = logging.getLogger(__name__)

_ONE_HOUR = timedelta(hours=1)
_ONE_DAY = timedelta(hours=24)


class TronscanCostGuard:
    """Sliding-window call counter with a soft hourly cap.

    Constructed once per :class:`~ops.billing.trc20_client.TronscanClient`
    instance (the client owns one guard).  Tests can inject a custom
    instance with ``max_calls_per_hour=0`` to disable the guard, or with
    a low threshold to test cap behaviour without spinning 200 calls.

    Args:
        max_calls_per_hour: Raise an error if this many calls are recorded
            in any rolling 1-hour window.  0 means "no cap" (test helper).
    """

    def __init__(self, *, max_calls_per_hour: int = 200) -> None:
        self._max = max_calls_per_hour
        # Timestamps of outbound API calls, oldest-first.
        self._calls: collections.deque[datetime] = collections.deque()
        self._lock: asyncio.Lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def record_call(self, *, now: datetime | None = None) -> None:
        """Record one outbound API call.

        Must be awaited **before** the HTTP request is dispatched.  If
        the hourly cap would be exceeded, raises
        :class:`~ops.billing.trc20_client.Trc20ClientError` without
        recording the call (so the cap count stays accurate).

        Args:
            now: Override for the current time; used in unit tests.

        Raises:
            Trc20ClientError: When ``max_calls_per_hour > 0`` and the
                sliding-window count equals or exceeds the cap.
        """
        # Lazy import to avoid circular: trc20_client imports this module
        # and Trc20ClientError lives in trc20_client.
        from ops.billing.trc20_client import Trc20ClientError

        now = now or datetime.now(UTC)
        async with self._lock:
            self._evict(now)
            count_1h = self.calls_in_window(_ONE_HOUR, now=now)
            if self._max > 0 and count_1h >= self._max:
                msg = (
                    f"TRC20 cost guard: {count_1h} calls in last 1 h "
                    f"(cap={self._max}). Skipping this tick. Check "
                    "BILLING_TRC20_POLL_INTERVAL or BILLING_TRC20_MAX_CALLS_PER_HOUR."
                )
                logger.error(msg)
                raise Trc20ClientError(msg)
            self._calls.append(now)

    def calls_in_window(
        self, window: timedelta, *, now: datetime | None = None
    ) -> int:
        """Count recorded calls that fall within ``window`` ending at ``now``.

        Thread-safe for reading without the lock because the deque is
        written only inside the locked path of :meth:`record_call`.

        Args:
            window: How far back to count (e.g. ``timedelta(hours=1)``).
            now: Override for the current time; used in unit tests.
        """
        now = now or datetime.now(UTC)
        cutoff = now - window
        return sum(1 for ts in self._calls if ts >= cutoff)

    def emit_metrics(self, *, now: datetime | None = None) -> dict[str, int]:
        """Return current window counts as a plain dict.

        Keys match the Prometheus gauge names emitted by
        ``ops.billing.trc20_health._write_metrics_file``.

        Returns:
            ``{"calls_1h": N, "calls_24h": N}``
        """
        now = now or datetime.now(UTC)
        return {
            "calls_1h": self.calls_in_window(_ONE_HOUR, now=now),
            "calls_24h": self.calls_in_window(_ONE_DAY, now=now),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _evict(self, now: datetime) -> None:
        """Remove timestamps older than 24 h (the longest window we track).

        Called inside the lock before every :meth:`record_call` so the
        deque never grows unboundedly even if the process runs for days.
        """
        cutoff = now - _ONE_DAY
        while self._calls and self._calls[0] < cutoff:
            self._calls.popleft()


__all__ = ["TronscanCostGuard"]
