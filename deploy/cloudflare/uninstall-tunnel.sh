#!/usr/bin/env bash
# uninstall-tunnel.sh — tear down the Cloudflare Tunnel + Access + DNS for
# an Aegis Panel instance. Required by L-022 emergency rollback (see
# docs/ai-cto/SPEC-deploy.md AC-D.4.3).
#
# Order matters: Access app first (must not 502 users mid-session), then DNS
# (so users immediately fall through), then tunnel (so cloudflared releases
# the routing slot). Local config is removed last.
#
# Idempotent: missing resources are skipped, not fatal.
#
# Exit codes:
#   0 — success (or already absent)
#   2 — missing prerequisite tool (curl, jq)
#   3 — invalid arguments
#   4 — CF_API_TOKEN unset
#
# License: AGPL-3.0-or-later. Aegis Panel is a hard fork of Marzneshin
# (https://github.com/marzneshin/marzneshin). See NOTICE.md.

set -euo pipefail
IFS=$'\n\t'

SCRIPT_NAME="$(basename "$0")"

PANEL_DOMAIN=""
INSTANCE="$(hostname -s 2>/dev/null || echo aegis)"
TUNNEL_NAME=""
APP_NAME=""
DRY_RUN=0
KEEP_CONFIG=0

CF_API="https://api.cloudflare.com/client/v4"

log()  { printf '[%s] %s\n' "$SCRIPT_NAME" "$*" >&2; }
die()  { printf '[%s] ERROR: %s\n' "$SCRIPT_NAME" "$*" >&2; exit "${2:-1}"; }
need() { command -v "$1" >/dev/null 2>&1 || die "missing required tool: $1" 2; }

usage() {
  cat <<EOF
Usage: $SCRIPT_NAME --domain <fqdn> [options]

Remove the Cloudflare Tunnel, Access application, and DNS CNAME created by
install-tunnel.sh / setup-access.sh. Safe to re-run; missing pieces skipped.

Required:
  --domain <fqdn>          Panel hostname previously installed.

Options:
  --instance <name>        Tunnel suffix (default: \$(hostname -s)).
  --app-name <name>        Access app to delete (default: aegis-panel-<domain>).
  --keep-config            Do not remove /etc/cloudflared/config.yml.
  --dry-run                Print intended deletions; fire nothing.
  -h, --help               Show this help and exit 0.

Environment:
  CF_API_TOKEN             REQUIRED. Same scopes as install-tunnel.sh.
  CF_ACCOUNT_ID            Optional; auto-resolved when one account is bound.

Exit codes: 0 ok | 2 missing tool | 3 bad args | 4 token unset
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --domain)       PANEL_DOMAIN="${2:-}"; shift 2 ;;
    --instance)     INSTANCE="${2:-}"; shift 2 ;;
    --app-name)     APP_NAME="${2:-}"; shift 2 ;;
    --keep-config)  KEEP_CONFIG=1; shift ;;
    --dry-run)      DRY_RUN=1; shift ;;
    -h|--help)      usage; exit 0 ;;
    *) die "unknown argument: $1 (try --help)" 3 ;;
  esac
done

[[ -n "$PANEL_DOMAIN" ]] || { usage; die "--domain is required" 3; }
TUNNEL_NAME="aegis-${INSTANCE}"
[[ -n "$APP_NAME" ]] || APP_NAME="aegis-panel-${PANEL_DOMAIN//./-}"

need curl
need jq
[[ -n "${CF_API_TOKEN:-}" ]] || die "CF_API_TOKEN env var not set" 4

cf_api() {
  local method="$1" path="$2"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    log "DRY-RUN: ${method} ${CF_API}${path}"
    echo '{"success":true,"result":[]}'
    return 0
  fi
  curl -sS -X "$method" -H "Authorization: Bearer ${CF_API_TOKEN}" \
       -H "Content-Type: application/json" "${CF_API}${path}"
}

