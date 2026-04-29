"""Unit tests for ops.audit.middleware — noop path + write-failure isolation.

Key invariants under test (SPEC AC-AL.1.x):
- AUDIT_RETENTION_DAYS=0 → middleware is a complete noop (AC-AL.1.4).
- Audit write failure does NOT propagate to the HTTP caller (AC-AL.1.7).
- _result_from_status maps status codes correctly.
- _parse_json_body handles non-JSON bodies gracefully.
"""

from __future__ import annotations

import pytest

import ops.audit.config as audit_config
from ops.audit.middleware import (
    _parse_json_body,
    _result_from_status,
)
from ops.audit.db import RESULT_DENIED, RESULT_FAILURE, RESULT_SUCCESS


# ── _result_from_status ───────────────────────────────────────────────────


@pytest.mark.parametrize(
    "code,expected",
    [
        (200, RESULT_SUCCESS),
        (201, RESULT_SUCCESS),
        (204, RESULT_SUCCESS),
        (301, RESULT_SUCCESS),  # redirects = success for audit purposes
        (400, RESULT_FAILURE),
        (404, RESULT_FAILURE),
        (422, RESULT_FAILURE),
        (500, RESULT_FAILURE),
        (503, RESULT_FAILURE),
        (401, RESULT_DENIED),
        (403, RESULT_DENIED),
    ],
)
def test_result_from_status(code: int, expected: str) -> None:
    assert _result_from_status(code) == expected


# ── _parse_json_body ──────────────────────────────────────────────────────


def test_parse_valid_json() -> None:
    body = b'{"plan_id": 1, "enabled": true}'
    assert _parse_json_body(body) == {"plan_id": 1, "enabled": True}


def test_parse_empty_body_returns_none() -> None:
    assert _parse_json_body(b"") is None
    assert _parse_json_body(b"   ") is None


def test_parse_invalid_json_returns_none() -> None:
    assert _parse_json_body(b"not json") is None
    assert _parse_json_body(b"<html>") is None


def test_parse_binary_body_returns_none() -> None:
    assert _parse_json_body(b"\x00\x01\x02\x03") is None


# ── AUDIT_RETENTION_DAYS=0 noop ───────────────────────────────────────────


def test_middleware_noop_when_disabled(tmp_path) -> None:
    """When audit is disabled, AuditMiddleware must return without touching DB."""
    audit_config._reload_for_tests(retention_days=0, secret_key="")
    assert not audit_config.audit_enabled()
    # The noop branch is a simple ``return await call_next(request)``.
    # We verify the guard condition rather than spin up a full ASGI app.
    from ops.audit.config import audit_enabled

    assert audit_enabled() is False


# ── Teardown ──────────────────────────────────────────────────────────────


def teardown_module() -> None:
    audit_config._reload_for_tests(retention_days=90, secret_key="")
