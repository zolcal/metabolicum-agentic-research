#!/usr/bin/env bash
# run-pipeline-ui.sh — Interactive UI for running the full Metabolicum pipeline.
#
# Usage:
#   ./scripts/run-pipeline-ui.sh
#
# Provides a menu-driven interface:
#   1. Select source fixture from available list
#   2. Select marker from marker glossary
#   3. Choose run mode: Stage 2 only, or Full pipeline (Stages 2-6)
#   4. Pipeline runs automatically with progress display
#   5. Final report shows output locations and claim counts

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR/.."
cd "$PROJECT_ROOT"

HERMES="$PROJECT_ROOT/run-hermes"
VENV_PYTHON="$PROJECT_ROOT/vendor/hermes-agent-v2026.5.16/.venv/bin/python"

# ─── Colors ───────────────────────────────────────────────────────────────

RED='\033[0;31m'
GRN='\033[0;32m'
YLW='\033[1;33m'
BLU='\033[0;34m'
CYAN='\033[0;36m'
RST='\033[0m'
BOLD='\033[1m'

# ─── Helpers ──────────────────────────────────────────────────────────────

clear_screen() {
    printf '\033[2J\033[H'
}

header() {
    echo ""
    echo -e "${CYAN}════════════════════════════════════════════════════════════════${RST}"
    echo -e "${BOLD}  $1${RST}"
    echo -e "${CYAN}════════════════════════════════════════════════════════════════${RST}"
    echo ""
}

success() { echo -e "${GRN}✓${RST} $1"; }
warn()    { echo -e "${YLW}⚠${RST} $1"; }
error()   { echo -e "${RED}✗${RST} $1"; }
info()    { echo -e "${BLU}ℹ${RST} $1"; }

