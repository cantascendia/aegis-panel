#!/usr/bin/env bash
# agpl-selfcheck.sh — Aegis Panel AGPL-3.0 compliance one-shot verifier.
#
# Differentiation #4 per docs/ai-cto/SPEC-deploy.md (S-D D.4): Aegis makes
# AGPL-3.0 §13 source-disclosure compliance one-command verifiable. Operators
# run this after deploy to confirm their installation correctly exposes a way
# for users to obtain the modified source code.
#
# Standalone deliverable. install.sh / OPS-deploy-runbook.md will wire it in
# later. No state, idempotent, reentrant.
#
# Exit codes:
#   0 — all checks pass
#   1 — missing source-code disclosure link (UI + /api/system/info both fail)
#   2 — NOTICE.md missing or upstream attribution stripped
#   3 — upstream copyright notice removed from app/ source files
#   4 — panel unreachable (HTTP checks skipped, fail loud)
#
# License: AGPL-3.0-or-later (see ../../LICENSE, ../../NOTICE.md).

set -euo pipefail

# -----------------------------------------------------------------------------
# Defaults & flags
# -----------------------------------------------------------------------------
SCRIPT_NAME="$(basename "$0")"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

PANEL_URL=""
CI_MODE=0

usage() {
    cat <<EOF
Usage: ${SCRIPT_NAME} [--url <panel-url>] [--ci] [--help]

AGPL-3.0 compliance self-check for Aegis Panel deployments.

Options:
  --url <url>   Panel base URL to probe (e.g. https://panel.example.com).
                Default: \$BILLING_PUBLIC_BASE_URL from <repo>/.env, else
                http://127.0.0.1:\${UVICORN_PORT:-8000}.
  --ci          Suppress human-readable output; rely on exit code only.
  -h, --help    Show this help and exit.

Checks (all run; first non-zero category determines exit code):
  1. Panel reachable at <url>/                         (else exit 4)
  2. Source-code disclosure link present
        either GET / HTML contains the canonical fork URL
        or     GET /api/system/info JSON has source_code_url
                                                       (else exit 1)
  3. NOTICE.md exists in repo root with upstream
     Marzneshin attribution intact                     (else exit 2)
  4. No upstream copyright header has been stripped
     from app/ Python sources                          (else exit 3)
  5. Best-effort: docker compose images look FOSS
     (warns only; never changes exit code)

Exit codes:
  0  pass    1  missing source link    2  NOTICE issue
  3  stripped copyright    4  panel unreachable
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --url)    PANEL_URL="${2:-}"; shift 2 ;;
        --ci)     CI_MODE=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "${SCRIPT_NAME}: unknown argument: $1" >&2; usage >&2; exit 64 ;;
    esac
done

# -----------------------------------------------------------------------------
# Output helpers — silent in --ci, verbose otherwise.
# -----------------------------------------------------------------------------
log()   { [[ ${CI_MODE} -eq 1 ]] || printf '%s\n' "$*"; }
pass()  { [[ ${CI_MODE} -eq 1 ]] || printf '  [PASS] %s\n' "$*"; }
fail()  { [[ ${CI_MODE} -eq 1 ]] || printf '  [FAIL] %s\n' "$*" >&2; }
warn()  { [[ ${CI_MODE} -eq 1 ]] || printf '  [WARN] %s\n' "$*"; }
header(){ [[ ${CI_MODE} -eq 1 ]] || printf '\n=== %s ===\n' "$*"; }

# -----------------------------------------------------------------------------
# Resolve panel URL — flag wins, then .env BILLING_PUBLIC_BASE_URL, then local
# fallback. Strips trailing slash for predictable concatenation.
# -----------------------------------------------------------------------------
resolve_panel_url() {
    if [[ -n "${PANEL_URL}" ]]; then
        :
    elif [[ -f "${REPO_ROOT}/.env" ]] && grep -qE '^BILLING_PUBLIC_BASE_URL=' "${REPO_ROOT}/.env"; then
        PANEL_URL="$(grep -E '^BILLING_PUBLIC_BASE_URL=' "${REPO_ROOT}/.env" \
            | head -n1 | cut -d= -f2- | tr -d '"' | tr -d "'")"
    else
        local port="8000"
        if [[ -f "${REPO_ROOT}/.env" ]] && grep -qE '^UVICORN_PORT=' "${REPO_ROOT}/.env"; then
            port="$(grep -E '^UVICORN_PORT=' "${REPO_ROOT}/.env" \
                | head -n1 | cut -d= -f2- | tr -d '"' | tr -d "'")"
        fi
        PANEL_URL="http://127.0.0.1:${port}"
    fi
    PANEL_URL="${PANEL_URL%/}"
}

