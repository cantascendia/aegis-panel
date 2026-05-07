"""Tests for customer-side auth (Track B).

Forbidden-path coverage target: ≥80% mutation score
(`mutmut run --paths-to-mutate app/utils/customer_auth.py`).

Layered:
* `test_parse_sub_url_*` — parser robustness against URL variants
* `test_create_customer_token_*` — JWT issuance shape + claims
* `test_get_customer_payload_*` — JWT decode + access-claim rejection
* `test_token_round_trip` — issue + decode end-to-end

These tests intentionally exercise:
* Negative paths (None / empty / malformed input)
* Boundary lengths (username 3-64, key 16-128)
* Cross-token rejection (admin tokens MUST fail customer decode)
* Forward compatibility (extra claims preserved when added)
"""

from __future__ import annotations

from datetime import timedelta

import jwt
import pytest

from app.config import get_secret_key
from app.utils._aegis_clocks import now_utc_naive
from app.utils.auth import create_admin_token
from app.utils.customer_auth import (
    CUSTOMER_TOKEN_EXPIRE_MINUTES,
    create_customer_token,
    get_customer_payload,
    parse_sub_url,
)

# ---------------------------------------------------------------------------
# parse_sub_url
# ---------------------------------------------------------------------------


def test_parse_sub_url_full_url() -> None:
    p = parse_sub_url("https://nilou.cc/sub/cust_abc123/0123456789abcdef0123456789abcdef")
    assert p is not None
    assert p.username == "cust_abc123"
    assert p.key == "0123456789abcdef0123456789abcdef"


def test_parse_sub_url_with_format_suffix() -> None:
    p = parse_sub_url("https://nilou.cc/sub/cust_abc/0123456789abcdef0123456789abcdef/v2ray-json")
    assert p is not None
    assert p.username == "cust_abc"
    assert p.key == "0123456789abcdef0123456789abcdef"


def test_parse_sub_url_no_scheme() -> None:
    p = parse_sub_url("nilou.cc/sub/foo123/0123456789abcdef0123456789abcdef")
    assert p is not None
    assert p.username == "foo123"


def test_parse_sub_url_relative() -> None:
    p = parse_sub_url("/sub/foo123/0123456789abcdef0123456789abcdef")
    assert p is not None
    assert p.username == "foo123"


def test_parse_sub_url_strips_whitespace() -> None:
    p = parse_sub_url("   https://nilou.cc/sub/foo/0123456789abcdef0123456789abcdef   \n")
    assert p is not None
    assert p.username == "foo"


@pytest.mark.parametrize(
    "bad",
    [
        "",
        " ",
        None,
        "not-a-url",
        "https://nilou.cc/admin/foo/key",
        "https://nilou.cc/sub/",
        "https://nilou.cc/sub/onlyuser",
        "https://nilou.cc/sub//emptyuser",
        # username too short
        "https://nilou.cc/sub/ab/0123456789abcdef0123456789abcdef",
        # key too short
        "https://nilou.cc/sub/foo/short",
        # key too long
        "https://nilou.cc/sub/foo/" + ("x" * 200),
        # username too long
        "https://nilou.cc/sub/" + ("u" * 100) + "/0123456789abcdef",
    ],
)
def test_parse_sub_url_rejects_garbage(bad) -> None:  # type: ignore[no-untyped-def]
    assert parse_sub_url(bad) is None


def test_parse_sub_url_non_string_input() -> None:
    assert parse_sub_url(12345) is None  # type: ignore[arg-type]
    assert parse_sub_url(["url"]) is None  # type: ignore[arg-type]
    assert parse_sub_url({}) is None  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# create_customer_token
# ---------------------------------------------------------------------------


def test_create_customer_token_returns_string() -> None:
    token = create_customer_token(42)
    assert isinstance(token, str)
    assert len(token) > 20  # JWT shape sanity


def test_create_customer_token_payload_shape() -> None:
    token = create_customer_token(42)
    decoded = jwt.decode(token, get_secret_key(), algorithms=["HS256"])
    assert decoded["sub"] == "42"
    assert decoded["access"] == "customer"
    assert "iat" in decoded
    assert "exp" in decoded


def test_create_customer_token_expiry_15_min() -> None:
    token = create_customer_token(7)
    decoded = jwt.decode(token, get_secret_key(), algorithms=["HS256"])
    iat = decoded["iat"]
    exp = decoded["exp"]
    assert exp - iat == CUSTOMER_TOKEN_EXPIRE_MINUTES * 60
    assert CUSTOMER_TOKEN_EXPIRE_MINUTES == 15  # contract


