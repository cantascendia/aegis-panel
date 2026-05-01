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
DB_PATH_IN_CONTAINER="${AEGIS_DB_IN_CONTAINER:-/var/lib/marzneshin/db.sqlite3}"

# Compose file auto-detect (codex P2 review on commit 11b4d08): the path
# varies across install layouts (manual git-clone vs Ansible vs Marzneshin
# upstream layout). Try known paths in priority order; operator can still
# override with AEGIS_COMPOSE_FILE env. SQLite first since that's the S1
# default for low-RAM VPSes.
if [[ -z "${AEGIS_COMPOSE_FILE:-}" ]]; then
  for candidate in \
      /opt/aegis-src/deploy/compose/docker-compose.sqlite.yml \
      /opt/aegis-src/deploy/compose/docker-compose.prod.yml \
      /opt/aegis/src/deploy/compose/docker-compose.sqlite.yml \
      /opt/aegis/src/deploy/compose/docker-compose.prod.yml \
      /opt/aegis/compose/docker-compose.sqlite.yml \
      /opt/aegis/compose/docker-compose.prod.yml; do
    if [[ -f "${candidate}" ]]; then
      COMPOSE_FILE="${candidate}"
      break
    fi
  done
  if [[ -z "${COMPOSE_FILE:-}" ]]; then
    echo "[sync] FATAL: cannot find docker-compose file. Set AEGIS_COMPOSE_FILE." >&2
    exit 2
  fi
else
  COMPOSE_FILE="${AEGIS_COMPOSE_FILE}"
fi

if ! docker ps --format '{{.Names}}' | grep -q "^${PANEL_CONTAINER}$"; then
  echo "[sync] FATAL: panel container '${PANEL_CONTAINER}' not running" >&2
  exit 2
fi
if [[ ! -f "${XRAY_CONFIG}" ]]; then
  echo "[sync] FATAL: xray config not found at ${XRAY_CONFIG}" >&2
  exit 2
fi

# Codex review on commit adae9ad caught: multi-inbound deployments. The
# panel's normal sync path builds per-user inbound tags via get_node_users.
# This workaround currently writes the same clients[] to every inbound. For
# B-stage (single Reality-VLESS inbound on single node) this is correct, but
# multi-inbound topologies need per-inbound user lists. Single-inbound check
# fail-closed if found:
INBOUND_COUNT="$(jq '.inbounds | length' "${XRAY_CONFIG}")"
if [[ "${INBOUND_COUNT}" -gt 1 ]]; then
  echo "[sync] FATAL: ${INBOUND_COUNT} inbounds detected. Per-inbound sync" >&2
  echo "[sync]   not implemented (codex review P1 on adae9ad). This script" >&2
  echo "[sync]   is safe for single-inbound deployments only. Block until" >&2
  echo "[sync]   wave-3 grpclib.py real fix lands or per-inbound logic ships." >&2
  exit 4
fi

# Generate clients JSON array from panel DB.
# UUID generation matches app/utils/keygen.py:gen_uuid (codex P2): respect
# AUTH_GENERATION_ALGORITHM env. PLAIN mode → key as UUID directly; otherwise
# xxhash.xxh128(key) bytes → UUID. Read panel env from container env (the
# panel process loaded its own AUTH_GENERATION_ALGORITHM at boot).
AUTH_ALGO="$(docker exec "${PANEL_CONTAINER}" sh -c 'echo "${AUTH_GENERATION_ALGORITHM:-XXH128}"' | tr -d '[:space:]')"
echo "[sync] panel AUTH_GENERATION_ALGORITHM=${AUTH_ALGO}"

# Preserve flow field of existing clients if any (codex P1.2): if all
# existing clients share the same flow, reuse it; if mixed/empty, default to
# empty (matches what panel emits in vless URI today — `&flow=` not present
# in the subscription URL, so server `flow:""` is correct for current setup).
EXISTING_FLOW="$(jq -r '[.inbounds[].settings.clients[].flow // ""] | unique | if length == 1 then .[0] else "" end' "${XRAY_CONFIG}")"
echo "[sync] preserving flow='${EXISTING_FLOW}' (must match subscription vless URI)"

CLIENTS_JSON="$(docker exec -e AUTH_ALGO="${AUTH_ALGO}" -e EXISTING_FLOW="${EXISTING_FLOW}" "${PANEL_CONTAINER}" python3 -c "
import json, os, sqlite3, uuid, xxhash
auth_algo = os.environ.get('AUTH_ALGO', 'XXH128').upper()
flow = os.environ.get('EXISTING_FLOW', '')
c = sqlite3.connect('${DB_PATH_IN_CONTAINER}')
clients = []
rows = c.execute(
    \"select id, username, key from users where removed=0 and enabled=1\"
).fetchall()
for uid, uname, key in rows:
    if auth_algo == 'PLAIN':
        xray_uuid = str(uuid.UUID(key))
    else:
        xray_uuid = str(uuid.UUID(bytes=xxhash.xxh128(key.encode()).digest()))
    clients.append({'id': xray_uuid, 'email': str(uid), 'flow': flow})
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
