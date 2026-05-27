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

HERMES_CMD="$PROJECT_ROOT/run-hermes"
PINNED=$(cat config/hermes-version.txt 2>/dev/null || echo "")
if [[ -z "$PINNED" ]]; then
    fail "config/hermes-version.txt missing or empty"
else
    INSTALLED=$($HERMES_CMD --version 2>/dev/null | head -1 | grep -oP 'v[\d.]+' || echo "")
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
    warn "llama-server not reachable at http://127.0.0.1:8080/v1 (operator must start it)"
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

# ─── Config drift (pinned hermes/config.yaml vs gateway-home/config.yaml) ─
# Per hermes-setup.md §2.1, full-file SHA-256 is not enforced — Hermes auto-
# expands the config on init and the dashboard rewrites model.default. The
# project-authoritative key set defined in hermes/config.yaml's header
# docstring is what must hold. This block validates that subset.

echo "─── Config drift ───"

if [[ -f hermes/gateway-home/config.yaml ]]; then
    DRIFT_REPORT=$(python3 - <<'PY'
import sys, yaml

try:
    live = yaml.safe_load(open("hermes/gateway-home/config.yaml").read())
except Exception as e:
    print(f"ERROR parsing live config: {e}")
    sys.exit(1)

# Authoritative scalar keys: (path, expected_value)
authoritative = [
    (("memory", "memory_enabled"), False),
    (("memory", "user_profile_enabled"), False),
    (("compression", "enabled"), False),
    (("worktree",), False),
    (("approvals", "mode"), "off"),
    (("skills", "guard_agent_created"), True),
    (("terminal", "backend"), "local"),
]

def getpath(d, path):
    for k in path:
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d

mismatches = []
for path, expected in authoritative:
    live_val = getpath(live, path)
    if live_val != expected:
        mismatches.append((".".join(path), expected, live_val))

required_disabled = {"memory", "skills", "cronjob", "messaging"}
live_disabled = set(getpath(live, ("agent", "disabled_toolsets")) or [])
missing = required_disabled - live_disabled
if missing:
    mismatches.append(("agent.disabled_toolsets",
                       f"⊇ {sorted(required_disabled)}",
                       f"missing {sorted(missing)}"))

if mismatches:
    print(f"DRIFT — {len(mismatches)} authoritative key(s) violated")
    for key, exp, got in mismatches:
        print(f"    {key}: expected={exp!r} got={got!r}")
    sys.exit(1)
else:
    n = len(authoritative) + 1  # +1 for disabled_toolsets check
    print(f"OK — all {n} authoritative keys match pinned spec")
PY
)
    DRIFT_EXIT=$?
    if [[ $DRIFT_EXIT -eq 0 ]]; then
        pass "gateway-home/config.yaml: $DRIFT_REPORT"
    else
        # Currently a warn (not fail) per hermes-setup.md §2.1 transition note;
        # promote to fail once #6 (worker home split) makes the dual-config
        # story concrete and the gateway-only exceptions are formalized.
        warn "gateway-home/config.yaml drift:"
        echo "$DRIFT_REPORT" | tail -n +2 | sed 's/^/      /'
    fi
else
    warn "hermes/gateway-home/config.yaml not initialized (expected on first ./run-hermes)"
fi

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

# Check local DB has the expected tables (pipeline uses local Supabase)
if [[ -n "${SUPABASE_DB_URL:-}" ]]; then
    TABLE_COUNT=$(python3 -c "
import psycopg2, sys
try:
    conn = psycopg2.connect('${SUPABASE_DB_URL}', connect_timeout=5)
    cur = conn.cursor()
    cur.execute(\"SELECT COUNT(*) FROM pg_tables WHERE schemaname='public'\")
    print(cur.fetchone()[0])
    conn.close()
except Exception as e:
    print(f'error: {e}', file=sys.stderr)
    print('0')
" 2>/dev/null)
    if [[ "$TABLE_COUNT" -ge 20 ]]; then
        pass "Local Supabase: $TABLE_COUNT tables in public schema (migration applied)"
    elif [[ "$TABLE_COUNT" -gt 0 ]]; then
        warn "Local Supabase: only $TABLE_COUNT tables (expected 20 — check migration)"
    else
        warn "Local Supabase not reachable or has no tables (operator must start it)"
    fi
fi

# Check remote Supabase is reachable
if [[ -n "${SUPABASE_URL:-}" ]]; then
    SUPA_HTTP=$(curl -s -o /dev/null -w "%{http_code}" "${SUPABASE_URL}/rest/v1/" \
        -H "apikey: ${SUPABASE_ANON_KEY:-}" 2>/dev/null)
    if [[ "$SUPA_HTTP" == "200" ]]; then
        pass "Remote Supabase reachable at $SUPABASE_URL"
    else
        warn "Remote Supabase returned HTTP $SUPA_HTTP"
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
