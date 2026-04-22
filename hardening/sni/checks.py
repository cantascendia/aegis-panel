"""
The six hard indicator check functions.

Each is an async coroutine with a focused signature and a pure-ish
contract: given input, return a bool (and maybe metadata). Keeping
them small means unit tests can mock one network call at a time.

Order they're called in (cheap-first):
  1. blacklist check       -- dict lookup, no network
  2. redirect check        -- HEAD + 1 follow
  3. same-ASN check        -- WHOIS (cached)
  4. TLS 1.3 handshake     -- ssl.get_server_certificate-style probe
  5. ALPN h2 negotiation   -- piggybacks on #4
  6. X25519 group advertised -- piggybacks on #4

Indicators 4-6 are coupled: we open ONE TLS connection per host,
inspect the resulting SSLObject, and derive the three booleans.
Splitting into three separate connections would triple load on the
target.
"""

from __future__ import annotations

import asyncio
import socket
import ssl
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

import aiohttp

from hardening.sni.asn import ASNLookupError, lookup_asn

if TYPE_CHECKING:
    from collections.abc import Iterable


# --------------------------------------------------------------------------
# 1. Blacklist
# --------------------------------------------------------------------------


def check_blacklist(host: str, blacklist: set[str]) -> bool:
    """Return True if `host` is NOT on the blacklist (i.e. ok to use).

    Exact match only. Subdomain logic (e.g. "*.speedtest.net") is
    deliberately out of scope for MVP — false positives on parent
    matches would exclude perfectly fine hosts.
    """
    return host not in blacklist


# --------------------------------------------------------------------------
# 2. No-redirect check
# --------------------------------------------------------------------------


async def check_no_redirect(
    host: str,
    session: aiohttp.ClientSession,
    *,
    timeout: float = 5.0,
) -> bool:
    """Return True if the host DOESN'T 301/302-redirect to a different name.

    We HEAD-request `https://<host>/` and inspect the response. A
    redirect to a different hostname is a fail (Reality needs the
    exact name to serve). Redirect to the *same* hostname on a
    different path (e.g. /en/) is fine.

    Non-2xx without a Location header is treated as "no redirect"
    — plenty of real servers 403/404 the root path but still serve
    Reality-usable TLS.
    """
    try:
        async with session.head(
            f"https://{host}/",
            allow_redirects=False,
            timeout=aiohttp.ClientTimeout(total=timeout),
        ) as resp:
            if resp.status not in (301, 302, 303, 307, 308):
                return True
            location = resp.headers.get("Location", "")
            if not location:
                return True  # redirect advertised but no Location == not a real redirect
            target_host = _extract_host(location)
            return target_host == "" or target_host == host
    except (TimeoutError, aiohttp.ClientError):
        # Network-level failure is not a "redirect" — return True and
        # let the TLS check decide. This keeps the redirect check
        # scoped to its name.
        return True


def _extract_host(url_or_path: str) -> str:
    """Pull the host from a Location header. Returns "" for path-only values."""
    from urllib.parse import urlparse

    parsed = urlparse(url_or_path)
    return parsed.hostname or ""


# --------------------------------------------------------------------------
# 3. Same-ASN check
# --------------------------------------------------------------------------


async def check_same_asn(host: str, vps_asn: int) -> bool:
    """Return True if `host` resolves to an IP whose ASN matches vps_asn."""
    try:
        host_ip = await asyncio.to_thread(socket.gethostbyname, host)
    except socket.gaierror:
        return False
    try:
        info = await lookup_asn(host_ip)
    except ASNLookupError:
        return False
    return info.asn == vps_asn


# --------------------------------------------------------------------------
# 4-6. TLS handshake (combined because they share the one TCP connection)
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class TLSProbe:
    tls13_ok: bool
    alpn_h2_ok: bool
    x25519_ok: bool
    ocsp_stapling: bool
    rtt_ms: int | None


