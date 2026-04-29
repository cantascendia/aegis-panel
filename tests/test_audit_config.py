"""Unit tests for ops.audit.config — env wiring, Fernet, fail-loud.

Mirrors the shape of ``tests/test_crypto.py`` (billing Fernet tests).
"""

from __future__ import annotations

import pytest
from cryptography.fernet import Fernet

import ops.audit.config as audit_config
from ops.audit.config import (
    AuditMisconfigured,
    audit_enabled,
    check_audit_key_at_startup,
    decrypt_state,
    encrypt_state,
)


# ── Helpers ───────────────────────────────────────────────────────────────


def _good_key() -> str:
    return Fernet.generate_key().decode()


def _reload(retention: int = 90, key: str = "") -> None:
    audit_config._reload_for_tests(retention_days=retention, secret_key=key)


# ── audit_enabled ──────────────────────────────────────────────────────────


def test_audit_enabled_true_by_default() -> None:
    _reload(retention=90)
    assert audit_enabled() is True


def test_audit_disabled_when_retention_zero() -> None:
    _reload(retention=0)
    assert audit_enabled() is False


# ── check_audit_key_at_startup ─────────────────────────────────────────────


def test_startup_check_noop_when_disabled() -> None:
    _reload(retention=0, key="")
    check_audit_key_at_startup()  # must not raise


def test_startup_check_raises_when_enabled_no_key() -> None:
    _reload(retention=90, key="")
    with pytest.raises(AuditMisconfigured, match="AUDIT_SECRET_KEY"):
        check_audit_key_at_startup()


def test_startup_check_ok_when_enabled_with_valid_key() -> None:
    _reload(retention=90, key=_good_key())
    check_audit_key_at_startup()  # must not raise


# ── encrypt_state / decrypt_state roundtrip ───────────────────────────────


def test_encrypt_decrypt_roundtrip() -> None:
    key = _good_key()
    _reload(key=key)
    data = {"plan_id": 42, "user": "alice", "password": "should_not_matter"}
    ciphertext = encrypt_state(data)
    assert isinstance(ciphertext, bytes)
    assert len(ciphertext) > 0
    plaintext = decrypt_state(ciphertext)
    assert plaintext == data


def test_encrypt_none_returns_none() -> None:
    _reload(key=_good_key())
    assert encrypt_state(None) is None
    assert encrypt_state({}) is None


def test_decrypt_none_returns_none() -> None:
    _reload(key=_good_key())
    assert decrypt_state(None) is None
    assert decrypt_state(b"") is None


def test_encrypt_raises_without_key() -> None:
    _reload(retention=90, key="")
    with pytest.raises(AuditMisconfigured):
        encrypt_state({"x": 1})


def test_decrypt_raises_with_wrong_key() -> None:
    key_a = _good_key()
    key_b = _good_key()
    _reload(key=key_a)
    ciphertext = encrypt_state({"x": 1})

    _reload(key=key_b)
    with pytest.raises(AuditMisconfigured, match="wrong AUDIT_SECRET_KEY"):
        decrypt_state(ciphertext)


# ── Teardown: restore sane defaults ──────────────────────────────────────


def teardown_module() -> None:
    _reload(retention=90, key="")
