Continue the Metabolicum Hermes-briefs work in /home/zoltan/Projects/metabolicum-agentic-research
(branch: main, all prior work committed + pushed to origin/main).

START BY READING: HANDOVER-SESSION-12.md (full state). Spec/plan for the discovery
work: docs/superpowers/specs/2026-05-30-practitioner-gap-discovery-design.md and
docs/superpowers/plans/2026-05-30-practitioner-gap-discovery.md.

WHERE THINGS STAND
- 982 hermes-briefs generated (230 MO-supported, 752 not-supported/empty by design).
- MO-supported coverage: practitioners 176/230, source URLs 174/230, PMIDs 116/230,
  videos 85/230. Up from ~50 at session start.
- A practitioner-gap discovery pipeline exists at scripts/practitioner_discovery/
  (terms, match, harvest_inventory, harvest_fresh, extract_candidates, threshold,
  ingest, audit, run, audit_channels). 23 tests pass. It enriches existing
  practitioners' marker_affinity from the local 26k-video inventory, evidence-gated
  (N>=2), with provenance. Briefs are re-assembled via scripts/assemble_hermes_briefs.py.
- Registry channel mappings were repaired (Attia/Hyman/Huberman + Eric Berg added);
  audit_channels.py shows 0 mismatches.
- Video relevance fixed: collect_videos T3 "duration" guard removed.

NEXT WORK (priority order)
1. FRESH SEARCH (the big remaining lever — finds NEW specialists the local inventory
   lacks; needed for the 25 fully-empty MO briefs + hormones/HRT + thin coverage).
   Code is ready. Steps:
   a. In /home/zoltan/Projects/metabolicum-research, run social_pipeline discovery
      for target markers WITH a YouTube key (sourced from ~/.secrets), producing
      youtube signal JSON per marker; collect them as <marker>.json into a dir.
   b. Here: python -m scripts.practitioner_discovery.run <markers...> --run-id <id>
      --fresh-signals-dir <dir> -n 2 --write-registry
   c. python3 scripts/build_canonical_practitioner_sources.py
   d. Re-assemble: for w in wave-0 wave-1 wave-2 wave-2b wave-3; do
      python3 scripts/assemble_hermes_briefs.py --wave $w; done
   e. Re-run audit_channels.py before ingest; verify 0 fabricated attributions.
2. BARREN CATEGORIES (~732 markers in allergy/drug-levels/autoimmune/microbiology/etc.
   with no alias terms): decide fresh-search vs out-of-MO-scope per category.
3. Fix the pre-existing failing test
   tests/test_hermes_asset_pipeline.py::test_assemble_brief_projects_clean_pointer_fields
   (brittle exact-match; make hermetic by monkeypatching the registry, or assert
   structure not exact values).

KEY GOTCHAS / RULES
- Zero fabrication: every marker_affinity must trace to retrievable evidence; the
  human-review gate caught a bad case this session (Eric Berg's videos almost
  attributed to Attia via a wrong channel_id). Always run audit_channels.py before
  ingesting, and eyeball the audit before --write-registry.
- collect_videos / discovery must be SCOPED TO MO-SUPPORTED MARKERS (230), never all
  982 — the 752 MO-excluded never get a packet. (Get them from each brief's
  mo_supported flag.)
- Drop unsafe terms: terms._is_safe_term already drops single tokens <=3 alnum chars
  (uk/pt/bun/sod abbreviations) — keep that behavior in any new matching.
- Inventory scans of ~100+ markers auto-background (~4 min); --write-registry
  persists through backgrounding (overwrite of existing file). Read the task output
  file for the summary.
- GITHUB_TOKEN in ~/.secrets is an EXPIRED classic PAT. To push:
  env -u GITHUB_TOKEN git -c credential.helper='!gh auth git-credential' push origin main
  (or regenerate the PAT / comment the line out in ~/.secrets).
- NEVER write to /tmp; use project-local dirs. Clean up scratch files/dirs after runs.

FURTHER HORIZON (not brief-generation): the briefs are TRIGGER files. The actual
Hermes Stage 1-6 research pipeline that consumes briefs to produce MO range_facts
(orchestrate.run_marker_live, the council/legal chain) is the larger next phase once
brief coverage is satisfactory.
