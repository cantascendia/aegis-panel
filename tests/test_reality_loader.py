"""
Tests for hardening/reality/loader.py — DB-row + xray-config paths.

Both loaders produce ``RealityTarget``; the rest of the audit pipeline
is loader-agnostic. Tests here pin the field-mapping logic and the
filtering rules so regressions surface as named test failures rather
than mysterious downstream check misfires.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from hardening.reality.loader import from_db_rows, from_xray_config


def _row(**kw: Any) -> SimpleNamespace:
    """Build a stand-in for InboundHost without dragging in SQLAlchemy."""
    defaults: dict[str, Any] = dict(
        address="jp1.example.com",
        remark="JP node 1",
        sni="static.naver.net",
        port=2083,
        reality_public_key="public-key-32chars-aaaaaaaaaa",
        reality_short_ids=["aabb", "ccdd"],
        fingerprint="chrome",
    )
    defaults.update(kw)
    return SimpleNamespace(**defaults)


# --------------------------------------------------------------------------
# from_db_rows
# --------------------------------------------------------------------------


def test_from_db_rows_filters_out_non_reality() -> None:
    """Rows without reality_public_key are dropped."""
    rows = [
        _row(reality_public_key=""),
        _row(reality_public_key=None),
        _row(),  # the one Reality row
    ]
    targets = from_db_rows(rows)
    assert len(targets) == 1
    assert targets[0].source == "db"


def test_from_db_rows_maps_fields() -> None:
    targets = from_db_rows([_row(port=2096, sni="example.com")])
    t = targets[0]
    assert t.host == "jp1.example.com"
    assert t.sni == "example.com"
    assert t.port == 2096
    assert t.short_ids == ["aabb", "ccdd"]
    assert t.fingerprint == "chrome"
    # DB doesn't expose these — checks must see None and emit warnings
    assert t.conn_idle is None
    assert t.xver is None
    assert t.spider_x is None


def test_from_db_rows_falls_back_address_to_remark() -> None:
    targets = from_db_rows([_row(address=None, remark="JP node 1")])
    assert targets[0].host == "JP node 1"


def test_from_db_rows_handles_enum_fingerprint() -> None:
    """SQLAlchemy enums often expose `.value` rather than __str__."""
    fake_enum = SimpleNamespace(value="firefox")
    targets = from_db_rows([_row(fingerprint=fake_enum)])
    assert targets[0].fingerprint == "firefox"


def test_from_db_rows_empty_short_ids_is_empty_list_not_none() -> None:
    targets = from_db_rows([_row(reality_short_ids=None)])
    assert targets[0].short_ids == []


# --------------------------------------------------------------------------
# from_xray_config
# --------------------------------------------------------------------------


def _config(**rs_overrides: Any) -> dict[str, Any]:
    """Minimal xray config dict with one Reality inbound."""
    rs: dict[str, Any] = dict(
        serverNames=["static.naver.net"],
        publicKey="public-key-32chars-aaaaaaaaaa",
        shortIds=["aabb", "ccdd"],
        fingerprint="chrome",
        xver=1,
        spiderX="/path",
    )
    rs.update(rs_overrides)
    return {
        "policy": {"levels": {"0": {"connIdle": 90}}},
        "inbounds": [
            {
                "tag": "in-1",
                "listen": "0.0.0.0",
                "port": 2083,
                "streamSettings": {
                    "security": "reality",
                    "realitySettings": rs,
                    "sockopt": {"tcpKeepAliveIdle": 90},
                },
            }
        ],
    }


def test_from_xray_config_happy_path() -> None:
    targets = from_xray_config(_config())
    assert len(targets) == 1
    t = targets[0]
    assert t.host == "0.0.0.0"
    assert t.sni == "static.naver.net"
    assert t.port == 2083
    assert t.public_key.startswith("public-key")
    assert t.short_ids == ["aabb", "ccdd"]
    assert t.fingerprint == "chrome"
    assert t.conn_idle == 90
    assert t.xver == 1
    assert t.spider_x == "/path"
    assert t.source == "config"


def test_from_xray_config_skips_non_reality_inbounds() -> None:
    cfg = _config()
    cfg["inbounds"].append(
        {
            "tag": "vmess",
            "port": 80,
            "streamSettings": {"security": "tls"},
        }
    )
    targets = from_xray_config(cfg)
    assert len(targets) == 1  # only the Reality one


def test_from_xray_config_falls_back_policy_conn_idle() -> None:
    """When sockopt.tcpKeepAliveIdle is absent, use policy.levels.0.connIdle."""
    cfg = _config()
    cfg["inbounds"][0]["streamSettings"]["sockopt"] = {}
    targets = from_xray_config(cfg)
    assert targets[0].conn_idle == 90  # from policy.levels.0


def test_from_xray_config_no_conn_idle_anywhere_yields_none() -> None:
    cfg = _config()
    del cfg["policy"]
    cfg["inbounds"][0]["streamSettings"]["sockopt"] = {}
    targets = from_xray_config(cfg)
    assert targets[0].conn_idle is None


def test_from_xray_config_empty_server_names_yields_empty_sni() -> None:
    targets = from_xray_config(_config(serverNames=[]))
    assert targets[0].sni == ""


def test_from_xray_config_empty_inbounds() -> None:
    targets = from_xray_config({"inbounds": []})
    assert targets == []


def test_from_xray_config_uses_private_key_when_public_absent() -> None:
    """Server-side configs carry privateKey, not publicKey. Loader picks
    whichever is present so the audit can still run."""
    cfg = _config()
    rs = cfg["inbounds"][0]["streamSettings"]["realitySettings"]
    del rs["publicKey"]
    rs["privateKey"] = "server-priv-key-32chars-bbbbbb"
    targets = from_xray_config(cfg)
    assert targets[0].public_key.startswith("server-priv")
