#!/bin/bash
#
# check_translations.sh — locale JSON drift gate
#
# Locale: grep -P (PCRE) requires a UTF-8 locale. CI (ubuntu-latest)
# defaults to C.UTF-8; some local Windows bashes default to plain C
# and silently return zero matches. Force UTF-8 up top to be safe.
export LANG=C.UTF-8
export LC_ALL=C.UTF-8
#
#
# Two modes:
#
# 1) Strict mode (default, backward-compatible):
#      bash tools/check_translations.sh <locale.json>
#    Fails if the locale file has any missing or extra keys vs the
#    dashboard's current `t("...")` calls.
#
# 2) Diff-based mode (added Round 2, LESSONS L-012 real fix):
#      bash tools/check_translations.sh \
#        --base-source <dir>  --base-json <file>  <locale.json>
#    Computes drift on both base (<dir> + <file>) and head (cwd +
#    <locale.json>). Fails only if HEAD drift > BASE drift. This
#    lets the repo's long-standing pre-existing drift coexist with
#    normal development: a PR can't make it worse, but doesn't have
#    to fix it either. When a "parity cleanup" PR finally lands,
#    drift drops to 0 and the strict mode can be re-enabled.
#
# Exit codes:
#   0 — check passed
#   1 — check failed (missing/extra in strict mode, or drift
#       increased in diff mode)
#   2 — usage error

set -u

die() { echo "error: $*" >&2; exit 2; }

usage() {
    cat >&2 <<EOF
Usage:
  $0 <locale.json>                            # strict mode
  $0 --base-source <dir> --base-json <file> <locale.json>   # diff mode
EOF
    exit 2
}

# -----------------------------------------------------------------
# Argument parsing
# -----------------------------------------------------------------
BASE_SOURCE=""
BASE_JSON=""
HEAD_JSON=""

while [ $# -gt 0 ]; do
    case "$1" in
        --base-source)
            [ $# -ge 2 ] || die "--base-source requires a value"
            BASE_SOURCE="$2"
            shift 2
            ;;
        --base-json)
            [ $# -ge 2 ] || die "--base-json requires a value"
            BASE_JSON="$2"
            shift 2
            ;;
        --help|-h)
            usage
            ;;
        -*)
            die "unknown option: $1"
            ;;
        *)
            if [ -z "$HEAD_JSON" ]; then
                HEAD_JSON="$1"
            else
                die "unexpected extra positional argument: $1"
            fi
            shift
            ;;
    esac
done

[ -n "$HEAD_JSON" ] || usage

if [ -n "$BASE_SOURCE" ] && [ -z "$BASE_JSON" ]; then
    die "--base-source requires --base-json"
fi
if [ -n "$BASE_JSON" ] && [ -z "$BASE_SOURCE" ]; then
    die "--base-json requires --base-source"
fi

DIFF_MODE=0
if [ -n "$BASE_SOURCE" ]; then
    DIFF_MODE=1
fi

# -----------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------
jq_pathify() {
    local key="$1"
    local jq_path=""
    IFS='.' read -ra parts <<< "$key"
    for part in "${parts[@]}"; do
        if [[ "$part" =~ ^[a-zA-Z0-9_]+$ ]]; then
            jq_path+=".${part}"
        else
            jq_path+="[\"$part\"]"
        fi
    done
    echo "$jq_path"
}

# extract_t_keys <dashboard_root>  -> writes sorted unique t() keys
# to stdout. Looks into <root>/dashboard. If <root> itself ends in
# "dashboard" we adjust — but CI callers always pass the repo root.
extract_t_keys() {
    local root="$1"
    if [ -d "$root/dashboard" ]; then
        root="$root/dashboard"
    fi
    grep --exclude-dir={node_modules,dist} -orPh \
        "\Wt\([\"']\K[\w.-]+(?=[\"'])" "$root" \
        | sort | uniq
}

