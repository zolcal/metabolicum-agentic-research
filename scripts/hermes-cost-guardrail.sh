#!/usr/bin/env bash
# hermes-cost-guardrail.sh — fail-closed cost guardrail for Hermes configs
#
# Usage:
#   ./scripts/hermes-cost-guardrail.sh           # run all checks
#   ./scripts/hermes-cost-guardrail.sh --ci      # terse output for CI
#
# Exit codes:
#   0  all checks passed
#   1  one or more checks failed (expensive model or memory enabled)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

CI_MODE=""
if [[ "${1:-}" == "--ci" ]]; then
    CI_MODE=1
fi

failures=0
err() {
    echo "  ❌ $1" >&2
    ((failures++)) || true
}
ok() {
    if [[ -z "$CI_MODE" ]]; then
        echo "  ✅ $1"
    fi
}

# ── Allowlists ───────────────────────────────────────────────────────────

# Gateway: interactive TUI models only (human-driven chat/CLI).
# gpt-5.5 is allowed HERE ONLY — interactive, negligible cost — and is
# deliberately absent from WORKER_ALLOWLIST so automated workers can't use it.
GATEWAY_ALLOWLIST=(
    "google/gemini-2.5-flash"
    "openai/gpt-5-mini"
    "x-ai/grok-4.1-fast"
    "gpt-5.5"
)

# Worker pin: models used by disposable worker homes
WORKER_ALLOWLIST=(
    "google/gemini-2.5-flash"
    "openai/gpt-5-mini"
    "gemma4-dflash"
    "deepseek-chat"
    "deepseek/deepseek-v4-flash"
)

# ── Helper: check model in allowlist ─────────────────────────────────────

check_model_allowlist() {
    local file="$1"
    local label="$2"
    shift 2
    local allowed=("$@")

    local model
    model="$(grep -A2 '^model:' "$file" | grep 'default:' | sed 's/.*default: *//;s/"//g' | tr -d ' ' || true)"

    if [[ -z "$model" ]]; then
        err "$label: could not parse model.default"
        return
    fi

    for a in "${allowed[@]}"; do
        if [[ "$model" == "$a" ]]; then
            ok "$label model: $model"
            return
        fi
    done

    err "$label model '$model' is NOT in the approved allowlist"
}

# ── Helper: check memory is disabled ─────────────────────────────────────

check_memory_disabled() {
    local file="$1"
    local label="$2"

    local memory_enabled
    memory_enabled="$(grep 'memory_enabled:' "$file" | head -1 | sed 's/.*memory_enabled: *//' | tr -d ' ' || true)"

    if [[ "$memory_enabled" == "false" ]]; then
        ok "$label memory_enabled: false"
    else
        err "$label memory_enabled is '$memory_enabled' (must be false)"
    fi
}

# ── Checks ───────────────────────────────────────────────────────────────

echo "Hermes Cost Guardrail"
echo "====================="
echo ""

# 1. Gateway config
echo "Checking gateway config (hermes/gateway-home/config.yaml)..."
check_model_allowlist "$PROJECT_ROOT/hermes/gateway-home/config.yaml" "Gateway" "${GATEWAY_ALLOWLIST[@]}"
check_memory_disabled "$PROJECT_ROOT/hermes/gateway-home/config.yaml" "Gateway"
echo ""

# 2. Worker pin config
echo "Checking worker pin config (hermes/config.yaml)..."
check_model_allowlist "$PROJECT_ROOT/hermes/config.yaml" "Worker" "${WORKER_ALLOWLIST[@]}"
check_memory_disabled "$PROJECT_ROOT/hermes/config.yaml" "Worker"
echo ""

# 3. llm-endpoints.yaml: no placeholder pricing
echo "Checking llm-endpoints.yaml for placeholder pricing..."
# Look for lines that have both cost_per_million AND placeholder/?? markers
if grep -n 'cost_per_million' "$PROJECT_ROOT/config/llm-endpoints.yaml" | grep -iE 'placeholder|\?\?' >/dev/null 2>&1; then
    err "llm-endpoints.yaml contains placeholder pricing (marked with 'placeholder' or '??')"
else
    ok "llm-endpoints.yaml: no placeholder pricing comments found"
fi
echo ""

# 4. llm-endpoints.yaml: council extractor role assignment
echo "Checking llm-endpoints.yaml council extractor assignment..."
# Find the endpoint whose roles line literally contains [council_extractor]
endpoint_name=""
while IFS= read -r line; do
    if [[ "$line" =~ ^[[:space:]]{2}[a-z0-9-]+:$ ]]; then
        current_ep="$(echo "$line" | sed 's/^  //;s/://')"
    fi
    if [[ "$line" =~ ^[[:space:]]{4}roles:\ \[council_extractor\] ]]; then
        endpoint_name="$current_ep"
        break
    fi
done < "$PROJECT_ROOT/config/llm-endpoints.yaml"

if [[ -n "$endpoint_name" ]]; then
    # Check if that endpoint is active
    if awk -v ep="$endpoint_name" '
        $0 ~ "^  " ep ":" {in_block=1; next}
        in_block && /^  [a-z0-9-]+:/ {in_block=0}
        in_block && /^    active: true/ {found=1}
        END {exit !found}
    ' "$PROJECT_ROOT/config/llm-endpoints.yaml"; then
        ok "llm-endpoints.yaml: council_extractor active on endpoint '$endpoint_name'"
    else
        err "llm-endpoints.yaml: council_extractor endpoint '$endpoint_name' is NOT active"
    fi
else
    err "llm-endpoints.yaml: no endpoint with roles: [council_extractor] found"
fi
echo ""

# ── Summary ──────────────────────────────────────────────────────────────

if [[ $failures -gt 0 ]]; then
    echo ""
    echo "GUARDRAIL FAILED: $failures check(s) failed."
    echo "Do not commit expensive configs. Run 'hermes model' to fix."
    exit 1
else
    echo ""
    echo "GUARDRAIL PASSED: all checks green."
    exit 0
fi
