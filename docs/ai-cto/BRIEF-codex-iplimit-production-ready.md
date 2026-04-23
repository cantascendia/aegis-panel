# Codex Delegation Brief — IP Limiter production readiness (Round 3 path B)

> **Purpose**: self-contained briefing for OpenAI Codex App to push the
> existing `hardening/iplimit/` from "MVP with fake tests" to
> "production-ready with real-node verification path", in an **isolated
> worktree** parallel to main CTO work on A.2/A.3 (EPay + TRC20).
>
> **Scope**: follow-ups identified during PR #24 / #26 cross-review
> (see `docs/ai-cto/STATUS.md` 未解决问题 section). No new feature;
> only hardening of the existing one.
>
> **Not in scope**: new functionality. If you think a new algorithm or
> feature is needed, stop and report — this brief is purely
> production-hardening of what's already there.

---

## Product context (why this matters)

Differentiator #2 (IP limiter) is **user-visible**: admin can set
policy + view audit in dashboard, detector runs on schedule, users get
disabled when they share too aggressively. But current confidence
level to turn `violation_action="disable"` on in **production with
real paying users** is LOW. Three reasons:

1. **Real Xray access log format unverified**. Tests use a hand-crafted
   log format `from tcp:1.2.3.4:5 ... email: alice`. Actual format
   from production Xray may differ by punctuation, order, IPv6
   bracketing, etc. If parser misses 50% of real lines, we under-
   observe → false negatives.

2. **No defense against legitimate mobile-switching users**. CGNAT /
   4G↔wifi roaming can legitimately cycle a user through 5+ IPs in
   5 minutes. Default `max_concurrent_ips=3` + no whitelist =
   disabling innocent paying users. We **need** operator-CIDR +
   payment-gateway + trusted-device allowlist infrastructure before
   action is safe in prod.

3. **Redis KEYS scan at >2000 users blocks Redis**. `store.py:93`
   uses `redis.keys(pattern)` which is O(N) and blocks the server.
   At target scale this will degrade the whole panel. Must switch
   to SCAN.

Plus three lower-priority items (TZ docs, poller metrics, clearer
disable-from-admin UX) that are "nice to have" for ops confidence.

---

## Architecture constraints (non-negotiable)

1. **No scope creep**: only touch `hardening/iplimit/*` + its tests +
   `docs/`. If a change needs to reach into `app/` or `ops/billing/`,
   stop and report.

2. **Migration discipline**: any new schema needs a **new Alembic
   revision** downstream of current head `44c0b755e487`. Never
   mutate merged revisions. See L-015 hard rule in
   `docs/ai-cto/LESSONS.md`.

3. **Aggregator registration**: if you add a new SQLAlchemy model,
   register it in `app/db/extra_models.py`, not directly in
   `app/db/migrations/env.py`. See L-014 hard rule.

4. **Redis optional contract (D-008)**: every new code path that
   touches Redis must gracefully skip when Redis is unconfigured.
   Mirror the `_redis_disabled_notice_logged` pattern already in
   `hardening/iplimit/task.py`.

5. **Tests must be offline**: no real Redis, no real Marznode, no
   real Xray, no real network. Mirror the `FakeRedis` + `FakeNode`
   patterns in `tests/test_iplimit.py`.

6. **i18n**: any new dashboard strings use `t(key, "english default")`
   mode. Do not edit locale JSON files. See L-012 + L-017.

7. **Hardening directory only**: NO edits to `app/` or `dashboard/src/`
   modules outside `dashboard/src/modules/users/dialogs/iplimit/`
   and `dashboard/src/modules/users/api/` (the paths the existing
   iplimit UI already owns).

---

## Feature spec (production-readiness checklist)

### B.1 — Real Xray log format validation

**Problem**: `hardening/iplimit/events.py:_EMAIL_RE` +
`_FROM_RE` + `_TIMESTAMP_RE` were designed from memory, not from
real log samples.

**Required**:

1. Add `docs/ai-cto/XRAY-ACCESS-LOG-SAMPLES.md` with **at least 10**
   real-world access-log variants, sourced from:
   - Xray official docs
   - Open-source panels' log capture(look at v2board, SSPanel,
     Hiddify issues — they all debug parsing at some point)
   - Different Xray versions(1.8 vs 1.9 may differ)
   - IPv4 + IPv6 + dual-stack formats
   - With / without TLS, with / without Reality, with / without
     `routing[sniffer]`-derived email
   **Attribute every sample to its source URL** so reviewer can verify.

2. Add `tests/test_iplimit_real_log_variants.py` with a
   parametrized test: feed each sample line to `parse_xray_access_line`
   with `{"alice": 1, "bob": 2, "charlie": 3}`. Assert:
   - IP extracted correctly(string match)
   - Username extracted correctly
   - Timestamp(`observed_at`)extracted if the sample has one

