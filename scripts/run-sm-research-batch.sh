#!/usr/bin/env bash
# run-sm-research-batch.sh — Batch-process SM anchor YAMLs through Hermes cloud.
#
# Usage:
#   time ./scripts/run-sm-research-batch.sh [marker1 marker2 ...]
#
# Defaults to 10 pilot markers if no args given.
# Uses the cloud provider configured in hermes/config.yaml (DashScope Qwen 3.7 Max).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR/.."
cd "$PROJECT_ROOT"

HERMES="$PROJECT_ROOT/run-hermes"
RUN_ID="$(date -u +%Y%m%d-%H%M%S)"
RUN_DIR="$PROJECT_ROOT/runs/sm-batch-$RUN_ID"
PROMPT_FILE="$PROJECT_ROOT/prompts/06-sm-research-brief.md"

# Default 10 markers
DEFAULT_MARKERS=(
    apob
    fasting-insulin
    hba1c
    lpa
    tg-hdl-ratio
    17-hydroxyprogesterone
    absolute-lymphocytes
    absolute-neutrophils
    albumin
    alpha-1-acid-glycoprotein
)

MARKERS=("${@:-${DEFAULT_MARKERS[@]}}")

# ─── Validate environment ─────────────────────────────────────────────────

if [[ ! -f "$PROMPT_FILE" ]]; then
    echo "ERROR: Prompt not found: $PROMPT_FILE"
    exit 1
fi

if [[ ! -f "$PROJECT_ROOT/hermes/config.yaml" ]]; then
    echo "ERROR: Hermes config not found"
    exit 1
fi

if [[ ! -f "$PROJECT_ROOT/hermes/SOUL.md" ]]; then
    echo "ERROR: Hermes SOUL.md not found"
    exit 1
fi

mkdir -p "$RUN_DIR"

echo "══════════════════════════════════════════════════════════════"
echo "  SM Anchor Research Batch"
echo "  Run ID: $RUN_ID"
echo "  Markers: ${#MARKERS[@]}"
echo "  Provider: $(grep -A1 "^model:" "$PROJECT_ROOT/hermes/config.yaml" | grep "provider:" | awk '{print $2}' || echo "unknown")"
echo "  Run dir: $RUN_DIR"
echo "══════════════════════════════════════════════════════════════"
echo ""

# ─── Load prompt once ─────────────────────────────────────────────────────

STAGE_PROMPT=$(cat "$PROMPT_FILE")

# ─── Process each marker ──────────────────────────────────────────────────

SUCCESS_COUNT=0
FAIL_COUNT=0

