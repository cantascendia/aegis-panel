"""
Tests for ``POST /api/nodes/sni-suggest`` (hardening/sni/endpoint.py).

Covered:
- **Auth gate**: 401 without token, 403 when the resolved admin is
  non-sudo (both via the real :func:`sudo_admin` dep being overridden
  to simulate each outcome).
- **Input validation**: 422 on bad region enum, bad count range.
- **Happy path**: 200, body is the ``SelectorResult.to_dict()`` of
  the mocked selector. No network (we monkeypatch
  ``select_candidates`` module-level).
- **Timeout**: 504 when the selector raises ``asyncio.TimeoutError``.
- **Seed load error**: 500 with cleanly surfaced reason.

Scope
-----
We build a minimal ``FastAPI`` app locally and include only our
``sni_router``. That keeps the test hermetic and avoids pulling all
of ``app.marzneshin`` + its startup side effects (DB, scheduler,
marznode clients). The router's auth dependency is the real
``app.dependencies.sudo_admin``, so the auth contract is exercised
end to end — we just provide fake Admins via
``app.dependency_overrides``.

Rate-limit interaction: in tests the env has no ``RATE_LIMIT_ENABLED``
set, so ``hardening.panel.rate_limit.limiter`` is built with
``enabled=False``. Its ``@limiter.limit(...)`` decorators become
no-ops. Tests don't need to worry about 429s from repeated calls.
"""

from __future__ import annotations

import asyncio
from dataclasses import asdict
from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

# --- fixtures --------------------------------------------------------------


@pytest.fixture
def fake_sudo_admin() -> Any:
    """A minimal object with just the attributes the endpoint reads."""

    class _FakeAdmin:
        username = "test-sudo"
        is_sudo = True
        enabled = True

    return _FakeAdmin()


@pytest.fixture
def app_with_sni(fake_sudo_admin: Any) -> FastAPI:
    """FastAPI app that mounts only the SNI router.

    We override ``sudo_admin`` at the dep level so requests bypass the
    real token-based auth path. Each test that wants to exercise the
    auth-denied path can re-override to raise.
    """
    from app.dependencies import sudo_admin
    from hardening.sni.endpoint import router as sni_router

    app = FastAPI()
    app.include_router(sni_router)

    def _ok_admin() -> Any:
        return fake_sudo_admin

    app.dependency_overrides[sudo_admin] = _ok_admin
    return app


@pytest.fixture
def client(app_with_sni: FastAPI) -> TestClient:
    return TestClient(app_with_sni)


@pytest.fixture
def fake_selector_result() -> dict[str, Any]:
    """Shape matches ``SelectorResult.to_dict()`` without constructing one.

    Using a dict keeps the test free of real Candidate/CheckResults
    imports. The golden-file test (``tests/test_sni_selector.py``)
    guards the schema; we only verify the endpoint returns what the
    selector gave it, verbatim.
    """
    return {
        "vps_ip": "1.2.3.4",
        "vps_asn": 14061,
        "vps_country": "US",
        "probed_at": "2026-04-22T10:00:00Z",
        "elapsed_seconds": 12.34,
        "candidates": [
            {
                "host": "www.microsoft.com",
                "score": 0.95,
                "checks": {
                    "blacklist_ok": True,
                    "no_redirect": True,
                    "same_asn": False,
                    "tls13_ok": True,
                    "alpn_h2_ok": True,
                    "x25519_ok": True,
                    "ocsp_stapling": True,
                    "rtt_ms": 45,
                },
                "notes": "",
            }
        ],
        "rejected": [
            {"host": "speedtest.net", "reason": "blacklist: Iran MCCI"}
        ],
    }


# --- auth gate -------------------------------------------------------------


def test_auth_401_without_token(app_with_sni: FastAPI) -> None:
    """No override that supplies an admin → FastAPI's real ``sudo_admin``
    dep resolves via the oauth2 flow, which returns 401 when no token
    is present.

    We purposely clear the dependency override here so the real chain
    runs. That chain is ``get_admin -> get_current_admin -> sudo_admin``;
    all three need either a token or a valid admin record, and without
    either the middle stage raises HTTP 401.
    """
    from app.dependencies import sudo_admin

    app_with_sni.dependency_overrides.pop(sudo_admin, None)
    with TestClient(app_with_sni) as c:
        resp = c.post(
            "/api/nodes/sni-suggest",
            json={"vps_ip": "1.2.3.4", "count": 5, "region": "auto"},
        )
    assert resp.status_code == 401


