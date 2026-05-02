#!/usr/bin/env bash
# scripts/lib/path-detect.sh — SSOT for aegis compose path + variant detection.
#
# install.sh + aegis-upgrade.sh both need to find the docker-compose dir
# and pick the variant (sqlite vs prod). Their layouts can diverge if
# install.sh changes — this lib unifies the logic so a fix in one place
# propagates to both, killing the L-040 class of bug at the root.
#
# Usage:
#   # shellcheck source=lib/path-detect.sh
#   source "${SCRIPT_DIR}/lib/path-detect.sh"
#   COMPOSE_DIR=""; COMPOSE_FILE=""; COMPOSE_VARIANT=""
#   aegis_resolve_compose ENV_FILE_PATH || exit 2
#   # On success, the three vars above are populated.
#
# Idempotent. No global side effects beyond setting the three OUT vars
# (COMPOSE_DIR, COMPOSE_FILE, COMPOSE_VARIANT) on success.
#
# Env inputs (operator overrides):
#   AEGIS_COMPOSE_DIR      — single candidate path; skips multi-scan.
#                            Typo'd override fail-loud (no silent fallthrough).
#   AEGIS_COMPOSE_VARIANT  — force "sqlite" | "prod" (overrides .env autodetect).
#   AEGIS_COMPOSE_CANDIDATES_OVERRIDE — bash array literal for tests; not
#                            for production use. If set, replaces the
#                            default candidate list. (Test-only.)
#
# Exit semantics: aegis_resolve_compose returns 0 on success, 2 on
# fail-loud (printing a FATAL message to stderr).
#
# Refs: L-040 (PR #191), this lib unifies install.sh + aegis-upgrade.sh.

# Default ordered candidates. install.sh installs to
# /opt/aegis-src/deploy/compose (canonical); /opt/aegis/compose was an
# older layout from PR #160 era. Order: canonical first, legacy second.
_aegis_default_candidates() {
  if [[ -n "${AEGIS_COMPOSE_CANDIDATES_OVERRIDE:-}" ]]; then
    # Test-only: caller supplies a colon-separated list.
    local IFS=':'
    # shellcheck disable=SC2206
    _AEGIS_CANDIDATES=( ${AEGIS_COMPOSE_CANDIDATES_OVERRIDE} )
  else
    _AEGIS_CANDIDATES=(
      "/opt/aegis-src/deploy/compose"   # installer-managed (install.sh default)
      "/opt/aegis/compose"              # legacy / pre-PR layout
    )
  fi
}

# aegis_detect_compose_variant ENV_FILE
#   Reads SQLALCHEMY_DATABASE_URL from the given .env path and prints
#   "sqlite" or "prod" to stdout. Empty stdout means "unknown" (caller
#   decides whether to fail-loud). Strips surrounding whitespace and
#   single/double quotes (common .env writer styles).
aegis_detect_compose_variant() {
  local env_file="$1"
  [[ -f "${env_file}" ]] || return 0
  local db_url
  db_url="$(awk -F= '/^SQLALCHEMY_DATABASE_URL=/ { sub(/^SQLALCHEMY_DATABASE_URL=/, ""); print; exit }' "${env_file}" || true)"
  # Strip surrounding whitespace.
  db_url="${db_url#"${db_url%%[![:space:]]*}"}"   # ltrim
  db_url="${db_url%"${db_url##*[![:space:]]}"}"   # rtrim
  # Strip surrounding quotes.
  if [[ "${db_url}" == \"*\" || "${db_url}" == \'*\' ]]; then
    db_url="${db_url:1:${#db_url}-2}"
  fi
  # SQLAlchemy permits dialect+driver via "+", e.g. postgresql+psycopg://.
  case "${db_url}" in
    sqlite:*|sqlite+*)         echo "sqlite" ;;
    postgresql:*|postgresql+*) echo "prod"   ;;
    postgres:*|postgres+*)     echo "prod"   ;;
    *) ;;  # unknown → empty stdout
  esac
}

# aegis_resolve_compose ENV_FILE [LOG_PREFIX]
#   On success: sets globals COMPOSE_DIR, COMPOSE_FILE, COMPOSE_VARIANT
#   and returns 0. On failure: prints FATAL to stderr and returns 2.
#
#   LOG_PREFIX defaults to "[path-detect]"; install.sh / aegis-upgrade.sh
#   pass their own (e.g. "[install]" / "[upgrade]") for log continuity.
aegis_resolve_compose() {
  local env_file="$1"
  local prefix="${2:-[path-detect]}"

  # Build candidate list: AEGIS_COMPOSE_DIR override (if set) wins; else
  # default ordered list. Override + missing compose => fail-loud (no
  # silent fallthrough — typo'd overrides surface immediately).
  local -a candidates
  if [[ -n "${AEGIS_COMPOSE_DIR:-}" ]]; then
    candidates=( "${AEGIS_COMPOSE_DIR}" )
  else
    _aegis_default_candidates
    candidates=( "${_AEGIS_CANDIDATES[@]}" )
  fi

  # Resolve variant from .env, then operator override, then validate.
  COMPOSE_VARIANT="$(aegis_detect_compose_variant "${env_file}")"
  if [[ -n "${AEGIS_COMPOSE_VARIANT:-}" ]]; then
    COMPOSE_VARIANT="${AEGIS_COMPOSE_VARIANT}"
  fi
  case "${COMPOSE_VARIANT}" in
    sqlite|prod|"") ;;
    *)
      echo "${prefix} FATAL: AEGIS_COMPOSE_VARIANT='${COMPOSE_VARIANT}' must be 'sqlite' or 'prod'" >&2
      return 2
      ;;
  esac

  COMPOSE_DIR=""
  COMPOSE_FILE=""
  local candidate sqlite_path prod_path
  for candidate in "${candidates[@]}"; do
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
          echo "${prefix} FATAL: both docker-compose.sqlite.yml and .prod.yml exist under" >&2
          echo "${prefix}   ${candidate}" >&2
          echo "${prefix} but ${env_file} has no SQLALCHEMY_DATABASE_URL we recognize." >&2
          echo "${prefix} hint: set AEGIS_COMPOSE_VARIANT=sqlite|prod to disambiguate" >&2
          return 2
        elif [[ -f "${sqlite_path}" ]]; then
          COMPOSE_DIR="${candidate}"; COMPOSE_FILE="${sqlite_path}"
          COMPOSE_VARIANT="sqlite"; break
        elif [[ -f "${prod_path}" ]]; then
          COMPOSE_DIR="${candidate}"; COMPOSE_FILE="${prod_path}"
          COMPOSE_VARIANT="prod"; break
        fi
        ;;
    esac
  done

  if [[ -z "${COMPOSE_FILE}" ]]; then
    echo "${prefix} FATAL: no docker-compose*.yml found (variant='${COMPOSE_VARIANT:-auto}') under any of:" >&2
    local c
    for c in "${candidates[@]}"; do
      echo "${prefix}   - ${c}" >&2
    done
    echo "${prefix} hint: set AEGIS_COMPOSE_DIR=/path/to/compose to override" >&2
    return 2
  fi

  return 0
}
