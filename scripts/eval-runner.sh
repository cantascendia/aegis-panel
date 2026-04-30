#!/usr/bin/env bash
# scripts/eval-runner.sh — local yaml parser, no external API
# Validates evals/<dir>/*.yaml against the required schema (7 fields).
#
# Usage:   bash scripts/eval-runner.sh [target_dir]
# Default: evals/golden-trajectories
#
# Exit 0: all yaml files pass schema validation
# Exit 1: at least one yaml file fails (caller can convert to advisory)
#
# v1: schema-only (field existence). Does NOT invoke Claude / any LLM.
# Used by .github/workflows/eval-gate.yml (advisory mode).
set -e

DIR="${1:-evals/golden-trajectories}"

if [ ! -d "$DIR" ]; then
  echo "ERROR: directory not found: $DIR" >&2
  exit 2
fi

REQUIRED=("id" "description" "input" "expected_steps" "forbidden_actions" "acceptance_criteria" "priority")

PASS=0
FAIL=0
RESULTS=()

shopt -s nullglob
for yaml in "$DIR"/*.yaml; do
  [ -f "$yaml" ] || continue
  ID=$(grep -E '^id:' "$yaml" | head -1 | sed 's/^id:[[:space:]]*//' | tr -d '"' | tr -d "'")
  PRIORITY=$(grep -E '^priority:' "$yaml" | head -1 | sed 's/^priority:[[:space:]]*//' | tr -d '"' | tr -d "'")
  [ -z "$ID" ] && ID="(no-id)"
  [ -z "$PRIORITY" ] && PRIORITY="?"

  MISSING=""
  for field in "${REQUIRED[@]}"; do
    if ! grep -qE "^${field}:" "$yaml"; then
      MISSING="$MISSING $field"
    fi
  done

  if [ -n "$MISSING" ]; then
    RESULTS+=("FAIL|${ID}|${PRIORITY}|missing fields:${MISSING}")
    FAIL=$((FAIL + 1))
  else
    RESULTS+=("PASS|${ID}|${PRIORITY}|")
    PASS=$((PASS + 1))
  fi
done
shopt -u nullglob

echo "## Eval-Gate Results"
echo ""
echo "Target: \`$DIR\`"
echo ""
echo "| ID | Priority | Status |"
echo "|---|---|---|"
for r in "${RESULTS[@]}"; do
  STATUS=$(echo "$r" | cut -d'|' -f1)
  ID=$(echo "$r" | cut -d'|' -f2)
  PRIO=$(echo "$r" | cut -d'|' -f3)
  REASON=$(echo "$r" | cut -d'|' -f4)
  if [ "$STATUS" = "PASS" ]; then
    ICON="✅"
    echo "| \`$ID\` | $PRIO | $ICON PASS |"
  else
    ICON="❌"
    echo "| \`$ID\` | $PRIO | $ICON FAIL — $REASON |"
  fi
done

echo ""
echo "**Summary:** $PASS pass, $FAIL fail"

if [ $FAIL -gt 0 ]; then
  exit 1
fi
exit 0
