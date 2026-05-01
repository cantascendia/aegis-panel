#!/usr/bin/env bash
# =============================================================================
# Aegis Panel — single-node installer (D.1)
#
# Refs: docs/ai-cto/SPEC-deploy.md §"install.sh 职责(D.1)" — 9 numbered steps.
# Acceptance: AC-D.1.1 through AC-D.1.12 (see SPEC §"Acceptance criteria").
#
# Exit code contract (SPEC §"非交互模式下的输出契约"):
#   0  success
#   1  dependency missing
#   2  configuration invalid
#   3  health check timeout
#   4  port occupied
#   5  reserved (D.4 — CF token scope mismatch)
#
# stdout : machine-readable KV (admin_username=... etc.)
# stderr : human-readable progress
#
# Idempotency: each of the 9 steps writes a sentinel under
# /opt/aegis/.install-step-N.done. A re-run skips completed steps.
# =============================================================================

set -euo pipefail
IFS=$'\n\t'

# ---------------------------------------------------------------------------
# Resolve our own directory so lib sources work whether invoked by absolute
# path, symlink, or `bash install.sh`.
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="${SCRIPT_DIR}/lib"
TEMPLATES_DIR="${SCRIPT_DIR}/templates"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# shellcheck source=lib/detect.sh
. "${LIB_DIR}/detect.sh"
# shellcheck source=lib/render.sh
. "${LIB_DIR}/render.sh"
# shellcheck source=lib/health.sh
. "${LIB_DIR}/health.sh"

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
AEGIS_PREFIX="${AEGIS_PREFIX:-/opt/aegis}"
AEGIS_VERSION="${AEGIS_VERSION:-v0.3.0}"

DB_KIND="postgres"
MARZNODE_MODE="same-host"
DOMAIN=""
ADMIN_USERNAME=""
ADMIN_PASSWORD=""
JWT_SECRET=""
CF_TUNNEL="skip"
NON_INTERACTIVE=0
FROM_ENV=""
DRY_RUN=0
FORCE=0

PANEL_PORT="${PANEL_PORT:-8443}"
MARZNODE_GRPC_PORT="${MARZNODE_GRPC_PORT:-62051}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_DB="${POSTGRES_DB:-aegis}"
POSTGRES_USER="${POSTGRES_USER:-aegis}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-}"
REDIS_PORT="${REDIS_PORT:-6379}"
REDIS_PASSWORD="${REDIS_PASSWORD:-}"
DASHBOARD_PATH="${DASHBOARD_PATH:-}"
XRAY_SUBSCRIPTION_PATH="${XRAY_SUBSCRIPTION_PATH:-}"
DATABASE_URL="${DATABASE_URL:-}"
CF_TUNNEL_ENABLED="false"
CF_TUNNEL_NAME=""

usage() {
  cat <<'EOF'
Aegis Panel installer (single-node, D.1)

Usage:
  install.sh [flags]

Flags:
  --help                       Show this help and exit (0).
  --non-interactive            Take all values from flags / env, never prompt.
  --from-env FILE              Inherit values from an existing rendered .env.
                               Suppresses prompts for fields already set.
  --db {sqlite|postgres}       Database backend (default: postgres). Auto
                               downgraded to sqlite on RAM < 2 GiB.
  --marznode {same-host|skip}  Whether to run a marznode container alongside
                               the panel on this VPS (default: same-host).
  --domain FQDN                Public domain. Required (subscription URLs,
                               CF tunnel, nginx server_name).
  --admin-username USER        Initial admin username (random if omitted).
  --admin-password PASS        Initial admin password (random if omitted).
  --jwt-secret B64             JWT_SECRET_KEY (random 64-byte b64 if omitted).
  --cf-tunnel {yes|no|skip}    Chain into deploy/cloudflare/install-tunnel.sh
                               after panel is healthy. Default: skip.
  --version V                  Override AEGIS_VERSION tag (default: v0.2.0).
  --prefix PATH                Install root (default: /opt/aegis).
  --dry-run                    Validate flags and templates only. No docker
                               compose, no filesystem mutation outside of a
                               temp render.
  --force                      Bypass tier-2 OS warning and continue.

Exit codes:
  0 success / 1 dep missing / 2 config invalid / 3 health timeout / 4 port busy

Examples:
  # Interactive S2 (postgres + same-host marznode + CF tunnel):
  sudo ./install.sh --domain panel.example.com --cf-tunnel yes

  # Non-interactive Ansible call:
  sudo ./install.sh --non-interactive --from-env /opt/aegis/.env

  # S1 light (SQLite, no CF):
  sudo ./install.sh --db sqlite --domain panel.example.com --cf-tunnel no
EOF
}

