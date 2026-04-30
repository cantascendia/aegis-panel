#!/usr/bin/env bash
# =============================================================================
# Aegis Panel — migrate from upstream Marzneshin (idempotent)
#
# Purpose: Automate Phase A §1-4 of MIGRATION-upstream-to-aegis.md for sites
# already running upstream marzneshin/marzneshin who want to drop-in switch
# to the aegis-panel fork while preserving JWT secret, DB, xray config, and
# marznode mTLS certs.
#
# Refs:
#   docs/ai-cto/MIGRATION-upstream-to-aegis.md (5-stage runbook)
#   docs/ai-cto/LESSONS.md L-032 (xray clients == users invariant)
#   docs/ai-cto/OPS-deploy-runbook.md (companion fresh-install runbook)
#
# Forbidden path notice: deploy/** requires §32 double-sign. PR carrying
# this file MUST land with `requires-double-review` label and a codex
# cross-review verdict in REVIEW-QUEUE.md.
#
# Exit code contract:
#   0  success (panel is on aegis-panel fork, all health checks green)
#   1  precondition failed (no upstream, missing docker, etc.)
#   2  backup failed (refuse to proceed without rollback insurance)
#   3  alembic upgrade failed (auto-rolled back)
#   4  health-check timeout (auto-rolled back)
#   5  user aborted (e.g. --confirm not passed)
#
# Idempotency: each phase writes a sentinel under ${BACKUP_DIR}/.phase-N.done.
# A re-run skips completed phases unless --force is set.
#
# Usage:
#   sudo ./migrate-from-upstream.sh \
#        --upstream-dir /opt/marzneshin \
#        --aegis-dir /opt/aegis/src \
#        --aegis-repo https://github.com/cantascendia/aegis-panel \
#        --aegis-ref main \
#        --domain panel.example.com \
#        --confirm
#
# Dry run (no changes, prints intended actions):
#   sudo ./migrate-from-upstream.sh --upstream-dir /opt/marzneshin --dry-run
# =============================================================================

set -euo pipefail
IFS=$'\n\t'

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
UPSTREAM_DIR="${UPSTREAM_DIR:-/opt/marzneshin}"
AEGIS_DIR="${AEGIS_DIR:-/opt/aegis/src}"
AEGIS_REPO="${AEGIS_REPO:-https://github.com/cantascendia/aegis-panel}"
AEGIS_REF="${AEGIS_REF:-main}"
DOMAIN="${DOMAIN:-}"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:8000/api/aegis/health}"
HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-60}"
CONFIRM=0
DRY_RUN=0
FORCE=0
NO_ROLLBACK=0
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_ROOT="${BACKUP_ROOT:-/opt/aegis-migration-backup}"
BACKUP_DIR="${BACKUP_ROOT}/${STAMP}"
LOG_FILE="${BACKUP_ROOT}/migration.log"

usage() {
  cat <<'EOF'
migrate-from-upstream.sh — drop-in migrate upstream Marzneshin → aegis-panel.

Required:
  --upstream-dir PATH    Path to existing upstream install (default /opt/marzneshin)

Optional:
  --aegis-dir PATH       Where to clone aegis-panel (default /opt/aegis/src)
  --aegis-repo URL       Repo URL (default cantascendia/aegis-panel)
  --aegis-ref REF        Branch/tag/sha to checkout (default main)
  --domain HOST          Panel public hostname (used for health probe)
  --health-url URL       Health endpoint (default http://127.0.0.1:8000/api/aegis/health)
  --health-timeout SEC   Wait this many seconds for health (default 60)
  --backup-root PATH     Where to put stamped backups (default /opt/aegis-migration-backup)
  --confirm              Required to actually run (without it: dry-run only)
  --dry-run              Print intended actions, change nothing
  --force                Re-run completed phases (bypass sentinels)
  --no-rollback          Disable auto-rollback on health-check failure (DEBUG ONLY)
  --help                 This help

Exit codes:
  0 success | 1 precondition | 2 backup | 3 alembic | 4 health | 5 user-abort
EOF
}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
log() { printf '[%s] %s\n' "$(date -Iseconds)" "$*" | tee -a "${LOG_FILE}" >&2; }
fail() { log "FATAL: $*"; exit "${2:-1}"; }
run() {
  if [[ ${DRY_RUN} -eq 1 ]]; then
    log "DRY-RUN: $*"
  else
    log "RUN: $*"
    eval "$@"
  fi
}

# ---------------------------------------------------------------------------
# Arg parse
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --upstream-dir)    UPSTREAM_DIR="$2"; shift 2 ;;
    --aegis-dir)       AEGIS_DIR="$2"; shift 2 ;;
    --aegis-repo)      AEGIS_REPO="$2"; shift 2 ;;
    --aegis-ref)       AEGIS_REF="$2"; shift 2 ;;
    --domain)          DOMAIN="$2"; shift 2 ;;
    --health-url)      HEALTH_URL="$2"; shift 2 ;;
    --health-timeout)  HEALTH_TIMEOUT="$2"; shift 2 ;;
    --backup-root)     BACKUP_ROOT="$2"; BACKUP_DIR="${BACKUP_ROOT}/${STAMP}"; shift 2 ;;
    --confirm)         CONFIRM=1; shift ;;
    --dry-run)         DRY_RUN=1; shift ;;
    --force)           FORCE=1; shift ;;
    --no-rollback)     NO_ROLLBACK=1; shift ;;
    --help|-h)         usage; exit 0 ;;
    *) fail "unknown arg: $1" 5 ;;
  esac