# compute_drift <tkeys_file> <json_file>
# Echoes "<missing> <extra> <verbose-report-path>" (space-separated).
# Missing = source has t("foo") but json lacks it.
# Extra   = json has "foo" but source has no t("foo") for it.
compute_drift() {
    local tkeys="$1"
    local json="$2"
    local report
    report=$(mktemp)
    local missing=0
    local extra=0

    if [ ! -f "$json" ]; then
        echo "0 0 $report"
        return
    fi

    # Missing: source keys absent in json.
    while IFS= read -r key; do
        [ -z "$key" ] && continue
        local q
        q=$(jq_pathify "$key")
        if [[ "$q" != .* ]]; then
            q=".$q"
        fi
        if ! jq -e "$q // empty" "$json" > /dev/null 2>&1; then
            echo "missing: $key" >> "$report"
            missing=$((missing + 1))
        fi
    done < "$tkeys"

    # Extra: json paths not in source tkeys.
    local json_paths
    json_paths=$(mktemp)
    jq -r 'paths(scalars) | join(".")' "$json" 2>/dev/null | sort -u > "$json_paths"

    while IFS= read -r line; do
        [ -z "$line" ] && continue
        if ! grep -qxF "$line" "$tkeys"; then
            echo "extra: $line" >> "$report"
            extra=$((extra + 1))
        fi
    done < "$json_paths"

    rm -f "$json_paths"
    echo "$missing $extra $report"
}

# -----------------------------------------------------------------
# Mode dispatch
# -----------------------------------------------------------------
if [ "$DIFF_MODE" -eq 0 ]; then
    # Strict mode (legacy).
    tkeys=$(mktemp)
    extract_t_keys "." > "$tkeys"

    read -r miss extra report <<<"$(compute_drift "$tkeys" "$HEAD_JSON")"

    # Print findings for log context (backward-compatible shape).
    if [ -f "$report" ] && [ -s "$report" ]; then
        while IFS= read -r line; do
            case "$line" in
                missing:*) echo "translation lacks ${line#missing: }" ;;
                extra:*)   echo "found extra key ${line#extra: }" ;;
            esac
        done < "$report"
    fi
    rm -f "$report" "$tkeys"

    if [ "$miss" -gt 0 ] || [ "$extra" -gt 0 ]; then
        echo "Check failed. missing keys: $miss, extra keys: $extra"
        exit 1
    fi
    echo "Check passed. No extra/missing keys."
    exit 0
fi

# Diff mode.
# Guard inputs.
[ -d "$BASE_SOURCE" ] || die "--base-source dir does not exist: $BASE_SOURCE"
[ -f "$BASE_JSON" ]   || die "--base-json file does not exist: $BASE_JSON"
[ -f "$HEAD_JSON" ]   || die "head json does not exist: $HEAD_JSON"

base_tkeys=$(mktemp)
head_tkeys=$(mktemp)
extract_t_keys "$BASE_SOURCE" > "$base_tkeys"
extract_t_keys "."            > "$head_tkeys"

read -r base_miss base_extra base_report <<<"$(compute_drift "$base_tkeys" "$BASE_JSON")"
read -r head_miss head_extra head_report <<<"$(compute_drift "$head_tkeys" "$HEAD_JSON")"

base_drift=$((base_miss + base_extra))
head_drift=$((head_miss + head_extra))

echo "Base (${BASE_JSON}): missing=$base_miss extra=$base_extra drift=$base_drift"
echo "Head (${HEAD_JSON}): missing=$head_miss extra=$head_extra drift=$head_drift"

if [ "$head_drift" -gt "$base_drift" ]; then
    delta=$((head_drift - base_drift))
    echo "::error::PR increases locale drift by $delta for ${HEAD_JSON}"
    echo "------ new-in-head (not in base) --------------------------------"
    # Show only entries present in head_report but not base_report so
    # reviewers see exactly what this PR introduced.
    comm -23 <(sort -u "$head_report") <(sort -u "$base_report") || true
    echo "-----------------------------------------------------------------"
    rm -f "$base_tkeys" "$head_tkeys" "$base_report" "$head_report"
    exit 1
fi

if [ "$head_drift" -lt "$base_drift" ]; then
    echo "Nice: drift dropped from $base_drift to $head_drift (fixed $((base_drift - head_drift)) stale keys)"
fi
echo "Diff-gate passed: drift did not increase ($base_drift -> $head_drift)."

rm -f "$base_tkeys" "$head_tkeys" "$base_report" "$head_report"
exit 0
