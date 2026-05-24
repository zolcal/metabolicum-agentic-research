#!/usr/bin/env bash
# init-pipeline.sh — Initialize the metabolicum research pipeline Kanban and verify setup.
#
# Usage:
#   ./scripts/init-pipeline.sh
#
# This script:
#   1. Runs the preflight checks
#   2. Switches to the metabolicum Kanban board
#   3. Verifies Hermes is properly configured
#   4. Shows current board status

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR/.."
cd "$PROJECT_ROOT"

HERMES="$PROJECT_ROOT/run-hermes"

echo "══════════════════════════════════════════════════════════════"
echo "  Metabolicum Agentic Research — Pipeline Initialization"
echo "  $(date -Iseconds)"
echo "══════════════════════════════════════════════════════════════"
echo ""

# ─── Preflight ────────────────────────────────────────────────────────────

echo "─── Running preflight checks ───"
if ./scripts/preflight.sh; then
    echo ""
    echo "✓ Preflight passed"
else
    echo ""
    echo "✗ Preflight failed — fix issues before continuing"
    exit 1
fi

echo ""

# ─── Hermes version ───────────────────────────────────────────────────────

echo "─── Hermes version ───"
$HERMES --version
echo ""

# ─── Kanban board ─────────────────────────────────────────────────────────

echo "─── Kanban board ───"
$HERMES kanban boards switch metabolicum-agentic-research 2>/dev/null || true
BOARD_LIST=$($HERMES kanban boards list 2>&1)
echo "$BOARD_LIST"
echo ""

# ─── Board status ─────────────────────────────────────────────────────────

echo "─── Current tasks ───"
$HERMES kanban list 2>/dev/null || echo "(no tasks yet)"
echo ""

# ─── Summary ──────────────────────────────────────────────────────────────

echo "══════════════════════════════════════════════════════════════"
echo "  Pipeline initialized and ready"
echo "══════════════════════════════════════════════════════════════"
echo ""
echo "Next steps:"
echo "  1. Enqueue a task:    ./scripts/enqueue-source.sh <source_id> <marker>"
echo "  2. Start a worker:    ./scripts/run-worker.sh"
echo "  3. Open Hermes CLI:   ./run-hermes"
echo "  4. Run acceptance:    ./scripts/run-acceptance.sh"
echo ""