def test_auth_403_when_admin_not_sudo(app_with_sni: FastAPI) -> None:
    """A real admin but without ``is_sudo`` must be rejected by
    ``sudo_admin`` with 403.

    We simulate that by overriding ``sudo_admin`` itself to raise the
    403 — which is exactly what the real dep does when
    ``admin.is_sudo`` is False.
    """
    from app.dependencies import sudo_admin

    def _non_sudo() -> Any:
        raise HTTPException(status_code=403, detail="Access Denied")

    app_with_sni.dependency_overrides[sudo_admin] = _non_sudo

    with TestClient(app_with_sni) as c:
        resp = c.post(
            "/api/nodes/sni-suggest",
            json={"vps_ip": "1.2.3.4", "count": 5, "region": "auto"},
        )
    assert resp.status_code == 403


# --- input validation ------------------------------------------------------


def test_validation_rejects_bad_region(client: TestClient) -> None:
    resp = client.post(
        "/api/nodes/sni-suggest",
        json={"vps_ip": "1.2.3.4", "count": 5, "region": "mars"},
    )
    assert resp.status_code == 422
    # Pydantic surfaces the specific field + allowed literals
    body = resp.json()
    assert any("region" in str(err.get("loc", [])) for err in body["detail"])


def test_validation_rejects_count_out_of_range(client: TestClient) -> None:
    resp = client.post(
        "/api/nodes/sni-suggest",
        json={"vps_ip": "1.2.3.4", "count": 0, "region": "auto"},
    )
    assert resp.status_code == 422

    resp_hi = client.post(
        "/api/nodes/sni-suggest",
        json={"vps_ip": "1.2.3.4", "count": 999, "region": "auto"},
    )
    assert resp_hi.status_code == 422


def test_validation_rejects_empty_vps_ip(client: TestClient) -> None:
    resp = client.post(
        "/api/nodes/sni-suggest",
        json={"vps_ip": "", "count": 5, "region": "auto"},
    )
    assert resp.status_code == 422


# --- happy path ------------------------------------------------------------


