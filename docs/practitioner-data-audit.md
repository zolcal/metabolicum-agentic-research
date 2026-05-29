# Practitioner Data Audit

Generated: 2026-05-29T15:55:54.383875+00:00

## Summary

- Candidate files: 51
- Structured files: 19
- Structured practitioner records across files: 754
- Projects: metabolicum-agentic-research=12, metabolicum-research=30, metasync=9
- Resource buckets: identity=19, marker_affinity=4, social_resources=48, web_resources=30
- Surface counts: other=19, podcast=18, twitter=40, website=72, x=1, youtube=73

## Active Canonical Sources

The maintained practitioner sources now live in `/home/zoltan/Projects/metabolicum-agentic-research/input/practitioners/`.

- `practitioners.json`: identity, aliases, credentials, region, source tier/grade, and COI.
- `practitioner-marker-affinity.json`: marker affinities, paradigm affinities, and contribution notes.
- `practitioner-web-resources.json`: official/searchable websites, blogs, profiles, and podcast feeds.
- `practitioner-social-resources.json`: YouTube, X/Twitter, LinkedIn, Instagram, Facebook, Substack/newsletter handles.

## Best Legacy Consolidated Input

- Path: `/home/zoltan/Projects/metabolicum-agentic-research/input/practitioner_registry.json`
- Practitioner records: 125
- Buckets: identity, marker_affinity, web_resources, social_resources
- Fields: aliases, canonical_name, commercial_interests, country, credentials, entity_type, id, key_contribution, languages, marker_affinity, paradigm_affinity, region, source_grade, source_tier, surfaces

## Canonical Split Status

The four-file split has been implemented. Legacy files are retained only for compatibility and historical traceability.

## Candidate Files

