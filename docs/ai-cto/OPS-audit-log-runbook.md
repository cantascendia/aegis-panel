# OPS Runbook: Audit Log (S-AL)

**Module**: `ops/audit/`  
**Table**: `aegis_audit_events`  
**Env vars**: `AUDIT_RETENTION_DAYS`, `AUDIT_SECRET_KEY`

---

## §1 Emergency wipe (30 seconds)

> Use only for legal takedown, data subject erasure request, or active breach response.  
> This is irreversible. Confirm with a second operator before executing.

```sql
-- Step 1 — verify row count first
SELECT COUNT(*) FROM aegis_audit_events;

-- Step 2 — wipe (no undo)
DELETE FROM aegis_audit_events;

-- Step 3 — confirm
SELECT COUNT(*) FROM aegis_audit_events;
-- expected: 0
```

To disable all future writes without dropping the table:

```bash
# In .env — set to 0, then restart panel
AUDIT_RETENTION_DAYS=0
# AUDIT_SECRET_KEY can be left as-is (writes are suppressed entirely)
```

With `AUDIT_RETENTION_DAYS=0`: middleware becomes a no-op, endpoints return 503, retention scheduler skips.

---

## §2 Key rotation

```bash
# 1. Generate new key
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 2. Stop the panel

# 3. Re-encrypt all existing rows with new key
#    (use the migration script below — requires old key still available)

# 4. Update .env: AUDIT_SECRET_KEY=<new_key>

# 5. Restart panel
```

**Re-encryption script** (run once, offline):

```python
from cryptography.fernet import Fernet, InvalidToken
from app.db.session import get_db
from ops.audit.db import AuditEvent

OLD_KEY = b"<paste_old_key>"
NEW_KEY = b"<paste_new_key>"
old_f = Fernet(OLD_KEY)
new_f = Fernet(NEW_KEY)

with next(get_db()) as db:
    for row in db.query(AuditEvent).yield_per(500):
        changed = False
        for col in ("before_state_encrypted", "after_state_encrypted"):
            ct = getattr(row, col)
            if ct:
                try:
                    setattr(row, col, new_f.encrypt(old_f.decrypt(ct)))
                    changed = True
                except InvalidToken:
                    pass  # already on new key or corrupt — skip
        if changed:
            db.add(row)
    db.commit()
print("done")
```

---

## §3 Retention sweep (manual trigger)

The APScheduler job runs daily at 03:00 UTC. To trigger manually:

```python
import asyncio
from ops.audit.scheduler import run_audit_retention_sweep
deleted = asyncio.get_event_loop().run_until_complete(run_audit_retention_sweep())
print(f"Deleted {deleted} rows")
```

Or via SQL:

```sql
-- Preview rows that would be deleted (default 90-day window)
SELECT COUNT(*) FROM aegis_audit_events
WHERE ts < NOW() - INTERVAL '90 days';

-- Hard-delete
DELETE FROM aegis_audit_events
WHERE ts < NOW() - INTERVAL '90 days';
```

---

## §4 Query patterns

```sql
-- All actions by a specific admin in last 24 h
SELECT id, ts, action, method, path, result, status_code
FROM aegis_audit_events
WHERE actor_username = 'admin@example.com'
  AND ts > NOW() - INTERVAL '1 day'
ORDER BY ts DESC;

-- All failed/denied actions in last 7 days
SELECT actor_username, action, path, result, status_code, ip, ts
FROM aegis_audit_events
WHERE result IN ('failure', 'denied')
  AND ts > NOW() - INTERVAL '7 days'
ORDER BY ts DESC
LIMIT 200;

-- Activity on a specific invoice
SELECT id, actor_username, action, method, path, result, ts
FROM aegis_audit_events
WHERE path LIKE '%/invoices/123%'
ORDER BY ts;

-- Cross-reference with billing PaymentEvent
-- (link by invoice_id extracted from path + timestamp range)
SELECT a.ts, a.actor_username, a.result,
       p.event_type, p.payload
FROM aegis_audit_events a
JOIN aegis_billing_payment_events p
  ON p.invoice_id = 123
  AND p.created_at BETWEEN a.ts - INTERVAL '5 seconds'
                       AND a.ts + INTERVAL '5 seconds'
WHERE a.path LIKE '%/invoices/123%'
ORDER BY a.ts;
```

---

## §5 Decrypt before/after state (offline)

```python
import os
from cryptography.fernet import Fernet
import json, base64

key = os.environ["AUDIT_SECRET_KEY"].encode()
f = Fernet(key)

# ciphertext is stored as bytes in the DB
def decrypt(ct_bytes):
    return json.loads(f.decrypt(ct_bytes))

# Example
from app.db.session import get_db
from ops.audit.db import AuditEvent

with next(get_db()) as db:
    row = db.get(AuditEvent, <event_id>)
    print("before:", decrypt(row.before_state_encrypted))
    print("after: ", decrypt(row.after_state_encrypted))
```

---

## §6 Export for compliance

```bash
# Via the panel API (sudo admin token required)
curl -H "Authorization: Bearer <token>" \
  "https://panel.example.com/api/audit/events/export.csv" \
  -o audit-export-$(date +%Y%m%d).csv
```

Max 10,000 rows per export call. For full exports, page with `before_id`:

```bash
# Get first 10k, then continue with before_id = last id
curl "...export.csv?limit=10000" -o part1.csv
last_id=$(tail -1 part1.csv | cut -d, -f1)
curl "...export.csv?before_id=$last_id&limit=10000" -o part2.csv
```

---

## §7 Alarm thresholds (suggested)

| Metric | Warning | Critical |
|--------|---------|----------|
| Denied events / 10 min | > 10 | > 50 |
| Failure events / 10 min | > 20 | > 100 |
| Single actor actions / 5 min | > 30 | > 100 |
| Table size | > 5 GB | > 20 GB |
| Rows older than retention | > 1000 | > 10000 |

---

## §8 Billing double-audit coverage

All billing admin endpoints are automatically captured by `AuditMiddleware` because they match `/api/billing/admin/*` (not in the exclude list). Each billing admin write generates:

1. **`aegis_billing_payment_events`** — domain-level event with invoice state transition and `admin_username` in payload (existing system)
2. **`aegis_audit_events`** — HTTP-layer event with actor_id, before_state (request body, encrypted), after_state (response body, encrypted), result, ip, user_agent (new system)

Cross-reference these two tables using `(invoice_id, timestamp range)` — see §4 query pattern above.