def test_happy_path_returns_selector_result_verbatim(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    fake_selector_result: dict[str, Any],
) -> None:
    """Endpoint delegates to ``select_candidates`` and passes its
    ``to_dict()`` output through as the response body.

    We mock at the symbol the endpoint imported (
    ``hardening.sni.endpoint.select_candidates``), not at the
    original definition site. Mocking the wrong symbol is a common
    trap — see LESSONS.md once if we hit it again.
    """
    from hardening.sni.candidate import (
        Candidate,
        CheckResults,
        Rejection,
        SelectorResult,
    )

    # Build a real SelectorResult whose to_dict() matches our fixture.
    cand_payload = fake_selector_result["candidates"][0]
    checks = CheckResults(**cand_payload["checks"])
    real_result = SelectorResult(
        vps_ip=fake_selector_result["vps_ip"],
        vps_asn=fake_selector_result["vps_asn"],
        vps_country=fake_selector_result["vps_country"],
        probed_at=fake_selector_result["probed_at"],
        elapsed_seconds=fake_selector_result["elapsed_seconds"],
        candidates=[
            Candidate(
                host=cand_payload["host"],
                score=cand_payload["score"],
                checks=checks,
                notes=cand_payload["notes"],
            )
        ],
        rejected=[
            Rejection(
                host=fake_selector_result["rejected"][0]["host"],
                reason=fake_selector_result["rejected"][0]["reason"],
            )
        ],
    )

    fake_select = AsyncMock(return_value=real_result)
    monkeypatch.setattr(
        "hardening.sni.endpoint.select_candidates", fake_select
    )

    resp = client.post(
        "/api/nodes/sni-suggest",
        json={"vps_ip": "1.2.3.4", "count": 5, "region": "auto"},
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body == real_result.to_dict()
    fake_select.assert_awaited_once_with(
        vps_ip="1.2.3.4", count=5, region="auto"
    )


def test_happy_path_passes_region_through(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Region argument is forwarded to ``select_candidates``."""
    from hardening.sni.candidate import SelectorResult

    captured_kwargs: dict[str, Any] = {}

    async def _capture(**kwargs: Any) -> SelectorResult:
        captured_kwargs.update(kwargs)
        return SelectorResult(
            vps_ip=kwargs["vps_ip"],
            vps_asn=None,
            vps_country=None,
            probed_at="2026-04-22T10:00:00Z",
            elapsed_seconds=0.5,
        )

    monkeypatch.setattr(
        "hardening.sni.endpoint.select_candidates", _capture
    )

    resp = client.post(
        "/api/nodes/sni-suggest",
        json={"vps_ip": "1.2.3.4", "count": 3, "region": "jp"},
    )
    assert resp.status_code == 200
    assert captured_kwargs == {
        "vps_ip": "1.2.3.4",
        "count": 3,
        "region": "jp",
    }


# --- error paths -----------------------------------------------------------


def test_timeout_surfaces_as_504(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If ``asyncio.wait_for`` raises ``TimeoutError``, we return 504.

    We simulate by patching ``select_candidates`` to hang longer than
    the endpoint's wall-clock budget, but use a tiny test-scoped
    budget via monkeypatching ``SNI_SUGGEST_TIMEOUT_SECONDS``.
    """
    monkeypatch.setattr(
        "hardening.sni.endpoint.SNI_SUGGEST_TIMEOUT_SECONDS", 0.05
    )

    async def _hang(**kwargs: Any) -> Any:
        await asyncio.sleep(1.0)
        raise AssertionError("should have been cancelled by timeout")

    monkeypatch.setattr(
        "hardening.sni.endpoint.select_candidates", _hang
    )

    resp = client.post(
        "/api/nodes/sni-suggest",
        json={"vps_ip": "1.2.3.4", "count": 5, "region": "auto"},
    )

    assert resp.status_code == 504
    body = resp.json()
    assert "sni_probe_timeout" in body["detail"]


def test_seed_load_error_surfaces_as_500(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Operator misconfiguration (malformed seeds/*.yaml or
    blacklist.yaml) surfaces as 500 with a clear reason, not a bare
    traceback."""
    from hardening.sni.loaders import SeedLoadError

    async def _broken(**kwargs: Any) -> Any:
        raise SeedLoadError("blacklist.yaml: missing 'blocked' key")

    monkeypatch.setattr(
        "hardening.sni.endpoint.select_candidates", _broken
    )

    resp = client.post(
        "/api/nodes/sni-suggest",
        json={"vps_ip": "1.2.3.4", "count": 5, "region": "auto"},
    )
    assert resp.status_code == 500
    body = resp.json()
    assert "sni_seed_load_error" in body["detail"]
    assert "blocked" in body["detail"]


# --- contract guards -------------------------------------------------------


def test_endpoint_path_and_method() -> None:
    """Guard against accidental route renames or method changes.

    Dashboard integration contract: ``POST /api/nodes/sni-suggest``.
    Breaking this path without coordinated dashboard PR silently
    breaks the new-node form.
    """
    from hardening.sni.endpoint import router

    paths = [(r.path, sorted(r.methods)) for r in router.routes]
    assert ("/api/nodes/sni-suggest", ["POST"]) in paths


def test_response_includes_rejected_section(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Operators diagnosing 'why is my list empty?' rely on the
    ``rejected`` array being populated with reasons. Guard that it
    survives serialization."""
    from hardening.sni.candidate import Rejection, SelectorResult

    result = SelectorResult(
        vps_ip="1.2.3.4",
        vps_asn=14061,
        vps_country="US",
        probed_at="2026-04-22T10:00:00Z",
        elapsed_seconds=1.0,
        candidates=[],
        rejected=[
            Rejection(host="speedtest.net", reason="blacklist: Iran MCCI"),
            Rejection(host="example.com", reason="tls13_ok=False"),
        ],
    )

    async def _give(**kwargs: Any) -> SelectorResult:
        return result

    monkeypatch.setattr(
        "hardening.sni.endpoint.select_candidates", _give
    )

    resp = client.post(
        "/api/nodes/sni-suggest",
        json={"vps_ip": "1.2.3.4", "count": 5, "region": "auto"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["rejected"] == [
        {"host": "speedtest.net", "reason": "blacklist: Iran MCCI"},
        {"host": "example.com", "reason": "tls13_ok=False"},
    ]
    assert body["candidates"] == []


# Silence the unused-import warning for `asdict`: only imported in case
# a future test wants to build from a dataclass without dict conversion.
_ = asdict
