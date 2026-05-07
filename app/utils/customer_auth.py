"""Customer-side JWT auth — sub URL = credential.

Track B of the Nilou rewrite (`docs/ai-cto/SPEC-dashboard-rewrite.md` §How.Track-B).
The customer portal's `/login` form accepts a subscription URL; the
backend parses `<username>/<key>`, looks up the corresponding User in the
panel DB, validates it (not removed, key matches), and issues a short
15-minute JWT scoped to that user_id.

Why "α subscription URL = credential" instead of email/password:
* Customers already have the URL — zero new infrastructure
* No User table schema change (sub key already stored as `User.key`)
* No SMTP / forgot-password flow needed in MVP
* α-mode tokens are forward-compatible with future β email/password —
  the JWT issuance pipeline is identical, only the credential check changes

Security boundary:
* JWT carries `{"sub": str(user_id), "access": "customer", "exp": now+15min}`
* `access: "customer"` distinguishes from admin's `"admin" / "sudo"` —
  upstream `app/dependencies.py` admin path won't accept customer tokens
* Sub URL leakage = same risk surface as before this feature existed
  (URL was always a bearer token, just for proxy traffic instead of panel)
* No password is stored or transmitted

Forbidden-path guard rails (per `.claude/rules/forbidden-paths.md`):
* This module + `app/routes/customer.py` requires double-sign before merge
* `tests/test_customer_auth.py` MUST hit ≥80% mutation score
* Pre-commit hook scan detects this file path → `requires-double-review`
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

import jwt

from app.config import get_secret_key
from app.utils._aegis_clocks import now_utc_naive

CUSTOMER_TOKEN_EXPIRE_MINUTES = 15


@dataclass(frozen=True)
class ParsedSubUrl:
    username: str
    key: str


def parse_sub_url(sub_url: str) -> ParsedSubUrl | None:
    """Extract `(username, key)` from a subscription URL.

    Accepts these shapes (all produced by `User.subscription_url` in
    `app/db/models.py:271-278` across history):
    * `https://nilou.cc/sub/<username>/<key>`
    * `https://nilou.cc/sub/<username>/<key>/v2ray-json`
    * `nilou.cc/sub/<username>/<key>` (no scheme — browser address bar)
    * `/sub/<username>/<key>` (relative — copy-paste from panel UI)

    Returns `None` for malformed input. Caller MUST treat None as
    "invalid credential" — never log the input verbatim (could be a real
    URL even if rejected here for unrelated reason).

    Username + key are not URL-decoded — Marzneshin's username is
    `[a-z0-9_]{3,32}` and key is 32-char hex, neither contains `%`.
    """
    if not sub_url or not isinstance(sub_url, str):
        return None
    sub_url = sub_url.strip()
    if not sub_url:
        return None

    # Normalize: strip scheme + host, leave just the path.
    if "://" in sub_url:
        try:
            parsed = urlparse(sub_url)
            path = parsed.path
        except (ValueError, AttributeError):
            return None
    elif sub_url.startswith("/"):
        path = sub_url
    else:
        # `nilou.cc/sub/foo/bar` (no scheme) — find first '/'
        first_slash = sub_url.find("/")
        if first_slash == -1:
            return None
        path = sub_url[first_slash:]

    # Path must start with /sub/
    if not path.startswith("/sub/"):
        return None

    # /sub/<username>/<key>[/...optional-suffix]
    parts = path[len("/sub/"):].split("/")
    if len(parts) < 2:
        return None
    username, key = parts[0], parts[1]

    # Bare sanity: username 3-32 chars, key 16-128 hex-ish chars.
    # Final auth happens via DB lookup; these checks just kill obvious
    # garbage early so we don't spam the DB on scraper traffic.
    if not (3 <= len(username) <= 64) or not username:
        return None
    if not (16 <= len(key) <= 128) or not key:
        return None

    return ParsedSubUrl(username=username, key=key)


def create_customer_token(user_id: int) -> str:
    """Issue a JWT for an authenticated customer.

    Caller must have already validated the sub URL against the User row
    (see `app/routes/customer.py` `sub_login` endpoint). This function
    only encodes the payload; it does NOT do any DB lookup itself.
    """
    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("user_id must be a positive int")

    now = now_utc_naive()
    payload = {
        "sub": str(user_id),
        "access": "customer",
        "iat": now,
        "exp": now + timedelta(minutes=CUSTOMER_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, get_secret_key(), algorithm="HS256")


def get_customer_payload(token: str) -> dict | None:
    """Decode + validate a customer JWT, return payload or None.

    Returns None on:
    * malformed JWT
    * expired
    * wrong algorithm
    * `access` claim != "customer" (admin token can't masquerade)
    * `sub` claim missing or non-int
    """
    if not token or not isinstance(token, str):
        return None
    try:
        payload = jwt.decode(token, get_secret_key(), algorithms=["HS256"])
    except jwt.InvalidTokenError:
        return None

    access = payload.get("access")
    if access != "customer":
        return None

    sub = payload.get("sub")
    if not sub:
        return None
    try:
        user_id = int(sub)
    except (ValueError, TypeError):
        return None
    if user_id <= 0:
        return None

    iat_value = payload.get("iat")
    created_at = None
    if iat_value is not None:
        try:
            created_at = datetime.fromtimestamp(iat_value, UTC).replace(tzinfo=None)
        except (ValueError, TypeError, OSError):
            created_at = None

    return {
        "user_id": user_id,
        "access": "customer",
        "created_at": created_at,
    }
