# Codex Delegation Brief — IP Limiter (Round 2 Path C)

> **Purpose**: self-contained briefing for OpenAI Codex App to implement
> `hardening/iplimit/` in an **isolated worktree**, parallel to main
> CTO work on B-batch and A (billing MVP).
>
> **Scope**: ROADMAP.md v0.3 differentiator #2 MVP (moved forward into
> Round 2 after SNI closed). Port Hiddify's `shared_limit` semantics
> to Marzneshin's data model, leveraging Xray stats API via Marznode.

---

## Product context (why this matters)

**Problem**: paid airport operators (>200 users) lose ~30% revenue
when users share subscriptions across >3 devices. Hiddify has
native IP concurrency limiting; Marzneshin does not. Existing
Marzban-era tools (V2IpLimit, miplimiter) are incompatible with
Marzneshin's API — see `docs/ai-cto/COMPETITORS.md`.

**Objective**: detect when a single user's traffic concurrently
originates from >N distinct IPs within a rolling window, and:

1. **Warn** (Telegram + audit log), default action
2. **Disable user** for M minutes (configurable) if violation persists
3. **Never block legitimate mobile-switching cases** (home wifi →
   4G → office wifi should not trip if the IPs don't overlap in
   time)

---

## Architecture constraints (non-negotiable)

