# Hermes Operational Runbook

> **Audience:** the Hermes worker runtime. After installation, this is the entry-point document. It tells Hermes what each stage does, where to read inputs from, what schemas constrain its output, where to write results, and what "done" means per marker. Everything Hermes needs is reachable from this file.
> **Status:** v1.0 (2026-05-23). Pre-conditions section is a one-time gate; once it's green, all subsequent work is the pipeline doing its actual job.

---

## 1. How to read this

This document is the operational entry point. The full architectural spec lives in `docs/agentic-workflow/`; this runbook tells Hermes how to execute it. Stage flow:

```
Stage 1  Discovery         (one task per platform agent, parallel)
   ↓
Stage 2  Extraction        (per source, sequential: extractor → tagger → structurer)
   ↓
Stage 3  Validation council (three model families, per claim-marker pair)
   ↓
Stage 4  Provenance         (PMID/DOI resolution)
   ↓
Stage 5  Legal review       (quote length, license, ToS)
   ↓
Stage 6  Assembly           (project approved claims to §18 export shape)
```

Each stage has a role-locked prompt in `prompts/`, a tool manifest in `config/tools.yaml`, an output schema in `code/schemas/`, and a target table in the Supabase project. The runner (Hermes) orchestrates the stages; the worker (Hermes-subprocess) executes one stage of one task per invocation.

---

## 2. Pre-conditions (the install-time gate)

Every item below MUST be true before Hermes accepts its first task. The `scripts/preflight.sh` script asserts each one and fails loud on any miss. If preflight fails, fix the missing piece — do not proceed.

**Configuration:**
- `config/hermes-version.txt` matches the installed Hermes binary.
- `config/llm-endpoints.yaml` resolves; every active endpoint's `api_key_env` is set in the environment.
- `config/tools.yaml` per-stage manifests load.
- `hermes/SOUL.md` and `hermes/config.yaml` SHA-256s match the values recorded at install.

**Secrets:**
- `secrets/.env` exists, populated from `secrets/.env.example`, gitignored.
- `OPENROUTER_API_KEY`, `GOOGLE_API_KEY`, `DASHSCOPE_API_KEY`, `SUPABASE_URL`, `SUPABASE_DB_URL`, `YOUTUBE_API_KEY` all set.

**Persistence:**
- Supabase project `metabolicum-agentic-research` provisioned.
- `supabase/migrations/0001_initial.sql` applied (full §04 schema with FKs and CHECK constraints).
- `paradigm_ranges_canonical_color` and `range_facts_canonical_color` CHECK constraints active.

**Backend services:**
- llama-server reachable at `http://127.0.0.1:8080/v1` (Qwen 3.6 27B MTP, single slot).
- SearXNG container `metabolicum-searxng` running on `http://127.0.0.1:8888`.
- PubMed E-utilities reachable (preflight does one test fetch).

**Inputs (agent-visible, populated):**
- `input/sm-ranges/wave-0/` — 5 marker SM-anchor YAMLs (apob, fasting-insulin, hba1c, lpa, tg-hdl-ratio).
- `input/registry/marker-identity-registry.v1.yaml` — 1,110 markers.
- `input/marker_glossary.json` — pilot markers + aliases.
- `fixtures/sources/` — at least one cached source transcript per marker being processed.

**Contracts (agent-readable from project boundary):**
- `docs/agentic-workflow/` — full spec set (§04–§18, hermes-setup, REVIEW-2026-05-21).
- `docs/policies/RANGE-STATUS-COLOR-POLICY.md` — canonical alias table + 7-hex palette.
- `prompts/` — five role-locked prompts (extractor, tagger, structurer, council-decider, legal-reviewer).
- `code/schemas/state.schema.json`, `code/schemas/extracted_claim.schema.json`.

**Acceptance:**
- The 10 acceptance tests in `docs/agentic-workflow/hermes-setup.md` §4 all passed against `fixtures/sources/<first-fixture>.json`.

Once these are green, the runbook below is the operating manual.

---

## 3. Project layout (where Hermes reads/writes)

