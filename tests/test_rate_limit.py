"""
Tests for hardening/panel/rate_limit.py.

Contract we're guarding:
1. Default config (RATE_LIMIT_ENABLED=false) produces a disabled
   Limiter that never blocks anything — ensures "existing deployments
   unaffected by upgrade" stays true.
2. Enabling rate limiting without REDIS_URL must raise
   RateLimitMisconfigured. Silently falling back to in-process
   counters in a multi-worker deployment is worse than refusing to
   start.
3. Enabling with REDIS_URL constructs an enabled Limiter pointing at
   Redis — no regression where the URL is ignored.

Implementation note — why no `importlib.reload`
------------------------------------------------
We deliberately DON'T reload the module to retest _build_limiter.
Reloading re-executes the `class RateLimitMisconfigured(...)`
statement, producing a *new* class object. Any reference captured
before reload (e.g. `pytest.raises(rl_module.RateLimitMisconfigured)`)
compares by `isinstance` against the old class, and the raised
exception is an instance of the new one — so the match fails and the
exception escapes the test. Driving different env permutations via
monkeypatch + direct `_build_limiter()` calls sidesteps the whole
class-identity trap.

Out of scope: end-to-end HTTP testing of 429 responses. That needs
the full FastAPI app + a running Redis, which belongs in the
integration-matrix CI job (future).
"""

from __future__ import annotations

import pytest


def test_default_singleton_limiter_is_disabled() -> None:
    """The module-level `limiter` built at import time must be disabled.

    Default env => RATE_LIMIT_ENABLED=false => any route decorated
    with @limiter.limit(...) must stay non-blocking. This is what
    keeps existing deployments unaffected on upgrade.
    """
    from hardening.panel import rate_limit as rl

    assert rl.limiter.enabled is False, (
        "Default config must produce a disabled Limiter so existing "
        "deployments don't suddenly 429 on upgrade."
    )


def test_enabled_without_redis_raises_misconfigured(monkeypatch) -> None:
    """Fail-loud: the whole point of rate limiting is a shared counter."""
    from hardening.panel import rate_limit as rl

    # Patch the *module-local* names that `_build_limiter` reads.
    # Patching `app.config.env` alone is not enough — the names were
    # already bound at rate_limit's import time.
    monkeypatch.setattr(rl, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(rl, "REDIS_URL", "")

    with pytest.raises(rl.RateLimitMisconfigured) as exc_info:
        rl._build_limiter()

    message = str(exc_info.value)
    # The error must name both env vars so the operator knows the fix.
    assert "RATE_LIMIT_ENABLED" in message
    assert "REDIS_URL" in message


def test_enabled_with_redis_builds_enabled_limiter(monkeypatch) -> None:
    from hardening.panel import rate_limit as rl

    monkeypatch.setattr(rl, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(rl, "REDIS_URL", "redis://127.0.0.1:6379/0")

    limiter = rl._build_limiter()

    assert limiter.enabled is True
    # We deliberately do NOT assert on slowapi-private attrs (`_storage`
    # etc.). Their names churn between minor versions; asserting on them
    # would turn every slowapi upgrade into a CI fire drill. "Constructed
    # an enabled Limiter without raising" is the contract that matters.


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
