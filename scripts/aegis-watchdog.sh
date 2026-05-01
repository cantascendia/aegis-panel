#!/usr/bin/env bash
# scripts/aegis-watchdog.sh — minimal SLO watchdog for B-stage operations.
#
# Runs hourly via cron on the production VPS. Checks:
#   1. Panel + marznode containers Up + healthy
#   2. Panel API /openapi.json returns 200
#   3. Disk space > 20% free on / and /opt
#   4. Audit log row count is non-zero (suggests admin activity)
#   5. xray client count matches active user count (drift detection)
#
# On failure: writes /var/log/aegis-watchdog.log + (optionally) sends
# webhook to TG_WEBHOOK_URL env. Operator should configure cron:
#   0 * * * * /usr/local/bin/aegis-watchdog
# (every hour)
#
# Refs: handbook §43 Reliability Engineering; B-stage SLO baseline.

set -euo pipefail
IFS=$'\n\t'

LOG="${AEGIS_WATCHDOG_LOG:-/var/log/aegis-watchdog.log}"
TG_WEBHOOK="${AEGIS_TG_WEBHOOK:-}"  # optional Telegram bot webhook
COMPOSE_FILE="${AEGIS_COMPOSE_FILE:-/opt/aegis-src/deploy/compose/docker-compose.sqlite.yml}"
PANEL_PORT="${AEGIS_PANEL_PORT:-8443}"
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

declare -a alerts=()

note() {
  echo "[${TS}] $*" >>"${LOG}"
}

alert() {
  local msg="$1"
  alerts+=("$msg")
  note "ALERT: $msg"
}

# 1. Container health
for svc in aegis-panel aegis-marznode; do
  status="$(docker inspect "${svc}" --format '{{.State.Status}}' 2>/dev/null || echo missing)"
  if [[ "${status}" != "running" ]]; then
    alert "${svc} not running (status=${status})"
  fi
  health="$(docker inspect "${svc}" --format '{{.State.Health.Status}}' 2>/dev/null || echo none)"
  if [[ "${health}" != "healthy" && "${health}" != "none" ]]; then
    alert "${svc} unhealthy (health=${health})"
  fi
done

# 2. Panel API
if ! curl -fsS -m 5 -o /dev/null "http://127.0.0.1:${PANEL_PORT}/openapi.json"; then
  alert "panel /openapi.json not responding"
fi

# 3. Disk space
for path in / /opt; do
  pct_used="$(df -P "${path}" | awk 'NR==2 {sub(/%/, "", $5); print $5}')"
  if [[ "${pct_used}" -gt 80 ]]; then
    alert "disk ${path} ${pct_used}% used (>80% threshold)"
  fi
done

# 4. Audit log activity (sanity — middleware writes rows)
audit_count="$(docker exec aegis-panel python3 -c '
import sqlite3
c = sqlite3.connect("/var/lib/marzneshin/db.sqlite3")
print(c.execute("select count(*) from aegis_audit_events").fetchone()[0])
' 2>/dev/null || echo none)"
if [[ "${audit_count}" == "none" ]]; then
  alert "cannot read aegis_audit_events table"
elif [[ "${audit_count}" == "0" ]]; then
  # Not necessarily an alert — could be quiet panel. Note only.
  note "INFO: aegis_audit_events count = 0 (quiet panel, no admin actions)"
else
  note "INFO: aegis_audit_events count = ${audit_count}"
fi

# 5. Drift between panel active users + xray runtime clients
panel_active="$(docker exec aegis-panel python3 -c '
import sqlite3
c = sqlite3.connect("/var/lib/marzneshin/db.sqlite3")
print(c.execute("select count(*) from users where removed=0 and enabled=1").fetchone()[0])
' 2>/dev/null || echo none)"

# Use panel API to get marznode runtime view (xray inbound config endpoint
# returns FILE not runtime — this is L-037 lesson; runtime delta via
# /api/system/stats/users instead, which is canonical)
TOKEN_USER="${AEGIS_WATCHDOG_USER:-}"
TOKEN_PASS="${AEGIS_WATCHDOG_PASS:-}"
if [[ -n "${TOKEN_USER}" && -n "${TOKEN_PASS}" ]]; then
  TOKEN="$(curl -fsS -m 5 -X POST "http://127.0.0.1:${PANEL_PORT}/api/admins/token" \
    -H 'Content-Type: application/x-www-form-urlencoded' \
    -d "username=${TOKEN_USER}&password=${TOKEN_PASS}" 2>/dev/null \
    | python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["access_token"])' 2>/dev/null \
    || echo)"
  if [[ -n "${TOKEN}" ]]; then
    api_active="$(curl -fsS -m 5 -H "Authorization: Bearer ${TOKEN}" \
      "http://127.0.0.1:${PANEL_PORT}/api/system/stats/users" \
      | python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["active"])' 2>/dev/null || echo none)"
    if [[ "${api_active}" =~ ^[0-9]+$ && "${panel_active}" =~ ^[0-9]+$ ]]; then
      if [[ "${api_active}" != "${panel_active}" ]]; then
        alert "active count drift: DB=${panel_active} API=${api_active}"
      fi
    fi
  fi
fi

# Send webhook if any alerts and webhook configured
if [[ ${#alerts[@]} -gt 0 && -n "${TG_WEBHOOK}" ]]; then
  body="🚨 aegis-watchdog (${TS})"$'\n'
  for a in "${alerts[@]}"; do body+="• $a"$'\n'; done
  curl -sS -m 5 -X POST "${TG_WEBHOOK}" \
    -H 'Content-Type: application/json' \
    -d "$(python3 -c "import json,os; print(json.dumps({'text': os.environ['B']}))" B="${body}")" \
    >/dev/null 2>&1 || true
fi

if [[ ${#alerts[@]} -gt 0 ]]; then
  echo "[watchdog] ${#alerts[@]} alert(s); see ${LOG}" >&2
  exit 1
fi

note "OK: all checks passed"
exit 0

# 6. DEBUG flag accidentally left on (wave-9 incident)
# /opt/aegis/.env should NOT have DEBUG=True. The flag disables
# dashboard static-file mount in app/marzneshin.py:main():
#   if not DEBUG: app.mount(DASHBOARD_PATH, StaticFiles(...))
# A leaked DEBUG=True from a marznode debug session blackholes the
# entire dashboard URL silently — operator only finds out when they
# try to log in and get 404.
debug_env="$(grep -E '^DEBUG=' /opt/aegis/.env 2>/dev/null | grep -i 'true' || true)"
if [[ -n "${debug_env}" ]]; then
  alert "DEBUG=True in /opt/aegis/.env — dashboard static mount disabled. Remove this line + restart panel."
fi
