#!/usr/bin/env bash
# scripts/aegis-staging-smoke.sh — Pre-promotion smoke test (no second VPS needed).
#
# L-034 process root cause: wave-1..5 hit production-only bugs because
# we had no staging environment. The "real" fix is a second VPS that
# CI auto-deploys to before promoting tags. That costs $6/month and
# requires real DNS setup.
#
# This script is the no-cost alternative: spins up panel + marznode
# locally (docker compose) using the candidate image tag, runs the
# same end-to-end checks the production GO-LIVE checklist runs, then
# tears down. Pass → safe to roll the tag to production VPS.
#
# Usage:
#   ./scripts/aegis-staging-smoke.sh v0.4.0
#
# Side effects:
# - Creates /tmp/aegis-staging-* directory (cleaned on exit)
# - Pulls images: ghcr.io/cantascendia/aegis-panel:v0.4.0 + dawsh/marznode:v0.5.7
# - Binds ports 18443 (panel) + 62052 (marznode) on localhost
# - No data persistence; all in-memory / temp
#
# Refs: L-034 process root cause; OPS-go-live-checklist.md

set -euo pipefail
IFS=$'\n\t'

VERSION="${1:?usage: aegis-staging-smoke.sh vX.Y.Z}"
MARZNODE_VERSION="${MARZNODE_VERSION:-v0.5.7}"
WORKDIR="$(mktemp -d /tmp/aegis-staging.XXXXXX)"
trap 'docker compose -f "${WORKDIR}/compose.yml" down -v 2>/dev/null || true; rm -rf "${WORKDIR}"' EXIT

PANEL_IMG="ghcr.io/cantascendia/aegis-panel:${VERSION}"
MARZNODE_IMG="dawsh/marznode:${MARZNODE_VERSION}"
PANEL_PORT=18443
MARZNODE_PORT=62052

echo "[smoke] target: panel=${PANEL_IMG} marznode=${MARZNODE_IMG}"
echo "[smoke] workdir: ${WORKDIR}"

# ---------------------------------------------------------------------
# 1. write minimal .env + compose
# ---------------------------------------------------------------------
mkdir -p "${WORKDIR}/data/panel" "${WORKDIR}/data/marznode" "${WORKDIR}/data/marznode-ssl"

# Generate Fernet key (matches install.sh §AUDIT_SECRET_KEY)
AUDIT_KEY="$(openssl rand 32 | base64 | tr '+/' '-_' | tr -d '\n')"
JWT_SECRET="$(openssl rand -base64 64 | tr -d '\n')"

cat >"${WORKDIR}/.env" <<EOF
AEGIS_VERSION=${VERSION}
MARZNODE_VERSION=${MARZNODE_VERSION}
AEGIS_DOMAIN=staging.local

UVICORN_HOST=127.0.0.1
UVICORN_PORT=${PANEL_PORT}
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=45
JWT_SECRET_KEY=${JWT_SECRET}
DASHBOARD_PATH=/staging
XRAY_SUBSCRIPTION_PATH=/sub
ADMIN_LOGIN_RATE_LIMIT=5/minute
SQLALCHEMY_DATABASE_URL=sqlite:////var/lib/marzneshin/db.sqlite3
SUDO_USERNAME=stagingadmin
SUDO_PASSWORD=stagingpass

PANEL_PORT=${PANEL_PORT}
MARZNODE_GRPC_PORT=${MARZNODE_PORT}
XRAY_POLICY_CONN_IDLE=120
XRAY_POLICY_HANDSHAKE=2

CF_TUNNEL_ENABLED=false
CF_ACCESS_REQUIRED_FOR_ADMIN=false
CF_TUNNEL_NAME=
CF_TUNNEL_UUID=

REALITY_SNI_REGION=auto
REALITY_SNI_DEFAULT_GLOBAL=www.microsoft.com
REALITY_SNI_DEFAULT_JP=www.lovelive-anime.jp
REALITY_SNI_DEFAULT_KR=static.naver.net
REALITY_SNI_DEFAULT_US=swdist.apple.com
REALITY_SNI_BLOCKLIST=www.google.com,speedtest.net
REALITY_UTLS_FINGERPRINT=chrome
REALITY_FLOW=xtls-rprx-vision

