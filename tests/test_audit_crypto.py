"""Tests for ops.audit.crypto (AL.2b — Fernet wrapper + redact chain).

Pin the load-bearing properties:

- Missing / malformed key → ``AuditMisconfigured`` (fail-loud, never silent).
- Encryption is round-trippable for valid payloads.
- Encryption ALWAYS redacts before encrypting (non-bypassable safety).
- Empty/None input → ``b""`` / ``None`` (no token overhead).
- Tampered ciphertext → ``AuditMisconfigured`` (HMAC catches it).
- Test hook ``_reload_for_tests`` works as documented.
"""

from __future__ import annotations

import pytest
from cryptography.fernet import Fernet


def _fresh_key() -> str:
    """Generate a valid Fernet key for tests."""
    return Fernet.generate_key().decode()


@pytest.fixture(autouse=True)
def reload_after_each_test(monkeypatch: pytest.MonkeyPatch):
    """Each test starts with no key + extras unset; they set what they
    need. This avoids cross-test cache pollution from
    ``lru_cache`` on ``_fernet``."""
    monkeypatch.delenv("AUDIT_SECRET_KEY", raising=False)
    monkeypatch.delenv("AUDIT_EXTRA_REDACT_FIELDS", raising=False)
    from ops.audit import crypto

    crypto._reload_for_tests()
    yield
    crypto._reload_for_tests()


# ---------------------------------------------------------------------
# is_configured()
# ---------------------------------------------------------------------


def test_is_configured_false_when_no_key() -> None:
    from ops.audit.crypto import is_configured

    assert is_configured() is False


def test_is_configured_true_when_key_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUDIT_SECRET_KEY", _fresh_key())
    from ops.audit import crypto

    crypto._reload_for_tests()
    assert crypto.is_configured() is True


# ---------------------------------------------------------------------
# Fail-loud on missing / malformed key
# ---------------------------------------------------------------------


def test_encrypt_without_key_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ops.audit.crypto import AuditMisconfigured, encrypt_audit_payload

    with pytest.raises(AuditMisconfigured) as exc_info:
        encrypt_audit_payload({"data_limit": 1024})
    assert "AUDIT_SECRET_KEY is not configured" in str(exc_info.value)


def test_decrypt_without_key_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ops.audit.crypto import AuditMisconfigured, decrypt_audit_payload

    with pytest.raises(AuditMisconfigured):
        decrypt_audit_payload(b"any-non-empty-bytes")


def test_malformed_key_raises_descriptive_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUDIT_SECRET_KEY", "not-a-valid-fernet-key")
    from ops.audit import crypto

    crypto._reload_for_tests()
    with pytest.raises(crypto.AuditMisconfigured) as exc_info:
        crypto.encrypt_audit_payload({"x": 1})
    assert "not a valid Fernet key" in str(exc_info.value)


# ---------------------------------------------------------------------
# Empty/None passthrough
# ---------------------------------------------------------------------


def test_encrypt_none_returns_empty_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUDIT_SECRET_KEY", _fresh_key())
    from ops.audit import crypto

    crypto._reload_for_tests()
    # No key needed for None passthrough — short-circuits before _fernet().
    assert crypto.encrypt_audit_payload(None) == b""


def test_decrypt_empty_bytes_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ops.audit import crypto

    # No key needed for empty-bytes passthrough.
    assert crypto.decrypt_audit_payload(b"") is None
    assert crypto.decrypt_audit_payload(None) is None


# ---------------------------------------------------------------------
# Round-trip
# ---------------------------------------------------------------------


