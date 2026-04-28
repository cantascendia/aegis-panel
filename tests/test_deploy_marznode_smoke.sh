#!/usr/bin/env bash
# tests/test_deploy_marznode_smoke.sh — Bash smoke test for deploy/marznode (D.2).
#
# Scope:
#   1. `bash -n` parse check on install-node.sh.
#   2. `--help` exits 0 with usage banner.
#   3. Unknown flag exits 2.
#   4. --non-interactive missing required flag exits 2 (--control-plane).
#   5. Dry-run with full flag set parses arguments cleanly through step 4
#      (does not exercise docker / cert fetch — those need a live panel).
#   6. .env.example references all required vars.
#
# Run:   bash tests/test_deploy_marznode_smoke.sh
# Pass:  exit 0 + "all tests passed" line.

set -euo pipefail
IFS=$'\n\t'

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_NODE_SH="${REPO_ROOT}/deploy/marznode/install-node.sh"
COMPOSE_YML="${REPO_ROOT}/deploy/marznode/docker-compose.yml"
ENV_EXAMPLE="${REPO_ROOT}/deploy/marznode/.env.example"

pass() { printf '  PASS  %s\n' "$*"; }
fail() { printf '  FAIL  %s\n' "$*"; exit 1; }

# ---------------------------------------------------------------------------
# 1. Parse check
# ---------------------------------------------------------------------------
echo "[smoke] T1: bash -n on install-node.sh"
bash -n "${INSTALL_NODE_SH}" || fail "install-node.sh has syntax errors"
pass "install-node.sh parses cleanly"

# ---------------------------------------------------------------------------
# 2. --help exits 0
# ---------------------------------------------------------------------------
echo "[smoke] T2: --help exits 0"
set +e
help_out="$(bash "${INSTALL_NODE_SH}" --help 2>&1)"
help_rc=$?
set -e
if (( help_rc != 0 )); then
  fail "--help exited ${help_rc}, expected 0"
fi
if ! grep -q 'Usage:' <<< "${help_out}"; then
  fail "--help output missing 'Usage:' banner"
fi
if ! grep -q -- '--control-plane' <<< "${help_out}"; then
  fail "--help output missing --control-plane flag"
fi
if ! grep -q -- '--cert-mode' <<< "${help_out}"; then
  fail "--help output missing --cert-mode flag"
fi
if ! grep -q -- '--non-interactive' <<< "${help_out}"; then
  fail "--help output missing --non-interactive flag"
fi
pass "--help shows usage banner with required flags"

# ---------------------------------------------------------------------------
# 3. Unknown flag exits 2
# ---------------------------------------------------------------------------
echo "[smoke] T3: unknown flag exits 2"
set +e
bash "${INSTALL_NODE_SH}" --bogus-flag >/dev/null 2>&1
rc=$?
set -e
if (( rc != 2 )); then
  fail "unknown flag exit code ${rc}, expected 2"
fi
pass "unknown flag rejected with code 2"

# ---------------------------------------------------------------------------
# 4. --non-interactive missing required flag exits 2.
#
# We point AEGIS_NODE_PREFIX at a tmp dir so the script doesn't try to write
# to /opt/aegis-marznode (which requires root in CI). The script exits in
# step 4 (collect_inputs) when --control-plane is empty, well before any
# filesystem mutation -- so the steps 1-3 sentinels created in TMP are fine.
# ---------------------------------------------------------------------------
echo "[smoke] T4: --non-interactive missing --control-plane exits 2"
TMP_PREFIX="$(mktemp -d)"
trap 'rm -rf "${TMP_PREFIX}"' EXIT

# Stub docker / openssl / curl on PATH so steps 1-3 don't trip dep checks.
STUB_BIN="${TMP_PREFIX}/bin"
mkdir -p "${STUB_BIN}"
for cmd in docker curl openssl; do
  cat >"${STUB_BIN}/${cmd}" <<'EOF'
#!/usr/bin/env bash
# minimal stub: echo args and exit 0 for `version` style probes.
case "$*" in
  *compose*version*) exit 0 ;;
  *version*)         exit 0 ;;
  *)                 exit 0 ;;
esac
EOF
  chmod +x "${STUB_BIN}/${cmd}"
done

set +e
AEGIS_NODE_PREFIX="${TMP_PREFIX}/prefix" \
  PATH="${STUB_BIN}:${PATH}" \
  bash "${INSTALL_NODE_SH}" \
    --non-interactive \
    --cert-mode bootstrap \
    --cert-token tok_test \
    --node-name test-node \
    --dry-run \
    >/dev/null 2>&1
rc=$?
set -e
if (( rc != 2 )); then
  fail "missing --control-plane in non-interactive should exit 2; got ${rc}"
fi
pass "missing --control-plane rejected with code 2"

# ---------------------------------------------------------------------------
# 5. Argument validation rejects bad combos.
#
# We can't drive the script all the way through dry-run on every CI host
# (step 2 reads /etc/os-release; CI runners with non-tier-1 distros would
# fail before parse validation completes). Instead we cover argument
# validation by sourcing the install-node.sh in library mode (skipping
# its trailing `main "$@"`) and calling parse_args + step_4_collect_inputs
# directly. The script is self-contained enough that this works even when
# /etc/os-release is missing -- step 4 doesn't touch the OS.
# ---------------------------------------------------------------------------
echo "[smoke] T5: argument validation rejects bad combos"

