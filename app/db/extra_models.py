"""Self-owned SQLAlchemy model registry for this fork.

Single import point for every SQLAlchemy model that lives outside the
upstream ``app/models/`` + ``app/db/models.py`` tree. ``env.py`` imports
only this module (not individual feature packages) so that:

1. **Upstream-sync diff stays at one line.** ``env.py`` is an
   upstream-owned file; every additional ``import hardening.x.db`` line
   grows the rebase conflict surface. Keeping the list here, in a
   fork-owned file, means upstream sync touches env.py never.
2. **Model discoverability is one grep.** New contributors asking
   "what custom tables does this fork add?" land here and see the
   whole list.
3. **Alembic metadata is complete.** SQLAlchemy's declarative ``Base``
   registry is populated by side-effect: ``class Foo(Base)`` must have
   been executed before ``Base.metadata`` sees ``foo``. Importing each
   feature's ``db`` module here runs those class statements.

**Rule (see `.agents/rules/python.md`):** any new SQLAlchemy model in
``hardening/`` or ``ops/`` must be registered here via
``from <package>.db import _  # noqa: F401``. env.py must not be
edited to add new model modules.

See also ``docs/ai-cto/LESSONS.md`` L-014 for the history of why
individual env.py imports were rejected as unsustainable.
"""

from __future__ import annotations

# ruff: noqa: F401  -- imports exist purely to register ORM models.

import hardening.iplimit.db  # aegis_iplimit_{config,override,disabled_state}
import ops.billing.db  # aegis_billing_{plans,channels,invoices,invoice_lines,payment_events}
