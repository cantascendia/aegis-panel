"""
Tests for ``hardening.health.endpoint`` — public liveness + sudo
extended report.

Same test pattern as tests/test_reality_endpoint.py: minimal FastAPI
app with just the router + sudo dep override + TestClient.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from hardening.health.endpoint import router as health_router
from hardening.health.models import (
    HealthReport,
    SubsystemHealth,
    aggregate_status,
)

# --------------------------------------------------------------------------
# Pure model tests
# --------------------------------------------------------------------------


def test_aggregate_status_picks_worst() -> None:
    assert aggregate_status([]) == "ok"
    assert aggregate_status([SubsystemHealth(name="a", status="ok")]) == "ok"
    assert (
        aggregate_status(
            [
                SubsystemHealth(name="a", status="ok"),
                SubsystemHealth(name="b", status="degraded"),
            ]
        )
        == "degraded"
    )
    assert (
        aggregate_status(
            [
                SubsystemHealth(name="a", status="degraded"),
                SubsystemHealth(name="b", status="down"),
            ]
        )
        == "down"
    )


def test_health_report_to_dict_round_trips() -> None:
    report = HealthReport(
        status="degraded",
        version="0.1.0",
        uptime_seconds=42,
        subsystems=[
            SubsystemHealth(
                name="db", status="ok", message="alive", details={"k": 1}
            ),
        ],
    )
    out = report.to_dict()
    assert out["status"] == "degraded"
    assert out["version"] == "0.1.0"
    assert out["uptime_seconds"] == 42
    assert out["subsystems"][0]["details"] == {"k": 1}


# --------------------------------------------------------------------------
# Liveness — public
# --------------------------------------------------------------------------


@pytest.fixture
def liveness_only_client() -> TestClient:
    """An app with the health router but no sudo override.

    The public ``/health`` should still respond 200; the extended one
    will reject (auth gate)."""
    app = FastAPI()
    app.include_router(health_router)
    return TestClient(app)


def test_liveness_returns_ok_without_auth(liveness_only_client) -> None:
    r = liveness_only_client.get("/api/aegis/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_liveness_does_not_leak_anything(liveness_only_client) -> None:
    """Public probe should not include version, subsystems, or uptime —
    those are recon vectors. Only ``status`` field is allowed."""
    r = liveness_only_client.get("/api/aegis/health")
    body = r.json()
    assert set(body.keys()) == {"status"}


# --------------------------------------------------------------------------
# Extended — sudo-admin gated
# --------------------------------------------------------------------------


@pytest.fixture
def fake_sudo_admin() -> Any:
    class _A:
        username = "test-sudo"
        is_sudo = True
        enabled = True

    return _A()


def _make_app(fake_sudo_admin: Any) -> FastAPI:
    """An app with the router + sudo override + faked subsystems wired
    onto app.state so probes return predictable shapes."""
    from app.dependencies import sudo_admin

    app = FastAPI()
    app.include_router(health_router)
    app.dependency_overrides[sudo_admin] = lambda: fake_sudo_admin

    # Fake the schedulers as installed (probes inspect app.state).
    class _FakeScheduler:
        def __init__(self, job_ids: list[str]):
            self._job_ids = job_ids

        def get_jobs(self):
            return [type("J", (), {"id": j})() for j in self._job_ids]

    app.state.billing_scheduler_installed = True
    app.state.billing_scheduler = _FakeScheduler(
        [
            "aegis-billing-reap",
            "aegis-billing-apply",
            "aegis-billing-trc20-poll",
        ]
    )
    app.state.iplimit_scheduler_installed = True
    app.state.iplimit_scheduler = _FakeScheduler(["aegis-iplimit-poll"])
    return app


def test_extended_requires_sudo_admin(fake_sudo_admin) -> None:
    """Without dependency override, the extended endpoint should reject."""
    app = FastAPI()
    app.include_router(health_router)
    client = TestClient(app)
    r = client.get("/api/aegis/health/extended")
    assert r.status_code in (401, 403, 422)


def test_extended_returns_full_report_shape(
    monkeypatch, fake_sudo_admin
) -> None:
    """When all probes return ok, top-level status is ok and the
    subsystems list is populated and stably-ordered."""
    # Stub the DB probe to avoid creating a real engine.
    from hardening.health import endpoint as endpoint_module

    async def _fake_db():
        return SubsystemHealth(name="db", status="ok", message="stubbed")

    monkeypatch.setattr(endpoint_module, "probe_db", _fake_db)

    app = _make_app(fake_sudo_admin)
    client = TestClient(app)
    r = client.get("/api/aegis/health/extended")
    assert r.status_code == 200, r.text
    body = r.json()

    assert set(body.keys()) == {
        "status",
        "version",
        "uptime_seconds",
        "subsystems",
    }
    names = [s["name"] for s in body["subsystems"]]
    # Stable alpha order so client diff stays predictable.
    assert names == sorted(names)
    # Both schedulers + db + trc20 + reality_seeds + sni_seeds.
    assert {"db", "billing_scheduler", "iplimit_scheduler", "trc20"} <= set(
        names
    )


def test_extended_aggregates_status_to_worst(
    monkeypatch, fake_sudo_admin
) -> None:
    """If db is down, top-level status must be down regardless of
    other subsystems being ok."""
    from hardening.health import endpoint as endpoint_module

    async def _down_db():
        return SubsystemHealth(name="db", status="down", message="stubbed")

    monkeypatch.setattr(endpoint_module, "probe_db", _down_db)

    app = _make_app(fake_sudo_admin)
    client = TestClient(app)
    r = client.get("/api/aegis/health/extended")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "down"


def test_extended_marks_billing_scheduler_down_when_not_installed(
    monkeypatch, fake_sudo_admin
) -> None:
    from hardening.health import endpoint as endpoint_module

    async def _ok_db():
        return SubsystemHealth(name="db", status="ok")

    monkeypatch.setattr(endpoint_module, "probe_db", _ok_db)

    app = _make_app(fake_sudo_admin)
    # Simulate a panel where install_billing_scheduler did not run.
    app.state.billing_scheduler_installed = False
    app.state.billing_scheduler = None

    client = TestClient(app)
    r = client.get("/api/aegis/health/extended")
    assert r.status_code == 200
    subsystems = {s["name"]: s for s in r.json()["subsystems"]}
    assert subsystems["billing_scheduler"]["status"] == "down"


def test_extended_marks_billing_scheduler_degraded_when_jobs_missing(
    monkeypatch, fake_sudo_admin
) -> None:
    from hardening.health import endpoint as endpoint_module

    async def _ok_db():
        return SubsystemHealth(name="db", status="ok")

    monkeypatch.setattr(endpoint_module, "probe_db", _ok_db)

    app = _make_app(fake_sudo_admin)

    class _PartialScheduler:
        def get_jobs(self):
            return [type("J", (), {"id": "aegis-billing-reap"})()]

    app.state.billing_scheduler = _PartialScheduler()

    client = TestClient(app)
    r = client.get("/api/aegis/health/extended")
    assert r.status_code == 200
    body = r.json()
    subsystems = {s["name"]: s for s in body["subsystems"]}
    assert subsystems["billing_scheduler"]["status"] == "degraded"
    assert "missing" in subsystems["billing_scheduler"]["message"]


def test_extended_includes_version_and_uptime(
    monkeypatch, fake_sudo_admin
) -> None:
    from hardening.health import endpoint as endpoint_module

    async def _ok_db():
        return SubsystemHealth(name="db", status="ok")

    monkeypatch.setattr(endpoint_module, "probe_db", _ok_db)

    app = _make_app(fake_sudo_admin)
    client = TestClient(app)
    r = client.get("/api/aegis/health/extended")
    body = r.json()
    assert isinstance(body["version"], str)
    assert isinstance(body["uptime_seconds"], int)
    assert body["uptime_seconds"] >= 0


# --------------------------------------------------------------------------
# Probe-level unit tests (no FastAPI)
# --------------------------------------------------------------------------


def test_probe_trc20_disabled_returns_ok() -> None:
    """A panel without TRC20 enabled is healthy by design — the
    feature is opt-in. Probe should report ok with a clear "disabled
    by env" message."""
    from ops.billing.trc20_config import _reload_for_tests

    _reload_for_tests(enabled=False)
    from hardening.health.checks import probe_trc20

    out = probe_trc20()
    assert out.status == "ok"
    assert "disabled" in out.message.lower()
    assert out.details["enabled"] is False


