#!/usr/bin/env bash
# run-stage.sh — Run a single pipeline stage via Hermes.
#
# Usage:
#   ./scripts/run-stage.sh <stage> <run_id> <source_id> <marker>
#
# Arguments:
#   stage     — stage name: extractor, tagger, structurer, council, legal
#   run_id    — run timestamp or identifier
#   source_id — source fixture ID or URL identifier
#   marker    — marker slug (e.g., apob)
#
# Example:
#   ./scripts/run-stage.sh extractor 2026-05-23T210000Z apob-peter-attia-source apob
#
# This script:
#   1. Creates a disposable HERMES_HOME under runs/<run_id>/
#   2. Loads the correct prompt from prompts/
#   3. Loads the source fixture or cached transcript
#   4. Invokes Hermes in non-interactive mode with the combined prompt
#   5. Extracts JSON output and writes to runs/<run_id>/<stage>/output.json
#   6. Returns the output path

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR/.."
cd "$PROJECT_ROOT"

HERMES="$PROJECT_ROOT/run-hermes"

STAGE="${1:-}"
RUN_ID="${2:-}"
SOURCE_ID="${3:-}"
MARKER="${4:-}"

if [[ -z "$STAGE" || -z "$RUN_ID" || -z "$SOURCE_ID" || -z "$MARKER" ]]; then
    echo "Usage: $0 <stage> <run_id> <source_id> <marker>"
    echo ""
    echo "Stages:"
    echo "  extractor   — Stage 2a: verbatim claim extraction"
    echo "  tagger      — Stage 2b: marker-tag attachment"
    echo "  structurer  — Stage 2c: population qualifier + units structuring"
    echo "  council     — Stage 3: validation council"
    echo "  legal       — Stage 5: legal review"
    exit 1
fi

# ─── Resolve paths ────────────────────────────────────────────────────────

RUN_DIR="$PROJECT_ROOT/runs/$RUN_ID"
STAGE_DIR="$RUN_DIR/$STAGE"
WORKER_HOME="$STAGE_DIR/hermes-home"
OUTPUT_FILE="$STAGE_DIR/output.json"
LOG_FILE="$STAGE_DIR/stage.log"
RAW_RESPONSE="$STAGE_DIR/raw_response.txt"

mkdir -p "$STAGE_DIR"

# Find source fixture
FIXTURE_PATH="$PROJECT_ROOT/fixtures/sources/${SOURCE_ID}.json"
if [[ ! -f "$FIXTURE_PATH" ]]; then
    echo "ERROR: Fixture not found: $FIXTURE_PATH"
    exit 1
fi

# Determine prompt file
PROMPT_FILE=""
case "$STAGE" in
    extractor)   PROMPT_FILE="$PROJECT_ROOT/prompts/01-content-extractor.md" ;;
    tagger)      PROMPT_FILE="$PROJECT_ROOT/prompts/02-marker-tagger.md" ;;
    structurer)  PROMPT_FILE="$PROJECT_ROOT/prompts/03-demographic-structurer.md" ;;
    council)     PROMPT_FILE="$PROJECT_ROOT/prompts/04c-council-decider.md" ;;
    legal)       PROMPT_FILE="$PROJECT_ROOT/prompts/05-legal-reviewer.md" ;;
    *)
        echo "ERROR: Unknown stage: $STAGE"
        exit 1
        ;;
esac

if [[ ! -f "$PROMPT_FILE" ]]; then
    echo "ERROR: Prompt not found: $PROMPT_FILE"
    exit 1
fi

echo "══════════════════════════════════════════════════════════════"
echo "  Running stage: $STAGE"
echo "  Run ID:        $RUN_ID"
echo "  Source:        $SOURCE_ID"
echo "  Marker:        $MARKER"
echo "  Prompt:        $(basename "$PROMPT_FILE")"
echo "  Worker home:   $WORKER_HOME"
echo "══════════════════════════════════════════════════════════════"

# ─── Setup disposable HERMES_HOME ─────────────────────────────────────────

rm -rf "$WORKER_HOME"
mkdir -p "$WORKER_HOME"
cp "$PROJECT_ROOT/hermes/config.yaml" "$WORKER_HOME/config.yaml"
cp "$PROJECT_ROOT/hermes/SOUL.md" "$WORKER_HOME/SOUL.md"

# ─── Build combined prompt ────────────────────────────────────────────────

# Read the stage prompt
STAGE_PROMPT=$(cat "$PROMPT_FILE")

# Read the source fixture
SOURCE_JSON=$(cat "$FIXTURE_PATH")

