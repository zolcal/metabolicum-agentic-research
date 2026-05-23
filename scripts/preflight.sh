#!/usr/bin/env bash
# preflight.sh — assert every runbook §2 pre-condition before first Hermes task.
# Exit on first failure. Run from project root.
set -uo pipefail

RED='\033[0;31m'
GRN='\033[0;32m'
YLW='\033[0;33m'
RST='\033[0m'

PASS=0
FAIL=0
WARN=0

pass() { PASS=$((PASS+1)); printf "${GRN}✓${RST} %s\n" "$1"; }
fail() { FAIL=$((FAIL+1)); printf "${RED}✗${RST} %s\n" "$1"; }
warn() { WARN=$((WARN+1)); printf "${YLW}⚠${RST} %s\n" "$1"; }

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "══════════════════════════════════════════════════════════════"
echo "  Hermes preflight — metabolicum-agentic-research"
echo "  $(date -Iseconds)"
echo "══════════════════════════════════════════════════════════════"
echo ""

# ─── Configuration ────────────────────────────────────────────────────────

echo "─── Configuration ───"

PINNED=$(cat config/hermes-version.txt 2>/dev/null || echo "")
if [[ -z "$PINNED" ]]; then
    fail "config/hermes-version.txt missing or empty"
else
    INSTALLED=$(hermes --version 2>/dev/null | head -1 | grep -oP 'v[\d.]+' || echo "")
    if [[ "$INSTALLED" == "$PINNED" ]]; then
        pass "Hermes version: pinned=$PINNED installed=$INSTALLED"
    else
        fail "Hermes version mismatch: pinned=$PINNED installed=${INSTALLED:-not found}"
    fi
fi

if [[ -f config/llm-endpoints.yaml ]]; then
    pass "config/llm-endpoints.yaml exists"
else
    fail "config/llm-endpoints.yaml missing"
fi

if [[ -f config/tools.yaml ]]; then
    pass "config/tools.yaml exists"
else
    fail "config/tools.yaml missing"
fi

if [[ -f hermes/SOUL.md ]]; then
    pass "hermes/SOUL.md exists"
else
    fail "hermes/SOUL.md missing"
fi

if [[ -f hermes/config.yaml ]]; then
    pass "hermes/config.yaml exists"
else
    fail "hermes/config.yaml missing"
fi

echo ""

# ─── Secrets ──────────────────────────────────────────────────────────────

echo "─── Secrets ───"

if [[ -f secrets/.env ]]; then
    pass "secrets/.env exists"
    # shellcheck disable=SC1091
    source secrets/.env 2>/dev/null || true

    for VAR in OPENROUTER_API_KEY GOOGLE_API_KEY DASHSCOPE_API_KEY \
               SUPABASE_URL SUPABASE_DB_URL YOUTUBE_API_KEY; do
        if [[ -n "${!VAR:-}" ]]; then
            pass "$VAR is set"
        else
            fail "$VAR is not set (required)"
        fi
    done
else
    fail "secrets/.env missing — copy from secrets/.env.example and populate"
fi

echo ""

# ─── Backend services ─────────────────────────────────────────────────────

echo "─── Backend services ───"

