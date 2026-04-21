"""
Smoke tests — intentionally trivial.

These exist to:
1. Prove `pytest` can discover and run our suite (catches pyproject / conftest
   misconfigurations before they block a real PR).
2. Guard against import-time regressions in the top-level app package.

Anything more ambitious belongs in a module-specific test file.
"""

from __future__ import annotations


def test_python_version_is_312() -> None:
    """We pin to 3.12 in CI and `requirements.txt` (grpcio compat)."""
    import sys

    assert sys.version_info[:2] == (3, 12), (
        f"Expected Python 3.12, got {sys.version_info[:3]}"
    )


def test_app_package_imports() -> None:
    """Importing the top-level app package must not error.

    Common regressions this catches:
    - Circular imports introduced by new modules.
    - Missing runtime deps after a `requirements.txt` edit.
    - Config module crashing on missing env vars (we scrub env in conftest).
    """
    import app  # noqa: F401


def test_hardening_package_tree_exists() -> None:
    """Scaffolded self-research dirs are importable as Python packages.

    Not strictly required today (they're doc-only), but the moment we add an
    `__init__.py` + a module, we want to notice if someone breaks discovery.
    """
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[1]
    for name in ("hardening", "deploy", "ops"):
        assert (root / name / "README.md").is_file(), (
            f"{name}/ scaffolding missing — did a rebase drop it?"
        )
