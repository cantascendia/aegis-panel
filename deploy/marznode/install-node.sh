#!/usr/bin/env bash
# =============================================================================
# Aegis Panel — standalone marznode installer (D.2)
#
# Provisions a pure data-plane VPS that runs marznode + xray-core and
# accepts gRPC connections from a remote control plane (deploy/install/
# install.sh on a different host). Mirrors the bash conventions from D.1
# (sentinel-based idempotency, --dry-run, --help, set -euo pipefail).
#
# Refs:
#   - docs/ai-cto/SPEC-deploy.md §"目录结构" deploy/marznode/ + AC-D.2.*
#   - deploy/install/install.sh (D.1) — base patterns + lib/* helpers
#   - deploy/cloudflare/install-tunnel.sh (D.4) — --dry-run convention
#
# Pipeline (8 steps, idempotent — sentinels under
# /opt/aegis-marznode/.install-step-N.done):
#   1. Dependency detection (docker, docker compose v2, curl, openssl)
#   2. OS preflight (reuses D.1 lib/detect.sh detect_os)
#   3. Hardware preflight (1 GiB RAM floor, nproc>=1, df>=5GiB)
#   4. Argument resolution (interactive vs --non-interactive)
#   5. Cert acquisition (--cert-mode bootstrap|file)
#   6. Render /opt/aegis-marznode/.env from --env-vars
#   7. docker compose up -d (deploy/marznode/docker-compose.yml)
#   8. Wait for gRPC listener + emit summary
#
# Exit codes (consistent with D.1 + D.4):
#   0 — success
#   1 — dependency missing
#   2 — configuration invalid
#   3 — gRPC health timeout
#   4 — port occupied / disk floor breach
#   5 — cert acquisition failed
#
# License: AGPL-3.0-or-later. Aegis Panel is a hard fork of Marzneshin
# (https://github.com/marzneshin/marzneshin). See NOTICE.md.
# =============================================================================

set -euo pipefail
IFS=$'\n\t'

SCRIPT_NAME="$(basename "$0")"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Reuse D.1 lib helpers — single source of truth for OS / dependency / port
# checks. The functions defined here MUST be additive; do not redefine names
# already exported by these libs.
# shellcheck source=../install/lib/detect.sh
. "${REPO_ROOT}/install/lib/detect.sh"

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
AEGIS_NODE_PREFIX="${AEGIS_NODE_PREFIX:-/opt/aegis-marznode}"
AEGIS_VERSION="${AEGIS_VERSION:-v0.2.0}"

CONTROL_PLANE=""
GRPC_PORT="${GRPC_PORT:-62051}"
NODE_NAME=""
CERT_MODE=""
CERT_FILE=""
CERT_TOKEN=""
NON_INTERACTIVE=0
DRY_RUN=0
FORCE=0

# Hardware floors specific to marznode (lighter than control plane).
MIN_MEMORY_MB=1024
MIN_DISK_GB=5

