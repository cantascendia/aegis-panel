#!/usr/bin/env bash
# tests/test_deploy_aegis_upgrade.sh — Bash unit test for aegis-upgrade.sh
# compose-dir + variant resolution (L-040 regression coverage).
#
# Scope:
#   T1. bash -n parse check.
#   T2. multi-candidate scan picks /opt/aegis-src/deploy/compose first
#       (installer-managed default).
#   T3. multi-candidate scan falls back to /opt/aegis/compose (legacy)
#       when the first candidate is empty.
#   T4. AEGIS_COMPOSE_DIR override is honored (single-candidate mode).
#   T5. fail-loud (exit 2) when *no* candidate has docker-compose*.yml.
#   T6. AEGIS_COMPOSE_DIR override + missing compose => fail-loud
#       (does NOT silently fall through to default candidates).
#   T7. variant=prod selected from SQLALCHEMY_DATABASE_URL=postgresql:...
#       even when both sqlite and prod compose files exist on disk
#       (codex cross-review P1 — installer-managed dir contains BOTH).
#   T8. variant=sqlite selected from SQLALCHEMY_DATABASE_URL=sqlite:....
#   T9. AEGIS_COMPOSE_VARIANT operator override wins over .env autodetect.
#   T10. ambiguous .env (no recognized DATABASE_URL) + both files present
#        => fail-loud, hints AEGIS_COMPOSE_VARIANT.
#   T11. AEGIS_COMPOSE_VARIANT=invalid => fail-loud.
#
# Strategy: we don't run docker. We patch the script to abort right after
# the compose-dir resolution step by injecting a fake ENV_FILE and
# replacing the docker / awk / mv stage with `exit 0` once COMPOSE_FILE
# is printed. We assert the printed COMPOSE_FILE matches expectation.
#
# Run:   bash tests/test_deploy_aegis_upgrade.sh
# Pass:  exit 0 + "all tests passed" line.
#
# Refs: L-040, PR fix/aegis-upgrade-compose-path

set -euo pipefail
IFS=$'\n\t'

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="${REPO_ROOT}/scripts/aegis-upgrade.sh"

pass() { printf '  PASS  %s\n' "$*"; }
fail() { printf '  FAIL  %s\n' "$*"; exit 1; }

# ---------------------------------------------------------------------------
# T1: parse check
# ---------------------------------------------------------------------------
echo "[smoke] T1: bash -n on aegis-upgrade.sh"
bash -n "${SCRIPT}" || fail "aegis-upgrade.sh has syntax errors"
pass "aegis-upgrade.sh parses"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
# Build a stub script that runs up to (and including) the compose-dir
# resolution block, then prints COMPOSE_FILE and exits. Avoids running
# docker / mutating /opt/aegis/.env.
make_stub() {
  local stub="$1"
  awk '
    /^# Backup \.env/ { print "echo \"COMPOSE_FILE=${COMPOSE_FILE}\""; print "exit 0"; exit }
    { print }
  ' "${SCRIPT}" >"${stub}"
  chmod +x "${stub}"
}

make_compose_dir() {
  # $1 = dir, $2 = which file ("sqlite" | "prod" | "both" | "none")
  local dir="$1" kind="$2"
  mkdir -p "${dir}"
  case "${kind}" in
    sqlite) : >"${dir}/docker-compose.sqlite.yml" ;;
    prod)   : >"${dir}/docker-compose.prod.yml"   ;;
    both)
      : >"${dir}/docker-compose.sqlite.yml"
      : >"${dir}/docker-compose.prod.yml"
      ;;
    none) ;;  # leave dir empty
  esac
}

write_env() {
  # $1 = path, $2 = db_url (may be empty)
  local path="$1" db_url="${2:-}"
  cat >"${path}" <<EOF
AEGIS_VERSION=v0.4.0
PANEL_PORT=8443
SQLALCHEMY_DATABASE_URL=${db_url}
EOF
}

VARIANT_STUB() {
  # $1 = first-candidate-dir, $2 = second-candidate-dir, $3 = output stub path
  local first="$1" second="$2" out="$3"
  awk -v first="${first}" -v second="${second}" '
    /^    "\/opt\/aegis-src\/deploy\/compose"/ { print "    \"" first "\""; next }
    /^    "\/opt\/aegis\/compose"/             { print "    \"" second "\""; next }
    /^# Backup \.env/                          { print "echo \"COMPOSE_FILE=${COMPOSE_FILE}\""; print "exit 0"; exit }
    { print }
  ' "${SCRIPT}" >"${out}"
  chmod +x "${out}"
}

TMPROOT="$(mktemp -d)"
trap 'rm -rf "${TMPROOT}"' EXIT

STUB="${TMPROOT}/aegis-upgrade-stub.sh"
make_stub "${STUB}"

# Default fake .env: prod variant (matches majority of installer-managed
# hosts). Tests that need a different DB_URL build their own.
ENV_FILE="${TMPROOT}/fake.env"
write_env "${ENV_FILE}" "postgresql+psycopg://u:p@127.0.0.1:5432/aegis"