log()  { printf '[install] %s\n' "$*" >&2; }
warn() { printf '[install] WARN: %s\n' "$*" >&2; }
fatal() {
  local code="${1:-1}"; shift || true
  printf '[install] FATAL: %s\n' "$*" >&2
  exit "${code}"
}

# ---------------------------------------------------------------------------
# Parse flags
# ---------------------------------------------------------------------------
parse_args() {
  while (( $# > 0 )); do
    case "$1" in
      --help|-h)
        usage
        exit 0
        ;;
      --non-interactive) NON_INTERACTIVE=1 ;;
      --from-env)        FROM_ENV="$2"; shift ;;
      --db)              DB_KIND="$2"; shift ;;
      --marznode)        MARZNODE_MODE="$2"; shift ;;
      --domain)          DOMAIN="$2"; shift ;;
      --admin-username)  ADMIN_USERNAME="$2"; shift ;;
      --admin-password)  ADMIN_PASSWORD="$2"; shift ;;
      --jwt-secret)      JWT_SECRET="$2"; shift ;;
      --cf-tunnel)       CF_TUNNEL="$2"; shift ;;
      --version)         AEGIS_VERSION="$2"; shift ;;
      --prefix)          AEGIS_PREFIX="$2"; shift ;;
      --dry-run)         DRY_RUN=1 ;;
      --force)           FORCE=1 ;;
      *)
        echo "unknown flag: $1" >&2
        usage >&2
        exit 2
        ;;
    esac
    shift
  done
}

# ---------------------------------------------------------------------------
# Sentinel helpers
# ---------------------------------------------------------------------------
sentinel_path() { printf '%s/.install-step-%s.done' "${AEGIS_PREFIX}" "$1"; }

step_done() {
  local n="$1"
  [[ -f "$(sentinel_path "${n}")" ]]
}

mark_step_done() {
  local n="$1"
  if (( DRY_RUN )); then return 0; fi
  mkdir -p "${AEGIS_PREFIX}"
  : >"$(sentinel_path "${n}")"
}

# ---------------------------------------------------------------------------
# Step 1 — dependency detection (no install).
# ---------------------------------------------------------------------------
step_1_dependencies() {
  if step_done 1; then log "step 1 (deps): already done, skipping"; return 0; fi
  log "step 1: dependency detection"

  local missing=0
  check_dep docker  "apt-get install -y docker.io || see https://docs.docker.com/engine/install/" || missing=1
  check_docker_compose_v2 || missing=1
  check_dep curl    "apt-get install -y curl"    || missing=1
  check_dep openssl "apt-get install -y openssl" || missing=1
  check_dep jq      "apt-get install -y jq"      || missing=1

  if (( missing )); then
    fatal 1 "one or more dependencies missing — see hints above"
  fi
  mark_step_done 1
}