spinner() {
    local pid=$1
    local msg="$2"
    local delay=0.5
    local spinstr='|/-\\'
    while kill -0 "$pid" 2>/dev/null; do
        local temp=${spinstr#?}
        printf "\r%s %c" "$msg" "$spinstr"
        local spinstr=$temp${spinstr%%$temp}
        sleep $delay
    done
    printf "\r%s    \n" "$msg"
}

# ─── Load available fixtures ──────────────────────────────────────────────

load_fixtures() {
    FIXTURES=()
    while IFS= read -r -d '' f; do
        local basename=$(basename "$f" .json)
        if [[ "$basename" != ".gitkeep" && "$basename" != "README" ]]; then
            FIXTURES+=("$basename")
        fi
    done < <(find "$PROJECT_ROOT/fixtures/sources" -maxdepth 1 -name "*.json" -print0 2>/dev/null | sort -z)
}

# ─── Load available markers ───────────────────────────────────────────────

load_markers() {
    if [[ -f "$PROJECT_ROOT/input/marker_glossary.json" ]]; then
        MARKERS=$(cat "$PROJECT_ROOT/input/marker_glossary.json" | python3 -c "
import json, sys
data = json.load(sys.stdin)
markers = data if isinstance(data, list) else list(data.keys())
for m in markers:
    print(m)
" 2>/dev/null)
    else
        MARKERS=""
    fi
}

# ─── Run a single stage via Hermes ────────────────────────────────────────

run_stage() {
    local stage="$1"
    local run_id="$2"
    local source_id="$3"
    local marker="$4"
    
    echo ""
    info "Running Stage: ${BOLD}$stage${RST} | Run: $run_id"
    
    "$PROJECT_ROOT/scripts/run-stage.sh" "$stage" "$run_id" "$source_id" "$marker" > "$PROJECT_ROOT/runs/$run_id/${stage}.log" 2>&1 &
    local pid=$!
    spinner "$pid" "  Processing $stage..."
    wait "$pid" || true
    
    local output_file="$PROJECT_ROOT/runs/$run_id/$stage/output.json"
    if [[ -f "$output_file" ]]; then
        local claim_count=$(python3 -c "
import json,sys
try:
    d=json.load(open('$output_file'))
    if isinstance(d, list): print(len(d))
    else: print('N/A')
except: print('ERR')
" 2>/dev/null)
        success "Stage $stage complete — $claim_count claims"
        return 0
    else
        error "Stage $stage failed — no output file"
        return 1
    fi
}

# ─── Run full Stage 2 chain ───────────────────────────────────────────────

run_stage2_chain() {
    local run_id="$1"
    local source_id="$2"
    local marker="$3"
    
    header "STAGE 2: Extraction Pipeline"
    
    # Extractor
    if ! run_stage "extractor" "$run_id" "$source_id" "$marker"; then
        error "Extraction failed. Aborting Stage 2."
        return 1
    fi
    
    # Tagger
    if ! run_stage "tagger" "$run_id" "$source_id" "$marker"; then
        warn "Tagger failed. Continuing with raw extraction output."
    fi
    
    # Structurer
    if ! run_stage "structurer" "$run_id" "$source_id" "$marker"; then
        warn "Structurer failed. Continuing with previous output."
    fi
    
    return 0
}

# ─── Display final report ─────────────────────────────────────────────────

show_report() {
    local run_id="$1"
    local source_id="$2"
    local marker="$3"
    local run_dir="$PROJECT_ROOT/runs/$run_id"
    
    clear_screen
    header "PIPELINE COMPLETE — Run Report"
    
    echo -e "  ${BOLD}Run ID:${RST}    $run_id"
    echo -e "  ${BOLD}Source:${RST}    $source_id"
    echo -e "  ${BOLD}Marker:${RST}    $marker"
    echo -e "  ${BOLD}Run dir:${RST}   $run_dir"
    echo ""
    
    echo -e "${BOLD}Stage Outputs:${RST}"
    for stage in extractor tagger structurer council legal assembly; do
        local out="$run_dir/$stage/output.json"
        if [[ -f "$out" ]]; then
            local size=$(wc -c < "$out" | tr -d ' ')
            local claims=$(python3 -c "
import json,sys
try:
    d=json.load(open('$out'))
    if isinstance(d, list): print(len(d))
    elif isinstance(d, dict) and 'claims' in d: print(len(d['claims']))
    else: print('1')
except: print('ERR')
" 2>/dev/null)
            success "  $stage: $out (${size} bytes, $claims claims)"
        else
            echo -e "  ${RED}✗${RST} $stage: (not run or failed)"
        fi
    done
    
    echo ""
    echo -e "${BOLD}Logs:${RST}"
    for log in "$run_dir"/*.log; do
        [[ -f "$log" ]] && info "  $(basename "$log")"
    done
    
    echo ""
    echo -e "${CYAN}════════════════════════════════════════════════════════════════${RST}"
    echo ""
}

# ─── Main Menu ────────────────────────────────────────────────────────────

main_menu() {
    while true; do
        clear_screen
        header "METABOLICUM AGENTIC RESEARCH — Pipeline Runner"
        
        echo -e "  ${BOLD}1.${RST} Run Stage 2 (extractor → tagger → structurer)"
        echo -e "  ${BOLD}2.${RST} Run Full Pipeline (Stages 2-6) — ${YLW}experimental${RST}"
        echo -e "  ${BOLD}3.${RST} View Previous Runs"
        echo -e "  ${BOLD}4.${RST} Check Kanban Board"
        echo -e "  ${BOLD}5.${RST} Run Preflight Checks"
        echo -e "  ${BOLD}Q.${RST} Quit"
        echo ""
        read -rp "Select option: " choice
        
        case "$choice" in
            1) run_stage2_menu ;;
            2) run_full_pipeline_menu ;;
            3) view_previous_runs ;;
            4) check_kanban ;;
            5) run_preflight ;;
            [Qq]) echo "Goodbye."; exit 0 ;;
            *) warn "Invalid option. Press Enter to continue."; read ;;
        esac
    done
}

# ─── Stage 2 Menu ─────────────────────────────────────────────────────────

run_stage2_menu() {
    clear_screen
    header "STAGE 2: Select Source & Marker"
    
    load_fixtures
    if [[ ${#FIXTURES[@]} -eq 0 ]]; then
        error "No fixtures found in fixtures/sources/"
        read -rp "Press Enter to return..."
        return
    fi
    
    echo -e "${BOLD}Available Sources:${RST}"
    for i in "${!FIXTURES[@]}"; do
        local num=$((i+1))
        echo -e "  ${BOLD}$num.${RST} ${FIXTURES[$i]}"
    done
    echo ""
    read -rp "Select source [1-${#FIXTURES[@]}]: " src_num
    
    if ! [[ "$src_num" =~ ^[0-9]+$ ]] || [[ "$src_num" -lt 1 ]] || [[ "$src_num" -gt ${#FIXTURES[@]} ]]; then
        error "Invalid selection"
        read -rp "Press Enter to return..."
        return
    fi
    
    local source_id="${FIXTURES[$((src_num-1))]}"
    
    # Auto-detect marker from fixture or ask
    local detected_marker=$(python3 -c "
import json
try:
    d=json.load(open('$PROJECT_ROOT/fixtures/sources/$source_id.json'))
    markers = d.get('expected_markers', [])
    print(markers[0] if markers else '')
except: print('')
" 2>/dev/null)
    
    if [[ -n "$detected_marker" ]]; then
        echo ""
        info "Detected marker from fixture: ${BOLD}$detected_marker${RST}"
        read -rp "Use this marker? [Y/n]: " confirm
        [[ "$confirm" =~ ^[Nn] ]] && detected_marker=""
    fi
    
    if [[ -z "$detected_marker" ]]; then
        load_markers
        echo ""
        echo -e "${BOLD}Available Markers:${RST}"
        echo "$MARKERS" | head -20 | nl
        echo ""
        read -rp "Enter marker slug: " detected_marker
    fi
    
    local run_id="$(date -u +%Y%m%dT%H%M%SZ)-stage2"
    
    echo ""
    info "Starting Stage 2 pipeline..."
    info "  Source: $source_id"
    info "  Marker: $detected_marker"
    info "  Run ID: $run_id"
    
    run_stage2_chain "$run_id" "$source_id" "$detected_marker"
    
    show_report "$run_id" "$source_id" "$detected_marker"
    
    read -rp "Press Enter to return to main menu..."
}

# ─── Full Pipeline Menu ───────────────────────────────────────────────────

run_full_pipeline_menu() {
    clear_screen
    header "FULL PIPELINE (Stages 2-6)"
    warn "This runs all stages including council, legal, and assembly."
    warn "Cloud API costs will apply for Stage 3 council."
    echo ""
    read -rp "Continue? [y/N]: " confirm
    [[ ! "$confirm" =~ ^[Yy] ]] && return
    
    load_fixtures
    echo -e "${BOLD}Available Sources:${RST}"
    for i in "${!FIXTURES[@]}"; do
        echo -e "  ${BOLD}$((i+1)).${RST} ${FIXTURES[$i]}"
    done
    echo ""
    read -rp "Select source: " src_num
    
    if ! [[ "$src_num" =~ ^[0-9]+$ ]] || [[ "$src_num" -lt 1 ]] || [[ "$src_num" -gt ${#FIXTURES[@]} ]]; then
        error "Invalid selection"
        read -rp "Press Enter to return..."
        return
    fi
    
    local source_id="${FIXTURES[$((src_num-1))]}"
    local detected_marker=$(python3 -c "
import json
try:
    d=json.load(open('$PROJECT_ROOT/fixtures/sources/$source_id.json'))
    markers = d.get('expected_markers', [])
    print(markers[0] if markers else '')
except: print('')
" 2>/dev/null)
    
    [[ -z "$detected_marker" ]] && read -rp "Enter marker slug: " detected_marker
    
    local run_id="$(date -u +%Y%m%dT%H%M%SZ)-full"
    
    run_stage2_chain "$run_id" "$source_id" "$detected_marker"
    
    # TODO: Add stages 3-6 when implemented
    warn "Stages 3-6 (council, legal, assembly) not yet fully implemented."
    warn "Only Stage 2 completed."
    
    show_report "$run_id" "$source_id" "$detected_marker"
    read -rp "Press Enter to return to main menu..."
}

# ─── View Previous Runs ───────────────────────────────────────────────────

view_previous_runs() {
    clear_screen
    header "PREVIOUS RUNS"
    
    local runs=()
    while IFS= read -r -d '' d; do
        runs+=("$(basename "$d")")
    done < <(find "$PROJECT_ROOT/runs" -maxdepth 1 -type d -print0 2>/dev/null | sort -z)
    
    if [[ ${#runs[@]} -le 1 ]]; then
        warn "No previous runs found."
        read -rp "Press Enter to return..."
        return
    fi
    
    echo -e "${BOLD}Available Runs:${RST}"
    for i in "${!runs[@]}"; do
        [[ "${runs[$i]}" == "runs" ]] && continue
        echo -e "  ${BOLD}$((i)).${RST} ${runs[$i]}"
    done
    echo ""
    read -rp "Select run to inspect (or Enter to cancel): " run_num
    
    if [[ -z "$run_num" ]] || ! [[ "$run_num" =~ ^[0-9]+$ ]]; then
        return
    fi
    
    local run_id="${runs[$run_num]}"
    [[ "$run_id" == "runs" ]] && return
    
    local run_dir="$PROJECT_ROOT/runs/$run_id"
    echo ""
    info "Run: $run_id"
    ls -la "$run_dir" 2>/dev/null || warn "Run directory empty or missing"
    echo ""
    read -rp "Press Enter to return..."
}

# ─── Check Kanban ─────────────────────────────────────────────────────────

check_kanban() {
    clear_screen
    header "KANBAN BOARD STATUS"
    "$HERMES" kanban boards switch metabolicum-agentic-research >/dev/null 2>&1 || true
    "$HERMES" kanban list 2>/dev/null || echo "(no tasks)"
    echo ""
    read -rp "Press Enter to return..."
}

# ─── Run Preflight ────────────────────────────────────────────────────────

run_preflight() {
    clear_screen
    header "PREFLIGHT CHECKS"
    "$PROJECT_ROOT/scripts/preflight.sh"
    echo ""
    read -rp "Press Enter to return..."
}

# ─── Entry Point ──────────────────────────────────────────────────────────

main_menu
