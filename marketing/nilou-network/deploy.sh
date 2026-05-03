#!/usr/bin/env bash
# One-command deploy of nilou.network landing to Cloudflare Pages.
#
# Prerequisites:
#   1. Cloudflare account (you already have one)
#   2. Node.js installed (any LTS)
#   3. First-time only: `npx wrangler login` (opens browser, OAuth)
#
# Usage:
#   bash marketing/nilou-network/deploy.sh
#
# What this does:
#   - Runs `wrangler pages deploy` from repo root
#   - Targets project name "nilou-network" (creates if missing)
#   - Deploys files in marketing/nilou-network/ verbatim (static, no build)
#   - Returns the *.pages.dev preview URL
#   - Custom domain (nilou.network) bound separately via dashboard once

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="nilou-network"

cd "$SCRIPT_DIR"

echo "[deploy] Deploying $SCRIPT_DIR to Cloudflare Pages project '$PROJECT_NAME'..."

if ! command -v npx >/dev/null 2>&1; then
  echo "[deploy] ERROR: npx not found. Install Node.js: https://nodejs.org/" >&2
  exit 1
fi

# Use the directory itself as the deploy root.
npx --yes wrangler@latest pages deploy . \
  --project-name="$PROJECT_NAME" \
  --branch=main \
  --commit-dirty=true

echo ""
echo "[deploy] ✓ Deployed."
echo "[deploy] Preview URL: https://$PROJECT_NAME.pages.dev"
echo "[deploy] Custom domain: bind nilou.network via Cloudflare dashboard → Pages → Custom domains."
