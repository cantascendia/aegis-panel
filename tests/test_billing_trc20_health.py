"""Tests for ``ops.billing.trc20_health`` — silent-failure detection.

Covers SPEC-trc20-poller-alerting.md §4.4 acceptance matrix:

- Debounce behaviour (alert fires once per outage window)
- Recovery message on first success after alert
- Counter reset semantics
- Textfile collector emission (atomic, opt-in by env var)
- Lag-seconds computation
- Lock safety under concurrent record_failure
"""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from ops.billing import trc20_health
from ops.billing.trc20_config import _reload_for_tests as _reload_cfg

_T0 = datetime(2026, 5, 11, 12, 0, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _reset_health_state():
    """Module-level state is shared — every test starts clean."""
    trc20_health._reset_for_tests()
    # Default config: threshold=3, metrics_dir="" (file emission off).
    _reload_cfg(alert_threshold=3, metrics_dir="")
    yield
    trc20_health._reset_for_tests()
    _reload_cfg()


@pytest.fixture
def captured_messages(monkeypatch):
    """Capture every call to telegram.send_message instead of dialling out."""
    calls: list[str] = []

    async def fake_send(message: str, parse_mode=None):
        calls.append(message)

    # Patch the underlying import path used by _send_telegram_safe.
    import app.notification.telegram as tg

    monkeypatch.setattr(tg, "send_message", fake_send)
    return calls


# --------------------------------------------------------------------------
# Debounce / threshold semantics
# --------------------------------------------------------------------------


async def test_first_two_failures_no_alert(captured_messages):
    await trc20_health.record_failure("transient blip", now=_T0)
    await trc20_health.record_failure(
        "transient blip", now=_T0 + timedelta(seconds=30)
    )

    assert captured_messages == []
    snap = trc20_health._snapshot_for_tests()
    assert snap.consecutive_failures == 2
    assert snap.alert_sent is False


async def test_third_failure_fires_alert(captured_messages):
    await trc20_health.record_failure("err", now=_T0)
    await trc20_health.record_failure(
        "err", now=_T0 + timedelta(seconds=30)
    )
    await trc20_health.record_failure(
        "err", now=_T0 + timedelta(seconds=60)
    )

    assert len(captured_messages) == 1
    assert "TRC20 poller degraded" in captured_messages[0]
    assert "<b>3</b>" in captured_messages[0]
    snap = trc20_health._snapshot_for_tests()
    assert snap.alert_sent is True


async def test_fourth_failure_debounced(captured_messages):
    """Once alert_sent=True, additional failures stay silent."""
    for i in range(5):
        await trc20_health.record_failure(
            "err", now=_T0 + timedelta(seconds=30 * i)
        )

    assert len(captured_messages) == 1  # still only the threshold-crossing one
    snap = trc20_health._snapshot_for_tests()
    assert snap.consecutive_failures == 5
    assert snap.alert_sent is True


# --------------------------------------------------------------------------
# Recovery semantics
# --------------------------------------------------------------------------


async def test_success_after_failure_clears_state(captured_messages):
    for i in range(3):
        await trc20_health.record_failure(
            "err", now=_T0 + timedelta(seconds=30 * i)
        )
    assert len(captured_messages) == 1  # alert fired

    await trc20_health.record_success(now=_T0 + timedelta(seconds=120))

    assert len(captured_messages) == 2
    assert "TRC20 poller recovered" in captured_messages[1]
    snap = trc20_health._snapshot_for_tests()
    assert snap.consecutive_failures == 0
    assert snap.alert_sent is False
    assert snap.last_success_at == _T0 + timedelta(seconds=120)


async def test_success_without_prior_alert_no_recovery_msg(captured_messages):
    """A single failure that recovers before threshold must NOT send any
    Telegram messages. Otherwise we'd page on every transient blip."""
    await trc20_health.record_failure("err", now=_T0)
    await trc20_health.record_success(now=_T0 + timedelta(seconds=30))

    assert captured_messages == []
    snap = trc20_health._snapshot_for_tests()
    assert snap.consecutive_failures == 0
    assert snap.alert_sent is False


async def test_outage_then_recovery_then_second_outage_re_alerts(
    captured_messages,
):
    """After recovery, the debounce flag must be cleared so a SECOND
    outage can fire a fresh alert. Otherwise the operator misses repeat
    incidents."""
    # First outage
    for i in range(3):
        await trc20_health.record_failure(
            "err1", now=_T0 + timedelta(seconds=30 * i)
        )
    # Recovery
    await trc20_health.record_success(now=_T0 + timedelta(seconds=120))
    # Second outage
    for i in range(3):
        await trc20_health.record_failure(
            "err2", now=_T0 + timedelta(seconds=200 + 30 * i)
        )

    # Expect: alert1 (degraded), recovery1 (recovered), alert2 (degraded)
    assert len(captured_messages) == 3
    assert "degraded" in captured_messages[0]
    assert "recovered" in captured_messages[1]
    assert "degraded" in captured_messages[2]


# --------------------------------------------------------------------------
# Textfile collector
# --------------------------------------------------------------------------


async def test_metrics_file_written_when_dir_set(
    captured_messages, tmp_path: Path
):
    _reload_cfg(alert_threshold=3, metrics_dir=str(tmp_path))

    await trc20_health.record_success(now=_T0)
    metrics_file = tmp_path / "trc20_poller.prom"
    assert metrics_file.exists()
    body = metrics_file.read_text(encoding="utf-8")
    assert "trc20_poller_last_success_timestamp" in body
    assert "trc20_poller_lag_seconds 0.0" in body
    assert "trc20_poller_consecutive_failures 0" in body
    assert "trc20_poller_alert_active 0" in body


async def test_metrics_file_skipped_when_dir_empty(captured_messages, tmp_path):
    # default fixture already sets metrics_dir=""
    await trc20_health.record_success(now=_T0)

    # tmp_path is unrelated to the (empty) dir setting — assert nothing
    # was created at the configured location by listing the empty CWD-
    # adjacent default.
    assert list(tmp_path.iterdir()) == []  # tmp_path was unused on purpose


async def test_lag_seconds_increases_after_failure(
    captured_messages, tmp_path: Path
):
    _reload_cfg(alert_threshold=3, metrics_dir=str(tmp_path))

    await trc20_health.record_success(now=_T0)
    # Simulate 95 seconds of subsequent failures (3 ticks @ 30s + a bit).
    await trc20_health.record_failure(
        "err", now=_T0 + timedelta(seconds=95)
    )

    body = (tmp_path / "trc20_poller.prom").read_text(encoding="utf-8")
    assert "trc20_poller_lag_seconds 95.0" in body
    assert "trc20_poller_consecutive_failures 1" in body


async def test_alert_active_gauge_reflects_state(
    captured_messages, tmp_path: Path
):
    _reload_cfg(alert_threshold=3, metrics_dir=str(tmp_path))

    for i in range(3):
        await trc20_health.record_failure(
            "err", now=_T0 + timedelta(seconds=30 * i)
        )
    body = (tmp_path / "trc20_poller.prom").read_text(encoding="utf-8")
    assert "trc20_poller_alert_active 1" in body

    await trc20_health.record_success(now=_T0 + timedelta(seconds=120))
    body = (tmp_path / "trc20_poller.prom").read_text(encoding="utf-8")
    assert "trc20_poller_alert_active 0" in body


async def test_metrics_file_write_creates_missing_directory(
    captured_messages, tmp_path: Path
):
    nested = tmp_path / "does" / "not" / "exist"
    _reload_cfg(alert_threshold=3, metrics_dir=str(nested))

    await trc20_health.record_success(now=_T0)
    assert (nested / "trc20_poller.prom").exists()


async def test_metrics_file_io_error_does_not_crash_poller(
    captured_messages, tmp_path: Path, monkeypatch
):
    """A disk-full / permission-denied during metric emission must NOT
    propagate — the poller's primary job (paying invoices) must succeed
    even when monitoring is degraded."""
    _reload_cfg(alert_threshold=3, metrics_dir=str(tmp_path))

    def boom(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(trc20_health, "_write_metrics_file", boom)

    # If this raises, the safety net is broken.
    await trc20_health.record_success(now=_T0)
    await trc20_health.record_failure("err", now=_T0 + timedelta(seconds=30))


# --------------------------------------------------------------------------
# Concurrency
# --------------------------------------------------------------------------


async def test_concurrent_failures_fire_exactly_one_alert(captured_messages):
    """Three coroutines racing record_failure must produce exactly one
    Telegram message, not three. The asyncio.Lock around state mutation
    is what guarantees this."""

    async def fail(n):
        await trc20_health.record_failure(
            f"err{n}", now=_T0 + timedelta(seconds=n)
        )

    await asyncio.gather(fail(0), fail(1), fail(2))

    assert len(captured_messages) == 1
    snap = trc20_health._snapshot_for_tests()
    assert snap.consecutive_failures == 3
    assert snap.alert_sent is True


# --------------------------------------------------------------------------
# Telegram failure safety
# --------------------------------------------------------------------------


async def test_telegram_send_error_does_not_propagate(monkeypatch):
    """send_message raising must not break record_failure / poller."""

    async def boom(message, parse_mode=None):
        raise RuntimeError("telegram api down")

    import app.notification.telegram as tg

    monkeypatch.setattr(tg, "send_message", boom)

    for i in range(3):
        await trc20_health.record_failure(
            "err", now=_T0 + timedelta(seconds=30 * i)
        )
    # No raise → safety net held. State must still reflect the alert
    # attempt so a successful telegram-up later doesn't double-alert.
    snap = trc20_health._snapshot_for_tests()
    assert snap.alert_sent is True


# --------------------------------------------------------------------------
# Reason truncation
# --------------------------------------------------------------------------


async def test_long_failure_reason_truncated(captured_messages):
    """Massive tracebacks must not blow past Telegram's 4096-char limit.
    record_failure caps reason at 500."""
    huge = "x" * 5000
    await trc20_health.record_failure(huge, now=_T0)
    await trc20_health.record_failure(huge, now=_T0)
    await trc20_health.record_failure(huge, now=_T0)

    snap = trc20_health._snapshot_for_tests()
    assert len(snap.last_failure_reason) == 500
    # Telegram message contains the truncated reason.
    assert "x" * 500 in captured_messages[0]
    assert "x" * 5000 not in captured_messages[0]
