"""Environment config for the IP limiter.

Kept outside ``app.config.env`` so the feature can evolve without
touching upstream-owned app files.
"""

from __future__ import annotations

from decouple import config

IPLIMIT_POLL_INTERVAL = config("IPLIMIT_POLL_INTERVAL", default=30, cast=int)
IPLIMIT_LOG_READ_LIMIT = config(
    "IPLIMIT_LOG_READ_LIMIT", default=1000, cast=int
)
IPLIMIT_LOG_READ_TIMEOUT_SECONDS = config(
    "IPLIMIT_LOG_READ_TIMEOUT_SECONDS", default=3.0, cast=float
)
IPLIMIT_AUDIT_LIMIT = config("IPLIMIT_AUDIT_LIMIT", default=100, cast=int)
