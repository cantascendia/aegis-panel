#!/usr/bin/env bash
# tests/test_deploy_path_detect.sh — Bash unit tests for
# scripts/lib/path-detect.sh (SSOT compose path + variant detection).
#
# Scope:
#   T1.  bash -n parse check.
#   T2.  aegis_detect_compose_variant: postgresql:// → "prod".
#   T3.  aegis_detect_compose_variant: postgresql+psycopg:// → "prod".
#   T4.  aegis_detect_compose_variant: sqlite:// → "sqlite".
#   T5.  aegis_detect_compose_variant: missing .env → empty.
#   T6.  aegis_detect_compose_variant: unrecognized scheme → empty.
#   T7.  aegis_detect_compose_variant: double-quoted value parsed.
#   T8.  aegis_detect_compose_variant: single-quoted value parsed.
#   T9.  aegis_detect_compose_variant: trailing whitespace stripped.
#   T10. aegis_resolve_compose: AEGIS_COMPOSE_DIR override happy path.
#   T11. aegis_resolve_compose: typo'd AEGIS_COMPOSE_DIR → fail-loud.
#   T12. aegis_resolve_compose: multi-candidate scan picks first present.
#   T13. aegis_resolve_compose: no candidate matches → fail-loud + lists.
#   T14. aegis_resolve_compose: AEGIS_COMPOSE_VARIANT="invalid" → fail-loud.
#   T15. aegis_resolve_compose: ambiguous .env + both files → fail-loud.
#   T16. aegis_resolve_compose: AEGIS_COMPOSE_VARIANT override beats .env.
#
# Run:   bash tests/test_deploy_path_detect.sh
# Pass:  exit 0 + "all tests passed" line.
#
# Refs: SSOT extraction PR, L-040 follow-up #1.

set -euo pipefail
IFS=$'\n\t'

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LIB="${REPO_ROOT}/scripts/lib/path-detect.sh"

pass() { printf '  PASS  %s\n' "$*"; }
fail() { printf '  FAIL  %s\n' "$*"; exit 1; }

# ---------------------------------------------------------------------------
# T1: parse check
# ---------------------------------------------------------------------------
echo "[smoke] T1: bash -n on path-detect.sh"
bash -n "${LIB}" || fail "path-detect.sh has syntax errors"
pass "path-detect.sh parses"

TMPROOT="$(mktemp -d)"
trap 'rm -rf "${TMPROOT}"' EXIT

write_env() {
  # $1 = path, $2 = raw line content for SQLALCHEMY_DATABASE_URL value
  local path="$1" raw="${2:-}"
  cat >"${path}" <<EOF
AEGIS_VERSION=v0.4.0
PANEL_PORT=8443
SQLALCHEMY_DATABASE_URL=${raw}
EOF
}

# Run a bash subshell that sources the lib then runs $1, capturing stdout.
# Env passes through. We deliberately use `bash -c` rather than sourcing in
# this test process so each call starts fresh (no leaked globals).
run_lib() {
  local snippet="$1"; shift
  bash -c ". '${LIB}'; ${snippet}" "$@"
}

# ---------------------------------------------------------------------------
# T2: postgresql:// → prod
# ---------------------------------------------------------------------------
echo "[smoke] T2: postgresql:// → prod"
ENV2="${TMPROOT}/t2.env"
write_env "${ENV2}" "postgresql://u:p@host/db"
out="$(run_lib "aegis_detect_compose_variant '${ENV2}'")"
[[ "${out}" == "prod" ]] || fail "T2 expected 'prod', got '${out}'"
pass "postgresql:// → prod"

# ---------------------------------------------------------------------------
# T3: postgresql+psycopg:// → prod
# ---------------------------------------------------------------------------
echo "[smoke] T3: postgresql+psycopg:// → prod"
ENV3="${TMPROOT}/t3.env"
write_env "${ENV3}" "postgresql+psycopg://u:p@host/db"
out="$(run_lib "aegis_detect_compose_variant '${ENV3}'")"
[[ "${out}" == "prod" ]] || fail "T3 expected 'prod', got '${out}'"
pass "postgresql+psycopg:// → prod"

# ---------------------------------------------------------------------------
# T4: sqlite:// → sqlite
# ---------------------------------------------------------------------------
echo "[smoke] T4: sqlite:// → sqlite"
ENV4="${TMPROOT}/t4.env"
write_env "${ENV4}" "sqlite:////var/lib/marzneshin/db.sqlite3"
out="$(run_lib "aegis_detect_compose_variant '${ENV4}'")"
[[ "${out}" == "sqlite" ]] || fail "T4 expected 'sqlite', got '${out}'"
pass "sqlite:// → sqlite"

# ---------------------------------------------------------------------------
# T5: missing .env → empty
# ---------------------------------------------------------------------------
echo "[smoke] T5: missing .env → empty"
out="$(run_lib "aegis_detect_compose_variant '${TMPROOT}/nope.env'")"
[[ -z "${out}" ]] || fail "T5 expected empty, got '${out}'"
pass "missing .env → empty"

