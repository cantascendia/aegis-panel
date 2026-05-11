"""
Tests for ``ops.billing.trc20_client`` — Tronscan response parsing.

We don't make real HTTP calls. Two layers of test:

- ``_parse_transfers`` (pure): hand-built JSON dict → list of
  ``Trc20Transfer``. Pins the parser against Tronscan's documented
  response shape so a vendor change surfaces here, not at production
  runtime.
- ``TronscanClient.list_recent_transfers`` (mocked HTTP): uses
  ``aiohttp`` mock to verify URL composition + error mapping.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import aiohttp
import pytest

from ops.billing.trc20_client import (
    Trc20ClientError,
    TronscanClient,
    _decode_memo,
    _parse_one,
    _parse_transfers,
)

# --------------------------------------------------------------------------
# Memo decoding
# --------------------------------------------------------------------------


def test_decode_memo_decodes_hex_utf8() -> None:
    """ABCDEFGH as UTF-8 hex → recovered string."""
    payload = b"ABCDEFGH".hex()
    assert _decode_memo(payload) == "ABCDEFGH"


def test_decode_memo_handles_0x_prefix() -> None:
    payload = "0x" + b"ABCD".hex()
    assert _decode_memo(payload) == "ABCD"


def test_decode_memo_returns_none_on_garbage() -> None:
    assert _decode_memo("not-hex") is None
    assert _decode_memo("") is None


def test_decode_memo_strips_null_bytes() -> None:
    """TRC20 wallets often pad memos with trailing nulls."""
    payload = ("ABCD" + "\x00\x00").encode().hex()
    assert _decode_memo(payload) == "ABCD"


def test_decode_memo_returns_none_on_invalid_utf8() -> None:
    assert _decode_memo("ff" * 4) is None  # 0xFFFFFFFF — not valid UTF-8


# --------------------------------------------------------------------------
# _parse_one — single tx record
# --------------------------------------------------------------------------


def _good_record(**overrides: Any) -> dict[str, Any]:
    """Default record approximating Tronscan's ``token_trc20/transfers``
    response item."""
    rec = {
        "transaction_id": "txABC",
        "amount_str": "1223000",  # 6 decimals on-chain → 1223 millis
        "block_ts": 1746100800000,  # ms epoch for 2026-05-01 12:00 UTC
        "confirmed": True,
        "block": 100,
        "data": b"ABCDEFGH".hex(),
    }
    rec.update(overrides)
    return rec


def test_parse_one_happy_path() -> None:
    out = _parse_one(_good_record())
    assert out is not None
    assert out.tx_hash == "txABC"
    assert out.amount_millis == 1223
    assert out.memo == "ABCDEFGH"
    assert out.confirmed is True
    assert out.block_number == 100


def test_parse_one_drops_zero_amount() -> None:
    """Tronscan sometimes returns 0-amount entries (e.g. failed
    triggers); we discard them upstream."""
    assert _parse_one(_good_record(amount_str="0")) is None


def test_parse_one_truncates_below_millis() -> None:
    """500 raw units = 0.0005 USDT, sub-millis → 0 → discarded."""
    assert _parse_one(_good_record(amount_str="500")) is None


def test_parse_one_handles_no_memo_data_field() -> None:
    out = _parse_one(_good_record(data=""))
    assert out is not None
    assert out.memo is None


# --------------------------------------------------------------------------
# _parse_transfers — list shape
# --------------------------------------------------------------------------


def test_parse_transfers_skips_unparseable_items() -> None:
    """One bad apple shouldn't poison the rest."""
    body = {
        "data": [
            {"transaction_id": "ok", "amount_str": "1000000", "block": 1},
            {"missing_id": True},  # malformed
        ]
    }
    out = _parse_transfers(body)
    assert len(out) == 1
    assert out[0].tx_hash == "ok"


def test_parse_transfers_handles_empty_response() -> None:
    assert _parse_transfers({"data": []}) == []
    assert _parse_transfers({}) == []


def test_parse_transfers_supports_token_transfers_alias() -> None:
    """Tronscan has used both 'data' and 'token_transfers' as the
    list-key over time; parser handles both."""
    body = {"token_transfers": [_good_record()]}
    out = _parse_transfers(body)
    assert len(out) == 1


# --------------------------------------------------------------------------
# TronscanClient — HTTP mock
# --------------------------------------------------------------------------


class _MockResponse:
    def __init__(self, status: int, body: dict | str):
        self.status = status
        self._body = body

    async def __aenter__(self) -> _MockResponse:
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        pass

    async def text(self) -> str:
        return (
            self._body
            if isinstance(self._body, str)
            else json.dumps(self._body)
        )

    async def json(self) -> dict:
        return self._body  # type: ignore[return-value]


