# SM range sample review — frozen-anchor interface with hidden derivation

**Date:** 2026-05-17
**Reviewers requested:** Codex, Kimi K2
**Scope:** Five pilot-marker sample YAML files in this directory, before scaling to all 108 wave-1 markers.
**Decision needed:** Sign-off on the sample shape so the 108-file generation can proceed.

---

## 1. Design principles

Two policy decisions shape this version:

1. **Hide internal derivation from research agents.** No paths to frozen files, no SHA-256s, no source-family identifiers, no data-collection lineage, no legacy artifact references, no information that lets an agent infer or publish hidden derivation. The agent receives a stable `anchor_version` and the row data only; the pipeline maintains an internal provenance ledger that is not in the sample.
2. **Expose public citation IDs for deduplication.** PMIDs, PMCIDs, and DOIs that are already public (and likely already known to the RC effort) are surfaced so the agent does not rediscover the same papers. Agents may use these IDs for dedup, retrieval, and context — **not** as permission to publish derivation rationale or infer private lineage.

The two principles work together: the agent is fenced from how the anchor was built but informed about which papers it already knows.

---

## 2. Canonical sample shape

```yaml
marker_slug: <slug>
canonical_slug: <slug>      # optional; present in wave-2A and later when identity registry binding is available
marker_name: <human name>
entity_type: evaluator | calculator | raw_input_marker   # optional; present in wave-2A and later
identity_binding_status: canonical_candidate | canonical_approved_wave_1 | needs_identity_review | unreviewed_db_marker   # optional; present in wave-2A and later
sample_status: review_sample
source_policy: frozen_standard_medical_anchor | standard_medical_anchor_candidate | not_in_frozen_wave_1 | calculated_surface
anchor_version: sm_wave_1_2026_05_05 | sm_wave_2a_2026_05_18 | sm_wave_2b_2026_05_18 | sm_wave_3_2026_05_18 | null
unit: <string> | null
crosscheck_status: <enum>   # optional, top-level. Wave-1 frozen-summary field only for now.
                            # Examples: not_performed, performed_clean, performed_with_deltas.
                            # Wave-2A, Wave-2B, and Wave-3 omit this until a later human-review + crosscheck/promotion pass exists.

rows:
  - stratum: <slug, e.g. male_18_50, all_adults>
    sex: male | female | all
    age_min: <int> | null
    age_max: <int> | null
    # optional context: weight_min/max, bmi_min/max, ethnicity, pregnancy_status
    # Raw source-side variant/population_scope labels are not exposed. Age-like
    # variants must be parsed into age_min/age_max or encoded only in stratum.
    min: <number> | null
    max: <number> | null
    status: <e.g. normal>
    use: internal_research_gate | comparison_only | display_eligible
    primary_display: <bool>     # optional, only when use=display_eligible
    public_source_ids:          # optional. Present only when this row is
      pmids: []                 # backed by a published paper. Public IDs
      pmcids: []                # attach to rows, not to the marker as a
      dois: []                  # whole — a hybrid marker can have a
                                # paper-backed row alongside population-derived rows.

anchor_provenance:
  source_visibility: public_ids_only
  hidden_derivation: true
  # No marker-wide public_source_ids list. IDs attach to rows individually.

known_research_context:
  source_visibility: public_ids_only
  purpose: deduplication_and_context
  pmids: []     # populate from RC research effort; marker-wide dedup hints
  pmcids: []
  dois: []
  note: |
    Public IDs exposed for deduplication. Do not treat as proof of current
    claim unless independently revalidated.

annotations:     # may be empty
  - role: clinical_cutoff | risk_treatment_threshold
    summary: <one-line description>
    thresholds:
      - {value: ..., meaning: ...}
    public_reference:
      url: ...
      pmids: []
      dois: []

reviewer_note: |
  Human-readable rationale: doctrine compliance, RI width explanation, MO
  divergence framing, caveats.
```

For markers **not in frozen wave-1**, replace `rows`, `anchor_provenance`, and `annotations` with empty content and add a `decision_needed:` block. See `lpa.sample.yaml`.

