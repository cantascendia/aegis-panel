from enum import Enum

from decouple import config
from dotenv import load_dotenv

load_dotenv()

DASHBOARD_PATH = config("DASHBOARD_PATH", default="/dashboard/")

SQLALCHEMY_DATABASE_URL = config(
    "SQLALCHEMY_DATABASE_URL", default="sqlite:///db.sqlite3"
)
SQLALCHEMY_CONNECTION_POOL_SIZE = config(
    "SQLALCHEMY_CONNECTION_POOL_SIZE", default=10, cast=int
)
SQLALCHEMY_CONNECTION_MAX_OVERFLOW = config(
    "SQLALCHEMY_CONNECTION_MAX_OVERFLOW", default=-1, cast=int
)

UVICORN_HOST = config("UVICORN_HOST", default="0.0.0.0")
UVICORN_PORT = config("UVICORN_PORT", cast=int, default=8000)
UVICORN_UDS = config("UVICORN_UDS", default=None)
UVICORN_SSL_CERTFILE = config("UVICORN_SSL_CERTFILE", default=None)
UVICORN_SSL_KEYFILE = config("UVICORN_SSL_KEYFILE", default=None)


DEBUG = config("DEBUG", default=False, cast=bool)
DOCS = config("DOCS", default=False, cast=bool)

VITE_BASE_API = (
    f"http://127.0.0.1:{UVICORN_PORT}/api/"
    if DEBUG and config("VITE_BASE_API", default="/api/") == "/api/"
    else config("VITE_BASE_API", default="/api/")
)

SUBSCRIPTION_URL_PREFIX = config("SUBSCRIPTION_URL_PREFIX", default="").strip(
    "/"
)

TELEGRAM_API_TOKEN = config("TELEGRAM_API_TOKEN", default="")
TELEGRAM_ADMIN_ID = config(
    "TELEGRAM_ADMIN_ID",
    default="",
    cast=lambda v: [
        int(i) for i in filter(str.isdigit, (s.strip() for s in v.split(",")))
    ],
)
TELEGRAM_PROXY_URL = config("TELEGRAM_PROXY_URL", default="")
TELEGRAM_LOGGER_CHANNEL_ID = config(
    "TELEGRAM_LOGGER_CHANNEL_ID", cast=int, default=0
)

# JWT signing secret. Externalize from the database to avoid putting the
# key inside SQL-injection / DB-dump blast radius (AUDIT.md section 4,
# finding P0-3). Generate a 32-byte hex secret with:
#     python -c "import secrets; print(secrets.token_hex(32))"
# If empty, app/config/db.py:get_secret_key falls back to the legacy
# in-database secret and emits a RuntimeWarning. The fallback will be
# removed in v0.2 — set this in .env before upgrading past that.
JWT_SECRET_KEY = config("JWT_SECRET_KEY", default="")

# P0: default token lifetime tightened from 24h (1440) to 60 minutes.
# 24h leaves a huge blast radius on any accidental token leak. Refresh
# tokens arrive in a later PR; until then operators who need longer
# sessions can override via .env.
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = config(
    "JWT_ACCESS_TOKEN_EXPIRE_MINUTES", cast=int, default=60
)

CUSTOM_TEMPLATES_DIRECTORY = config("CUSTOM_TEMPLATES_DIRECTORY", default=None)

SUBSCRIPTION_PAGE_TEMPLATE = config(
    "SUBSCRIPTION_PAGE_TEMPLATE", default="subscription/index.html"
)
HOME_PAGE_TEMPLATE = config("HOME_PAGE_TEMPLATE", default="home/index.html")

SINGBOX_SUBSCRIPTION_TEMPLATE = config(
    "SINGBOX_SUBSCRIPTION_TEMPLATE", default=None
)
XRAY_SUBSCRIPTION_TEMPLATE = config("XRAY_SUBSCRIPTION_TEMPLATE", default=None)
CLASH_SUBSCRIPTION_TEMPLATE = config(
    "CLASH_SUBSCRIPTION_TEMPLATE", default=None
)

WEBHOOK_ADDRESS = config("WEBHOOK_ADDRESS", default=None)
WEBHOOK_SECRET = config("WEBHOOK_SECRET", default=None)


# CORS allowed origins (comma-separated). Empty list == no cross-origin
# access (same-origin only). AUDIT.md section 4, finding P0-4.
#
# Upstream shipped `allow_origins=["*"]` + `allow_credentials=True`, a
# combination browsers reject AND one that, if browsers accepted it,
# would let any website read an authenticated admin's session. We
# default to the closed position and require operators to opt in.
#
# Example: CORS_ALLOWED_ORIGINS="https://panel.example.com,https://admin.example.com"
# Dev override: CORS_ALLOWED_ORIGINS="http://localhost:3000"
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="",
    cast=lambda v: [o.strip() for o in v.split(",") if o.strip()],
)


# Redis 7 (optional). See docs/ai-cto/SPEC-postgres-redis.md.
#
# Empty == disabled. Consumers that *require* Redis (rate limit) must
# check is_redis_configured() and fail loud when absent. Consumers
# that can degrade (opportunistic cache) should skip silently.
#
# Connection string format:
#   redis://[:password@]host[:port][/db]
#   rediss://... (TLS)
#   unix:///path/to/socket?db=0
REDIS_URL = config("REDIS_URL", default="")
REDIS_POOL_SIZE = config("REDIS_POOL_SIZE", cast=int, default=20)


class AuthAlgorithm(Enum):
    PLAIN = "plain"
    XXH128 = "xxh128"


AUTH_GENERATION_ALGORITHM = config(
    "AUTH_GENERATION_ALGORITHM",
    cast=AuthAlgorithm,
    default=AuthAlgorithm.XXH128,
)

# recurrent notifications

# timeout between each retry of sending a notification in seconds
RECURRENT_NOTIFICATIONS_TIMEOUT = config(
    "RECURRENT_NOTIFICATIONS_TIMEOUT", default=180, cast=int
)
# how many times to try after ok response not received after sending a notifications
NUMBER_OF_RECURRENT_NOTIFICATIONS = config(
    "NUMBER_OF_RECURRENT_NOTIFICATIONS", default=3, cast=int
)

# sends a notification when the user uses this much of their data
NOTIFY_REACHED_USAGE_PERCENT = config(
    "NOTIFY_REACHED_USAGE_PERCENT", default=80, cast=int
)

# sends a notification when there is n days left of their service
NOTIFY_DAYS_LEFT = config("NOTIFY_DAYS_LEFT", default=3, cast=int)

DISABLE_RECORDING_NODE_USAGE = config(
    "DISABLE_RECORDING_NODE_USAGE", cast=bool, default=False
)

TASKS_RECORD_USER_USAGES_INTERVAL = config(
    "TASKS_RECORD_USER_USAGES_INTERVAL", default=30, cast=int
)
TASKS_REVIEW_USERS_INTERVAL = config(
    "TASKS_REVIEW_USERS_INTERVAL", default=30, cast=int
)
TASKS_EXPIRE_DAYS_REACHED_INTERVAL = config(
    "TASKS_EXPIRE_DAYS_REACHED_INTERVAL", default=30, cast=int
)
TASKS_RESET_USER_DATA_USAGE = config(
    "TASKS_RESET_USER_DATA_USAGE", default=3600, cast=int
)