# Resolve account id (best-effort).
if [[ -z "${CF_ACCOUNT_ID:-}" ]]; then
  ar="$(cf_api GET /accounts)"
  CF_ACCOUNT_ID="$(echo "$ar" | jq -r '.result[0].id // empty')"
  [[ -n "$CF_ACCOUNT_ID" || "$DRY_RUN" -eq 1 ]] || log "warning: could not resolve CF_ACCOUNT_ID; Access cleanup may be skipped"
fi

# -----------------------------------------------------------------------------
# 1. Access app + policies
# -----------------------------------------------------------------------------
if [[ -n "${CF_ACCOUNT_ID:-}" ]]; then
  log "Removing Access app '${APP_NAME}'..."
  apps="$(cf_api GET "/accounts/${CF_ACCOUNT_ID}/access/apps")"
  app_id="$(echo "$apps" | jq -r --arg n "$APP_NAME" '.result[] | select(.name==$n) | .id' | head -n1)"
  if [[ -n "$app_id" ]]; then
    cf_api DELETE "/accounts/${CF_ACCOUNT_ID}/access/apps/${app_id}" >/dev/null \
      && log "  deleted app id=${app_id}" \
      || log "  app delete returned non-zero; continuing"
  else
    log "  no app named '${APP_NAME}' found, skipping."
  fi
fi

# -----------------------------------------------------------------------------
# 2. DNS CNAME
# -----------------------------------------------------------------------------
ZONE_NAME="$(echo "$PANEL_DOMAIN" | awk -F. '{n=NF; print $(n-1)"."$n}')"
log "Resolving zone for ${ZONE_NAME}..."
zr="$(cf_api GET "/zones?name=${ZONE_NAME}")"
ZONE_ID="$(echo "$zr" | jq -r '.result[0].id // empty')"
if [[ -n "$ZONE_ID" ]]; then
  log "Removing CNAME ${PANEL_DOMAIN}..."
  recs="$(cf_api GET "/zones/${ZONE_ID}/dns_records?type=CNAME&name=${PANEL_DOMAIN}")"
  rec_id="$(echo "$recs" | jq -r '.result[0].id // empty')"
  if [[ -n "$rec_id" ]]; then
    cf_api DELETE "/zones/${ZONE_ID}/dns_records/${rec_id}" >/dev/null \
      && log "  deleted record id=${rec_id}" \
      || log "  DNS delete returned non-zero; continuing"
  else
    log "  no CNAME for ${PANEL_DOMAIN}, skipping."
  fi
else
  log "  zone not found, skipping DNS step."
fi

# -----------------------------------------------------------------------------
# 3. Tunnel — clean route then delete
# -----------------------------------------------------------------------------
if command -v cloudflared >/dev/null 2>&1 && [[ "$DRY_RUN" -eq 0 ]]; then
  log "Stopping cloudflared.service..."
  systemctl disable --now cloudflared.service >/dev/null 2>&1 || true

  uuid="$(cloudflared tunnel list -o json 2>/dev/null \
            | jq -r --arg n "$TUNNEL_NAME" '.[] | select(.name==$n) | .id' || true)"
  if [[ -n "${uuid:-}" ]]; then
    log "Deleting tunnel ${TUNNEL_NAME} (uuid=${uuid})..."
    cloudflared tunnel cleanup "$TUNNEL_NAME" >/dev/null 2>&1 || true
    cloudflared tunnel delete -f "$TUNNEL_NAME" >/dev/null 2>&1 \
      || log "  tunnel delete returned non-zero; check 'cloudflared tunnel list'"
  else
    log "  no tunnel named ${TUNNEL_NAME}, skipping."
  fi
else
  log "DRY-RUN or cloudflared absent — skipping tunnel delete."
fi

# -----------------------------------------------------------------------------
# 4. Local config
# -----------------------------------------------------------------------------
if [[ "$KEEP_CONFIG" -eq 0 && "$DRY_RUN" -eq 0 ]]; then
  rm -f /etc/cloudflared/config.yml
  log "Removed /etc/cloudflared/config.yml (--keep-config to retain)."
fi

log "Done. Verify: dig ${PANEL_DOMAIN} returns NXDOMAIN or origin record only."