# ---------------------------------------------------------------------------
# T2: prefer first candidate (installer-managed) when present
# ---------------------------------------------------------------------------
echo "[smoke] T2: default candidate order picks first when present"
T2_FIRST="${TMPROOT}/t2-first/compose"
T2_SECOND="${TMPROOT}/t2-second/compose"
make_compose_dir "${T2_FIRST}"  prod
make_compose_dir "${T2_SECOND}" prod
T2_STUB="${TMPROOT}/t2-stub.sh"
VARIANT_STUB "${T2_FIRST}" "${T2_SECOND}" "${T2_STUB}"
out="$(AEGIS_ENV_FILE="${ENV_FILE}" bash "${T2_STUB}" v0.4.1 2>&1)"
echo "${out}" | grep -qF "COMPOSE_FILE=${T2_FIRST}/docker-compose.prod.yml" \
  || fail "T2 expected first candidate, got: ${out}"
pass "first candidate (installer-managed) wins when present"

# ---------------------------------------------------------------------------
# T3: fall back to second candidate when first is empty
# ---------------------------------------------------------------------------
echo "[smoke] T3: fall back to second candidate"
T3_FIRST="${TMPROOT}/t3-first/compose"
T3_SECOND="${TMPROOT}/t3-second/compose"
make_compose_dir "${T3_FIRST}"  none
make_compose_dir "${T3_SECOND}" prod
T3_STUB="${TMPROOT}/t3-stub.sh"
VARIANT_STUB "${T3_FIRST}" "${T3_SECOND}" "${T3_STUB}"
out="$(AEGIS_ENV_FILE="${ENV_FILE}" bash "${T3_STUB}" v0.4.1 2>&1)"
echo "${out}" | grep -qF "COMPOSE_FILE=${T3_SECOND}/docker-compose.prod.yml" \
  || fail "T3 expected second candidate, got: ${out}"
pass "falls back to second candidate (legacy /opt/aegis/compose layout)"

# ---------------------------------------------------------------------------
# T4: AEGIS_COMPOSE_DIR override honored
# ---------------------------------------------------------------------------
echo "[smoke] T4: AEGIS_COMPOSE_DIR override honored"
T4_DIR="${TMPROOT}/t4-override/compose"
make_compose_dir "${T4_DIR}" prod
out="$(AEGIS_ENV_FILE="${ENV_FILE}" AEGIS_COMPOSE_DIR="${T4_DIR}" bash "${STUB}" v0.4.1 2>&1)"
echo "${out}" | grep -qF "COMPOSE_FILE=${T4_DIR}/docker-compose.prod.yml" \
  || fail "T4 expected override path, got: ${out}"
pass "AEGIS_COMPOSE_DIR override picks the operator-supplied dir"

# ---------------------------------------------------------------------------
# T5: fail-loud when no candidate has docker-compose*.yml
# ---------------------------------------------------------------------------
echo "[smoke] T5: fail-loud when no compose found"
T5_FIRST="${TMPROOT}/t5-first/compose"
T5_SECOND="${TMPROOT}/t5-second/compose"
make_compose_dir "${T5_FIRST}"  none
make_compose_dir "${T5_SECOND}" none
T5_STUB="${TMPROOT}/t5-stub.sh"
VARIANT_STUB "${T5_FIRST}" "${T5_SECOND}" "${T5_STUB}"
set +e
out="$(AEGIS_ENV_FILE="${ENV_FILE}" bash "${T5_STUB}" v0.4.1 2>&1)"
rc=$?
set -e
[[ "${rc}" -eq 2 ]] || fail "T5 expected exit 2, got ${rc}"
echo "${out}" | grep -qF "FATAL: no docker-compose" \
  || fail "T5 expected FATAL message, got: ${out}"
echo "${out}" | grep -qF "${T5_FIRST}" \
  || fail "T5 expected error to list first candidate, got: ${out}"
pass "fail-loud (exit 2) + lists candidates when none match"

# ---------------------------------------------------------------------------
# T6: override + missing compose => fail-loud (no silent fallthrough)
# ---------------------------------------------------------------------------
echo "[smoke] T6: override + missing compose => fail-loud"
T6_OVERRIDE="${TMPROOT}/t6-typo/compose"
make_compose_dir "${T6_OVERRIDE}" none
set +e
out="$(AEGIS_ENV_FILE="${ENV_FILE}" AEGIS_COMPOSE_DIR="${T6_OVERRIDE}" bash "${STUB}" v0.4.1 2>&1)"
rc=$?
set -e
[[ "${rc}" -eq 2 ]] || fail "T6 expected exit 2, got ${rc}"
echo "${out}" | grep -qF "${T6_OVERRIDE}" \
  || fail "T6 expected error to mention the override path, got: ${out}"
pass "AEGIS_COMPOSE_DIR override does not silently fall through"

