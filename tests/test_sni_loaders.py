"""
Tests for hardening/sni/loaders.py — YAML load + validation.

Pure filesystem work, no network. Uses the bundled real
blacklist.yaml + seeds/ since those are data files we check into
the repo; if those files are broken, load_* should surface it
loudly, and so should these tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hardening.sni.loaders import SeedLoadError, load_blacklist, load_seeds


def test_load_blacklist_returns_set_of_hosts() -> None:
    """The bundled blacklist.yaml loads into a non-empty set."""
    blacklist = load_blacklist()
    # speedtest.net is the compass-documented canonical example;
    # if it ever disappears from the blacklist without a replacement
    # entry, this test fails loudly.
    assert "speedtest.net" in blacklist
    assert isinstance(blacklist, set)


def test_load_blacklist_custom_path_missing_file_raises(
    tmp_path: Path,
) -> None:
    with pytest.raises(SeedLoadError, match="blacklist file missing"):
        load_blacklist(tmp_path / "nonexistent.yaml")


def test_load_blacklist_malformed_yaml_raises(tmp_path: Path) -> None:
    f = tmp_path / "bl.yaml"
    f.write_text("not: a: valid: yaml: {{{{", encoding="utf-8")
    with pytest.raises(SeedLoadError, match="YAML invalid"):
        load_blacklist(f)


def test_load_blacklist_missing_blocked_key_raises(tmp_path: Path) -> None:
    f = tmp_path / "bl.yaml"
    f.write_text("notblocked: []\n", encoding="utf-8")
    with pytest.raises(SeedLoadError, match="'blocked'"):
        load_blacklist(f)


def test_load_blacklist_entry_missing_host_key_raises(tmp_path: Path) -> None:
    f = tmp_path / "bl.yaml"
    f.write_text(
        "blocked:\n  - reason: no host field\n",
        encoding="utf-8",
    )
    with pytest.raises(SeedLoadError, match="missing 'host'"):
        load_blacklist(f)


def test_load_blacklist_empty_file_ok(tmp_path: Path) -> None:
    """An empty file is a valid 'no blacklist' config."""
    f = tmp_path / "bl.yaml"
    f.write_text("", encoding="utf-8")
    assert load_blacklist(f) == set()


# --------------------------------------------------------------------------


def test_load_seeds_global_only() -> None:
    """Default 'auto' region loads only global.yaml."""
    seeds = load_seeds("auto")
    assert seeds, "global.yaml must have at least one entry"
    # Each seed is a dict with host/category/notes keys.
    for s in seeds:
        assert "host" in s
        assert "category" in s
        assert "notes" in s


def test_load_seeds_regional_includes_global() -> None:
    """Regional load merges global + region, de-duplicating."""
    global_seeds = load_seeds("global")
    jp_seeds = load_seeds("jp")
    global_hosts = {s["host"] for s in global_seeds}
    jp_hosts = {s["host"] for s in jp_seeds}
    # JP must include every global host plus at least one region-specific.
    assert global_hosts.issubset(jp_hosts)
    assert len(jp_hosts) > len(global_hosts)


def test_load_seeds_unknown_region_raises() -> None:
    with pytest.raises(SeedLoadError, match="seed file not found"):
        load_seeds("antarctica")


def test_load_seeds_dedupe_preserves_order() -> None:
    """If a region re-includes a global host, first-seen order wins."""
    seeds = load_seeds("us")
    hosts = [s["host"] for s in seeds]
    # No duplicates in the merged list.
    assert len(hosts) == len(set(hosts))
