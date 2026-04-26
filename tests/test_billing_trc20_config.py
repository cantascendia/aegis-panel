"""
Tests for ``ops.billing.trc20_config`` — env-driven provider factory.

Use ``_reload_for_tests`` to isolate state between cases (the
``lru_cache`` on ``get_trc20_provider`` would otherwise leak between
tests).
"""

from __future__ import annotations

import pytest

from ops.billing.providers import get_provider
from ops.billing.providers.trc20 import Trc20Provider
from ops.billing.trc20_config import (
    Trc20Misconfigured,
    _reload_for_tests,
    get_trc20_provider,
)


@pytest.fixture(autouse=True)
def _reset_state():
    """Always start with the provider disabled so leaks between tests
    surface as a ``Trc20Misconfigured`` rather than silent wiring."""
    _reload_for_tests(enabled=False)
    yield
    _reload_for_tests(enabled=False)


def test_provider_disabled_by_default() -> None:
    with pytest.raises(Trc20Misconfigured, match="not enabled"):
        get_trc20_provider()


def test_provider_enabled_without_address_fails_loud() -> None:
    """``ENABLED=true`` but address missing → fail at instantiation,
    not silently default to a no-op."""
    _reload_for_tests(enabled=True, rate_fen_per_usdt=720, memo_salt="s")
    with pytest.raises(Trc20Misconfigured, match="RECEIVE_ADDRESS"):
        get_trc20_provider()


def test_provider_enabled_without_rate_fails_loud() -> None:
    _reload_for_tests(enabled=True, receive_address="TR-x", memo_salt="s")
    with pytest.raises(Trc20Misconfigured, match="RATE_FEN_PER_USDT"):
        get_trc20_provider()


def test_provider_enabled_without_salt_fails_loud() -> None:
    _reload_for_tests(
        enabled=True, receive_address="TR-x", rate_fen_per_usdt=720
    )
    with pytest.raises(Trc20Misconfigured, match="MEMO_SALT"):
        get_trc20_provider()


def test_provider_fully_configured_returns_provider() -> None:
    _reload_for_tests(
        enabled=True,
        receive_address="TR-x",
        rate_fen_per_usdt=720,
        memo_salt="op-salt",
    )
    p = get_trc20_provider()
    assert isinstance(p, Trc20Provider)
    assert p.receive_address == "TR-x"
    assert p.rate_fen_per_usdt == 720


def test_provider_factory_caches_singleton() -> None:
    _reload_for_tests(
        enabled=True,
        receive_address="TR-x",
        rate_fen_per_usdt=720,
        memo_salt="s",
    )
    a = get_trc20_provider()
    b = get_trc20_provider()
    assert a is b


def test_get_provider_kind_trc20_routes_to_factory() -> None:
    """``get_provider("trc20")`` from the public registry must
    delegate to the env-driven singleton, ignoring channel arg."""
    _reload_for_tests(
        enabled=True,
        receive_address="TR-x",
        rate_fen_per_usdt=720,
        memo_salt="s",
    )
    p = get_provider("trc20")
    assert isinstance(p, Trc20Provider)


def test_get_provider_kind_trc20_disabled_raises() -> None:
    """When TRC20 not enabled, ``get_provider("trc20")`` surfaces
    the misconfiguration loudly to the caller (checkout / scheduler)."""
    with pytest.raises(Trc20Misconfigured):
        get_provider("trc20")
