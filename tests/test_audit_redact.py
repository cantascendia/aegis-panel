"""Tests for ops.audit.redact (AL.2a — D-018 TBD-2 SEALED).

Pin the matching rules from the module docstring so future refactors
can't silently weaken the redaction guarantee:

- Base list is non-mutable (frozenset).
- Extras union, not override (operators cannot remove base entries).
- Case-insensitive key match.
- No partial / prefix match.
- Recursive walk (nested dict + list).
- Hash is NEVER substituted — placeholder is the literal string.
"""

from __future__ import annotations

import pytest

from ops.audit.redact import (
    BASE_REDACT_FIELDS,
    REDACTED_PLACEHOLDER,
    effective_redact_set,
    redact_payload,
)


# ---------------------------------------------------------------------
# Sealed base list invariants (D-018 TBD-2)
# ---------------------------------------------------------------------


def test_base_redact_fields_is_frozenset() -> None:
    """Base list must be immutable so no code path can shrink it."""
    assert isinstance(BASE_REDACT_FIELDS, frozenset)
    with pytest.raises(AttributeError):
        BASE_REDACT_FIELDS.add("foo")  # type: ignore[attr-defined]


def test_base_includes_critical_secrets() -> None:
    """Sealed base must always cover these — D-018 TBD-2."""
    must_redact = {
        "password",
        "passwd",
        # ``hashed_password`` is the actual Admin column (codex review
        # P2 — must redact or offline-crackable hash leaks via audit).
        "hashed_password",
        "password_hash",  # alias retained
        "jwt",
        "secret_key",
        # ``key`` and ``subscription_url`` are the actual User
        # bearer-credential fields per ``app.models.user.User`` /
        # ``UserResponse`` — codex review P2.
        "key",
        "subscription_url",
        "merchant_key",
        "trc20_private_key",
        "private_key",
        "api_key",
        "cf_token",
        "subscription_token",
    }
    missing = must_redact - BASE_REDACT_FIELDS
    assert not missing, f"Sealed base must cover: {missing}"


def test_base_redacts_real_user_bearer_fields() -> None:
    """Regression: codex review 2026-04-30 P2 — User.key (16-hex
    bearer) and UserResponse.subscription_url must redact."""
    from ops.audit.redact import redact_payload

    payload = {
        "username": "alice",
        "key": "a1b2c3d4e5f6a7b8",  # User.key
        "subscription_url": "https://panel.example.com/sub/eyJ...",
    }
    out = redact_payload(payload)
    assert out["username"] == "alice"
    assert out["key"] == REDACTED_PLACEHOLDER
    assert out["subscription_url"] == REDACTED_PLACEHOLDER


def test_base_redacts_real_admin_password_field() -> None:
    """Regression: codex review 2026-04-30 P2 — Admin.hashed_password
    must redact (not just password_hash alias)."""
    from ops.audit.redact import redact_payload

    payload = {"username": "ops_dave", "hashed_password": "$2b$12$abc..."}
    out = redact_payload(payload)
    assert out["username"] == "ops_dave"
    assert out["hashed_password"] == REDACTED_PLACEHOLDER


# ---------------------------------------------------------------------
# Extras union behaviour
# ---------------------------------------------------------------------


