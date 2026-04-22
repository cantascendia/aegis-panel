# SPEC - IP Limiter MVP

> Round 2 Path C - per `docs/ai-cto/BRIEF-codex-ip-limiter.md`.
>
> Status: draft plus implementation in `hardening/ip-limiter`.
>
> Template: follows the D-005 Spec-Driven shape used by
> `SPEC-sni-selector.md`.

---

## What

Add a self-owned `hardening/iplimit/` module that detects subscription
sharing by counting distinct source IPs per user in a rolling window.

MVP surface:

- SQL policy tables under the existing Alembic migration path.
- Redis rolling-window keyspace under `aegis:iplimit:*`.
- APScheduler poll task installed through `apply_panel_hardening()`.
- Sudo-admin REST endpoints:
  - `GET /api/users/{username}/iplimit`
  - `PATCH /api/users/{username}/iplimit/override`
  - `GET /api/users/{username}/iplimit/audit`
- Dashboard user settings tab for current observed IPs, overrides, and
  audit history.

Scope boundaries:

- In scope: warn and temporary disable actions, per-user override, Redis
  disabled graceful skip, Telegram alert best-effort.
- In scope: Xray access events read through existing Marznode clients.
- Out of scope: parsing local Xray log files, extending upstream user
  models, country filters, paid fraud scoring, long-term analytics.

## Why

Paid operators lose revenue when one subscription is shared across many
devices. Hiddify has `shared_limit`; Marzneshin currently does not.
Marzban-era limiters parse local Xray files and do not match
Marzneshin's control-plane/data-plane split.

The differentiator is a native, panel-owned limiter that works with
Marznode and does not create upstream-sync conflicts.

## How

### Policy

`hardening/iplimit/db.py` defines:

- `IpLimitConfig`: global default policy.
- `UserIpLimitOverride`: nullable per-user override row. `NULL` means
  inherit the global policy.

The effective policy is:

1. First row from `aegis_iplimit_config`, else built-in defaults.
2. Per-user override fields when present.

Defaults:

- `max_concurrent_ips = 3`
- `window_seconds = 300`
- `violation_action = "warn"`
- `disable_duration_seconds = 3600`

### Redis

All runtime state lives under `aegis:iplimit:*`:

- `observed:{user_id}`: ZSET member IP, score last-seen unix timestamp.
- `violation:{user_id}`: STRING unix timestamp until a disable expires.
- `audit:{user_id}`: capped LIST of JSON audit events.
- `dedupe:{user_id}`: STRING event fingerprint with a short TTL, used to
  avoid duplicate warns or disables on an unchanged IP set.

If `REDIS_URL` is unset, the task logs one disabled notice per process
start and skips. Endpoints still return effective SQL policy with empty
runtime state.

### Event Collection

The detector consumes access log lines via existing Marznode clients
(`app.marznode.nodes[*].get_logs("xray", include_buffer=True)`). It does
not open new gRPC connections and does not read local Xray log files.

The parser extracts:

- username from `email: <username>`
- source IP from `from tcp:<ip>:<port>` or `from <ip>:<port>`

Usernames are resolved against enabled, non-removed users from the
database.

### Detection

Every poll:

1. Build username to user-id map for enabled users.
2. Collect bounded recent events from existing Marznode clients.
3. ZADD observed IPs by user.
4. Remove entries older than each user's effective window.
5. Count distinct IPs in the window.
6. If count exceeds policy:
   - write audit entry
   - action `warn`: Telegram alert, deduped by current IP set
   - action `disable`: set disable-until in Redis, deactivate the user
     through the same ORM path used by the user route, and push the
     update to Marznode
7. Re-enable users whose Redis disable-until timestamp has passed.

The detector is idempotent for repeated runs with the same observed IP
set inside the policy window.

## Risks

| Risk | Mitigation |
|---|---|
| Xray access log format differs | Parser is isolated and unit-tested; unparseable lines are ignored. |
| Redis missing | Feature disabled without crashing, per D-008. |
| Duplicate punishment | Dedupe key plus disable-until key make repeated polls idempotent. |
| Upstream conflicts | Runtime code lives under `hardening/iplimit/`; app integration stays in `hardening/panel/middleware.py`. |
| Temporary disable lost after Redis flush | Accepted MVP trade-off; durable enforcement can move to a hardening-owned table later if operators need it. |

## Acceptance Criteria

- [ ] Models and migration create `aegis_iplimit_config` and
      `aegis_iplimit_override`.
- [ ] Redis keyspace uses only `aegis:iplimit:*`.
- [ ] Redis disabled path logs once and skips.
- [ ] Scheduler task registered from `apply_panel_hardening()`.
- [ ] REST endpoints are sudo-admin only and typed with Pydantic.
- [ ] Tests cover window counting, warn, disable, Redis disabled skip,
      idempotent re-run, and override fallback.
- [ ] Dashboard uses `t(key, "English default")` for new strings and does
      not edit locale JSON files.
- [ ] `hardening/iplimit/README.md` documents operator usage.
- [ ] CI checks pass: ruff, pytest, dashboard build, dashboard lint.

