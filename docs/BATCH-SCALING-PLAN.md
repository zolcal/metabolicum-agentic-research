# Batch Scaling Plan — From 10 to 700 Markers

> **Status:** Draft — model-usage architecture first, implementation second.  
> **Date:** 2026-05-25  
> **Scope:** Phase 2+ pipeline scaling, cost control, and model routing strategy.

---

## 1. The Model-Usage Problem (address this first)

Current pilot cost per source: **~$0.10** (full Stage 2 chain on qwen3.7-max).

| Scale | Sources | Cost at $0.10/source | Time at 10 min/source |
|-------|---------|---------------------|----------------------|
| Pilot (5 markers) | 5 | $0.50 | ~50 min |
| Wave 1 (108 markers) | ~300 | **$30** | ~50 hours |
| Full set (700 markers) | ~2,000 | **$200** | ~330 hours |

At $30/month DashScope budget, the current approach is **not viable** beyond the pilot.

### 1.1 Model tier strategy (revised post-cost analysis)

**Critical finding:** Cloud `qwen3.7-max` is **not** a cheap open-weight model. It is Alibaba's flagship API priced like GPT-5 (~$1.60/M input + $6.40/M output). The $0.10/source burn rate from the pilot was real and unsustainable. The actual free Qwen is the **local llama.cpp Qwen 3.6 27B** on the 5060 Ti.

Revised tier strategy — match compute cost to stage criticality:

| Tier | Model | Role | Cost | When to use |
|------|-------|------|------|-------------|
| **T0 — Free** | Local Qwen 3.6 27B MTP | Bulk extractor, tagger, legal reviewer | $0 | High-volume stages where determinism > brilliance |
| **T1 — Flat-rate** | MiniMax M2.7-highspeed | Council extractor (Stage 3, one of three families) | $80/mo unlimited | Where you need a Chinese-family voice without per-token bleed |
| **T2 — Cheap cloud** | Gemini 2.5 Flash (OpenRouter) | Council reviewer | ~$0.015/review | Google-family sanity check on quotes and sources |
| **T3 — Premium** | GPT-5-mini (OpenRouter) | Council decider, structurer fallback | ~$0.03–0.05/call | OpenAI-family final judgment and schema enforcement |
| **T4 — Chat** | GPT-5.5 (existing $100/mo sub) | Hermes TUI, interactive reasoning | Sunk cost | Chat / dashboard / human-facing only |

**Hard rule:** Chat models (T4) and pipeline models (T0–T3) must never share a default. Workers must resolve endpoints by **role**, not by Hermes gateway default.

### 1.2 Cost per source under new strategy

| Stage | Old (all qwen3.7-max) | New (tiered) |
|-------|----------------------|--------------|
| Extractor | $0.07 (qwen3.7-max) | **$0** (local Qwen) |
| Tagger | $0.05 (qwen3.7-max) | **$0** (local Qwen) |
| Structurer | $0.06 (qwen3.7-max) | **$0.03** (GPT-5-mini or local Qwen) |
| Council extractor | $0.05 (qwen3.7-max) | **$0** (MiniMax, flat-rate) |
| Council reviewer | $0.02 (Gemini Flash) | **$0.015** (Gemini Flash) |
| Council decider | $0.03 (GPT-5-mini) | **$0.03** (GPT-5-mini) |
| **Total per source (Stage 2 only)** | **$0.18** | **$0.03** |
| **Total per claim (Stage 3 council)** | **$0.10** | **$0.045** |

**Savings: 6× cheaper on extraction, 2× cheaper on council.**

### 1.3 Further optimization: pre-screen before any LLM

Add a **deterministic pre-screen** that runs before T0:

```python
def prescreen(text, marker_terms):
    has_numbers = bool(re.search(r'\d+(?:\.\d+)?\s*(?:mg/dL|nmol/L|%|μIU/mL)', text))
    has_markers = any(term in text.lower() for term in marker_terms)
    return has_numbers and has_markers
```