usage() {
  cat <<'EOF'
Aegis Panel — standalone marznode installer (D.2)

Usage:
  install-node.sh [flags]

Provisions a data-plane-only VPS. The control plane runs elsewhere; this
script only stands up the marznode container that talks gRPC back to the
panel. After install, register the node in the panel UI under Nodes.

Required flags (or interactive prompts):
  --control-plane <fqdn|ip>   Hostname or IP of the marzneshin control plane.
  --node-name <slug>          Identifier the panel will use for this node.
  --cert-mode {bootstrap|file}
                              bootstrap : fetch cert from control plane via a
                                          one-time --cert-token (issued by
                                          the panel under Nodes > New).
                              file      : use an existing PEM at --cert-file
                                          (already on disk; e.g. provisioned
                                          via Ansible Vault).

Conditional flags:
  --cert-token <token>        Required when --cert-mode=bootstrap.
  --cert-file <path>          Required when --cert-mode=file.

Optional flags:
  --grpc-port <int>           Local gRPC listener port. Default: 62051
                              (matches deploy/install/.env MARZNODE_GRPC_PORT).
  --version V                 Override AEGIS_VERSION tag. Default: v0.2.0.
  --prefix PATH               Install root. Default: /opt/aegis-marznode.
  --non-interactive           Take values from flags / env, never prompt.
  --dry-run                   Validate flags + render only. No docker compose,
                              no filesystem mutation outside a temp render.
  --force                     Bypass tier-2 OS warning and continue.
  --help, -h                  Show this help and exit 0.

Exit codes:
  0 success | 1 dep missing | 2 config invalid | 3 health timeout
  4 port busy / disk floor | 5 cert acquisition failed

Examples:
  # Bootstrap path (most common — node fetches cert from panel):
  sudo ./install-node.sh \
       --control-plane panel.example.com \
       --node-name node-tokyo-01 \
       --cert-mode bootstrap \
       --cert-token tok_abcdef0123456789

  # File path (cert pre-provisioned by Ansible Vault on /opt/aegis-marznode/):
  sudo ./install-node.sh \
       --control-plane panel.example.com \
       --node-name node-singapore-01 \
       --cert-mode file \
       --cert-file ./marznode-cert.pem

  # Dry-run (validate flags without touching docker):
  sudo ./install-node.sh --control-plane panel.example.com \
       --node-name preview --cert-mode bootstrap --cert-token x --dry-run

After success, open the panel at https://<control-plane>/nodes and click
"Add node". The node identifier you enter must match --node-name.
EOF
}

log()   { printf '[%s] %s\n' "$SCRIPT_NAME" "$*" >&2; }
warn()  { printf '[%s] WARN: %s\n' "$SCRIPT_NAME" "$*" >&2; }
fatal() {
  local code="${1:-1}"; shift || true
  printf '[%s] FATAL: %s\n' "$SCRIPT_NAME" "$*" >&2
  exit "${code}"
}

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
parse_args() {
  while (( $# > 0 )); do
    case "$1" in
      --help|-h)           usage; exit 0 ;;
      --control-plane)     CONTROL_PLANE="${2:-}"; shift ;;
      --grpc-port)         GRPC_PORT="${2:-}"; shift ;;
      --node-name)         NODE_NAME="${2:-}"; shift ;;
      --cert-mode)         CERT_MODE="${2:-}"; shift ;;
      --cert-file)         CERT_FILE="${2:-}"; shift ;;
      --cert-token)        CERT_TOKEN="${2:-}"; shift ;;
      --version)           AEGIS_VERSION="${2:-}"; shift ;;
      --prefix)            AEGIS_NODE_PREFIX="${2:-}"; shift ;;
      --non-interactive)   NON_INTERACTIVE=1 ;;
      --dry-run)           DRY_RUN=1 ;;
      --force)             FORCE=1 ;;
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
# Sentinel helpers (mirror D.1 install.sh)
# ---------------------------------------------------------------------------
sentinel_path() { printf '%s/.install-step-%s.done' "${AEGIS_NODE_PREFIX}" "$1"; }

step_done() {
  local n="$1"
  [[ -f "$(sentinel_path "${n}")" ]]
}

mark_step_done() {
  local n="$1"
  if (( DRY_RUN )); then return 0; fi
  mkdir -p "${AEGIS_NODE_PREFIX}"
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

  if (( missing )); then
    fatal 1 "one or more dependencies missing — see hints above"
  fi
  mark_step_done 1
}

# ---------------------------------------------------------------------------
# Step 2 — OS preflight (reuses D.1 detect_os tier classification).
# ---------------------------------------------------------------------------
step_2_os_preflight() {
  if step_done 2; then log "step 2 (os): already done, skipping"; return 0; fi
  log "step 2: OS preflight"

  set +e
  detect_os
  local os_tier=$?
  set -e

  case "${os_tier}" in
    0) log "OS tier-1 supported: ${AEGIS_OS_ID} ${AEGIS_OS_VERSION_ID}" ;;
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
    *) fatal 2 "could not classify OS" ;;
  esac
  mark_step_done 2
}