```
/                              project root, real or symlinked
├── code/
│   ├── llm_client.py          OpenAI-compatible adapter (role → endpoint)
│   └── schemas/
│       ├── state.schema.json          stage-handoff contract
│       └── extracted_claim.schema.json Stage-2 constrained-decoding target
├── config/
│   ├── llm-endpoints.yaml     endpoint registry (role-tagged)
│   ├── tools.yaml             per-stage tool manifests
│   └── hermes-version.txt     pinned Hermes tag/commit
├── docs/
│   ├── HERMES-RUNBOOK.md      this file
│   ├── agentic-workflow/      full spec set
│   └── policies/              vendored policies (color, etc.)
├── fixtures/
│   ├── sources/               cached source transcripts (acceptance + per-run inputs)
│   └── expected/wave-0/       end-product reference samples (gold standard, post-run)
├── hermes/
│   ├── SOUL.md                stateless task-executor persona
│   └── config.yaml            disable flags + restriction config
├── input/
│   ├── sm-ranges/             SM anchor YAMLs (wave-0 + waves 1/2/2b/3)
│   ├── registry/              practitioner + marker identity registry
│   └── marker_glossary.json   tagger alias table
├── prompts/
│   ├── 01-content-extractor.md
│   ├── 02-marker-tagger.md
│   ├── 03-demographic-structurer.md
│   ├── 04-council-decider.md
│   └── 05-legal-reviewer.md
├── runs/<run_timestamp>/      per-run artifacts (stage outputs, state.json, hermes-home)
├── output/                    final approved per-marker exports
└── supabase/migrations/       schema migrations (canonical research persistence)
```

Everything Hermes reads is under this tree. Anything not under this tree is not reachable; do not attempt cross-repo access.

---

## 4. Stage runbook

### Stage 1 — Discovery

**Purpose:** find candidate sources for a marker across configured platforms.

**Worker tasks (one per platform, parallel):**
- `x-discovery`, `youtube-discovery`, `podcast-discovery`, `telegram-discovery`, `blog-discovery`, `reddit-discovery`

**Input** (read from task payload + filesystem):
- Marker discovery brief (from caller)
- Practitioner registry: query `practitioners` table or read `input/registry/marker-identity-registry.v1.yaml`
- Sanitized envelope facts: query `research_target_envelopes WHERE readiness_state='ready'` and project per §17 boundary rules
- Stage 1 tool manifest from `config/tools.yaml` (`stage_1_discovery`)

**Prompt:** stage 1 does not currently have a checked-in prompt — discovery is parameter-driven (queries, registry lookups, semantic rerank) rather than free-form LLM extraction. See `docs/agentic-workflow/03-social-agents-spec.md` for the per-platform contract.

**Output:** `runs/<run_id>/discovery/<platform>.json` containing ranked source candidates. After all platform tasks complete, the runner produces `runs/<run_id>/discovery/ranked_sources.json` (the merged, deduplicated list).

**Success:** at least one source candidate per platform that supports the marker. Empty result is acceptable; it goes to the next stage as "no sources found via platform X."

**Failure modes:**
- Platform unreachable → record provider error, skip platform, do not fail the run.
- Rate-limited → backoff per provider policy, then skip if budget exceeded.
- No verifiable practitioner matches in registry → log and continue.

---

### Stage 2 — Extraction (per-source, sequential)

**Purpose:** turn one cached source transcript into one or more verbatim claims that conform to `MarkerRecommendation`.

**Worker tasks (sequential per source):**

| Sub-stage | Prompt | Endpoint role | Tools |
|---|---|---|---|
| 2a Extractor | `prompts/01-content-extractor.md` | `extractor` (qwen-local) | none — operates on cached transcript |
| 2b Tagger | `prompts/02-marker-tagger.md` | `tagger` (qwen-local) | none |
| 2c Structurer | `prompts/03-demographic-structurer.md` | `structurer` (qwen-local) | none |
| 2d Paradigm classifier | (inline in structurer prompt) | `paradigm_classifier` (qwen-local) | none |

**Input** (read from task payload + filesystem):
- `runs/<run_id>/sources/<source_id>/transcript.txt` (cached during Stage 1 or earlier)
- `input/marker_glossary.json` for tagger lookup
- `input/registry/marker-identity-registry.v1.yaml` for alias resolution
- Sanitized envelope facts (optional, for context only — must not flatten source granularity per §17)

