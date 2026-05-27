# Hermes Implementation Gap Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the recovered Hermes research work into a coherent, verified implementation of the documented workflow.

**Architecture:** Stabilize broken contracts first, then add missing executable stages. Keep Stage 1 discovery and Stage 2 extraction as the current working base, and implement Stage 3-6 as small Python orchestration modules over the existing prompts, schemas, `PipelineRun`, and `DBClient`.

**Tech Stack:** Python 3.11 in conda env `hermes`, Supabase/Postgres, JSON Schema, OpenAI-compatible model clients, SearXNG/YouTube API, local run artifacts under `runs/`.

---

## Audit Snapshot

Baseline inspected:

- Repository: `/home/zoltan/Projects/metabolicum-agentic-research`
- Current HEAD: `25b39c2 CRASH-RECOVERY-2: preserve untracked source, docs, fixtures, inputs, and run logs after system crash on 2026-05-26`
- Dirty state at audit time: only `.claude-temp/youtube-seed-bad-surfaces.json` untracked
- Latest complete 10-marker run: `runs/10-marker-validation/20260526-221106/summary.json`

What is already real:

- Stage 1 web discovery exists in `code/discovery/web.py`.
- Stage 1 YouTube inventory/ranking/cache exists in `code/discovery/youtube.py`.
- Table extraction exists in `code/discovery/tables.py`.
- Stage 2 extraction/tagging/structuring exists in `code/pipeline/stages.py` and `code/pipeline/ingest.py`.
- 10-marker validation exists in `scripts/run_10marker_validation.py`.
- Registry, aliases, marker categories, and topic descriptors are present.
- DB schema has tables for later stages: `biomarker_claims`, `provenance`, `legal_reviews`, `research_studies`, `marker_content_sections`, and links.

Highest-risk gaps:

- `docs/agentic-workflow/07-legal-and-ip-agent.md` was overwritten with the YouTube transcript doc content, while the same YouTube content also exists correctly at `docs/agentic-workflow/youtube-transcript-discovery.md`.
- Temp-file policy is violated by `/tmp`, `mktemp`, and Python `TemporaryDirectory()` defaults.
- Stage state contract is inconsistent: `code/schemas/state.schema.json` requires `schema_version` and stage names like `stage_2_extraction`, while `code/state.py` writes stages like `sources` and default run ids like `20260526T...`.
- `code/pipeline/ingest.py` best-effort quarantine writes use `rejection_stage: "ingestion"` and a `payload` key, neither of which match `supabase/migrations/0001_initial.sql`.
- Stage 3-6 are mostly prompts/schema/state scaffolding; there are no executable pipeline modules for council, provenance, legal review, or assembly/export.
- `scripts/run-stage.sh` maps `council` to only `04c-council-decider.md`, skipping `04a` and `04b`, and validates all stages as if they returned `extracted_claim.schema.json`.
- The 10-marker validation produces useful output, but it is not yet a production gate: latest run has one `vitamin-d` JSON parse error, zero HbA1c recommendations, and outputs needing target-marker quality review.

---

### Task 1: Restore The Legal/IP Spec

**Files:**
- Modify: `docs/agentic-workflow/07-legal-and-ip-agent.md`
- Read: `docs/agentic-workflow/youtube-transcript-discovery.md`

- [ ] **Step 1: Restore the legal/IP content from the last known-good commit**

Run:

```bash
git show 5a12164:docs/agentic-workflow/07-legal-and-ip-agent.md > docs/agentic-workflow/07-legal-and-ip-agent.md
```

Expected: `docs/agentic-workflow/07-legal-and-ip-agent.md` begins with `# Legal and IP agent`.

- [ ] **Step 2: Confirm YouTube content remains in its own doc**

Run:

```bash
head -1 docs/agentic-workflow/youtube-transcript-discovery.md
```

Expected:

```text
# YouTube Transcript Discovery
```

- [ ] **Step 3: Verify no duplicate YouTube title remains in the legal doc**

Run:

```bash
rg -n "^# YouTube Transcript Discovery|^# Legal and IP agent" docs/agentic-workflow/07-legal-and-ip-agent.md docs/agentic-workflow/youtube-transcript-discovery.md
```

Expected: legal doc has only `# Legal and IP agent`; YouTube doc has only `# YouTube Transcript Discovery`.

- [ ] **Step 4: Commit**

Run:

```bash
git add docs/agentic-workflow/07-legal-and-ip-agent.md
git commit -m "docs: restore legal and IP agent spec"
```

