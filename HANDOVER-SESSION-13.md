# HANDOVER-SESSION-13

## Date
2026-05-30

## Summary
Diagnosed and fixed the empty-brief / missing-practitioner-association problem: category cohorts in `marker_categories.yaml` had gone stale (the canonical builder was never re-run after the session-12 affinity enrichment). Re-ran the builder, re-assembled all 5 waves. Empty MO briefs 25→1; practitioner coverage 176→228/230. Committed + pushed to origin/main.

## Completed
- **Root-caused the practitioner association.** Association = `direct_affinity ∪ category_cohort` (`scripts/assemble_hermes_briefs.py::_practitioners_for`, already union-over-ALL-`gt.categories_for(marker)`). For the 25 empty briefs BOTH levers were 0: no video-evidence affinity AND their category had an empty cohort. The cohort field in `input/marker_categories.yaml` is built by `scripts/derive_marker_categories.py` as the exact affinity-union over each category's markers — but it was **never re-run after the session-12 hormone/kidney/electrolyte enrichment**, so e.g. `hormones` sat at 0 practitioners even though cortisol-am/dht/testosterone had direct affinities. Stale data, not a logic bug.
- **Fix (no new code):** re-ran `python -m scripts.derive_marker_categories` → cohorts refreshed from the current registry. Additive union — every changed category GREW, none shrank: hormones 0→11, kidney-function 0→19, electrolytes 0→15, blood-count 0→10, environmental 0→9, micronutrients 6→15, inflammatory 3→13, cardiovascular 29→35, glycemic-insulin 55→59, liver-function 14→15.
- **Re-assembled all 5 waves** (`python -m scripts.assemble_hermes_briefs --wave <w>`). Empty MO briefs **25→1**, practitioners **176→228/230**, source URLs **174→228/230** (cohort practitioners bring their website/RSS surfaces). All 5 waves pass `code/acceptance/check_hermes_briefs.py`.
- **Verified the test case** the user asked for: `input/hermes-briefs/wave-2/bio-t.yaml` was empty → now carries 11 hormone-cohort practitioners + 7 source URLs. (Confirmed regen is deterministic/idempotent first — byte-identical SHA when inputs unchanged.)
- **Committed `037f651` + pushed to origin/main** (via `env -u GITHUB_TOKEN git -c credential.helper='!gh auth git-credential' push origin main`; the `GITHUB_TOKEN` in `~/.secrets` is still an expired classic PAT). Origin: 0 ahead / 0 behind.
- Updated project memory (`marker_taxonomy_source_of_truth.md` + `MEMORY.md` index): retired the resolved "regenerate briefs from new categories" TODO; recorded the "re-run `derive_marker_categories.py` after ANY registry affinity change" lesson.

## In Progress
- None. Cohort refresh is complete, committed, pushed.

## Key Decisions
- **Re-run the canonical builder rather than write new code or hand-edit the YAML.** `derive_marker_categories.py` already implements option-A (affinity-union cohorts) — the file was just stale. No prod-divergence: cohorts derive from the (already-audited) registry `marker_affinity`, not from a separate prod list.
- **No channel audit needed.** No new affinities were ingested; cohorts are re-derived from already-audited registry entries, so no new attributions were created (the `audit_channels.py` gate guards ingestion, which didn't happen).
- **Cohort = category-level association**, not marker-specific. bio-t's 11 are practitioners *active in the `hormones` category* (each with ≥1 evidence-backed hormone affinity), same fallback that gives `alt` the liver cohort. Traceable, not fabricated; the downstream research agent treats them as starting pointers.
- **Scoped the commit to my paths only** (`marker_categories.yaml` + `input/hermes-briefs/`). The pre-existing uncommitted "alias-redesign + youtube-inventory" WIP thread (see below) was left untouched.

## Next Steps (priority order)
1. **Fresh search (the remaining lever).** Cohorts can't fill PMIDs (**116/230**) or videos (**85/230**) — only fresh YouTube/podcast search can. Also fixes the last empty brief, `cortisol-saliva` (`salivary` category has no affinity-backed practitioner). Procedure (unchanged from the kickoff prompt): in `metabolicum-research` run `python -m scripts.social_pipeline.discover <marker> --sources youtube` with `YOUTUBE_API_KEY` set → collect each `<marker>.json` of youtube signals into a dir → here `python -m scripts.practitioner_discovery.run <markers...> --run-id <id> --fresh-signals-dir <dir> -n 2 --write-registry` → `python -m scripts.derive_marker_categories` (NOW required after any affinity change) → re-assemble all waves → `audit_channels.py` before/after ingest. Both ends verified wired up this session; `YOUTUBE_API_KEY` is present in the shell env.
2. **Decide the uncommitted WIP thread.** The working tree carries an unrelated, uncommitted "alias-handling redesign + YouTube video inventory" thread NOT in any handover: tracked edits to `input/marker_glossary.json` (−258 lines), `run-hermes`, two docs, and a deleted `fixtures/expected/wave-0/apob.expected.yaml`; ~23 untracked items (`docs/ALIAS-HANDLING-REDESIGN-PROPOSAL.md`, `scripts/build_alias_policy.py`, `build_youtube_video_inventory.py`, `build_top50_video_index.py`, `input/youtube-video-inventory/`, `input/research-assets/alias-*.{json,yaml,md}`, new wave-0/1 fixtures incl. `apob.yaml`, untracked `HANDOVER-SESSION-6.md`/`-7.md`). Decide commit vs stash vs discard.
3. **Pre-existing failing test:** `tests/test_hermes_asset_pipeline.py::test_assemble_brief_projects_clean_pointer_fields` — brittle exact-match on apob's practitioner list (now the enriched cohort). Make hermetic (monkeypatch the registry, or assert structure not exact values). The uncommitted `apob.yaml`/`apob.expected.yaml` fixture churn in the WIP thread looks like a started-but-unfinished attempt at this.
4. **FURTHER HORIZON:** brief coverage is now strong; the actual Hermes Stage 1-6 pipeline (`orchestrate.run_marker_live` — council/legal chain that consumes briefs to produce MO range_facts) is the larger next phase.

## Files Changed
- `input/marker_categories.yaml` — cohorts re-derived from enriched registry (15 categories grew, none shrank).
- `input/hermes-briefs/{wave-0,wave-1,wave-2,wave-2b,wave-3}/*.yaml` (197 briefs) + per-wave `_generation_summary.json` — regenerated.
- `~/.claude/.../memory/marker_taxonomy_source_of_truth.md` + `MEMORY.md` — TODO retired, lesson recorded.
- All of the above committed as `037f651` and pushed to origin/main.