**Output:** `runs/<run_id>/sources/<source_id>/extracted_claims.jsonl` — one JSON object per claim, each validating against `code/schemas/extracted_claim.schema.json`.

Constrained decoding: the LLM call sets `response_format: {type: json_schema, schema: <extracted_claim.schema.json>}`. Schema-violating output is rejected at the model layer before it reaches the runner.

**Success:** every emitted claim has:
- a verbatim quote that appears as a substring of the cached transcript (whitespace-normalized)
- at least one marker tag from the glossary
- no inferred demographic qualifiers (under-specified preserved as `applies_to: unspecified`)
- a paradigm label (SM, RC, or MO) — agentic pipeline emits MO by default; SM/RC come from non-agentic pipelines

**Failure modes:**
- Schema violation → schema layer rejects; runner sends to quarantine with `rejection_stage: 'extractor'`
- Verbatim quote not in transcript → quarantine with `rejection_codes: ['quote_not_in_source']`
- Invented marker tag → quarantine with `rejection_codes: ['hallucinated_marker_tag']`
- Empty output (no claims found) → record `claims_emitted: 0` and continue; not a failure

---

### Stage 3 — Validation council (three model families)

**Purpose:** validate each extracted claim against three independent model families before persisting it.

**Worker tasks (three parallel, per claim-marker pair):**

| Sub-role | Endpoint | Family |
|---|---|---|
| `council_extractor` | `dashscope-qwen-max` | Alibaba |
| `council_reviewer` | `openrouter-reviewer` (Gemini 2.5 Flash) | Google |
| `council_decider` | `openrouter-decider` (gpt-5-mini) | OpenAI |

**Input:**
- The claim being validated (one `MarkerRecommendation` from Stage 2)
- The fetched source URL (council_reviewer re-fetches fresh — not from cached transcript)
- `sm_anchors` row(s) for the marker (sanity-check reference)
- `practitioner_commercial_interests` rows for the speaker (conflict check)
- Sanitized envelope facts (per §17 — comparison only)

**Prompt:** `prompts/04-council-decider.md` (intentionally merges reviewer + decider responsibilities; the runner executes the same prompt across all three model families and applies the consensus rule)

**Output:** the runner compares the three JSON outputs and applies the **2-of-3 consensus rule** on three fields:
1. `decision` (approve | quarantine | reject)
2. `paradigm_assigned` (SM | RC | MO)
3. `financial_conflict_flag` (true | false)

Outcomes:
- **≥2 agree on all three** → emit `biomarker_claims` row with the majority values; record dissent in review notes
- **<2 agree on any of the three** → quarantine with `rejection_codes: ['council_disagreement']`

Council reviewer additionally writes:
- `reviewer_quote_verified` (true if verbatim quote substring-matches the freshly-fetched source, false otherwise)
- `reviewer_fetched_at` and `reviewer_fetched_url`
- `reviewer_fetch_status` (one of `verified_present | verified_absent | source_unreachable | cached_only | not_attempted`)

**Success criteria for a claim to advance:**
- 2-of-3 family agreement on decision, paradigm, conflict
- `reviewer_quote_verified = true` (or `reviewer_fetch_status = source_unreachable` with quarantine routing — see failure modes)
- SM anchor sanity check: if the claim diverges from the SM anchor by more than the configured threshold, `paradigm_divergence_flag` is set to `extreme` (informational; does not auto-reject)

**Output target:** `biomarker_claims` rows (Supabase) — one per claim-marker pair. Quarantine entries go to `quarantine` table.

**Failure modes:**
- Source URL temporarily unreachable during re-fetch → quarantine with `rejection_codes: ['source_unreachable']`; cached transcript exists for later human review but does not bypass the fresh-fetch requirement
- Council disagreement → quarantine as above; preserved for review, not silently dropped
- Paradigm reassignment by decider → recorded in review notes with original and revised values
- Direct competitor or undisclosed financial conflict → quarantine with `rejection_codes: ['financial_conflict_direct_competitor']` or `['financial_conflict_undisclosed']`; manual review required

---

### Stage 4 — Provenance resolution

**Purpose:** resolve cited PMIDs and DOIs against authoritative external sources.

**Worker task:** `provenance-resolver`