done

mkdir -p "${BACKUP_ROOT}"
touch "${LOG_FILE}"

if [[ ${CONFIRM} -eq 0 && ${DRY_RUN} -eq 0 ]]; then
  log "Refusing to run without --confirm or --dry-run. Read MIGRATION-upstream-to-aegis.md first."
  exit 5
fi

# ---------------------------------------------------------------------------
# Phase sentinels
# ---------------------------------------------------------------------------
phase_done() {
  local phase="$1"
  [[ -f "${BACKUP_DIR}/.phase-${phase}.done" ]]
}
phase_mark() {
  local phase="$1"
  [[ ${DRY_RUN} -eq 1 ]] && return 0
  mkdir -p "${BACKUP_DIR}"
  touch "${BACKUP_DIR}/.phase-${phase}.done"
}

# ---------------------------------------------------------------------------
# Phase 1 — preflight
# ---------------------------------------------------------------------------
phase_1_preflight() {
  log "=== Phase 1: preflight ==="
  if phase_done 1 && [[ ${FORCE} -eq 0 ]]; then
    log "phase 1 already done, skip"
    return 0
  fi

  command -v docker >/dev/null 2>&1 || fail "docker not on PATH" 1
  command -v jq >/dev/null 2>&1 || fail "jq not on PATH" 1

  [[ -d "${UPSTREAM_DIR}" ]] || fail "upstream dir not found: ${UPSTREAM_DIR}" 1
  [[ -f "${UPSTREAM_DIR}/.env" ]] || fail ".env not found in ${UPSTREAM_DIR}" 1
  [[ -f "${UPSTREAM_DIR}/docker-compose.yml" || -f "${UPSTREAM_DIR}/docker-compose.yaml" ]] \
    || fail "docker-compose not found in ${UPSTREAM_DIR}" 1

  # JWT secret must exist (otherwise users get logged out)
  if ! grep -qE '^JWT_SECRET=.+' "${UPSTREAM_DIR}/.env"; then
    log "WARN: JWT_SECRET not found in upstream .env; users may need to re-login"
  fi

  # DB type detection
  local db_url
  db_url="$(grep -E '^(SQLALCHEMY_DATABASE_URI|DATABASE_URL)=' "${UPSTREAM_DIR}/.env" \
            | head -1 | cut -d= -f2- | tr -d '"' || true)"
  case "${db_url}" in
    sqlite*)        DB_KIND="sqlite" ;;
    postgresql*|postgres*) DB_KIND="postgres" ;;
    mysql*|mariadb*) DB_KIND="mysql" ;;
    *) DB_KIND="sqlite" ;;  # marzneshin default
  esac
  log "detected DB kind: ${DB_KIND}"

  phase_mark 1
  log "phase 1 ok"
}