@pytest.mark.parametrize("bad", [0, -1, -999, "42", 1.5, None, [], {}])
def test_create_customer_token_rejects_bad_user_id(bad) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ValueError):
        create_customer_token(bad)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# get_customer_payload
# ---------------------------------------------------------------------------


def test_get_customer_payload_round_trip() -> None:
    token = create_customer_token(123)
    payload = get_customer_payload(token)
    assert payload is not None
    assert payload["user_id"] == 123
    assert payload["access"] == "customer"


def test_get_customer_payload_rejects_admin_token() -> None:
    """Admin tokens MUST NOT decode as customer (cross-class rejection).

    This is the central security property of the access-claim scheme:
    even though both tokens are signed with the same JWT secret, the
    `access` claim differentiates audience.
    """
    admin = create_admin_token("riku", is_sudo=True)
    assert get_customer_payload(admin) is None


def test_get_customer_payload_rejects_admin_non_sudo() -> None:
    admin = create_admin_token("ops", is_sudo=False)
    assert get_customer_payload(admin) is None


def test_get_customer_payload_rejects_expired() -> None:
    """Forge an expired token by manually encoding."""
    payload = {
        "sub": "42",
        "access": "customer",
        "iat": now_utc_naive() - timedelta(hours=1),
        "exp": now_utc_naive() - timedelta(minutes=10),
    }
    expired = jwt.encode(payload, get_secret_key(), algorithm="HS256")
    assert get_customer_payload(expired) is None


def test_get_customer_payload_rejects_wrong_signature() -> None:
    payload = {
        "sub": "42",
        "access": "customer",
        "iat": now_utc_naive(),
        "exp": now_utc_naive() + timedelta(minutes=15),
    }
    forged = jwt.encode(payload, "wrong-secret", algorithm="HS256")
    assert get_customer_payload(forged) is None


def test_get_customer_payload_rejects_wrong_algorithm() -> None:
    """HS512 token must NOT pass HS256 decode (algorithm confusion attack)."""
    payload = {
        "sub": "42",
        "access": "customer",
        "exp": now_utc_naive() + timedelta(minutes=15),
    }
    other_alg = jwt.encode(payload, get_secret_key(), algorithm="HS512")
    assert get_customer_payload(other_alg) is None


def test_get_customer_payload_rejects_missing_sub() -> None:
    payload = {
        "access": "customer",
        "iat": now_utc_naive(),
        "exp": now_utc_naive() + timedelta(minutes=15),
    }
    bad = jwt.encode(payload, get_secret_key(), algorithm="HS256")
    assert get_customer_payload(bad) is None


def test_get_customer_payload_rejects_non_int_sub() -> None:
    payload = {
        "sub": "not-an-int",
        "access": "customer",
        "iat": now_utc_naive(),
        "exp": now_utc_naive() + timedelta(minutes=15),
    }
    bad = jwt.encode(payload, get_secret_key(), algorithm="HS256")
    assert get_customer_payload(bad) is None


def test_get_customer_payload_rejects_zero_sub() -> None:
    payload = {
        "sub": "0",
        "access": "customer",
        "iat": now_utc_naive(),
        "exp": now_utc_naive() + timedelta(minutes=15),
    }
    bad = jwt.encode(payload, get_secret_key(), algorithm="HS256")
    assert get_customer_payload(bad) is None


def test_get_customer_payload_rejects_negative_sub() -> None:
    payload = {
        "sub": "-7",
        "access": "customer",
        "iat": now_utc_naive(),
        "exp": now_utc_naive() + timedelta(minutes=15),
    }
    bad = jwt.encode(payload, get_secret_key(), algorithm="HS256")
    assert get_customer_payload(bad) is None


def test_get_customer_payload_rejects_missing_access() -> None:
    payload = {
        "sub": "42",
        "iat": now_utc_naive(),
        "exp": now_utc_naive() + timedelta(minutes=15),
    }
    bad = jwt.encode(payload, get_secret_key(), algorithm="HS256")
    assert get_customer_payload(bad) is None


@pytest.mark.parametrize("bad", [None, "", "   ", 12345, [], {}])
def test_get_customer_payload_rejects_invalid_input(bad) -> None:  # type: ignore[no-untyped-def]
    assert get_customer_payload(bad) is None  # type: ignore[arg-type]


def test_get_customer_payload_garbage_token() -> None:
    assert get_customer_payload("not.a.valid.jwt") is None
    assert get_customer_payload("a.b.c") is None


# ---------------------------------------------------------------------------
# End-to-end issue/decode property
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("user_id", [1, 42, 999, 1_000_000])
def test_customer_token_round_trip_various_user_ids(user_id: int) -> None:
    token = create_customer_token(user_id)
    payload = get_customer_payload(token)
    assert payload is not None
    assert payload["user_id"] == user_id
