"""
YAML loaders with minimal validation.

Keeping this as its own module means tests can exercise loader
behavior (malformed YAML, missing keys, etc.) without involving
networking / asyncio / ssl.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_PKG_ROOT = Path(__file__).parent


class SeedLoadError(ValueError):
    """Raised when a seed or blacklist YAML fails validation.

    The CLI turns this into a non-zero exit with a clear message —
    silent "empty seed list" would degrade to zero candidates with
    no explanation.
    """


def load_blacklist(path: Path | None = None) -> set[str]:
    """Load the DPI blacklist as a set of blocked hostnames.

    Empty set is allowed (no blacklist == every host clears the
    blacklist check). Malformed YAML or a missing `blocked` key
    raises SeedLoadError rather than silently returning empty —
    silent empty blacklists have caused real-world incidents.
    """
    if path is None:
        path = _PKG_ROOT / "blacklist.yaml"

    try:
        data: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SeedLoadError(f"blacklist file missing: {path}") from exc
    except yaml.YAMLError as exc:
        raise SeedLoadError(f"blacklist YAML invalid: {exc}") from exc

    if data is None:
        return set()
    if not isinstance(data, dict) or "blocked" not in data:
        raise SeedLoadError(
            f"blacklist {path} must be a mapping with a 'blocked' key"
        )
    blocked = data["blocked"] or []
    if not isinstance(blocked, list):
        raise SeedLoadError(
            f"blacklist 'blocked' must be a list, got {type(blocked).__name__}"
        )

    hosts: set[str] = set()
    for idx, entry in enumerate(blocked):
        if not isinstance(entry, dict) or "host" not in entry:
            raise SeedLoadError(
                f"blacklist entry #{idx} missing 'host' key: {entry!r}"
            )
        hosts.add(entry["host"])
    return hosts


def load_seeds(region: str = "auto") -> list[dict[str, str]]:
    """Load seed candidate hosts for a region.

    `region` is a lowercase two-letter code (jp / kr / us / eu) or
    'auto' (== use `global.yaml` only; caller picks the region
    based on VPS ASN country and then calls again if needed) or
    'global' (same as auto).

    Returns a de-duplicated list of ``{host, category, notes}`` dicts
    preserving first-seen order. de-dup matters because a region
    file often re-includes a global-level host with regional notes.
    """
    region = region.lower()
    if region in ("auto", "global"):
        files = ["global.yaml"]
    else:
        files = ["global.yaml", f"{region}.yaml"]

    seen: set[str] = set()
    result: list[dict[str, str]] = []

    seeds_dir = _PKG_ROOT / "seeds"
    for filename in files:
        path = seeds_dir / filename
        if not path.exists():
            # An unknown region code is a config error, not silence.
            raise SeedLoadError(
                f"seed file not found: {path}. "
                f"Known regions: global, jp, kr, us, eu."
            )
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if "hosts" not in data:
            raise SeedLoadError(f"seed file {path} must have a 'hosts' key")
        hosts = data["hosts"] or []
        for idx, entry in enumerate(hosts):
            if not isinstance(entry, dict) or "host" not in entry:
                raise SeedLoadError(
                    f"{path} entry #{idx} missing 'host': {entry!r}"
                )
            if entry["host"] in seen:
                continue
            seen.add(entry["host"])
            result.append(
                {
                    "host": entry["host"],
                    "category": entry.get("category", "unknown"),
                    "notes": entry.get("notes", ""),
                }
            )
    return result