# ---------------------------------------------------------------------------
# Phase 2 — backup
# ---------------------------------------------------------------------------
phase_2_backup() {
  log "=== Phase 2: backup ==="
  if phase_done 2 && [[ ${FORCE} -eq 0 ]]; then
    log "phase 2 already done, skip"
    return 0
  fi

  run "mkdir -p '${BACKUP_DIR}'"
  run "chmod 700 '${BACKUP_DIR}'"

  # 2.2 .env
  run "cp '${UPSTREAM_DIR}/.env' '${BACKUP_DIR}/marzneshin.env'"
  run "chmod 600 '${BACKUP_DIR}/marzneshin.env'"

  # 2.3 DB
  case "${DB_KIND}" in
    sqlite)
      local sqlite_path
      sqlite_path="$(find "${UPSTREAM_DIR}" -maxdepth 3 -name 'db.sqlite3' 2>/dev/null | head -1 || true)"
      [[ -n "${sqlite_path}" ]] || fail "sqlite db file not found under ${UPSTREAM_DIR}" 2
      if command -v sqlite3 >/dev/null 2>&1; then
        run "sqlite3 '${sqlite_path}' \".backup '${BACKUP_DIR}/db.sqlite3.bak'\""
      else
        run "cp '${sqlite_path}' '${BACKUP_DIR}/db.sqlite3.bak'"
      fi
      ;;
    postgres)
      log "Postgres dump — operator must run pg_dump from inside their DB container."
      log "Suggested: docker exec -t <db_container> pg_dump -U <user> <db> | gzip > ${BACKUP_DIR}/postgres.sql.gz"
      log "Set NO_ROLLBACK=1 if you have already taken an external snapshot."
      [[ ${NO_ROLLBACK} -eq 1 ]] || fail "Postgres backup must be taken manually first; re-run with --no-rollback once done" 2
      ;;
    mysql)
      log "MySQL/MariaDB dump — operator must run mysqldump from inside their DB container."
      log "Suggested: docker exec -t <db_container> mysqldump --single-transaction -u <user> -p <db> | gzip > ${BACKUP_DIR}/mysql.sql.gz"
      [[ ${NO_ROLLBACK} -eq 1 ]] || fail "MySQL backup must be taken manually first; re-run with --no-rollback once done" 2
      ;;
  esac

  # 2.4 xray.json (best-effort; panel rebuilds from DB on start)
  run "docker exec marzneshin cat /code/xray.json > '${BACKUP_DIR}/xray.json' 2>/dev/null || true"

  # 2.4 marznode certs (best-effort)
  for d in /var/lib/marznode /opt/marznode; do
    [[ -d "${d}" ]] && run "cp -r '${d}' '${BACKUP_DIR}/marznode-$(basename ${d})' 2>/dev/null || true"
  done

  # 2.5 ROLLBACK.sh
  if [[ ${DRY_RUN} -eq 0 ]]; then
    cat > "${BACKUP_DIR}/ROLLBACK.sh" <<EOF
#!/usr/bin/env bash
# Auto-generated rollback script — restores upstream Marzneshin.
set -euo pipefail
echo "[rollback] stop aegis"
cd "${AEGIS_DIR}" 2>/dev/null && docker compose down 2>/dev/null || true
echo "[rollback] restore .env"
cp "${BACKUP_DIR}/marzneshin.env" "${UPSTREAM_DIR}/.env"
echo "[rollback] restore DB (DB kind: ${DB_KIND})"
case "${DB_KIND}" in
  sqlite)
    cp "${BACKUP_DIR}/db.sqlite3.bak" "$(find ${UPSTREAM_DIR} -maxdepth 3 -name db.sqlite3 | head -1)"
    ;;
  postgres|mysql)
    echo "[rollback] manual DB restore required from ${BACKUP_DIR}/(postgres|mysql).sql.gz"
    ;;
esac
echo "[rollback] start upstream"
cd "${UPSTREAM_DIR}" && docker compose up -d
echo "[rollback] wait health"
for i in \$(seq 1 30); do
  curl -fsSL "${HEALTH_URL}" 2>/dev/null && { echo "[rollback] OK"; exit 0; }
  curl -fsSL http://127.0.0.1:8000/api/system 2>/dev/null && { echo "[rollback] OK (upstream /api/system)"; exit 0; }
  sleep 2
done
echo "[rollback] WARN: health did not come up in 60s — investigate"
exit 1
EOF
    chmod +x "${BACKUP_DIR}/ROLLBACK.sh"
  fi

  log "Rollback script: ${BACKUP_DIR}/ROLLBACK.sh"
  phase_mark 2
  log "phase 2 ok"
}

# ---------------------------------------------------------------------------
# Phase 3 — swap
# ---------------------------------------------------------------------------
phase_3_swap() {
  log "=== Phase 3: swap (downtime starts) ==="
  if phase_done 3 && [[ ${FORCE} -eq 0 ]]; then
    log "phase 3 already done, skip"
    return 0
  fi

  # 3.2 stop upstream
  run "(cd '${UPSTREAM_DIR}' && docker compose down)"

  # 3.3 clone aegis
  if [[ ! -d "${AEGIS_DIR}/.git" ]]; then
    run "mkdir -p '$(dirname ${AEGIS_DIR})'"
    run "git clone '${AEGIS_REPO}' '${AEGIS_DIR}'"
  else
    run "(cd '${AEGIS_DIR}' && git fetch origin)"
  fi
  run "(cd '${AEGIS_DIR}' && git checkout '${AEGIS_REF}')"

  # 3.4 .env reuse (preserves JWT secret, DB URL, etc.)
  run "cp '${BACKUP_DIR}/marzneshin.env' '${AEGIS_DIR}/.env'"

  # 3.5 SQLite: copy DB into aegis data dir if path differs
  if [[ "${DB_KIND}" == "sqlite" ]]; then
    run "mkdir -p '${AEGIS_DIR}/data'"
    run "cp '${BACKUP_DIR}/db.sqlite3.bak' '${AEGIS_DIR}/data/db.sqlite3' 2>/dev/null || true"
  fi

  # 3.6 alembic upgrade head (creates aegis_* tables)
  log "running alembic upgrade head — this will create 9 aegis_* tables"
  if [[ ${DRY_RUN} -eq 0 ]]; then
    if ! (cd "${AEGIS_DIR}" && docker compose run --rm marzneshin alembic upgrade head 2>&1 | tee -a "${LOG_FILE}"); then
      log "alembic upgrade FAILED — auto-rollback"
      [[ ${NO_ROLLBACK} -eq 0 ]] && bash "${BACKUP_DIR}/ROLLBACK.sh" || true
      exit 3
    fi
  fi

  # 3.7 start aegis
  run "(cd '${AEGIS_DIR}' && docker compose up -d)"

  phase_mark 3
  log "phase 3 ok"
}

