"""TRC20 poller health tracker — silent-failure detection + alerting.

Plugged into :mod:`ops.billing.trc20_poller` to address the
reliability-auditor 2026-05-11 P0 finding: the poller has 8 try/except
+ 6 logger.* calls but **no alerting outlet**. Tronscan persistent
failure used to surface only as repeated WARN log lines that nobody
reads — customers paid USDT, on-chain confirmed, panel never flipped
``awaiting_payment → paid``, refund disputes followed.

Design contract (SPEC-trc20-poller-alerting.md)
-----------------------------------------------
- **Module-level state**, single process, no DB schema migration. Restart
  clears state — restart is already an ops-intervention signal.
- **Telegram out-bound** via existing ``app.notification.telegram.send_message``;
  no new dependency. Operator already subscribes to that channel.
- **Debounced**: alert fires exactly once per outage window. Subsequent
  failures are silent until a success resets the counter; a recovery
  message then fires on the next success.
- **Textfile collector metric** (optional) — atomic write to
  ``BILLING_TRC20_METRICS_DIR / trc20_poller.prom`` for node_exporter
  ``--collector.textfile.directory`` to scrape. Off-by-default so a fresh
  deploy without monitoring wired pays no cost.
- **Lock-protected**: async lock around state mutations means two
  concurrent ``record_failure`` calls don't double-fire the alert.
- **Crash-safe**: any internal exception in the alert / metrics path is
  caught and logged — the poller's primary work must never fail because
  the health tracker did.

Why not a DB column for ``last_success_at``
-------------------------------------------
- Schema migration touches ``app/db/extra_models.py`` aggregator (L-014)
  and Alembic, widening forbidden-path blast radius for what is
  fundamentally a transient observability state.
- Restart is already an operator action; losing 30 s of in-memory state
  at that boundary is acceptable.
- If we ever want persistence (e.g. multi-process panels), the textfile
  metric IS the persistence — Prometheus retains history.
"""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# State
# --------------------------------------------------------------------------


@dataclass
class _HealthState:
    consecutive_failures: int = 0
    alert_sent: bool = False
    last_success_at: Optional[datetime] = None
    last_failure_at: Optional[datetime] = None
    last_failure_reason: str = ""


_state: _HealthState = _HealthState()
_lock: asyncio.Lock = asyncio.Lock()


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------


async def record_success(*, now: Optional[datetime] = None) -> None:
    """Called by the poller after a clean Tronscan fetch.

    Side effects (in order):

    1. If an alert had previously been sent (i.e. we're recovering),
       fire a recovery Telegram message exactly once.
    2. Reset ``consecutive_failures`` and ``alert_sent``.
    3. Update ``last_success_at``.
    4. Snapshot the textfile metric.
    """
    now = now or _now_utc()
    async with _lock:
        was_alerting = _state.alert_sent
        prior_failures = _state.consecutive_failures

        _state.consecutive_failures = 0
        _state.alert_sent = False
        _state.last_success_at = now

        if was_alerting:
            await _send_telegram_safe(
                _format_recovery_message(now, prior_failures)
            )

        _write_metrics_file_safe(now)


async def record_failure(
    reason: str, *, now: Optional[datetime] = None
) -> None:
    """Called by the poller when ``Trc20ClientError`` was raised.

    Side effects (in order):

    1. Increment ``consecutive_failures``; stamp ``last_failure_*``.
    2. If counter hits ``BILLING_TRC20_ALERT_THRESHOLD`` AND
       ``alert_sent`` is False → fire one Telegram alert and set
       ``alert_sent=True``.
    3. Snapshot the textfile metric.

    The debounce flag is reset only by :func:`record_success`. This is
    the contract that prevents a long Tronscan outage from spamming
    operators with one alert per 30 s tick.
    """
    now = now or _now_utc()
    # Truncate reason; Telegram messages have a 4096-char limit and we
    # don't want an exception traceback to blow past it.
    reason = (reason or "")[:500]

    async with _lock:
        _state.consecutive_failures += 1
        _state.last_failure_at = now
        _state.last_failure_reason = reason

        # Re-read threshold each call so test ``_reload_for_tests`` is
        # honoured without re-importing.
        from ops.billing.trc20_config import BILLING_TRC20_ALERT_THRESHOLD

        should_alert = (
            _state.consecutive_failures >= BILLING_TRC20_ALERT_THRESHOLD
            and not _state.alert_sent
        )
        if should_alert:
            _state.alert_sent = True
            await _send_telegram_safe(
                _format_failure_message(
                    now, _state.consecutive_failures, reason
                )
            )

        _write_metrics_file_safe(now)


# --------------------------------------------------------------------------
# Message formatting
# --------------------------------------------------------------------------


