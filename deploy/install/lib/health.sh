#!/usr/bin/env bash
# deploy/install/lib/health.sh — panel readiness polling.
#
# Sourced by install.sh step 7. Polls the panel system info endpoint until
# 200 or timeout. On timeout, dumps the last 50 lines of `docker compose
# logs` for the panel service to stderr and returns 3 (matches install.sh
# exit code 3 = healthcheck timeout).
#
# Refs: SPEC-deploy.md §"install.sh 职责(D.1)" step 7 + exit code contract.

set -euo pipefail
IFS=$'\n\t'

# ---------------------------------------------------------------------------
# wait_for_panel_health PORT [TIMEOUT_SECONDS]
#   Default timeout 120s, poll interval 2s.
# ---------------------------------------------------------------------------
wait_for_panel_health() {
  local port="${1:-8443}"
  local timeout="${2:-120}"
  local interval=2
  local elapsed=0
  # /api/system/info doesn't exist on Marzneshin upstream — first real
  # deploy 2026-04-30 found this 404s. /openapi.json is FastAPI auto,
  # present on every upstream version (codex review P1 on commit fb33c57:
  # the compose healthcheck was switched but this poller missed the
  # update). Both must agree or step 7 times out while Docker thinks
  # the panel is healthy.
  local url="http://127.0.0.1:${port}/openapi.json"

  echo "[health] waiting for ${url} (timeout=${timeout}s)" >&2

  while (( elapsed < timeout )); do
    # We don't care about the JSON body here, only the HTTP status. -f makes
    # curl exit non-zero on >=400, which is what we want.
    if curl -fsS --max-time 3 -o /dev/null "${url}" 2>/dev/null; then
      echo "[health] panel ready after ${elapsed}s" >&2
      return 0
    fi
    sleep "${interval}"
    elapsed=$(( elapsed + interval ))
  done

  echo "[health] FATAL: panel did not become healthy within ${timeout}s" >&2
  return 3
}

# ---------------------------------------------------------------------------
# dump_compose_tail COMPOSE_FILE [SERVICE] [LINES]
#   Last N lines of `docker compose logs` for SERVICE (default: panel).
# ---------------------------------------------------------------------------
dump_compose_tail() {
  local compose_file="$1"
  local service="${2:-panel}"
  local lines="${3:-50}"
  if ! command -v docker >/dev/null 2>&1; then
    echo "[health] docker not on PATH — cannot dump logs" >&2
    return 0
  fi
  echo "[health] --- last ${lines} lines of docker compose logs ${service} ---" >&2
  docker compose -f "${compose_file}" logs --tail="${lines}" "${service}" >&2 2>&1 || true
  echo "[health] --- end log tail ---" >&2
}
