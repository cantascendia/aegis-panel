#!/usr/bin/env bash
# deploy/install/lib/detect.sh — OS / hardware / provider preflight helpers.
#
# This file is sourced by install.sh. Functions defined here MUST NOT exit
# the parent shell directly — they return non-zero and let the caller decide.
# stderr is the human-readable channel; stdout is reserved for KV output.
#
# Refs: SPEC-deploy.md §"install.sh 职责(D.1)" step 2 (preflight) and
# AC-D.1.7 (Debian 12 path) / AC-D.1.8 (CentOS reject) / AC-D.1.12 (脏 ASN).

set -euo pipefail
IFS=$'\n\t'

# ---------------------------------------------------------------------------
# detect_os — populate AEGIS_OS_ID and AEGIS_OS_VERSION_ID from /etc/os-release.
#
# Returns 0 on tier-1 distros (ubuntu 22.04/24.04, debian 12), 2 on tier-2
# (debian 11, ubuntu 20.04 — accepted with warning), 3 on hard-rejected
# (rhel/centos/alma/rocky/fedora). The caller decides whether --force can
# downgrade tier-2 to tier-1.
# ---------------------------------------------------------------------------
detect_os() {
  if [[ ! -r /etc/os-release ]]; then
    echo "[detect] /etc/os-release missing — cannot detect distro" >&2
    AEGIS_OS_ID="unknown"
    AEGIS_OS_VERSION_ID="unknown"
    return 3
  fi
  # shellcheck disable=SC1091
  . /etc/os-release
  AEGIS_OS_ID="${ID:-unknown}"
  AEGIS_OS_VERSION_ID="${VERSION_ID:-unknown}"
  export AEGIS_OS_ID AEGIS_OS_VERSION_ID

  case "${AEGIS_OS_ID}" in
    ubuntu)
      case "${AEGIS_OS_VERSION_ID}" in
        22.04|24.04) return 0 ;;
        20.04)       return 2 ;;
        *)           return 2 ;;
      esac
      ;;
    debian)
      case "${AEGIS_OS_VERSION_ID}" in
        12) return 0 ;;
        11) return 2 ;;
        *)  return 2 ;;
      esac
      ;;
    centos|rhel|almalinux|rocky|fedora|amzn)
      return 3
      ;;
    *)
      return 2
      ;;
  esac
}

# ---------------------------------------------------------------------------
# detect_memory_mb — print total RAM in MiB to stdout.
# ---------------------------------------------------------------------------
detect_memory_mb() {
  if [[ -r /proc/meminfo ]]; then
    awk '/^MemTotal:/ { printf "%d\n", $2/1024; exit }' /proc/meminfo
  else
    echo "0"
  fi
}

# ---------------------------------------------------------------------------
# detect_cpu_count — print logical CPU count.
# ---------------------------------------------------------------------------
detect_cpu_count() {
  if command -v nproc >/dev/null 2>&1; then
    nproc
  else
    grep -c '^processor' /proc/cpuinfo 2>/dev/null || echo "1"
  fi
}

# ---------------------------------------------------------------------------
# detect_disk_free_gb PATH — print free space at PATH in GiB.
# ---------------------------------------------------------------------------
detect_disk_free_gb() {
  local path="${1:-/}"
  if [[ ! -e "${path}" ]]; then
    path="/"
  fi
  df -BG "${path}" 2>/dev/null | awk 'NR==2 { gsub(/G/,"",$4); print $4; exit }'
}

