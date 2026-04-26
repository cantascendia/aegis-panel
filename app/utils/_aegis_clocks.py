"""
Aegis fork: naive-UTC datetime helper for the ``datetime.utcnow()``
migration.

Python 3.12 deprecated ``datetime.utcnow()``. Upstream Marzneshin's
``app/db/`` columns are all ``DateTime`` without ``timezone=True``,
so we preserve the historical naive-UTC shape exactly via
``datetime.now(UTC).replace(tzinfo=None)`` rather than migrating the
column types. Centralizing the one-line decision here keeps each
call site short (``now_utc_naive()`` vs the verbose inline form) and
makes the upstream-merge story simple: if/when upstream Marzneshin
adopts the same approach, this file gets deleted and imports can
redirect to upstream's helper.

The ``_aegis_`` filename prefix is deliberate — it signals that this
file is an aegis-fork-local addition under ``app/`` (the upstream-sync
surface), so an upstream sync that touches ``app/utils/`` doesn't
collide. The leading ``_`` matches the Python "private module"
convention.

See ``docs/ai-cto/LESSONS.md#L-009`` for the original PR-#11 context.
"""

from __future__ import annotations

from datetime import UTC, datetime


def now_utc_naive() -> datetime:
    """Return the current UTC time as a naive ``datetime``.

    Replacement for ``datetime.utcnow()`` (deprecated in Python 3.12).
    Output shape: ``tzinfo is None``, value identical to what
    ``datetime.utcnow()`` would have returned at the same instant.

    Suitable both for:
    - Direct calls: ``edited_at = now_utc_naive()``
    - SQLAlchemy column defaults: ``default=now_utc_naive``
      (the function itself is the callable SQLAlchemy invokes per-row)
    """
    return datetime.now(UTC).replace(tzinfo=None)