def test_probe_trc20_enabled_unconfigured_returns_down() -> None:
    """If operator set ENABLED=true without supporting env, probe
    must surface the config gap as down (not silently degraded)."""
    from ops.billing.trc20_config import _reload_for_tests

    _reload_for_tests(enabled=True)  # missing required fields
    from hardening.health.checks import probe_trc20

    out = probe_trc20()
    assert out.status == "down"


def test_probe_trc20_fully_configured_masks_address() -> None:
    """Address is masked so log/metric scrapers can't easily harvest
    receive addresses across panels."""
    from ops.billing.trc20_config import _reload_for_tests

    _reload_for_tests(
        enabled=True,
        receive_address="TRabcdefghijklmnopqrstuvwxyz1234",
        rate_fen_per_usdt=720,
        memo_salt="x",
    )
    from hardening.health.checks import probe_trc20

    out = probe_trc20()
    assert out.status == "ok"
    address = out.details["address"]
    assert "…" in address  # masked
    assert "abcdef" not in address  # middle bytes hidden

    # Cleanup so other tests see disabled state.
    _reload_for_tests(enabled=False)


def test_probe_reality_seeds_loads_baseline() -> None:
    """The shipped seeds file must always load — if this fails, deploy
    is broken."""
    from hardening.health.checks import probe_reality_seeds

    out = probe_reality_seeds()
    assert out.status == "ok"
    assert out.details["count"] > 0


def test_probe_sni_seeds_loads_baseline() -> None:
    from hardening.health.checks import probe_sni_seeds

    out = probe_sni_seeds()
    assert out.status == "ok"
    assert out.details["count"] > 0