# ---------------------------------------------------------------------------
# preflight_hardware — enforces SPEC §step 2 hardware floor.
#
# Sets AEGIS_FORCE_SQLITE=1 if RAM < 2GB (caller must respect this and switch
# --db postgres to --db sqlite). Returns 4 on disk floor breach (hard fail).
# ---------------------------------------------------------------------------
preflight_hardware() {
  local mem_mb cpu_count disk_gb
  mem_mb="$(detect_memory_mb)"
  cpu_count="$(detect_cpu_count)"
  disk_gb="$(detect_disk_free_gb /var/lib)"

  echo "[detect] memory=${mem_mb}MiB cpu=${cpu_count} disk_free(/var/lib)=${disk_gb}GiB" >&2

  if (( mem_mb < 2048 )); then
    echo "[detect] WARN: memory < 2GiB — postgres path is unsupported. Forcing --db sqlite." >&2
    export AEGIS_FORCE_SQLITE=1
  fi

  if (( cpu_count < 2 )); then
    echo "[detect] WARN: cpu_count < 2 — performance will be poor under load." >&2
  fi

  if [[ -n "${disk_gb}" ]] && (( disk_gb < 20 )); then
    echo "[detect] FATAL: free disk on /var/lib < 20GiB. Aborting." >&2
    return 4
  fi

  return 0
}

# ---------------------------------------------------------------------------
# detect_provider_asn — best-effort ASN lookup via ifconfig.co.
#
# Sets AEGIS_PROVIDER_ASN. Empty string on lookup failure (do NOT block on
# network errors — the install must work in air-gapped reruns). The caller
# decides whether to warn based on a blocklist file at
# deploy/install/lib/asn-blocklist.txt (TODO: ship in a follow-up; for now
# the function is a no-op marker so the install summary records "unchecked").
# ---------------------------------------------------------------------------
detect_provider_asn() {
  AEGIS_PROVIDER_ASN=""
  if ! command -v curl >/dev/null 2>&1; then
    echo "[detect] curl missing — skipping ASN probe" >&2
    export AEGIS_PROVIDER_ASN
    return 0
  fi
  AEGIS_PROVIDER_ASN="$(curl -fsS --max-time 5 https://ifconfig.co/asn 2>/dev/null || true)"
  export AEGIS_PROVIDER_ASN
  echo "[detect] provider_asn=${AEGIS_PROVIDER_ASN:-<unknown>}" >&2
}

# ---------------------------------------------------------------------------
# check_dep CMD HINT — verify CMD is on PATH; on miss, print install hint and
# return 1 so the caller can aggregate misses before exiting.
# ---------------------------------------------------------------------------
check_dep() {
  local cmd="$1" hint="${2:-}"
  if command -v "${cmd}" >/dev/null 2>&1; then
    return 0
  fi
  echo "[detect] missing dependency: ${cmd}" >&2
  if [[ -n "${hint}" ]]; then
    echo "         install with: ${hint}" >&2
  fi
  return 1
}

# ---------------------------------------------------------------------------
# check_docker_compose_v2 — v2 plugin; v1 standalone is rejected.
# ---------------------------------------------------------------------------
check_docker_compose_v2() {
  if ! docker compose version >/dev/null 2>&1; then
    echo "[detect] missing 'docker compose' v2 plugin (standalone docker-compose v1 is unsupported)" >&2
    echo "         install with: apt-get install docker-compose-plugin" >&2
    return 1
  fi
  return 0
}

# ---------------------------------------------------------------------------
# check_port_free PORT — true if no listener on PORT (loopback or wildcard).
# Sets AEGIS_PORT_OWNER_PID to the offending PID if available.
# ---------------------------------------------------------------------------
check_port_free() {
  local port="$1"
  AEGIS_PORT_OWNER_PID=""
  if command -v ss >/dev/null 2>&1; then
    if ss -ltnp "( sport = :${port} )" 2>/dev/null | tail -n +2 | grep -q .; then
      AEGIS_PORT_OWNER_PID="$(ss -ltnp "( sport = :${port} )" 2>/dev/null | tail -n +2 | grep -oP 'pid=\K[0-9]+' | head -n1 || true)"
      export AEGIS_PORT_OWNER_PID
      return 1
    fi
  elif command -v lsof >/dev/null 2>&1; then
    if lsof -iTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1; then
      AEGIS_PORT_OWNER_PID="$(lsof -iTCP:"${port}" -sTCP:LISTEN -t 2>/dev/null | head -n1 || true)"
      export AEGIS_PORT_OWNER_PID
      return 1
    fi
  fi
  export AEGIS_PORT_OWNER_PID
  return 0
}