# ---------------------------------------------------------------------------
# Step 2 — OS / hardware / provider preflight.
# ---------------------------------------------------------------------------
step_2_preflight() {
  if step_done 2; then log "step 2 (preflight): already done, skipping"; return 0; fi
  log "step 2: OS + hardware + provider preflight"

  set +e
  detect_os
  local os_tier=$?
  set -e

  case "${os_tier}" in
    0)
      log "OS tier-1 supported: ${AEGIS_OS_ID} ${AEGIS_OS_VERSION_ID}"
      ;;
    2)
      if (( FORCE )); then
        warn "OS tier-2 (${AEGIS_OS_ID} ${AEGIS_OS_VERSION_ID}) — continuing under --force"
      else
        fatal 2 "OS ${AEGIS_OS_ID} ${AEGIS_OS_VERSION_ID} is tier-2; pass --force to continue or migrate to Ubuntu 22.04/24.04 / Debian 12"
      fi
      ;;
    3)
      fatal 2 "OS ${AEGIS_OS_ID} ${AEGIS_OS_VERSION_ID} is unsupported (CentOS/Alma/RHEL/Fedora). Use Ubuntu 22.04/24.04 or Debian 12."
      ;;
    *)
      fatal 2 "could not classify OS"
      ;;
  esac

  if ! preflight_hardware; then
    fatal 4 "hardware preflight failed — see messages above"
  fi
  if [[ "${AEGIS_FORCE_SQLITE:-0}" == "1" && "${DB_KIND}" == "postgres" ]]; then
    warn "RAM < 2GiB → forcing --db sqlite (was --db postgres)"
    DB_KIND="sqlite"
  fi

  detect_provider_asn || true
  mark_step_done 2
}

# ---------------------------------------------------------------------------
# Step 3 — interactive vs non-interactive prompt resolution.
# ---------------------------------------------------------------------------
prompt_if_empty() {
  # prompt_if_empty VAR_NAME PROMPT [SECRET=0]
  local var="$1" prompt="$2" secret="${3:-0}"
  local current="${!var:-}"
  if [[ -n "${current}" ]]; then return 0; fi
  if (( NON_INTERACTIVE )); then return 0; fi
  if (( secret )); then
    read -r -s -p "${prompt}: " current
    echo >&2
  else
    read -r -p "${prompt}: " current </dev/tty
  fi
  printf -v "${var}" '%s' "${current}"
}

