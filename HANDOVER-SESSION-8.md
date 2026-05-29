# HANDOVER-SESSION-8

## Date
2026-05-29

## Summary
Audited practitioner data across `metasync`, `metabolicum-research`, and `metabolicum-agentic-research` to prepare consolidation into one canonical practitioner source model.

## Completed
- Added `scripts/audit_practitioner_data.py`, an audit-only scanner with explicit project targets and generated/heavy folder exclusions.
- Added `tests/test_practitioner_data_audit.py` to verify the audit detects structured practitioner files, practitioner directory docs, and skips generated Hermes briefs.
- Generated `input/research-assets/practitioner-data-inventory.json` with 46 candidate files, 17 structured files, and 504 structured practitioner records across the scanned projects.
- Generated `docs/practitioner-data-audit.md` with the recommended canonical candidate and migration notes.

## Key Decisions
- Recommended `/home/zoltan/Projects/metabolicum-agentic-research/input/practitioner_registry.json` as the canonical base because it has the strongest combined identity, marker affinity, web resource, and social resource coverage.
- Keep practitioner maintenance split into four source files:
  - `practitioners.json` for canonical identity, aliases, credentials, region, and source tier/grade.
  - `practitioner-marker-affinity.json` for marker affinities, categories, topics, and match confidence.
  - `practitioner-web-resources.json` for official/searchable practitioner resources.
  - `practitioner-social-resources.json` for YouTube, X/Twitter, LinkedIn, Instagram, Facebook, Substack/newsletter, and similar distribution surfaces.
- Social resource data is intentionally not wired into Hermes input in this pass; it is for future content discovery and maintenance.
- The audit uses explicit scan targets instead of broad repository traversal to avoid pulling in generated inventory, brief, and cache trees.

## Verification
- `env TMPDIR=/home/zoltan/Projects/metabolicum-agentic-research/.pytest-tmp python3 -m pytest -p no:cacheprovider tests/test_practitioner_data_audit.py -q` passed: 1 test.
- `python3 -m json.tool input/research-assets/practitioner-data-inventory.json` parsed successfully.
- `sed -n '1,120p' docs/practitioner-data-audit.md` confirmed the expected summary and canonical recommendation.

## Next Steps
- Decide the exact canonical schema for the four practitioner files.
- Build a migration/merge script that reads the audited sources and produces the four canonical files without losing aliases or source provenance.
- After review, update downstream Hermes/resource collection scripts to consume the canonical practitioner files.

## Files Changed
- `scripts/audit_practitioner_data.py` — new audit-only practitioner data inventory script.
- `tests/test_practitioner_data_audit.py` — focused regression test for the audit script.
- `input/research-assets/practitioner-data-inventory.json` — generated practitioner data inventory.
- `docs/practitioner-data-audit.md` — generated human-readable audit report.
- `HANDOVER-SESSION-8.md` — session handover for this audit pass.

## 2026-05-29 Practitioner Consolidation Implementation

Completed after the audit:
- Added `scripts/build_canonical_practitioner_sources.py`.
- Created canonical source directory `input/practitioners/` with the four maintained files.
- Added legacy redirect metadata to `input/practitioner_registry.json` and `input/practitioner_aliases.json`.
- Updated the audit scanner/report so it names `input/practitioners/` as the active canonical source and treats old consolidated registries as legacy inputs.
- Added redirect notes in old `metabolicum-research` and `metasync` practitioner sources where safe to do so without staging unrelated pre-existing changes.

Verification run for this implementation:
- `env TMPDIR=/home/zoltan/Projects/metabolicum-agentic-research/.pytest-tmp python3 -m pytest -p no:cacheprovider tests/test_build_canonical_practitioner_sources.py tests/test_practitioner_data_audit.py -q` passed: 3 tests.
- `python3 scripts/build_canonical_practitioner_sources.py` generated 125 practitioners, 125 marker affinities, 53 web resources, and 55 social resources.
- Social-domain URLs were checked to ensure none remain in `practitioner-web-resources.json`.