This eliminates **~70% of fetched pages** before any LLM call. At scale, this is the difference between $200 and $60.

### 1.4 Local LLM throughput reality

Local Qwen 3.6 27B MTP on llama-server:
- **Speed:** ~6 minutes/source (single slot, no batching)
- **Throughput:** ~10 sources/hour
- **Context limit:** 8K tokens (some long transcripts won't fit)

For 300 sources (108-marker wave):
- Sequential: **30 hours**
- Parallel (4× llama-server on different ports): **~8 hours**

**Recommendation:** Run local extraction overnight or on a dedicated batch machine. Reserve cloud qwen3.7-max for structurer only.

### 1.5 Council stage cost (Phase 2)

Stage 3 council (extractor + reviewer + decider) requires **three independent model families** (§05). The new trio:

| Council voice | Model | Family | Cost per claim |
|--------------|-------|--------|---------------|
| council_extractor | MiniMax M2.7-highspeed | Chinese (non-Alibaba) | **$0** (flat-rate) |
| council_reviewer | Gemini 2.5 Flash (OpenRouter) | Google | ~$0.015 |
| council_decider | GPT-5-mini (OpenRouter) | OpenAI | ~$0.03 |
| **Total per claim** | | | **~$0.045** |

At 5 claims per marker × 108 markers = 540 claims:
- **Council cost: ~$24** (vs. ~$54 with qwen3.7-max)

This is acceptable **if** the council runs only on claims that pass Stage 2. It is not acceptable to run council on every candidate source.

**Why MiniMax replaces qwen3.7-max:** The three-family rule is about *independent training corpora and teams*, not specific brand names. MiniMax (Chinese, independent of Alibaba/Moonshot/Zhipu) satisfies the independence requirement while providing a fixed cost ceiling. Document the swap in a one-paragraph addendum to §05 so the rationale is auditable.

---

## 2. The 10-Marker Validation Protocol

Before scaling to 108 or 700, validate the tiered model strategy on **10 diverse markers**.

### 2.1 Marker selection criteria

Pick 10 markers that represent the diversity of the full set:

| # | Marker | SM anchor count | Pilot status | Why include |
|---|--------|----------------|--------------|-------------|
| 1 | apob | High | ✅ Has claims | Baseline — known good |
| 2 | hba1c | High | ❌ 0 claims | High-priority, needs better sources |
| 3 | fasting-insulin | High | ❌ 0 claims | High-priority, needs better sources |
| 4 | lpa | Medium | ⚠️ Weak claims | Edge case — conceptual content |
| 5 | tg-hdl-ratio | Medium | ⚠️ Weak claims | Edge case — ratio math |
| 6 | homa-ir | High | Not in pilot | Calculator/index marker |
| 7 | crp | High | Not in pilot | Inflammatory marker |
| 8 | uric-acid | Medium | Not in pilot | Metabolic syndrome marker |
| 9 | vitamin-d | High | Not in pilot | Common supplement marker |
| 10 | testosterone | High | Not in pilot | Hormone marker |

### 2.2 Validation steps (per marker)

**Step 0 — Discovery (SearXNG, free):**
1. Select top 3 practitioners for marker from registry (tier + MO + no COI)
2. Run SearXNG: `"{marker}" "{practitioner_name}" target threshold`
3. Fetch top 5 result pages with trafilatura
4. Score each page: numeric threshold count × marker mention count
5. Keep top 3 scored pages

**Step 1 — Pre-screen (deterministic, free):**
1. Regex scan each page for marker terms + numeric values
2. Discard pages with 0 matches
3. Build temporary fixtures for survivors

**Step 2 — Local extraction (T0, free):**
1. Run Stage 2a (extractor) on local Qwen
2. Run Stage 2b (tagger) on local Qwen
3. Keep fixtures that produce ≥1 claim with valid marker

**Step 3 — Cloud structurer (T1, cheap):**
1. Run Stage 2c (structurer) on qwen3.7-max with JSON schema
2. Write recommendations to DB
3. Track cost per marker

**Step 4 — Report:**
1. Claims per marker
2. Recommendations per marker
3. Cost per marker
4. Time per marker

### 2.3 Success criteria for 10-marker validation

| Metric | Target | Fail threshold |
|--------|--------|---------------|
| Yield (markers with ≥1 rec) | ≥6/10 (60%) | <4/10 |
| Avg cost per marker | ≤$0.50 | >$1.00 |
| Avg time per marker | ≤20 min | >40 min |
| Invalid marker leakage | 0 | >0 |
| Schema violations | 0 | >0 |

If validation passes, scale to 108. If fails, diagnose which stage (discovery, pre-screen, local extraction, or structurer) is the bottleneck.

---

## 3. Scaling Architecture (108 → 700 markers)

### 3.1 Phase 0: Batch discovery

**Input:** All markers from `sm_anchors` table + `practitioner_registry.json`

**Process:**
```python
for marker in markers:
    practitioners = rank_practitioners(marker, top_n=3)
    for practitioner in practitioners:
        results = searxng_search(f'"{marker}" "{practitioner.name}" target')
        for result in results[:5]:
            page = trafilatura_fetch(result.url)
            score = score_page(page, marker)
            if score > 0:
                queue.append((marker, result.url, score, page))
```

**Output:** `runs/batch-discovery/candidates.jsonl` — ranked candidates per marker

**Cost:** $0 (SearXNG is local)

### 3.2 Phase 1: Pre-screen

**Input:** Candidate queue

**Process:**
```python
for candidate in candidates:
    if prescreen(candidate.page, candidate.marker_terms):
        fixtures.append(build_fixture(candidate))
```

**Output:** Pre-screened fixtures ready for extraction

**Expected survival rate:** ~30% of candidates (70% eliminated)

### 3.3 Phase 2: Local extraction (bulk)

**Input:** Pre-screened fixtures

**Process:**
```python
for fixture in fixtures:
    claims = run_extractor_local(fixture)
    if len(claims) > 0:
        tagged = run_tagger_local(claims, fixture)
        viable.append((fixture, claims, tagged))
```

**Output:** Viable fixtures with claims + tagger output

**Cost:** $0 (local Qwen)

**Time:** ~6 min/fixture sequential, ~1.5 min/fixture with 4× parallel

### 3.4 Phase 3: Cloud structurer (selective)

**Input:** Viable fixtures from Phase 2

**Process:**
```python
for fixture, claims, tagged in viable:
    recs = run_structurer_cloud(claims, tagged, fixture)
    db.write_recommendations(recs)
    cost_tracker.record(fixture.marker, recs)
```

**Output:** Structured recommendations in DB

**Cost:** ~$0.03 per viable fixture

**Guardrail:** Hard stop at $5.00 per batch run. If a marker exceeds $0.50 with 0 yield, flag for manual review.

### 3.5 Phase 4: Batch council (future)

**Input:** Approved `biomarker_claims` rows per marker

**Process:**
```python
for marker in markers:
    claims = db.get_claims(marker, status='approved')
    for claim in claims:
        council_result = run_council(claim)
        if council_result.approved:
            db.promote_to_biomarker_claim(claim)
        else:
            db.quarantine(claim, reason=council_result.reason)
```

**Cost:** ~$0.10 per claim

**Batching:** Group claims by marker and run council in parallel where possible.

---

## 4. DB Schema Additions for Scale

To support 700 markers, we need tracking tables:

```sql
-- Batch run tracking
CREATE TABLE batch_runs (
    run_id TEXT PRIMARY KEY,
    started_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ,
    marker_count INT,
    source_count INT,
    claim_count INT,
    recommendation_count INT,
    total_cost_usd DECIMAL(10,4),
    status TEXT CHECK (status IN ('running', 'completed', 'stopped'))
);

-- Per-marker cost tracking
CREATE TABLE batch_marker_costs (
    run_id TEXT REFERENCES batch_runs(run_id),
    marker TEXT,
    sources_processed INT,
    claims_extracted INT,
    recommendations INT,
    cost_usd DECIMAL(10,4),
    time_seconds INT,
    status TEXT,
    PRIMARY KEY (run_id, marker)
);
```

---

## 5. Implementation Order

1. **This document** — review and approve model-usage strategy
2. **10-marker validation** — run Steps 0–4 on 10 markers, measure yield/cost/time
3. **Batch discovery script** — build Phase 0 (SearXNG + scoring)
4. **Batch pre-screen script** — build Phase 1 (deterministic filter)
5. **Batch local extraction** — build Phase 2 (local Qwen bulk runner)
6. **Batch cloud structurer** — build Phase 3 (selective cloud runs with cost guardrails)
7. **108-marker wave** — full run on current wave
8. **Council integration** — wire Phase 4 for multi-model validation
9. **700-marker scaling** — optimize throughput for full registry

---

## 6. Operational Prerequisites (do before wave-0)

These are not optional — they are load-bearing for cost control and scientific rigor.

### 6.1 Worker vs. gateway isolation

Right now `./run-hermes` sets `HERMES_HOME` to `hermes/gateway-home`, which means any pipeline worker launched from the same environment inherits the gateway's default model (gpt-5.5). A misrouted role call could silently send Stage-2 extraction to your $100/mo chat subscription.

**Fix:** Build a separate worker launcher that uses a **disposable per-task HERMES_HOME**:
```bash
# run-hermes-worker — pipeline-only, no gateway state
HERMES_HOME=$(mktemp -d) /home/zoltan/miniconda3/envs/hermes/bin/python -m code.pipeline.ingest ...
```

The worker reads only `config/llm-endpoints.yaml` (role-based routing) and never touches `hermes/config.yaml` (gateway defaults). Acceptance tests #5 (state isolation) and #7 (restriction enforcement) verify this.

### 6.2 Re-enable web toolset

The council reviewer (Stage 3) must re-fetch source URLs to verify verbatim quotes. Stage 4 provenance needs HTTP for PMID/DOI resolution. Stage 5 legal review uses Playwright for license checks.

**Fix:** In `hermes/config.yaml`, remove `web` from `disabled_toolsets` (or remove the `disabled_toolsets` block entirely for workers).

### 6.3 Re-pin config files

The runbook says `hermes/config.yaml` and `hermes/SOUL.md` are SHA-256 pinned at install. If Hermes auto-expanded the live config and the pinned copy drifted, either:
- (a) Re-baseline the pinned copy to match the live one, or
- (b) Accept the SHA-256 invariant is decorative and document that.

Pick one story and stick to it. Half-pinned configs create confusion about what's authoritative.

## 7. Open Questions

1. **Local Qwen capacity:** Can we run 4× llama-server instances on the 5060 Ti for parallel extraction?
2. **SearXNG rate limits:** At 700 markers × 3 practitioners × 5 queries = 10,500 searches, will SearXNG throttle?
3. **Glossary coverage:** For 700 markers, do we have glossary terms? If not, tagger will skip most claims.
4. **MiniMax integration:** Is the $80/mo MiniMax subscription already active? Do we have API credentials?
5. **Council cost at scale:** 700 markers × 5 claims × $0.045 = ~$157. Is this acceptable?
6. **Storage:** 700 markers × 3 sources × 30KB transcripts = ~63MB of fixture data. Trivial.

---

## 7. Immediate Action

**Approve this plan, then run 10-marker validation.**

The validation will tell us:
- Whether the tiered model strategy actually saves money
- Whether local Qwen extraction quality is sufficient
- Whether pre-screen eliminates too many viable sources
- Whether we need better glossary coverage before scaling

Without the 10-marker validation, scaling to 108 or 700 is speculative.