1. **Location**: all new code goes under `hardening/iplimit/`. Zero
   modifications to `app/` files. Integration point is ONE import
   + ONE function call inside `hardening/panel/middleware.py::apply_panel_hardening`
   (following the SNI-endpoint precedent in PR #16).

2. **Data source for concurrent-IP counts**: Xray access logs via
   Marznode's gRPC stats API. Marznode already exposes this; see
   `app/marznode/grpclib.py` for the client surface. Do **not**
   parse Xray log files directly (the Marzban-era approach) — that
   breaks the control-plane/data-plane separation that's Marzneshin's
   strongest architectural trait.

3. **Storage**: Redis (via the existing `hardening/panel/rate_limit`
   shared Limiter infrastructure? No — build your own Redis keyspace
   under `aegis:iplimit:*`). Reuse `app/cache/redis.py` for the
   connection + `is_redis_configured()` guard. When Redis unconfigured,
   the feature is **disabled but not crashing** (matches D-008 Redis
   optional contract in DECISIONS.md).

4. **Upstream conflict surface = zero**. If a feature requires changes
   to `app/models/user.py` or `app/db/models.py` (e.g. per-user IP
   limit config), put the new field under a join-table in
   `hardening/iplimit/db.py` with SQLAlchemy 2.0 typed mappings and a
   dedicated Alembic migration. Do not extend upstream models.

5. **License**: Hiddify is AGPL-3.0 — you may study its
   `app/roles/shared_limit.py` logic for *algorithm inspiration*,
   but don't copy code. Independent implementation under this repo's
   AGPL-3.0 umbrella. See `.agents/skills/agpl-compliance/SKILL.md`
   if unsure.

---

## Feature spec (minimum viable)

### Data model

One new table, one new per-user override row, one new Redis keyspace:

```
# SQLAlchemy 2.0 typed (hardening/iplimit/db.py)
class IpLimitConfig(Base):
    __tablename__ = "aegis_iplimit_config"
    id: Mapped[int] = mapped_column(primary_key=True)
    # Default policy applies when no per-user override exists:
    max_concurrent_ips: Mapped[int] = mapped_column(default=3)
    window_seconds: Mapped[int] = mapped_column(default=300)   # 5 min
    violation_action: Mapped[str] = mapped_column(default="warn")  # warn | disable
    disable_duration_seconds: Mapped[int] = mapped_column(default=3600)

class UserIpLimitOverride(Base):
    __tablename__ = "aegis_iplimit_override"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    # All fields optional; NULL == inherit from IpLimitConfig
    max_concurrent_ips: Mapped[int | None]
    window_seconds: Mapped[int | None]
    violation_action: Mapped[str | None]
```

Redis (per-user rolling window, ZADD/ZREMRANGEBYSCORE):

```
aegis:iplimit:observed:{user_id}  # ZSET: ip -> last-seen unix ts
aegis:iplimit:violation:{user_id} # STRING: "disabled_until_ts" when action=disable
aegis:iplimit:audit:{user_id}     # LIST: recent events (capped LPUSH+LTRIM)
```

### Control flow

One APScheduler task in `hardening/iplimit/task.py`, scheduled every
`IPLIMIT_POLL_INTERVAL` seconds (default 30). Task:

1. For each enabled user, pull recent connection events from Marznode
   gRPC stats (use the existing `app/marznode` client; do not open a
   new gRPC connection).
2. ZADD each (user_id, source_ip, now) into the user's `observed` ZSET.
3. ZREMRANGEBYSCORE to drop entries older than `window_seconds`.
4. ZCARD to count distinct IPs in the window.
5. If count > `max_concurrent_ips`:
   - Compose an audit entry {user_id, ip_list, count, action, ts}
   - `violation_action == "warn"`: push to audit list + send Telegram
     alert via existing `app/notification/telegram.py` helper
   - `violation_action == "disable"`: set `violation:{user_id}` in
     Redis with `now + disable_duration_seconds`; also call the
     existing user-disable CRUD path (`app/db/crud.py` — check for
     existing helper; do not write raw SQL)
6. Task must be **idempotent** — re-running after crash should not
   double-count or double-punish.

### Admin UX (dashboard)

Single new dashboard page or section under "Users" → user detail:

- **View**: current IPs observed in window + count
- **Edit**: per-user override form (max_concurrent_ips, window, action)
- **Audit log**: last N violations for this user

Put it in `dashboard/src/modules/users/dialogs/iplimit/`. Mirror the
SNI dialog shape from `dashboard/src/modules/nodes/dialogs/sni-suggest/`
(PR #18).

### API

```
GET  /api/users/{username}/iplimit          → current state + config
PATCH /api/users/{username}/iplimit/override → set overrides
GET  /api/users/{username}/iplimit/audit    → recent violations
```

All sudo-admin only. Route lives in `hardening/iplimit/endpoint.py`,
registered via `apply_panel_hardening(app)` (not under `app/routes/`).

---

## Acceptance criteria (CI must pass these)

- [ ] New SQLAlchemy models + 1 Alembic migration that runs idempotently
      on SQLite + PostgreSQL 16
- [ ] APScheduler task registered in `hardening/iplimit/scheduler.py`
      and hooked via `apply_panel_hardening` (NOT by editing
      `app/tasks/`)
- [ ] Redis keyspace under `aegis:iplimit:*`; when `REDIS_URL` unset,
      the feature is disabled and the task logs one "disabled" notice
      per startup, not per poll
- [ ] Three REST endpoints implemented, sudo-admin gated, with Pydantic
      request/response models
- [ ] Backend tests (mirror PR #13 pattern — no real network):
  - Window-based concurrent-IP counting (ZADD/ZCARD semantics)
  - Warn vs disable action paths
  - Redis-disabled graceful skip
  - Idempotent re-run after simulated crash
  - Per-user override falls back to global config when NULL
  - Target: ≥ 15 passing tests
- [ ] Dashboard component with `t(key, "english default")` pattern for
      i18n (no locale JSON edits — see LESSONS.md L-012)
- [ ] `hardening/iplimit/README.md` with same shape as
      `hardening/sni/README.md`
- [ ] CI green: `Lint (ruff)` + `Test (pytest)` + `Dependency audit
      (pip-audit)` + `Conventional Commit Title`

---

## Suggested PR sequence (to land incrementally)

1. `docs(spec): SPEC-ip-limiter.md` — matches D-005 Spec-Driven convention
2. `feat(hardening): iplimit db models + alembic migration`
3. `feat(hardening): iplimit detector (Redis keyspace + APScheduler task)`
4. `feat(hardening): iplimit REST endpoints`
5. `feat(dashboard): iplimit user-detail section`

If Codex worktree mode lets you land a single PR with all five,
fine — but keep commits separated by concern for easier review.

---

## Model + personality recommendation

- **Model**: `gpt-5.4` (flagship, reasoning=high) for design passes;
  `gpt-5.3-codex` for the mechanical implementation commits
- **Reasoning**: `high` for SPEC draft, `medium` for code
- **Mode**: Worktree (isolated), NOT Local
- **Personality**: Pragmatic

---

## Forbidden (will cause PR rejection)

- Editing any file under `app/` (including `app/models/`, `app/db/`,
  `app/routes/`, `app/tasks/`). If you think you need to, stop and
  report — the constraint is real and there's always an `apply_panel_hardening`
  shaped alternative
- Copying code verbatim from Hiddify. Algorithm study is fine; pasted
  code is an AGPL attribution risk
- Hardcoded secrets / user data / default passwords
- Editing `dashboard/public/locales/*.json` (see LESSONS L-012)
- Skipping the Alembic migration path ("just run the DDL on startup")
- `except: pass` or any bare-except that swallows errors
- Running destructive git commands: `--force`, `reset --hard`, `clean -fd`

---

## Reference files to read before starting

1. `docs/ai-cto/VISION.md` — product positioning
2. `docs/ai-cto/DECISIONS.md` — especially D-008 (Redis optional),
   D-009 (CI gate philosophy), D-005 (Spec-Driven convention)
3. `docs/ai-cto/LESSONS.md` — L-010 to L-013 cover traps you will
   definitely encounter
4. `docs/ai-cto/SPEC-sni-selector.md` — the SPEC format to mirror
5. `hardening/sni/endpoint.py` + `hardening/panel/middleware.py` —
   the integration pattern
6. `app/marznode/grpclib.py` — the gRPC client surface you'll call

---

## Reporting back

When the PR is ready, return to the main CTO session with:

- PR URL
- Branch name
- `git log --oneline main..HEAD` summary
- CI check results (Lint / Test / pip-audit)
- Anything you *couldn't* do and the reason
- Any new LESSON worth logging

The main session will then:
- Read the actual diff (trust but verify per CTO tenet #2)
- Review + merge or request changes
- Update STATUS.md with self-built features 2/8 → 3/8

---

_Brief authored by CTO session 2026-04-22 during Round 2 B-batch cleanup.
Revise this file if the scope shifts before Codex starts._