def test_no_extras_means_just_base(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AUDIT_EXTRA_REDACT_FIELDS", raising=False)
    assert effective_redact_set() == BASE_REDACT_FIELDS


def test_extras_union_with_base(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUDIT_EXTRA_REDACT_FIELDS", "email,phone")
    eff = effective_redact_set()
    assert "email" in eff
    assert "phone" in eff
    # Base must still be present — D-018 TBD-2 invariant.
    assert BASE_REDACT_FIELDS.issubset(eff)


def test_extras_cannot_override_base(monkeypatch: pytest.MonkeyPatch) -> None:
    """Even if an operator's extras list omits 'password', base still
    redacts it. This is the load-bearing safety guarantee."""
    monkeypatch.setenv("AUDIT_EXTRA_REDACT_FIELDS", "email")
    eff = effective_redact_set()
    assert "password" in eff  # base still wins


def test_extras_whitespace_stripped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUDIT_EXTRA_REDACT_FIELDS", "  email , phone  ,  ")
    eff = effective_redact_set()
    assert "email" in eff
    assert "phone" in eff
    # No empty entry from the trailing comma.
    assert "" not in eff


def test_extras_case_normalised(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUDIT_EXTRA_REDACT_FIELDS", "Email,PHONE")
    eff = effective_redact_set()
    assert "email" in eff
    assert "phone" in eff


# ---------------------------------------------------------------------
# Redaction behaviour
# ---------------------------------------------------------------------


def test_redact_replaces_with_literal_placeholder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AUDIT_EXTRA_REDACT_FIELDS", raising=False)
    out = redact_payload({"password": "hunter2"})
    assert out == {"password": REDACTED_PLACEHOLDER}
    # Hash-style substitution would break the no-comparability rule.
    assert REDACTED_PLACEHOLDER == "<REDACTED>"


def test_redact_preserves_non_secret_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AUDIT_EXTRA_REDACT_FIELDS", raising=False)
    payload = {"username": "alice", "password": "x", "is_admin": True}
    out = redact_payload(payload)
    assert out["username"] == "alice"
    assert out["password"] == REDACTED_PLACEHOLDER
    assert out["is_admin"] is True


def test_redact_case_insensitive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AUDIT_EXTRA_REDACT_FIELDS", raising=False)
    payload = {"Password": "x", "PASSWORD": "y", "PaSsWoRd": "z"}
    out = redact_payload(payload)
    assert out == {
        "Password": REDACTED_PLACEHOLDER,
        "PASSWORD": REDACTED_PLACEHOLDER,
        "PaSsWoRd": REDACTED_PLACEHOLDER,
    }


def test_redact_no_partial_match(monkeypatch: pytest.MonkeyPatch) -> None:
    """``password_strength_score`` must NOT be redacted — that's a
    metric, not a secret. Operators wanting to redact it add the
    explicit field to AUDIT_EXTRA_REDACT_FIELDS."""
    monkeypatch.delenv("AUDIT_EXTRA_REDACT_FIELDS", raising=False)
    payload = {"password_strength_score": 7, "key_count": 3}
    out = redact_payload(payload)
    assert out == payload  # unchanged


def test_redact_walks_nested_dict(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AUDIT_EXTRA_REDACT_FIELDS", raising=False)
    payload = {
        "user": {
            "id": 1,
            "credentials": {"password": "p1", "api_key": "k1"},
        }
    }
    out = redact_payload(payload)
    assert out["user"]["id"] == 1
    assert out["user"]["credentials"]["password"] == REDACTED_PLACEHOLDER
    assert out["user"]["credentials"]["api_key"] == REDACTED_PLACEHOLDER


def test_redact_walks_list_of_dicts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AUDIT_EXTRA_REDACT_FIELDS", raising=False)
    payload = {
        "channels": [
            {"name": "epay-1", "merchant_key": "secret1"},
            {"name": "epay-2", "merchant_key": "secret2"},
        ]
    }
    out = redact_payload(payload)
    assert out["channels"][0]["name"] == "epay-1"
    assert out["channels"][0]["merchant_key"] == REDACTED_PLACEHOLDER
    assert out["channels"][1]["merchant_key"] == REDACTED_PLACEHOLDER


def test_redact_does_not_mutate_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Caller may keep using the raw payload after redaction
    (e.g. return real after_state to API client while persisting only
    the redacted copy)."""
    monkeypatch.delenv("AUDIT_EXTRA_REDACT_FIELDS", raising=False)
    raw = {"password": "hunter2", "user": {"jwt": "eyJ..."}}
    redact_payload(raw)
    assert raw == {"password": "hunter2", "user": {"jwt": "eyJ..."}}


def test_redact_passes_through_scalars(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-dict, non-list inputs return unchanged — the function is
    callable on any JSON-shaped value, not just dicts."""
    monkeypatch.delenv("AUDIT_EXTRA_REDACT_FIELDS", raising=False)
    assert redact_payload("hello") == "hello"
    assert redact_payload(42) == 42
    assert redact_payload(None) is None
    assert redact_payload(True) is True


def test_redact_does_not_redact_value_strings_that_look_like_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Module is a *field-name* redactor, not a value-content
    detector. ``"eyJhbGciOi..."`` style values pass through if their
    key is non-secret. Heuristic value-content detection is a
    different module (not in scope here)."""
    monkeypatch.delenv("AUDIT_EXTRA_REDACT_FIELDS", raising=False)
    payload = {"note": "eyJhbGciOiJIUzI1NiJ9.fake.jwt"}
    out = redact_payload(payload)
    assert out == payload  # unchanged — key 'note' is not in redact set


def test_extras_redact_at_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    """Extras edits between requests take effect immediately
    (no-restart operator workflow)."""
    monkeypatch.delenv("AUDIT_EXTRA_REDACT_FIELDS", raising=False)
    out1 = redact_payload({"email": "a@b.c"})
    assert out1 == {"email": "a@b.c"}  # not redacted yet

    monkeypatch.setenv("AUDIT_EXTRA_REDACT_FIELDS", "email")
    out2 = redact_payload({"email": "a@b.c"})
    assert out2 == {"email": REDACTED_PLACEHOLDER}
