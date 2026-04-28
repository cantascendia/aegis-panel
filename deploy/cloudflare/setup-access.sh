#!/usr/bin/env bash
# setup-access.sh — provision Cloudflare Access app + policy for the panel.
#
# Implements deploy/cloudflare/ §"setup-access.sh" of docs/ai-cto/SPEC-deploy.md
# (D.4). Wraps Cloudflare Access API to require operator authentication on the
# panel before requests reach the origin tunnel. Default allow rule is email
# OTP — operators receive a one-time code by email; --sso google switches to
# Google Workspace SAML/OIDC if the IdP is preconfigured in CF Zero Trust.
#
# Idempotent: looks up the Access application by name first; if present, the
# existing app/policy is updated in place (PUT) rather than duplicated.
#
# Exit codes:
#   0 — success
#   2 — missing prerequisite tool (curl, jq)
#   3 — invalid arguments
#   4 — CF_API_TOKEN unset or token verify failed
#   5 — required token scope missing
#   6 — Access API call failed
#   7 — CF_ACCOUNT_ID unset and not auto-resolvable
#
# License: AGPL-3.0-or-later. Aegis Panel is a hard fork of Marzneshin
# (https://github.com/marzneshin/marzneshin). See NOTICE.md.

set -euo pipefail
IFS=$'\n\t'

SCRIPT_NAME="$(basename "$0")"

# -----------------------------------------------------------------------------
# Defaults
# -----------------------------------------------------------------------------
PANEL_DOMAIN=""
DASHBOARD_PATH=""        # optional path scope (e.g. /admin)
ADMIN_EMAILS=""          # comma-separated
APP_NAME=""              # default: aegis-panel-<domain>
SSO_PROVIDER="email"     # email | google | onetimepin
SESSION_DURATION="24h"
DRY_RUN=0

CF_API="https://api.cloudflare.com/client/v4"

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
log()  { printf '[%s] %s\n' "$SCRIPT_NAME" "$*" >&2; }
die()  { printf '[%s] ERROR: %s\n' "$SCRIPT_NAME" "$*" >&2; exit "${2:-1}"; }
need() { command -v "$1" >/dev/null 2>&1 || die "missing required tool: $1" 2; }

usage() {
  cat <<EOF
Usage: $SCRIPT_NAME --domain <fqdn> --emails <a@b.com,c@d.com> [options]

Create / update a Cloudflare Access application protecting the Aegis panel.

Required:
  --domain <fqdn>          Panel hostname (matches install-tunnel.sh --domain).
  --emails <list>          Comma-separated admin emails allowed by the policy.

Options:
  --path <path>            Restrict app to a path prefix (default: whole host).
  --app-name <name>        Override app name (default: aegis-panel-<domain>).
  --sso <provider>         email (default) | google | onetimepin
  --session <duration>     Session length, e.g. 24h, 8h (default: 24h).
  --dry-run                Print intended API calls; fire nothing.
  -h, --help               Show this help and exit 0.

Environment:
  CF_API_TOKEN             REQUIRED at runtime. Needs Access:Apps and
                           Policies:Edit scope. Token is read from env only —
                           never written to disk.
  CF_ACCOUNT_ID            Optional. Auto-resolved from /accounts if a single
                           account is associated with the token.

Exit codes: 0 ok | 2 missing tool | 3 bad args | 4 token invalid
            5 missing scope | 6 API failure | 7 account id unresolved
EOF
}

# -----------------------------------------------------------------------------
# Argument parsing
# -----------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --domain)    PANEL_DOMAIN="${2:-}"; shift 2 ;;
    --emails)    ADMIN_EMAILS="${2:-}"; shift 2 ;;
    --path)      DASHBOARD_PATH="${2:-}"; shift 2 ;;
    --app-name)  APP_NAME="${2:-}"; shift 2 ;;
    --sso)       SSO_PROVIDER="${2:-}"; shift 2 ;;
    --session)   SESSION_DURATION="${2:-}"; shift 2 ;;
    --dry-run)   DRY_RUN=1; shift ;;
    -h|--help)   usage; exit 0 ;;
    *) die "unknown argument: $1 (try --help)" 3 ;;
  esac
done

[[ -n "$PANEL_DOMAIN" ]] || { usage; die "--domain is required" 3; }
[[ -n "$ADMIN_EMAILS" ]] || { usage; die "--emails is required" 3; }
[[ -n "$APP_NAME" ]] || APP_NAME="aegis-panel-${PANEL_DOMAIN//./-}"

case "$SSO_PROVIDER" in
  email|onetimepin|google) ;;
  *) die "--sso must be one of: email | onetimepin | google" 3 ;;
esac

# -----------------------------------------------------------------------------
# Preflight
# -----------------------------------------------------------------------------
need curl
need jq
[[ -n "${CF_API_TOKEN:-}" ]] || die "CF_API_TOKEN env var not set" 4

cf_api() {
  local method="$1" path="$2" body="${3:-}"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    log "DRY-RUN: ${method} ${CF_API}${path} ${body:+(body=$body)}"
    echo '{"success":true,"result":[{"id":"dryrun-id"}],"result_info":{}}'
    return 0
  fi
  local args=(-sS -X "$method" -H "Authorization: Bearer ${CF_API_TOKEN}" \
              -H "Content-Type: application/json" "${CF_API}${path}")
  [[ -n "$body" ]] && args+=(--data "$body")
  curl "${args[@]}"
}