**Input:**
- Approved `biomarker_claims` rows (one or many at a time)
- Tools from `config/tools.yaml` `stage_4_provenance`: `paper-search-mcp` (PubMed, Crossref) + `biomcp`

**Logic:**
- For each claim's `cited_paper` field, attempt to resolve PMID via PubMed E-utilities
- If PMID resolves: insert/update `research_studies` row with full metadata; insert `provenance` edge with `resolution_status: 'resolved'`
- If multiple candidates match: insert edge with `resolution_status: 'ambiguous'`; flag for human review
- If no match: insert edge with `resolution_status: 'unresolvable'`
- Update `biomarker_claims.provenance_status` to `resolved | ambiguous | unresolvable`

**Success criteria:**
- ≥80% of cited papers resolved across approved claims for the marker (configurable threshold)
- Every resolved PMID has a corresponding `research_studies` row

**Failure modes:**
- PubMed E-utilities rate-limited → backoff per policy; if quota exhausted, defer remaining claims to next run
- Network unreachable → fail the resolver task loud; do not mark provenance status

---

### Stage 5 — Legal review

**Purpose:** gate approved claims through quote-length, license, and ToS checks before they're eligible for export.

**Worker task:** `legal-reviewer`

**Prompt:** `prompts/05-legal-reviewer.md`
**Endpoint:** `legal_reviewer` (qwen-local)
**Tools:** `config/tools.yaml` `stage_5_legal` — `playwright-mcp` for license re-verification on source URLs only.

**Input:**
- Approved `biomarker_claims` rows (post-Stage-3, post-Stage-4)
- The source's recorded license (from `sources.license`)
- `docs/agentic-workflow/07-legal-and-ip-agent.md` policy rules

**Logic** (per claim):
- Quote length check: ≤ shortest contiguous excerpt needed; default ≤80 words for long-form sources
- License check: CC-BY / CC-BY-SA permits ingestion; CC-BY-ND permits quotes only; CC-BY-NC and variants → reject (Metabolicum is commercial)
- ToS check: source surface complies with §07 platform-by-platform rules
- Feist compilation-risk check: 'none' for line-by-line factual citation; 'high' if reproducing a table/compilation

**Output:** `legal_reviews` row with decision (`approve | approve_with_modification | quarantine | reject`); update `biomarker_claims.legal_status`.

**Success criteria:**
- All approved claims have `legal_status IN ('approved', 'approved_with_modification')`
- `approve_with_modification` is limited to non-substantive edits (quote truncation, attribution correction, license note addition) — never changes numeric claim or meaning

**Failure modes:**
- License unverifiable → quarantine with `rejection_stage: 'legal'`, `rejection_codes: ['license_unknown']`
- ToS violation detected → reject with `feist_compilation_risk: 'high'` and clear rationale

---

### Stage 6 — Assembly (per marker, MO export)

**Purpose:** project approved `biomarker_claims` rows for one marker into the §18 export shape and emit the per-marker artifact.

**Worker task:** `assembly`

**Input:**
- All `biomarker_claims WHERE marker = '<slug>' AND paradigm = 'MO' AND approval_status = 'approved' AND legal_status IN ('approved', 'approve_with_modification')`
- The marker's `practitioners`, `research_studies`, `provenance` rows transitively
- Sanitized envelope facts for `claim_envelope_evaluations`

**Logic:**
- Project each approved claim per §18 field mapping (see `docs/agentic-workflow/18-research-output-ingestion-contract.md` §"Field-level projection mapping")
- Apply status-derivation rules (§18) to compute `range_fact.status`
- Apply `canonical_color(status)` (`docs/policies/RANGE-STATUS-COLOR-POLICY.md`) to compute `range_fact.color`
- Construct `range_source_artifacts`, `range_fact_sources`, `marker_content_sections`, `research_studies`, `research_citations`
- Emit deterministic, canonicalized YAML (or JSON twin)

**Output:**
- `output/markers/<slug>/artifact.sql` — SQL INSERT statements (idempotent, ON CONFLICT clauses)
- `fixtures/expected/wave-0/<slug>.expected.yaml` overwritten with the assembled real-data version (replaces the placeholder template once real claims exist)

**Success criteria — definition of done for a marker:**