# Read the marker glossary if available
GLOSSARY=""
if [[ -f "$PROJECT_ROOT/input/marker_glossary.json" ]]; then
    GLOSSARY=$(cat "$PROJECT_ROOT/input/marker_glossary.json")
fi

# Build the query
COMBINED_QUERY=$(cat <<EOF
# STAGE INSTRUCTIONS
${STAGE_PROMPT}

# SOURCE DATA
The following is the source fixture you must process:
\`\`\`json
${SOURCE_JSON}
\`\`\`

# ADDITIONAL CONTEXT
Marker to focus on: ${MARKER}
Project root: ${PROJECT_ROOT}
Expected output file: ${OUTPUT_FILE}

# OUTPUT REQUIREMENTS
Produce ONLY a valid JSON object conforming to the schema in code/schemas/extracted_claim.schema.json.
Do not include markdown fences, explanations, or any text outside the JSON.
The JSON must be parseable by Python's json.loads() without any preprocessing.
EOF
)

# Write combined query to file for inspection
QUERY_FILE="$STAGE_DIR/query.txt"
echo "$COMBINED_QUERY" > "$QUERY_FILE"
echo "Query written to: $QUERY_FILE ($(wc -c < "$QUERY_FILE") bytes)"

# ─── Invoke Hermes ────────────────────────────────────────────────────────

export HERMES_HOME="$WORKER_HOME"
export UV_NO_CONFIG=1

echo ""
echo "Invoking Hermes (non-interactive) ..."
echo ""

# Run Hermes in non-interactive mode
# -Q = quiet (no banner, spinner)
# --ignore-rules = skip AGENTS.md/SOUL.md auto-injection (we copied our own)
# --max-turns = limit iterations
# We redirect stderr to log as well
if "$HERMES" chat \
    -q "$COMBINED_QUERY" \
    -Q \
    --ignore-rules \
    --max-turns 15 \
    > "$RAW_RESPONSE" \
    2> "$LOG_FILE"; then
    
    echo "Hermes exited successfully."
else
    EXIT_CODE=$?
    echo "Hermes exited with code $EXIT_CODE"
    echo "Check log: $LOG_FILE"
fi

# ─── Extract JSON from response ───────────────────────────────────────────

echo ""
echo "Extracting JSON from response ..."

# Try to extract JSON from the raw response
# First, try python extraction
python3 <<PYEOF > "$OUTPUT_FILE" 2>> "$LOG_FILE" || true
import json
import re
import sys

with open("$RAW_RESPONSE", "r") as f:
    raw = f.read()

# Look for JSON block inside markdown fences
match = re.search(r'\`\`\`(?:json)?\s*\n(.*?)\n\`\`\`', raw, re.DOTALL)
if match:
    json_str = match.group(1).strip()
else:
    # Try to find the first { and last }
    start = raw.find('{')
    end = raw.rfind('}')
    if start != -1 and end != -1 and end > start:
        json_str = raw[start:end+1]
    else:
        # Maybe it's a JSON array
        start = raw.find('[')
        end = raw.rfind(']')
        if start != -1 and end != -1 and end > start:
            json_str = raw[start:end+1]
        else:
            json_str = raw.strip()

# Try to parse
try:
    data = json.loads(json_str)
    with open("$OUTPUT_FILE", "w") as f:
        json.dump(data, f, indent=2)
    print(f"Extracted JSON to $OUTPUT_FILE")
except json.JSONDecodeError as e:
    # Write a failure record
    failure = {
        "stage": "$STAGE",
        "source_id": "$SOURCE_ID",
        "marker": "$MARKER",
        "status": "failed",
        "error": f"JSON decode error: {e}",
        "raw_preview": raw[:2000]
    }
    with open("$OUTPUT_FILE", "w") as f:
        json.dump(failure, f, indent=2)
    print(f"JSON extraction failed — wrote failure record to $OUTPUT_FILE")
    sys.exit(1)
PYEOF

# ─── Validate output ──────────────────────────────────────────────────────

if [[ -f "$OUTPUT_FILE" ]]; then
    echo ""
    echo "✓ Stage $STAGE completed"
    echo "  Output:   $OUTPUT_FILE"
    echo "  Raw:      $RAW_RESPONSE"
    echo "  Log:      $LOG_FILE"
    echo "  Query:    $QUERY_FILE"
    
    # Show output preview
    echo ""
    echo "Output preview:"
    head -20 "$OUTPUT_FILE"
else
    echo ""
    echo "✗ Stage $STAGE failed — no output file"
    exit 1
fi
