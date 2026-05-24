#!/usr/bin/env bash
# enqueue-source.sh — Enqueue a source×marker task onto the Kanban board.
#
# Usage:
#   ./scripts/enqueue-source.sh <source_id> <marker_slug> [stage]
#
# Arguments:
#   source_id    — fixture ID (e.g., apob-peter-attia-source) or source URL
#   marker_slug  — marker to process (e.g., apob)
#   stage        — optional: specific stage to run (default: stage_2_extraction)
#
# Examples:
#   ./scripts/enqueue-source.sh apob-peter-attia-source apob
#   ./scripts/enqueue-source.sh apob-peter-attia-source apob stage_3_council

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR/.."
cd "$PROJECT_ROOT"

HERMES="$PROJECT_ROOT/run-hermes"

SOURCE_ID="${1:-}"
MARKER="${2:-}"
STAGE="${3:-stage_2_extraction}"

if [[ -z "$SOURCE_ID" || -z "$MARKER" ]]; then
    echo "Usage: $0 <source_id> <marker_slug> [stage]"
    echo ""
    echo "Stages:"
    echo "  stage_1_discovery      — source discovery"
    echo "  stage_2_extraction     — content extraction (default)"
    echo "  stage_3_council        — validation council"
    echo "  stage_4_provenance     — provenance resolution"
    echo "  stage_5_legal          — legal review"
    echo "  stage_6_assembly       — SQL assembly"
    exit 1
fi

# Validate fixture exists if it looks like a fixture ID
FIXTURE_PATH="$PROJECT_ROOT/fixtures/sources/${SOURCE_ID}.json"
if [[ -f "$FIXTURE_PATH" ]]; then
    echo "Using fixture: $FIXTURE_PATH"
    SOURCE_TYPE="fixture"
else
    echo "Source not found in fixtures/: $SOURCE_ID"
    echo "Treating as raw URL/identifier"
    SOURCE_TYPE="raw"
fi

# Build task title and description
TASK_TITLE="$STAGE: $MARKER ← $SOURCE_ID"
TASK_DESC="""Stage: $STAGE
Source: $SOURCE_ID
Marker: $MARKER
Source type: $SOURCE_TYPE
Project: metabolicum-agentic-research
Queued at: $(date -Iseconds)
"""

# Ensure we're on the right board
$HERMES kanban boards switch metabolicum-agentic-research >/dev/null 2>&1 || true

echo "Enqueuing task: $TASK_TITLE"

# Create the task
$HERMES kanban create "$TASK_TITLE" \
    --body "$TASK_DESC" \
    --idempotency-key "${STAGE}:${SOURCE_ID}:${MARKER}"

echo ""
echo "✓ Task enqueued. Current board status:"
$HERMES kanban list