3. If any sample currently fails, fix the regex in `events.py`.
   Document each fix with a comment pointing to the sample ID.
   Keep changes minimal — don't rewrite the parser just because
   one sample is weird; widen specifically for each failing case.

4. If >30% of samples fail in a way that requires rewriting the
   regex fundamentally, STOP and report. That's a design decision,
   not an implementation tweak.

**Acceptance**:
- [ ] `docs/ai-cto/XRAY-ACCESS-LOG-SAMPLES.md` with ≥10 variants
- [ ] `tests/test_iplimit_real_log_variants.py` with parametrized
      test covering all samples; all pass
- [ ] Any regex changes are minimal and commented

---

### B.2 — CIDR allowlist

**Problem**: no escape hatch for legitimate multi-IP users. Default
`max_concurrent_ips=3` will false-positive on:
- Users behind CGNAT (public IP rotates every few minutes)
- Users on mobile 4G carriers (CGNAT + frequent re-assignment)
- Operator's own IP (monitoring, status checks)
- Payment gateway callback IPs (if they happen to show up in logs)

**Required**:

1. Add `ip_allowlist_cidrs` column to `IpLimitConfig`(global)and
   `UserIpLimitOverride`(per-user):
   - Type: `TEXT`(SQLite) / `TEXT`(Postgres), nullable
   - Content: newline-separated list of CIDR strings,
     e.g. `"10.0.0.0/8\n192.168.0.0/16"`
   - Validation: admit only valid CIDRs via `ipaddress.ip_network()`
     at write time
2. Add a **new Alembic revision** downstream of `44c0b755e487`:
   `20260424_<new_id>_iplimit_allowlist_cidrs.py`
3. New `hardening/iplimit/allowlist.py` with:
   ```python
   def parse_cidrs(text: str) -> list[IPv4Network | IPv6Network]: ...
   def ip_matches_any_cidr(ip: str, cidrs: Sequence[...]) -> bool: ...
   ```
4. In `events.py::parse_xray_access_line`, **after** IP parse,
   pass resolved `ip` through allowlist filter. If in allowlist,
   skip(return None — not a ConnectionEvent).
5. Allowlist resolution order: **global union user-level**(both
   apply, if either matches → skip). Cache resolved CIDR list
   per-poll inside `task.run_iplimit_poll`(don't re-parse every
   line).
6. Dashboard UI: add textarea in iplimit dialog for per-user
   allowlist(copy-paste CIDR list). Admin-global UI is out of
   scope here(goes to future global-policy admin page).
7. REST: extend `IpLimitOverridePatch` / `IpLimitConfigResponse`
   with `ip_allowlist_cidrs: str | None`.

**Tests**:
- [ ] `test_parse_cidrs_accepts_ipv4_ipv6_mixed`
- [ ] `test_parse_cidrs_rejects_invalid_cidr`
- [ ] `test_ip_matches_allowlist_ipv4`
- [ ] `test_ip_matches_allowlist_ipv6`
- [ ] `test_ip_outside_allowlist_not_matched`
- [ ] `test_event_parser_skips_allowlisted_ip`
- [ ] `test_override_allowlist_merges_with_global`
- [ ] `test_patch_override_stores_cidrs_accepts_empty_string`

**Acceptance**:
- [ ] Alembic revision passes stepped-upgrade CI(new test-alembic-
      stepped job will cover this automatically)
- [ ] 8+ tests, all offline
- [ ] Dashboard textarea renders + saves + reloads on the user's
      iplimit tab
- [ ] `hardening/iplimit/README.md` section documents the allowlist
      semantics(global ∪ user, CIDR format, why it exists)

---

### B.3 — Redis KEYS → SCAN

**Problem**: `hardening/iplimit/store.py::list_disabled_user_ids`
uses `redis.keys(pattern)`. Redis `KEYS` is O(N) and blocks the
server for the duration. At 2000+ users with iplimit enabled this
will cause 100+ms stalls on the whole Redis cluster.

**Required**:

1. Replace `redis.keys()` with `redis.scan_iter(match=pattern,
   count=500)`:
   ```python
   async def list_disabled_user_ids(redis: object) -> list[int]:
       user_ids: list[int] = []
       async for key in redis.scan_iter(
           match=f"{KEY_PREFIX}:violation:*", count=500,
       ):
           try:
               user_ids.append(int(str(key).rsplit(":", 1)[1]))
           except (IndexError, ValueError):
               continue
       return user_ids
   ```
2. Verify `FakeRedis` in `tests/test_iplimit.py` supports
   `scan_iter` — if not, add an async-iterator implementation that
   mirrors `keys()` behavior(easy; just yield matching keys).
