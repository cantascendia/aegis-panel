#!/usr/bin/env bash
# scripts/aegis-sync-clients.sh — Phase C workaround for L-032 mTLS bug.
#
# panel↔marznode gRPC SyncUsers stream task dies after first iteration
# of _monitor_channel timeout (grpclib.py:82-84 cancels streaming on
# transient __connect__ timeout). Result: panel API user-create/delete
# never reaches marznode, xray_config.json stays out of sync with DB.
#
# This script bypasses the broken RPC channel entirely:
# 1. Read panel SQLite DB → get all active users + their `key`
# 2. Transform key → xray UUID via xxhash.xxh128 (matches panel/utils/keygen.py)
# 3. Atomically rewrite xray_config.json clients[] (preserve other inbound config)
# 4. Restart marznode container so xray-core reloads
#
# Usage: aegis-sync-clients
#
# Idempotent. Safe to run as cron / after every panel user op.
#
# Refs: L-032 root cause analysis, PLAN-mtls-fix.md Phase C

set -euo pipefail
IFS=$'\n\t'

PANEL_CONTAINER="${AEGIS_PANEL_CONTAINER:-aegis-panel}"
XRAY_CONFIG="${AEGIS_XRAY_CONFIG:-/opt/aegis/data/marznode/xray_config.json}"
COMPOSE_FILE="${AEGIS_COMPOSE_FILE:-/opt/aegis-src/deploy/compose/docker-compose.sqlite.yml}"
DB_PATH_IN_CONTAINER="${AEGIS_DB_IN_CONTAINER:-/var/lib/marzneshin/db.sqlite3}"

if ! docker ps --format '{{.Names}}' | grep -q "^${PANEL_CONTAINER}$"; then
  echo "[sync] FATAL: panel container '${PANEL_CONTAINER}' not running" >&2
  exit 2
fi
if [[ ! -f "${XRAY_CONFIG}" ]]; then
  echo "[sync] FATAL: xray config not found at ${XRAY_CONFIG}" >&2
  exit 2
fi

# Generate clients JSON array from panel DB (using xxhash.xxh128 transform
# from app/utils/keygen.py:gen_uuid — guarantees match with vless URI).
CLIENTS_JSON="$(docker exec "${PANEL_CONTAINER}" python3 -c "
import json, sqlite3, uuid, xxhash
c = sqlite3.connect('${DB_PATH_IN_CONTAINER}')
clients = []
# Active users only (removed=0). enabled flag exists on some schema versions.
rows = c.execute(
    \"select id, username, key from users where removed=0 and enabled=1\"
).fetchall()
for uid, uname, key in rows:
    xray_uuid = str(uuid.UUID(bytes=xxhash.xxh128(key.encode()).digest()))
    # email = numeric user.id (matches marznode's int(stat.name.split('.')[0]))
    clients.append({'id': xray_uuid, 'email': str(uid), 'flow': ''})
print(json.dumps(clients))
")"

if [[ -z "${CLIENTS_JSON}" ]]; then
  echo "[sync] FATAL: panel DB query returned empty" >&2
  exit 3
fi

CLIENT_COUNT="$(echo "${CLIENTS_JSON}" | python3 -c 'import json,sys; print(len(json.loads(sys.stdin.read())))')"
echo "[sync] generated ${CLIENT_COUNT} clients from panel DB"

# Atomic rewrite (backup + jq + mv).
BAK="${XRAY_CONFIG}.bak.$(date -u +%Y%m%dT%H%M%SZ)"
cp "${XRAY_CONFIG}" "${BAK}"
TMP="$(mktemp)"
jq --argjson cs "${CLIENTS_JSON}" \
   '.inbounds[].settings.clients = $cs' \
   "${XRAY_CONFIG}" >"${TMP}"
chmod 644 "${TMP}"
mv -f "${TMP}" "${XRAY_CONFIG}"

echo "[sync] xray_config rewritten (backup: ${BAK})"

# Restart marznode so xray-core picks up new config.
echo "[sync] restarting marznode..."
docker compose -f "${COMPOSE_FILE}" restart marznode >/dev/null 2>&1
echo "[sync] done. ${CLIENT_COUNT} active users now in xray."
