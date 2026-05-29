# Research output ingestion contract

This contract defines the required shape of research outputs that may be handed from the agentic research workflow into controlled SQL import tooling.

**The contract is a projection of the canonical research model, not a parallel system.** The agentic research workflow has exactly one source of truth for evidence-bearing claims: the `biomarker_claims` table defined in section four (and the `sources`, `provenance`, `legal_reviews`, `quarantine`, and `citation_edges` tables that surround it). The SQL import surfaces described in this section are deterministic export views over that canonical model.

Research agents must not produce free-form memos when the result is intended to become marker ranges, learn-page narrative, references, or citation-linked evidence. Equally, agents must not produce stand-alone "range packets," "reference packets," or "content packets" that exist independently of an approved BiomarkerClaim row and its linked source, provenance, and legal-review records. Every approved export artifact must trace back to BiomarkerClaim ids; anything that cannot is by definition not yet evidence.

The contract applies to Standard Medical, Research Consensus, and Metabolic Optimization research outputs. It is especially important for Metabolic Optimization research because MO discovery may produce practitioner claims, cited studies, narrative explanation, and numeric target ranges in the same run. Those pieces must stay connected through the shared BiomarkerClaim chain.

## Canonical model and export projections

There is one ontology — section four's BiomarkerClaim — and several export projections derived from it:

| Export surface | Projected from | Projection rule |
|---|---|---|
| `range_facts` | `biomarker_claims` where `approval_status = 'approved'` and (`target_range_low IS NOT NULL` OR `target_range_high IS NOT NULL` OR `target_value IS NOT NULL`) | One range_fact per approved numeric biomarker_claim row. `subject_slug = marker`. See projection mapping at the end of this section. |
| `range_source_artifacts` | `sources` joined through `biomarker_claims.source_id` | One source_artifact per distinct source used by an approved claim in the batch. |
| `range_fact_sources` | `biomarker_claims.source_id` + `cited_paper` jsonb | One link row per (range_fact, supporting source) pair. |
| `marker_content_sections` | Assembly step: narrative composed from approved `biomarker_claims` for that marker, with citation keys resolving back to the same source ids. | Narrative is an assembly artifact, not an agent-produced packet. Every citation key in the content must resolve to a source_id that supports at least one approved BiomarkerClaim for this marker. |
| `research_studies` | `provenance` resolved edges (PMID/DOI) plus PubMed/Crossref metadata fetched in Stage 5 | One study per resolved PMID or DOI cited by at least one approved BiomarkerClaim. |
| `research_study_translations` | Translation/summary step downstream of `research_studies` | One translation per (study_slug, language) pair. |
| `research_citations` | Many-to-many between `research_studies` and `marker_content_sections` | One citation link per (study_slug, source_page) pair. |
| `rejected_item` | `quarantine` | One rejected_item per quarantine row that is in scope for the export batch. |

The export step is deterministic. If two different export runs see the same set of approved BiomarkerClaim rows, they must produce byte-equivalent export artifacts (after sorting and canonicalization). No agent reinterpretation is allowed at export time — any reinterpretation would have happened upstream as part of the council or assembly step and is already recorded in `biomarker_claims`.

Fields that exist on `biomarker_claims` or its linked pre-council `claims` row but have no flat home in this contract (`council_consensus_score`, `financial_conflict_flag`, `financial_conflict_severity`, `paradigm_divergence_flag`, `provenance_status`, `legal_status`, `claim_polarity`, `direction`, raw `target_value` when it is not a range, `extraction_model`, `extractor_confidence`) are preserved in the `provenance: {}` JSONB on `range_fact` and the `provenance: {}` JSONB on `source_artifact`. They are never silently dropped.

## Boundary

The agentic research project is not the production application and must not write directly into the production database. Its responsibility is to emit reviewed, SQL-compatible export artifacts derived from `biomarker_claims` and its linked tables. A separate controlled import step may then insert or update production-facing tables.

Research output is not considered complete unless it can populate all applicable layers:

- range facts
- source artifacts
- source-to-range evidence links
- learn-page narrative sections
- reference-library studies and translations
- page-to-reference citation links

If a run discovers a numeric range but does not preserve the source, quote, PMID or DOI where available, narrative context, and citation mapping, the output is incomplete.

