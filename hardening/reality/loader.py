"""
Loaders for the Reality audit pipeline (R.2).

Two paths produce identical :class:`RealityTarget` shapes:

- :func:`from_db_rows` — pulls from panel ``InboundHost`` SQLAlchemy
  rows. Filters for Reality-configured rows (``reality_public_key``
  non-empty). Cannot read ``conn_idle`` / ``xver`` / ``spider_x``
  because the upstream DB schema doesn't surface them; those
  fields land as ``None`` and the corresponding checks return
  warnings.

- :func:`from_xray_config` — parses an xray config JSON dict
  (``{"inbounds": [{"streamSettings": {"security": "reality",
  "realitySettings": {...}}, ...}, ...], "policy": {...}}``).
  Recovers the full set including timeouts.

The two loaders share output type, so the rest of the pipeline
(checks / scoring / report) doesn't care which side of the system
produced the targets.

Pure functions; the only "I/O" is reading attributes off the input
objects/dicts. Nothing here calls the network or the DB directly —
the caller is responsible for fetching rows / reading the JSON file.
This keeps loader unit tests trivial and zero-network.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from hardening.reality.models import RealityTarget

if TYPE_CHECKING:
    from collections.abc import Iterable


class _InboundHostLike(Protocol):
    """Structural type matching the subset of ``InboundHost`` we read.

    Defined as a protocol so unit tests can pass in light dataclasses
    or ``SimpleNamespace`` objects without needing the full
    SQLAlchemy ``Base`` machinery + alembic migration in CI.
    """

    address: str | None
    remark: str | None
    sni: str | None
    port: int | None
    reality_public_key: str | None
    reality_short_ids: list[str] | None
    fingerprint: Any  # SQLAlchemy Enum, stringifies via str()


def from_db_rows(rows: Iterable[_InboundHostLike]) -> list[RealityTarget]:
    """Convert ``InboundHost`` rows to ``RealityTarget`` list.

    Filters: only rows whose ``reality_public_key`` is non-empty are
    kept. The panel's ``InboundHostSecurity`` enum lacks a "reality"
    value (upstream models reality as "tls + reality_public_key set"),
    so the public-key presence is our discriminator.

    Missing fields:
    - ``conn_idle`` / ``xver`` / ``spider_x``: not in the upstream
      schema. Set to ``None`` so ``check_timeout_config`` etc. emit
      explicit warnings rather than silently passing.
    - ``host`` falls back: address → remark → "?".
    """
    out: list[RealityTarget] = []
    for row in rows:
        public_key = getattr(row, "reality_public_key", None)
        if not public_key:
            continue
        host = (
            getattr(row, "address", None)
            or getattr(row, "remark", None)
            or "?"
        )
        sni = getattr(row, "sni", None) or ""
        port = int(getattr(row, "port", None) or 0)
        short_ids = list(getattr(row, "reality_short_ids", None) or [])
        fingerprint = _stringify_enum(getattr(row, "fingerprint", None))

        out.append(
            RealityTarget(
                host=host,
                sni=sni,
                port=port,
                public_key=public_key,
                short_ids=short_ids,
                fingerprint=fingerprint,
                conn_idle=None,
                xver=None,
                spider_x=None,
                source="db",
            )
        )
    return out


def from_xray_config(config: dict[str, Any]) -> list[RealityTarget]:
    """Parse an xray-server config dict, return one target per Reality inbound.

    Walks ``config["inbounds"]``, keeps entries whose
    ``streamSettings.security == "reality"``. ``conn_idle`` resolution
    order:

    1. ``streamSettings.sockopt.tcpKeepAliveIdle`` (per-inbound)
    2. ``policy.levels["0"].connIdle`` (server-wide default)
    3. ``None`` (xray default — checked as critical)
    """
    out: list[RealityTarget] = []
    inbounds = config.get("inbounds") or []
    server_default_idle = _policy_default_conn_idle(config)

    for inb in inbounds:
        ss = inb.get("streamSettings") or {}
        if ss.get("security") != "reality":
            continue
        rs = ss.get("realitySettings") or {}
        server_names = rs.get("serverNames") or []
        sni = server_names[0] if server_names else ""

        sock_idle = (ss.get("sockopt") or {}).get("tcpKeepAliveIdle")
        conn_idle = sock_idle if sock_idle is not None else server_default_idle

        out.append(
            RealityTarget(
                host=str(inb.get("listen") or inb.get("tag") or "?"),
                sni=sni,
                port=int(inb.get("port") or 0),
                # Servers usually carry privateKey; clients carry publicKey.
                # Either is sufficient for "Reality is configured" presence.
                public_key=str(
                    rs.get("publicKey") or rs.get("privateKey") or ""
                ),
                short_ids=list(rs.get("shortIds") or []),
                fingerprint=str(rs.get("fingerprint") or ""),
                conn_idle=int(conn_idle) if conn_idle is not None else None,
                xver=rs.get("xver"),
                spider_x=rs.get("spiderX"),
                source="config",
            )
        )
    return out


def _policy_default_conn_idle(config: dict[str, Any]) -> int | None:
    """Pull ``policy.levels["0"].connIdle`` if present, else None."""
    levels = (config.get("policy") or {}).get("levels") or {}
    level_0 = levels.get("0") or levels.get(0) or {}
    val = level_0.get("connIdle")
    return int(val) if val is not None else None


def _stringify_enum(val: Any) -> str:
    """Return a plain string for SQLAlchemy / Pydantic enum-ish inputs.

    Handles three shapes: actual ``Enum`` instances (``.value``),
    plain strings (passthrough), and ``None`` (empty string).
    """
    if val is None:
        return ""
    if hasattr(val, "value"):
        return str(val.value)
    return str(val)


__all__ = ["from_db_rows", "from_xray_config"]
