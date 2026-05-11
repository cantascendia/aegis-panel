#!/usr/bin/env bash
# cost-cap-check.sh — 周度 cost cap 校验（PreToolUse hook 调用）
# 设计：count tool_call × 估算单价 vs AEGIS_WEEKLY_COST_CAP
# 出口码：0 = 允许，2 = 阻塞（Claude Code 把 PreToolUse exit 2 当作 deny）
# 依赖：.claude/agent-logs/YYYY-MM-DD.jsonl（已存在）
# 文档：手册 §43 reliability + CLAUDE.md「成本封顶」章节
# 哲学：cheap insurance — 默认 $50/wk + $0.05/call 约 1000 call/wk 余量，
#       runaway loop（如 PR #245 那样）单日 4000 call 必触发
set +e

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
[ -z "$REPO_ROOT" ] && exit 0
LOG_DIR="$REPO_ROOT/.claude/agent-logs"
[ ! -d "$LOG_DIR" ] && exit 0

# Configurable via env
WEEKLY_CAP_USD="${AEGIS_WEEKLY_COST_CAP:-50}"
PER_CALL_USD="${AEGIS_COST_PER_CALL_USD:-0.05}"
HARD_FLOOR="${AEGIS_COST_BYPASS:-0}"

# Bypass switch（紧急放行；操作员手动 export AEGIS_COST_BYPASS=1）
[ "$HARD_FLOOR" = "1" ] && exit 0

# Compute "current week" = ISO week start (Mon)
# 跨 Git Bash / mac / linux 兼容：用 date -d 在前 0..6 天回退到周一
TODAY=$(date +%Y-%m-%d 2>/dev/null)
[ -z "$TODAY" ] && exit 0

# day-of-week: Sun=0..Sat=6（GNU date %w）。Mon=1，回退 (dow-1) 天到周一；周日回退 6。
DOW=$(date +%w 2>/dev/null || echo 1)
case "$DOW" in
  0) OFFSET=6 ;;
  1) OFFSET=0 ;;
  2) OFFSET=1 ;;
  3) OFFSET=2 ;;
  4) OFFSET=3 ;;
  5) OFFSET=4 ;;
  6) OFFSET=5 ;;
  *) OFFSET=0 ;;
esac

# 聚合本周 tool_call 计数（从周一到今天）
TOTAL=0
i=0
while [ "$i" -le "$OFFSET" ]; do
  DAY=$(date -d "$TODAY -$i day" +%Y-%m-%d 2>/dev/null)
  if [ -z "$DAY" ]; then
    # BSD date fallback
    DAY=$(date -v-"$i"d -j -f %Y-%m-%d "$TODAY" +%Y-%m-%d 2>/dev/null)
  fi
  if [ -n "$DAY" ] && [ -f "$LOG_DIR/$DAY.jsonl" ]; then
    COUNT=$(grep -c '"type":"tool_call"' "$LOG_DIR/$DAY.jsonl" 2>/dev/null || echo 0)
    TOTAL=$((TOTAL + COUNT))
  fi
  i=$((i + 1))
done

# 估算成本 (USD)
# awk 跨平台浮点（dash/zsh 不支持原生浮点）
EST_USD=$(awk -v c="$TOTAL" -v r="$PER_CALL_USD" 'BEGIN{printf "%.2f", c*r}')

# 比较：用 awk（POSIX 浮点）
OVER=$(awk -v e="$EST_USD" -v cap="$WEEKLY_CAP_USD" 'BEGIN{print (e+0 > cap+0) ? 1 : 0}')

if [ "$OVER" = "1" ]; then
  # 写入审计日志（与 codex-bridge 共用 CODEX-REVIEW-LOG.md 不合适，独立一份）
  AUDIT_LOG="$REPO_ROOT/docs/ai-cto/COST-CAP-LOG.md"
  mkdir -p "$REPO_ROOT/docs/ai-cto"
  TS=$(date -Iseconds 2>/dev/null || date)
  printf "%s | week_calls=%s | est_usd=%s | cap=%s | mode=BLOCKED\n" \
    "$TS" "$TOTAL" "$EST_USD" "$WEEKLY_CAP_USD" >> "$AUDIT_LOG" 2>/dev/null

  # stderr 给 Claude Code 看 + 阻塞
  cat >&2 <<EOF
🛑 §43 成本封顶触发（铁律 #反 silent-failure）

本周累计 tool_call: ${TOTAL} 次
估算消耗: \$${EST_USD} USD
本周上限: \$${WEEKLY_CAP_USD} USD（AEGIS_WEEKLY_COST_CAP）

——————————————————————————————————————
此 tool 调用已被阻塞。可选项：

1️⃣ 等到下周一自动重置（推荐）
2️⃣ 临时提升上限：
   PowerShell:  \$env:AEGIS_WEEKLY_COST_CAP="100"
   Bash:        export AEGIS_WEEKLY_COST_CAP=100
3️⃣ 紧急放行单 session（不推荐）：
   export AEGIS_COST_BYPASS=1
4️⃣ 调整单价估值（如已切换至 Haiku）：
   export AEGIS_COST_PER_CALL_USD=0.01

审计日志: docs/ai-cto/COST-CAP-LOG.md
配置文档: CLAUDE.md「成本封顶」章节
EOF
  exit 2
fi

exit 0
