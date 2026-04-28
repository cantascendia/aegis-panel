#!/usr/bin/env bash
# tests/test_deploy_install_smoke.sh — Bash smoke test for deploy/install.
#
# Scope (D.1):
#   1. `--help` exits 0 with usage banner.
#   2. Missing required flag (--domain in non-interactive) exits 2.
#   3. Bash parse check on install.sh + lib/*.sh.
#   4. Dry-run with --non-interactive --domain X --jwt-secret Y
#      --admin-password Z renders an env to a temp dir without docker.
#   5. Rendered env passes validate_rendered_env.
#
# Run:   bash tests/test_deploy_install_smoke.sh
# Pass:  exit 0 + "all tests passed" line.

set -euo pipefail
IFS=$'\n\t'

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_SH="${REPO_ROOT}/deploy/install/install.sh"
LIB_DIR="${REPO_ROOT}/deploy/install/lib"

pass() { printf '  PASS  %s\n' "$*"; }
fail() { printf '  FAIL  %s\n' "$*"; exit 1; }

# ---------------------------------------------------------------------------
# 1. parse check on every shell file we ship
# ---------------------------------------------------------------------------
echo "[smoke] T1: bash -n on install.sh + libs"
bash -n "${INSTALL_SH}"            || fail "install.sh has syntax errors"
bash -n "${LIB_DIR}/detect.sh"     || fail "detect.sh has syntax errors"
bash -n "${LIB_DIR}/render.sh"     || fail "render.sh has syntax errors"
bash -n "${LIB_DIR}/health.sh"     || fail "health.sh has syntax errors"
pass "all shell files parse"

# ---------------------------------------------------------------------------
# 2. --help exits 0 and prints usage
# ---------------------------------------------------------------------------
echo "[smoke] T2: --help exits 0"
help_out="$(bash "${INSTALL_SH}" --help 2>&1)"
help_rc=$?
if (( help_rc != 0 )); then
  fail "--help exited ${help_rc}, expected 0"
fi
if ! grep -q 'Usage:' <<< "${help_out}"; then
  fail "--help output missing 'Usage:' banner"
fi
if ! grep -q -- '--non-interactive' <<< "${help_out}"; then
  fail "--help output missing --non-interactive flag"
fi
pass "--help shows usage banner"

# ---------------------------------------------------------------------------
# 3. Unknown flag exits 2
# ---------------------------------------------------------------------------
echo "[smoke] T3: unknown flag exits 2"
set +e
bash "${INSTALL_SH}" --bogus-flag >/dev/null 2>&1
rc=$?
set -e
if (( rc != 2 )); then
  fail "unknown flag exit code ${rc}, expected 2"
fi
pass "unknown flag rejected with code 2"

# ---------------------------------------------------------------------------
# 4. Render lib unit-style: source render.sh in isolation, render to tmp.
#    We avoid running install.sh end-to-end because it needs docker, which
#    isn't guaranteed in CI for pure-bash tests.
# ---------------------------------------------------------------------------
echo "[smoke] T4: render_env_template + validate_rendered_env"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

# Set up env vars the renderer expects.
export AEGIS_VERSION="v0.2.0-test"
export AEGIS_DOMAIN="test.local"
export PANEL_PORT="8443"
export MARZNODE_GRPC_PORT="62051"
export POSTGRES_PORT="5432"
export POSTGRES_DB="aegis"
export POSTGRES_USER="aegis"
export POSTGRES_PASSWORD="pgpass-AAA"
export REDIS_PORT="6379"
export REDIS_PASSWORD="redispass-BBB"
export JWT_SECRET="AAA"
export DASHBOARD_PATH="/abcd1234"
export XRAY_SUBSCRIPTION_PATH="/qwer5678"
export ADMIN_USERNAME="admin-test"
export ADMIN_PASSWORD="BBB"
export DATABASE_URL="postgresql+psycopg://aegis:pgpass-AAA@127.0.0.1:5432/aegis"
export CF_TUNNEL_ENABLED="false"
export CF_TUNNEL_NAME=""

# shellcheck source=../deploy/install/lib/render.sh
. "${LIB_DIR}/render.sh"

