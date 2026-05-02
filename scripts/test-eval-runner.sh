#!/usr/bin/env bash
# scripts/test-eval-runner.sh — local self-test for scripts/eval-runner.sh
#
# Verifies enforce-mode behavior (audit P4, 2026-05-02):
#   - Real evals/ dirs (5 P0 + 5 regression) → exit 0
#   - Synthetic broken yaml (missing acceptance_criteria) → exit 1
#   - Synthetic empty dir → exit 0 (no yamls = no failures)
#
# Run:    bash scripts/test-eval-runner.sh
# Exit:   0 = all assertions pass, 1 = at least one assertion failed
#
# Not run by CI (would require dual-running the workflow). Exists for
# manual verification + future regression coverage.
set -u

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUNNER="$REPO_ROOT/scripts/eval-runner.sh"
PASS=0
FAIL=0

assert_exit() {
  local desc="$1"
  local expected="$2"
  local actual="$3"
  if [ "$expected" = "$actual" ]; then
    echo "  PASS: $desc (exit=$actual)"
    PASS=$((PASS + 1))
  else
    echo "  FAIL: $desc (expected exit=$expected, got=$actual)"
    FAIL=$((FAIL + 1))
  fi
}

echo "== test-eval-runner =="

# Test 1: real golden-trajectories should pass (5 P0)
set +e
bash "$RUNNER" "$REPO_ROOT/evals/golden-trajectories" >/dev/null 2>&1
STATUS=$?
set -e
assert_exit "real evals/golden-trajectories → exit 0" 0 "$STATUS"

# Test 2: real regression should pass (5 P0 incl. 006-eval-gate-enforce)
set +e
bash "$RUNNER" "$REPO_ROOT/evals/regression" >/dev/null 2>&1
STATUS=$?
set -e
assert_exit "real evals/regression → exit 0" 0 "$STATUS"

# Test 3: synthetic broken yaml (missing acceptance_criteria) → exit 1
TMP_BROKEN=$(mktemp -d)
trap "rm -rf '$TMP_BROKEN'" EXIT
cat > "$TMP_BROKEN/999-broken.yaml" <<'EOF'
id: 999-broken
description: synthetic test fixture missing acceptance_criteria
input: "test"
expected_steps:
  - step1
forbidden_actions:
  - none
priority: P2
EOF
set +e
bash "$RUNNER" "$TMP_BROKEN" >/dev/null 2>&1
STATUS=$?
set -e
assert_exit "synthetic broken yaml (missing field) → exit 1" 1 "$STATUS"

# Test 4: empty dir (no yamls at all) → exit 0
TMP_EMPTY=$(mktemp -d)
set +e
bash "$RUNNER" "$TMP_EMPTY" >/dev/null 2>&1
STATUS=$?
set -e
rm -rf "$TMP_EMPTY"
assert_exit "empty dir (no yamls) → exit 0" 0 "$STATUS"

# Test 5: missing dir → exit 2 (per script ERROR path)
set +e
bash "$RUNNER" "/tmp/definitely-not-a-real-dir-$$" >/dev/null 2>&1
STATUS=$?
set -e
assert_exit "missing dir → exit 2" 2 "$STATUS"

echo ""
echo "Summary: $PASS pass, $FAIL fail"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
