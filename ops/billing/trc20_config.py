"""TRC20 environment configuration + provider factory.

Separate module from ``ops.billing.config`` because:

- ``config.py`` already covers cross-provider concerns (Fernet key for
  EPay merchant secrets, panel public URL, trusted-proxy CIDRs); piling
  TRC20 there would muddy responsibilities.
- TRC20 config is **all opt-in** — defaults disable the provider, so an
  operator who never enables it pays no boot cost and triggers no
  fail-loud paths.
- The provider factory in ``providers/__init__.py`` reads from here,
  not from ``config.py``, keeping the import graph one-way.

Why ``BILLING_TRC20_RATE_FEN_PER_USDT`` is operator-set, not auto-fetched
------------------------------------------------------------------------
The exchange rate at invoice-creation is the operator's snapshot; the
user should pay that exact amount (down to the millis). Auto-fetching
introduces:

- One more API dependency (CoinGecko / Binance ticker) at the worst
  possible time (peak payment hours).
- A market-fluctuation surface where the rate changes between the
  user clicking "checkout" and submitting the tx, leaving us with
  ambiguous matching.

Operator workflow: review the live rate weekly, set the env, redeploy.
For a 7.20-CNY/USDT operator-locked rate, set
``BILLING_TRC20_RATE_FEN_PER_USDT=720``. The cost of running 1-2% off
market for a few days is negligible vs. on-call exposure to a third
ticker outage.

Why MIN_CONFIRMATIONS=1 is the MVP default
------------------------------------------
Tron has 3-second block times and `confirmed=true` from Tronscan
indicates the tx is in a block irreversibility-checked. The 3+
confirmations doctrine is borrowed from Bitcoin and doesn't translate
directly. We expose the env var so paranoid operators can dial up to
3 / 5 / 19 (the latter being Tron's super-representative round
boundary), but the default keeps user latency low.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from decouple import config

from ops.billing.providers.trc20 import Trc20Provider

logger = logging.getLogger(__name__)


class Trc20Misconfigured(RuntimeError):
    """Raised at provider-instantiation time when ``BILLING_TRC20_ENABLED``
    is set but the supporting env vars are missing.

    We choose fail-loud over silent disable because an operator who set
    ``ENABLED=true`` clearly intended TRC20 to work; ignoring the gap
    would surface as ghost user-facing errors at checkout.
    """


# Master switch. Defaults False so a fresh deploy without TRC20 setup
# doesn't surface checkout errors — the provider simply isn't visible
# in get_provider("trc20").
BILLING_TRC20_ENABLED: bool = config(
    "BILLING_TRC20_ENABLED", default=False, cast=bool
)

# Public receive address (TRC20). Operator's cold-wallet address.
# **Never** put a private key in env; the panel never signs txs.
BILLING_TRC20_RECEIVE_ADDRESS: str = config(
    "BILLING_TRC20_RECEIVE_ADDRESS", default=""
)

# Operator-locked rate, fen per 1 USDT. 720 = 7.20 CNY/USDT.
# Setting this requires intent — no useful default exists.
BILLING_TRC20_RATE_FEN_PER_USDT: int = int(
    config("BILLING_TRC20_RATE_FEN_PER_USDT", default=0)
)

# Per-invoice memo salt. Memos = HMAC(salt, invoice_id), so a
# sniffer who sees invoice INV-42's memo cannot predict INV-43's.
# Required when TRC20 is enabled.
BILLING_TRC20_MEMO_SALT: str = config("BILLING_TRC20_MEMO_SALT", default="")

# Tronscan public API base — no key required, 100 req/s public limit
# is enormous overkill for our 30-s poll. Falls back to a private
# Trongrid endpoint by overriding this var if Tronscan is degraded.
BILLING_TRC20_TRONSCAN_API_BASE: str = config(
    "BILLING_TRC20_TRONSCAN_API_BASE",
    default="https://apilist.tronscanapi.com",
)

# Block confirmations gate before we accept a tx as final.
# Default 1 — see module docstring on Tron block-time math.
BILLING_TRC20_MIN_CONFIRMATIONS: int = int(
    config("BILLING_TRC20_MIN_CONFIRMATIONS", default=1)
)

# Poll interval. 30s matches the SPEC's "user paid → state visible"
# SLA; halving costs more API calls per hour for negligible UX gain.
BILLING_TRC20_POLL_INTERVAL: int = int(
    config("BILLING_TRC20_POLL_INTERVAL", default=30)
)

# How long after invoice creation we keep polling. Past this, the
# applier has already flipped the invoice to ``expired`` (via the
# A.5 reaper); we just stop wasting API quota on it.
BILLING_TRC20_PAYMENT_WINDOW_MINUTES: int = int(
    config("BILLING_TRC20_PAYMENT_WINDOW_MINUTES", default=30)
)

# USDT contract on Tron. The Tronscan endpoint we use accepts a
# ``contract_address`` filter; this is the canonical "Tether USD"
# (TRC20) contract. Hardcoding is fine — a contract migration would
# require a wider operator-side response than an env var anyway.
BILLING_TRC20_USDT_CONTRACT: str = config(
    "BILLING_TRC20_USDT_CONTRACT",
    default="TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
)


@lru_cache(maxsize=1)
def get_trc20_provider() -> Trc20Provider:
    """Construct the singleton Trc20Provider from env.

    Raises :class:`Trc20Misconfigured` if ``BILLING_TRC20_ENABLED`` is
    True but supporting vars are missing. Returns a memoised instance
    so repeated calls are cheap.

    Tests can clear via ``get_trc20_provider.cache_clear()`` after
    ``_reload_for_tests``.
    """
    if not BILLING_TRC20_ENABLED:
        raise Trc20Misconfigured(
            "TRC20 provider not enabled. Set BILLING_TRC20_ENABLED=true "
            "and configure BILLING_TRC20_{RECEIVE_ADDRESS, "
            "RATE_FEN_PER_USDT, MEMO_SALT}."
        )
    missing = []
    if not BILLING_TRC20_RECEIVE_ADDRESS:
        missing.append("BILLING_TRC20_RECEIVE_ADDRESS")
    if BILLING_TRC20_RATE_FEN_PER_USDT <= 0:
        missing.append("BILLING_TRC20_RATE_FEN_PER_USDT")
    if not BILLING_TRC20_MEMO_SALT:
        missing.append("BILLING_TRC20_MEMO_SALT")
    if missing:
        raise Trc20Misconfigured(
            f"TRC20 enabled but required env vars missing: {missing}. "
            "Either disable BILLING_TRC20_ENABLED or fill the gaps."
        )

    return Trc20Provider(
        receive_address=BILLING_TRC20_RECEIVE_ADDRESS,
        rate_fen_per_usdt=BILLING_TRC20_RATE_FEN_PER_USDT,
        memo_salt=BILLING_TRC20_MEMO_SALT,
    )


def _reload_for_tests(
    *,
    enabled: bool = False,
    receive_address: str = "",
    rate_fen_per_usdt: int = 0,
    memo_salt: str = "",
    tronscan_api_base: str = "https://apilist.tronscanapi.com",
    min_confirmations: int = 1,
    poll_interval: int = 30,
    payment_window_minutes: int = 30,
) -> None:
    """Test-only hook to rewire module state without re-importing.

    Mirrors :func:`ops.billing.config._reload_for_tests` shape so test
    suites use the same idiom across both config modules.
    """
    global \
        BILLING_TRC20_ENABLED, \
        BILLING_TRC20_RECEIVE_ADDRESS, \
        BILLING_TRC20_RATE_FEN_PER_USDT, \
        BILLING_TRC20_MEMO_SALT, \
        BILLING_TRC20_TRONSCAN_API_BASE, \
        BILLING_TRC20_MIN_CONFIRMATIONS, \
        BILLING_TRC20_POLL_INTERVAL, \
        BILLING_TRC20_PAYMENT_WINDOW_MINUTES
    BILLING_TRC20_ENABLED = enabled
    BILLING_TRC20_RECEIVE_ADDRESS = receive_address
    BILLING_TRC20_RATE_FEN_PER_USDT = rate_fen_per_usdt
    BILLING_TRC20_MEMO_SALT = memo_salt
    BILLING_TRC20_TRONSCAN_API_BASE = tronscan_api_base
    BILLING_TRC20_MIN_CONFIRMATIONS = min_confirmations
    BILLING_TRC20_POLL_INTERVAL = poll_interval
    BILLING_TRC20_PAYMENT_WINDOW_MINUTES = payment_window_minutes
    get_trc20_provider.cache_clear()


__all__ = [
    "BILLING_TRC20_ENABLED",
    "BILLING_TRC20_MEMO_SALT",
    "BILLING_TRC20_MIN_CONFIRMATIONS",
    "BILLING_TRC20_PAYMENT_WINDOW_MINUTES",
    "BILLING_TRC20_POLL_INTERVAL",
    "BILLING_TRC20_RATE_FEN_PER_USDT",
    "BILLING_TRC20_RECEIVE_ADDRESS",
    "BILLING_TRC20_TRONSCAN_API_BASE",
    "BILLING_TRC20_USDT_CONTRACT",
    "Trc20Misconfigured",
    "get_trc20_provider",
]