# -----------------------------------------------------------------------------
# Source the canonical fork URL from NOTICE.md (no hard-coding). The header
# block lists "https://github.com/<org>/<repo>" lines; we pick the first
# non-upstream GitHub URL. If none found, fall back to the documented default.
# -----------------------------------------------------------------------------
canonical_source_url() {
    local default="https://github.com/cantascendia/aegis-panel"
    [[ -f "${REPO_ROOT}/NOTICE.md" ]] || { echo "${default}"; return; }
    # Prefer an explicit "Source:" or "Fork:" line if NOTICE.md ever adds one.
    local from_notice
    from_notice="$(grep -Eo 'https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+' \
        "${REPO_ROOT}/NOTICE.md" \
        | grep -viE 'marzneshin|gozargah|marzban' \
        | head -n1 || true)"
    if [[ -n "${from_notice}" ]]; then
        echo "${from_notice}"
    else
        echo "${default}"
    fi
}

# -----------------------------------------------------------------------------
# Check 1 — panel reachable. Exit 4 on miss; everything downstream is moot.
# -----------------------------------------------------------------------------
check_reachable() {
    header "1/5 panel reachability"
    local code
    code="$(curl -fsS -o /dev/null -w '%{http_code}' --max-time 10 \
        "${PANEL_URL}/" 2>/dev/null || true)"
    # Marzneshin redirects unauthenticated / to the dashboard route, so 200,
    # 301, 302, 307, 308 all count as reachable.
    case "${code}" in
        2??|3??) pass "panel responds at ${PANEL_URL} (HTTP ${code})"; return 0 ;;
        *)       fail "panel unreachable at ${PANEL_URL} (HTTP ${code:-no-response})"; return 4 ;;
    esac
}

# -----------------------------------------------------------------------------
# Check 2 — source-code disclosure link.
#   path A: GET / HTML contains the canonical fork URL literal
#   path B: GET /api/system/info JSON has a non-empty source_code_url field
# -----------------------------------------------------------------------------
check_source_link() {
    header "2/5 source-code disclosure link (AGPL-3.0 §13)"
    local fork_url; fork_url="$(canonical_source_url)"
    log "  canonical fork URL: ${fork_url}"

    # Path A — HTML root
    local body
    body="$(curl -fsSL --max-time 10 "${PANEL_URL}/" 2>/dev/null || true)"
    if [[ -n "${body}" ]] && printf '%s' "${body}" | grep -qF "${fork_url}"; then
        pass "GET / HTML contains canonical fork URL"
        return 0
    fi

    # Path B — /api/system/info JSON
    local info
    info="$(curl -fsS --max-time 10 "${PANEL_URL}/api/system/info" 2>/dev/null || true)"
    if [[ -n "${info}" ]]; then
        if command -v jq >/dev/null 2>&1; then
            local url_field
            url_field="$(printf '%s' "${info}" | jq -r '.source_code_url // empty' 2>/dev/null || true)"
            if [[ -n "${url_field}" && "${url_field}" != "null" ]]; then
                pass "/api/system/info exposes source_code_url=${url_field}"
                return 0
            fi
        else
            # jq absent — best-effort grep for the field. Tolerates whitespace.
            if printf '%s' "${info}" | grep -qE '"source_code_url"[[:space:]]*:[[:space:]]*"https?://'; then
                pass "/api/system/info exposes source_code_url (grep fallback; install jq for strict parsing)"
                return 0
            fi
        fi
    fi

    fail "no source-code disclosure link found in GET / nor /api/system/info"
    fail "  remediation: add a GitHub link to dashboard footer, OR expose source_code_url in /api/system/info"
    return 1
}

# -----------------------------------------------------------------------------
# Check 3 — NOTICE.md exists with upstream attribution intact. SPEC-deploy.md
# §合规一键自检 explicitly grep "Marzneshin" in NOTICE.md.
# -----------------------------------------------------------------------------
check_notice() {
    header "3/5 NOTICE.md upstream attribution"
    local notice="${REPO_ROOT}/NOTICE.md"
    if [[ ! -f "${notice}" ]]; then
        fail "NOTICE.md missing at repo root (${notice})"
        return 2
    fi
    if ! grep -qE '(Forked from|Marzneshin)' "${notice}"; then
        fail "NOTICE.md exists but upstream attribution stripped (expected 'Forked from' or 'Marzneshin')"
        return 2
    fi
    pass "NOTICE.md present and upstream attribution intact"
    return 0
}