step_3_collect_inputs() {
  if step_done 3; then log "step 3 (inputs): already done, skipping"; return 0; fi
  log "step 3: collect inputs"

  if [[ -n "${FROM_ENV}" ]]; then
    if [[ ! -r "${FROM_ENV}" ]]; then
      fatal 2 "--from-env file not readable: ${FROM_ENV}"
    fi
    # shellcheck disable=SC1090
    set -a; . "${FROM_ENV}"; set +a
    DOMAIN="${AEGIS_DOMAIN:-${DOMAIN}}"
    ADMIN_USERNAME="${SUDO_USERNAME:-${ADMIN_USERNAME}}"
    ADMIN_PASSWORD="${SUDO_PASSWORD:-${ADMIN_PASSWORD}}"
    JWT_SECRET="${JWT_SECRET_KEY:-${JWT_SECRET}}"
    DASHBOARD_PATH="${DASHBOARD_PATH:-}"
    XRAY_SUBSCRIPTION_PATH="${XRAY_SUBSCRIPTION_PATH:-}"
    PANEL_PORT="${PANEL_PORT:-8443}"
    MARZNODE_GRPC_PORT="${MARZNODE_GRPC_PORT:-62051}"
    log "inherited values from ${FROM_ENV}"
  fi

  prompt_if_empty DOMAIN "Public panel domain (FQDN)"
  if [[ -z "${DOMAIN}" ]]; then
    fatal 2 "--domain is required"
  fi
  if [[ "${DOMAIN}" =~ [[:space:]] ]]; then
    fatal 2 "--domain contains whitespace: ${DOMAIN}"
  fi

  case "${DB_KIND}" in
    sqlite|postgres) ;;
    *) fatal 2 "--db must be sqlite or postgres (got ${DB_KIND})" ;;
  esac
  case "${MARZNODE_MODE}" in
    same-host|skip) ;;
    *) fatal 2 "--marznode must be same-host or skip (got ${MARZNODE_MODE})" ;;
  esac
  case "${CF_TUNNEL}" in
    yes|no|skip) ;;
    *) fatal 2 "--cf-tunnel must be yes/no/skip (got ${CF_TUNNEL})" ;;
  esac

  # Auto-fill randoms.
  if [[ -z "${ADMIN_USERNAME}" ]]; then ADMIN_USERNAME="admin-$(rand_urlsafe 6)"; fi
  if [[ -z "${ADMIN_PASSWORD}" ]]; then ADMIN_PASSWORD="$(rand_urlsafe 24)"; fi
  if [[ -z "${JWT_SECRET}"     ]]; then JWT_SECRET="$(rand_secret 64)"; fi
  if [[ -z "${DASHBOARD_PATH}" ]]; then DASHBOARD_PATH="/$(rand_urlsafe 8)"; fi
  if [[ -z "${XRAY_SUBSCRIPTION_PATH}" ]]; then XRAY_SUBSCRIPTION_PATH="/$(rand_urlsafe 8)"; fi
  if [[ -z "${POSTGRES_PASSWORD}" ]]; then POSTGRES_PASSWORD="$(rand_urlsafe 32)"; fi
  if [[ -z "${REDIS_PASSWORD}"    ]]; then REDIS_PASSWORD="$(rand_urlsafe 24)"; fi

  # Build database URL based on selection.
  if [[ "${DB_KIND}" == "postgres" ]]; then
    DATABASE_URL="postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@127.0.0.1:${POSTGRES_PORT}/${POSTGRES_DB}"
  else
    # Container path: panel container mounts ${AEGIS_PREFIX}/data/panel
    # to /var/lib/marzneshin (see compose volumes). The DATABASE_URL the
    # panel reads must reflect the IN-CONTAINER path, not the host path
    # (codex review P1 on commit fb33c57 — host-path URL was the original
    # bug, the render.sh fallback fix was insufficient because this line
    # always overrides the fallback).
    DATABASE_URL="sqlite:////var/lib/marzneshin/db.sqlite3"
    POSTGRES_PASSWORD=""
    REDIS_PASSWORD=""
  fi

  if [[ "${CF_TUNNEL}" == "yes" ]]; then
    CF_TUNNEL_ENABLED="true"
    CF_TUNNEL_NAME="aegis-$(hostname -s 2>/dev/null || echo node)"
  fi

  export AEGIS_VERSION AEGIS_PREFIX
  export DOMAIN ADMIN_USERNAME ADMIN_PASSWORD JWT_SECRET
  export DASHBOARD_PATH XRAY_SUBSCRIPTION_PATH
  export PANEL_PORT MARZNODE_GRPC_PORT
  export POSTGRES_PORT POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD
  export REDIS_PORT REDIS_PASSWORD
  export DATABASE_URL CF_TUNNEL_ENABLED CF_TUNNEL_NAME
  # render_env_template reads AEGIS_DOMAIN by name — alias for clarity.
  export AEGIS_DOMAIN="${DOMAIN}"

  mark_step_done 3
}

# ---------------------------------------------------------------------------
# Step 4 — port availability check (matches AC-D.1.9).
# ---------------------------------------------------------------------------
step_4_ports() {
  if step_done 4; then log "step 4 (ports): already done, skipping"; return 0; fi
  log "step 4: port availability"
  local p
  for p in "${PANEL_PORT}" "${MARZNODE_GRPC_PORT}"; do
    if ! check_port_free "${p}"; then
      fatal 4 "port ${p} occupied (pid=${AEGIS_PORT_OWNER_PID:-unknown}) — free it or pick another via env"
    fi
  done
  if [[ "${DB_KIND}" == "postgres" ]]; then
    if ! check_port_free "${POSTGRES_PORT}"; then
      fatal 4 "postgres port ${POSTGRES_PORT} occupied (pid=${AEGIS_PORT_OWNER_PID:-unknown})"
    fi
  fi
  mark_step_done 4
}

