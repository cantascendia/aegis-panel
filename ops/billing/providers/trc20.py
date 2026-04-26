"""TRC20 USDT direct-payment adapter.

Distinct from the EPay path: there is **no third-party gateway and no
webhook**. The user receives a TRC20 address + memo + exact USDT
amount, opens their own wallet, sends the transaction, and we **poll**
the Tron blockchain until a matching transfer lands.

Why polling over webhook
------------------------
- Tron itself doesn't push webhooks — confirmations come from chain
  observation. Tronscan / Trongrid / our own node are all "we read".
- Pull-based suits the operator's threat model: no third-party gets a
  callback we have to authenticate; the only trust boundary is "this
  RPC endpoint says this tx is on-chain".
- Pricing is operator-friendly: no merchant fees, just gas paid by the
  sender. Our cost is ~30s of poll latency.

Singleton, env-driven
---------------------
Unlike EPay (one ``PaymentChannel`` row per 码商), TRC20 is one
configuration globally. The receive address is the operator's cold
wallet; rotating it requires a config flip + redeploy, not a DB row.
``ops.billing.providers.get_provider("trc20")`` constructs from env
vars in :mod:`ops.billing.trc20_config`.

Memo strategy
-------------
Each invoice gets a deterministic 8-char alphanumeric memo derived
from ``invoice_id``. Memos are short enough to type if a wallet asks,
unique within the universe of open invoices, and reproducible from
``invoice_id`` alone (no DB round-trip needed to verify a tx).

We use a strict alphabet (``0-9 A-Z`` minus ``0OIL1`` to avoid
human-confusion glyphs) and a salted hash so memos aren't trivially
guessable from invoice IDs (a sniffer who sees `INV-42` shouldn't be
able to predict `INV-43`'s memo and try to claim it).

Wallet support reality
----------------------
~half of TRC20-capable mobile wallets surface the optional ``data``
field where memos live. The other half drop it silently. The poller
therefore has a **two-tier match**: memo-match first (O(1), unambiguous),
amount-match second (with cents-dither so concurrent invoices don't
collide). See :mod:`ops.billing.trc20_matcher`.

In-app payment URL
------------------
``payment_url`` returns a path on **our own panel** (``/billing/trc20/<id>``),
not an external URL. The dashboard renders that route as
"copy address / copy memo / show QR / live status" — all read-only,
no provider interaction. R.4-style follow-up: the dashboard route is
A.4's territory; this provider only declares the URL contract.
"""

from __future__ import annotations

import hashlib
import hmac
from collections.abc import Mapping

from ops.billing.providers.base import (
    BasePaymentProvider,
    CreateInvoiceResult,
    UnhandledEventType,
    WebhookOutcome,
)

# Alphabet for memos: uppercase alnum minus glyphs commonly confused
# in phone-typed scenarios. Length 30, plenty of entropy at 8 chars
# (30^8 ≈ 6.5e11).
_MEMO_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
_MEMO_LENGTH = 8


