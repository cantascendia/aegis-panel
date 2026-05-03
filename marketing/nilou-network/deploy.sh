#!/usr/bin/env bash
# Deploy nilou.network static files to Cloudflare Pages.
#
# Prerequisites:
#   1. Cloudflare account access.
#   2. Wrangler CLI already installed and authenticated.
#
# Usage:
#   bash marketing/nilou-network/deploy.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="nilou-network"

cd "$SCRIPT_DIR"

if ! command -v wrangler >/dev/null 2>&1; then
  echo "[deploy] ERROR: wrangler CLI is not available in PATH." >&2
  echo "[deploy] This static site has no package install step; provide wrangler outside this directory." >&2
  exit 1
fi

echo "[deploy] Deploying static files from $SCRIPT_DIR to Cloudflare Pages project '$PROJECT_NAME'..."

wrangler pages deploy . \
  --project-name="$PROJECT_NAME" \
  --branch=main \
  --commit-dirty=true

echo ""
echo "[deploy] Deployed."
echo "[deploy] Preview URL: https://$PROJECT_NAME.pages.dev"
