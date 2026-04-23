# hardening/iplimit/ - IP concurrency limiter

**Status**: Round 2 MVP.

**Goal**: detect subscription sharing by counting distinct source IPs
per user in a rolling window, using Marznode-provided Xray access
events and Redis runtime state.

## Architecture

The module is self-owned under `hardening/iplimit/`:

| File | Role |
|---|---|
| `db.py` | SQLAlchemy policy models and effective-policy resolution |
| `events.py` | Marznode access-log event parser and bounded collector |
| `store.py` | Redis key helpers, rolling-window state, audit persistence |
| `task.py` | Scheduled detector and warn/disable enforcement |
| `scheduler.py` | APScheduler installation through `apply_panel_hardening()` |
| `endpoint.py` | Sudo-admin REST endpoints for dashboard use |

The runtime integration point is
`hardening.panel.middleware.apply_panel_hardening()`, which includes the
router and starts the feature-owned scheduler by wrapping the FastAPI
lifespan. No `app/tasks/` or `app/routes/` files are edited.

## Redis Contract

Redis is optional. If `REDIS_URL` is unset, the scheduler logs one
disabled notice per process start and skips polling. The REST endpoints
still return SQL policy state with empty runtime observations.

Keys:

```text
aegis:iplimit:observed:{user_id}   # ZSET ip -> last-seen unix ts
aegis:iplimit:violation:{user_id}  # STRING disabled-until unix ts
aegis:iplimit:audit:{user_id}      # LIST capped JSON events
aegis:iplimit:dedupe:{user_id}     # STRING violation fingerprint
```

## Policy

Global defaults live in `aegis_iplimit_config`; nullable per-user
overrides live in `aegis_iplimit_override`.

Defaults:

- `max_concurrent_ips = 3`
- `window_seconds = 300`
- `violation_action = "warn"`
- `disable_duration_seconds = 3600`

Per-user `NULL` fields inherit the global value.

`ip_allowlist_cidrs` is a newline-separated CIDR list used to ignore
legitimate source IPs before they enter the rolling window. The
effective allowlist is the union of global config and per-user override:
if an observed source IP matches either list, the event is skipped.
Use this for operator monitoring addresses and known CGNAT / mobile
carrier ranges that would otherwise create false positives. Both IPv4
and IPv6 CIDRs are accepted.

## Scheduler

The poll interval is controlled by:

```text
IPLIMIT_POLL_INTERVAL=30
IPLIMIT_LOG_READ_LIMIT=1000
IPLIMIT_LOG_READ_TIMEOUT_SECONDS=3
IPLIMIT_AUDIT_LIMIT=100
```

The collector calls existing `app.marznode.nodes[*].get_logs(...)`
clients. It does not open a new gRPC connection and does not parse local
Xray log files.

## API

```text
GET   /api/users/{username}/iplimit
PATCH /api/users/{username}/iplimit/override
GET   /api/users/{username}/iplimit/audit
```

All endpoints require sudo-admin access.

## Operator Notes

Action `warn` writes an audit event and sends a Telegram alert if the
panel already has Telegram configured. Action `disable` writes an audit
event, marks the user disabled, pushes the removal to Marznode, and
automatically re-enables the user when the Redis `disabled_until` value
expires.

## License

This is an independent AGPL-3.0 implementation. Hiddify's
`shared_limit` feature was used only as product-level inspiration; no
code was copied.