class _MockSession:
    """Minimal stand-in for aiohttp.ClientSession.

    Captures the (url, params) pair the client builds so tests can
    assert on URL composition without spinning up a real server.
    """

    def __init__(self, response: _MockResponse) -> None:
        self.response = response
        self.calls: list[tuple[str, dict]] = []

    def get(self, url: str, params: dict | None = None, timeout=None):
        self.calls.append((url, params or {}))
        return self.response

    async def close(self) -> None:
        pass


def _run(coro):
    return asyncio.run(coro)


def test_client_builds_correct_url_and_params() -> None:
    body = {"data": []}
    session = _MockSession(_MockResponse(200, body))
    client = TronscanClient(
        api_base="https://example.com",
        contract_address="USDT-CONTRACT",
        session=session,  # type: ignore[arg-type]
    )

    _run(client.list_recent_transfers(to_address="TR-receive"))

    assert len(session.calls) == 1
    url, params = session.calls[0]
    assert url == "https://example.com/api/token_trc20/transfers"
    assert params == {
        "contract_address": "USDT-CONTRACT",
        "toAddress": "TR-receive",
        "limit": "50",
        "confirm": "true",
    }


def test_client_raises_on_4xx() -> None:
    session = _MockSession(_MockResponse(400, "bad request"))
    client = TronscanClient(
        api_base="https://example.com",
        contract_address="USDT-CONTRACT",
        session=session,  # type: ignore[arg-type]
    )

    with pytest.raises(Trc20ClientError, match="HTTP 400"):
        _run(client.list_recent_transfers(to_address="TR-receive"))


def test_client_raises_on_network_error() -> None:
    class _ExplodingSession:
        def get(self, *args, **kwargs):
            raise aiohttp.ClientError("connection refused")

        async def close(self) -> None:
            pass

    client = TronscanClient(
        api_base="https://example.com",
        contract_address="USDT-CONTRACT",
        session=_ExplodingSession(),  # type: ignore[arg-type]
    )

    with pytest.raises(Trc20ClientError, match="network"):
        _run(client.list_recent_transfers(to_address="TR-receive"))


def test_client_returns_parsed_transfers() -> None:
    body = {
        "data": [
            {
                "transaction_id": "tx-1",
                "amount_str": "1223000",
                "block_ts": 1746100800000,
                "confirmed": True,
                "block": 100,
                "data": b"ABCDEFGH".hex(),
            }
        ]
    }
    session = _MockSession(_MockResponse(200, body))
    client = TronscanClient(
        api_base="https://example.com",
        contract_address="USDT-CONTRACT",
        session=session,  # type: ignore[arg-type]
    )

    transfers = _run(client.list_recent_transfers(to_address="TR-receive"))

    assert len(transfers) == 1
    assert transfers[0].amount_millis == 1223
    assert transfers[0].memo == "ABCDEFGH"


# --------------------------------------------------------------------------
# Fallback chain
# --------------------------------------------------------------------------


class _SequentialSession:
    """Session that fails on ``primary_base`` and succeeds on any other.

    Used to test the fallback chain without real network calls.
    Tracks (url, base) pairs for all calls made.
    """

    def __init__(self, fail_base: str, success_body: dict) -> None:
        self._fail_base = fail_base.rstrip("/")
        self._success_body = success_body
        self.calls: list[str] = []  # base prefixes actually called

    def get(self, url: str, params: dict | None = None, timeout=None):
        # Extract base from the URL (everything before /api/)
        base = url.split("/api/")[0]
        self.calls.append(base)
        if base == self._fail_base:
            return _MockResponse(500, "server error")
        return _MockResponse(200, self._success_body)

    async def close(self) -> None:
        pass


