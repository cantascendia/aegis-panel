#!/usr/bin/env bash
# deploy/install/lib/render.sh — .env template renderer.
#
# Sourced by install.sh. Replaces __TOKEN__ placeholders in the env template
# with values from the parent shell's exported variables. Intentionally does
# NOT use envsubst(1) — that pulls in gettext, which is missing on minimal
# Debian images, and we want to keep install.sh dependency-free past
# coreutils + docker.
#
# Refs: SPEC-deploy.md §"install.sh 职责(D.1)" step 5.

set -euo pipefail
IFS=$'\n\t'

# ---------------------------------------------------------------------------
# rand_urlsafe N — print N bytes of base64 URL-safe randomness (no padding).
# Used for DASHBOARD_PATH, XRAY_SUBSCRIPTION_PATH, secrets.
# ---------------------------------------------------------------------------
rand_urlsafe() {
  local bytes="${1:-12}"
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -base64 "${bytes}" | tr -d '\n=+/' | head -c "${bytes}"
    return 0
  fi
  # Fallback: /dev/urandom + base32 trim. Not as uniform but acceptable.
  head -c "$(( bytes * 2 ))" /dev/urandom | base64 | tr -d '\n=+/' | head -c "${bytes}"
}

# ---------------------------------------------------------------------------
# rand_secret N — print N bytes of base64 randomness for JWT / passwords.
# Default 64 bytes -> ~86 chars base64.
# ---------------------------------------------------------------------------
rand_secret() {
  local bytes="${1:-64}"
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -base64 "${bytes}" | tr -d '\n'
    return 0
  fi
  head -c "${bytes}" /dev/urandom | base64 | tr -d '\n'
}

# ---------------------------------------------------------------------------
# render_env_template SRC DST — substitute __TOKENS__ in SRC, write to DST.
#
# The variables consulted (env-exported by install.sh before calling this):
#   AEGIS_VERSION AEGIS_DOMAIN
#   PANEL_PORT MARZNODE_GRPC_PORT POSTGRES_PORT REDIS_PORT
#   POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD REDIS_PASSWORD
#   JWT_SECRET DASHBOARD_PATH XRAY_SUBSCRIPTION_PATH
#   ADMIN_USERNAME ADMIN_PASSWORD
#   DATABASE_URL CF_TUNNEL_ENABLED CF_TUNNEL_NAME
#
# Implementation: pure-bash read + token replace. Avoids sed escaping pain
# with passwords containing /, +, &, etc.
# ---------------------------------------------------------------------------
render_env_template() {
  local src="$1" dst="$2"
  if [[ ! -r "${src}" ]]; then
    echo "[render] template not readable: ${src}" >&2
    return 2
  fi

  # Map of token -> variable. Keep in sync with templates/env.tmpl.
  local -a tokens=(
    "__AEGIS_VERSION__"
    "__AEGIS_DOMAIN__"
    "__PANEL_PORT__"
    "__MARZNODE_GRPC_PORT__"
    "__POSTGRES_PORT__"
    "__POSTGRES_DB__"
    "__POSTGRES_USER__"
    "__POSTGRES_PASSWORD__"
    "__REDIS_PORT__"
    "__REDIS_PASSWORD__"
    "__JWT_SECRET__"
    "__DASHBOARD_PATH__"
    "__XRAY_SUBSCRIPTION_PATH__"
    "__ADMIN_USERNAME__"
    "__ADMIN_PASSWORD__"
    "__DATABASE_URL__"
    "__CF_TUNNEL_ENABLED__"
    "__CF_TUNNEL_NAME__"
  )
  local -a values=(
    "${AEGIS_VERSION:-v0.2.0}"
    "${AEGIS_DOMAIN:-localhost}"
    "${PANEL_PORT:-8443}"
    "${MARZNODE_GRPC_PORT:-62051}"
    "${POSTGRES_PORT:-5432}"
    "${POSTGRES_DB:-aegis}"
    "${POSTGRES_USER:-aegis}"
    "${POSTGRES_PASSWORD:-}"
    "${REDIS_PORT:-6379}"
    "${REDIS_PASSWORD:-}"
    "${JWT_SECRET:-}"
    "${DASHBOARD_PATH:-}"
    "${XRAY_SUBSCRIPTION_PATH:-}"
    "${ADMIN_USERNAME:-admin}"
    "${ADMIN_PASSWORD:-}"
    "${DATABASE_URL:-sqlite:////opt/aegis/data/panel/db.sqlite3}"
    "${CF_TUNNEL_ENABLED:-false}"
    "${CF_TUNNEL_NAME:-}"
  )

  # Read template once, run replacements in-memory, write atomically.
  local content
  content="$(cat "${src}")"
  local i token value
  for i in "${!tokens[@]}"; do
    token="${tokens[$i]}"
    value="${values[$i]}"
    # bash parameter expansion handles arbitrary chars in `value` safely as
    # long as we use the ${var//pattern/replacement} form with string (not
    # regex) semantics.
    content="${content//${token}/${value}}"
  done

  local tmp
  tmp="$(mktemp "${dst}.XXXXXX")"
  printf '%s\n' "${content}" >"${tmp}"
  chmod 600 "${tmp}"
  mv -f "${tmp}" "${dst}"
}

