"""
SNI intelligent selector (Reality `serverName` candidate finder).

Public API:
- :func:`select_candidates` — async, takes a VPS IP + count + region,
  returns a ranked list of :class:`Candidate`.
- :func:`main` — CLI entry point. Invoked via
  ``python -m hardening.sni.selector``.

See ``docs/ai-cto/SPEC-sni-selector.md`` for the full contract and
the six hard indicators.
"""

from __future__ import annotations

from hardening.sni.candidate import Candidate, CheckResults
from hardening.sni.selector import main, select_candidates

__all__ = ["Candidate", "CheckResults", "main", "select_candidates"]