3. Audit the whole `hardening/iplimit/` + `hardening/panel/` for
   any OTHER `redis.keys(` call. Replace each with `scan_iter`.

**Tests**:
- [ ] `test_list_disabled_user_ids_uses_scan_iter`(monkeypatch
      `keys()` to raise, confirm `scan_iter` is what's called)
- [ ] All existing tests still pass with the FakeRedis update

**Acceptance**:
- [ ] No `redis.keys(` calls remain under `hardening/iplimit/`
- [ ] FakeRedis supports `scan_iter` with same semantics as real
      Redis's async iterator
- [ ] New test pinning the SCAN path
- [ ] `docs/ai-cto/LESSONS.md` gets an L-018 if the migration
      surfaced any non-obvious caveat(e.g. cursor lifetime,
      concurrent modification behavior); skip if none worth logging

---

### B.4 — TZ alignment runbook

**Problem**: `_parse_xray_timestamp` in `events.py` uses
`time.mktime()` which converts parsed naive datetime as **system
local time**. Xray log timestamps are in container-local time. If
Marznode container TZ and panel container TZ differ(e.g. Marznode=
UTC, panel=Asia/Shanghai), the parsed timestamp will be off by
hours, causing `zremrangebyscore` to immediately prune all events,
silently disabling detection with NO error.

**Required**:

1. Write `docs/ai-cto/OPS-iplimit-runbook.md` with sections:
   - **Deployment prerequisite**: panel container and all marznode
     containers must have the same TZ(preferred: all UTC via
     `TZ=UTC` env in docker-compose and Dockerfile)
   - **Validation command**: `docker exec marzneshin-panel date &&
     docker exec marznode-1 date` — compare timestamps
   - **Symptoms of mismatch**: iplimit audit shows 0 observed IPs
     even with confirmed user activity; `observed` ZSET scores in
     Redis are from N hours ago
   - **Recovery**: align TZ, restart detector; no DB fix needed
   - **Long-term fix**: switch parser to assume UTC + document in
     SPEC(this goes into B.5 if we do it; skip for this round)
2. Add a startup-time warning to `hardening/iplimit/task.py`: if
   `time.timezone != 0`(i.e. panel not running UTC), log ONE
   warning per process start: `"iplimit: panel container TZ is not
   UTC; confirm all marznode containers match or events may be
   silently dropped"`. Do NOT crash.

**Acceptance**:
- [ ] `OPS-iplimit-runbook.md` merged
- [ ] TZ warning log added + tested
      (`test_non_utc_tz_logs_warning_once`)
- [ ] `README.md` cross-references the runbook

---

### B.5 — "disabled by iplimit" visibility for admins

**Problem**(lower priority — nice-to-have): when admin sees a
user marked `enabled=False` in the main admin panel, there's no
indication whether they were disabled by admin manual action, by
data limit, by expiry, or by iplimit. Post-C-2 fix, iplimit now
only re-enables users it disabled itself, so correctness is fine —
but admins need to **see** this to make informed overrides.

**Required**:

1. Extend `IpLimitStateResponse`(the GET endpoint) to include:
   ```python
   class IpLimitStateResponse(BaseModel):
       ...  # existing fields
       owned_disable: IpLimitOwnedDisableResponse | None

   class IpLimitOwnedDisableResponse(BaseModel):
       disabled_at: int
       disabled_until: int
       reason: str            # "iplimit_violation"
       can_clear: bool        # always True for sudo-admin
   ```
2. In `hardening/iplimit/endpoint.py::get_user_iplimit_state`,
   query `aegis_iplimit_disabled_state` and populate.
3. Dashboard: on the user's iplimit tab, if `owned_disable` is
   present, show a prominent red banner:
   "⚠ Disabled by IP limiter until <time>" + "Clear disable" button
   (already exists, but make it more prominent).

**Tests**:
- [ ] `test_state_endpoint_reports_owned_disable_when_present`
- [ ] `test_state_endpoint_owned_disable_absent_when_no_row`

**Acceptance**:
- [ ] Endpoint populates `owned_disable` from DB
- [ ] Dashboard banner renders conditionally with i18n
      defaultValue mode
- [ ] Cross-check: if admin manually disables user AFTER iplimit
      already did, dashboard still shows the iplimit banner
      (endpoint reads the disabled_state row regardless of current
      `user.enabled`)

---

## Acceptance criteria (CI must pass all)

- [ ] All B.1-B.5 acceptance checklists above tick green
- [ ] `pytest tests/` passes; existing iplimit tests still pass
- [ ] New Alembic revision for B.2 passes **both**:
  - `Test (pytest, PostgreSQL 16)` fresh-DB chain from init
  - `Test (alembic stepped upgrade)` base-then-PR simulation
- [ ] `ruff check hardening deploy ops tests` — clean
- [ ] `ruff format --check` — clean
- [ ] `pip-audit --requirement requirements.txt --strict` — clean
- [ ] `cd dashboard && pnpm run build && pnpm run lint` — green
- [ ] `run-script` (locale drift) — diff not increased
- [ ] Conventional Commit titles on each sub-PR
- [ ] `docs/ai-cto/OPS-iplimit-runbook.md` + `XRAY-ACCESS-LOG-
      SAMPLES.md` both merged

---

## Suggested PR sequence

Each sub-PR independently mergeable; keep commits separated by
concern per `.agents/rules/git-conventions.md`:

1. `docs(ops): iplimit runbook + xray access log samples` — B.1 docs
   + B.4 runbook(docs-only, fast green)
2. `test(hardening): parametrized xray log variant regression` — B.1
   tests + any parser tweaks
3. `feat(hardening): iplimit CIDR allowlist + alembic revision` —
   B.2 full stack including dashboard textarea
4. `refactor(hardening): iplimit redis keys -> scan_iter` — B.3
5. `feat(hardening): iplimit owned-disable visibility + admin banner`
   — B.5

5 sub-PRs, each ≤ 400 lines diff. Aim to land in ~3 days.

---

## Model + personality recommendation

- **Model**: `gpt-5.4` reasoning=high for B.2 design(schema +
  ordering logic); `gpt-5.3-codex` medium reasoning for B.1/B.3/B.4/
  B.5 mechanical work
- **Mode**: Worktree(isolated)
- **Personality**: Pragmatic; no over-engineering. These are
  surgical fixes, not redesigns.

---

## Forbidden (will cause PR rejection)

- Touching `app/` files(except `app/db/extra_models.py` to register
  any new model — that's the ONE allowed entry)
- Touching `ops/billing/` in ANY way(parallel A.2/A.3 work lives
  there; collisions = merge hell)
- Mutating any existing Alembic revision(hard rule L-015)
- Editing `dashboard/public/locales/*.json`(L-012)
- `t("...")` literal inside code comments(L-017)
- Hardcoded secrets / IP / URLs
- Bare `except:` / `except Exception: pass`
- `redis.keys()` anywhere new(we're removing the existing one, don't
  add more)
- Destructive git(`--force`, `reset --hard`, `clean -fd`)

---

## Reference files to read before starting

1. `docs/ai-cto/SPEC-ip-limiter.md` — the original MVP spec
2. `docs/ai-cto/BRIEF-codex-ip-limiter.md` — the original delegation
   brief, for shape reference
3. `docs/ai-cto/LESSONS.md` — especially L-014 / L-015 / L-016 / L-017
4. `hardening/iplimit/` — read all 7 files; especially
   `events.py`, `task.py`, `store.py`
5. `tests/test_iplimit.py` — for the FakeRedis + FakeNode patterns
6. `app/db/extra_models.py` — the aggregator you register through
7. `app/db/migrations/versions/20260423_44c0b755e487_*` — your
   new revision's direct parent(the safety-net migration)

---

## Reporting back

When the sub-PRs are ready, return to the main CTO session with:

- PR URL for each sub-PR
- Branch names
- `git log --oneline main..HEAD` per PR
- CI check results summary
- Anything you **couldn't** do and the reason
- Any new LESSON worth logging(L-018+)
- Specific concern: did the real Xray log samples reveal the parser
  is fundamentally wrong somewhere? If yes, call it out loudly —
  that's production bug territory, not a tweak

The main CTO session will:
- Cross-review B.2(CIDR allowlist — has security edge cases, IPv6
  parsing has gotchas, merge/overlap logic can be subtle) and B.3
  (SCAN semantics have cursor lifetime gotchas). Both worth a
  second pair of eyes per iplimit cross-review ROI precedent
- Merge the rest on green CI
- Update STATUS.md: iplimit "✅ MVP"→ "✅ production-ready,
  E2E pending"

---

## Out of scope(explicitly deferred)

- **Real-node E2E smoke test harness**: requires a real VPS + real
  Marznode + real user + watching real logs. Human-supervised task,
  not a Codex PR. The runbook in B.4 gives operator the steps; this
  brief stops at "build the parts needed to run the E2E; don't run
  it in CI".
- **Admin-global policy UI**: the current flow is per-user. A
  global policy admin page(edit `IpLimitConfig` in UI instead of
  via SQL)is a separate future PR.
- **iplimit metrics export**(Prometheus etc): future observability
  PR, orthogonal.
- **Parser switching to UTC assumption + abandoning TZ concern**:
  that's a breaking change to B.1's regex; do B.4 runbook instead
  this round.

---

_Brief authored by CTO session 2026-04-23 during Round 3 mid
parallel-delegation. Revise if scope shifts before Codex starts._
