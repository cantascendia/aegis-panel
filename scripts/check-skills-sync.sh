#!/usr/bin/env bash
# scripts/check-skills-sync.sh — 检查 .claude/skills/ 与 .agents/skills/ 双位置同步
# 配合白名单 scripts/skills-intentionally-mono.txt 标注"有意单边" skills。
#
# Exit 0: 双位置同步（忽略白名单单边项）
# Exit 1: 发现非白名单的漂移
#
# 用法：
#   bash scripts/check-skills-sync.sh
#
# 适合作为 pre-commit chain 的一环（见 scripts/install-pre-commit.sh）。

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WHITELIST="$SCRIPT_DIR/skills-intentionally-mono.txt"
CLAUDE_SKILLS_DIR="$REPO_ROOT/.claude/skills"
AGENTS_SKILLS_DIR="$REPO_ROOT/.agents/skills"

# Helpers
list_skills() {
  local dir=$1
  test -d "$dir" || return 0
  ls -1 "$dir" 2>/dev/null | sort
}

is_whitelisted() {
  local skill=$1
  local expected_loc=$2  # "claude-only" or "agents-only"
  test -f "$WHITELIST" || return 1
  grep -E "^${skill}:${expected_loc}\$" "$WHITELIST" > /dev/null 2>&1
}

# Compute sets
CLAUDE_SKILLS=$(list_skills "$CLAUDE_SKILLS_DIR")
AGENTS_SKILLS=$(list_skills "$AGENTS_SKILLS_DIR")

# Symmetric difference (requires sorted input — list_skills sorts)
ONLY_IN_CLAUDE=$(comm -23 <(echo "$CLAUDE_SKILLS") <(echo "$AGENTS_SKILLS"))
ONLY_IN_AGENTS=$(comm -13 <(echo "$CLAUDE_SKILLS") <(echo "$AGENTS_SKILLS"))

EXIT_CODE=0
DRIFT_FOUND=""

# Check claude-only entries
if [ -n "$ONLY_IN_CLAUDE" ]; then
  while IFS= read -r skill; do
    [ -z "$skill" ] && continue
    if is_whitelisted "$skill" "claude-only"; then
      echo "[ok] $skill: claude-only (whitelisted)"
    else
      echo "[drift] $skill: only in .claude/skills/, missing in .agents/skills/"
      DRIFT_FOUND="yes"
      EXIT_CODE=1
    fi
  done <<< "$ONLY_IN_CLAUDE"
fi

# Check agents-only entries
if [ -n "$ONLY_IN_AGENTS" ]; then
  while IFS= read -r skill; do
    [ -z "$skill" ] && continue
    if is_whitelisted "$skill" "agents-only"; then
      echo "[ok] $skill: agents-only (whitelisted)"
    else
      echo "[drift] $skill: only in .agents/skills/, missing in .claude/skills/"
      DRIFT_FOUND="yes"
      EXIT_CODE=1
    fi
  done <<< "$ONLY_IN_AGENTS"
fi

if [ "$DRIFT_FOUND" = "yes" ]; then
  echo ""
  echo "Skills drift detected. Either:"
  echo "  1. cp the missing skill to the other location to sync, or"
  echo "  2. Add an entry to scripts/skills-intentionally-mono.txt if intentional."
  exit 1
fi

echo ""
echo "[ok] All skills synced (or whitelisted as intentionally mono-located)."
exit 0