## Required import surfaces

Approved research output must be compatible with these import surfaces:

```text
range_import_batches
range_source_artifacts
range_facts
range_fact_sources
marker_content_sections
research_studies
research_study_translations
research_citations
```

`range_facts` is the canonical range output surface. Older or app-specific range tables may exist in downstream systems, but the agentic research handoff should target the range-fact model first.

`marker_content_sections` is the canonical learn-page narrative surface. The narrative layer is not optional. A marker range without explanatory content is not sufficient for a user-facing marker page.

`research_studies`, `research_study_translations`, and `research_citations` are the canonical reference-library surface. References must be structured separately from inline narrative so they can be reused, searched, translated, and cited from multiple pages.

## Batch metadata

Each export artifact must identify the batch or run that produced it.

```yaml
batch:
  batch_slug: string
  paradigm: standard-medical | research-consensus | metabolic-optimization
  source_kind: string
  importer_version: string
  status: review | approved | rejected
  notes: null | string
  generated_at: datetime
```

The batch status describes the export artifact, not the truth of individual claims. Individual source artifacts, range facts, and content sections still carry their own review fields.

## Source artifacts

Every cited source used to support a range, narrative claim, or reference-library entry must be represented as a source artifact.

```yaml
source_artifact:
  source_id: string
  source_family: pubmed | pmc | doi | guideline | practitioner_surface | podcast | video | blog | social | other
  source_url: null | string
  source_title: null | string
  source_authors: null | string
  source_year: null | integer
  source_license: null | string
  raw_artifact_ref: null | string
  raw_sha256: null | string
  retrieved_at: null | datetime
  review_status: unreviewed | source_policy_checked | approved | rejected
  evidence_grade: null | string
  source_quality: null | string
  source_bounds:
    supports_min: null | boolean
    supports_max: null | boolean
    supports_value: null | boolean
  provenance: {}
```

`source_id` must be stable inside the export. Preferred forms are `pmid:<id>`, `doi:<doi>`, `url:<hash>`, or another deterministic identifier. A human-readable source title is not an identifier.

For cited papers, PMID and DOI should be captured when available. PMID capture is useful even when the source is discovered through a practitioner surface because it prevents duplicated rediscovery and allows the reference library to merge evidence later.

## Range facts

Each numeric recommendation, threshold, interval, target, or comparison range becomes one range fact. A single marker may have many facts when values differ by age, sex, specimen, method, population, endpoint, or context.

```yaml
range_fact:
  subject_slug: string
  entity_type: marker | calculator | evaluator | index
  paradigm: standard-medical | research-consensus | metabolic-optimization
  range_version: string
  range_order: integer
  min_value: null | number
  max_value: null | number
  unit: string
  status: string                         # from the alias table in metasync's RANGE-STATUS-COLOR-POLICY.md;
                                         # buckets: optimal | near_optimal | borderline | elevated | critical | severe | indeterminate
                                         # plus aliases (normal, good, target, high, low, deficient, very_high, very_low, ...).
                                         # canonical_color(status) raises on unmapped values.
  label: null | string
  color: null | string                   # derived by canonical_color(status) at export. One of:
                                         #   #22c55e (optimal)    #84cc16 (near_optimal)  #eab308 (borderline)
                                         #   #f97316 (elevated)   #ef4444 (critical)      #dc2626 (severe)
                                         #   #9ca3af (indeterminate)
                                         # DB CHECK-constrained against this 7-hex set.
  gender: null | all | female | male | string
  sex_for_lab_reference: null | female | male | string
  stratum: null | string
  age_min: null | number
  age_max: null | number
  variant: null | string
  specimen: null | string
  population_scope: null | string
  endpoint: null | string
  outcome_target: null | string
  endpoint_note: null | string
  evidence_grade: null | string         # parent letter, e.g. "B"
  evidence_sub_grade: null | string     # full code, e.g. "B2"
  validation_grade: null | string
  validation_tier: null | string
  source_quality: null | string
  extraction_confidence: null | low | medium | high | number
  display_role: null | primary_standard_medical_anchor | primary_research_consensus_range | primary_metabolic_optimization_target | supporting | comparison_only | internal_research_gate
  primary_display: boolean
  public_display_approved: boolean
  method_note: null | string
  derivation_note: null | string
  context_note: null | string
  source_ids: [string]
  review_status: unreviewed | review | approved | rejected
  provenance:
    verbatim_quote: null | string
    source_pmid: null | string
    source_doi: null | string
    source_url: null | string
    verified_present: null | boolean
    extraction_notes: null | string
```