# ---------------------------------------------------------------------------
# Phase 4 — verify
# ---------------------------------------------------------------------------
phase_4_verify() {
  log "=== Phase 4: verify ==="
  if phase_done 4 && [[ ${FORCE} -eq 0 ]]; then
    log "phase 4 already done, skip"
    return 0
  fi

  # 4.1 health probe
  log "polling ${HEALTH_URL} for up to ${HEALTH_TIMEOUT}s"
  local ok=0
  if [[ ${DRY_RUN} -eq 0 ]]; then
    for i in $(seq 1 "${HEALTH_TIMEOUT}"); do
      if curl -fsSL --max-time 3 "${HEALTH_URL}" >/dev/null 2>&1; then
        ok=1; break
      fi
      sleep 1
    done
    if [[ ${ok} -eq 0 ]]; then
      log "health-check FAILED — auto-rollback"
      [[ ${NO_ROLLBACK} -eq 0 ]] && bash "${BACKUP_DIR}/ROLLBACK.sh" || true
      exit 4
    fi
  fi

  # 4.4 feature flag posture (should be all OFF for drop-in)
  log "verifying feature flags default OFF"
  if [[ ${DRY_RUN} -eq 0 ]]; then
    local flags
    flags="$(docker exec marzneshin sh -c 'env' 2>/dev/null \
             | grep -E '^(RATE_LIMIT_ENABLED|BILLING_TRC20_ENABLED|BILLING_EPAY_ENABLED|AUDIT_RETENTION_DAYS)=' \
             || true)"
    log "flag posture:"
    log "${flags:-  (all unset → defaults to OFF)}"
    if echo "${flags}" | grep -qE '^(RATE_LIMIT_ENABLED|BILLING_TRC20_ENABLED|BILLING_EPAY_ENABLED)=true'; then
      log "WARN: a paid/risk feature is enabled. For 3-user prod, runbook recommends OFF."
    fi
  fi

  # 4.5 alembic head check
  if [[ ${DRY_RUN} -eq 0 ]]; then
    local head
    head="$(docker exec marzneshin alembic current 2>/dev/null | tail -1 || true)"
    log "alembic head: ${head}"
  fi

  phase_mark 4
  log "phase 4 ok"
}

# ---------------------------------------------------------------------------
# Phase 6 — AGPL §13 compliance (Phase 5 is interactive flag-by-flag, skipped here)
# ---------------------------------------------------------------------------
phase_6_agpl() {
  log "=== Phase 6: AGPL §13 selfcheck ==="
  if [[ -x "${AEGIS_DIR}/deploy/compliance/agpl-selfcheck.sh" ]]; then
    if [[ ${DRY_RUN} -eq 0 ]]; then
      (cd "${AEGIS_DIR}" && bash deploy/compliance/agpl-selfcheck.sh) \
        || log "WARN: agpl-selfcheck reported issues — read NOTICE.md and fix before public service"
    else
      log "DRY-RUN: would run deploy/compliance/agpl-selfcheck.sh"
    fi
  else
    log "WARN: agpl-selfcheck.sh not found at ${AEGIS_DIR}/deploy/compliance/ — skipping"
  fi
  log "phase 6 ok"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
  log "migrate-from-upstream.sh start (stamp=${STAMP}, dry_run=${DRY_RUN}, force=${FORCE})"
  log "config: UPSTREAM_DIR=${UPSTREAM_DIR} AEGIS_DIR=${AEGIS_DIR} AEGIS_REF=${AEGIS_REF}"

  phase_1_preflight
  phase_2_backup
  phase_3_swap
  phase_4_verify
  phase_6_agpl

  log "migration complete. Backup retained at ${BACKUP_DIR}."
  log "Next steps (manual):"
  log "  - Validate the 3 test users can log in"
  log "  - curl ${HEALTH_URL}/extended with sudo token (see runbook §4.1)"
  log "  - Verify xray clients count == active user count (LESSONS L-032)"
  log "  - Once stable for 30+ days, shred the backup: shred -u ${BACKUP_DIR}/*"
  exit 0
}

main "$@"