1. At least one approved `biomarker_claims` row with `paradigm = 'MO'` and `display_role = 'primary_metabolic_optimization_target'`
2. Every approved claim has `reviewer_quote_verified = true`
3. ≥80% of cited PMIDs/DOIs resolved (provenance_status IN ('resolved', 'ambiguous'); 'unresolvable' counts against the 80%)
4. All claims have `legal_status IN ('approved', 'approved_with_modification')`
5. §18 export emitted to `output/markers/<slug>/artifact.sql` and `fixtures/expected/wave-0/<slug>.expected.yaml`
6. `marker_content_sections` populated for at least these section types: `why_matters`, `paradigm_thresholds`, `mechanism`, `interpretation`, `limitations`, `evidence_badge`, `references`
7. Every citation key in `marker_content_sections.content.citations` resolves to a `research_studies` row referenced in `research_citations`
8. Renderer transitions from State C (paradigm_unavailable) to State A (defined_range) per `docs/policies/RANGE-STATUS-COLOR-POLICY.md`

When all eight hold for the marker, it ships.

**Failure modes:**
- Zero approved MO claims after Stages 2–5 → assembly emits `output/markers/<slug>/no-output.report.md` describing why; no SQL artifact
- Citation resolution failure (citation_key has no research_study) → assembly fails loud; do not emit a half-broken artifact

---

## 5. Council orchestration (runner responsibility)

The runner (Hermes outer orchestration, not the per-stage worker) is responsible for the council pass mechanics:

- For each Stage 2 output (one `MarkerRecommendation`), enqueue **three parallel council worker tasks** with identical input but different endpoint role assignments (`council_extractor`, `council_reviewer`, `council_decider`).
- Wait for all three to complete (or one to fail).
- Apply the 2-of-3 consensus rule on the three required fields.
- Record per-task dissent in the resulting `biomarker_claims.derivation_note` or in a sibling review log.

The runner does NOT execute the prompt itself; it orchestrates three worker subprocesses each running `prompts/04-council-decider.md` against a different endpoint. The consensus comparison is plain JSON diff with field-level equality checks.

If any of the three workers fails (LLM error, timeout, schema violation):
- Retry once with exponential backoff
- On second failure, treat that family as "no vote"; if the remaining two agree, proceed; if they don't, quarantine

---

## 6. Storage targets

| What | Where | Format |
|---|---|---|
| Per-stage handoff | `runs/<run_id>/<stage>/state.json` | JSON conforming to `code/schemas/state.schema.json` |
| Stage 1 ranked sources | `runs/<run_id>/discovery/ranked_sources.json` | JSON |
| Stage 2 extracted claims | `runs/<run_id>/sources/<source_id>/extracted_claims.jsonl` | JSON Lines, one `MarkerRecommendation` per line |
| Stage 2 source cache | `runs/<run_id>/sources/<source_id>/transcript.txt` | Plain text (canonical normalized form) |
| Stage 3 pre-council claims | `claims` table (Supabase) | rows per §04 |
| Stage 3 council-approved | `biomarker_claims` table | rows per §04 |
| Stage 3 quarantine | `quarantine` table | rows per §04 |
| Stage 4 provenance edges | `provenance` table | rows per §06 |
| Stage 4 resolved studies | `research_studies` table | rows per §04 |
| Stage 5 legal reviews | `legal_reviews` table | rows per §04 |
| Stage 6 per-marker SQL artifact | `output/markers/<slug>/artifact.sql` | SQL INSERTs (idempotent) |
| Stage 6 §18 export | `fixtures/expected/wave-0/<slug>.expected.yaml` | YAML per §18 |

Supabase connection comes from `SUPABASE_DB_URL` in `secrets/.env`. No production `metasync` credentials are available in this project; export to `metasync` is a separate controlled handoff outside Hermes's scope.

---

## 7. Failure modes (summary)