# ---------------------------------------------------------------------------
# validate_rendered_env PATH — quick spot-check the rendered env has no
# stray placeholders and respects AC-D.1.10 (compass 五件套 floor).
# Returns 2 on violation (matches install.sh exit code 2 = config invalid).
# ---------------------------------------------------------------------------
validate_rendered_env() {
  local path="$1"
  if [[ ! -r "${path}" ]]; then
    echo "[render] cannot validate: ${path} not readable" >&2
    return 2
  fi

  if grep -q '__[A-Z_]*__' "${path}"; then
    echo "[render] FATAL: rendered env still has __TOKEN__ placeholders:" >&2
    grep -n '__[A-Z_]*__' "${path}" >&2 || true
    return 2
  fi

  # AC-D.1.10 floor checks. We grep keyed lines so commented mentions don't
  # flag false positives.
  local v
  v="$(awk -F= '/^XRAY_POLICY_CONN_IDLE=/ { print $2; exit }' "${path}")"
  if [[ -z "${v}" || "${v}" -gt 180 ]]; then
    echo "[render] FATAL: XRAY_POLICY_CONN_IDLE missing or > 180 (compass §Vision+短 connIdle)" >&2
    return 2
  fi
  v="$(awk -F= '/^JWT_ACCESS_TOKEN_EXPIRE_MINUTES=/ { print $2; exit }' "${path}")"
  if [[ -z "${v}" || "${v}" -gt 60 ]]; then
    echo "[render] FATAL: JWT_ACCESS_TOKEN_EXPIRE_MINUTES > 60 (compass §管理面板加固)" >&2
    return 2
  fi
  v="$(awk -F= '/^PANEL_PORT=/ { print $2; exit }' "${path}")"
  case "${v}" in
    80|443|8080)
      echo "[render] FATAL: PANEL_PORT=${v} is a standard port (compass §非标准端口 forbids)" >&2
      return 2
      ;;
  esac
  v="$(awk -F= '/^REALITY_UTLS_FINGERPRINT=/ { print $2; exit }' "${path}")"
  case "${v}" in
    chrome|firefox|edge|safari|ios) ;;
    *)
      echo "[render] FATAL: REALITY_UTLS_FINGERPRINT=${v} not in {chrome,firefox,edge,safari,ios}" >&2
      return 2
      ;;
  esac
  v="$(awk -F= '/^REALITY_FLOW=/ { print $2; exit }' "${path}")"
  if [[ "${v}" != "xtls-rprx-vision" ]]; then
    echo "[render] FATAL: REALITY_FLOW must be xtls-rprx-vision (compass §Vision+短 connIdle)" >&2
    return 2
  fi

  # SNI defaults must not collide with the blocklist.
  local blocklist
  blocklist="$(awk -F= '/^REALITY_SNI_BLOCKLIST=/ { print $2; exit }' "${path}")"
  IFS=',' read -r -a banned <<< "${blocklist}"
  local key default_value
  for key in REALITY_SNI_DEFAULT_GLOBAL REALITY_SNI_DEFAULT_JP REALITY_SNI_DEFAULT_KR REALITY_SNI_DEFAULT_US; do
    default_value="$(awk -F= -v k="^${key}=" '$0 ~ k { print $2; exit }' "${path}")"
    for b in "${banned[@]:-}"; do
      if [[ -n "${b}" && "${default_value}" == "${b}" ]]; then
        echo "[render] FATAL: ${key}=${default_value} matches REALITY_SNI_BLOCKLIST" >&2
        return 2
      fi
    done
  done

  return 0
}
