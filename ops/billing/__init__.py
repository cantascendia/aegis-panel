"""
ops.billing — commercial billing layer for Aegis Panel.

Round 2 path A; see docs/ai-cto/SPEC-billing-mvp.md for the full
design, OPS-epay-vendor-guide.md for operator 码商 selection, and
OPS-jpy-cashout.md for the USDT→JPY cashout flow.

A.1.1 lands the data models + Alembic migration. Pricing, state
machine, providers, REST, and dashboard follow in A.1.2+.

Public API is intentionally minimal for now — call sites should
import from the submodule they need (``ops.billing.db``), not from
this package root, to keep the import graph readable.
"""

from __future__ import annotations

__all__: list[str] = []
