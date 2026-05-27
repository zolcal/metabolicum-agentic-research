# HANDOVER-SESSION-5

## Date
2026-05-26

## Summary
Preserve the current uncommitted Hermes 10-marker / Stage 2 batch-processing work before it is lost in the dirty tree.

## Current State
- The project is `/home/zoltan/Projects/metabolicum-agentic-research` and resolves to `/media/zoltan/4TSSD/metabolicum-agentic-research`.
- The intended runtime environment is the `hermes` conda env.
- Latest committed baseline is `5a12164 Phase 1 complete + handover session 3`.
- A large amount of useful work exists only in the dirty worktree: tracked modifications plus many untracked fixtures, docs, scripts, logs, and acceptance checks.

## Completed / Implemented But Uncommitted
- 10-marker fixture batch-processing work:
  - Validation script: `scripts/run_10marker_validation.py`.
  - Run outputs under `runs/10-marker-validation/`.
  - Latest complete summary inspected: `runs/10-marker-validation/20260526-221106/summary.json`.
  - That run processed 14 fixtures, produced 29 recommendations, and had 1 JSON parse error on `vitamin-d`.
- Stage 2 extraction/tagging recovery:
  - `code/pipeline/stages.py` now contains stronger extractor normalization, chunking/fallback behavior, marker tag normalization, and semantic fallback integration.
  - `code/pipeline/ingest.py` now carries hybrid model routing / threshold handling through the ingest flow.
  - `prompts/01-content-extractor.md` enforces marker-bearing context in quotes.
  - `prompts/02-marker-tagger.md` and `code/schemas/marker_tagger.schema.json` constrain tagger output and avoid fake marker slugs.
- Table extraction:
  - `code/discovery/tables.py` and `docs/TABLE-EXTRACTION-TOOLS.md` document and implement HTML/PDF/image table extraction paths.
  - Table-derived text is intended to be appended as labelled source-derived blocks; no table interpretation should be invented by the extractor.
- Stage 1 discovery:
  - `code/discovery/web.py` implements public web discovery and source fixture creation.
  - `code/discovery/youtube.py` is present as an untracked YouTube inventory/ranking/transcript-cache implementation.
  - `docs/agentic-workflow/youtube-transcript-discovery.md` documents the inventory-first YouTube contract.
- Marker-group / practitioner association:
  - `input/practitioner_registry.json`, `input/practitioner_aliases.json`, and `supabase/seeds/0001_practitioner_roster.sql` were expanded.
  - `docs/agentic-workflow/practitioner-registry-sync-report-2026-05-26.md` records the sync: 125 registry entries, 522 aliases added, 84 surfaces added, including 31 YouTube surfaces.
  - `input/marker_glossary.json`, `input/marker_categories.yaml`, and `input/topic_descriptors.yaml` support broader marker grouping / semantic association.
- Model-routing / local-model evaluation:
  - `config/llm-endpoints.yaml` now routes bulk Stage 2 through `gemma4-local` with `deepseek-direct-chat` fallback.
  - `deepseek-direct-chat` is configured as non-thinking DeepSeek V4 Flash for cheap large-context extraction fallback.
  - `code/pipeline/semantic_fallback.py` adds e5 embedding fallback for marker tagging.
  - Acceptance scripts include `code/acceptance/verify_hybrid_extractor.py`, `quality_check_stage2_extractor.py`, `quality_check_council_extractor.py`, and `verify_routing_isolation.py`.

## Latest Observed 10-Marker Results
From `runs/10-marker-validation/20260526-221106/summary.json`:

- `markers_total`: 10
- `fixtures_processed`: 14
- `errors`: 1
- `total_recommendations`: 29
- Recommendation counts:
  - `apob`: 3
  - `fasting-insulin`: 5
  - `lpa`: 4
  - `igf-1`: 5
  - `crp-standard`: 3
  - `hdl-cholesterol`: 1
  - `uric-acid`: 4
  - `fructosamine`: 4
  - `hba1c`: 0
  - `vitamin-d`: 0 due to JSON parse error

## Known Issues
- Work is not committed; preserve it before any cleanup or refactor.
- `vitamin-d` failed with JSON parsing in the latest complete 10-marker summary.
- `hba1c` still has weak/no numeric output from available fixtures.
- Some outputs need quality review for over-broad marker tagging or non-target marker recommendations.
- The local-model log `runs/10-marker-validation-local-final.log` appears truncated at 33 lines and should not be treated as complete validation evidence.
- There are generated/runtime files in the tree (`hermes/gateway-home`, run logs, pycache-like artifacts). Separate signal from runtime noise before committing.

## Suggested Next Steps
1. Run a scoped `git status --short` and decide commit batches before touching behavior.
2. Commit in logical chunks:
   - Stage 2 recovery and schema/prompt changes.
   - Discovery/table extraction.
   - Practitioner registry and marker grouping data.
   - YouTube inventory/transcript cache.
   - 10-marker validation scripts and selected fixture artifacts.
3. Re-run focused verification in the `hermes` env after staging:
   - `python -m py_compile code/pipeline/stages.py code/pipeline/ingest.py code/pipeline/semantic_fallback.py scripts/run_10marker_validation.py`
   - `python code/acceptance/verify_hybrid_extractor.py`
   - targeted 10-marker validation after fixing `vitamin-d`.
4. Add an explicit quality-review pass over latest `runs/10-marker-validation/20260526-221106/summary.json` before treating recommendations as pipeline-ready.

## Files Of Interest
- `config/llm-endpoints.yaml` - current role/model routing.
- `code/pipeline/stages.py` - Stage 2 extraction/tagging/structuring core.
- `code/pipeline/ingest.py` - ingest orchestration and hybrid threshold routing.
- `code/pipeline/semantic_fallback.py` - e5 marker fallback.
- `code/discovery/web.py` - public web discovery.
- `code/discovery/tables.py` - table extraction.
- `code/discovery/youtube.py` - YouTube inventory/ranking/cache work.
- `scripts/run_10marker_validation.py` - validation runner.
- `runs/10-marker-validation/20260526-221106/summary.json` - latest complete inspected batch summary.
- `docs/BATCH-SCALING-PLAN.md` - cost/routing strategy.
- `docs/agentic-workflow/practitioner-registry-sync-report-2026-05-26.md` - registry expansion report.
- `docs/agentic-workflow/youtube-transcript-discovery.md` - YouTube Stage 1 contract.