# ---------------------------------------------------------------------------
# Step 5 — render .env to ${AEGIS_PREFIX}/.env (mode 600).
# ---------------------------------------------------------------------------
step_5_render_env() {
  if step_done 5; then log "step 5 (render): already done, skipping"; return 0; fi
  log "step 5: render .env"

  local target="${AEGIS_PREFIX}/.env"
  if (( DRY_RUN )); then
    target="$(mktemp)"
    log "dry-run: rendering to ${target}"
  else
    mkdir -p "${AEGIS_PREFIX}"
    chmod 700 "${AEGIS_PREFIX}"
  fi

  render_env_template "${TEMPLATES_DIR}/env.tmpl" "${target}"
  validate_rendered_env "${target}" || fatal 2 "rendered env failed validation"
  log ".env rendered: ${target}"
  mark_step_done 5
}

# ---------------------------------------------------------------------------
# Step 6 — `docker compose up -d`.
# ---------------------------------------------------------------------------
compose_file_for_kind() {
  if [[ "${DB_KIND}" == "sqlite" ]]; then
    echo "${REPO_ROOT}/deploy/compose/docker-compose.sqlite.yml"
  else
    echo "${REPO_ROOT}/deploy/compose/docker-compose.prod.yml"
  fi
}

prepare_marznode_dirs() {
  # Real-deploy lessons (2026-04-30, see LESSONS L-030):
  #   1) marznode container expects /etc/marzneshin to exist for its
  #      own server keypair generation. Compose mounts the host dir
  #      ${AEGIS_PREFIX}/data/marznode-ssl into it.
  #   2) marznode reads SSL_CLIENT_CERT_FILE on boot; the panel publishes
  #      its client cert via GET /api/nodes/settings AFTER panel is up.
  #      The marznode container will fail to start until the cert is
  #      fetched and dropped here. Step 7 (post-panel-health) chains
  #      fetch_marznode_client_cert below.
  #   3) marznode validates xray_config.json at boot and rejects empty
  #      inbounds (`config doesn't have inbounds`). We seed a placeholder
  #      dokodemo-door inbound; panel pushes the real Reality config via
  #      gRPC after the node registers.
  install -d -m 0755 "${AEGIS_PREFIX}/data/marznode"
  install -d -m 0755 "${AEGIS_PREFIX}/data/marznode-ssl"
  if [[ ! -f "${AEGIS_PREFIX}/data/marznode/xray_config.json" ]]; then
    cp "${TEMPLATES_DIR}/xray_config.json" \
       "${AEGIS_PREFIX}/data/marznode/xray_config.json"
    chmod 0644 "${AEGIS_PREFIX}/data/marznode/xray_config.json"
  fi
}

step_6_compose_up() {
  if step_done 6; then log "step 6 (compose up): already done, skipping"; return 0; fi
  local compose_file
  compose_file="$(compose_file_for_kind)"
  log "step 6: docker compose up -d (${compose_file})"
  if (( DRY_RUN )); then
    log "dry-run: would prepare ${AEGIS_PREFIX}/data/marznode + ${AEGIS_PREFIX}/data/marznode-ssl (skipped)"
    log "dry-run: would run: docker compose -f ${compose_file} --env-file ${AEGIS_PREFIX}/.env up -d panel"
    mark_step_done 6
    return 0
  fi
  prepare_marznode_dirs  # codex P2 fix: gate behind DRY_RUN guard
  # Bring up panel only first; marznode depends on panel-health AND
  # needs the panel-issued client cert (fetched in step 7 once panel
  # is reachable). Bringing up everything at once causes marznode to
  # crash-loop on missing cert.
  docker compose -f "${compose_file}" --env-file "${AEGIS_PREFIX}/.env" up -d panel
  mark_step_done 6
}