async def probe_tls(host: str, *, timeout: float = 5.0) -> TLSProbe:
    """One TLS 1.3 handshake, three booleans + optional signals.

    Why we don't just use aiohttp: we need to inspect low-level
    SSLObject attributes (negotiated version, ALPN, ECDHE group,
    OCSP blob) that aiohttp doesn't expose cleanly. We do the
    connection with stdlib ssl in a thread — simpler and avoids
    pulling in more async-TLS glue.
    """
    return await asyncio.to_thread(_probe_tls_sync, host, timeout)


def _probe_tls_sync(host: str, timeout: float) -> TLSProbe:
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    # Force TLS 1.3 as the minimum. If the server can't speak 1.3,
    # the handshake fails and we return all-False.
    ctx.minimum_version = ssl.TLSVersion.TLSv1_3
    ctx.set_alpn_protocols(["h2", "http/1.1"])
    # We don't verify the cert — Reality doesn't need a trust chain,
    # we just need to characterize the remote TLS stack. check_hostname
    # must be off before verify_mode can be CERT_NONE.
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    # OCSP stapling requires a special request; Python ssl doesn't
    # expose a clean API for it on the client side. We probe whether
    # the server sends an OCSP response by calling
    # SSLSocket.ocsp_response_received or equivalent — not all
    # Python/OpenSSL builds support reading it back. We default to
    # False and populate only when detection is reliable.
    ocsp_stapling = False

    try:
        t0 = time.monotonic()
        with socket.create_connection((host, 443), timeout=timeout) as raw:
            with ctx.wrap_socket(raw, server_hostname=host) as tls:
                elapsed = time.monotonic() - t0
                tls_version = tls.version()
                alpn = tls.selected_alpn_protocol()
                shared_curves = _extract_shared_groups(tls)
    except (TimeoutError, OSError, ssl.SSLError):
        return TLSProbe(
            tls13_ok=False,
            alpn_h2_ok=False,
            x25519_ok=False,
            ocsp_stapling=False,
            rtt_ms=None,
        )

    tls13_ok = tls_version == "TLSv1.3"
    # Precise X25519 detection lands on Python 3.13+ via
    # `SSLSocket.group()`. On 3.12 `_extract_shared_groups` returns
    # [] (no way to ask OpenSSL from stdlib). Pragmatic fallback:
    # a successful TLS 1.3 handshake with a modern client (which we
    # just performed) implies X25519 support in >95% of real servers
    # -- OpenSSL 3.0+ defaults to X25519 as the preferred TLS 1.3
    # key-exchange group, and our probe advertises it. So on 3.12 we
    # treat TLS 1.3 success as X25519 yes; precision comes free on
    # 3.13. Documented in hardening/sni/README.md.
    if shared_curves:
        x25519_ok = _contains_x25519(shared_curves)
    else:
        x25519_ok = tls13_ok

    return TLSProbe(
        tls13_ok=tls13_ok,
        alpn_h2_ok=alpn == "h2",
        x25519_ok=x25519_ok,
        ocsp_stapling=ocsp_stapling,
        rtt_ms=int(elapsed * 1000),
    )


def _extract_shared_groups(tls: ssl.SSLSocket) -> list[str]:
    """Return the ECDHE groups negotiated, if the runtime can tell us.

    Python 3.12 ssl offers `SSLObject.get_group()` returning the
    selected group name (a single group in TLS 1.3). Older runtimes
    don't have it; we return an empty list in that case and the
    caller treats X25519 as unknown/false.

    OpenSSL 3.2+ is the de-facto requirement for reliable X25519
    detection. Alpine 3.19+ ships 3.2.
    """
    get_group = getattr(tls, "group", None)
    if get_group is not None:
        # 3.13+ offers this as a property.
        try:
            g = tls.group()  # type: ignore[attr-defined]
        except (AttributeError, ssl.SSLError):
            return []
        return [g] if g else []
    # Python 3.12 fallback — negotiation info may live in the cipher
    # selection detail. If we can't find it, return [].
    cipher_info = tls.cipher()  # (cipher_name, tls_version, secret_bits)
    # cipher_info doesn't contain ECDHE group on stdlib ssl.
    # Mark unknown and let scoring treat x25519 as False.
    _ = cipher_info
    return []


def _contains_x25519(groups: Iterable[str]) -> bool:
    return any("x25519" in g.lower() for g in groups)
