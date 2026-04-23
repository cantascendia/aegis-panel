#!/usr/bin/env bash
#
# setup-session-worktrees.sh — 为多 Claude session 并行工作建 git worktree
#
# 背景(强制读一下):docs/ai-cto/SESSIONS.md §铁规则 #7 +
# docs/ai-cto/LESSONS.md L-018。共享一个 working tree 并发开 session
# 会导致 branch 切换撞车、stash 污染、PR 落错分支。worktree 是 git
# 原生的隔离机制。
#
# 用法:
#   # 1) 在主 repo 目录跑(一次性):
#   bash tools/setup-session-worktrees.sh
#
#   # 2) 之后每次开新 Claude session,第一条消息先 cd:
#   cd C:/projects/aegis-B   # S-B session
#   cd C:/projects/aegis-D   # S-D session
#   cd C:/projects/aegis-R   # S-R session
#   cd C:/projects/aegis-X   # S-X session
#
# 幂等:已经存在的 worktree 跳过。删除某个 worktree 用
#   git worktree remove ../aegis-X
#
# 参数:
#   --dry-run   只打印会执行的命令,不真的创建
#   --base <dir> 指定 worktree 根目录(默认 ../aegis-* 即主 repo 的
#               兄弟目录)

set -euo pipefail

DRY_RUN=0
BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PARENT_DIR="$(dirname "$BASE_DIR")"
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) DRY_RUN=1; shift ;;
        --base) PARENT_DIR="$2"; shift 2 ;;
        *) echo "Unknown flag: $1" >&2; exit 2 ;;
    esac
done

echo "Main repo: $BASE_DIR"
echo "Worktrees will be created under: $PARENT_DIR"
echo ""

# 约定的 session 清单。编号 → (目录后缀, 默认分支名, 建议基于)
# 分支名用占位 naming;session 自己第一件事应该 git checkout -b
# 到自己的 feat/* 分支。基础分支都是 main,避免从别人的 WIP 分支
# 引入漂移。
declare -a SESSIONS=(
    "B:billing-backend:feat/billing-session-B-home"
    "D:deploy:docs/session-D-home"
    "R:reality-audit:docs/session-R-home"
    "X:dashboard-tests:feat/session-X-home"
)

run() {
    if [[ $DRY_RUN -eq 1 ]]; then
        echo "  [dry-run] $*"
    else
        echo "  $*"
        eval "$*"
    fi
}

pushd "$BASE_DIR" > /dev/null

# 确保本地 main 最新,worktree 会基于当前 main HEAD
echo "Fetching origin..."
if [[ $DRY_RUN -eq 0 ]]; then
    git fetch origin main > /dev/null 2>&1 || true
fi

for entry in "${SESSIONS[@]}"; do
    IFS=":" read -r letter subdir branch <<< "$entry"
    target="$PARENT_DIR/aegis-$letter"
    echo "=== S-$letter ($subdir) → $target ==="

    if [[ -d "$target" ]]; then
        echo "  [skip] directory already exists"
        continue
    fi

    # 分支可能已经存在(session 之前建过),也可能没有 ——
    # `git worktree add -B` 同时处理两种情况:存在就重置到起点,
    # 不存在就创建。起点固定为 origin/main 以免借别人的 HEAD。
    run "git worktree add -B $branch $target origin/main"
    echo ""
done

popd > /dev/null

echo "Done. 当前 worktree 列表:"
if [[ $DRY_RUN -eq 0 ]]; then
    git -C "$BASE_DIR" worktree list
fi

echo ""
echo "下一步:"
echo "  1) 打开新 Claude session"
echo "  2) 第一条消息粘:cd $PARENT_DIR/aegis-<letter>"
echo "  3) 会话启动 preflight 命令:pwd && git branch --show-current && git status --porcelain"
echo "  4) 让 session 自己 'git checkout -b feat/...' 切到真工作分支"