for MARKER in "${MARKERS[@]}"; do
    echo "─── Processing: $MARKER ───"

    # Find the sm-range YAML
    YAML_PATH=$(find "$PROJECT_ROOT/input/sm-ranges" -name "$MARKER.yaml" | head -1)
    if [[ -z "$YAML_PATH" ]]; then
        echo "  ✗ SKIP: No sm-range YAML found for $MARKER"
        FAIL_COUNT=$((FAIL_COUNT + 1))
        continue
    fi
    echo "  YAML: $YAML_PATH"

    MARKER_DIR="$RUN_DIR/$MARKER"
    WORKER_HOME="$MARKER_DIR/hermes-home"
    OUTPUT_FILE="$MARKER_DIR/output.json"
    LOG_FILE="$MARKER_DIR/stage.log"
    RAW_RESPONSE="$MARKER_DIR/raw_response.txt"
    QUERY_FILE="$MARKER_DIR/query.txt"

    mkdir -p "$MARKER_DIR"

    # Setup disposable HERMES_HOME
    rm -rf "$WORKER_HOME"
    mkdir -p "$WORKER_HOME"
    cp "$PROJECT_ROOT/hermes/config.yaml" "$WORKER_HOME/config.yaml"
    cp "$PROJECT_ROOT/hermes/SOUL.md" "$WORKER_HOME/SOUL.md"

    # Build combined query
    YAML_CONTENT=$(cat "$YAML_PATH")

    COMBINED_QUERY=$(cat <<EOF
# STAGE INSTRUCTIONS
${STAGE_PROMPT}

# SM ANCHOR DATA
The following is the Standard Medical anchor YAML for marker "${MARKER}".
Analyze it and produce the structured JSON research brief defined above.

\`\`\`yaml
${YAML_CONTENT}
\`\`\`

# OUTPUT REQUIREMENTS
Produce ONLY a valid JSON object conforming to the schema in the instructions.
Do not include markdown fences, explanations, or any text outside the JSON.
The JSON must be parseable by Python's json.loads() without any preprocessing.
EOF
)

    echo "$COMBINED_QUERY" > "$QUERY_FILE"
    echo "  Query: $QUERY_FILE ($(wc -c < "$QUERY_FILE") bytes)"

    # Invoke Hermes
    export HERMES_HOME="$WORKER_HOME"
    export UV_NO_CONFIG=1

    echo "  Invoking Hermes ..."
    if "$HERMES" chat \
        -q "$COMBINED_QUERY" \
        -Q \
        --ignore-rules \
        --max-turns 15 \
        > "$RAW_RESPONSE" \
        2> "$LOG_FILE"; then
        echo "  Hermes exited successfully."
    else
        EXIT_CODE=$?
        echo "  Hermes exited with code $EXIT_CODE"
    fi

    # Extract JSON from response
    python3 <<PYEOF > "$OUTPUT_FILE" 2>> "$LOG_FILE" || true
import json
import re
import sys

with open("$RAW_RESPONSE", "r") as f:
    raw = f.read()

json_str = None

# 1. Look for JSON block inside markdown fences
match = re.search(r'\`\`\`(?:json)?\s*\n(.*?)\n\`\`\`', raw, re.DOTALL)
if match:
    json_str = match.group(1).strip()

# 2. Try to find plain JSON (not in diff format) — scan line-by-line
#    Hermes sometimes emits plain JSON after a truncated diff.
if not json_str:
    lines = raw.splitlines()
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped == '{' and not line.startswith('+'):
            # Count braces to find matching closure
            brace_count = 0
            json_lines = []
            for j in range(i, len(lines)):
                json_lines.append(lines[j])
                for ch in lines[j]:
                    if ch == '{':
                        brace_count += 1
                    elif ch == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            candidate = '\n'.join(json_lines).strip()
                            try:
                                json.loads(candidate)
                                json_str = candidate
                                break
                            except json.JSONDecodeError:
                                pass
                if json_str:
                    break
            if json_str:
                break

# 3. Try to find diff-style JSON (review diff with + prefixes)
if not json_str:
    diff_lines = []
    in_diff = False
    for line in raw.splitlines():
        if line.strip().startswith('┊ review diff') or line.strip().startswith('@@'):
            in_diff = True
            continue
        if in_diff and line.startswith('+'):
            diff_lines.append(line[1:])
        elif in_diff and line.startswith('-'):
            continue
        elif in_diff and line.startswith(' '):
            diff_lines.append(line[1:])
    if diff_lines:
        candidate = '\n'.join(diff_lines).strip()
        if candidate.startswith('{') or candidate.startswith('['):
            json_str = candidate

# 4. Try to find the first { and last }
if not json_str:
    start = raw.find('{')
    end = raw.rfind('}')
    if start != -1 and end != -1 and end > start:
        json_str = raw[start:end+1]

# 5. Maybe it's a JSON array
if not json_str:
    start = raw.find('[')
    end = raw.rfind(']')
    if start != -1 and end != -1 and end > start:
        json_str = raw[start:end+1]

if not json_str:
    json_str = raw.strip()

try:
    data = json.loads(json_str)
    with open("$OUTPUT_FILE", "w") as f:
        json.dump(data, f, indent=2)
except json.JSONDecodeError as e:
    failure = {
        "marker": "$MARKER",
        "status": "failed",
        "error": f"JSON decode error: {e}",
        "raw_preview": raw[:2000]
    }
    with open("$OUTPUT_FILE", "w") as f:
        json.dump(failure, f, indent=2)
    sys.stderr.write("JSON extraction failed — wrote failure record\n")
    sys.exit(1)
PYEOF

    if [[ -f "$OUTPUT_FILE" ]]; then
        # Validate it's a success JSON (not a failure record)
        if python3 -c "import json; d=json.load(open('$OUTPUT_FILE')); exit(0 if d.get('status') != 'failed' else 1)" 2>/dev/null; then
            echo "  ✓ Success — $OUTPUT_FILE"
            SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        else
            echo "  ✗ Failed — JSON extraction or schema issue"
            FAIL_COUNT=$((FAIL_COUNT + 1))
        fi
    else
        echo "  ✗ Failed — no output file"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi

    echo ""
done

# ─── Summary ──────────────────────────────────────────────────────────────

echo "══════════════════════════════════════════════════════════════"
echo "  Batch complete"
echo "  Success: $SUCCESS_COUNT / ${#MARKERS[@]}"
echo "  Failed:  $FAIL_COUNT / ${#MARKERS[@]}"
echo "  Run dir: $RUN_DIR"
echo "══════════════════════════════════════════════════════════════"

if [[ $FAIL_COUNT -gt 0 ]]; then
    exit 1
fi