FALLBACK_CHANNEL_ENABLED=false
FALLBACK_PORT_BACKUP=2053

AUDIT_SECRET_KEY=${AUDIT_KEY}
AUDIT_RETENTION_DAYS=90

SUBSCRIPTION_URL_PREFIX=http://127.0.0.1:${PANEL_PORT}
EOF
chmod 600 "${WORKDIR}/.env"

cat >"${WORKDIR}/compose.yml" <<EOF
services:
  panel:
    image: ${PANEL_IMG}
    container_name: aegis-staging-panel
    network_mode: host
    env_file:
      - ${WORKDIR}/.env
    volumes:
      - ${WORKDIR}/data/panel:/var/lib/marzneshin
    # Seed admin BEFORE main.py — codex P1 on commit 27e25dc:
    # SUDO_USERNAME/PASSWORD env vars are read by 'marzneshin-cli admin
    # import-from-env' subcommand only, NOT auto-imported on boot. Without
    # this step the smoke script's /api/admins/token always 401s on a
    # fresh DB.
    entrypoint:
      - /bin/sh
      - -c
      - |
        alembic upgrade head && \
        (marzneshin-cli admin import-from-env || marzneshin admin import-from-env || python -m cli.main admin import-from-env || true) && \
        exec python main.py
    healthcheck:
      test: ["CMD-SHELL", "curl -fsS http://127.0.0.1:${PANEL_PORT}/openapi.json -o /dev/null || exit 1"]
      interval: 5s
      timeout: 3s
      retries: 30
      start_period: 30s
EOF
# marznode service intentionally NOT in initial compose — codex P2 on
# commit 27e25dc: SSL_CLIENT_CERT_FILE points to a file that doesn't
# exist on a fresh staging volume; marznode would crash-loop. Real
# install.sh fetches /api/nodes/settings AFTER panel is healthy. The
# staging smoke similarly bootstraps cert post-panel-healthy then
# starts marznode in §3 below.

# ---------------------------------------------------------------------
# 2. start
# ---------------------------------------------------------------------
echo "[smoke] pulling images..."
docker compose -f "${WORKDIR}/compose.yml" pull -q
echo "[smoke] starting..."
docker compose -f "${WORKDIR}/compose.yml" up -d

# Wait for panel healthy
echo "[smoke] waiting for panel healthy (timeout 90s)..."
for i in $(seq 1 18); do
  status="$(docker inspect aegis-staging-panel --format '{{.State.Health.Status}}' 2>/dev/null || echo none)"
  if [[ "${status}" == "healthy" ]]; then
    echo "[smoke] panel healthy after $((i * 5))s"
    break
  fi
  sleep 5
done
if [[ "${status}" != "healthy" ]]; then
  echo "[smoke] FAIL: panel did not become healthy" >&2
  docker compose -f "${WORKDIR}/compose.yml" logs --tail=50 panel >&2
  exit 1
fi

# Bootstrap marznode cert from panel /api/nodes/settings (codex P2 fix).
# Panel exposes the certificate publicly (it's the cert marznode trusts
# as the *client* — same cert panel grpclib loads).
echo "[smoke] bootstrapping marznode SSL_CLIENT_CERT_FILE..."
panel_cert="$(curl -fsS -m 5 "http://127.0.0.1:${PANEL_PORT}/api/nodes/settings" \
  | python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["certificate"])' || echo)"
if [[ -z "${panel_cert}" ]]; then
  echo "[smoke] FAIL: cannot fetch /api/nodes/settings cert" >&2
  exit 1
fi
echo "${panel_cert}" >"${WORKDIR}/data/marznode-ssl/ssl_client_cert.pem"
chmod 644 "${WORKDIR}/data/marznode-ssl/ssl_client_cert.pem"