# ---------------------------------------------------------------------------
# T6: unrecognized scheme → empty
# ---------------------------------------------------------------------------
echo "[smoke] T6: unrecognized scheme → empty"
ENV6="${TMPROOT}/t6.env"
write_env "${ENV6}" "mysql://u:p@host/db"
out="$(run_lib "aegis_detect_compose_variant '${ENV6}'")"
[[ -z "${out}" ]] || fail "T6 expected empty, got '${out}'"
pass "unrecognized scheme → empty"

# ---------------------------------------------------------------------------
# T7: double-quoted value parsed
# ---------------------------------------------------------------------------
echo "[smoke] T7: double-quoted value parsed"
ENV7="${TMPROOT}/t7.env"
cat >"${ENV7}" <<'EOF'
SQLALCHEMY_DATABASE_URL="postgresql+psycopg://u:p@host/db"
EOF
out="$(run_lib "aegis_detect_compose_variant '${ENV7}'")"
[[ "${out}" == "prod" ]] || fail "T7 expected 'prod', got '${out}'"
pass "double-quoted value parsed"

# ---------------------------------------------------------------------------
# T8: single-quoted value parsed
# ---------------------------------------------------------------------------
echo "[smoke] T8: single-quoted value parsed"
ENV8="${TMPROOT}/t8.env"
cat >"${ENV8}" <<EOF
SQLALCHEMY_DATABASE_URL='sqlite:////var/lib/db.sqlite3'
EOF
out="$(run_lib "aegis_detect_compose_variant '${ENV8}'")"
[[ "${out}" == "sqlite" ]] || fail "T8 expected 'sqlite', got '${out}'"
pass "single-quoted value parsed"

# ---------------------------------------------------------------------------
# T9: trailing whitespace stripped
# ---------------------------------------------------------------------------
echo "[smoke] T9: trailing whitespace stripped"
ENV9="${TMPROOT}/t9.env"
printf 'SQLALCHEMY_DATABASE_URL=  postgresql://u:p@host/db  \n' >"${ENV9}"
out="$(run_lib "aegis_detect_compose_variant '${ENV9}'")"
[[ "${out}" == "prod" ]] || fail "T9 expected 'prod', got '${out}'"
pass "trailing whitespace stripped"

# ---------------------------------------------------------------------------
# T10: aegis_resolve_compose AEGIS_COMPOSE_DIR override happy path
# ---------------------------------------------------------------------------
echo "[smoke] T10: aegis_resolve_compose AEGIS_COMPOSE_DIR override"
T10_DIR="${TMPROOT}/t10/compose"
mkdir -p "${T10_DIR}"
: >"${T10_DIR}/docker-compose.prod.yml"
ENV10="${TMPROOT}/t10.env"
write_env "${ENV10}" "postgresql://u:p@host/db"
out="$(AEGIS_COMPOSE_DIR="${T10_DIR}" run_lib \
  "aegis_resolve_compose '${ENV10}' '[t10]' && echo \"DIR=\${COMPOSE_DIR}\" && echo \"FILE=\${COMPOSE_FILE}\" && echo \"VARIANT=\${COMPOSE_VARIANT}\"")"
echo "${out}" | grep -qF "DIR=${T10_DIR}" || fail "T10 missing DIR: ${out}"
echo "${out}" | grep -qF "FILE=${T10_DIR}/docker-compose.prod.yml" || fail "T10 missing FILE: ${out}"
echo "${out}" | grep -qF "VARIANT=prod" || fail "T10 missing VARIANT: ${out}"
pass "aegis_resolve_compose override + prod variant"

# ---------------------------------------------------------------------------
# T11: typo'd AEGIS_COMPOSE_DIR → fail-loud
# ---------------------------------------------------------------------------
echo "[smoke] T11: typo'd AEGIS_COMPOSE_DIR → fail-loud"
ENV11="${TMPROOT}/t11.env"
write_env "${ENV11}" "postgresql://u:p@host/db"
set +e
out="$(AEGIS_COMPOSE_DIR="${TMPROOT}/does-not-exist" run_lib \
  "aegis_resolve_compose '${ENV11}' '[t11]'" 2>&1)"
rc=$?
set -e
[[ "${rc}" -eq 2 ]] || fail "T11 expected exit 2, got ${rc}"
echo "${out}" | grep -qF "FATAL: no docker-compose" || fail "T11 missing FATAL: ${out}"
echo "${out}" | grep -qF "${TMPROOT}/does-not-exist" || fail "T11 missing override path: ${out}"
pass "typo'd override → fail-loud (no silent fallthrough)"

# ---------------------------------------------------------------------------
# T12: multi-candidate scan picks first present
# ---------------------------------------------------------------------------
echo "[smoke] T12: multi-candidate scan picks first present"
T12_FIRST="${TMPROOT}/t12-first/compose"
T12_SECOND="${TMPROOT}/t12-second/compose"
mkdir -p "${T12_FIRST}" "${T12_SECOND}"
: >"${T12_SECOND}/docker-compose.prod.yml"  # only second has it
ENV12="${TMPROOT}/t12.env"
write_env "${ENV12}" "postgresql://u:p@host/db"
out="$(AEGIS_COMPOSE_CANDIDATES_OVERRIDE="${T12_FIRST}:${T12_SECOND}" run_lib \
  "aegis_resolve_compose '${ENV12}' '[t12]' && echo \"DIR=\${COMPOSE_DIR}\"")"