For **calculated_surface** markers, replace `anchor_provenance` semantics with a `formula:` block referencing input evaluator markers by `marker_slug + anchor_version` only (no file paths), plus an `mo_research_context:` block that surfaces public PMIDs for paradigm comparison. See `tg-hdl-ratio.sample.yaml`.

---

## 2A. Top-level lifecycle enums

### `sample_status`

| Value | Meaning | Current use |
|---|---|---|
| `review_sample` | Generated or drafted input for review. Not production-approved and not display-ready by itself. | Wave-1, Wave-2A, Wave-2B, and Wave-3 |
| `approved` | Reserved. Human-reviewed contract payload approved for pipeline use. | Not used yet |
| `production` | Reserved. Payload accepted into production anchor release. | Not used yet |

### `source_policy`

| Value | Meaning |
|---|---|
| `frozen_standard_medical_anchor` | Wave-1 anchor generated from the frozen clean SM range set. |
| `standard_medical_anchor_candidate` | Later-wave anchor candidate generated from the marker identity registry plus local import-ready SM rows. Wave-2A uses canonical candidates; Wave-2B uses identity-review candidates; Wave-3 uses unreviewed DB markers. Wave-2B and Wave-3 are locked to `internal_research_gate`. |
| `calculated_surface` | Formula-derived surface; no direct SM anchor rows are emitted. |
| `not_in_frozen_wave_1` | Placeholder for markers intentionally absent from wave-1. Use only until a later wave supersedes it. |

These fields are gates. They describe lifecycle and source-contract class; they are not evidence grades and must not be used as MO research targets.

---

## 3. The `use:` enum

| Value | Meaning |
|---|---|
| `internal_research_gate` | Council may compare claims against this row; agent must not surface or publish it. Default for population-RI rows. |
| `comparison_only` | Council may compare; row may be surfaced in internal review screens but not in user-facing display. |
| `display_eligible` | Row has cleared cross-check and may be promoted to user-facing display. Combine with `primary_display: true` to mark the canonical display row. |

Wave-1 default: `internal_research_gate` unless cross-check is complete. ApoB row 1 is the only `display_eligible` row in the pilot (international Grade A guideline reference interval already validated).

---

## 4. What gets hidden

Removed from sample files vs. earlier drafts and the underlying frozen exports:

- `frozen_source.path` — no path disclosure
- `frozen_source.sha256` — no hash, no SHA-bound pointer
- `source_track`, `source_family`, `source_id`, `source_url`, `raw_artifact_ref`, `raw_sha256`, `retrieved_at`, `review_status`
- `derivation_audit`, `derivation_note`, `method_note`
- `evidence_grade` per row (the population-data vs. guideline distinction is communicated implicitly via `use` and via which rows carry PMCIDs in `anchor_provenance`)
- `license` (legally important for the pipeline, but not relevant to the agent's claim-comparison job — kept in the internal ledger)
- `validation_grade`, `validation_tier` (kept in internal ledger; agent sees only `use:` and an optional wave-1 `crosscheck_status:` at the top level)
- raw source-side `variant` and `population_scope` labels; parse demographic meaning into structured fields instead
- All references to NHANES, CDC, PMC OA pipelines, sm-next paths, or legacy `output/markers/` artifacts

---

## 5. What gets surfaced

| Field | Purpose | Example |
|---|---|---|
| `anchor_version` | Stable reference the pipeline can resolve internally | `sm_wave_1_2026_05_05` |
| `canonical_slug` | Identity-registry canonical binding when available | `lpa` |
| `identity_binding_status` | Identity-registry quality tier for wave-2A+ payloads | `canonical_candidate`, `needs_identity_review`, `unreviewed_db_marker` |
| `rows[].stratum` and demographic fields | Population-aware comparison | `male_18_50` |
| `rows[].use` | Tells agent how the row may be used | `internal_research_gate` |
| `rows[].public_source_ids` | Row-level paper backing; lets agent know "this specific row is paper-backed" without revealing the pipeline | ApoB row 1: `pmcids: ["PMC10498001"]` |
| `known_research_context.pmids` | Marker-wide dedup hint: "RC already discovered these papers; don't re-fetch" | populated per marker from RC research |
| `annotations[].public_reference` | Public URL/PMID for guideline annotations so the agent can verify them legitimately | ADA Standards of Care 2025 URL |
| `mo_research_context.pmids` (calculated_surface only) | Surfaces public PMIDs already known on the MO side, **without** exposing the MO target value or rationale | TG/HDL: 6 PMIDs; target range is hidden |

---

## 6. Per-marker handling

| Marker | `source_policy` | Rows | Public IDs surfaced | Open question |
|---|---|---|---|---|
| `hba1c` | `frozen_standard_medical_anchor` | 8 sex × age | none (population-derived, no paper backing) | none |
| `apob` | `frozen_standard_medical_anchor` | 9 (1 all-adults display + 8 sex × age internal) | PMCID `PMC10498001` attached to row 1 only via `rows[0].public_source_ids` | none |
| `fasting-insulin` | `frozen_standard_medical_anchor` | 8 sex × age | none | `crosscheck_status: not_performed` — required before any row promotes to display |
| `lpa` | `not_in_frozen_wave_1` | 0 | none | **Decision required**: wave_2_freeze / document_exclusion / downgrade_from_pilot |
| `tg-hdl-ratio` | `calculated_surface` | 0 (formula surface) | 6 PMIDs in `mo_research_context`; MO target range hidden | none |

---


## 6A. Wave-2A contract addendum (2026-05-18)

Wave-2A is generated from the marker identity registry first and local import-ready SM bundles second. It is a review sample, not a display-ready source.

Locked decisions:

- Wave-2A rows use the same logical row shape as wave-1. Raw `variant` and `population_scope` labels are not agent-visible.
- Age-like source variants are parsed into `age_min` / `age_max` where possible. Examples: `greater-than-19-years` -> `age_min: 19`, `7-years-20-years` -> `age_min: 7`, `age_max: 20`, `newborn` -> `age_min: 0`, `age_max: 0`.
- `variant: all` is a no-op and is dropped.
- `identity_binding_status` is approved as a top-level wave-2A+ field. It exposes identity-registry binding quality, not range derivation.
- `crosscheck_status` is intentionally absent from wave-2A files until a later promotion pass exists.
- Wave-2A rows from `legacy_sql_backfill_final` bundles use `internal_research_gate`; other included rows use `comparison_only`.
- Promotion path: human review confirms marker identity and row semantics; a crosscheck/promotion pass records readiness; promotion is a regeneration event with a new `anchor_version`, not an in-place edit.
- Status values are validated against an allowlist. Non-allowlisted rows are excluded from the agent-visible payload and counted in the internal generation report.
- Common representation-only unit spellings may be normalized; real unit differences remain as row-level `unit` values.


## 6B. Wave-2B contract addendum (2026-05-18)

Wave-2B is generated from marker identity registry entries whose marker identity still needs arbitration. It uses the same local import-ready SM row source as Wave-2A but is stricter because the marker binding is unresolved.

Locked decisions:

- Wave-2B includes only `identity_binding_status: needs_identity_review` markers and excludes all prior wave-1 and wave-2A marker files.
- Every Wave-2B row is `use: internal_research_gate`. No Wave-2B row is `comparison_only` or `display_eligible`.
- Wave-2B rows are identity-review inputs only. They may help the council or reviewer inspect possible SM row semantics, but they must not be treated as approved marker identity or display-ready anchors.
- The row schema stays compatible with wave-1 and Wave-2A: raw `variant`, `population_scope`, provider fields, raw extraction fields, local paths, and source collection details are not agent-visible.
- `crosscheck_status` is intentionally absent. Promotion requires identity arbitration first, followed by a later crosscheck/promotion regeneration under a new `anchor_version`.
- Non-allowlisted status rows are excluded from the agent-visible payload, not preserved as review flags.
- Representation-only unit spellings may be normalized; real unit differences remain as row-level `unit` values.


## 6C. Wave-3 contract addendum (2026-05-18)

Wave-3 is generated from marker identity registry entries imported from the legacy database that have not yet received marker-identity adjudication. It is useful as broad SM input coverage, but it is the strictest generated wave.

Locked decisions:

- Wave-3 includes only `identity_binding_status: unreviewed_db_marker` markers and excludes all prior wave-1, Wave-2A, and Wave-2B marker files.
- Every Wave-3 row is `use: internal_research_gate`. No Wave-3 row is `comparison_only` or `display_eligible`.
- Wave-3 rows are unreviewed legacy-DB inputs. They do not imply bad data, but they also do not imply reviewed identity. They must not be treated as approved marker identity or display-ready anchors.
- The row schema stays compatible with prior waves: raw `variant`, `population_scope`, provider fields, raw extraction fields, local paths, and source collection details are not agent-visible.
- `crosscheck_status` is intentionally absent. Promotion requires marker identity review first, followed by a later crosscheck/promotion regeneration under a new `anchor_version`.
- Non-allowlisted status rows are excluded from the agent-visible payload, not preserved as review flags.
- Representation-only unit spellings may be normalized; real unit/method differences remain as row-level `unit` values and in the internal generation report.


## 6D. SM/MO stage separation

SM anchor files are council-stage comparison inputs, not MO discovery seeds.

- **Discovery stage:** MO search agents must not receive SM anchor rows. This avoids anchoring the MO search around conventional ranges.
- **Council/sanity-check stage:** SM anchors may be used to classify an MO claim's relationship to standard medical interpretation: concordant, divergent, narrower, wider, lower, higher, or review-needed.
- **Assembly/internal review stage:** `comparison_only` rows may appear in internal review surfaces. `internal_research_gate` rows remain council-comparison inputs only. Neither value is user-facing display permission.
- **Display promotion:** only `display_eligible` rows with promotion metadata may be surfaced as display-ready SM anchors.

## 7. What the pipeline does with these samples

1. **Read `rows`** as the agent-visible SM anchor for population-aware comparison. Stratify by sex × age × any other supplied context.
2. **Use `anchor_version`** as the stable token. Internal pipeline maps `anchor_version → frozen file` for integrity verification; the agent never sees that mapping.
3. **Treat `public_source_ids` and `known_research_context` as dedup signal**, not as derivation explanation. An agent that finds the same PMID through discovery should mark it `already_in_ledger` rather than treat it as fresh evidence.
4. **Surface `annotations` as context only.** They appear in dashboards but cannot override or replace population-RI rows.
5. **Refuse to construct an SM anchor for `not_in_frozen_wave_1` markers.** Route discovered claims for those markers to manual review.
6. **For `calculated_surface` markers**, do not return an SM anchor; compute the implied range from input evaluator markers via the `formula:` block.

---

## 8. What the doc set will need to change (HOLD until samples sign off)

These are queued; no doc files were modified in this pass.

- §04 schema: `sm_anchors` must support multiple stratified rows per marker. Add columns `stratum`, `sex`, `age_min`, `age_max`, plus optional `weight_min`/`weight_max`/`bmi_min`/`bmi_max`/`ethnicity`/`pregnancy_status`/`cohort`. Replace `anchor_grade` enum with a `use` enum (`internal_research_gate` / `comparison_only` / `display_eligible`).
- §04 schema: rename `guideline_source` → `anchor_version` (a stable token, not a name).
- §04 schema: add a sibling table `sm_anchor_public_ids` (or jsonb column) for `pmids[]`, `pmcids[]`, `dois[]`.
- §04 schema: add `sm_anchor_annotations` table (or jsonb) for guideline cutoffs attached to a marker.
- §04 schema: add `sm_calculated_surfaces` (or extend `sm_anchors` with `surface_kind`) to represent formula-derived markers.
- §05 sanity-check paragraph: reword to read stratified rows and apply sex/age-aware comparison; explicitly state that internal derivation is hidden from the council prompts.
- §07: must state explicitly that **hidden does not mean optional**. The internal ledger holds `license`, `source_url`, `raw_artifact_ref`, `raw_sha256`, etc., and is the authority for license/ToS checks. Legal review must consult it before any source-derived value, annotation, or row is promoted to displayable status. The agent contract hides these fields; the pipeline gate does not.
- §14: add open question — Lp(a) wave-2 decision.
- Drop the `source_type` / `anchor_grade` enum proposals from earlier rounds; they don't fit the hidden-derivation model.

The internal provenance ledger (where SHA-256s, source families, NHANES variable maps, raw artifact refs, and license data live) is **not** part of the agent contract. It needs its own location and access policy — proposed in §04 as a new private table `sm_anchor_internal_ledger` or as an out-of-band file outside the agentic project.

---

## 9. Codex review 2026-05-17 — resolutions

| # | Codex finding | Resolution |
|---|---|---|
| 1 | TG/HDL still leaked the MO target range despite saying it was hidden. | `target_range_optimal` removed from `tg-hdl-ratio.sample.yaml`. Only PMIDs and the population caveat remain. The agent must derive its expectation from open-source discovery. |
| 2 | Public IDs need row-level attachment, not marker-level. | Restructured: `public_source_ids` now lives inside `rows[]` (optional per row). `anchor_provenance` is meta only — visibility policy + hidden_derivation flag, no marker-wide ID list. ApoB's PMC10498001 now sits on `rows[0]`. |
| 3 | `crosscheck_status` was used in samples but missing from canonical shape. | Added to the canonical YAML block in section 2 as a top-level optional field. |
| 4 | §07 may overhide license; hidden ≠ optional for the legal gate. | Section 8 (queued doc changes) now explicitly requires §07 to state that the internal ledger remains the authority for license/ToS checks; hiding from the agent does not weaken the legal gate. |

## 10. Remaining open questions for reviewers

1. **Lp(a) policy**: Recommended option among the three in `lpa.sample.yaml`?
2. **PMIDs in `known_research_context`**: Should this be pre-populated per marker from the RC PMID inventory before review, or left empty as a placeholder until the agentic pipeline runs?
3. **`use:` defaults**: For wave-1 markers without crosscheck, all rows default to `internal_research_gate`. Confirm or adjust.
4. **Scaling to 108 markers**: Anything in the shape that would break or become unwieldy at scale? Anything that should hoist to a shared registry instead of being repeated per-file?

---

## 11. Reviewer verdict 2026-05-17 (second pass)

**Verdict:** Sign-off on the sample shape. The five YAMLs are consistent, the hidden-derivation principle is applied correctly, and the Codex resolutions are sound. Bottleneck moves to the contract docs (§04, §05, §07, §14), which still describe the pre-review single-row `sm_anchors` model.

**Sample-side action taken:** removed redundant `surface_kind: calculated_surface` from `tg-hdl-ratio.sample.yaml`; `source_policy: calculated_surface` is now the sole canonical discriminator.

### Three structural questions the reviewer raised — proposed answers

**Q1: `already_in_ledger` — schema field or prompt-only?**

`[JUDGMENT]` Schema field. Add a boolean column `was_in_known_research_context boolean DEFAULT false` to `biomarker_claims` in §04. Reason: future audits need to distinguish freshly-discovered evidence from rediscovered evidence; prompt-only behavior is unauditable and drifts across council prompts. The agent sets the flag when a discovered claim's PMID/PMCID/DOI matches the marker's `known_research_context` ID set.

**Q2: `crosscheck_status` SQL mapping — column on `sm_anchors`, marker-level table, or anchor_version field?**

`[JUDGMENT]` New marker-level metadata table. Crosscheck applies per-marker-per-anchor-version, not per-row.

```sql
CREATE TABLE sm_anchor_marker_meta (
    marker text NOT NULL,
    anchor_version text NOT NULL,
    crosscheck_status text CHECK (crosscheck_status IN (
        'not_performed',
        'performed_clean',
        'performed_with_deltas',
        'not_applicable'
    )),
    doctrine_version text,
    frozen_at timestamptz,
    notes text,
    PRIMARY KEY (marker, anchor_version)
);
```

Keeps `sm_anchors` strictly row-focused; gives a clean home for anchor-version-scoped metadata that doesn't belong on every row.

**Q3: `known_research_context` schema home — same as `sm_anchor_public_ids` or separate?**

`[JUDGMENT]` Separate normalized table. `sm_anchor_public_ids` is row-level (which paper backs *this row*). `known_research_context` is marker-wide dedup signal across paradigms (which papers the RC/MO efforts already discovered for *this marker*).

```sql
CREATE TABLE marker_known_public_ids (
    marker text NOT NULL,
    paradigm_track text CHECK (paradigm_track IN ('RC', 'MO', 'SM_adjacent')),
    id_type text CHECK (id_type IN ('pmid', 'pmcid', 'doi')),
    public_id text NOT NULL,
    recorded_at timestamptz NOT NULL,
    note text,
    PRIMARY KEY (marker, paradigm_track, id_type, public_id)
);

CREATE INDEX idx_marker_known_public_ids_lookup ON marker_known_public_ids(marker, public_id);
```

Supports the agent's core dedup query: "is PMID X already known for marker Y?" as a single indexed lookup.

### Consolidated action list (priority order)

| Priority | Action | File / target |
|---|---|---|
| **P0** | Replace `sm_anchors` schema with stratified-row design: `stratum`, `sex`, `age_min`/`age_max`, optional context cols (`weight_*`, `bmi_*`, `ethnicity`, `pregnancy_status`, `cohort`), `use` enum, `anchor_version`, `range_order`, `min`, `max`, `status`, `primary_display`. Drop `anchor_grade`, `guideline_source`, `target_value`/`target_range_low`/`target_range_high` (replaced by row-level `min`/`max`). | §04 |
| **P0** | Add sibling tables: `sm_anchor_public_ids` (row-level), `sm_anchor_annotations` (marker-level), `sm_calculated_surfaces` (formula surfaces), `sm_anchor_marker_meta` (per Q2 above), `marker_known_public_ids` (per Q3 above), `sm_anchor_internal_ledger` (private; SHA-256s, source families, license, NHANES variable maps, raw artifact refs). | §04 |
| **P0** | Remove `source_url` and `citation` from agent-visible `sm_anchors`; move to `sm_anchor_internal_ledger`. | §04 |
| **P0** | Add `was_in_known_research_context boolean DEFAULT false` to `biomarker_claims` (per Q1 above). | §04 |
| **P1** | Rewrite §05 council sanity-check paragraph: stratified-row aware (sex/age comparison), with explicit statement that internal derivation is hidden from council prompts. | §05 |
| **P1** | Add "hidden ≠ optional" paragraph to §07: internal provenance ledger remains the authority for license/ToS checks; agent contract hiding does not weaken the legal gate. | §07 |
| **P1** | Update §14 SM-anchor blocker description: drop "one row per marker" language; note TG/HDL is a calculated surface; note Lp(a) is `not_in_frozen_wave_1` with a separate decision needed. | §14 |
| **P2** | Apply N1–N3 schema fixes from prior validation reports (envelope FK, `no_open_source_support_yet` removal, `range_order` semantics). | §04, §17 |
| **P2** | Address remaining pre-existing gaps: takedown column on `biomarker_claims`, `citation_edges.cited_registry_id` FK, marker_glossary seed languages, practitioner create workflow, lock mechanism, run compaction shape. | §04, §10, §16 |

---

## 12. Files affected (sample directory only)

- `apob.sample.yaml` — 9 rows (1 display-eligible + 8 internal gate); `PMC10498001` on `rows[0].public_source_ids`
- `hba1c.sample.yaml` — 8 rows, no row-level public IDs (population-derived)
- `fasting-insulin.sample.yaml` — 8 rows, no row-level public IDs, no guideline annotations, `crosscheck_status: not_performed`
- `lpa.sample.yaml` — empty rows, `decision_needed:` block
- `tg-hdl-ratio.sample.yaml` — empty rows, `formula:` block, 6 PMIDs in `mo_research_context` (target range hidden)

No documentation files were modified. Doc changes are queued in section 8 and will land after sign-off.