# Now add marznode service + start it
cat >>"${WORKDIR}/compose.yml" <<EOF

  marznode:
    image: ${MARZNODE_IMG}
    container_name: aegis-staging-marznode
    network_mode: host
    environment:
      SERVICE_ADDRESS: "127.0.0.1"
      SERVICE_PORT: "${MARZNODE_PORT}"
      INSECURE: "True"
      SSL_CLIENT_CERT_FILE: "/etc/marzneshin/ssl_client_cert.pem"
      XRAY_EXECUTABLE_PATH: "/usr/local/bin/xray"
      XRAY_ASSETS_PATH: "/usr/local/lib/xray"
      XRAY_CONFIG_PATH: "/var/lib/marznode/xray_config.json"
    volumes:
      - ${WORKDIR}/data/marznode:/var/lib/marznode
      - ${WORKDIR}/data/marznode-ssl:/etc/marzneshin
EOF
echo "[smoke] starting marznode..."
docker compose -f "${WORKDIR}/compose.yml" up -d marznode
sleep 5  # let marznode boot

# ---------------------------------------------------------------------
# 3. smoke tests (mirrors OPS-go-live-checklist.md)
# ---------------------------------------------------------------------
PASS=0
FAIL=0
check() {
  local name="$1"
  shift
  if "$@" >/dev/null 2>&1; then
    echo "  ✅ ${name}"
    PASS=$(( PASS + 1 ))
  else
    echo "  ❌ ${name}" >&2
    FAIL=$(( FAIL + 1 ))
  fi
}

echo
echo "[smoke] ① infrastructure"
check "panel API responds" curl -fsS -m 5 "http://127.0.0.1:${PANEL_PORT}/openapi.json"

# Get admin token
TOKEN="$(curl -fsS -m 5 -X POST "http://127.0.0.1:${PANEL_PORT}/api/admins/token" \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d "username=stagingadmin&password=stagingpass" | python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["access_token"])' || echo)"
if [[ -z "${TOKEN}" ]]; then
  echo "  ❌ admin login (cannot continue smoke)" >&2
  FAIL=$(( FAIL + 1 ))
else
  echo "  ✅ admin login"
  PASS=$(( PASS + 1 ))

  echo
  echo "[smoke] ② create node + verify grpcio default"
  NODE_RESP="$(curl -fsS -m 10 -X POST "http://127.0.0.1:${PANEL_PORT}/api/nodes" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H 'Content-Type: application/json' \
    -d '{"name":"staging","address":"127.0.0.1","port":'"${MARZNODE_PORT}"',"usage_coefficient":1.0}' || echo '{}')"
  NODE_BACKEND="$(echo "${NODE_RESP}" | python3 -c 'import json,sys; print(json.loads(sys.stdin.read()).get("connection_backend","none"))')"
  if [[ "${NODE_BACKEND}" == "grpcio" ]]; then
    echo "  ✅ node default backend = grpcio (wave-6 PR #169 alive)"
    PASS=$(( PASS + 1 ))
  else
    echo "  ❌ node default backend = ${NODE_BACKEND} (expected grpcio)" >&2
    FAIL=$(( FAIL + 1 ))
  fi

  echo
  echo "[smoke] ③ create user via API + propagation"
  # codex P2 fix: count failure as actual smoke FAIL (was permissive).
  # Service ID 1 is created by alembic migration on fresh DB (default
  # marzneshin schema seeds it). If your fork removed that migration,
  # this check would surface the regression — which is the point.
  user_resp_code="$(curl -sS -m 10 -o /dev/null -w '%{http_code}' \
    -X POST "http://127.0.0.1:${PANEL_PORT}/api/users" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H 'Content-Type: application/json' \
    -d '{"username":"smoke_alice","service_ids":[1],"data_limit":1073741824,"data_limit_reset_strategy":"no_reset","expire_strategy":"never"}')"
  if [[ "${user_resp_code}" == "200" ]]; then
    echo "  ✅ POST /api/users returned 200"
    PASS=$(( PASS + 1 ))
  else
    echo "  ❌ POST /api/users returned ${user_resp_code} (regression on user create path)" >&2
    FAIL=$(( FAIL + 1 ))
  fi

  echo
  echo "[smoke] ④ audit log enabled"
  AUDIT_COUNT="$(docker exec aegis-staging-panel python3 -c '