OUT_ENV="${TMP_DIR}/.env"
render_env_template "${REPO_ROOT}/deploy/install/templates/env.tmpl" "${OUT_ENV}"
[[ -f "${OUT_ENV}" ]] || fail "render_env_template did not produce ${OUT_ENV}"

if grep -q '__[A-Z_]*__' "${OUT_ENV}"; then
  echo "------"
  grep '__[A-Z_]*__' "${OUT_ENV}" || true
  echo "------"
  fail "rendered env has stray __TOKEN__ placeholders"
fi

validate_rendered_env "${OUT_ENV}" || fail "validate_rendered_env rejected the rendered env"
pass "render_env_template + validate_rendered_env"

# ---------------------------------------------------------------------------
# 5. AC-D.1.10 floor: rendered env must contain compass 五件套 defaults.
# ---------------------------------------------------------------------------
echo "[smoke] T5: AC-D.1.10 compass 五件套 defaults present"
grep -qE '^XRAY_POLICY_CONN_IDLE=120$'         "${OUT_ENV}" || fail "XRAY_POLICY_CONN_IDLE missing or wrong"
grep -qE '^XRAY_POLICY_HANDSHAKE=2$'           "${OUT_ENV}" || fail "XRAY_POLICY_HANDSHAKE missing"
grep -qE '^JWT_ACCESS_TOKEN_EXPIRE_MINUTES=45$' "${OUT_ENV}" || fail "JWT expiry not 45"
grep -qE '^PANEL_PORT=8443$'                   "${OUT_ENV}" || fail "PANEL_PORT not 8443"
grep -qE '^REALITY_UTLS_FINGERPRINT=chrome$'   "${OUT_ENV}" || fail "uTLS fingerprint not chrome"
grep -qE '^REALITY_FLOW=xtls-rprx-vision$'     "${OUT_ENV}" || fail "REALITY_FLOW not vision"
grep -qE '^REALITY_SNI_BLOCKLIST=.*www\.google\.com.*speedtest\.net' "${OUT_ENV}" || fail "SNI blocklist missing canon entries"
pass "all compass 五件套 defaults present"

# ---------------------------------------------------------------------------
# 6. Validation rejects an env with a default SNI that hits the blocklist.
# ---------------------------------------------------------------------------
echo "[smoke] T6: validate_rendered_env rejects banned SNI in defaults"
BAD_ENV="${TMP_DIR}/bad.env"
cp "${OUT_ENV}" "${BAD_ENV}"
# Force a default SNI to a banned value.
# Use awk so we don't depend on GNU sed -i quirks across BSD/macOS.
awk '/^REALITY_SNI_DEFAULT_GLOBAL=/ { print "REALITY_SNI_DEFAULT_GLOBAL=www.google.com"; next } { print }' "${BAD_ENV}" > "${BAD_ENV}.new"
mv "${BAD_ENV}.new" "${BAD_ENV}"
set +e
validate_rendered_env "${BAD_ENV}" >/dev/null 2>&1
rc=$?
set -e
if (( rc == 0 )); then
  fail "validate_rendered_env accepted banned SNI; expected rejection"
fi
pass "banned SNI in defaults correctly rejected (rc=${rc})"

# ---------------------------------------------------------------------------
# 7. Validation rejects standard panel port (80/443/8080).
# ---------------------------------------------------------------------------
echo "[smoke] T7: validate_rendered_env rejects standard panel port"
BAD2="${TMP_DIR}/bad2.env"
cp "${OUT_ENV}" "${BAD2}"
awk '/^PANEL_PORT=/ { print "PANEL_PORT=8080"; next } { print }' "${BAD2}" > "${BAD2}.new"
mv "${BAD2}.new" "${BAD2}"
set +e
validate_rendered_env "${BAD2}" >/dev/null 2>&1
rc=$?
set -e
if (( rc == 0 )); then
  fail "validate_rendered_env accepted PANEL_PORT=8080; expected rejection"
fi
pass "standard panel port correctly rejected (rc=${rc})"

echo
echo "all tests passed"