if curl -sf -o /dev/null http://127.0.0.1:8080/v1/models; then
    MODEL=$(curl -s http://127.0.0.1:8080/v1/models | python3 -c "
import sys,json
d=json.load(sys.stdin)
print(d.get('data',[{}])[0].get('id','unknown'))" 2>/dev/null || echo "unknown")
    pass "llama-server reachable (model: $MODEL)"
else
    fail "llama-server not reachable at http://127.0.0.1:8080/v1"
fi

if curl -sf -o /dev/null http://127.0.0.1:8888; then
    pass "SearXNG reachable at http://127.0.0.1:8888"
else
    fail "SearXNG not reachable at http://127.0.0.1:8888"
fi

PUBMED_HTTP=$(curl -s -o /dev/null -w "%{http_code}" \
    "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=test&retmax=1" 2>/dev/null)
if [[ "$PUBMED_HTTP" == "200" ]]; then
    pass "PubMed E-utilities reachable"
else
    fail "PubMed E-utilities not reachable (HTTP $PUBMED_HTTP)"
fi

echo ""

# ─── Inputs ───────────────────────────────────────────────────────────────

echo "─── Inputs ───"

WAVE0_COUNT=$(find input/sm-ranges/wave-0/ -name "*.yaml" 2>/dev/null | wc -l)
if [[ "$WAVE0_COUNT" -ge 5 ]]; then
    pass "input/sm-ranges/wave-0/ has $WAVE0_COUNT marker YAMLs (≥5 required)"
else
    fail "input/sm-ranges/wave-0/ has $WAVE0_COUNT marker YAMLs (need ≥5)"
fi

if [[ -f input/registry/marker-identity-registry.v1.yaml ]]; then
    pass "input/registry/marker-identity-registry.v1.yaml exists"
else
    fail "input/registry/marker-identity-registry.v1.yaml missing"
fi

if [[ -f input/marker_glossary.json ]]; then
    pass "input/marker_glossary.json exists"
else
    fail "input/marker_glossary.json missing"
fi

FIXTURE_COUNT=$(find fixtures/sources/ -name "*.json" 2>/dev/null | wc -l)
if [[ "$FIXTURE_COUNT" -ge 1 ]]; then
    pass "fixtures/sources/ has $FIXTURE_COUNT cached source(s)"
else
    fail "fixtures/sources/ has no cached source transcripts"
fi

echo ""

# ─── Contracts ────────────────────────────────────────────────────────────

echo "─── Contracts ───"

SPEC_COUNT=$(find docs/agentic-workflow/ -name "*.md" 2>/dev/null | wc -l)
if [[ "$SPEC_COUNT" -ge 10 ]]; then
    pass "docs/agentic-workflow/ has $SPEC_COUNT spec docs"
else
    fail "docs/agentic-workflow/ has only $SPEC_COUNT spec docs (expected ≥10)"
fi

if [[ -f docs/policies/RANGE-STATUS-COLOR-POLICY.md ]]; then
    pass "docs/policies/RANGE-STATUS-COLOR-POLICY.md exists"
else
    fail "docs/policies/RANGE-STATUS-COLOR-POLICY.md missing"
fi

PROMPT_COUNT=$(find prompts/ -name "*.md" ! -name "README.md" 2>/dev/null | wc -l)
if [[ "$PROMPT_COUNT" -ge 7 ]]; then
    pass "prompts/ has $PROMPT_COUNT role-locked prompts (≥7 required)"
else
    fail "prompts/ has $PROMPT_COUNT role-locked prompts (need ≥7)"
fi

for SCHEMA in state.schema.json extracted_claim.schema.json \
              extracted_raw_claim.schema.json source_fixture.schema.json; do
    if [[ -f "code/schemas/$SCHEMA" ]]; then
        if python3 -c "import json; json.load(open('code/schemas/$SCHEMA'))" 2>/dev/null; then
            pass "code/schemas/$SCHEMA (valid JSON)"
        else
            fail "code/schemas/$SCHEMA (invalid JSON)"
        fi
    else
        fail "code/schemas/$SCHEMA missing"
    fi
done

echo ""

# ─── Persistence (Supabase) ──────────────────────────────────────────────

echo "─── Persistence ───"

if [[ -f supabase/migrations/0001_initial.sql ]]; then
    pass "supabase/migrations/0001_initial.sql exists"
    if grep -q "canonical_color\|color.*CHECK" supabase/migrations/0001_initial.sql 2>/dev/null; then
        pass "Color CHECK constraint found in migration"
    else
        warn "No explicit color CHECK constraint in migration (may be in downstream schema)"
    fi
else
    fail "supabase/migrations/0001_initial.sql missing"
fi

# Check if Supabase is reachable (only if SUPABASE_URL is set)
if [[ -n "${SUPABASE_URL:-}" ]]; then
    SUPA_HTTP=$(curl -s -o /dev/null -w "%{http_code}" "$SUPABASE_URL" 2>/dev/null)
    if [[ "$SUPA_HTTP" == "200" || "$SUPA_HTTP" == "301" || "$SUPA_HTTP" == "302" ]]; then
        pass "Supabase project reachable at $SUPABASE_URL"
    else
        warn "Supabase returned HTTP $SUPA_HTTP — may need migration applied"
    fi
fi

echo ""

# ─── Fixture schema validation ───────────────────────────────────────────

echo "─── Fixture validation ───"

FIRST_FIXTURE=$(find fixtures/sources/ -name "*.json" 2>/dev/null | head -1)
if [[ -n "$FIRST_FIXTURE" ]]; then
    VALIDATION=$(python3 -c "
import json, sys
schema = json.load(open('code/schemas/source_fixture.schema.json'))
fixture = json.load(open('$FIRST_FIXTURE'))
required = schema.get('required', [])
missing = [r for r in required if r not in fixture]
if missing:
    print(f'FAIL: missing required fields: {missing}')
    sys.exit(1)
else:
    print(f'OK: all {len(required)} required fields present')
" 2>&1)
    if [[ $? -eq 0 ]]; then
        pass "$(basename "$FIRST_FIXTURE"): $VALIDATION"
    else
        fail "$(basename "$FIRST_FIXTURE"): $VALIDATION"
    fi
fi

echo ""

# ─── Summary ─────────────────────────────────────────────────────────────

echo "══════════════════════════════════════════════════════════════"
printf "  Results: ${GRN}%d passed${RST}  ${RED}%d failed${RST}  ${YLW}%d warnings${RST}\n" "$PASS" "$FAIL" "$WARN"
echo "══════════════════════════════════════════════════════════════"

if [[ "$FAIL" -gt 0 ]]; then
    echo ""
    echo "  ✗ Preflight FAILED — fix the above before running Hermes."
    exit 1
else
    echo ""
    echo "  ✓ Preflight PASSED — ready for acceptance tests."
    exit 0
fi