---

### Task 2: Remove `/tmp` And Default TemporaryDirectory Usage

**Files:**
- Modify: `code/acceptance/check_youtube_inventory.py`
- Modify: `code/discovery/tables.py`
- Modify: `docs/BATCH-SCALING-PLAN.md`
- Modify: `docs/superpowers/plans/2026-05-26-youtube-inventory-transcript-cache.md`

- [ ] **Step 1: Replace acceptance temp dirs with project-local temp dirs**

In `code/acceptance/check_youtube_inventory.py`, add near the `SAMPLE` constant:

```python
PROJECT_TMP = ROOT / "runs" / "_tmp" / "youtube_inventory_acceptance"
PROJECT_TMP.mkdir(parents=True, exist_ok=True)
```

Then replace every:

```python
with TemporaryDirectory() as tmp:
```

with:

```python
with TemporaryDirectory(dir=PROJECT_TMP) as tmp:
```

- [ ] **Step 2: Replace table extraction temp dir with project-local temp dir**

In `code/discovery/tables.py`, add a project-local temp root:

```python
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROJECT_TMP = PROJECT_ROOT / "runs" / "_tmp" / "table_extraction"
```

Inside `_extract_pdf_tables_pdftotext`, before creating the temporary directory:

```python
PROJECT_TMP.mkdir(parents=True, exist_ok=True)
```

Then change:

```python
with tempfile.TemporaryDirectory() as tmp:
```

to:

```python
with tempfile.TemporaryDirectory(dir=PROJECT_TMP) as tmp:
```

- [ ] **Step 3: Replace `/tmp` and `mktemp` examples in docs**

Replace `/tmp/...` examples with paths under `runs/_tmp/...`. Replace `mktemp -d` in `docs/BATCH-SCALING-PLAN.md` with an explicit `runs/_tmp/hermes-worker-home/<run-id>` example.

- [ ] **Step 4: Verify no temp-policy violations remain**

Run:

```bash
rg -n "TemporaryDirectory\\(\\)|/tmp|mktemp" code scripts docs/superpowers docs/agentic-workflow docs/BATCH-SCALING-PLAN.md
```

Expected: no output, or only explicit comments explaining why a match is not a write path.

- [ ] **Step 5: Commit**

Run:

```bash
git add code/acceptance/check_youtube_inventory.py code/discovery/tables.py docs/BATCH-SCALING-PLAN.md docs/superpowers/plans/2026-05-26-youtube-inventory-transcript-cache.md
git commit -m "fix: keep temporary artifacts inside project runs"
```

---

### Task 3: Align Run State Schema And PipelineRun

**Files:**
- Modify: `code/state.py`
- Modify: `code/schemas/state.schema.json`
- Create: `code/acceptance/check_state_contract.py`

- [ ] **Step 1: Add a state contract acceptance check**

Create `code/acceptance/check_state_contract.py` that:

- creates a run id shaped like `2026-05-27T120000Z-state-contract`
- writes states for all canonical stages
- validates every `state.json` against `code/schemas/state.schema.json`
- uses `runs/_tmp/state_contract/` and deletes only that project-local scratch directory if needed

Expected canonical stage keys:

```python
CANONICAL_STAGES = [
    "stage_1_discovery",
    "stage_2_extraction",
    "stage_2_tagging",
    "stage_2_structuring",
    "stage_3_council",
    "stage_4_provenance",
    "stage_5_legal",
    "stage_6_assembly",
]
```

- [ ] **Step 2: Update `PipelineRun.create()` to use schema-valid run ids**

Change default run id format from compact timestamp to:

```python
run_id = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
```

- [ ] **Step 3: Update `PipelineRun.write_stage_state()`**

Ensure every state object includes:

```python
"schema_version": "1",
```

Do not write non-canonical stage names into `state.json`. If caller code wants directories named `sources` or `council`, map them internally to the schema stage key.

- [ ] **Step 4: Run the acceptance check**

Run:

```bash
python code/acceptance/check_state_contract.py
```

Expected: prints a JSON summary with all 8 stages validated and exits `0`.

- [ ] **Step 5: Commit**

Run:

```bash
git add code/state.py code/schemas/state.schema.json code/acceptance/check_state_contract.py
git commit -m "fix: align run state writer with state schema"
```

---

### Task 4: Fix Stage 2 Quarantine Writes

**Files:**
- Modify: `code/pipeline/ingest.py`
- Test: `code/acceptance/check_ingest_quarantine_contract.py`