| Failure | Action | Quarantine code |
|---|---|---|
| Schema violation (any stage) | Reject at model layer; runner sends to quarantine | `schema_violation` |
| Verbatim quote not in source | Quarantine | `quote_not_in_source` |
| Source URL unreachable during re-fetch | Quarantine; preserve cached transcript | `source_unreachable` |
| Council disagreement (<2-of-3) | Quarantine | `council_disagreement` |
| Direct-competitor financial conflict | Quarantine pending manual review | `financial_conflict_direct_competitor` |
| Undisclosed financial conflict | Quarantine pending manual review | `financial_conflict_undisclosed` |
| Paradigm divergence (extreme) | Approve with `paradigm_divergence_flag: extreme`; surface in dashboard | (informational, not quarantine) |
| Provenance unresolvable | Mark `provenance_status: unresolvable`; surface in run report | (not quarantine) |
| Legal license unknown | Quarantine | `license_unknown` |
| ToS violation | Reject | `tos_violation` |
| Refutation with no matching supportive claim | Quarantine | `no_supportive_claim_to_contradict` |
| Persona drift detected (per SOUL.md §7) | Quarantine with partial state | `persona_drift_detected` |

Every quarantine entry includes `rejection_stage`, `rejection_reason`, `rejection_codes[]`, and `reviewer_notes`. Quarantine is not a silent drop — it preserves what failed and where, with a path to reopen after a fix.

---

## 8. References (the authoritative reading list)

| Reading | What for |
|---|---|
| `docs/agentic-workflow/00-executive-summary.md` | One-page architecture summary |
| `docs/agentic-workflow/02-architecture-overview.md` | Pipeline diagram, data flow |
| `docs/agentic-workflow/04-research-agents-spec.md` | Full §04 SQL schema, `MarkerRecommendation` Python contract |
| `docs/agentic-workflow/05-validation-council.md` | Council process detail (extractor → reviewer → decider) |
| `docs/agentic-workflow/06-provenance-and-chain-of-evidence.md` | PMID/DOI resolution rules |
| `docs/agentic-workflow/07-legal-and-ip-agent.md` | Quote length, license, ToS, Feist rules |
| `docs/agentic-workflow/10-orchestration-and-filesystem.md` | File-system layout, state.json shape, council orchestration rules |
| `docs/agentic-workflow/15-evidence-rating-system.md` | A1–E3 + P1/P2 evidence sub-grade enum |
| `docs/agentic-workflow/16-practitioner-directory-system.md` | Practitioner registry shape, prefix mapping, COI severity |
| `docs/agentic-workflow/17-research-target-envelopes.md` | Envelope firewall rules — agents see sanitized atomic facts only |
| `docs/agentic-workflow/18-research-output-ingestion-contract.md` | §18 export projection (range_facts, marker_content_sections, etc.) |
| `docs/agentic-workflow/hermes-setup.md` | Install configuration + 10 acceptance tests |
| `docs/policies/RANGE-STATUS-COLOR-POLICY.md` | Status alias table + 7-hex canonical palette + State A/B/C |
| `prompts/01-content-extractor.md` | Stage 2a prompt |
| `prompts/02-marker-tagger.md` | Stage 2b prompt |
| `prompts/03-demographic-structurer.md` | Stage 2c prompt |
| `prompts/04-council-decider.md` | Stage 3 prompt (run 3 times across model families) |
| `prompts/05-legal-reviewer.md` | Stage 5 prompt |
| `code/schemas/state.schema.json` | Stage handoff contract |
| `code/schemas/extracted_claim.schema.json` | Stage 2 constrained-decoding target |
| `config/llm-endpoints.yaml` | Endpoint registry (role → endpoint mapping) |
| `config/tools.yaml` | Per-stage tool manifests |
| `hermes/SOUL.md` | Stateless task-executor persona |

---

## 9. When something is unclear

If a contract appears ambiguous in any of the references above, the resolution rule is:

1. The **schemas** (`code/schemas/*.json`, `supabase/migrations/0001_initial.sql`) are the most concrete authority. If the schema says a field is required, it is required regardless of prose elsewhere.
2. **Policies** in `docs/policies/` (color, evidence-grade alias table, etc.) bind every component that touches the relevant data.
3. **§-numbered spec docs** (`docs/agentic-workflow/04`, `05`, `18`, ...) are the architectural authority for behavior not covered by schemas.
4. **This runbook** is the operational entry point but inherits authority from the documents above. If this file conflicts with a schema or policy, the schema or policy wins; fix this file.

Quarantine on uncertainty. Never invent. Never silently degrade. The architecture's job is to produce gold; failure surfaces in `quarantine` for review, not in partial or speculative output.