The structured fields must carry the queryable meaning. Agents must not hide age, sex, population, or method qualifiers inside `label`, `context_note`, or `variant` when a structured field exists.

`public_display_approved` is a publication gate. It is not the same as `review_status`. A fact may be reviewed and still not approved for public display.

## Range-source links

The export must preserve which source supports which fact and which part of the fact it supports.

```yaml
range_fact_source:
  range_order: integer
  source_id: string
  source_role: supports_range | supports_min | supports_max | supports_context | contradicts_range | background
  supports_bound: min | max | both | value | context | none
  evidence_grade: null | string
```

Range-source links are required when a range fact has any `source_ids`. The list of IDs on the range fact is not enough by itself because it does not explain the support role.

## Learn-page narrative sections

Research output intended to support a marker page must include learn-page content sections. These sections are database content, not markdown drafts.

```yaml
marker_content_section:
  marker_slug: string
  marker_type: marker | calculator | evaluator | index
  language: string
  section_type: why_matters | paradigm_thresholds | evidence_badge | mechanism | interpretation | limitations | references | other
  section_order: null | integer
  paradigm: null | standard-medical | research-consensus | metabolic-optimization
  content: {}
  source_type: pipeline | human | imported | generated_reviewed
  evidence_grade: null | string
  source_url: null | string
  content_hash: null | string
  status: draft | review | published | rejected
  version: null | integer
```

Inline references inside narrative content must use stable citation keys that can be resolved to `research_citations`. Narrative text should not include bare URLs as the primary citation mechanism.

The `content` object must match the section type. A simple prose section may use:

```yaml
content:
  title: string
  body: string
  citations:
    - citation_key: string
      source_id: string
```

More structured sections may use arrays, threshold blocks, badges, or comparison tables, but they must remain JSON-compatible and citation-addressable.

## Reference-library studies

Every cited study that should appear in the reference library must be represented as a study record plus at least one translation record.

```yaml
research_study:
  slug: string
  pmid: null | string
  doi: null | string
  original_title: string
  authors_short: null | string
  journal: null | string
  publication_year: null | integer
  study_type: null | string
  evidence_grade: null | string
  evidence_sub_grade: null | string
  sample_size: null | integer
  grading_confidence: null | string
  auto_graded: boolean
  paradigm_standard: boolean
  paradigm_research: boolean
  paradigm_optimization: boolean
  pubmed_url: null | string
  doi_url: null | string
  full_text_url: null | string
  topics: [string]
  biomarkers: [string]
  status: draft | published | archived
```

```yaml
research_study_translation:
  study_slug: string
  language: string
  title: string
  summary_plain: null | string
  key_finding: null | string
  key_findings: []
  content: {}
  content_source: pipeline_research | human | imported
```

Study slugs must be deterministic enough to avoid duplicate records for the same PMID or DOI. If PMID exists, the PMID is the preferred deduplication key.

## Citation links

Reference records must be connected to the page or content surface where they are used.

```yaml
research_citation:
  study_slug: string
  source_page: string
  display_order: integer
  citation_context: null | string
  citation_key: null | string
```

`source_page` should be the stable page path or content-surface identifier, such as `/learn/markers/apob`. `citation_context` should explain why the study appears on that page, usually by reusing the key finding or the exact narrative point it supports.

## Minimum complete MO output

A Metabolic Optimization research result is complete only when it includes:

- at least one range fact or an explicit no-range-found outcome
- at least one source artifact for every range fact source
- range-source links for every supported range
- verbatim support for numeric values when available
- PMID or DOI capture for cited studies when available
- learn-page narrative sections for user-facing explanation
- reference-library records for studies that should appear in references
- citation links connecting narrative pages to reference records

If the MO run discovers useful papers but no defensible numeric range, it should still emit source artifacts, reference-library records, citation links, and a reviewed no-range outcome. It must not fabricate a range to satisfy the range-fact layer.

