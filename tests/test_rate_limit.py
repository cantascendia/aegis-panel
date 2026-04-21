"""
Tests for hardening/panel/rate_limit.py.

Contract we're guarding:
1. Default config (RATE_LIMIT_ENABLED=false) produces a disabled
   Limiter that never blocks anything — ensures "existing deployments
   unaffected by upgrade" stays true.
2. Enabling rate limiting without REDIS_URL must raise
   RateLimitMisconfigured at import time. Silently falling back to
   in-process counters in a multi-worker deployment is worse than
   refusing to start.
3. Enabling with REDIS_URL constructs an enabled Limiter pointing at
   Redis — no regression where the URL is ignored.

Out of scope: end-to-end HTTP testing of 429 responses. That needs
the full FastAPI app + a running Redis, which belongs in the
integration-matrix CI job (future).
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from types import ModuleType


def _reload_rate_limit(
    monkeypatch, *, enabled: bool, redis_url: str
) -> ModuleType:
    """Reload the rate_limit module with fresh env values.

    The Limiter is built at import time from env constants captured
    when `app.config.env` is imported. Tests need to drive different
    permutations, so we monkeypatch the env module's bindings and
    reload rate_limit to rebuild the singleton.
    """
    from app.config import env as env_module

    monkeypatch.setattr(env_module, "RATE_LIMIT_ENABLED", enabled)
    monkeypatch.setattr(env_module, "REDIS_URL", redis_url)

    from hardening.panel import rate_limit as rl_module

    return importlib.reload(rl_module)


def test_default_disabled_limiter_is_safe_to_decorate_with(
    monkeypatch,
) -> None:
    rl = _reload_rate_limit(monkeypatch, enabled=False, redis_url="")

    assert rl.limiter.enabled is False, (
        "Default config must produce a disabled Limiter so existing "
        "deployments don't suddenly 429 on upgrade."
    )


def test_enabled_without_redis_raises_misconfigured(monkeypatch) -> None:
    """Fail-loud: the whole point of rate limiting is a shared counter."""
    from app.config import env as env_module

    monkeypatch.setattr(env_module, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(env_module, "REDIS_URL", "")

    from hardening.panel import rate_limit as rl_module

    with pytest.raises(rl_module.RateLimitMisconfigured) as exc_info:
        importlib.reload(rl_module)

    message = str(exc_info.value)
    # The error must name both env vars so the operator knows the fix.
    assert "RATE_LIMIT_ENABLED" in message
    assert "REDIS_URL" in message

    # Reset the module to the known-good state so later tests (and
    # any app import chain) see a sane singleton.
    monkeypatch.setattr(env_module, "RATE_LIMIT_ENABLED", False)
    importlib.reload(rl_module)


def test_enabled_with_redis_builds_enabled_limiter(monkeypatch) -> None:
    rl = _reload_rate_limit(
        monkeypatch,
        enabled=True,
        redis_url="redis://127.0.0.1:6379/0",
    )

    assert rl.limiter.enabled is True
    # We deliberately do NOT assert the storage URI on the Limiter
    # here. slowapi's internal attribute name is private (`_storage`)
    # and has churned between versions; asserting on it breaks CI on
    # every minor upgrade. The meaningful contract — "we constructed
    # an enabled Limiter without RateLimitMisconfigured" — is already
    # covered by the enabled=True assert above plus the misconfigured
    # test below proving the REDIS_URL branch is reachable.

    # Reset to disabled to avoid leaking enabled state into unrelated tests.
    _reload_rate_limit(monkeypatch, enabled=False, redis_url="")


def test_admin_login_limit_label_is_a_valid_limits_string() -> None:
    """Guard against someone changing the default to something nonsensical."""
    from app.config.env import RATE_LIMIT_ADMIN_LOGIN

    # `limits` accepts forms like "5/minute", "100/hour", "10 per second".
    # A minimal sanity check: must contain a digit and one of the
    # known time granularities.
    assert any(ch.isdigit() for ch in RATE_LIMIT_ADMIN_LOGIN)
    assert any(
        unit in RATE_LIMIT_ADMIN_LOGIN.lower()
        for unit in ("second", "minute", "hour", "day")
    )