# ---------------------------------------------------------------------------
# T7: variant=prod from SQLALCHEMY_DATABASE_URL=postgresql:...
#     even when both compose files exist (codex P1).
# ---------------------------------------------------------------------------
echo "[smoke] T7: postgres .env + both compose files => picks prod"
T7_DIR="${TMPROOT}/t7-both/compose"
make_compose_dir "${T7_DIR}" both
T7_ENV="${TMPROOT}/t7.env"
write_env "${T7_ENV}" "postgresql+psycopg://u:p@127.0.0.1:5432/aegis"
out="$(AEGIS_ENV_FILE="${T7_ENV}" AEGIS_COMPOSE_DIR="${T7_DIR}" bash "${STUB}" v0.4.1 2>&1)"
echo "${out}" | grep -qF "COMPOSE_FILE=${T7_DIR}/docker-compose.prod.yml" \
  || fail "T7 expected prod variant, got: ${out}"
pass "postgres .env + both files => picks docker-compose.prod.yml"

# ---------------------------------------------------------------------------
# T8: variant=sqlite from SQLALCHEMY_DATABASE_URL=sqlite:...
#     even when both compose files exist.
# ---------------------------------------------------------------------------
echo "[smoke] T8: sqlite .env + both compose files => picks sqlite"
T8_DIR="${TMPROOT}/t8-both/compose"
make_compose_dir "${T8_DIR}" both
T8_ENV="${TMPROOT}/t8.env"
write_env "${T8_ENV}" "sqlite:////var/lib/marzneshin/db.sqlite3"
out="$(AEGIS_ENV_FILE="${T8_ENV}" AEGIS_COMPOSE_DIR="${T8_DIR}" bash "${STUB}" v0.4.1 2>&1)"
echo "${out}" | grep -qF "COMPOSE_FILE=${T8_DIR}/docker-compose.sqlite.yml" \
  || fail "T8 expected sqlite variant, got: ${out}"
pass "sqlite .env + both files => picks docker-compose.sqlite.yml"

# ---------------------------------------------------------------------------
# T9: AEGIS_COMPOSE_VARIANT override wins over .env
# ---------------------------------------------------------------------------
echo "[smoke] T9: AEGIS_COMPOSE_VARIANT override wins over .env"
T9_DIR="${TMPROOT}/t9-both/compose"
make_compose_dir "${T9_DIR}" both
T9_ENV="${TMPROOT}/t9.env"
write_env "${T9_ENV}" "postgresql+psycopg://u:p@127.0.0.1:5432/aegis"
out="$(AEGIS_ENV_FILE="${T9_ENV}" AEGIS_COMPOSE_DIR="${T9_DIR}" \
       AEGIS_COMPOSE_VARIANT="sqlite" bash "${STUB}" v0.4.1 2>&1)"
echo "${out}" | grep -qF "COMPOSE_FILE=${T9_DIR}/docker-compose.sqlite.yml" \
  || fail "T9 expected sqlite override to win, got: ${out}"
pass "AEGIS_COMPOSE_VARIANT override beats .env autodetect"

# ---------------------------------------------------------------------------
# T10: ambiguous (.env has no recognized DATABASE_URL) + both files
#      => fail-loud, hints AEGIS_COMPOSE_VARIANT.
# ---------------------------------------------------------------------------
echo "[smoke] T10: ambiguous .env + both compose files => fail-loud"
T10_DIR="${TMPROOT}/t10-both/compose"
make_compose_dir "${T10_DIR}" both
T10_ENV="${TMPROOT}/t10.env"
write_env "${T10_ENV}" ""   # empty DB URL
set +e
out="$(AEGIS_ENV_FILE="${T10_ENV}" AEGIS_COMPOSE_DIR="${T10_DIR}" bash "${STUB}" v0.4.1 2>&1)"
rc=$?
set -e
[[ "${rc}" -eq 2 ]] || fail "T10 expected exit 2, got ${rc}"
echo "${out}" | grep -qF "AEGIS_COMPOSE_VARIANT" \
  || fail "T10 expected hint about AEGIS_COMPOSE_VARIANT, got: ${out}"
pass "ambiguous .env + both compose files => fail-loud with hint"

# ---------------------------------------------------------------------------
# T11: AEGIS_COMPOSE_VARIANT=invalid => fail-loud
# ---------------------------------------------------------------------------
echo "[smoke] T11: AEGIS_COMPOSE_VARIANT invalid => fail-loud"
T11_DIR="${TMPROOT}/t11-both/compose"
make_compose_dir "${T11_DIR}" both
set +e
out="$(AEGIS_ENV_FILE="${ENV_FILE}" AEGIS_COMPOSE_DIR="${T11_DIR}" \
       AEGIS_COMPOSE_VARIANT="mysql" bash "${STUB}" v0.4.1 2>&1)"
rc=$?
set -e
[[ "${rc}" -eq 2 ]] || fail "T11 expected exit 2, got ${rc}"
echo "${out}" | grep -qF "must be 'sqlite' or 'prod'" \
  || fail "T11 expected validation error, got: ${out}"
pass "AEGIS_COMPOSE_VARIANT validates input"

echo
echo "all tests passed"