# ---------------------------------------------------------------------------
# Step 3 — hardware preflight (marznode-specific floors).
#
# Marznode is lighter than the control plane (no DB, no UI), so we floor at
# 1 GiB RAM / 1 vCPU / 5 GiB disk vs. D.1's 2 GiB / 2 vCPU / 20 GiB.
# ---------------------------------------------------------------------------
step_3_hardware_preflight() {
  if step_done 3; then log "step 3 (hardware): already done, skipping"; return 0; fi
  log "step 3: hardware preflight"

  local mem_mb cpu_count disk_gb
  mem_mb="$(detect_memory_mb)"
  cpu_count="$(detect_cpu_count)"
  disk_gb="$(detect_disk_free_gb /var/lib)"

  log "memory=${mem_mb}MiB cpu=${cpu_count} disk_free(/var/lib)=${disk_gb}GiB"

  if (( mem_mb < MIN_MEMORY_MB )); then
    fatal 4 "memory ${mem_mb}MiB < ${MIN_MEMORY_MB}MiB floor for marznode"
  fi
  if (( cpu_count < 1 )); then
    fatal 4 "cpu_count ${cpu_count} < 1 — marznode requires at least 1 vCPU"
  fi
  if [[ -n "${disk_gb}" ]] && (( disk_gb < MIN_DISK_GB )); then
    fatal 4 "free disk ${disk_gb}GiB < ${MIN_DISK_GB}GiB floor on /var/lib"
  fi
  mark_step_done 3
}

# ---------------------------------------------------------------------------
# Step 4 — argument resolution + validation.
# ---------------------------------------------------------------------------
prompt_if_empty() {
  local var="$1" prompt="$2"
  local current="${!var:-}"
  if [[ -n "${current}" ]]; then return 0; fi
  if (( NON_INTERACTIVE )); then return 0; fi
  read -r -p "${prompt}: " current </dev/tty
  printf -v "${var}" '%s' "${current}"
}

step_4_collect_inputs() {
  if step_done 4; then log "step 4 (inputs): already done, skipping"; return 0; fi
  log "step 4: collect inputs"

  prompt_if_empty CONTROL_PLANE "Control plane (panel) FQDN or IP"
  prompt_if_empty NODE_NAME     "Node name (panel identifier)"
  prompt_if_empty CERT_MODE     "Cert mode (bootstrap|file)"

  if [[ -z "${CONTROL_PLANE}" ]]; then fatal 2 "--control-plane is required"; fi
  if [[ -z "${NODE_NAME}"     ]]; then fatal 2 "--node-name is required"; fi
  if [[ -z "${CERT_MODE}"     ]]; then fatal 2 "--cert-mode is required"; fi

  if [[ "${CONTROL_PLANE}" =~ [[:space:]] ]]; then
    fatal 2 "--control-plane contains whitespace: ${CONTROL_PLANE}"
  fi
  if [[ ! "${NODE_NAME}" =~ ^[A-Za-z0-9._-]+$ ]]; then
    fatal 2 "--node-name must be slug-shaped (alnum + . _ -); got: ${NODE_NAME}"
  fi
  case "${GRPC_PORT}" in
    ''|*[!0-9]*) fatal 2 "--grpc-port must be integer; got: ${GRPC_PORT}" ;;
    *)
      if (( GRPC_PORT < 1 || GRPC_PORT > 65535 )); then
        fatal 2 "--grpc-port out of range 1-65535: ${GRPC_PORT}"
      fi
      ;;
  esac
  case "${CERT_MODE}" in
    bootstrap)
      prompt_if_empty CERT_TOKEN "One-time bootstrap token (from panel Nodes > New)"
      if [[ -z "${CERT_TOKEN}" ]]; then
        fatal 2 "--cert-token is required when --cert-mode=bootstrap"
      fi
      ;;
    file)
      prompt_if_empty CERT_FILE "Path to existing cert PEM"
      if [[ -z "${CERT_FILE}" ]]; then
        fatal 2 "--cert-file is required when --cert-mode=file"
      fi
      if [[ ! -r "${CERT_FILE}" ]]; then
        fatal 2 "--cert-file not readable: ${CERT_FILE}"
      fi
      ;;
    *)
      fatal 2 "--cert-mode must be bootstrap or file (got ${CERT_MODE})"
      ;;
  esac

  if ! check_port_free "${GRPC_PORT}"; then
    fatal 4 "gRPC port ${GRPC_PORT} occupied (pid=${AEGIS_PORT_OWNER_PID:-unknown}) — free it or pass --grpc-port"
  fi
  mark_step_done 4
}