class Trc20Provider(BasePaymentProvider):
    """Singleton TRC20 USDT provider.

    Construct via :func:`ops.billing.providers.get_provider("trc20")`,
    which reads :mod:`ops.billing.trc20_config` and passes the config
    through. Direct construction is allowed for tests / scripts that
    want isolated state.
    """

    kind = "trc20"

    def __init__(
        self,
        *,
        receive_address: str,
        rate_fen_per_usdt: int,
        memo_salt: str,
        in_app_path_prefix: str = "/billing/trc20",
    ) -> None:
        if not receive_address:
            raise ValueError(
                "receive_address must be a non-empty TRC20 address"
            )
        if rate_fen_per_usdt <= 0:
            raise ValueError(
                f"rate_fen_per_usdt must be positive, got {rate_fen_per_usdt}"
            )
        if not memo_salt:
            raise ValueError(
                "memo_salt must be set; otherwise memos are predictable from "
                "invoice_id alone, allowing an attacker who sees invoice INV-42 "
                "to predict INV-43's memo"
            )
        self._receive_address = receive_address
        self._rate_fen_per_usdt = rate_fen_per_usdt
        self._memo_salt = memo_salt
        self._in_app_path_prefix = in_app_path_prefix.rstrip("/")

    @property
    def receive_address(self) -> str:
        """Public TRC20 receive address (safe to log / display)."""
        return self._receive_address

    @property
    def rate_fen_per_usdt(self) -> int:
        """Current snapshot rate (fen per 1 USDT). Set at invoice
        creation; recorded in ``PaymentEvent.payload_json`` for
        audit."""
        return self._rate_fen_per_usdt

    async def create_invoice(
        self,
        invoice_id: int,
        amount_cny_fen: int,
        subject: str,
        success_url: str,
        cancel_url: str,
    ) -> CreateInvoiceResult:
        """Compute memo + USDT-millis amount; return an in-app URL.

        ``subject`` / ``success_url`` / ``cancel_url`` are unused by
        TRC20: there's no external gateway redirect, so the invoice
        details + status are rendered in the panel itself.

        The returned ``payment_url`` is a relative path on the panel,
        e.g. ``/billing/trc20/42``. Caller is responsible for prefixing
        the panel origin if it needs an absolute URL.
        """
        _ = subject  # Reserved for future per-tx labelling.
        _ = success_url
        _ = cancel_url

        # Local import dodges a circular: pricing → providers → pricing.
        from ops.billing.pricing import convert_fen_to_usdt_millis

        memo = generate_memo(invoice_id, salt=self._memo_salt)
        expected_millis = convert_fen_to_usdt_millis(
            amount_cny_fen, self._rate_fen_per_usdt
        )
        payment_url = f"{self._in_app_path_prefix}/{invoice_id}"

        return CreateInvoiceResult(
            provider_invoice_id=memo,
            payment_url=payment_url,
            extra_payload={
                "receive_address": self._receive_address,
                "memo": memo,
                "expected_amount_millis": expected_millis,
                "rate_fen_per_usdt_at_create": self._rate_fen_per_usdt,
            },
        )

    async def handle_webhook(
        self,
        params: Mapping[str, str],
        raw_body: bytes,
    ) -> WebhookOutcome:
        """TRC20 has no webhook — payments arrive via the poller.

        We could expose a ``/webhook/trc20`` endpoint that 404s
        explicitly, but raising :class:`UnhandledEventType` matches the
        "well-formed but no-op" contract; route handlers know how to
        translate that to a clean response.

        In practice this method is never reached: nothing in the panel
        routes a TRC20 webhook to the provider. It exists because
        :class:`BasePaymentProvider` declares it abstract.
        """
        _ = params
        _ = raw_body
        raise UnhandledEventType(
            "TRC20 has no webhook callback; payments are detected by "
            "the trc20_poller scheduler task. If you see this exception "
            "in logs, a webhook route was wired in error — remove it."
        )


# ---------------------------------------------------------------------
# Memo generation — pure helper, exported for the matcher's benefit
# ---------------------------------------------------------------------


def generate_memo(invoice_id: int, *, salt: str) -> str:
    """Deterministic 8-char memo for a given invoice + salt.

    HMAC-SHA256 of ``str(invoice_id)`` keyed by ``salt``, mapped onto
    ``_MEMO_ALPHABET``. Same (invoice_id, salt) → same memo, so the
    poller can verify a memo without a DB lookup.

    Different operators with different ``BILLING_TRC20_MEMO_SALT``
    won't collide on memos — useful when one operator runs multiple
    panels under the same wallet (rare, but free).
    """
    if invoice_id <= 0:
        raise ValueError(f"invoice_id must be positive, got {invoice_id}")
    digest = hmac.new(
        salt.encode("utf-8"),
        str(invoice_id).encode("ascii"),
        hashlib.sha256,
    ).digest()

    # Interpret the digest as a stream of unsigned bytes; map each
    # byte mod len(alphabet) to a memo char. We use the first 8 bytes
    # — plenty of entropy and trivially reversible logic for tests.
    return "".join(
        _MEMO_ALPHABET[b % len(_MEMO_ALPHABET)] for b in digest[:_MEMO_LENGTH]
    )


def is_valid_memo(memo: str) -> bool:
    """Cheap structural check for poller-side filtering.

    Accepts only memos with the right length and alphabet. Tron
    transactions whose ``data`` field decodes to garbage are filtered
    out by this before we even hit the DB lookup.
    """
    if len(memo) != _MEMO_LENGTH:
        return False
    return all(ch in _MEMO_ALPHABET for ch in memo)


__all__ = [
    "Trc20Provider",
    "generate_memo",
    "is_valid_memo",
]
