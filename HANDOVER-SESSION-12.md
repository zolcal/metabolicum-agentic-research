# HANDOVER-SESSION-12

## Date
2026-05-30

## Summary
Fixed Hermes brief assembly so practitioner websites actually reach briefs, collapsed the two video sections into one ranked ID list, and broadened practitioner matching to direct-affinity ∪ category-cohort. Regenerated all 5 waves; all acceptance checks pass.

## Completed
- **Practitioner-website drop fixed.** `recommended_source_urls` previously came only from `source-index.json` (built by `collect_sources.py` off a stale `practitioner-index.json` whose practitioner list diverged from the brief's). Added `_practitioner_public_urls()` in `scripts/assemble_hermes_briefs.py`, which derives website/blog surfaces from the brief's own `recommended_practitioner_ids` via the registry, reusing `collect_sources._is_public_surface`. Merged into `recommended_source_urls`.
- **Video section collapsed.** Removed `recommended_videos` (verbose `video_id/score/title/channel`) from `assemble_marker` (both branches) and the summary counter. Only the ranked `recommended_youtube_video_ids` remains — restores the canonical clean schema (`POINTER_FIELDS` / acceptance no-bloat rule). The research agent retrieves title+transcript itself; Stage-1 fetch is code (`code/discovery/youtube.py`), not a prompt.
- **Practitioner matching broadened.** `_practitioners_for` now returns `direct_affinity ∪ category_cohort` instead of direct-only-when-present. Before: `alt` had 1 practitioner (paul-saladino direct), `alp` had 14 (no direct → cohort). After: both get the full liver-function cohort.
- **Social URL leakage fixed.** `collect_sources._is_public_surface` now also rejects by URL domain (`SOCIAL_DOMAINS`: twitter/x/instagram/facebook/tiktok/linkedin/youtube), because registry `platform` labels are unreliable (a twitter.com URL tagged `website` was leaking in). Rebuilt `source-index.json` + reassembled all waves with `--collect-sources`. Result: 0 social-domain URLs across all briefs. Podcast/RSS/patreon surfaces intentionally still pass (not flagged; may carry mineable transcripts).

## Verification
- alp: source_urls 1 → 17; single ranked video-id list; no `recommended_videos`.
- alt: practitioners 1 → 14; source_urls 2 → 17.
- All 5 waves regenerated (`python scripts/assemble_hermes_briefs.py --wave <wave>`).
- `code/acceptance/check_hermes_briefs.py --wave <wave>` → all 5 waves pass.
- Coverage: 230 MO-supported briefs; 157 now have ≥1 practitioner, 164 have ≥1 source URL; 0 still carry `recommended_videos`.

## Key Decisions
- Derive practitioner URLs in assembly from the brief's matched practitioner list (single source of truth) rather than syncing a second matcher in `collect_sources`.
- Direct affinity is too sparse (often 0-1) → cohort always supplements, not just as fallback.
- Briefs are currently a **closed** source list — the documented "search-mode" expansion for thin coverage is NOT implemented (framework doc §19 lists it as a future enhancement). No code/prompt expands beyond the brief.

## Still Open / Deferred
- **Video relevance ("fluff")** — user's item 3, under analysis. Generic videos (e.g. "Normal Labs are NOT Healthy", "Ranked 100 markers") match via category cohort + broad T3 terms. Lever: tighten T3 so bare domain terms only count in titles or co-occurring with a T1/T2 phrase.
- **Podcast/RSS surfaces** — still included in `recommended_source_urls` (Apple Podcasts, Spotify, Patreon, libsyn/podbean RSS). Social domains are now excluded; podcast/RSS left in by design. Revisit if they should be dropped.
- **Stale unit test** — `tests/test_hermes_asset_pipeline.py::test_assemble_brief_projects_clean_pointer_fields` fails (pre-existing, from today's cohort commits): asserts apob → 2 practitioners + `recommended_source_urls == ["peterattiamd.com"]`, but apob now resolves to the 14-person cohort. Needs updating to current behavior.
- Changes are **uncommitted**.

## Practitioner Gap Discovery project (in progress, branch `feat/practitioner-gap-discovery`)
- Spec: `docs/superpowers/specs/2026-05-30-practitioner-gap-discovery-design.md`. Plan: `docs/superpowers/plans/2026-05-30-practitioner-gap-discovery.md`.
- Built inventory-source pipeline `scripts/practitioner_discovery/` (terms, harvest_inventory, extract_candidates, threshold, ingest, audit, run) — 16 tests pass. Commits `cc47314`..`74b4ad5`. Includes word-boundary fix (lookarounds, for parenthesized terms) and an **enrichment path** (registered channels with ≥N evidence get the marker ADDED to their existing affinity).
- **Dry-run on total-testosterone + cortisol-am: 87 signals, 0 NEW practitioners (inventory is metabolic-only), 4 enriched, 6 held.** Decision (user): option 3 — enrich existing from inventory now, fresh-search (Task 10) for new specialists later.
- **BLOCKER (data integrity) — registry NOT written:** enrichment surfaced 2 pre-existing bad YouTube channel mappings (the session-64 bug never ported to the agentic registry):
  - `person:peter-attia` youtube = `UC3w193M5tYPJqF0Hi-7U-2g` = **Eric Berg's** channel (real Attia = `UC8kGsMa0LygSX9nkBcBH1Sg`). The "Attia cortisol (64)" enrichment is really Eric Berg's videos; Berg isn't in the registry.
  - `person:mark-hyman` youtube = `UC2D2CMWXMOVWx7giW1n3LIg` = **Huberman's** channel (real Hyman = `UC5IuDMmKWSsBFB0iKky6aEQ`).
  - Clean enrichments: `company:levels-health` cortisol-am (9), `person:sten-ekberg` cortisol-am (2).
- **RESOLVED + ingested.** Added `scripts/practitioner_discovery/audit_channels.py` (free channel-ID audit vs inventory names, camelCase-aware). Audit found only the 2 real bugs (+2 camelCase false positives). Fixed Attia→`UC8kGsMa0LygSX9nkBcBH1Sg`, Hyman→`UC5IuDMmKWSsBFB0iKky6aEQ`, Huberman→`UC2D2CMWXMOVWx7giW1n3LIg` (inventory-confirmed), added `person:eric-berg`. Registry now 0 mismatches (commit `d138383`).
- **Hormones pilot ingested (commit `1004a70`):** full 15-marker run → 11 existing practitioners enriched with evidence-backed hormone affinities (Berg 11 markers, Huberman 11, Levels, Siim Land, Ekberg, Physionic, Judy Cho, Perlmutter, Ken Berry, Thomas Brewer, Mind&Matter); 0 new practitioners (inventory is metabolic-only — fresh search needed for genuinely new specialists); threshold held 1-evidence noise. Synced canonical, re-assembled all waves, acceptance passes. **cortisol-am 0→4 practitioners, total-testosterone 0→1, dht 0→3** etc. `bio-t` stays empty (nobody says "bioavailable testosterone" on video).
- **Task 10 (fresh search) — code complete + merged to main (`34a48cc`).** Decoupled design avoids cross-project import + network: the live YouTube/podcast harvest runs in metabolicum-research (`python -m scripts.social_pipeline.discover <marker>`, needs YOUTUBE_API_KEY) and writes signal JSONs; this pipeline ingests them via `--fresh-signals-dir <dir>` (expects `<marker>.json` files of SocialSignal dicts). `harvest_fresh.video_from_signal` + `signals_dir_harvester` + `scan_fresh` map+thread them through the same extract→threshold→ingest path. 22 tests pass. **The live fresh harvest was NOT run here (sandbox blocks outbound network) — it's the user's step with their API key.**
- All discovery work is now on **main** (branches deleted). origin/main is behind by ~19 commits (not pushed).
- **To run fresh search (find NEW specialists):** (1) in metabolicum-research, run social_pipeline discover for the target markers with a YouTube key → collect each `<marker>.json` (youtube signals) into a dir; (2) here: `python -m scripts.practitioner_discovery.run <markers...> --run-id <id> --fresh-signals-dir <dir> -n 2 [--write-registry]`; (3) sync canonical + re-assemble as in the hormones pilot.
- **Expansion done (local resources, commit `0353ba2`):** ran inventory enrichment for the other 16 under-covered categories. Of 834 markers there, only 102 have usable alias terms; of those, **72 have specific (safe) terms and were ingested** → 16 practitioners enriched with kidney/blood-count/urine/coagulation affinities (creatinine 6, uric-acid 7, homocysteine 6, glyphosate 7, egfr 2, …). Coverage: **MO briefs with practitioners 157 → 173**. Acceptance passes. Channel audit was already global (0 mismatches) so no re-audit needed; verified 0 suspect-term leakage post-ingest.
- **DEFERRED — 16 markers with over-generic alias terms** (need alias-policy cleanup before their enrichment is trustworthy): bare abbreviations `uk`(→"UK"), `cat`, `pt`, `bun`, `sod`, `mda`, `mcv`, `alc`, `pth`; bare element names `calcium`/`potassium`/`sodium`/`chloride`/`phosphorus`/`selenium`/`hemoglobin` (match dietary mentions, not the serum lab marker). This is the same "alias quality" thread deferred at session start — fix = drop unsafe bare tokens in `terms.marker_terms` (or tighten the alias-policy), then re-run those 16. The remaining ~732 markers (allergy/drug-levels/autoimmune/microbiology/etc.) have NO alias terms and no local-resource coverage — genuinely need fresh search or are out of MO scope.
- **16 deferred markers UNBLOCKED + ingested (commits `1e8fac9` + `4834057`).** Added `terms._is_safe_term`: drops single tokens with ≤3 alnum chars (uk/pt/bun/sod/pth/cat/mda/mcv/alc abbreviations that matched unrelated words) while keeping multi-word phrases and longer bare names (potassium/sodium/calcium...). Re-ran the 16: element markers enriched (potassium 10, sodium 15, calcium 17, bun 9 practitioners, + chloride/phosphorus/selenium/hemoglobin), abbreviation markers via safe terms (sod→superoxide dismutase 3, pth→parathyroid hormone 10); uk/pt = 0 (their exact phrases rare — correctly no false positives); cat/mda skipped (no safe term). +1 new practitioner (Anthony Chaffee). 23 discovery tests pass.
- **Local-resource enrichment COMPLETE.** Final coverage: **MO briefs with practitioners 50 → 176, with sources 50 → 174** (of 230). Every marker answerable from the 26k inventory is now ingested.
- **Remaining work needs non-local resources:** (1) fresh YouTube/podcast search (Task 10 code ready; run with a YouTube key to find NEW specialists); (2) ~732 markers in barren categories (allergy/drug-levels/autoimmune/microbiology/etc.) have no alias terms + no local coverage — fresh search or out-of-MO-scope decision. Note: `terms._is_safe_term` now drops bare ≤3-char tokens globally, so a future re-run would skip `dht` (already ingested, unaffected).
- All on local `main` (origin behind ~26 commits, not pushed).

## Files Changed
- `scripts/assemble_hermes_briefs.py` — `_practitioner_public_urls()` added; `_practitioners_for` now union; `recommended_videos` removed; summary counter updated.
- `scripts/collect_sources.py` — `_is_public_surface` now rejects by URL domain via `SOCIAL_DOMAINS`.
- `input/hermes-briefs/*/*.yaml` — all 5 waves regenerated.
- `input/research-assets/*/source-index.json` + `source-index-summary.json` — rebuilt with the domain filter.
- `input/hermes-briefs/*/_generation_summary.json` — regenerated.
