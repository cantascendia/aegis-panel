# SPEC — PostgreSQL 16 + Redis 7 Integration

> Round 1 v0.1 basetable hardening, per `docs/ai-cto/ROADMAP.md` and
> `docs/ai-cto/DECISIONS.md#D-004`.
>
> Status: draft → implementation in PR `feat/postgres-redis`.

---

## What

Make PostgreSQL 16 and Redis 7 first-class optional dependencies of the
panel, without breaking any existing SQLite-backed deployment.

**Scope boundaries**:

- ✅ Provide Docker Compose profiles so operators can spin up PG/Redis
  alongside the panel with one flag.
- ✅ Add an optional Redis client module used by future rate-limit /
  cache code. Startup must not fail if `REDIS_URL` is unset.
- ✅ Document the upgrade path for an existing SQLite deployment.
- ❌ Do **not** force-switch anyone's database.
- ❌ Do **not** implement admin-login rate limiting here — that's the
  next PR, and it will depend on this one landing.
- ❌ Do **not** move hot query paths onto Redis cache. Cache-adoption
  is a per-endpoint decision that lands as separate PRs once we have
  actual latency data to justify it.

## Why

Quoting `docs/ai-cto/VISION.md`:

> 能支撑 ≤1000 用户,>200 付费场景需要以下投入:
> - DB 切 PostgreSQL 16(默认 SQLite 在并发订阅生成时吃不消)
> - Redis 7 作为缓存层(用户查询 / 统计 / 限流令牌桶)

And `AUDIT.md` P1-2: N+1 + Task 异步化 — fixable without Redis but
much cheaper with one.

The concrete triggers:

1. **Concurrency ceiling**. SQLite serializes writes. A single user
   triggering a subscription-generation request while the scheduler
   reviews users will contend; above ~100 concurrent actions the
   symptom is request timeouts, not a clean failure.
2. **Rate limiting** (the next PR) cannot live in-process — the
   whole point is defeating distributed brute force, which requires
   a shared counter. Redis token-bucket is the standard move.
3. **Query caching** for hot reads (subscription endpoint, user
   list, system stats) becomes trivial once Redis exists.

## How

### 1. Database — PostgreSQL 16

**Zero code change required**. `app/db/base.py` already branches on
the URL scheme:

```python
IS_SQLITE = SQLALCHEMY_DATABASE_URL.startswith("sqlite")
if IS_SQLITE: ... else: ...  # pool_size / max_overflow / recycle
```

`requirements.txt` already pins `psycopg==3.1.18` and
`psycopg-binary==3.1.18`.

Operators switch by setting in `.env`:

```
SQLALCHEMY_DATABASE_URL=postgresql+psycopg://aegis:<pw>@postgres:5432/aegis
```

Verification steps documented in `DEVELOPMENT.md`.

**Migration compatibility**: all new Alembic revisions must run green
on both SQLite and PostgreSQL. The existing `tests/test_migrations.py`
(pytest-alembic) already catches SQLite regressions; we extend it to
run against PG via CI services matrix in a later PR (scope creep to
avoid here).

### 2. Redis 7 — optional caching / coordination substrate

New module `app/cache/redis.py`:

- Single async client instance, lazy-initialized on first use.
- Reads `REDIS_URL` from env. **If unset, all Redis operations
  silently no-op** (or raise `RedisDisabled` when explicitly
  required — e.g. rate-limit config should fail-loud if operator
  enables it without providing Redis).
- Connection pool sizing driven by env (`REDIS_POOL_SIZE`,
  default 20).
- Built on the `redis` package's async API (`redis.asyncio`).

This PR does **not** add runtime callers. The module exists so the
next PR (admin rate limit) can import `from app.cache.redis import
get_redis` without negotiating the shape.

### 3. Docker Compose — profiles

New optional services added to `docker-compose.yml`:

```yaml
services:
  postgres:
    image: postgres:16-alpine
    profiles: [postgres]
    ...
  redis:
    image: redis:7-alpine
    profiles: [redis]
    ...
```

Operators opt in:

```
docker compose --profile postgres --profile redis up -d
```

Existing SQLite-only deployments see **no behavior change**.

Both services expose healthchecks, persist to named volumes, and bind
only to localhost by default — access from the panel container is
via compose service name.

### 4. Dependencies

Add to `requirements.txt`:

- `redis==5.2.1` (pure-python async client; no C extension required)

No other changes. `psycopg` already pinned.

### 5. Tests

- `tests/test_redis_optional.py`: when `REDIS_URL` is unset, importing
  the client module must succeed and `get_redis()` must raise a typed
  error without connecting.
- When `REDIS_URL` is set but unreachable, connection errors must
  surface at call time, not at import time — startup must not crash.

Integration tests against real services land in a later CI matrix
expansion (out of scope).

### 6. Documentation

- `DEVELOPMENT.md`: local dev flow with PG + Redis via compose profile.
- `hardening/panel/README.md`: reference Redis as the coordination
  substrate the rate-limit module will use.
- `deploy/compose/` (stub already exists): will receive a
  production-oriented compose overlay in a later PR.

## Risks

| Risk | Mitigation |
|---|---|
| New compose services break `docker compose up` for operators who never set `--profile` | `profiles` key is exactly the Docker-native way to solve this; no-op without the flag. CI doesn't exercise compose, so no additional CI risk. |
| PG migration path breaks for existing SQLite data | Out of scope. Operators with live data export via `marzneshin-cli` and re-import after the switch. Documented. |
| Redis client module imports `redis` package eagerly; startup cost | `redis-py` imports in ~10ms; acceptable. Lazy `get_redis()` connection means no network cost at startup. |
| `REDIS_URL` mistyped silently disables rate-limit later | Address in the rate-limit PR by failing loud when rate-limit is enabled + Redis unreachable. |

## Acceptance criteria

- [ ] `docker compose up -d` (no profile) behaves identically to pre-PR
- [ ] `docker compose --profile postgres up -d` brings up a healthy
  PG 16 container reachable from the panel container
- [ ] `docker compose --profile redis up -d` same for Redis 7
- [ ] `tests/test_redis_optional.py` passes with and without
  `REDIS_URL` set
- [ ] CI pip-audit does not flag `redis==5.2.1`
- [ ] Documentation updates cover local dev and production switch