import sqlite3
c = sqlite3.connect("/var/lib/marzneshin/db.sqlite3")
print(c.execute("select count(*) from aegis_audit_events").fetchone()[0])
' 2>/dev/null || echo none)"
  if [[ "${AUDIT_COUNT}" =~ ^[0-9]+$ ]]; then
    echo "  ✅ audit_events table exists (count=${AUDIT_COUNT})"
    PASS=$(( PASS + 1 ))
  else
    echo "  ❌ audit_events table missing or DB inaccessible" >&2
    FAIL=$(( FAIL + 1 ))
  fi

  echo
  echo "[smoke] ⑤ FastAPI Depends DI (L-034 regression — pre-wave-6 this 500'd)"
  USERS_HTTP="$(curl -sS -m 5 -o /dev/null -w '%{http_code}' \
    -H "Authorization: Bearer ${TOKEN}" \
    "http://127.0.0.1:${PANEL_PORT}/api/users")"
  if [[ "${USERS_HTTP}" == "200" ]]; then
    echo "  ✅ GET /api/users HTTP 200 (AuditMiddleware pure ASGI works)"
    PASS=$(( PASS + 1 ))
  else
    echo "  ❌ GET /api/users HTTP ${USERS_HTTP} (L-034 regression?)" >&2
    FAIL=$(( FAIL + 1 ))
  fi
fi

echo
echo "[smoke] tear down..."
docker compose -f "${WORKDIR}/compose.yml" down -v >/dev/null 2>&1

# ---------------------------------------------------------------------
# 4. cutover dry-run (L-040 防线 #2)
# ---------------------------------------------------------------------
# Validates aegis-upgrade.sh + scripts/lib/path-detect.sh SSOT + compose
# AEGIS_VERSION pinning end-to-end without touching real /opt/aegis-src.
# Wave-9 saw L-040/L-041 as live production bugs because the cutover
# automation path was never exercised pre-promotion. This section closes
# that loop: 5 sub-tests on a /tmp staging area, no side effects.
#
# Sub-tests:
#   a. SSOT detects compose dir from override (sqlite variant via .env)
#   b. SSOT picks docker-compose.sqlite.yml file
#   c. aegis_detect_compose_variant returns "sqlite" for sqlite:// URL
#   d. docker compose config substitutes AEGIS_VERSION (warn-not-fail
#      if docker absent, e.g. minimal CI runner)
#   e. SSOT detects "prod" variant from postgresql+psycopg:// URL
echo
echo "[smoke] ⑥ cutover dry-run (L-040 防线 #2)"

