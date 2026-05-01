from __future__ import annotations

from pathlib import Path


def test_optional_profiles_do_not_require_env_at_parse_time() -> None:
    """SQLite-only compose usage must not require optional profile env vars."""
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")

    assert 'POSTGRES_PASSWORD: "${POSTGRES_PASSWORD:-}"' in compose
    assert 'POSTGRES_PASSWORD: "${POSTGRES_PASSWORD:?' not in compose


def test_marznode_version_decoupled_from_aegis_version() -> None:
    """L-036 wave-4: MARZNODE_VERSION must be its own variable, NOT
    bound to AEGIS_VERSION. Conflating them caused production VPS
    to silently use marznode v0.2.0 (matching the very first
    AEGIS_VERSION at install time) all through wave-1/2/3 cutovers.

    marznode is upstream `dawsh/marznode` (not forked), so its tag
    must be pinnable independently. Default v0.5.7 because that's the
    first marznode tag with the multi-Backend gRPC API (FetchBackends
    / RestartBackend / etc.) the fork panel calls.
    """
    for compose_path in (
        "deploy/compose/docker-compose.prod.yml",
        "deploy/compose/docker-compose.sqlite.yml",
        "deploy/marznode/docker-compose.yml",
    ):
        text = Path(compose_path).read_text(encoding="utf-8")
        # marznode service must reference MARZNODE_VERSION variable
        # with v0.5.7 default — never AEGIS_VERSION.
        assert (
            "dawsh/marznode:${MARZNODE_VERSION:-v0.5.7}" in text
        ), f"{compose_path}: marznode image must use MARZNODE_VERSION var with v0.5.7 default"
        assert (
            "dawsh/marznode:${AEGIS_VERSION" not in text
        ), f"{compose_path}: marznode image must NOT bind to AEGIS_VERSION (L-036 regression)"


def test_env_template_has_marznode_version_field() -> None:
    """Fresh installs must seed MARZNODE_VERSION in the rendered .env
    so operators see the variable + can override without surprise."""
    tmpl = Path("deploy/install/templates/env.tmpl").read_text(
        encoding="utf-8"
    )
    assert "MARZNODE_VERSION=v0.5.7" in tmpl


def test_env_template_has_audit_secret_key_placeholder() -> None:
    """Fresh installs must seed AUDIT_SECRET_KEY (Fernet) so the panel
    boot's validate_startup() doesn't crash with AuditMisconfigured
    when AUDIT_RETENTION_DAYS > 0 (B.2 wave-2 closure)."""
    tmpl = Path("deploy/install/templates/env.tmpl").read_text(
        encoding="utf-8"
    )
    assert "AUDIT_SECRET_KEY=__AUDIT_SECRET_KEY__" in tmpl
