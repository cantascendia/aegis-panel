#!/usr/bin/env bash
# install-tunnel.sh — provision a Cloudflare Tunnel for an Aegis Panel instance.
#
# Implements deploy/cloudflare/ §"install-tunnel.sh" of docs/ai-cto/SPEC-deploy.md
# (D.4). Five steps, all idempotent on re-run:
#   1. Verify CF_API_TOKEN scopes (Tunnel:Edit + DNS:Edit + Access:Edit).
#   2. cloudflared tunnel create aegis-<instance>  (skips if exists).
#   3. Render /etc/cloudflared/config.yml from the template.
#   4. Upsert DNS CNAME PANEL_DOMAIN -> <uuid>.cfargotunnel.com via CF API.
#   5. Install + enable cloudflared.service via systemd.
#
# Operational rationale: hides origin IP behind CF Anycast (compass artifact
# §"CF Tunnel"), defends against L4 reflection, prerequisite for Access policy
# enforcement (setup-access.sh).
#
# Exit codes:
#   0 — success
#   2 — missing prerequisite tool (cloudflared, curl, jq, envsubst)
#   3 — invalid arguments
#   4 — CF_API_TOKEN unset or token verify failed
#   5 — required token scope missing (AC-D.4.5)
#   6 — DNS / Tunnel API call failed
#   7 — systemd unavailable (cannot install service)
#
# License: AGPL-3.0-or-later. Aegis Panel is a hard fork of Marzneshin
# (https://github.com/marzneshin/marzneshin). See NOTICE.md.

set -euo pipefail
IFS=$'\n\t'

SCRIPT_NAME="$(basename "$0")"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# -----------------------------------------------------------------------------
# Defaults
# -----------------------------------------------------------------------------
PANEL_DOMAIN=""
PANEL_PORT="${PANEL_PORT:-8443}"
TUNNEL_NAME=""
INSTANCE="$(hostname -s 2>/dev/null || echo aegis)"
CONFIG_DIR="/etc/cloudflared"
CRED_DIR="/etc/cloudflared"
DRY_RUN=0
SKIP_SYSTEMD=0

CF_API="https://api.cloudflare.com/client/v4"
REQUIRED_SCOPES=(
  "com.cloudflare.api.account.cfd_tunnel"            # Tunnel:Edit
  "com.cloudflare.api.account.zone.dns_records"      # Zone DNS:Edit
  "com.cloudflare.api.account.access"                # Access apps/policies:Edit
)

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
log()   { printf '[%s] %s\n' "$SCRIPT_NAME" "$*" >&2; }
die()   { printf '[%s] ERROR: %s\n' "$SCRIPT_NAME" "$*" >&2; exit "${2:-1}"; }
need()  { command -v "$1" >/dev/null 2>&1 || die "missing required tool: $1" 2; }

usage() {
  cat <<EOF
Usage: $SCRIPT_NAME --domain <fqdn> [options]

Provision a Cloudflare Tunnel routing PANEL_DOMAIN to localhost:PANEL_PORT.

Required:
  --domain <fqdn>          Public hostname for the panel (must own the zone).

Options:
  --instance <name>        Tunnel suffix (default: \$(hostname -s) -> aegis-<host>).
  --panel-port <port>      Local panel HTTP port (default: 8443 / env PANEL_PORT).
  --config-dir <path>      Where to write config.yml (default: /etc/cloudflared).
  --cred-dir <path>        Where cloudflared stores <uuid>.json (default: /etc/cloudflared).
  --skip-systemd           Render config but do not install systemd unit.
  --dry-run                Print intended API calls + commands; fire nothing.
  -h, --help               Show this help and exit 0.

Environment:
  CF_API_TOKEN             REQUIRED at runtime. Scopes: Tunnel:Edit + DNS:Edit
                           + Access:Edit (see deploy/cloudflare/README.md for
                           the full minimal-scope table). Token is read from
                           env only — never written to disk by this script.

Exit codes: 0 ok | 2 missing tool | 3 bad args | 4 token invalid
            5 missing scope | 6 API failure | 7 systemd unavailable
EOF
}

