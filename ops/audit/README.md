# ops/audit — Admin Audit Log (S-AL)

Records every admin mutating operation with actor, payload, result, and timestamp.

## Key files

| File | Purpose |
|---|---|
| `config.py` | Env vars (`AUDIT_RETENTION_DAYS`, `AUDIT_SECRET_KEY`) + Fernet helpers |
| `redact.py` | `REDACT_FIELDS` + `deep_redact()` — runs before encryption |
| `db.py` | `AuditEvent` SQLAlchemy model (`aegis_audit_events`) |
| `schemas.py` | Pydantic schemas for REST API |
| `middleware.py` | `AuditMiddleware` — intercepts POST/PATCH/PUT/DELETE to `/api/` |
| `scheduler.py` | Daily retention sweep at 03:00 UTC |
| `endpoint.py` | REST API: list, detail, export.csv, stats, me/events |

## Environment variables

```env
# 0 = fully disabled (kill-switch for legally hostile environments, D-003)
# Default: 90 days
AUDIT_RETENTION_DAYS=90

# Fernet key for encrypting before/after state at rest. REQUIRED when
# AUDIT_RETENTION_DAYS > 0. Generate:
#   python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
AUDIT_SECRET_KEY=
```

## API routes (sudo-admin unless noted)

```
GET  /api/audit/events                   list + cursor pagination + filters
GET  /api/audit/events/{id}              detail with decrypted before/after
GET  /api/audit/events/export.csv        CSV, max 10 000 rows
GET  /api/audit/stats                    7-day summary
GET  /api/audit/me/events                own events (any admin, no decryption)
```

## Emergency wipe (D-003 legal scenario)

30-second procedure — see `docs/ai-cto/OPS-audit-log-runbook.md §1`.

```sql
-- Hard wipe all audit rows (irreversible):
TRUNCATE aegis_audit_events;
-- Or: set AUDIT_RETENTION_DAYS=0 and restart to stop all future writes.
```

## SPEC

`docs/ai-cto/SPEC-audit-log.md`
