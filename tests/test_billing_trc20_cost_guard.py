"""Tests for ``ops.billing.trc20_cost_guard.TronscanCostGuard``.

All tests run entirely in-process; no network calls, no real HTTP.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from ops.billing.trc20_client import Trc20ClientError
from ops.billing.trc20_cost_guard import TronscanCostGuard


def _now() -> datetime:
    return datetime.now(UTC)


def _run(coro):
    return asyncio.run(coro)


# --------------------------------------------------------------------------
# Basic counting
# --------------------------------------------------------------------------


def test_under_cap_no_error() -> None:
    """199 calls inside cap → all succeed, no exception."""
    guard = TronscanCostGuard(max_calls_per_hour=200)

    async def _go():
        now = _now()
        for i in range(199):
            # Advance timestamps by 1 ms each to keep them within 1 hour
            ts = now + timedelta(milliseconds=i)
            await guard.record_call(now=ts)
        return guard.calls_in_window(
            timedelta(hours=1), now=now + timedelta(milliseconds=198)
        )

    count = _run(_go())
    assert count == 199


def test_over_cap_raises_immediately() -> None:
    """200th call at cap → raises Trc20ClientError; call NOT recorded."""
    guard = TronscanCostGuard(max_calls_per_hour=5)

    async def _go():
        now = _now()
        for i in range(5):
            await guard.record_call(now=now + timedelta(milliseconds=i))
        # 6th call should raise
        with pytest.raises(Trc20ClientError, match="cost guard"):
            await guard.record_call(now=now + timedelta(milliseconds=5))
        # Deque should still be 5, not 6
        return guard.calls_in_window(
            timedelta(hours=1), now=now + timedelta(milliseconds=5)
        )

    count = _run(_go())
    assert count == 5


def test_cap_zero_disables_guard() -> None:
    """max_calls_per_hour=0 means no cap — 500 calls all succeed."""
    guard = TronscanCostGuard(max_calls_per_hour=0)

    async def _go():
        now = _now()
        for i in range(500):
            await guard.record_call(now=now + timedelta(seconds=i))

    _run(_go())  # must not raise


# --------------------------------------------------------------------------
# Sliding window
# --------------------------------------------------------------------------


def test_sliding_window_drops_old_calls() -> None:
    """Calls older than 1 h are evicted from the window count."""
    guard = TronscanCostGuard(max_calls_per_hour=200)

    async def _go():
        base = _now()
        # Record 10 calls 2 hours ago
        for i in range(10):
            old_ts = base - timedelta(hours=2) + timedelta(milliseconds=i)
            await guard.record_call(now=old_ts)
        # Record 3 recent calls
        for i in range(3):
            await guard.record_call(now=base + timedelta(seconds=i))
        return guard.calls_in_window(
            timedelta(hours=1), now=base + timedelta(seconds=2)
        )

    count = _run(_go())
    assert count == 3


def test_window_buckets_independent() -> None:
    """1 h and 24 h windows return distinct values."""
    guard = TronscanCostGuard(max_calls_per_hour=200)

    async def _go():
        base = _now()
        # 5 calls 2 h ago (inside 24 h, outside 1 h)
        for i in range(5):
            await guard.record_call(
                now=base - timedelta(hours=2) + timedelta(milliseconds=i)
            )
        # 3 calls now (inside both windows)
        for i in range(3):
            await guard.record_call(now=base + timedelta(seconds=i))
        return (
            guard.calls_in_window(
                timedelta(hours=1), now=base + timedelta(seconds=2)
            ),
            guard.calls_in_window(
                timedelta(hours=24), now=base + timedelta(seconds=2)
            ),
        )

    count_1h, count_24h = _run(_go())
    assert count_1h == 3
    assert count_24h == 8


def test_eviction_prevents_unbounded_growth() -> None:
    """After 48 h gap, the deque is cleared by eviction."""
    guard = TronscanCostGuard(max_calls_per_hour=10_000)

    async def _go():
        base = _now()
        # Fill 500 calls 30 h ago
        for i in range(500):
            await guard.record_call(
                now=base - timedelta(hours=30) + timedelta(milliseconds=i)
            )
        # One call now
        await guard.record_call(now=base)
        return len(guard._calls)

    size = _run(_go())
    # All old calls should have been evicted (they are >24 h old)
    assert size == 1


# --------------------------------------------------------------------------
# emit_metrics
# --------------------------------------------------------------------------


def test_emit_metrics_shape() -> None:
    """emit_metrics returns both '1h' and '24h' keys with correct counts."""
    guard = TronscanCostGuard(max_calls_per_hour=200)

    async def _go():
        base = _now()
        # 2 calls 2 h ago
        for i in range(2):
            await guard.record_call(
                now=base - timedelta(hours=2) + timedelta(milliseconds=i)
            )
        # 7 calls now
        for i in range(7):
            await guard.record_call(now=base + timedelta(seconds=i))
        return guard.emit_metrics(now=base + timedelta(seconds=6))

    metrics = _run(_go())
    assert set(metrics.keys()) == {"calls_1h", "calls_24h"}
    assert metrics["calls_1h"] == 7
    assert metrics["calls_24h"] == 9


# --------------------------------------------------------------------------
# Concurrency
# --------------------------------------------------------------------------


def test_concurrent_record_call_lock_safe() -> None:
    """Concurrent record_call calls respect the lock; no lost counts."""
    guard = TronscanCostGuard(max_calls_per_hour=1_000)

    async def _go():
        base = _now()
        # Fire 50 concurrent calls
        tasks = [
            guard.record_call(now=base + timedelta(milliseconds=i))
            for i in range(50)
        ]
        await asyncio.gather(*tasks)
        return guard.calls_in_window(
            timedelta(hours=1), now=base + timedelta(milliseconds=49)
        )

    count = _run(_go())
    assert count == 50
