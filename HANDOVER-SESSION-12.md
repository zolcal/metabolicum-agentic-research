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

## Files Changed
- `scripts/assemble_hermes_briefs.py` — `_practitioner_public_urls()` added; `_practitioners_for` now union; `recommended_videos` removed; summary counter updated.
- `scripts/collect_sources.py` — `_is_public_surface` now rejects by URL domain via `SOCIAL_DOMAINS`.
- `input/hermes-briefs/*/*.yaml` — all 5 waves regenerated.
- `input/research-assets/*/source-index.json` + `source-index-summary.json` — rebuilt with the domain filter.
- `input/hermes-briefs/*/_generation_summary.json` — regenerated.