# Build a sourceable copy of install-node.sh with `main "$@"` stripped AND
# the detect.sh source line rewritten to point at the real lib (otherwise
# the relative path resolves against tmp dir).
LIB_INSTALL="${TMP_PREFIX}/install-node.lib.sh"
DETECT_SH="${REPO_ROOT}/deploy/install/lib/detect.sh"
awk -v detect="${DETECT_SH}" '
  /^main "\$@"$/ { next }
  /\/install\/lib\/detect\.sh"$/ { print ". \"" detect "\""; next }
  { print }
' "${INSTALL_NODE_SH}" > "${LIB_INSTALL}"

run_validate() {
  # Run parse_args + step_4_collect_inputs in a subshell. The script uses
  # `fatal` -> `exit N` so the subshell propagates the exit code directly.
  set +e
  AEGIS_NODE_PREFIX="${TMP_PREFIX}/prefix5" \
    PATH="${STUB_BIN}:${PATH}" \
    bash -c "
      # Source as a library (the lib has no trailing main call).
      # shellcheck disable=SC1090
      . '${LIB_INSTALL}'
      # Skip the system port probe; we only want argument-validation coverage.
      check_port_free() { return 0; }
      parse_args \"\$@\"
      step_4_collect_inputs >/dev/null 2>&1
    " _ "$@" >/dev/null 2>&1
  local rc=$?
  set -e
  echo "${rc}"
}

# 5a. Bad --cert-mode -> exit 2.
rc="$(run_validate --non-interactive --control-plane p.test --node-name n1 --cert-mode badmode --dry-run)"
[[ "${rc}" == "2" ]] || fail "bad --cert-mode should exit 2; got ${rc}"

# 5b. --cert-mode bootstrap without --cert-token -> exit 2.
rc="$(run_validate --non-interactive --control-plane p.test --node-name n1 --cert-mode bootstrap --dry-run)"
[[ "${rc}" == "2" ]] || fail "missing --cert-token in bootstrap mode should exit 2; got ${rc}"

# 5c. --cert-mode file without --cert-file -> exit 2.
rc="$(run_validate --non-interactive --control-plane p.test --node-name n1 --cert-mode file --dry-run)"
[[ "${rc}" == "2" ]] || fail "missing --cert-file in file mode should exit 2; got ${rc}"

# 5d. Invalid --node-name (whitespace) -> exit 2.
rc="$(run_validate --non-interactive --control-plane p.test --node-name 'bad name' --cert-mode bootstrap --cert-token tok --dry-run)"
[[ "${rc}" == "2" ]] || fail "bad --node-name should exit 2; got ${rc}"

# 5e. --grpc-port non-numeric -> exit 2.
rc="$(run_validate --non-interactive --control-plane p.test --node-name n1 --grpc-port abc --cert-mode bootstrap --cert-token tok --dry-run)"
[[ "${rc}" == "2" ]] || fail "non-numeric --grpc-port should exit 2; got ${rc}"

# 5f. --grpc-port out of range -> exit 2.
rc="$(run_validate --non-interactive --control-plane p.test --node-name n1 --grpc-port 70000 --cert-mode bootstrap --cert-token tok --dry-run)"
[[ "${rc}" == "2" ]] || fail "out-of-range --grpc-port should exit 2; got ${rc}"

# 5g. Happy path -> exit 0.
PEM_FILE="${TMP_PREFIX}/marznode-cert.pem"
cat >"${PEM_FILE}" <<'EOF'
-----BEGIN CERTIFICATE-----
MIIBkTCCATigAwIBAgIUTestSmokeCertNotForRealUseAtAllAA0wDQYJKoZIhvcN
-----END CERTIFICATE-----
EOF
rc="$(run_validate --non-interactive --control-plane panel.smoke.test --grpc-port 62051 --node-name smoke-node-01 --cert-mode file --cert-file "${PEM_FILE}" --dry-run)"
[[ "${rc}" == "0" ]] || fail "happy path should exit 0; got ${rc}"

pass "argument validation correctly accepts/rejects each flag combo"

# ---------------------------------------------------------------------------
# 6. compose file references the env vars install-node.sh writes.
# ---------------------------------------------------------------------------
echo "[smoke] T6: docker-compose.yml references AEGIS_VERSION + GRPC_PORT + NODE_NAME"
[[ -r "${COMPOSE_YML}" ]] || fail "docker-compose.yml not readable"
grep -q 'AEGIS_VERSION' "${COMPOSE_YML}" || fail "compose missing AEGIS_VERSION reference"
grep -q 'GRPC_PORT'     "${COMPOSE_YML}" || fail "compose missing GRPC_PORT reference"
grep -q 'NODE_NAME'     "${COMPOSE_YML}" || fail "compose missing NODE_NAME reference"
pass "compose references the rendered env vars"

# ---------------------------------------------------------------------------
# 7. .env.example mentions every var the renderer writes.
# ---------------------------------------------------------------------------
echo "[smoke] T7: .env.example contains all rendered keys"
[[ -r "${ENV_EXAMPLE}" ]] || fail ".env.example not readable"
for key in AEGIS_VERSION CONTROL_PLANE_URL GRPC_PORT NODE_NAME CERT_PATH; do
  grep -qE "^${key}=" "${ENV_EXAMPLE}" || fail ".env.example missing ${key}="
done
pass ".env.example contains all rendered keys"

echo
echo "all tests passed"
