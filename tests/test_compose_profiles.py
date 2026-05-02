from __future__ import annotations

from pathlib import Path

import yaml


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


def test_panel_image_uses_aegis_version_variable() -> None:
    """L-041 wave-9: the `panel` service image tag must come from the
    AEGIS_VERSION env var, not be hardcoded `:latest`. Wave-9 cutover
    (v0.4.0 → v0.4.1) found `docker inspect aegis-panel` reporting
    `:latest` even though the rendered .env had AEGIS_VERSION=v0.4.1 —
    because compose hardcoded the tag, the env var was ignored.

    Risks of `:latest`:
      1. Reproducibility — rollback meaningless (compose always pulls
         `:latest`, which is whatever GH Actions last pushed).
      2. Silent upgrade — next `docker compose up` after a release
         picks up the new image without operator action or audit trail.
      3. AEGIS_VERSION (set by aegis-upgrade) silently does nothing.

    Fix: image: ghcr.io/cantascendia/aegis-panel:${AEGIS_VERSION:-latest}
    Fallback to :latest preserves backward compatibility for fresh
    bootstraps where the var hasn't been seeded yet.

    Codex cross-review (PR #193 P2): scope the assertion to the actual
    `panel` service via YAML parsing — a substring-only check would
    pass even if `panel:` later switches to a fixed tag while another
    service (e.g. `alembic`, which also uses the panel image) still
    references AEGIS_VERSION. Parsing the compose tree closes that hole.
    """
    expected = "ghcr.io/cantascendia/aegis-panel:${AEGIS_VERSION:-latest}"
    for compose_path in (
        "deploy/compose/docker-compose.prod.yml",
        "deploy/compose/docker-compose.sqlite.yml",
    ):
        spec = yaml.safe_load(Path(compose_path).read_text(encoding="utf-8"))
        services = spec.get("services", {})
        assert (
            "panel" in services
        ), f"{compose_path}: missing required `panel` service"
        panel_image = services["panel"].get("image")
        assert panel_image == expected, (
            f"{compose_path}: panel.image must be {expected!r}, "
            f"got {panel_image!r}"
        )

        # If alembic exists in this compose (prod stack), it also runs
        # the panel image (init-style migration container) and must
        # share the same pin so prod doesn't end up with split versions.
        if "alembic" in services:
            alembic_image = services["alembic"].get("image")
            assert alembic_image == expected, (
                f"{compose_path}: alembic.image must match panel.image "
                f"({expected!r}), got {alembic_image!r}"
            )


def test_panel_image_never_hardcodes_latest_tag() -> None:
    """L-041 regression guard: forbid any service that uses the
    aegis-panel image from hardcoding the literal `:latest` tag (i.e.
    without `${AEGIS_VERSION}` substitution). Catches a future drive-by
    edit that re-introduces silent-upgrade risk by typing `:latest`
    directly into any service definition.
    """
    forbidden_literal = "ghcr.io/cantascendia/aegis-panel:latest"
    for compose_path in (
        "deploy/compose/docker-compose.prod.yml",
        "deploy/compose/docker-compose.sqlite.yml",
    ):
        spec = yaml.safe_load(Path(compose_path).read_text(encoding="utf-8"))
        services = spec.get("services", {})
        for svc_name, svc in services.items():
            image = (svc or {}).get("image")
            if not image:
                continue
            assert image != forbidden_literal, (
                f"{compose_path}: service {svc_name!r} hardcodes "
                f"{forbidden_literal!r} (L-041) — use "
                f"${{AEGIS_VERSION:-latest}} instead"
            )


def test_env_template_has_aegis_version_placeholder() -> None:
    """L-041: Fresh installs must seed AEGIS_VERSION in the rendered .env
    so the compose ${AEGIS_VERSION:-latest} substitution actually pins
    the operator-installed version (instead of silently falling back to
    `:latest`, which defeats the whole reproducibility fix).
    install.sh writes the current stable tag in place of __AEGIS_VERSION__.
    """
    tmpl = Path("deploy/install/templates/env.tmpl").read_text(
        encoding="utf-8"
    )
    assert "AEGIS_VERSION=__AEGIS_VERSION__" in tmpl


def test_env_template_has_audit_secret_key_placeholder() -> None:
    """Fresh installs must seed AUDIT_SECRET_KEY (Fernet) so the panel
    boot's validate_startup() doesn't crash with AuditMisconfigured
    when AUDIT_RETENTION_DAYS > 0 (B.2 wave-2 closure)."""
    tmpl = Path("deploy/install/templates/env.tmpl").read_text(
        encoding="utf-8"
    )
    assert "AUDIT_SECRET_KEY=__AUDIT_SECRET_KEY__" in tmpl