# -----------------------------------------------------------------------------
# Check 4 — upstream copyright not stripped from app/ Python sources.
# Heuristic: any .py file with an explicit "removed copyright" marker fails.
# We do NOT require headers in every file (AGPL-3.0 doesn't either) — we just
# refuse known stripping markers a sloppy contributor might leave behind.
# -----------------------------------------------------------------------------
check_copyright_headers() {
    header "4/5 upstream copyright preservation in app/"
    local appdir="${REPO_ROOT}/app"
    if [[ ! -d "${appdir}" ]]; then
        warn "app/ directory absent — skipping copyright scan"
        return 0
    fi
    local hits
    # Patterns that imply someone deliberately removed an attribution line.
    hits="$(grep -RIlEn \
        -e '#[[:space:]]*(removed|stripped)[[:space:]]+(upstream[[:space:]]+)?(copyright|notice|attribution)' \
        -e '#[[:space:]]*(copyright|notice)[[:space:]]+removed' \
        --include='*.py' \
        "${appdir}" 2>/dev/null || true)"
    if [[ -n "${hits}" ]]; then
        fail "found stripped-copyright markers in app/:"
        printf '%s\n' "${hits}" | sed 's/^/      /' >&2
        return 3
    fi
    pass "no stripped-copyright markers found in app/*.py"
    return 0
}

# -----------------------------------------------------------------------------
# Check 5 — best-effort docker image scan. Never fails the run; just warns
# operators who might be pulling unexpected images. Skipped if docker missing.
# -----------------------------------------------------------------------------
check_docker_images() {
    header "5/5 docker image FOSS sanity (advisory)"
    if ! command -v docker >/dev/null 2>&1; then
        warn "docker not installed — skipping image scan"
        return 0
    fi
    local compose_out
    compose_out="$(cd "${REPO_ROOT}" && docker compose config 2>/dev/null \
        | grep -E '^\s*image:' || true)"
    if [[ -z "${compose_out}" ]]; then
        warn "no docker compose images resolvable — skipping"
        return 0
    fi
    log "  resolved images:"
    printf '%s\n' "${compose_out}" | sed 's/^/      /'
    # Heuristic blocklist of known proprietary registries. Extend as needed.
    if printf '%s' "${compose_out}" | grep -qiE '(mcr\.microsoft\.com/(sql|mssql)|oracle/database|ibmcom)'; then
        warn "proprietary image detected — review license obligations"
    else
        pass "no obvious proprietary images"
    fi
    return 0
}

# -----------------------------------------------------------------------------
# Main — run all checks; report the FIRST non-zero category as exit code so
# operators get the most actionable signal. Always run every check so the
# output covers everything in one pass (idempotent + complete).
# -----------------------------------------------------------------------------
main() {
    resolve_panel_url
    log "Aegis Panel AGPL-3.0 self-check"
    log "  repo:  ${REPO_ROOT}"
    log "  panel: ${PANEL_URL}"

    local exit_code=0
    local rc=0

    check_reachable || rc=$?
    if [[ ${rc} -eq 4 ]]; then
        # Panel down — the network checks below would all fail spuriously.
        # Still run filesystem checks (NOTICE / copyright) since they don't
        # need the panel and operators want one report covering everything.
        exit_code=4
        check_notice            || { [[ ${exit_code} -eq 0 ]] && exit_code=$?; }
        check_copyright_headers || { [[ ${exit_code} -eq 0 ]] && exit_code=$?; }
        check_docker_images     || true
        header "result"
        log "FAIL — panel unreachable; remaining HTTP checks skipped (exit ${exit_code})"
        return ${exit_code}
    fi

    rc=0; check_source_link        || rc=$?; [[ ${exit_code} -eq 0 ]] && exit_code=${rc}
    rc=0; check_notice             || rc=$?; [[ ${exit_code} -eq 0 ]] && exit_code=${rc}
    rc=0; check_copyright_headers  || rc=$?; [[ ${exit_code} -eq 0 ]] && exit_code=${rc}
    check_docker_images || true

    header "result"
    if [[ ${exit_code} -eq 0 ]]; then
        log "PASS — AGPL-3.0 compliance self-check clean"
    else
        log "FAIL — exit ${exit_code} (see [FAIL] lines above)"
    fi
    return ${exit_code}
}

main "$@"
