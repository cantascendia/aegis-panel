"""
Tests for ``ops.billing.providers.trc20`` — TRC20Provider + memo helpers.

Pure logic; no DB, no network. Each test pins one rule from the
module docstring.
"""

from __future__ import annotations

import asyncio

import pytest

from ops.billing.providers.trc20 import (
    Trc20Provider,
    generate_memo,
    is_valid_memo,
)

# --------------------------------------------------------------------------
# Memo generation
# --------------------------------------------------------------------------


def test_generate_memo_is_deterministic() -> None:
    """Same (invoice_id, salt) → same memo. Crucial for poller-side
    verification without DB lookup."""
    a = generate_memo(42, salt="test-salt")
    b = generate_memo(42, salt="test-salt")
    assert a == b


def test_generate_memo_changes_with_salt() -> None:
    """Different operators must not collide on memos when sharing
    a wallet."""
    a = generate_memo(42, salt="op-A")
    b = generate_memo(42, salt="op-B")
    assert a != b


def test_generate_memo_changes_with_invoice_id() -> None:
    a = generate_memo(42, salt="x")
    b = generate_memo(43, salt="x")
    assert a != b


def test_generate_memo_uses_safe_alphabet() -> None:
    """Memo must avoid confusable glyphs (0/O/I/L/1)."""
    memo = generate_memo(99, salt="x")
    assert all(ch not in memo for ch in "0OIL1")
    assert len(memo) == 8


def test_generate_memo_rejects_zero_invoice_id() -> None:
    with pytest.raises(ValueError, match="positive"):
        generate_memo(0, salt="x")


def test_is_valid_memo_accepts_generated() -> None:
    memo = generate_memo(42, salt="x")
    assert is_valid_memo(memo)


def test_is_valid_memo_rejects_wrong_length() -> None:
    assert not is_valid_memo("ABCDEFG")  # 7 chars
    assert not is_valid_memo("ABCDEFGHI")  # 9 chars
    assert not is_valid_memo("")


def test_is_valid_memo_rejects_unsafe_glyphs() -> None:
    assert not is_valid_memo("ABCD0EFG")  # contains 0
    assert not is_valid_memo("ABCDOEFG")  # contains O
    assert not is_valid_memo("ABCDIEFG")  # contains I


# --------------------------------------------------------------------------
# Provider construction
# --------------------------------------------------------------------------


def test_provider_requires_receive_address() -> None:
    with pytest.raises(ValueError, match="receive_address"):
        Trc20Provider(receive_address="", rate_fen_per_usdt=720, memo_salt="s")


def test_provider_requires_positive_rate() -> None:
    with pytest.raises(ValueError, match="rate_fen_per_usdt"):
        Trc20Provider(
            receive_address="TR-x", rate_fen_per_usdt=0, memo_salt="s"
        )


def test_provider_requires_memo_salt() -> None:
    """Empty salt makes memos predictable from invoice_id, opening
    a memo-spoof attack. Module docstring documents this risk."""
    with pytest.raises(ValueError, match="memo_salt"):
        Trc20Provider(
            receive_address="TR-x", rate_fen_per_usdt=720, memo_salt=""
        )


# --------------------------------------------------------------------------
# create_invoice
# --------------------------------------------------------------------------


def _provider() -> Trc20Provider:
    return Trc20Provider(
        receive_address="TRtest123abc",
        rate_fen_per_usdt=720,
        memo_salt="test-salt",
    )


def _create(invoice_id: int = 100, amount_fen: int = 880) -> dict:
    """Run create_invoice synchronously and unpack to a dict."""
    p = _provider()
    result = asyncio.run(
        p.create_invoice(
            invoice_id=invoice_id,
            amount_cny_fen=amount_fen,
            subject="Test plan",
            success_url="/success",
            cancel_url="/cancel",
        )
    )
    return {
        "provider_invoice_id": result.provider_invoice_id,
        "payment_url": result.payment_url,
        "extra": result.extra_payload,
    }


def test_create_invoice_returns_memo_as_provider_invoice_id() -> None:
    """The provider_invoice_id is the memo — webhook dedup keys off it."""
    out = _create(invoice_id=100)
    assert is_valid_memo(out["provider_invoice_id"])
    assert out["provider_invoice_id"] == out["extra"]["memo"]


def test_create_invoice_returns_in_app_payment_url() -> None:
    """payment_url is a panel-relative path, not an external URL —
    matches docstring spec for in-app rendering."""
    out = _create(invoice_id=42)
    assert out["payment_url"] == "/billing/trc20/42"


def test_create_invoice_computes_usdt_millis_from_rate() -> None:
    """¥8.80 at 7.20 CNY/USDT → ceil(880 * 1000 / 720) = 1223 millis."""
    out = _create(invoice_id=100, amount_fen=880)
    assert out["extra"]["expected_amount_millis"] == 1223


def test_create_invoice_records_rate_snapshot() -> None:
    """Rate snapshot must land in extra_payload so PaymentEvent's
    audit trail can reproduce the conversion."""
    out = _create(invoice_id=100)
    assert out["extra"]["rate_fen_per_usdt_at_create"] == 720


def test_create_invoice_includes_receive_address() -> None:
    out = _create(invoice_id=100)
    assert out["extra"]["receive_address"] == "TRtest123abc"


# --------------------------------------------------------------------------
# handle_webhook — TRC20 has none
# --------------------------------------------------------------------------


def test_handle_webhook_raises_unhandled_event_type() -> None:
    """TRC20 has no webhook (we poll); abstract method raises
    UnhandledEventType so route handlers never accidentally wire one."""
    from ops.billing.providers.base import UnhandledEventType

    p = _provider()
    with pytest.raises(UnhandledEventType, match="no webhook"):
        asyncio.run(p.handle_webhook({}, b""))