## Field-level projection mapping

The `range_fact` row is the most opinionated projection. Its field-by-field derivation from `biomarker_claims` is:

| `range_fact` field | Derived from `biomarker_claims` | Rule |
|---|---|---|
| `subject_slug` | `marker` | Direct copy. |
| `entity_type` | (lookup) | Resolved from the marker registry (marker / calculator / evaluator / index). |
| `paradigm` | `paradigm` | Enum rename: `SM` → `standard-medical`, `RC` → `research-consensus`, `MO` → `metabolic-optimization`. |
| `range_version` | (batch metadata) | Tag from the export batch, not from the claim row. |
| `range_order` | (assigned) | Assigned deterministically at export from the ordered set of approved claims for the marker. |
| `min_value` | `target_range_low` | Direct copy when set. |
| `max_value` | `target_range_high` | Direct copy when set. |
| `unit` | `units` | Direct copy. |
| `status` | `direction` + `claim_polarity` + `target_value` | See status-derivation rules below. Output must be a key in the alias table in metasync's `RANGE-STATUS-COLOR-POLICY.md`. |
| `color` | `status` | Derived at assembly via `canonical_color(status)` per `RANGE-STATUS-COLOR-POLICY.md`. Helper raises on unmapped status; DB CHECK constraint enforces the 7-hex canonical palette. |
| `gender`, `sex_for_lab_reference`, `stratum`, `age_min`, `age_max`, `variant`, `specimen`, `population_scope` | `population` jsonb | Each flat field reads its known key out of `population`. Unset keys remain null. |
| `endpoint`, `outcome_target`, `endpoint_note` | `population.endpoint` etc. | Same JSONB-to-flat rule. |
| `evidence_sub_grade` | `evidence_sub_grade` | Direct copy. |
| `evidence_grade` | `evidence_grade` | Parent letter from the generated column `LEFT(evidence_sub_grade, 1)` on `biomarker_claims`. |
| `display_role`, `primary_display`, `public_display_approved` | `legal_status` + assembly policy | `public_display_approved = (legal_status = 'approved' AND approval_status = 'approved')`. `display_role` is assigned by the assembly step from paradigm + envelope alignment. |
| `review_status` | `approval_status` | Direct copy. |
| `source_ids[]` | `biomarker_claims.source_id` plus resolved cited-paper sources where applicable | The source row that produced the claim is always included. Resolved cited papers may add additional source ids through provenance. |
| `provenance.verbatim_quote` | `verbatim_quote` | Direct copy. |
| `provenance.source_pmid`, `source_doi`, `source_url` | `cited_paper` jsonb + resolved `provenance` table | PMID/DOI populated only when provenance resolution succeeded. |
| `provenance.verified_present` | (reviewer log) | True iff the reviewer agent re-fetched the source URL and confirmed the verbatim quote is present per section five. |
| `provenance.council_consensus_score` | `council_consensus_score` | Preserved here because there is no flat home. |
| `provenance.financial_conflict_flag`, `financial_conflict_severity` | `financial_conflict_flag`, `financial_conflict_severity` | Preserved here. |
| `provenance.paradigm_divergence_flag` | `paradigm_divergence_flag` | Preserved here. |
| `provenance.claim_polarity`, `direction`, `target_value` | `claim_polarity`, `direction`, `target_value` | Preserved here for refutation, "at" claims, and downstream consumers that need the raw shape. |
| `provenance.extraction_model`, `extractor_confidence` | `claims.extraction_model`, `claims.extractor_confidence` through `biomarker_claims.claim_id` | Preserved here. |

### Status-derivation rules

`range_fact.status` is a downstream display label derived from the canonical `direction` + `claim_polarity` + range-bound shape on `biomarker_claims`. Every status this section emits (`target`, `normal`, `optimal`) is a key in the alias table in metasync's `RANGE-STATUS-COLOR-POLICY.md`; the assembly step then resolves color via `canonical_color(status)`. If a future rule produces a status string not in the alias table, it must be added to the policy before the rule ships. The rules:

- `direction = 'below'`, `claim_polarity = 'supports'`, `target_range_high IS NOT NULL`, `target_range_low IS NULL` → `status = 'target'` with `min_value = null`, `max_value = target_range_high`.
- `direction = 'above'`, `claim_polarity = 'supports'`, `target_range_low IS NOT NULL`, `target_range_high IS NULL` → `status = 'target'` with `min_value = target_range_low`, `max_value = null`.
- `direction = 'between'`, `claim_polarity = 'supports'`, both bounds set → `status = 'normal'` (SM/RC) or `status = 'optimal'` (MO) with both bounds copied. Paradigm choice is fixed by the claim's paradigm.
- `direction = 'at'`, `target_value IS NOT NULL` → `status = 'target'`, `min_value = target_value`, `max_value = target_value`. The original `target_value` is preserved in `provenance`.
- `claim_polarity = 'refutes'` → no `range_fact` row is emitted. The refutation is linked to every approved supportive claim that matches on `(marker, paradigm, direction, units)` via one `range_fact_sources` row per match, with `source_role = 'contradicts_range'` and the refuting claim's `source_id`. If zero approved supportive claims match, the refutation goes to `quarantine` with `rejection_stage = 'assembly'` and `rejection_codes` including `no_supportive_claim_to_contradict`.
- `claim_polarity = 'qualifies'` → a `range_fact` row is emitted only if a numeric bound is set; the qualifier is preserved in `provenance.extraction_notes`.

Any claim whose status cannot be derived by these rules is held back from export and surfaces in the export run report as an unmapped claim. The assembly step never invents a status.

## Search-stage policy

The SQL-compatible output contract does not mean discovery agents should be anchored on downstream import fields. Discovery remains source-first: find public claims, tables, papers, practitioner statements, podcasts, videos, and blogs. The structured export is assembled after extraction, validation, provenance review, and legal review.

Standard Medical anchors and research target envelopes are not MO discovery goals, and their numeric values are withheld from discovery and extraction. They are revealed only to the council or review layer (the visibility gate; sections 2, 17, 19), which uses them to detect agreement, tension, contradiction, missing strata, or convergence. They must not be used to coerce MO research into producing a predetermined value.

## What agents may not produce

No agent — extractor, tagger, structurer, reviewer, decider, provenance, legal, or assembly — may produce a stand-alone export-shaped artifact that is not anchored to BiomarkerClaim rows. In particular:

- No "range packet" that is a raw `range_fact` produced outside the canonical claim flow.
- No "reference packet" that is a `research_study` row without a corresponding resolved provenance edge to an approved BiomarkerClaim.
- No "content packet" that is a `marker_content_section` whose citation keys do not resolve to source ids backing approved BiomarkerClaim rows.

If an agent has structured numeric output that is not yet bound to a BiomarkerClaim row, it is a candidate claim, not an export artifact. It flows through the canonical pipeline (Stage 2 → 3 → 5 → 6) and only acquires export shape at the assembly step.

## Rejection and incompleteness

Rejected or incomplete material must not disappear silently. The export should preserve a quarantine or review record with:

```yaml
rejected_item:
  subject_slug: string
  item_type: source | range_fact | narrative_section | reference | citation
  rejection_stage: extractor | reviewer | council | provenance | legal | assembly
  rejection_reason: string
  rejection_codes: [string]
  reviewer_notes: null | string
  source_id: null | string
  created_at: datetime
```

This allows later runs to avoid repeating the same failed extraction and gives reviewers a clear reason why a marker has no approved range yet.

## Acceptance rule

An export artifact passes this contract when, and only when, both of the following hold:

1. Every record in the export traces back to one or more approved BiomarkerClaim rows (or, for `rejected_item`, to a quarantine row). The mapping from canonical row id to export row is recorded in the batch manifest, so the projection is auditable and replayable.

2. A deterministic importer can insert or update all applicable records in the required import surfaces without guessing:

   - which marker or calculator the data belongs to
   - which paradigm the data belongs to
   - which source supports which value
   - which quote or PMID supports a claim
   - which narrative section should appear on the learn page
   - which references should appear in the reference library
   - which citation key connects narrative text to a reference record
   - whether a fact is approved for public display or only internal comparison

Anything that requires a human or importer to infer these relationships from prose is not a valid ingestion-ready research output. Any export record that cannot be projected from a specific BiomarkerClaim id (or quarantine row id) is by definition not yet ingestion-ready and must not be included in the batch.