# ---------------------------------------------------------------------------
# Step 7 — wait for panel health.
# ---------------------------------------------------------------------------
fetch_marznode_client_cert() {
  # Pull the panel's client cert (returned by /api/nodes/settings) and
  # write it where compose mounts it as SSL_CLIENT_CERT_FILE in the
  # marznode container. Panel must already be healthy. See L-030.
  local out="${AEGIS_PREFIX}/data/marznode-ssl/ssl_client_cert.pem"
  if [[ -s "${out}" ]]; then
    log "marznode client cert already present (${out})"
    return 0
  fi
  log "fetching marznode client cert from panel"
  # Panel /api/nodes/settings is unauthenticated for this single field
  # on Marzneshin; if upstream tightens this in a future release, switch
  # to admin-token auth here.
  local resp
  resp="$(curl -fsS "http://127.0.0.1:${PANEL_PORT}/api/nodes/settings" 2>/dev/null || true)"
  local cert
  cert="$(printf '%s' "${resp}" | jq -r '.certificate // empty' 2>/dev/null || true)"
  if [[ -z "${cert}" ]]; then
    warn "could not fetch panel client cert (response: $(printf '%s' "${resp}" | head -c 80)). marznode will fail to start until cert is provided manually."
    return 1
  fi
  printf '%s\n' "${cert}" > "${out}"
  chmod 0644 "${out}"
  log "wrote marznode client cert (${out})"
}

# ---------------------------------------------------------------------------
# deploy_aegis_upgrade_script — install /usr/local/bin/aegis-upgrade so
# operators can roll the panel image with one command. Idempotent on purpose
# (no step sentinel): re-runs of install.sh keep the on-host script fresh.
# ---------------------------------------------------------------------------
deploy_aegis_upgrade_script() {
  local src="${REPO_ROOT}/scripts/aegis-upgrade.sh"
  local dst="/usr/local/bin/aegis-upgrade"
  if [[ ! -r "${src}" ]]; then
    warn "aegis-upgrade source not found at ${src}, skipping deploy"
    return 0
  fi
  if (( DRY_RUN )); then
    log "dry-run: would install ${dst}"
    return 0
  fi
  install -m 0755 "${src}" "${dst}"
  log "installed ${dst} (run 'aegis-upgrade vX.Y.Z' to roll panel image)"
}

step_7_wait_health() {
  if step_done 7; then log "step 7 (health): already done, skipping"; return 0; fi
  log "step 7: wait for panel health"
  if (( DRY_RUN )); then
    log "dry-run: skipping health check"
    mark_step_done 7
    return 0
  fi
  local compose_file
  compose_file="$(compose_file_for_kind)"
  if ! wait_for_panel_health "${PANEL_PORT}" 120; then
    dump_compose_tail "${compose_file}" panel 50
    fatal 3 "panel did not become healthy"
  fi
  # Now panel is up. Fetch marznode bootstrap cert and bring up marznode.
  if [[ "${MARZNODE_MODE}" == "same-host" ]]; then
    fetch_marznode_client_cert || warn "marznode will not start without client cert"
    log "starting marznode + remaining services"
    docker compose -f "${compose_file}" --env-file "${AEGIS_PREFIX}/.env" up -d
  fi
  mark_step_done 7
}