def _format_failure_message(
    now: datetime, consecutive: int, reason: str
) -> str:
    return (
        "🔴 <b>TRC20 poller degraded</b>\n"
        f"Consecutive Tronscan failures: <b>{consecutive}</b>\n"
        f"Last error: <code>{_html_escape(reason)}</code>\n"
        f"Detected at: {now.isoformat(timespec='seconds')}\n"
        "\n"
        "Customers paying via USDT may not get their grants applied "
        "until this recovers. Check OPS-trc20-runbook.md §6.1."
    )


def _format_recovery_message(now: datetime, prior_failures: int) -> str:
    return (
        "🟢 <b>TRC20 poller recovered</b>\n"
        f"Tronscan reachable again after {prior_failures} consecutive "
        "failed ticks.\n"
        f"Recovered at: {now.isoformat(timespec='seconds')}"
    )


def _html_escape(s: str) -> str:
    # Minimal HTML escape; Telegram parse_mode=HTML chokes on raw <>&.
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# --------------------------------------------------------------------------
# Telegram outlet (with safety net)
# --------------------------------------------------------------------------


async def _send_telegram_safe(message: str) -> None:
    """Call Telegram bot send_message; absorb any exception.

    The poller's primary contract is "mark paid invoices paid". A flaky
    Telegram outage must not crash the tick.
    """
    try:
        from app.notification.telegram import send_message

        await send_message(message)
    except Exception:  # pragma: no cover — defensive
        logger.exception(
            "trc20 health: telegram alert send failed (state still tracked)"
        )


# --------------------------------------------------------------------------
# Textfile collector
# --------------------------------------------------------------------------


_METRICS_FILENAME = "trc20_poller.prom"


def _write_metrics_file_safe(now: datetime) -> None:
    """Write the current health snapshot to the prom-textfile path.

    No-op if ``BILLING_TRC20_METRICS_DIR`` is unset / empty. Any I/O
    error is logged but never propagated.
    """
    from ops.billing.trc20_config import BILLING_TRC20_METRICS_DIR

    if not BILLING_TRC20_METRICS_DIR:
        return
    try:
        _write_metrics_file(BILLING_TRC20_METRICS_DIR, now)
    except Exception:  # pragma: no cover — defensive
        logger.exception(
            "trc20 health: failed to write metrics file to %s",
            BILLING_TRC20_METRICS_DIR,
        )


def _write_metrics_file(directory: str, now: datetime) -> None:
    """Atomic write: tmp file in same dir + os.replace.

    The node_exporter textfile collector reads files mid-write at its
    own scrape cadence; an atomic rename guarantees readers see either
    the old snapshot or the new one, never a partial one.
    """
    os.makedirs(directory, exist_ok=True)

    last_success_ts = (
        _state.last_success_at.timestamp() if _state.last_success_at else 0.0
    )
    if _state.last_success_at:
        lag_seconds = max(0.0, (now - _state.last_success_at).total_seconds())
    else:
        lag_seconds = 0.0

    body = (
        "# HELP trc20_poller_last_success_timestamp "
        "Unix epoch of last successful Tronscan fetch.\n"
        "# TYPE trc20_poller_last_success_timestamp gauge\n"
        f"trc20_poller_last_success_timestamp {last_success_ts:.1f}\n"
        "# HELP trc20_poller_lag_seconds "
        "Seconds since last successful poll.\n"
        "# TYPE trc20_poller_lag_seconds gauge\n"
        f"trc20_poller_lag_seconds {lag_seconds:.1f}\n"
        "# HELP trc20_poller_consecutive_failures "
        "Number of consecutive Tronscan failures.\n"
        "# TYPE trc20_poller_consecutive_failures gauge\n"
        f"trc20_poller_consecutive_failures {_state.consecutive_failures}\n"
        "# HELP trc20_poller_alert_active "
        "1 if a Telegram alert has been fired and not yet recovered.\n"
        "# TYPE trc20_poller_alert_active gauge\n"
        f"trc20_poller_alert_active {1 if _state.alert_sent else 0}\n"
    )

    target = os.path.join(directory, _METRICS_FILENAME)
    # NamedTemporaryFile in the SAME dir → os.replace is atomic across
    # files only when both are on the same filesystem.
    fd, tmp_path = tempfile.mkstemp(
        prefix=".trc20_poller.", suffix=".prom.tmp", dir=directory
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(body)
        os.replace(tmp_path, target)
    except Exception:
        # Clean tmp leftover on failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# --------------------------------------------------------------------------
# Test hooks
# --------------------------------------------------------------------------


def _reset_for_tests() -> None:
    """Reset module state. Tests use this in an autouse fixture."""
    global _state, _lock
    _state = _HealthState()
    _lock = asyncio.Lock()


def _snapshot_for_tests() -> _HealthState:
    """Return a defensive copy of the state — tests can read without
    accidentally mutating."""
    return _HealthState(
        consecutive_failures=_state.consecutive_failures,
        alert_sent=_state.alert_sent,
        last_success_at=_state.last_success_at,
        last_failure_at=_state.last_failure_at,
        last_failure_reason=_state.last_failure_reason,
    )


__all__ = [
    "record_failure",
    "record_success",
]