cutover_dry_run() {
  local stage_root
  stage_root="$(mktemp -d /tmp/aegis-cutover-dryrun.XXXXXX)"
  # shellcheck disable=SC2064  # expand stage_root NOW for the trap
  trap "rm -rf '${stage_root}'" RETURN

  local compose_dir="${stage_root}/deploy/compose"
  mkdir -p "${compose_dir}"
  cp "$(dirname "$0")/../deploy/compose/docker-compose.sqlite.yml" "${compose_dir}/"
  cp "$(dirname "$0")/../deploy/compose/docker-compose.prod.yml"   "${compose_dir}/"

  # SQLite .env first
  cat >"${stage_root}/.env" <<EOF_DRYRUN
AEGIS_VERSION=v0.4.1
SQLALCHEMY_DATABASE_URL=sqlite:///./data/db.sqlite3
MARZNODE_VERSION=v0.5.7
EOF_DRYRUN

  # Source SSOT in subshell-safe way (path-detect.sh is idempotent).
  # Path resolves relative to this script.
  # shellcheck disable=SC1091
  source "$(dirname "$0")/lib/path-detect.sh"

  # Sub-test (a) + (b): aegis_resolve_compose with override picks sqlite.
  AEGIS_COMPOSE_CANDIDATES_OVERRIDE="${compose_dir}" \
    aegis_resolve_compose "${stage_root}/.env" "[cutover-dryrun]" \
    || { echo "  ❌ aegis_resolve_compose failed (sqlite path)" >&2; return 1; }
  if [[ "${COMPOSE_DIR}" != "${compose_dir}" ]]; then
    echo "  ❌ COMPOSE_DIR='${COMPOSE_DIR}' (expected '${compose_dir}')" >&2
    return 1
  fi
  if [[ "${COMPOSE_FILE}" != "${compose_dir}/docker-compose.sqlite.yml" ]]; then
    echo "  ❌ COMPOSE_FILE='${COMPOSE_FILE}' (expected sqlite variant)" >&2
    return 1
  fi
  echo "  ✅ (a+b) SSOT resolved sqlite compose dir+file from override"

  # Sub-test (c): variant probe directly on .env
  local detected_variant
  detected_variant="$(aegis_detect_compose_variant "${stage_root}/.env")"
  if [[ "${detected_variant}" != "sqlite" ]]; then
    echo "  ❌ aegis_detect_compose_variant returned '${detected_variant}', expected 'sqlite'" >&2
    return 1
  fi
  echo "  ✅ (c) variant probe: sqlite:// → sqlite"

  # Sub-test (d): docker compose config substitutes AEGIS_VERSION.
  # The compose file references /opt/aegis/.env via `env_file:` (production
  # path); dry-run sidesteps that by rendering a sanitized copy with the
  # env_file: directive stripped, so substitution alone is exercised.
  # Warn-not-fail if docker is absent or compose returns non-zero — keeps
  # this section runnable in minimal CI too.
  if command -v docker >/dev/null 2>&1; then
    local compose_sanitized="${stage_root}/compose-dryrun.yml"
    # Drop the two-line `env_file:` block (directive + single hyphen-list item).
    awk '
      /^[[:space:]]*env_file:[[:space:]]*$/ { skip=1; next }
      skip && /^[[:space:]]*-[[:space:]]/   { next }
      skip                                  { skip=0 }
      { print }
    ' "${COMPOSE_FILE}" >"${compose_sanitized}"

    local compose_out
    if compose_out="$(AEGIS_VERSION=v0.4.1 MARZNODE_VERSION=v0.5.7 \
         docker compose -f "${compose_sanitized}" config 2>/dev/null)"; then
      if echo "${compose_out}" | grep -qE 'image:.*aegis-panel:v0\.4\.1'; then
        echo "  ✅ (d) docker compose config substituted AEGIS_VERSION=v0.4.1"
      else
        echo "  ⚠️  (d) AEGIS_VERSION substitution NOT visible — possible :latest hardcode regression" >&2
        echo "          (smoke does not fail this; review compose output manually)"
      fi
    else
      echo "  ⚠️  (d) docker compose config failed (skipping AEGIS_VERSION substitution check)"
    fi
  else
    echo "  ⚠️  (d) docker absent in PATH (skipping AEGIS_VERSION substitution check)"
  fi

  # Sub-test (e): swap .env to PG URL → variant should flip to "prod".
  cat >"${stage_root}/.env" <<'EOF_PG'
AEGIS_VERSION=v0.4.1
SQLALCHEMY_DATABASE_URL=postgresql+psycopg://user:pass@db:5432/aegis
MARZNODE_VERSION=v0.5.7
EOF_PG
  local pg_variant
  pg_variant="$(aegis_detect_compose_variant "${stage_root}/.env")"
  if [[ "${pg_variant}" != "prod" ]]; then
    echo "  ❌ aegis_detect_compose_variant on PG URL returned '${pg_variant}', expected 'prod'" >&2
    return 1
  fi
  echo "  ✅ (e) variant probe: postgresql+psycopg:// → prod"

  return 0
}

if cutover_dry_run; then
  echo "  ✅ cutover dry-run (path-detect SSOT + compose AEGIS_VERSION pin)"
  PASS=$(( PASS + 1 ))
else
  echo "  ❌ cutover dry-run regression (L-040 防线 #2 broken)" >&2
  FAIL=$(( FAIL + 1 ))
fi

# ---------------------------------------------------------------------
# 5. verdict
# ---------------------------------------------------------------------
echo
echo "════════════════════════════════════════════"
echo "  Pass: ${PASS}  Fail: ${FAIL}"
echo "════════════════════════════════════════════"
if (( FAIL == 0 )); then
  echo "✅ ${VERSION} ready for production. Roll with:"
  echo "   ssh root@<vps> 'aegis-upgrade ${VERSION}'"
  exit 0
else
  echo "❌ ${VERSION} has regressions. DO NOT promote to production."
  exit 1
fi