| Project | Records | Buckets | Path |
| --- | ---: | --- | --- |
| metabolicum-agentic-research | 125 | identity, marker_affinity, web_resources, social_resources | `/home/zoltan/Projects/metabolicum-agentic-research/input/practitioner_registry.json` |
| metabolicum-agentic-research | 125 | identity, marker_affinity, social_resources | `/home/zoltan/Projects/metabolicum-agentic-research/input/practitioners/practitioner-marker-affinity.json` |
| metabolicum-agentic-research | 125 | identity, social_resources | `/home/zoltan/Projects/metabolicum-agentic-research/input/practitioners/practitioners.json` |
| metabolicum-agentic-research | 41 | identity | `/home/zoltan/Projects/metabolicum-agentic-research/input/practitioner_aliases.json` |
| metabolicum-agentic-research | 0 | social_resources | `/home/zoltan/Projects/metabolicum-agentic-research/docs/ALIAS-HANDLING-REDESIGN-PROPOSAL.md` |
| metabolicum-agentic-research | 0 | web_resources, social_resources | `/home/zoltan/Projects/metabolicum-agentic-research/docs/agentic-workflow/03-social-agents-spec.md` |
| metabolicum-agentic-research | 0 | social_resources | `/home/zoltan/Projects/metabolicum-agentic-research/docs/agentic-workflow/16-practitioner-directory-system.md` |
| metabolicum-agentic-research | 0 | social_resources | `/home/zoltan/Projects/metabolicum-agentic-research/docs/agentic-workflow/20-semantic-practitioner-matching.md` |
| metabolicum-agentic-research | 0 | web_resources, social_resources | `/home/zoltan/Projects/metabolicum-agentic-research/docs/agentic-workflow/practitioner-registry-sync-report-2026-05-26.md` |
| metabolicum-agentic-research | 0 | social_resources | `/home/zoltan/Projects/metabolicum-agentic-research/input/practitioners/README.md` |
| metabolicum-agentic-research | 0 | web_resources, social_resources | `/home/zoltan/Projects/metabolicum-agentic-research/input/practitioners/practitioner-social-resources.json` |
| metabolicum-agentic-research | 0 | web_resources, social_resources | `/home/zoltan/Projects/metabolicum-agentic-research/input/practitioners/practitioner-web-resources.json` |
| metabolicum-research | 110 | identity, web_resources, social_resources | `/home/zoltan/Projects/metabolicum-research/output/social-discovery/practitioner-registry.json` |
| metabolicum-research | 79 | identity, social_resources | `/home/zoltan/Projects/metabolicum-research/output/mo-research-2026/work-orders/approved-practitioner-roster.yaml` |
| metabolicum-research | 43 | identity, marker_affinity, web_resources, social_resources | `/home/zoltan/Projects/metabolicum-research/config/practitioners.yaml` |
| metabolicum-research | 18 | identity, web_resources, social_resources | `/home/zoltan/Projects/metabolicum-research/output/social-discovery/quicki/practitioner-rank.json` |
| metabolicum-research | 13 | identity, web_resources, social_resources | `/home/zoltan/Projects/metabolicum-research/output/social-discovery/tg-hdl-ratio/practitioner-rank.json` |
| metabolicum-research | 12 | identity, web_resources, social_resources | `/home/zoltan/Projects/metabolicum-research/output/social-discovery/homa-ir/practitioner-rank.json` |
| metabolicum-research | 11 | identity, web_resources, social_resources | `/home/zoltan/Projects/metabolicum-research/output/social-discovery/aip/practitioner-rank.json` |
| metabolicum-research | 10 | identity, marker_affinity, social_resources | `/home/zoltan/Projects/metabolicum-research/scripts/mo-practitioners.json` |
| metabolicum-research | 9 | identity, web_resources, social_resources | `/home/zoltan/Projects/metabolicum-research/output/social-discovery/homa-b/practitioner-rank.json` |
| metabolicum-research | 7 | identity, web_resources, social_resources | `/home/zoltan/Projects/metabolicum-research/output/social-discovery/eag/practitioner-rank.json` |
| metabolicum-research | 7 | identity, web_resources, social_resources | `/home/zoltan/Projects/metabolicum-research/output/social-discovery/fib-4/practitioner-rank.json` |
| metabolicum-research | 7 | identity, web_resources, social_resources | `/home/zoltan/Projects/metabolicum-research/output/social-discovery/fli/practitioner-rank.json` |
| metabolicum-research | 5 | identity, web_resources, social_resources | `/home/zoltan/Projects/metabolicum-research/output/social-discovery/non-hdl-c/practitioner-rank.json` |
| metabolicum-research | 4 | identity, web_resources, social_resources | `/home/zoltan/Projects/metabolicum-research/output/social-discovery/remnant-c/practitioner-rank.json` |
| metabolicum-research | 3 | identity, web_resources, social_resources | `/home/zoltan/Projects/metabolicum-research/output/social-discovery/whtr/practitioner-rank.json` |
| metabolicum-research | 0 | web_resources, social_resources | `/home/zoltan/Projects/metabolicum-research/output/mo-research-2026/control/practitioner-directory-sync.yaml` |
| metabolicum-research | 0 | social_resources | `/home/zoltan/Projects/metabolicum-research/output/mo-research-2026/reviews/batch-001-detailed-practitioner-source-review.md` |
| metabolicum-research | 0 | web_resources, social_resources | `/home/zoltan/Projects/metabolicum-research/output/social-discovery/aip/discovery-summary.json` |
| metabolicum-research | 0 | web_resources, social_resources | `/home/zoltan/Projects/metabolicum-research/output/social-discovery/eag/discovery-summary.json` |
| metabolicum-research | 0 | web_resources, social_resources | `/home/zoltan/Projects/metabolicum-research/output/social-discovery/fib-4/discovery-summary.json` |
| metabolicum-research | 0 | web_resources, social_resources | `/home/zoltan/Projects/metabolicum-research/output/social-discovery/fli/discovery-summary.json` |
| metabolicum-research | 0 | web_resources, social_resources | `/home/zoltan/Projects/metabolicum-research/output/social-discovery/homa-ir/discovery-summary.json` |
| metabolicum-research | 0 |  | `/home/zoltan/Projects/metabolicum-research/output/social-discovery/lean-mass-hyper-responder-score/practitioner-rank.json` |
| metabolicum-research | 0 | web_resources, social_resources | `/home/zoltan/Projects/metabolicum-research/output/social-discovery/quicki/discovery-summary.json` |
| metabolicum-research | 0 | web_resources, social_resources | `/home/zoltan/Projects/metabolicum-research/output/social-discovery/remnant-c/discovery-summary.json` |
| metabolicum-research | 0 | web_resources, social_resources | `/home/zoltan/Projects/metabolicum-research/output/social-discovery/tg-hdl-ratio/discovery-summary.json` |
| metabolicum-research | 0 | web_resources, social_resources | `/home/zoltan/Projects/metabolicum-research/output/social-discovery/whtr/discovery-summary.json` |
| metabolicum-research | 0 | social_resources | `/home/zoltan/Projects/metabolicum-research/research/practitioners/MetabolicumGlobalPractitionerResearcherDirectory-v0.4.md` |
| metabolicum-research | 0 | web_resources, social_resources | `/home/zoltan/Projects/metabolicum-research/research/practitioners/RESEARCH_DRIVEN_UPDATES.md` |
| metabolicum-research | 0 | social_resources | `/home/zoltan/Projects/metabolicum-research/research/practitioners/index.md` |
| metasync | 0 | social_resources | `/home/zoltan/Projects/metasync/docs/plans/2026-01-16-practitioners-page-design.md` |
| metasync | 0 |  | `/home/zoltan/Projects/metasync/docs/plans/practitioners/index.md` |
| metasync | 0 | social_resources | `/home/zoltan/Projects/metasync/docs/plans/practitioners/practitioner-network-page-spec-v2.md` |
| metasync | 0 | web_resources, social_resources | `/home/zoltan/Projects/metasync/docs/research/practitioners/Metabolicum-Global-Practitioner-Social-Network-Mapping.html` |
| metasync | 0 | social_resources | `/home/zoltan/Projects/metasync/docs/research/practitioners/MetabolicumGlobalPractitionerResearcherDirectory-v0.4.md` |
| metasync | 0 | social_resources | `/home/zoltan/Projects/metasync/docs/research/practitioners/index.md` |
| metasync | 0 | social_resources | `/home/zoltan/Projects/metasync/docs/research/templates/mo-five-layer-evidence-template.md` |
| metasync | 0 | social_resources | `/home/zoltan/Projects/metasync/docs/research/templates/mo-practitioner-consensus-template.md` |
| metasync | 0 | social_resources | `/home/zoltan/Projects/metasync/docs/research/templates/pm-phenotype-context-template.md` |

## Migration Notes

- This report is audit-only; source practitioner files were not modified.
- Generated Hermes briefs, SM ranges, YouTube inventory, vendor folders, and wave-specific generated research assets are skipped.
- Files with zero structured records may still contain useful narrative context or old directory versions.
