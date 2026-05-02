#!/usr/bin/env bash
# scripts/aegis-upgrade.sh — VPS-side panel image upgrade.
#
# Usage: aegis-upgrade vX.Y.Z
#
# Rewrites AEGIS_VERSION in /opt/aegis/.env, pulls the new panel image from
# ghcr.io/cantascendia/aegis-panel, and rolls panel only (postgres / redis /
# marznode untouched). Volume mounts under /opt/aegis/data/ are host paths,
# so DB / xray_config / Reality keypair survive the swap.
#
# Rollback: re-run with previous version tag.
#
# Refs: docs/ai-cto/RUNBOOK-fork-image-cutover.md

set -euo pipefail
IFS=$'\n\t'

NEW_VERSION="${1:?usage: aegis-upgrade vX.Y.Z}"
ENV_FILE="${AEGIS_ENV_FILE:-/opt/aegis/.env}"

# Compose dir + variant resolution (L-040, wave-9 cutover fix).
#
# Sourced from scripts/lib/path-detect.sh — SSOT shared with install.sh
# so a fix in one place propagates to both. The lib handles:
#   * multi-candidate scan (/opt/aegis-src/deploy/compose first, legacy
#     /opt/aegis/compose second) with fail-loud (exit 2) when none match
#   * variant from .env's SQLALCHEMY_DATABASE_URL (sqlite vs postgres)
#     so installer-managed dirs holding BOTH yml files don't silently
#     downgrade Postgres installs (codex P1)
#   * operator overrides AEGIS_COMPOSE_DIR / AEGIS_COMPOSE_VARIANT,
#     including typo-detection on AEGIS_COMPOSE_DIR
#
# Three layouts source the lib:
#   1. in-tree:        /opt/aegis-src/scripts/aegis-upgrade.sh →
#                      sibling /opt/aegis-src/scripts/lib/path-detect.sh
#   2. /usr/local/bin: install.sh co-installs the lib at
#                      /usr/local/lib/aegis/path-detect.sh (REPO_ROOT-independent;
#                      codex P2 fix)
#   3. legacy/dev:     fallback to /opt/aegis-src/scripts/lib
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_path_detect_lib=""
# AEGIS_PATH_DETECT_LIB env var (test-only) lets harnesses point at the
# repo's lib without copying it next to a stub.
for libdir in \
    "${AEGIS_PATH_DETECT_LIB_DIR:-}" \
    "${SCRIPT_DIR}/lib" \
    "/usr/local/lib/aegis" \
    "/opt/aegis-src/scripts/lib"; do
  [[ -z "${libdir}" ]] && continue
  if [[ -f "${libdir}/path-detect.sh" ]]; then
    _path_detect_lib="${libdir}/path-detect.sh"
    break
  fi
done
if [[ -z "${_path_detect_lib}" ]]; then
  echo "[upgrade] FATAL: path-detect.sh not found (looked in ${SCRIPT_DIR}/lib, /usr/local/lib/aegis, /opt/aegis-src/scripts/lib)" >&2
  exit 2
fi
# shellcheck source=lib/path-detect.sh
. "${_path_detect_lib}"

COMPOSE_DIR=""
COMPOSE_FILE=""
COMPOSE_VARIANT=""
aegis_resolve_compose "${ENV_FILE}" "[upgrade]" || exit 2

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "[upgrade] FATAL: ${ENV_FILE} not found" >&2
  exit 2
fi

# Sanity: NEW_VERSION must look like vX.Y.Z or "latest" or "nightly".
case "${NEW_VERSION}" in
  v[0-9]*.[0-9]*.[0-9]*|latest|nightly) ;;
  *)
    echo "[upgrade] FATAL: version '${NEW_VERSION}' must be vX.Y.Z, latest, or nightly" >&2
    exit 2
    ;;
esac

CURRENT_VERSION="$(awk -F= '/^AEGIS_VERSION=/ { print $2; exit }' "${ENV_FILE}")"
echo "[upgrade] current=${CURRENT_VERSION:-<unset>} target=${NEW_VERSION}"
echo "[upgrade] compose=${COMPOSE_FILE}"

# Backup .env (single point of truth — JWT secret, DB password, paths).
BACKUP="${ENV_FILE}.bak.$(date +%Y%m%d-%H%M%S)"
cp "${ENV_FILE}" "${BACKUP}"
echo "[upgrade] env backup → ${BACKUP}"

# Idempotent rewrite. Use a temp file + mv so a crash mid-write doesn't truncate.
tmp="$(mktemp)"
awk -v v="${NEW_VERSION}" '
  /^AEGIS_VERSION=/ { print "AEGIS_VERSION=" v; next }
  { print }
' "${ENV_FILE}" >"${tmp}"
chmod 600 "${tmp}"
mv -f "${tmp}" "${ENV_FILE}"

# Pull only the panel image — marznode / postgres / redis stay put.
# `--env-file` is required: compose interpolates `${AEGIS_VERSION}` from the
# env file at parse time. If the operator's compose file lives outside
# /opt/aegis/.env's directory (the common install layout), compose falls
# back to `${AEGIS_VERSION:-latest}` and we'd silently pull `:latest`
# instead of the requested tag. Verified during 2026-05-01 v0.3.5 cutover.
echo "[upgrade] docker compose pull panel"
docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" pull panel

# Roll panel. Compose recreates the container with the new image; volume mounts
# (host paths under /opt/aegis/data/) are preserved across the swap.
echo "[upgrade] docker compose up -d panel"
docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d panel

# Give Alembic a moment, then dump status.
sleep 5
docker compose -f "${COMPOSE_FILE}" ps

PANEL_PORT="$(awk -F= '/^PANEL_PORT=/ { print $2; exit }' "${ENV_FILE}")"
PANEL_PORT="${PANEL_PORT:-8443}"

cat <<EOF

[upgrade] panel rolled to ${NEW_VERSION}.
[verify] Run these to confirm:
  curl -fsS http://127.0.0.1:${PANEL_PORT}/openapi.json | head -c 100
  docker compose -f ${COMPOSE_FILE} logs --tail=50 panel
[rollback] aegis-upgrade ${CURRENT_VERSION:-v0.2.0}
EOF