# ---------------------------------------------------------------------------
# Step 5 — cert acquisition.
#
# bootstrap: HTTPS GET to control plane's bootstrap endpoint with the
#            one-time token. The endpoint is a thin v0.2 contract that the
#            control plane MUST expose at /api/nodes/bootstrap?token=<x>;
#            it returns the PEM cert body. If you operate a panel that
#            hasn't enabled this route yet, fall back to --cert-mode file
#            with a cert manually downloaded via panel UI.
# file:      copy the user-provided cert into the install prefix.
# ---------------------------------------------------------------------------
step_5_acquire_cert() {
  if step_done 5; then log "step 5 (cert): already done, skipping"; return 0; fi
  log "step 5: acquire marznode cert (mode=${CERT_MODE})"

  local target_cert="${AEGIS_NODE_PREFIX}/marznode-cert.pem"

  if (( DRY_RUN )); then
    log "dry-run: would write cert to ${target_cert}"
    mark_step_done 5
    return 0
  fi

  mkdir -p "${AEGIS_NODE_PREFIX}"
  chmod 700 "${AEGIS_NODE_PREFIX}"

  case "${CERT_MODE}" in
    bootstrap)
      local url="https://${CONTROL_PLANE}/api/nodes/bootstrap?token=${CERT_TOKEN}"
      log "fetching cert via bootstrap token from ${CONTROL_PLANE}"
      if ! curl -fsS --max-time 15 "${url}" -o "${target_cert}.tmp"; then
        rm -f "${target_cert}.tmp"
        fatal 5 "bootstrap GET ${url} failed; verify --cert-token validity (5-min TTL) and control-plane reachability"
      fi
      # Sanity: PEM must contain a BEGIN line.
      if ! grep -q 'BEGIN CERTIFICATE' "${target_cert}.tmp"; then
        rm -f "${target_cert}.tmp"
        fatal 5 "bootstrap response is not a PEM cert; check that the token is valid and unconsumed"
      fi
      mv -f "${target_cert}.tmp" "${target_cert}"
      ;;
    file)
      cp -f "${CERT_FILE}" "${target_cert}"
      if ! grep -q 'BEGIN CERTIFICATE' "${target_cert}"; then
        fatal 5 "--cert-file ${CERT_FILE} does not look like a PEM cert"
      fi
      ;;
  esac
  chmod 600 "${target_cert}"
  log "cert written to ${target_cert} (mode 600)"
  mark_step_done 5
}

# ---------------------------------------------------------------------------
# Step 6 — render /opt/aegis-marznode/.env.
#
# We don't need the full panel template — just the four vars compose
# substitutes. Pure bash heredoc keeps this dependency-free.
# ---------------------------------------------------------------------------
step_6_render_env() {
  if step_done 6; then log "step 6 (render): already done, skipping"; return 0; fi
  log "step 6: render .env"

  local target="${AEGIS_NODE_PREFIX}/.env"
  if (( DRY_RUN )); then
    target="$(mktemp)"
    log "dry-run: rendering to ${target}"
  else
    mkdir -p "${AEGIS_NODE_PREFIX}"
    chmod 700 "${AEGIS_NODE_PREFIX}"
  fi

  local tmp
  tmp="$(mktemp "${target}.XXXXXX")"
  cat >"${tmp}" <<EOF
# Aegis Panel marznode (data-plane) — generated by install-node.sh.
# DO NOT commit. Mode 600.
AEGIS_VERSION=${AEGIS_VERSION}
CONTROL_PLANE_URL=${CONTROL_PLANE}
GRPC_PORT=${GRPC_PORT}
NODE_NAME=${NODE_NAME}
CERT_PATH=${AEGIS_NODE_PREFIX}/marznode-cert.pem
EOF
  chmod 600 "${tmp}"
  mv -f "${tmp}" "${target}"
  log ".env rendered: ${target}"
  mark_step_done 6
}

