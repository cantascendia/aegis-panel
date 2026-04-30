# `ops/audit/` — Panel-wide Audit Log (S-AL session, v0.3 #4)

Append-only audit trail for all admin mutate actions on the control
plane. Powers operator追责 / 客诉举证 / RBAC actor-role 联动.

## Phase status

| Phase | Scope | Status |
|---|---|---|
| **AL.1** | `db.py` (`AuditEvent` model) + Alembic migration | **this PR** |
| AL.2 | `middleware.py` (FastAPI `BaseHTTPMiddleware`) + redact + Fernet encryption | pending |
| AL.3 | `endpoint.py` (sudo-only `GET /api/audit/events` + CSV export) | pending |
| AL.4 | `dashboard/src/modules/audit/` (sudo dashboard page) + retention sweep scheduler task | pending |

Phases land in strict serial order — they share `ops/audit/` directory
and downstream phases depend on upstream model invariants (D-018
SEALED 2026-04-30).

## Sealed decisions (D-018)

See `docs/ai-cto/SPEC-audit-log.md` §"TBD 决策" for the full text.

| TBD | Decision |
|---|---|
| TBD-1 dashboard wipe button | ❌ Not exposed — wipe via `psql` / `TRUNCATE` only (Runbook command, AL.4) |
| TBD-2 REDACT_FIELDS | 🔧 base list `frozenset()` + `.env` `AUDIT_EXTRA_REDACT_FIELDS` union (no override) |
| TBD-3 `payment_events` reverse FK | ❌ Not added — billing autonomy (D-014); use `(invoice_id, ts)` range query |
| TBD-4 `audit` vs `ops_events` | ❌ Separate — `ops_events` is a v0.4 SPEC, not in scope here |

## Schema (this PR)

Single table `aegis_audit_events`. Every column described inline in
`db.py` docstrings — read those, not this README, for invariants.

Indexes:
- `ix_audit_actor_ts` — actor history
- `ix_audit_action_ts` — action history
- `ix_audit_target_ts` — target history
- column-level `index=True` on `ts` — drives retention sweep

Row size: ≈ 2 KB (encrypted state ≈ 1.5 KB + metadata). With ~100
events/day at >200-user scale, 90-day retention table size ≈ 18 MB on
PostgreSQL 16 — no partitioning needed until v1.0.

## Bootstrap & migration safety

- Registered via `app/db/extra_models.py` (LESSONS L-014 — never edit
  `env.py` directly).
- Migration `down_revision = c3d2e1f4a5b6` (latest at branch time —
  billing A.2.2 webhook fields).
- LESSONS L-015 invariant: this revision will never be mutated after
  merge. If schema changes are needed, a new revision is added.
- `pytest tests/test_migrations.py` covers fresh-DB autogen drift;
  `test-alembic-stepped` CI job covers stepped-upgrade safety
  (PR #31, mandatory).

## Cross-references

- SPEC: [`docs/ai-cto/SPEC-audit-log.md`](../../docs/ai-cto/SPEC-audit-log.md)
- Decision: D-018 (SEALED 2026-04-30, issue #103)
- Companion: SPEC-rbac (`actor_role_at_time` snapshot lives here in
  AL.2 once RBAC role assignments table exists)
- Runbook: `docs/ai-cto/OPS-audit-log-runbook.md` (lands AL.4)
