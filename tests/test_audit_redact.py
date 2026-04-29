"""Unit tests for ops.audit.redact — REDACT_FIELDS + deep_redact().

These tests are the primary defence against ``deep_redact`` silently
missing a field. The test is intentionally exhaustive on the SSOT:
every key in ``REDACT_FIELDS`` must be covered. Add new fields to the
module *and* to the parametrise list here.
"""

from __future__ import annotations

import pytest

from ops.audit.redact import REDACT_FIELDS, deep_redact

_SENTINEL = "[REDACTED]"


# ── Every REDACT_FIELDS key must be redacted at top level ────────────────


@pytest.mark.parametrize("field", sorted(REDACT_FIELDS))
def test_top_level_field_is_redacted(field: str) -> None:
    """Each listed field must be replaced with the sentinel."""
    obj = {field: "secret_value_123"}
    result = deep_redact(obj)
    assert result[field] == _SENTINEL, f"{field!r} was not redacted"


# ── Case-insensitive matching ─────────────────────────────────────────────


def test_case_insensitive_redaction() -> None:
    obj = {"Password": "hunter2", "PASSWORD": "abc"}
    result = deep_redact(obj)
    assert result["Password"] == _SENTINEL
    assert result["PASSWORD"] == _SENTINEL


# ── Non-sensitive fields are NOT redacted ────────────────────────────────


def test_non_sensitive_fields_pass_through() -> None:
    obj = {"username": "alice", "enabled": True, "plan_id": 42}
    result = deep_redact(obj)
    assert result == obj


# ── Nested dict ──────────────────────────────────────────────────────────


def test_nested_dict_redaction() -> None:
    obj = {"config": {"merchant_key": "secret", "gateway_url": "https://pay.example"}}
    result = deep_redact(obj)
    assert result["config"]["merchant_key"] == _SENTINEL
    assert result["config"]["gateway_url"] == "https://pay.example"


# ── Nested list ──────────────────────────────────────────────────────────


def test_nested_list_redaction() -> None:
    obj = {"items": [{"password": "p1"}, {"password": "p2"}, {"other": "ok"}]}
    result = deep_redact(obj)
    assert result["items"][0]["password"] == _SENTINEL
    assert result["items"][1]["password"] == _SENTINEL
    assert result["items"][2]["other"] == "ok"


# ── Scalars pass through unchanged ──────────────────────────────────────


def test_scalar_passes_through() -> None:
    assert deep_redact(42) == 42
    assert deep_redact("hello") == "hello"
    assert deep_redact(None) is None
    assert deep_redact(True) is True


# ── None input is safe ───────────────────────────────────────────────────


def test_none_dict_is_safe() -> None:
    assert deep_redact({}) == {}
    assert deep_redact([]) == []


# ── Original object is NOT mutated ──────────────────────────────────────


def test_no_mutation_of_original() -> None:
    original = {"password": "original_secret"}
    _ = deep_redact(original)
    assert original["password"] == "original_secret"


# ── Depth limit does not crash ───────────────────────────────────────────


def test_depth_limit_no_crash() -> None:
    # Build a dict nested 25 levels deep (above the 20-level limit).
    obj: dict = {}
    node = obj
    for _ in range(25):
        child: dict = {}
        node["nested"] = child
        node = child
    node["password"] = "deep_secret"

    # Should not raise; deepest redaction may or may not happen but
    # the function must not raise a RecursionError.
    deep_redact(obj)
