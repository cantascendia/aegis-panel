#!/usr/bin/env bash
# 给本仓库装 git pre-commit hook，让终端 git commit 也触发 §48 codex review
# 用途：用户不通过 Claude Code（如 PowerShell / IDE）commit 时，Stop hook 不会触发，
# pre-commit hook 是额外的入口。
#
# 用法：
#   bash scripts/install-pre-commit.sh
#
# 卸载：
#   rm .git/hooks/pre-commit

set -e

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
[ -z "$REPO_ROOT" ] && { echo "Not in a git repo"; exit 1; }
cd "$REPO_ROOT"

HOOK=".git/hooks/pre-commit"

if [ -f "$HOOK" ]; then
  echo "⚠️  $HOOK 已存在。备份到 ${HOOK}.bak"
  cp "$HOOK" "${HOOK}.bak"
fi

cat > "$HOOK" <<'EOF'
#!/usr/bin/env bash
# §48 codex-bridge pre-commit trigger + skills-sync drift check
set -e

# 1. Skills drift check (blocking — exit 1 阻断 commit)
SYNC_CHECK="scripts/check-skills-sync.sh"
if [ -x "$SYNC_CHECK" ]; then
  if ! bash "$SYNC_CHECK"; then
    echo ""
    echo "pre-commit blocked: skills drift detected (see above)."
    echo "Override with: git commit --no-verify  (only if you know what you're doing)"
    exit 1
  fi
fi

# 2. §48 codex-bridge — 异步后台跑，不阻塞 commit
RUN_SH=".agents/skills/codex-bridge/run.sh"
if [ -x "$RUN_SH" ]; then
  ( bash "$RUN_SH" HEAD &> /dev/null & disown 2>/dev/null ) || true
fi

exit 0
EOF
chmod +x "$HOOK"

echo "✓ git pre-commit hook 已安装到 $HOOK"
echo ""
echo "下次 git commit 时（无论通过 Claude Code 还是终端），"
echo "都会异步触发 codex-bridge review，结果写入 docs/ai-cto/REVIEW-QUEUE.md"
echo ""
echo "卸载：rm $HOOK"
