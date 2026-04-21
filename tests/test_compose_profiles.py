from __future__ import annotations

from pathlib import Path


def test_optional_profiles_do_not_require_env_at_parse_time() -> None:
    """SQLite-only compose usage must not require optional profile env vars."""
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")

    assert 'POSTGRES_PASSWORD: "${POSTGRES_PASSWORD:-}"' in compose
    assert 'POSTGRES_PASSWORD: "${POSTGRES_PASSWORD:?' not in compose