# ---------------------------------------------------------------------------
# Step 8 — emit credentials to stdout (KV) and INSTALL-SUMMARY.txt.
# ---------------------------------------------------------------------------
step_8_emit_credentials() {
  if step_done 8; then log "step 8 (summary): already done, skipping"; return 0; fi
  log "step 8: emit credentials"

  local dashboard_url="https://${DOMAIN}${DASHBOARD_PATH}"
  local sub_url="https://${DOMAIN}${XRAY_SUBSCRIPTION_PATH}"

  # stdout KV (machine-readable; Ansible `register` parses this).
  printf 'admin_username=%s\n' "${ADMIN_USERNAME}"
  printf 'admin_password=%s\n' "${ADMIN_PASSWORD}"
  printf 'dashboard_url=%s\n'  "${dashboard_url}"
  printf 'subscription_url_prefix=%s\n' "${sub_url}"
  printf 'aegis_version=%s\n'  "${AEGIS_VERSION}"
  printf 'db_kind=%s\n'        "${DB_KIND}"
  printf 'provider_asn=%s\n'   "${AEGIS_PROVIDER_ASN:-unknown}"

  if (( ! DRY_RUN )); then
    local summary="${AEGIS_PREFIX}/INSTALL-SUMMARY.txt"
    {
      echo "Aegis Panel — install summary"
      echo "Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
      echo
      echo "Version       : ${AEGIS_VERSION}"
      echo "Domain        : ${DOMAIN}"
      echo "DB            : ${DB_KIND}"
      echo "Marznode      : ${MARZNODE_MODE}"
      echo "Panel port    : ${PANEL_PORT}"
      echo "gRPC port     : ${MARZNODE_GRPC_PORT}"
      echo "Dashboard URL : ${dashboard_url}"
      echo "Sub URL prefix: ${sub_url}"
      echo "Admin user    : ${ADMIN_USERNAME}"
      echo "Admin pass    : ${ADMIN_PASSWORD}"
      echo "OS            : ${AEGIS_OS_ID:-unknown} ${AEGIS_OS_VERSION_ID:-}"
      echo "Provider ASN  : ${AEGIS_PROVIDER_ASN:-unknown}"
      if [[ -n "${AEGIS_PROVIDER_ASN:-}" ]]; then
        # We don't ship the blocklist file in this PR — record raw value so
        # the operator can cross-check against compass §"脏 ASN 段".
        echo "  (compare against compass 'dirty ASN' list; consider Hetzner / RackNerd / 搬瓦工 CN2 GIA if your ASN is on the GCP/Oracle/Vultr-bulk shortlist.)"
      fi
    } >"${summary}"
    chmod 600 "${summary}"
    log "wrote ${summary}"
  fi

  mark_step_done 8
}

# ---------------------------------------------------------------------------
# Step 9 — print next-step checklist.
# ---------------------------------------------------------------------------
step_9_next_steps() {
  if step_done 9; then log "step 9 (next): already done, skipping"; return 0; fi
  cat >&2 <<EOF

================================================================
Aegis Panel install complete.

Next steps (in order):

  1) Firewall:
       sudo ufw allow 22/tcp
       sudo ufw allow ${PANEL_PORT}/tcp   # only if exposing without CF
       sudo ufw enable

  2) TLS certificate (if not using CF Tunnel):
       sudo apt-get install -y certbot
       sudo certbot certonly --standalone -d ${DOMAIN}

  3) CF Tunnel (recommended for production):
       deploy/cloudflare/install-tunnel.sh   # D.4, separate PR

  4) Subscription smoke test:
       curl -sI https://${DOMAIN}${XRAY_SUBSCRIPTION_PATH}/<token>

  5) AGPL self-check (compliance):
       deploy/compliance/agpl-selfcheck.sh

Credentials are in ${AEGIS_PREFIX}/INSTALL-SUMMARY.txt (mode 600).
================================================================
EOF
  mark_step_done 9
}

# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
main() {
  parse_args "$@"
  log "Aegis installer ${AEGIS_VERSION} starting (prefix=${AEGIS_PREFIX}, dry_run=${DRY_RUN})"

  step_1_dependencies
  step_2_preflight
  step_3_collect_inputs
  step_4_ports
  step_5_render_env
  step_6_compose_up
  step_7_wait_health
  deploy_aegis_upgrade_script
  step_8_emit_credentials
  step_9_next_steps

  log "done."
}

main "$@"
