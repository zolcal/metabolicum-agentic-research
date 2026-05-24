#!/usr/bin/env bash
# run-acceptance.sh — Run the Stage 2 acceptance test harness.
#
# Usage:
#   ./scripts/run-acceptance.sh [--runs N] [--fixture <id>]
#
# This invokes the Python acceptance harness (code/acceptance/run_acceptance.py)
# which exercises the 10 criteria from hermes-setup.md §3.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR/.."
cd "$PROJECT_ROOT"

RUNS="${1:-1}"
FIXTURE="${2:-apob-peter-attia-source}"

echo "══════════════════════════════════════════════════════════════"
echo "  Metabolicum Acceptance Test — Stage 2 Pipeline"
echo "  Fixture: $FIXTURE"
echo "  Runs: $RUNS"
echo "  $(date -Iseconds)"
echo "══════════════════════════════════════════════════════════════"
echo ""

# Ensure dependencies
VENV_PYTHON="$PROJECT_ROOT/vendor/hermes-agent-v2026.5.16/.venv/bin/python"
if [[ ! -f "$VENV_PYTHON" ]]; then
    echo "ERROR: Hermes venv not found"
    exit 1
fi

# Install test deps if missing
$VENV_PYTHON -c "import openai, jsonschema" 2>/dev/null || {
    echo "Installing test dependencies..."
    UV_NO_CONFIG=1 "$PROJECT_ROOT/vendor/hermes-agent-v2026.5.16/.venv/bin/pip" install openai jsonschema 2>/dev/null || true
}

# Run acceptance
FIXTURE_PATH="$PROJECT_ROOT/fixtures/sources/${FIXTURE}.json"
if [[ ! -f "$FIXTURE_PATH" ]]; then
    echo "ERROR: Fixture not found: $FIXTURE_PATH"
    exit 1
fi

exec "$VENV_PYTHON" code/acceptance/run_acceptance.py \
    --runs "$RUNS" \
    --fixture "$FIXTURE_PATH"
