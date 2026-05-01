#!/usr/bin/env bash
# scripts/aegis-create-trial-batch.sh — generate batch SSH commands to create trial users.
#
# Operator UX helper. Generates a copy-pastable shell block for the VPS
# that creates N trial users via aegis-user CLI, then collects their
# subscription URLs.
#
# Does NOT execute over SSH itself — operator must paste output into
# their VPS shell. This keeps secrets (SSH keys, panel tokens) on
# operator's machine, not in repo or in a logged session.
#
# Usage:
#   bash scripts/aegis-create-trial-batch.sh [--count N] [--prefix STR] [--note STR]
#
# Defaults:
#   --count 5
#   --prefix test
#   --note "trial / 安卓+PC / $(date +%Y-%m-%d)"
#
# Examples:
#   # 5 users named test01..test05
#   bash scripts/aegis-create-trial-batch.sh
#
#   # 3 users named demo01..demo03 with custom note
#   bash scripts/aegis-create-trial-batch.sh --count 3 --prefix demo --note "demo / friends"
#
# Output: bash block to paste into SSH session on the VPS.
#
# After running on VPS, operator gets one subscription URL per user;
# distribute via WeChat / Telegram with the customer onboarding template
# (see docs/launch/CUSTOMER-ONBOARDING.md §4).
#
# Idempotency: each `aegis-user create` is idempotent at the CLI layer
# (rejects duplicate username with non-zero exit). Re-running this batch
# is safe — existing usernames will fail individually, others succeed.

set -e

COUNT=5
PREFIX="test"
NOTE_DEFAULT="trial / 安卓+PC / $(date +%Y-%m-%d)"
NOTE="$NOTE_DEFAULT"
PLAN="trial"

while [ $# -gt 0 ]; do
  case "$1" in
    --count)  COUNT="$2"; shift 2 ;;
    --prefix) PREFIX="$2"; shift 2 ;;
    --note)   NOTE="$2"; shift 2 ;;
    --plan)   PLAN="$2"; shift 2 ;;
    --help|-h)
      sed -n '1,40p' "$0" | sed 's/^# //; s/^#//'
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      echo "Usage: $0 [--count N] [--prefix STR] [--note STR] [--plan trial|m1|q1|y1]" >&2
      exit 2
      ;;
  esac
done

# Validate
case "$COUNT" in ''|*[!0-9]*) echo "Error: --count must be a positive integer" >&2; exit 2 ;; esac
if [ "$COUNT" -lt 1 ] || [ "$COUNT" -gt 99 ]; then
  echo "Error: --count must be 1..99 (got $COUNT)" >&2
  exit 2
fi
case "$PREFIX" in *[!a-zA-Z0-9_-]*)
  echo "Error: --prefix must be [a-zA-Z0-9_-]+ (panel constraint, no spaces / Chinese)" >&2
  exit 2 ;;
esac
case "$PLAN" in
  trial|m1|q1|y1) ;;
  *) echo "Error: --plan must be one of: trial, m1, q1, y1" >&2; exit 2 ;;
esac

# Generate
cat <<EOF
# ─────────────────────────────────────────────────────────────────────
# Aegis trial batch — paste into your VPS SSH session
# Generated: $(date -Iseconds 2>/dev/null || date)
# Plan: $PLAN | Count: $COUNT | Prefix: $PREFIX
# Note: $NOTE
# ─────────────────────────────────────────────────────────────────────

set -e

# ${COUNT} users; aegis-user CLI handles duplicate-name as non-fatal per-user
EOF

i=1
while [ "$i" -le "$COUNT" ]; do
  USERNAME=$(printf '%s%02d' "$PREFIX" "$i")
  cat <<EOF
echo "── Creating ${USERNAME} ──"
aegis-user create "${USERNAME}" "${PLAN}" --note "${NOTE}" || echo "(skip ${USERNAME}: already exists or aegis-user CLI errored)"
EOF
  i=$((i + 1))
done

cat <<EOF

# ─────────────────────────────────────────────────────────────────────
# Collect subscription URLs (paste below after the create block)
# ─────────────────────────────────────────────────────────────────────

PREFIX="${PREFIX}"
COUNT=${COUNT}

echo
echo "── Subscription URLs ──"
for u in \$(seq -f "\${PREFIX}%02g" 1 \${COUNT}); do
  # aegis-user show prints subscription URL (panel API call under the hood)
  if command -v aegis-user >/dev/null 2>&1; then
    URL=\$(aegis-user show "\$u" 2>/dev/null | grep -E "^Subscription URL:" | awk '{print \$3}')
    [ -n "\$URL" ] && echo "\$u: \$URL" || echo "\$u: (creation failed or aegis-user show unsupported)"
  else
    echo "(aegis-user CLI not in PATH; check /usr/local/bin/aegis-user)"
    break
  fi
done

# ─────────────────────────────────────────────────────────────────────
# Next: copy URLs into your customer-onboarding workflow.
#   - docs/launch/CUSTOMER-ONBOARDING.md §4 has client-import template
#   - One sub URL works on Android + PC simultaneously (IPLIMIT off by default)
# ─────────────────────────────────────────────────────────────────────
EOF
