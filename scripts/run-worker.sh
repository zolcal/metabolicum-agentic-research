#!/usr/bin/env bash
# run-worker.sh — Start a Kanban worker that processes metabolicum research tasks.
#
# Usage:
#   ./scripts/run-worker.sh [options]
#
# Options:
#   --once       — Process a single task and exit
#   --dry-run    — Show what would be done without executing
#   --profile    — Worker profile name (default: metabolicum-worker)
#
# This worker:
#   1. Claims the next ready task from the Kanban
#   2. Parses stage, source_id, and marker from the task
#   3. Runs ./scripts/run-stage.sh with a disposable HERMES_HOME
#   4. Marks the task complete or failed based on exit code

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR/.."
cd "$PROJECT_ROOT"

HERMES="$PROJECT_ROOT/run-hermes"
PROFILE="${PROFILE:-metabolicum-worker}"
ONCE=false
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --once) ONCE=true; shift ;;
        --dry-run) DRY_RUN=true; shift ;;
        --profile) PROFILE="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

echo "══════════════════════════════════════════════════════════════"
echo "  Metabolicum Agentic Research — Kanban Worker"
echo "  Profile: $PROFILE"
echo "  Mode: $([ "$ONCE" = true ] && echo "single-task" || echo "continuous")"
echo "  $(date -Iseconds)"
echo "══════════════════════════════════════════════════════════════"
echo ""

# Ensure board is selected
$HERMES kanban boards switch metabolicum-agentic-research >/dev/null 2>&1 || true

# ─── Worker loop ──────────────────────────────────────────────────────────

while true; do
    echo "─── Checking for tasks ───"
    
    # List ready tasks
    READY_TASKS=$($HERMES kanban list --status ready 2>/dev/null | head -20)
    if [[ -z "$READY_TASKS" || "$READY_TASKS" == *"no matching tasks"* ]]; then
        echo "No ready tasks found."
        if [[ "$ONCE" = true ]]; then
            echo "Exiting (--once mode)."
            exit 0
        fi
        echo "Sleeping 10s..."
        sleep 10
        continue
    fi
    
    echo "$READY_TASKS"
    echo ""
    
    if [[ "$DRY_RUN" = true ]]; then
        echo "[DRY RUN] Would claim next ready task"
        if [[ "$ONCE" = true ]]; then
            exit 0
        fi
        sleep 5
        continue
    fi
    
    # Claim the next task
    echo "Attempting to claim task..."
    CLAIM_RESULT=$($HERMES kanban claim --profile "$PROFILE" 2>&1) || {
        echo "Claim failed: $CLAIM_RESULT"
        sleep 5
        continue
    }
    
    echo "$CLAIM_RESULT"
    
    # Parse task ID from claim output
    # Hermes outputs workspace path; task ID is often in the path or we extract from list
    TASK_ID=$(echo "$CLAIM_RESULT" | grep -oP '[a-f0-9-]{36}' | head -1 || echo "")
    
    if [[ -z "$TASK_ID" ]]; then
        echo "Could not extract task ID from claim output. Checking latest ready task..."
        TASK_ID=$($HERMES kanban list --status active --assignee "$PROFILE" 2>/dev/null | grep -oP '[a-f0-9-]{36}' | head -1 || echo "")
    fi
    
    if [[ -z "$TASK_ID" ]]; then
        echo "Could not determine task ID. Skipping."
        sleep 5
        continue
    fi
    
    echo "Claimed task: $TASK_ID"
    
    # Get task details to extract stage/source/marker
    TASK_SHOW=$($HERMES kanban show "$TASK_ID" 2>/dev/null || echo "")
    TASK_TITLE=$(echo "$TASK_SHOW" | grep "^Task" | sed 's/^Task [a-f0-9-]*: //' || echo "")
    
    # Parse stage, source, marker from title or body
    # Expected format: "stage_2_extraction: apob ← apob-peter-attia-source"
    STAGE=$(echo "$TASK_TITLE" | grep -oP '^[^:]+' || echo "stage_2_extraction")
    MARKER=$(echo "$TASK_TITLE" | grep -oP '(?<=: )[^←]+' | tr -d ' ' || echo "")
    SOURCE_ID=$(echo "$TASK_TITLE" | grep -oP '(?<=← ).+' | tr -d ' ' || echo "")
    
    # Fallback: if parsing fails, use defaults
    if [[ -z "$MARKER" || -z "$SOURCE_ID" ]]; then
        echo "Could not parse stage details from task title: $TASK_TITLE"
        echo "Falling back to direct stage execution with defaults."
        STAGE="extractor"
        SOURCE_ID="apob-peter-attia-source"
        MARKER="apob"
    fi
    
    # Map stage name
    case "$STAGE" in
        stage_1_discovery)  STAGE_SHORT="discovery" ;;
        stage_2_extraction) STAGE_SHORT="extractor" ;;
        stage_3_council)    STAGE_SHORT="council" ;;
        stage_4_provenance) STAGE_SHORT="provenance" ;;
        stage_5_legal)      STAGE_SHORT="legal" ;;
        stage_6_assembly)   STAGE_SHORT="assembly" ;;
        *)                  STAGE_SHORT="$STAGE" ;;
    esac
    
    RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-${TASK_ID:0:8}"
    
    echo ""
    echo "Task details:"
    echo "  Stage:  $STAGE_SHORT ($STAGE)"
    echo "  Source: $SOURCE_ID"
    echo "  Marker: $MARKER"
    echo "  Run ID: $RUN_ID"
    echo ""
    
    # Run the stage
    echo "Executing stage via run-stage.sh..."
    if "$PROJECT_ROOT/scripts/run-stage.sh" "$STAGE_SHORT" "$RUN_ID" "$SOURCE_ID" "$MARKER" 2>&1 | tee "$PROJECT_ROOT/runs/$RUN_ID/worker.log"; then
        echo ""
        echo "Stage completed successfully."
        $HERMES kanban complete "$TASK_ID" --comment "Completed by $PROFILE. Run: $RUN_ID"
    else
        echo ""
        echo "Stage failed."
        $HERMES kanban block "$TASK_ID" --comment "Failed by $PROFILE. Run: $RUN_ID. Check logs."
    fi
    
    echo ""
    echo "✓ Task $TASK_ID finished"
    echo ""
    
    if [[ "$ONCE" = true ]]; then
        echo "Exiting (--once mode)."
        exit 0
    fi
done