# -----------------------------------------------------------------------------
# Argument parsing
# -----------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --domain)        PANEL_DOMAIN="${2:-}"; shift 2 ;;
    --instance)      INSTANCE="${2:-}"; shift 2 ;;
    --panel-port)    PANEL_PORT="${2:-}"; shift 2 ;;
    --config-dir)    CONFIG_DIR="${2:-}"; shift 2 ;;
    --cred-dir)      CRED_DIR="${2:-}"; shift 2 ;;
    --skip-systemd)  SKIP_SYSTEMD=1; shift ;;
    --dry-run)       DRY_RUN=1; shift ;;
    -h|--help)       usage; exit 0 ;;
    *) die "unknown argument: $1 (try --help)" 3 ;;
  esac
done

[[ -n "$PANEL_DOMAIN" ]] || { usage; die "--domain is required" 3; }
TUNNEL_NAME="aegis-${INSTANCE}"

# -----------------------------------------------------------------------------
# Step 0 — preflight: tools + token + scopes
# -----------------------------------------------------------------------------
need curl
need jq
need envsubst
[[ "$DRY_RUN" -eq 1 ]] || need cloudflared

[[ -n "${CF_API_TOKEN:-}" ]] || die "CF_API_TOKEN env var not set; export it before running" 4

cf_api() {
  local method="$1" path="$2" body="${3:-}"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    log "DRY-RUN: ${method} ${CF_API}${path} ${body:+(body=$body)}"
    echo '{"success":true,"result":[],"result_info":{}}'
    return 0
  fi
  local args=(-sS -X "$method" -H "Authorization: Bearer ${CF_API_TOKEN}" \
              -H "Content-Type: application/json" "${CF_API}${path}")
  [[ -n "$body" ]] && args+=(--data "$body")
  curl "${args[@]}"
}

