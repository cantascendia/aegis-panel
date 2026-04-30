"""Tests for ops.audit.config (AL.2c.1 — startup validation + retention).

Pin the SEALED behaviour:

- ``AUDIT_RETENTION_DAYS=0`` → audit disabled, key check skipped (D-018
  TBD-1 SEALED — opt-out path).
- ``AUDIT_RETENTION_DAYS>0`` + missing/malformed key → boot abort
  (fail-loud, never silent event-drop).
- Negative retention clamps to 0 (defensive).
- Non-int retention raises (fail-loud on misconfig).
- ``validate_startup()`` is idempotent.
"""

from __future__ import annotations

import logging

import pytest
from cryptography.fernet import Fernet


def _fresh_key() -> str:
    return Fernet.generate_key().decode()


@pytest.fixture(autouse=True)
def reset_env(monkeypatch: pytest.MonkeyPatch):
    """Each test starts with no env vars set; tests opt in to what
    they need. Crypto cache cleared so old key state doesn't leak."""
    monkeypatch.delenv("AUDIT_SECRET_KEY", raising=False)
    monkeypatch.delenv("AUDIT_RETENTION_DAYS", raising=False)
    monkeypatch.delenv("AUDIT_EXTRA_REDACT_FIELDS", raising=False)
    from ops.audit import crypto

    crypto._reload_for_tests()
    yield
    crypto._reload_for_tests()


# ---------------------------------------------------------------------
# retention_days() / is_audit_enabled()
# ---------------------------------------------------------------------


def test_default_retention_is_90_days(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ops.audit.config import DEFAULT_RETENTION_DAYS, retention_days

    assert DEFAULT_RETENTION_DAYS == 90
    assert retention_days() == 90


def test_retention_explicit_value_honored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUDIT_RETENTION_DAYS", "30")
    from ops.audit.config import retention_days

    assert retention_days() == 30


def test_retention_zero_means_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUDIT_RETENTION_DAYS", "0")
    from ops.audit.config import is_audit_enabled, retention_days

    assert retention_days() == 0
    assert is_audit_enabled() is False


def test_retention_negative_clamps_to_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Defensive: misconfigured ``-1`` = "audit off", not "audit on
    with funny retention"."""
    monkeypatch.setenv("AUDIT_RETENTION_DAYS", "-5")
    from ops.audit.config import is_audit_enabled, retention_days

    assert retention_days() == 0
    assert is_audit_enabled() is False


def test_retention_non_int_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail-loud on misconfig: ``"forever"`` should not silently
    accept and skip the sweep."""
    monkeypatch.setenv("AUDIT_RETENTION_DAYS", "forever")
    from ops.audit.config import retention_days

    with pytest.raises(ValueError):
        retention_days()


# ---------------------------------------------------------------------
# validate_startup() — opt-out path (AUDIT_RETENTION_DAYS=0)
# ---------------------------------------------------------------------


def test_validate_startup_opt_out_does_not_raise(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-018 TBD-1 SEALED opt-out: retention=0 skips key check."""
    monkeypatch.setenv("AUDIT_RETENTION_DAYS", "0")
    # Deliberately NO AUDIT_SECRET_KEY — should still pass.
    from ops.audit.config import validate_startup

    validate_startup()  # must not raise


def test_validate_startup_opt_out_logs_intentional_disable(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """D-003-conscious deployments need a positive boot-log signal
    that audit is *intentionally* off (not accidentally)."""
    monkeypatch.setenv("AUDIT_RETENTION_DAYS", "0")
    from ops.audit.config import validate_startup

    with caplog.at_level(logging.INFO, logger="ops.audit.config"):
        validate_startup()

    log_text = caplog.text
    assert "disabled" in log_text.lower()
    assert "AUDIT_RETENTION_DAYS=0" in log_text


# ---------------------------------------------------------------------
# validate_startup() — enabled path (AUDIT_RETENTION_DAYS > 0)
# ---------------------------------------------------------------------


def test_validate_startup_missing_key_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The combination 'audit on' + 'no key' must abort boot."""
    monkeypatch.setenv("AUDIT_RETENTION_DAYS", "30")
    # No AUDIT_SECRET_KEY.
    from ops.audit.config import AuditMisconfigured, validate_startup

    with pytest.raises(AuditMisconfigured) as exc_info:
        validate_startup()
    msg = str(exc_info.value)
    assert "AUDIT_RETENTION_DAYS=30" in msg
    assert "AUDIT_SECRET_KEY is not set" in msg
    # Operator-friendly hint with both remediation paths:
    assert "Fernet" in msg
    assert "AUDIT_RETENTION_DAYS=0" in msg
    # Refuses to boot, not silently accepts:
    assert "Refusing to boot" in msg


def test_validate_startup_malformed_key_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Malformed key surfaces here at boot, not first request."""
    monkeypatch.setenv("AUDIT_RETENTION_DAYS", "30")
    monkeypatch.setenv("AUDIT_SECRET_KEY", "not-a-valid-fernet-key")
    from ops.audit import crypto
    from ops.audit.config import AuditMisconfigured, validate_startup

    crypto._reload_for_tests()
    with pytest.raises(AuditMisconfigured):
        validate_startup()


def test_validate_startup_happy_path(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setenv("AUDIT_RETENTION_DAYS", "30")
    monkeypatch.setenv("AUDIT_SECRET_KEY", _fresh_key())
    from ops.audit import crypto
    from ops.audit.config import validate_startup

    crypto._reload_for_tests()
    with caplog.at_level(logging.INFO, logger="ops.audit.config"):
        validate_startup()

    log_text = caplog.text
    assert "enabled" in log_text.lower()
    assert "30" in log_text  # retention echoed


def test_validate_startup_warms_fernet_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Calling validate_startup() should leave the Fernet cipher
    instantiated, so the first audit write doesn't pay the
    construction cost."""
    monkeypatch.setenv("AUDIT_RETENTION_DAYS", "30")
    monkeypatch.setenv("AUDIT_SECRET_KEY", _fresh_key())
    from ops.audit import crypto
    from ops.audit.config import validate_startup

    crypto._reload_for_tests()
    assert crypto._fernet.cache_info().currsize == 0

    validate_startup()
    assert crypto._fernet.cache_info().currsize == 1


def test_validate_startup_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Multiple calls must not blow up — boot sequences may double-
    invoke (lifespan handlers etc.)."""
    monkeypatch.setenv("AUDIT_RETENTION_DAYS", "30")
    monkeypatch.setenv("AUDIT_SECRET_KEY", _fresh_key())
    from ops.audit import crypto
    from ops.audit.config import validate_startup

    crypto._reload_for_tests()
    validate_startup()
    validate_startup()  # second call must not raise
    validate_startup()  # third either


# ---------------------------------------------------------------------
# Single error class
# ---------------------------------------------------------------------


def test_audit_misconfigured_is_runtime_error_subclass() -> None:
    """``except RuntimeError`` must catch our exception (general
    boot-error catch path in app/marzneshin.py)."""
    from ops.audit.config import AuditMisconfigured

    assert issubclass(AuditMisconfigured, RuntimeError)


def test_config_and_crypto_share_exception_class() -> None:
    """``from ops.audit.config import AuditMisconfigured`` must be
    the same class as ``ops.audit.crypto.AuditMisconfigured`` so
    callers don't need to catch both."""
    from ops.audit import config, crypto

    assert config.AuditMisconfigured is crypto.AuditMisconfigured
