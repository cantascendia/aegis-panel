"""
Tests for ``ops.billing.trc20_matcher`` — pure tx → invoice matching.

No DB, no network. Each case pins one branch of the two-tier
matching strategy + edge cases (window, confirmations, dither).
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from ops.billing.trc20_matcher import (
    CandidateInvoice,
    Trc20Transfer,
    add_cents_dither,
    find_matching_transfer,
)

_NOW = datetime(2026, 5, 1, 12, 0, 0)
_WINDOW = timedelta(minutes=30)


def _transfer(
    *,
    tx_hash: str = "txABC",
    amount_millis: int = 1223,
    memo: str | None = None,
    timestamp: datetime | None = None,
    confirmed: bool = True,
    block_number: int = 100,
) -> Trc20Transfer:
    return Trc20Transfer(
        tx_hash=tx_hash,
        amount_millis=amount_millis,
        memo=memo,
        timestamp=timestamp or _NOW + timedelta(minutes=5),
        confirmed=confirmed,
        block_number=block_number,
    )


def _invoice(
    *,
    invoice_id: int = 100,
    memo: str = "ABCDEFGH",
    expected_amount_millis: int = 1223,
    created_at: datetime | None = None,
) -> CandidateInvoice:
    return CandidateInvoice(
        invoice_id=invoice_id,
        memo=memo,
        expected_amount_millis=expected_amount_millis,
        created_at=created_at or _NOW,
    )


# --------------------------------------------------------------------------
# add_cents_dither
# --------------------------------------------------------------------------


def test_add_cents_dither_adds_invoice_id_mod_1000() -> None:
    assert add_cents_dither(5000, 100) == 5100
    assert add_cents_dither(5000, 1234) == 5234  # mod 1000


def test_add_cents_dither_disambiguates_concurrent_invoices() -> None:
    """Two invoices for the same plan must produce distinct totals."""
    inv_a = add_cents_dither(5000, 101)
    inv_b = add_cents_dither(5000, 102)
    assert inv_a != inv_b


def test_add_cents_dither_rejects_non_positive_invoice_id() -> None:
    with pytest.raises(ValueError, match="positive"):
        add_cents_dither(5000, 0)


def test_add_cents_dither_rejects_negative_amount() -> None:
    with pytest.raises(ValueError, match=">= 0"):
        add_cents_dither(-1, 100)


# --------------------------------------------------------------------------
# Memo match (Strategy 1)
# --------------------------------------------------------------------------


def test_memo_match_takes_precedence() -> None:
    """If memo + amount both match a tx, memo path wins (canonical)."""
    invoice = _invoice(memo="ABCDEFGH")
    transfers = [_transfer(memo="ABCDEFGH")]
    match = find_matching_transfer(
        transfers,
        invoice,
        payment_window=_WINDOW,
        min_confirmations_satisfied=True,
    )
    assert match is not None
    assert match.tx_hash == "txABC"


def test_memo_mismatch_falls_through_to_amount_match() -> None:
    invoice = _invoice(memo="ABCDEFGH", expected_amount_millis=1223)
    transfers = [_transfer(memo="WRONGSAL", amount_millis=1223)]
    match = find_matching_transfer(
        transfers,
        invoice,
        payment_window=_WINDOW,
        min_confirmations_satisfied=True,
    )
    # Memo "WRONGSAL" wouldn't validate as a memo (uses W S which are
    # in alphabet — but it doesn't match invoice memo). Amount matches,
    # so amount path returns it.
    assert match is not None


def test_memo_match_respects_payment_window() -> None:
    """Stale memo from beyond the window: rejected even if it matches.
    Defends against memo replay from old invoices."""
    invoice = _invoice(memo="ABCDEFGH")
    transfers = [
        _transfer(
            memo="ABCDEFGH", timestamp=_NOW + timedelta(minutes=60)
        )  # outside window
    ]
    match = find_matching_transfer(
        transfers,
        invoice,
        payment_window=_WINDOW,
        min_confirmations_satisfied=True,
    )
    assert match is None


def test_invalid_memo_format_ignored_for_memo_match() -> None:
    """Garbage in tx data field shouldn't accidentally match anything."""
    invoice = _invoice(memo="ABCDEFGH", expected_amount_millis=1223)
    transfers = [
        _transfer(
            memo="garbage", amount_millis=999
        )  # wrong length AND wrong amount
    ]
    match = find_matching_transfer(
        transfers,
        invoice,
        payment_window=_WINDOW,
        min_confirmations_satisfied=True,
    )
    assert match is None


# --------------------------------------------------------------------------
# Amount match (Strategy 2)
# --------------------------------------------------------------------------


def test_amount_match_when_no_memo_present() -> None:
    """Most mobile wallets strip the memo; amount + window must work
    as the fallback."""
    invoice = _invoice(expected_amount_millis=1223)
    transfers = [_transfer(memo=None, amount_millis=1223)]
    match = find_matching_transfer(
        transfers,
        invoice,
        payment_window=_WINDOW,
        min_confirmations_satisfied=True,
    )
    assert match is not None


def test_amount_must_be_exact_no_fuzzy() -> None:
    """User pays 0.999 USDT for a 1.000 USDT invoice → no match,
    user must re-send. Avoids under-pay / over-pay accounting."""
    invoice = _invoice(expected_amount_millis=1000)
    transfers = [_transfer(memo=None, amount_millis=999)]
    match = find_matching_transfer(
        transfers,
        invoice,
        payment_window=_WINDOW,
        min_confirmations_satisfied=True,
    )
    assert match is None


def test_amount_match_respects_window() -> None:
    invoice = _invoice(expected_amount_millis=1223)
    transfers = [
        _transfer(
            memo=None,
            amount_millis=1223,
            timestamp=_NOW - timedelta(minutes=1),  # before invoice creation
        )
    ]
    match = find_matching_transfer(
        transfers,
        invoice,
        payment_window=_WINDOW,
        min_confirmations_satisfied=True,
    )
    assert match is None


# --------------------------------------------------------------------------
# Confirmations / unconfirmed gating
# --------------------------------------------------------------------------


def test_unconfirmed_transfer_skipped_even_with_memo_match() -> None:
    invoice = _invoice(memo="ABCDEFGH")
    transfers = [_transfer(memo="ABCDEFGH", confirmed=False)]
    match = find_matching_transfer(
        transfers,
        invoice,
        payment_window=_WINDOW,
        min_confirmations_satisfied=True,
    )
    assert match is None


def test_min_confirmations_not_satisfied_returns_none() -> None:
    """Caller-side flag: even if everything else matches, gate
    rejects."""
    invoice = _invoice(memo="ABCDEFGH")
    transfers = [_transfer(memo="ABCDEFGH")]
    match = find_matching_transfer(
        transfers,
        invoice,
        payment_window=_WINDOW,
        min_confirmations_satisfied=False,
    )
    assert match is None


def test_empty_transfer_list_returns_none() -> None:
    assert (
        find_matching_transfer(
            [],
            _invoice(),
            payment_window=_WINDOW,
            min_confirmations_satisfied=True,
        )
        is None
    )