# ---------------------------------------------------------------------------
# Step 7 — docker compose up -d.
# ---------------------------------------------------------------------------
step_7_compose_up() {
  if step_done 7; then log "step 7 (compose up): already done, skipping"; return 0; fi
  local compose_file="${SCRIPT_DIR}/docker-compose.yml"
  log "step 7: docker compose up -d (${compose_file})"

  if [[ ! -r "${compose_file}" ]]; then
    fatal 2 "compose file missing: ${compose_file}"
  fi
  if (( DRY_RUN )); then
    log "dry-run: would run: docker compose -f ${compose_file} --env-file ${AEGIS_NODE_PREFIX}/.env up -d"
    mark_step_done 7
    return 0
  fi
  docker compose -f "${compose_file}" --env-file "${AEGIS_NODE_PREFIX}/.env" up -d
  mark_step_done 7
}

# ---------------------------------------------------------------------------
# Step 8 — wait for gRPC listener + emit summary.
#
# We don't run grpc_health_probe to avoid pulling in an extra binary; instead
# we poll the TCP socket. Once the listener is bound, the panel side will
# initiate the gRPC handshake on its own (verified via panel Nodes UI).
# ---------------------------------------------------------------------------
wait_for_grpc_listener() {
  local port="$1"
  local timeout="${2:-60}"
  local interval=2
  local elapsed=0

  log "waiting for gRPC listener on 127.0.0.1:${port} (timeout=${timeout}s)"
  while (( elapsed < timeout )); do
    # bash builtin /dev/tcp; works without nc / ncat.
    if (echo >"/dev/tcp/127.0.0.1/${port}") >/dev/null 2>&1; then
      log "marznode listening after ${elapsed}s"
      return 0
    fi
    sleep "${interval}"
    elapsed=$(( elapsed + interval ))
  done
  return 3
}

step_8_health_and_summary() {
  if step_done 8; then log "step 8 (health): already done, skipping"; return 0; fi
  log "step 8: gRPC listener wait + summary"

  if (( DRY_RUN )); then
    log "dry-run: skipping listener wait"
  else
    if ! wait_for_grpc_listener "${GRPC_PORT}" 60; then
      log "FATAL: marznode did not bind ${GRPC_PORT} within 60s"
      docker compose -f "${SCRIPT_DIR}/docker-compose.yml" \
        --env-file "${AEGIS_NODE_PREFIX}/.env" \
        logs --tail=50 marznode >&2 2>&1 || true
      fatal 3 "gRPC listener wait failed"
    fi
  fi

  cat >&2 <<EOF

================================================================
Aegis Panel marznode install complete.

  Node name        : ${NODE_NAME}
  Control plane    : ${CONTROL_PLANE}
  gRPC endpoint    : 0.0.0.0:${GRPC_PORT}
  Cert path        : ${AEGIS_NODE_PREFIX}/marznode-cert.pem
  Install prefix   : ${AEGIS_NODE_PREFIX}

Next steps:

  1) Firewall (open gRPC only to the control plane source IP):
       sudo ufw allow 22/tcp
       sudo ufw allow from <CONTROL_PLANE_IP> to any port ${GRPC_PORT} proto tcp
       sudo ufw enable

  2) Add this node in the panel UI:
       https://${CONTROL_PLANE}/nodes  -> "Add node"
       Name        : ${NODE_NAME}
       Address     : <this VPS public IP>
       Port        : ${GRPC_PORT}

  3) Verify online status:
       Panel dashboard should show the node green within 30s of adding it.
================================================================
EOF
  mark_step_done 8
}

# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
main() {
  parse_args "$@"
  log "Aegis marznode installer ${AEGIS_VERSION} starting (prefix=${AEGIS_NODE_PREFIX}, dry_run=${DRY_RUN})"

  step_1_dependencies
  step_2_os_preflight
  step_3_hardware_preflight
  step_4_collect_inputs
  step_5_acquire_cert
  step_6_render_env
  step_7_compose_up
  step_8_health_and_summary

  log "done."
}

main "$@"