def test_fallback_kicks_in_after_threshold_failures() -> None:
    """Active base rotates after ``fallback_threshold`` consecutive failures.

    Semantics: within a single call the client tries all bases in order.
    Before the threshold is reached the call still succeeds via the fallback
    without permanently changing the active base.  On the call where the
    threshold is crossed, the active base pointer rotates to the next entry —
    subsequent calls start from the fallback directly (no primary retry).
    """
    success_body = {"data": [_good_record(transaction_id="tx-fallback")]}
    # Primary (index 0) always fails; fallback (index 1) always succeeds.
    session = _SequentialSession(
        fail_base="https://primary.example.com",
        success_body=success_body,
    )

    client = TronscanClient(
        api_bases=[
            "https://primary.example.com",
            "https://fallback.example.com",
        ],
        contract_address="USDT-CONTRACT",
        session=session,  # type: ignore[arg-type]
        fallback_threshold=3,
    )

    # Calls 1–2: primary fails (count < 3), fallback succeeds within same
    # call.  Active base is still primary (idx=0).
    for call_num in range(1, 3):
        transfers = _run(client.list_recent_transfers(to_address="TR-receive"))
        assert (
            len(transfers) == 1
        ), f"call {call_num}: expected fallback success"
    assert client._active_base_idx == 0, "active base should still be primary"

    # Call 3: primary fails (count reaches 3 = threshold) → active base
    # rotates to fallback (idx=1); fallback succeeds within same call.
    transfers = _run(client.list_recent_transfers(to_address="TR-receive"))
    assert len(transfers) == 1
    assert transfers[0].tx_hash == "tx-fallback"
    assert client._active_base_idx == 1, "active base should now be fallback"

    # Call 4+: now the active base is fallback directly — primary is NOT
    # tried again.
    prev_call_count = len(session.calls)
    _run(client.list_recent_transfers(to_address="TR-receive"))
    new_calls = session.calls[prev_call_count:]
    assert len(new_calls) == 1
    assert "fallback" in new_calls[0]


def test_fallback_switch_emits_health_failure() -> None:
    """When the fallback switch fires, trc20_health.record_failure is
    called exactly once with reason='fallback_switch:<new_base>'."""
    health_calls: list[str] = []

    import ops.billing.trc20_client as _client_mod

    original_method = _client_mod.TronscanClient._record_fallback_switch

    @staticmethod  # type: ignore[misc]
    async def _patched(new_base: str) -> None:
        health_calls.append(f"fallback_switch:{new_base}")

    _client_mod.TronscanClient._record_fallback_switch = _patched  # type: ignore[assignment]

    try:
        success_body = {"data": []}
        session = _SequentialSession(
            fail_base="https://primary.example.com",
            success_body=success_body,
        )
        client = TronscanClient(
            api_bases=[
                "https://primary.example.com",
                "https://fallback.example.com",
            ],
            contract_address="USDT-CONTRACT",
            session=session,  # type: ignore[arg-type]
            fallback_threshold=2,
        )
        # Call 1: primary fails (count=1 < 2), fallback succeeds — no switch yet.
        _run(client.list_recent_transfers(to_address="TR-receive"))
        assert len(health_calls) == 0

        # Call 2: primary fails (count=2 >= threshold) → switch fires, fallback
        # succeeds within same call.
        _run(client.list_recent_transfers(to_address="TR-receive"))
    finally:
        _client_mod.TronscanClient._record_fallback_switch = original_method  # type: ignore[assignment]

    # Exactly one switch notification on call 2, mentioning the fallback base.
    assert len(health_calls) == 1
    assert "fallback_switch:" in health_calls[0]
    assert "fallback.example.com" in health_calls[0]


def test_no_fallback_configured_raises_normal() -> None:
    """With a single-element api_bases list, failures raise normally
    without any fallback rotation — behaviour identical to pre-resilience
    code."""
    session = _MockSession(_MockResponse(500, "error"))
    client = TronscanClient(
        api_bases=["https://only.example.com"],
        contract_address="USDT-CONTRACT",
        session=session,  # type: ignore[arg-type]
    )

    with pytest.raises(Trc20ClientError):
        _run(client.list_recent_transfers(to_address="TR-receive"))

    # Only one HTTP call was made (no retry to another base)
    assert len(session.calls) == 1


def test_trongrid_response_schema_parsed() -> None:
    """Parser handles Trongrid-style ``token_transfers`` key and
    ``block_timestamp`` field instead of ``block_ts``."""
    trongrid_body = {
        "token_transfers": [
            {
                "transaction_id": "tg-tx-1",
                "amount_str": "5000000",  # 5 USDT on-chain → 5000 millis
                "block_timestamp": 1746100800000,
                "confirmed": True,
                "block": 42,
            }
        ]
    }
    session = _MockSession(_MockResponse(200, trongrid_body))
    client = TronscanClient(
        api_base="https://api.trongrid.io",
        contract_address="USDT-CONTRACT",
        session=session,  # type: ignore[arg-type]
    )

    transfers = _run(client.list_recent_transfers(to_address="TR-receive"))

    assert len(transfers) == 1
    assert transfers[0].tx_hash == "tg-tx-1"
    assert transfers[0].amount_millis == 5000
    assert transfers[0].block_number == 42