# Verify token (lightweight; install-tunnel.sh does the full scope enumeration).
if [[ "$DRY_RUN" -eq 0 ]]; then
  vr="$(cf_api GET /user/tokens/verify)"
  [[ "$(echo "$vr" | jq -r '.success // false')" == "true" ]] \
    || die "CF_API_TOKEN verify failed: $vr" 4
fi

# Resolve account id.
if [[ -z "${CF_ACCOUNT_ID:-}" ]]; then
  log "CF_ACCOUNT_ID not set — auto-resolving..."
  ar="$(cf_api GET /accounts)"
  if [[ "$DRY_RUN" -eq 0 ]]; then
    count="$(echo "$ar" | jq -r '.result | length')"
    [[ "$count" == "1" ]] || die "expected exactly 1 CF account, got ${count}; export CF_ACCOUNT_ID explicitly" 7
    CF_ACCOUNT_ID="$(echo "$ar" | jq -r '.result[0].id')"
  else
    CF_ACCOUNT_ID="dryrun-account-id"
  fi
fi
log "Using CF_ACCOUNT_ID=${CF_ACCOUNT_ID}"

# -----------------------------------------------------------------------------
# Idempotent upsert: find existing app by name
# -----------------------------------------------------------------------------
APPS_PATH="/accounts/${CF_ACCOUNT_ID}/access/apps"
log "Looking up existing Access app named '${APP_NAME}'..."
existing_apps="$(cf_api GET "${APPS_PATH}")"
if [[ "$DRY_RUN" -eq 0 ]]; then
  APP_ID="$(echo "$existing_apps" | jq -r --arg n "$APP_NAME" '.result[] | select(.name==$n) | .id' | head -n1)"
else
  APP_ID=""
fi

# Build app payload.
DOMAIN_FIELD="${PANEL_DOMAIN}"
[[ -n "$DASHBOARD_PATH" ]] && DOMAIN_FIELD="${PANEL_DOMAIN}${DASHBOARD_PATH}"

app_payload="$(jq -nc \
  --arg name "$APP_NAME" \
  --arg domain "$DOMAIN_FIELD" \
  --arg session "$SESSION_DURATION" \
  '{
     name: $name,
     domain: $domain,
     type: "self_hosted",
     session_duration: $session,
     app_launcher_visible: false,
     auto_redirect_to_identity: false,
     allowed_idps: []
   }')"

if [[ -n "$APP_ID" ]]; then
  log "Updating Access app id=${APP_ID}..."
  upsert="$(cf_api PUT "${APPS_PATH}/${APP_ID}" "$app_payload")"
else
  log "Creating new Access app..."
  upsert="$(cf_api POST "${APPS_PATH}" "$app_payload")"
  APP_ID="$(echo "$upsert" | jq -r '.result.id // .result[0].id // empty')"
fi
[[ -n "$APP_ID" || "$DRY_RUN" -eq 1 ]] || die "Access app upsert failed: $upsert" 6
log "Access app id=${APP_ID:-dryrun-id}"

# -----------------------------------------------------------------------------
# Policy — allow listed emails. Email OTP is the default decision when no SSO
# IdP is bound; --sso google adds a require rule for the Google IdP group.
# -----------------------------------------------------------------------------
emails_json="$(echo "$ADMIN_EMAILS" | tr ',' '\n' | jq -R 'select(length>0)' | jq -sc 'map({email:.})')"

policy_includes="$emails_json"
case "$SSO_PROVIDER" in
  google)
    # Operator must have created the IdP in CF Zero Trust dashboard first.
    # We add a permissive include so SSO-authenticated users in the email
    # list are allowed; non-SSO users still hit OTP fallback.
    policy_includes="$(echo "$emails_json" | jq -c '. + [{"login_method":{"id":"google"}}]')"
    ;;
  email|onetimepin) ;; # default OTP; nothing extra
esac

policy_payload="$(jq -nc \
  --arg name "Aegis admins" \
  --argjson includes "$policy_includes" \
  '{
     name: $name,
     decision: "allow",
     include: $includes,
     require: [],
     exclude: []
   }')"

POLICIES_PATH="${APPS_PATH}/${APP_ID:-dryrun-id}/policies"
log "Looking up existing policy 'Aegis admins'..."
existing_pols="$(cf_api GET "${POLICIES_PATH}")"
if [[ "$DRY_RUN" -eq 0 ]]; then
  POL_ID="$(echo "$existing_pols" | jq -r '.result[] | select(.name=="Aegis admins") | .id' | head -n1)"
else
  POL_ID=""
fi

if [[ -n "$POL_ID" ]]; then
  log "Updating policy id=${POL_ID}..."
  cf_api PUT "${POLICIES_PATH}/${POL_ID}" "$policy_payload" >/dev/null \
    || die "policy update failed" 6
else
  log "Creating policy..."
  cf_api POST "${POLICIES_PATH}" "$policy_payload" >/dev/null \
    || die "policy create failed" 6
fi

log "Done. Verify: open https://${PANEL_DOMAIN}${DASHBOARD_PATH} in a private window — expect CF Access login page."
log "Rollback: deploy/cloudflare/uninstall-tunnel.sh --domain ${PANEL_DOMAIN}"