- [ ] **Step 1: Add a DB-free quarantine payload check**

Create `code/acceptance/check_ingest_quarantine_contract.py` with a fake DB object that records the quarantine row passed by `ingest_source()` when extraction fails. The test should assert:

- `rejection_stage == "extractor"`
- there is no `payload` key
- `rejection_codes` includes `stage_2_failure`
- `source_id`, `rejection_reason`, and timestamps can satisfy the SQL table shape

- [ ] **Step 2: Patch `ingest_source()` error handling**

In `code/pipeline/ingest.py`, replace:

```python
"rejection_stage": "ingestion",
"payload": {"source_url": source_url},
```

with:

```python
"rejection_stage": "extractor",
"reviewer_notes": f"source_url={source_url}",
```

- [ ] **Step 3: Run the DB-free check**

Run:

```bash
python code/acceptance/check_ingest_quarantine_contract.py
```

Expected: exit `0`, JSON summary indicates the fake quarantine row conforms to the migration enum.

- [ ] **Step 4: Commit**

Run:

```bash
git add code/pipeline/ingest.py code/acceptance/check_ingest_quarantine_contract.py
git commit -m "fix: make stage 2 quarantine rows match schema"
```

---

### Task 5: Add Executable Stage 3 Council

**Files:**
- Create: `code/pipeline/council.py`
- Modify: `code/db.py`
- Create: `code/acceptance/check_council_contract.py`
- Read: `prompts/04a-council-extractor.md`
- Read: `prompts/04b-council-reviewer.md`
- Read: `prompts/04c-council-decider.md`

- [ ] **Step 1: Add pure decision helpers first**

Implement pure helpers in `code/pipeline/council.py` before any LLM calls:

- `compare_claims(stage2_claim, council_extractor_output, reviewer_output) -> dict`
- `build_biomarker_claim_row(stage2_claim, decision, source_row) -> dict`
- `build_quarantine_row(stage2_claim, decision, reason) -> dict`

Acceptance behavior:

- material quote mismatch returns quarantine with `rejection_codes=["council_disagreement"]`
- verified quote + matching marker returns approval candidate
- financial conflict copied from practitioner registry decision facts when present

- [ ] **Step 2: Add `DBClient` helpers**

Add helpers in `code/db.py`:

- `insert_biomarker_claim(...)` already exists; keep it.
- Add `insert_claim_envelope_evaluation(...)`.
- Add `query_practitioner_commercial_interests(practitioner_id: str)`.

- [ ] **Step 3: Add DB-free council acceptance check**

Create `code/acceptance/check_council_contract.py` using fixture-like dicts. It must exercise approval and quarantine paths without network or model calls.

- [ ] **Step 4: Add optional live council runner**

In `code/pipeline/council.py`, add a CLI that accepts:

```bash
python -m code.pipeline.council --run-id <run> --claims-jsonl <path> --dry-run
```

The first implementation may support `--dry-run` only. It must write:

- `runs/<run-id>/council/accepted_claims.jsonl`
- `runs/<run-id>/council/rejected_claims.jsonl`
- `runs/<run-id>/council/state.json`

- [ ] **Step 5: Commit**

Run:

```bash
git add code/pipeline/council.py code/db.py code/acceptance/check_council_contract.py
git commit -m "feat: add executable stage 3 council contract"
```

---

### Task 6: Add Executable Stage 4 Provenance

**Files:**
- Create: `code/pipeline/provenance.py`
- Modify: `code/db.py`
- Create: `code/acceptance/check_provenance_contract.py`

- [ ] **Step 1: Implement deterministic paper locator parsing**

Add pure functions:

- `extract_locator(cited_paper: dict) -> dict`
- `slug_for_study(pmid: str | None, doi: str | None, title: str | None) -> str`
- `build_provenance_row(biomarker_claim_id, locator, status) -> dict`

No network in the first task.

- [ ] **Step 2: Add DB helpers**

Add:

- `insert_provenance(...)`
- `upsert_research_study(...)` already exists; confirm it handles PMID/DOI dedupe.

- [ ] **Step 3: Add acceptance check**

`code/acceptance/check_provenance_contract.py` should validate:

- PMID locator builds `pmid:<id>`
- DOI locator builds `doi:<doi>`
- missing locator becomes `resolution_status="unresolvable"`
- rows satisfy enum values in `supabase/migrations/0001_initial.sql`

- [ ] **Step 4: Commit**

Run:

```bash
git add code/pipeline/provenance.py code/db.py code/acceptance/check_provenance_contract.py
git commit -m "feat: add executable stage 4 provenance contract"
```

---

### Task 7: Add Executable Stage 5 Legal Review

**Files:**
- Restore/modify: `docs/agentic-workflow/07-legal-and-ip-agent.md`
- Create: `code/pipeline/legal.py`
- Modify: `code/db.py`
- Create: `code/acceptance/check_legal_contract.py`

- [ ] **Step 1: Implement deterministic legal pre-gates**

In `code/pipeline/legal.py`, add pure functions:

- `word_count_quote(quote: str) -> int`
- `classify_quote_length(source_type: str, quote: str) -> dict`
- `classify_license(license_value: str | None) -> dict`
- `build_legal_review_row(biomarker_claim_id: str, decision: dict) -> dict`

Default policy from the restored legal doc:

- long-form quote target: one sentence, preferably under 80 words
- no-license/custom-license: review required
- `CC BY-NC*`: reject/quarantine for commercial pipeline
- envelope facts are never legal support

- [ ] **Step 2: Add DB helper**

Add `insert_legal_review(...)` to `code/db.py`.

- [ ] **Step 3: Add acceptance check**

`code/acceptance/check_legal_contract.py` should test:

- short attributed blog quote approves at deterministic pre-gate level
- long quote returns `approve_with_modification` or `quarantine`
- non-commercial CC license rejects/quarantines
- generated row has `decision`, `rationale`, booleans, `feist_compilation_risk`, `eu_database_flag`

- [ ] **Step 4: Commit**

Run:

```bash
git add docs/agentic-workflow/07-legal-and-ip-agent.md code/pipeline/legal.py code/db.py code/acceptance/check_legal_contract.py
git commit -m "feat: add executable stage 5 legal review contract"
```

---

### Task 8: Add Stage 6 Assembly / Export Skeleton

**Files:**
- Create: `code/pipeline/assembly.py`
- Create: `code/acceptance/check_assembly_contract.py`
- Read: `docs/agentic-workflow/18-research-output-ingestion-contract.md`

- [ ] **Step 1: Implement deterministic export projection from approved claims**

In `code/pipeline/assembly.py`, implement pure builders:

- `build_source_artifact(source_row) -> dict`
- `build_range_fact(biomarker_claim_row) -> dict`
- `build_range_source_link(range_fact_id, source_id, biomarker_claim_id) -> dict`
- `derive_status(direction, claim_polarity, target_shape) -> str`

- [ ] **Step 2: Add acceptance check**

`code/acceptance/check_assembly_contract.py` should assert:

- every range fact references a `biomarker_claim_id`
- no free-form packet can be produced without approved claim rows
- status is one of the known color-policy aliases
- export JSON is deterministic after sorting

- [ ] **Step 3: Add dry-run CLI**

Add:

```bash
python -m code.pipeline.assembly --marker apob --run-id <run> --dry-run
```

It writes project-local:

- `runs/<run-id>/assembly/<marker>/artifact.json`
- `runs/<run-id>/assembly/<marker>/RUN_REPORT.md`

- [ ] **Step 4: Commit**

Run:

```bash
git add code/pipeline/assembly.py code/acceptance/check_assembly_contract.py
git commit -m "feat: add deterministic stage 6 assembly skeleton"
```

---

### Task 9: Repair `run-stage.sh` Or Demote It To Legacy

**Files:**
- Modify: `scripts/run-stage.sh`
- Modify: `scripts/run-worker.sh`
- Modify: `prompts/README.md`

- [ ] **Step 1: Choose one path**

Preferred path: demote `scripts/run-stage.sh` to a legacy/manual wrapper and make Kanban workers call Python modules:

- Stage 1: `python -m code.discovery.web` or `python -m code.discovery.youtube`
- Stage 2: `python -m code.pipeline.ingest`
- Stage 3: `python -m code.pipeline.council`
- Stage 4: `python -m code.pipeline.provenance`
- Stage 5: `python -m code.pipeline.legal`
- Stage 6: `python -m code.pipeline.assembly`

- [ ] **Step 2: Update worker dispatch table**

In `scripts/run-worker.sh`, map canonical stage names to Python module commands instead of a single generic Hermes prompt call.

- [ ] **Step 3: If keeping `run-stage.sh`, fix stage-specific prompt/schema behavior**

If not demoting it, `run-stage.sh` must:

- run council as `04a` then `04b` then `04c`
- validate extractor with `extracted_raw_claim.schema.json`
- validate tagger with `marker_tagger.schema.json`
- validate structurer with `extracted_claim.schema.json`
- validate legal with a legal-review schema
- never say every stage returns `extracted_claim.schema.json`

- [ ] **Step 4: Commit**

Run:

```bash
git add scripts/run-stage.sh scripts/run-worker.sh prompts/README.md
git commit -m "fix: route workers through stage-specific pipeline commands"
```

---

### Task 10: Promote 10-Marker Validation Into A Quality Gate

**Files:**
- Modify: `scripts/run_10marker_validation.py`
- Create: `code/acceptance/check_10marker_summary.py`
- Read/write: `runs/10-marker-validation/<run-id>/summary.json`

- [ ] **Step 1: Add target-marker gating**

`scripts/run_10marker_validation.py` should fail the run if a recommendation does not include the marker being validated unless the fixture explicitly declares a multi-marker target.

- [ ] **Step 2: Add parse-error retry or quarantine accounting**

When a fixture fails JSON parsing, the summary must record:

```json
{
  "status": "quarantined",
  "rejection_stage": "extractor",
  "rejection_codes": ["json_parse_error"]
}
```

- [ ] **Step 3: Add summary acceptance check**

`code/acceptance/check_10marker_summary.py` should read a summary path and enforce:

- no invalid marker slugs
- no schema-invalid recommendations
- every recommendation quote is grounded in its fixture transcript
- all errors are represented as quarantine-like records
- per-marker counts are printed

- [ ] **Step 4: Re-run latest summary through the checker**

Run:

```bash
python code/acceptance/check_10marker_summary.py runs/10-marker-validation/20260526-221106/summary.json
```

Expected now: likely fails because of `vitamin-d` parse error and target-marker quality issues. Use that failure as the exact repair list.

- [ ] **Step 5: Commit**

Run:

```bash
git add scripts/run_10marker_validation.py code/acceptance/check_10marker_summary.py
git commit -m "feat: enforce 10-marker validation quality gate"
```

---

### Task 11: Final Verification Pass

**Files:**
- All changed files

- [ ] **Step 1: Run offline/static checks**

Run:

```bash
python -m json.tool code/schemas/source_fixture.schema.json >/dev/null
python -m json.tool code/schemas/extracted_raw_claim.schema.json >/dev/null
python -m json.tool code/schemas/marker_tagger.schema.json >/dev/null
python -m json.tool code/schemas/extracted_claim.schema.json >/dev/null
python -m json.tool code/schemas/state.schema.json >/dev/null
python -m py_compile code/pipeline/stages.py code/pipeline/ingest.py code/pipeline/council.py code/pipeline/provenance.py code/pipeline/legal.py code/pipeline/assembly.py code/state.py
```

Expected: all commands exit `0`. If redirecting output, keep it to `/dev/null` or project-local paths, never `/tmp`.

- [ ] **Step 2: Run acceptance checks**

Run:

```bash
python code/acceptance/check_fixture_contract.py
python code/acceptance/check_youtube_inventory.py
python code/acceptance/check_state_contract.py
python code/acceptance/check_ingest_quarantine_contract.py
python code/acceptance/check_council_contract.py
python code/acceptance/check_provenance_contract.py
python code/acceptance/check_legal_contract.py
python code/acceptance/check_assembly_contract.py
```

Expected: all exit `0`.

- [ ] **Step 3: Run focused live/model checks only when services are up**

Run these only after confirming local services and keys:

```bash
./scripts/preflight.sh
python code/acceptance/verify_routing_isolation.py
python code/acceptance/verify_hybrid_extractor.py
```

Expected: preflight has no failures; routing isolation and hybrid extractor checks pass.

- [ ] **Step 4: Commit verification notes**

Update `HANDOVER-SESSION-5.md` or create the next handover with:

- commits made
- commands run
- failures remaining
- next marker-specific quality issues

Commit:

```bash
git add HANDOVER-SESSION-5.md
git commit -m "docs: record Hermes gap-closure verification"
```

---

## Execution Recommendation

Execute Tasks 1-4 first. They are contract repairs and should be low-risk.

Then execute Tasks 5-8 in order. They create the missing executable Stage 3-6 pipeline.

Task 9 should happen after Stage 3-6 modules exist, otherwise the worker script has nowhere reliable to dispatch.

Task 10 should be last before scaling, because it will expose real data-quality failures that are easier to interpret once the contracts are stable.
