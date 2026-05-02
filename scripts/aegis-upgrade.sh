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

# Compose dir resolution (L-040, wave-9 cutover fix).
#
# install.sh (deploy/install/install.sh L405-409) runs compose from the
# cloned repo at ${REPO_ROOT}/deploy/compose/, where REPO_ROOT defaults
# to /opt/aegis-src/ on installer-managed VPS. Earlier versions of this
# script hardcoded /opt/aegis/compose/, which never exists on a fresh
# install — wave-9 v0.4.0→v0.4.1 production cutover hit
#   "[upgrade] FATAL: no compose file found under /opt/aegis/compose"
# and forced manual fallback. We now scan ordered candidates and
# fail-loud (exit 2) when none match.
#
# Operator override: set AEGIS_COMPOSE_DIR=/path/to/compose to skip
# autodetect. The override path is checked first; if it has no
# docker-compose*.yml inside, we still fail-loud rather than silently
# trying the next candidate (so a typo'd override surfaces immediately).
#
# SSOT cleanup (single shared path-detect lib for install.sh +
# aegis-upgrade.sh) is tracked as a follow-up; this PR is the minimal
# scope fix.
declare -a COMPOSE_CANDIDATES
if [[ -n "${AEGIS_COMPOSE_DIR:-}" ]]; then
  COMPOSE_CANDIDATES=("${AEGIS_COMPOSE_DIR}")
else
  COMPOSE_CANDIDATES=(
    "/opt/aegis-src/deploy/compose"   # installer-managed (install.sh default)
    "/opt/aegis/compose"              # legacy / pre-PR layout
  )
fi

# Compose variant (sqlite vs prod) MUST be derived from the install state
# (.env's SQLALCHEMY_DATABASE_URL), not from "first matching file" — the
# installer-managed compose dir contains BOTH variants on disk, so a
# file-presence-first scan would silently downgrade Postgres installs to
# SQLite topology on upgrade. Codex cross-review P1, 2026-05-02.
#
# DB_KIND_DETECTED ∈ {sqlite, prod}. If the .env has no DATABASE_URL we
# stay strict and fail-loud rather than guess.
COMPOSE_VARIANT=""
if [[ -f "${ENV_FILE}" ]]; then
  DB_URL_LINE="$(awk -F= '/^SQLALCHEMY_DATABASE_URL=/ { sub(/^SQLALCHEMY_DATABASE_URL=/, ""); print; exit }' "${ENV_FILE}" || true)"
  # Match the SQLAlchemy URL scheme prefix. SQLAlchemy permits dialect
  # plus driver via "+", e.g. `postgresql+psycopg://`, `sqlite+pysqlite:`,
  # so we accept both `<scheme>:` and `<scheme>+<driver>:` forms.
  case "${DB_URL_LINE}" in
    sqlite:*|sqlite+*)         COMPOSE_VARIANT="sqlite" ;;
    postgresql:*|postgresql+*) COMPOSE_VARIANT="prod"   ;;
    postgres:*|postgres+*)     COMPOSE_VARIANT="prod"   ;;
    *) ;;  # unknown / empty → resolved below
  esac
fi

# Operator override: if AEGIS_COMPOSE_VARIANT is set, it wins over
# autodetect (lets ops force a specific compose during recovery).
if [[ -n "${AEGIS_COMPOSE_VARIANT:-}" ]]; then
  COMPOSE_VARIANT="${AEGIS_COMPOSE_VARIANT}"
fi

case "${COMPOSE_VARIANT}" in
  sqlite|prod|"") ;;
  *)
    echo "[upgrade] FATAL: AEGIS_COMPOSE_VARIANT='${COMPOSE_VARIANT}' must be 'sqlite' or 'prod'" >&2
    exit 2
    ;;
esac

COMPOSE_DIR=""
COMPOSE_FILE=""
for candidate in "${COMPOSE_CANDIDATES[@]}"; do
  sqlite_path="${candidate}/docker-compose.sqlite.yml"
  prod_path="${candidate}/docker-compose.prod.yml"
  case "${COMPOSE_VARIANT}" in
    sqlite)
      if [[ -f "${sqlite_path}" ]]; then
        COMPOSE_DIR="${candidate}"; COMPOSE_FILE="${sqlite_path}"; break
      fi
      ;;
    prod)
      if [[ -f "${prod_path}" ]]; then
        COMPOSE_DIR="${candidate}"; COMPOSE_FILE="${prod_path}"; break
      fi
      ;;
    "")
      # Variant unknown (.env missing or DATABASE_URL not recognized).
      # Pick whichever compose file exists; if BOTH exist we cannot
      # disambiguate safely → fail-loud below.
      if [[ -f "${sqlite_path}" && -f "${prod_path}" ]]; then
        echo "[upgrade] FATAL: both docker-compose.sqlite.yml and .prod.yml exist under" >&2
        echo "[upgrade]   ${candidate}" >&2
        echo "[upgrade] but ${ENV_FILE} has no SQLALCHEMY_DATABASE_URL we recognize." >&2
        echo "[upgrade] hint: set AEGIS_COMPOSE_VARIANT=sqlite|prod to disambiguate" >&2
        exit 2
      elif [[ -f "${sqlite_path}" ]]; then
        COMPOSE_DIR="${candidate}"; COMPOSE_FILE="${sqlite_path}"; break
      elif [[ -f "${prod_path}" ]]; then
        COMPOSE_DIR="${candidate}"; COMPOSE_FILE="${prod_path}"; break
      fi
      ;;
  esac
done

if [[ -z "${COMPOSE_FILE}" ]]; then
  echo "[upgrade] FATAL: no docker-compose*.yml found (variant='${COMPOSE_VARIANT:-auto}') under any of:" >&2
  for candidate in "${COMPOSE_CANDIDATES[@]}"; do
    echo "[upgrade]   - ${candidate}" >&2
  done
  echo "[upgrade] hint: set AEGIS_COMPOSE_DIR=/path/to/compose to override" >&2
  exit 2
fi

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