echo "${out}" | grep -qF "DIR=${T12_SECOND}" || fail "T12 expected fallback to second, got: ${out}"
pass "multi-candidate scan falls back to second when first is empty"

# ---------------------------------------------------------------------------
# T13: no candidate matches → fail-loud + lists candidates
# ---------------------------------------------------------------------------
echo "[smoke] T13: no candidate matches → fail-loud"
T13_FIRST="${TMPROOT}/t13-first/compose"
T13_SECOND="${TMPROOT}/t13-second/compose"
mkdir -p "${T13_FIRST}" "${T13_SECOND}"  # both empty
ENV13="${TMPROOT}/t13.env"
write_env "${ENV13}" "postgresql://u:p@host/db"
set +e
out="$(AEGIS_COMPOSE_CANDIDATES_OVERRIDE="${T13_FIRST}:${T13_SECOND}" run_lib \
  "aegis_resolve_compose '${ENV13}' '[t13]'" 2>&1)"
rc=$?
set -e
[[ "${rc}" -eq 2 ]] || fail "T13 expected exit 2, got ${rc}"
echo "${out}" | grep -qF "${T13_FIRST}" || fail "T13 missing first candidate in error: ${out}"
echo "${out}" | grep -qF "${T13_SECOND}" || fail "T13 missing second candidate in error: ${out}"
pass "no candidate matches → fail-loud lists all candidates"

# ---------------------------------------------------------------------------
# T14: AEGIS_COMPOSE_VARIANT="invalid" → fail-loud
# ---------------------------------------------------------------------------
echo "[smoke] T14: invalid AEGIS_COMPOSE_VARIANT → fail-loud"
T14_DIR="${TMPROOT}/t14/compose"
mkdir -p "${T14_DIR}"
: >"${T14_DIR}/docker-compose.prod.yml"
ENV14="${TMPROOT}/t14.env"
write_env "${ENV14}" "postgresql://u:p@host/db"
set +e
out="$(AEGIS_COMPOSE_DIR="${T14_DIR}" AEGIS_COMPOSE_VARIANT="mysql" run_lib \
  "aegis_resolve_compose '${ENV14}' '[t14]'" 2>&1)"
rc=$?
set -e
[[ "${rc}" -eq 2 ]] || fail "T14 expected exit 2, got ${rc}"
echo "${out}" | grep -qF "must be 'sqlite' or 'prod'" || fail "T14 missing validation msg: ${out}"
pass "invalid AEGIS_COMPOSE_VARIANT validated"

# ---------------------------------------------------------------------------
# T15: ambiguous .env (no DATABASE_URL) + both files → fail-loud
# ---------------------------------------------------------------------------
echo "[smoke] T15: ambiguous .env + both files → fail-loud"
T15_DIR="${TMPROOT}/t15/compose"
mkdir -p "${T15_DIR}"
: >"${T15_DIR}/docker-compose.sqlite.yml"
: >"${T15_DIR}/docker-compose.prod.yml"
ENV15="${TMPROOT}/t15.env"
write_env "${ENV15}" ""  # empty DB URL
set +e
out="$(AEGIS_COMPOSE_DIR="${T15_DIR}" run_lib \
  "aegis_resolve_compose '${ENV15}' '[t15]'" 2>&1)"
rc=$?
set -e
[[ "${rc}" -eq 2 ]] || fail "T15 expected exit 2, got ${rc}"
echo "${out}" | grep -qF "AEGIS_COMPOSE_VARIANT" || fail "T15 missing hint: ${out}"
pass "ambiguous .env + both files → fail-loud with hint"

# ---------------------------------------------------------------------------
# T16: AEGIS_COMPOSE_VARIANT override beats .env autodetect
# ---------------------------------------------------------------------------
echo "[smoke] T16: AEGIS_COMPOSE_VARIANT override beats .env"
T16_DIR="${TMPROOT}/t16/compose"
mkdir -p "${T16_DIR}"
: >"${T16_DIR}/docker-compose.sqlite.yml"
: >"${T16_DIR}/docker-compose.prod.yml"
ENV16="${TMPROOT}/t16.env"
write_env "${ENV16}" "postgresql://u:p@host/db"  # would pick prod
out="$(AEGIS_COMPOSE_DIR="${T16_DIR}" AEGIS_COMPOSE_VARIANT="sqlite" run_lib \
  "aegis_resolve_compose '${ENV16}' '[t16]' && echo \"FILE=\${COMPOSE_FILE}\"")"
echo "${out}" | grep -qF "FILE=${T16_DIR}/docker-compose.sqlite.yml" \
  || fail "T16 expected sqlite override, got: ${out}"
pass "AEGIS_COMPOSE_VARIANT override beats .env"

echo
echo "all tests passed"