log "Verifying CF_API_TOKEN..."
verify_resp="$(cf_api GET /user/tokens/verify)"
if [[ "$DRY_RUN" -eq 0 ]]; then
  ok="$(echo "$verify_resp" | jq -r '.success // false')"
  [[ "$ok" == "true" ]] || die "token verify failed: $verify_resp" 4

  # Enumerate token policies and resolve scopes. We accept tokens whose
  # permission_groups names contain the keywords below — CF returns symbolic
  # ids that vary by account, so substring matching the human name is the
  # most stable check we can do without an additional permissions endpoint.
  scopes_json="$(echo "$verify_resp" | jq -c '.result // {}')"
  missing=()
  for kw in "Cloudflare Tunnel:Edit" "DNS:Edit" "Access: Apps and Policies:Edit"; do
    if ! echo "$scopes_json" | jq -e --arg kw "$kw" '
          (.. | objects | select(.name? != null) | .name) | select(contains($kw))
        ' >/dev/null 2>&1; then
      missing+=("$kw")
    fi
  done
  if [[ ${#missing[@]} -gt 0 ]]; then
    log "Token is missing required scopes:"
    for s in "${missing[@]}"; do log "  - $s"; done
    log "See deploy/cloudflare/README.md §'Token scopes' for the full table."
    exit 5
  fi
fi
log "Token OK."

# -----------------------------------------------------------------------------
# Step 1 — create tunnel (idempotent: if name exists, reuse UUID)
# -----------------------------------------------------------------------------
log "Ensuring tunnel ${TUNNEL_NAME} exists..."
if [[ "$DRY_RUN" -eq 1 ]]; then
  log "DRY-RUN: cloudflared tunnel create ${TUNNEL_NAME}"
  TUNNEL_UUID="00000000-0000-0000-0000-000000000000"
  CRED_FILE="${CRED_DIR}/${TUNNEL_UUID}.json"
else
  if existing="$(cloudflared tunnel list -o json 2>/dev/null | jq -r --arg n "$TUNNEL_NAME" '.[] | select(.name==$n) | .id' || true)"; then :; fi
  if [[ -n "${existing:-}" ]]; then
    TUNNEL_UUID="$existing"
    log "Tunnel ${TUNNEL_NAME} already exists (uuid=${TUNNEL_UUID}), reusing."
  else
    create_out="$(cloudflared tunnel create "$TUNNEL_NAME" 2>&1)" || die "tunnel create failed: $create_out" 6
    TUNNEL_UUID="$(echo "$create_out" | grep -oE '[0-9a-f-]{36}' | head -n1)"
    [[ -n "$TUNNEL_UUID" ]] || die "could not extract tunnel UUID from cloudflared output" 6
  fi
  CRED_FILE="$(find "$HOME/.cloudflared" "$CRED_DIR" -maxdepth 2 -name "${TUNNEL_UUID}.json" 2>/dev/null | head -n1)"
  [[ -n "$CRED_FILE" ]] || die "credentials file ${TUNNEL_UUID}.json not found under ~/.cloudflared or ${CRED_DIR}" 6
fi
log "Tunnel UUID: ${TUNNEL_UUID}"

# -----------------------------------------------------------------------------
# Step 2 — render config.yml from template
# -----------------------------------------------------------------------------
TEMPLATE="${SCRIPT_DIR}/cloudflared.config.yml.template"
[[ -f "$TEMPLATE" ]] || die "template not found: $TEMPLATE" 2

OUT_CONFIG="${CONFIG_DIR}/config.yml"
log "Rendering ${OUT_CONFIG}..."
if [[ "$DRY_RUN" -eq 1 ]]; then
  log "DRY-RUN: would write ${OUT_CONFIG} (TUNNEL_UUID + PANEL_DOMAIN substituted)"
else
  mkdir -p "$CONFIG_DIR"
  TUNNEL_UUID="$TUNNEL_UUID" TUNNEL_NAME="$TUNNEL_NAME" \
  PANEL_DOMAIN="$PANEL_DOMAIN" PANEL_PORT="$PANEL_PORT" CRED_FILE="$CRED_FILE" \
    envsubst '${TUNNEL_UUID} ${TUNNEL_NAME} ${PANEL_DOMAIN} ${PANEL_PORT} ${CRED_FILE}' \
    < "$TEMPLATE" > "$OUT_CONFIG"
  chmod 0644 "$OUT_CONFIG"
fi

# -----------------------------------------------------------------------------
# Step 3 — DNS CNAME upsert
# -----------------------------------------------------------------------------
log "Resolving zone for ${PANEL_DOMAIN}..."
ZONE_NAME="$(echo "$PANEL_DOMAIN" | awk -F. '{n=NF; print $(n-1)"."$n}')"
zone_resp="$(cf_api GET "/zones?name=${ZONE_NAME}")"
ZONE_ID="$(echo "$zone_resp" | jq -r '.result[0].id // empty')"
[[ -n "${ZONE_ID:-}" || "$DRY_RUN" -eq 1 ]] || die "zone ${ZONE_NAME} not found in this CF account" 6

CNAME_TARGET="${TUNNEL_UUID}.cfargotunnel.com"
log "Upserting CNAME ${PANEL_DOMAIN} -> ${CNAME_TARGET} (zone=${ZONE_ID:-DRY_RUN})..."

if [[ "$DRY_RUN" -eq 0 ]]; then
  existing_rec="$(cf_api GET "/zones/${ZONE_ID}/dns_records?type=CNAME&name=${PANEL_DOMAIN}")"
  rec_id="$(echo "$existing_rec" | jq -r '.result[0].id // empty')"
  payload="$(jq -nc --arg n "$PANEL_DOMAIN" --arg c "$CNAME_TARGET" \
              '{type:"CNAME",name:$n,content:$c,proxied:true,ttl:1}')"
  if [[ -n "$rec_id" ]]; then
    cf_api PUT "/zones/${ZONE_ID}/dns_records/${rec_id}" "$payload" >/dev/null \
      || die "DNS update failed" 6
  else
    cf_api POST "/zones/${ZONE_ID}/dns_records" "$payload" >/dev/null \
      || die "DNS create failed" 6
  fi
fi

# -----------------------------------------------------------------------------
# Step 4 — systemd service
# -----------------------------------------------------------------------------
if [[ "$SKIP_SYSTEMD" -eq 1 ]]; then
  log "Skipping systemd install (--skip-systemd)."
elif [[ "$DRY_RUN" -eq 1 ]]; then
  log "DRY-RUN: would run cloudflared service install --config ${OUT_CONFIG}"
else
  command -v systemctl >/dev/null 2>&1 || die "systemctl not found; rerun with --skip-systemd" 7
  log "Installing cloudflared systemd unit..."
  cloudflared --config "$OUT_CONFIG" service install >/dev/null 2>&1 || true
  systemctl enable --now cloudflared.service
fi

log "Done. Verify: dig +short ${PANEL_DOMAIN} (expect CF anycast IPs only)."
log "Next: deploy/cloudflare/setup-access.sh --domain ${PANEL_DOMAIN} --emails ops@example.com"
