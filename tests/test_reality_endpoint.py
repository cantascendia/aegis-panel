"""
Tests for hardening/reality/endpoint.py — REST surface (R.3).

Same test pattern as `tests/test_billing_checkout_webhook.py` and
`tests/test_sni_endpoint.py`: build a minimal FastAPI app with just
the router under test, stub `SudoAdminDep`, exercise via TestClient.

No DB, no network — `source='config'` requests carry their own
xray-config dict, and asn_match is monkey-patched the same way the
SNI tests do.
"""

from __future__ import annotations

import json
import socket
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from hardening.reality.endpoint import router as reality_router

_FIXTURES_DIR = Path(__file__).parent / "fixtures"
_PERFECT_PATH = _FIXTURES_DIR / "reality_perfect.json"
_BROKEN_PATH = _FIXTURES_DIR / "reality_broken.json"


def _patch_asn_lookup_to_match(monkeypatch, vps_asn: int) -> None:
    from hardening.sni import asn as sni_asn

    sni_asn._cached_lookup.cache_clear()
    monkeypatch.setattr(socket, "gethostbyname", lambda h: "1.2.3.4")

    async def _fake(ip: str) -> Any:
        return sni_asn.ASNInfo(
            asn=vps_asn,
            country="JP",
            bgp_prefix="1.2.3.0/24",
            registry="apnic",
            allocated="",
            org="NAVER",
        )

    monkeypatch.setattr(sni_asn, "lookup_asn", _fake)


@pytest.fixture
def fake_sudo_admin() -> Any:
    class _A:
        username = "test-sudo"
        is_sudo = True
        enabled = True

    return _A()


@pytest.fixture
def app(fake_sudo_admin) -> FastAPI:
    """Minimal app with just the reality router + sudo dep override."""
    from app.dependencies import sudo_admin

    app = FastAPI()
    app.include_router(reality_router)
    app.dependency_overrides[sudo_admin] = lambda: fake_sudo_admin
    return app


@pytest.fixture
def client(app) -> TestClient:
    return TestClient(app)


# --------------------------------------------------------------------------
# Body validation
# --------------------------------------------------------------------------


def test_audit_source_config_requires_config_field(client) -> None:
    r = client.post("/api/reality/audit", json={"source": "config"})
    assert r.status_code == 400
    assert "requires a 'config'" in r.text


def test_audit_source_db_rejects_config_field(client) -> None:
    r = client.post(
        "/api/reality/audit",
        json={"source": "db", "config": {"inbounds": []}},
    )
    assert r.status_code == 400
    assert "must not include" in r.text


def test_audit_unknown_source_rejected(client) -> None:
    """`source` must be 'db' or 'config' (Pydantic Literal enforces)."""
    r = client.post("/api/reality/audit", json={"source": "elsewhere"})
    assert r.status_code == 422


def test_audit_extra_fields_rejected(client) -> None:
    """ConfigDict(extra='forbid') means typo'd fields surface clearly."""
    r = client.post(
        "/api/reality/audit",
        json={"source": "db", "vpc_asn": 14061},  # typo: vpc not vps
    )
    assert r.status_code == 422


# --------------------------------------------------------------------------
# Happy path: source='config' (the path that doesn't need a DB)
# --------------------------------------------------------------------------


def test_audit_source_config_perfect_returns_green(
    monkeypatch, client
) -> None:
    _patch_asn_lookup_to_match(monkeypatch, vps_asn=23576)
    config = json.loads(_PERFECT_PATH.read_text(encoding="utf-8"))

    r = client.post(
        "/api/reality/audit",
        json={"source": "config", "config": config, "vps_asn": 23576},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["schema_version"] == "1.0"
    assert body["source"] == "config"
    assert len(body["targets"]) == 1
    assert body["targets"][0]["score"] >= 90
    assert body["targets"][0]["grade"] == "green"


def test_audit_source_config_broken_returns_red(client) -> None:
    """Even without --vps-asn this should drop into red (criticals stack)."""
    config = json.loads(_BROKEN_PATH.read_text(encoding="utf-8"))

    r = client.post(
        "/api/reality/audit",
        json={"source": "config", "config": config},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["targets"][0]["score"] < 60
    assert body["targets"][0]["grade"] == "red"
    # summary should reflect 1 red, 0 green/yellow
    assert body["summary"] == {
        "total": 1,
        "green": 0,
        "yellow": 0,
        "red": 1,
        "worst_score": body["targets"][0]["score"],
    }


def test_audit_vps_asn_omitted_yields_warning_finding(client) -> None:
    config = json.loads(_PERFECT_PATH.read_text(encoding="utf-8"))
    r = client.post(
        "/api/reality/audit",
        json={"source": "config", "config": config},
    )
    assert r.status_code == 200
    body = r.json()
    findings = body["targets"][0]["findings"]
    asn_finding = next(f for f in findings if f["check"] == "asn_match")
    assert asn_finding["severity"] == "warning"
    assert "vps_asn omitted" in asn_finding["evidence"]


def test_audit_returns_v1_schema_keys(monkeypatch, client) -> None:
    _patch_asn_lookup_to_match(monkeypatch, vps_asn=23576)
    config = json.loads(_PERFECT_PATH.read_text(encoding="utf-8"))
    r = client.post(
        "/api/reality/audit",
        json={"source": "config", "config": config, "vps_asn": 23576},
    )
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == {
        "schema_version",
        "audited_at",
        "source",
        "targets",
        "summary",
    }
    assert set(body["targets"][0].keys()) == {
        "host",
        "sni",
        "port",
        "score",
        "grade",
        "findings",
    }


def test_audit_empty_config_returns_empty_targets(client) -> None:
    r = client.post(
        "/api/reality/audit",
        json={"source": "config", "config": {"inbounds": []}},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["targets"] == []
    assert body["summary"]["total"] == 0
    assert body["summary"]["worst_score"] == 100


# --------------------------------------------------------------------------
# Auth gate
# --------------------------------------------------------------------------


def test_audit_requires_sudo_admin() -> None:
    """Without the sudo dep override, the endpoint should reject."""
    app = FastAPI()
    app.include_router(reality_router)
    # No dependency_overrides → real SudoAdminDep runs and rejects unauth.

    client = TestClient(app)
    r = client.post(
        "/api/reality/audit",
        json={"source": "config", "config": {"inbounds": []}},
    )
    # SudoAdminDep typically returns 401 (no token) or 403; either is auth-gate.
    assert r.status_code in (401, 403, 422)