def test_round_trip_simple_dict(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUDIT_SECRET_KEY", _fresh_key())
    from ops.audit import crypto

    crypto._reload_for_tests()
    payload = {"data_limit": 1024, "expire_date": "2026-12-31"}
    ct = crypto.encrypt_audit_payload(payload)
    assert isinstance(ct, bytes) and ct
    # Round-trip recovers the data (no secrets in this payload, so
    # redact is a no-op).
    assert crypto.decrypt_audit_payload(ct) == payload


def test_round_trip_nested(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUDIT_SECRET_KEY", _fresh_key())
    from ops.audit import crypto

    crypto._reload_for_tests()
    payload = {
        "user": {"id": 1, "username": "alice"},
        "changes": [{"field": "expire_date", "old": "a", "new": "b"}],
    }
    ct = crypto.encrypt_audit_payload(payload)
    assert crypto.decrypt_audit_payload(ct) == payload


# ---------------------------------------------------------------------
# Non-bypassable redact (load-bearing safety property)
# ---------------------------------------------------------------------


def test_encrypt_redacts_before_encryption(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Critical safety: even though caller passes the secret in
    cleartext, the ciphertext (when decrypted by the legitimate key
    holder) must not contain it."""
    monkeypatch.setenv("AUDIT_SECRET_KEY", _fresh_key())
    from ops.audit import crypto

    crypto._reload_for_tests()
    # Note: build the dict programmatically so GitGuardian's
    # Username/Password generic detector doesn't match a literal
    # `{"username": ..., "password": ...}` pattern in source.
    user_field = "username"
    pw_field = "password"  # noqa: S105
    pw_value = "DUMMY_PW_FOR_TEST"  # noqa: S105  pragma: allowlist secret
    payload = {user_field: "alice", pw_field: pw_value}
    ct = crypto.encrypt_audit_payload(payload)
    decrypted = crypto.decrypt_audit_payload(ct)
    assert decrypted == {user_field: "alice", pw_field: "<REDACTED>"}
    # The literal secret must not survive any code path.
    assert pw_value not in str(decrypted)


def test_encrypt_redacts_real_user_bearer_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pins the codex-review fix on the redact module: real bearer
    field names (User.key, subscription_url, hashed_password) are
    redacted on the encrypt-side too."""
    monkeypatch.setenv("AUDIT_SECRET_KEY", _fresh_key())
    from ops.audit import crypto

    crypto._reload_for_tests()
    payload = {
        "key": "16hex_bearer_token_value",
        "subscription_url": "https://panel.example.com/sub/eyJ",
        "hashed_password": "$2b$12$bcrypt_hash",
    }
    ct = crypto.encrypt_audit_payload(payload)
    decrypted = crypto.decrypt_audit_payload(ct)
    assert decrypted["key"] == "<REDACTED>"
    assert decrypted["subscription_url"] == "<REDACTED>"
    assert decrypted["hashed_password"] == "<REDACTED>"
    # No literal secret in the round-tripped output.
    assert "16hex_bearer_token_value" not in str(decrypted)
    assert "$2b$12$bcrypt_hash" not in str(decrypted)


def test_encrypt_does_not_mutate_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUDIT_SECRET_KEY", _fresh_key())
    from ops.audit import crypto

    crypto._reload_for_tests()
    # See test_encrypt_redacts_before_encryption for the rationale on
    # programmatic dict construction (GitGuardian false-positive avoidance).
    user_field = "username"
    pw_field = "password"  # noqa: S105
    raw = {user_field: "alice", pw_field: "p"}
    crypto.encrypt_audit_payload(raw)
    # The caller's dict is unchanged — they may still send the real
    # password in a response (rare; usually shouldn't), and the audit
    # row holds only the redacted ciphertext.
    assert raw == {user_field: "alice", pw_field: "p"}


# ---------------------------------------------------------------------
# Tamper detection
# ---------------------------------------------------------------------


def test_tampered_ciphertext_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUDIT_SECRET_KEY", _fresh_key())
    from ops.audit import crypto

    crypto._reload_for_tests()
    ct = crypto.encrypt_audit_payload({"x": 1})
    # Flip a byte in the middle (avoid the version byte at index 0
    # which would also fail but with a different code path).
    tampered = ct[:20] + bytes([(ct[20] + 1) % 256]) + ct[21:]
    with pytest.raises(crypto.AuditMisconfigured) as exc_info:
        crypto.decrypt_audit_payload(tampered)
    assert "wrong key or corrupted ciphertext" in str(exc_info.value)


def test_wrong_key_raises_with_rotation_hint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rotated key without MultiFernet wrapping = decrypt fails;
    the error message must guide the operator to MultiFernet."""
    monkeypatch.setenv("AUDIT_SECRET_KEY", _fresh_key())
    from ops.audit import crypto

    crypto._reload_for_tests()
    ct = crypto.encrypt_audit_payload({"x": 1})

    # Operator rotates the key without keeping the old one.
    monkeypatch.setenv("AUDIT_SECRET_KEY", _fresh_key())
    crypto._reload_for_tests()
    with pytest.raises(crypto.AuditMisconfigured) as exc_info:
        crypto.decrypt_audit_payload(ct)
    assert "MultiFernet" in str(exc_info.value)


# ---------------------------------------------------------------------
# Determinism + uniqueness invariants
# ---------------------------------------------------------------------


def test_iv_randomisation_two_encrypts_differ(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fernet adds a random IV per encrypt — two calls with the same
    plaintext must produce different ciphertext (forward secrecy
    against ciphertext-equality leak)."""
    monkeypatch.setenv("AUDIT_SECRET_KEY", _fresh_key())
    from ops.audit import crypto

    crypto._reload_for_tests()
    payload = {"x": 1}
    ct1 = crypto.encrypt_audit_payload(payload)
    ct2 = crypto.encrypt_audit_payload(payload)
    assert ct1 != ct2
    # But both decrypt to the same value.
    assert crypto.decrypt_audit_payload(ct1) == crypto.decrypt_audit_payload(
        ct2
    )


def test_extras_redact_applied_at_encrypt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Operator extends redact list via env; encrypt picks it up
    immediately (same no-restart contract as the redact module)."""
    monkeypatch.setenv("AUDIT_SECRET_KEY", _fresh_key())
    monkeypatch.setenv("AUDIT_EXTRA_REDACT_FIELDS", "email,phone")
    from ops.audit import crypto

    crypto._reload_for_tests()
    ct = crypto.encrypt_audit_payload({"email": "a@b.c", "phone": "+1"})
    decrypted = crypto.decrypt_audit_payload(ct)
    assert decrypted == {"email": "<REDACTED>", "phone": "<REDACTED>"}
