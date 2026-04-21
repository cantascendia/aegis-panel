"""
hardening/panel — panel self-hardening modules.

Public API:
- :func:`apply_panel_hardening` — install middleware and exception
  handlers on the FastAPI app. Called once from `app/marzneshin.py`.
- :data:`rate_limit.limiter` — module-level Limiter singleton, imported
  by route files to decorate specific endpoints.

See `hardening/panel/README.md` for the full module plan.
"""

from __future__ import annotations

from hardening.panel.middleware import apply_panel_hardening

__all__ = ["apply_panel_hardening"]
