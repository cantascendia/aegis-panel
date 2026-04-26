"""Reality audit check functions.

Each module exports one ``check_*(target, **deps) -> Finding`` callable
that operates on a single :class:`hardening.reality.models.RealityTarget`
and returns one :class:`Finding`. Pure-function shape (no I/O except
the `asn_match` check, which monkey-patches into the same WHOIS path
``hardening.sni.asn`` already uses) so unit tests can feed dataclass
inputs directly.
"""

from __future__ import annotations

from hardening.reality.checks.asn_match import check_asn_match
from hardening.reality.checks.port_canonical import check_port_canonical
from hardening.reality.checks.shortid_compliance import (
    check_shortid_compliance,
)
from hardening.reality.checks.sni_coldness import check_sni_coldness
from hardening.reality.checks.timeout_config import check_timeout_config

__all__ = [
    "check_asn_match",
    "check_port_canonical",
    "check_shortid_compliance",
    "check_sni_coldness",
    "check_timeout_config",
]
