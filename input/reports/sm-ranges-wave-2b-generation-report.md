# SM Agent-Visible Input Generation Report — Wave-2B

**Date:** 2026-05-18
**Source universe:** internal marker identity registry (`identity_ground_truth`)
**Value-row source:** local `output/import-ready-sm/*/bundle.yaml` files
**Generator:** `scripts/agentic_workflow/generate_sm_wave2b_agent_input.py`
**Output:** `/home/zoltan/Projects/metabolicum-research/docs/agentic-workflow/input/sm-ranges/wave-2b`
**Status:** generated review sample; all emitted rows are `internal_research_gate` pending identity arbitration

Internal-only report. Do not ship this report inside the agent-visible payload.

## Scope

Wave-2B includes markers with `needs_identity_review` binding status and local import-ready SM rows. It excludes wave-1, wave-2A, superseded aliases, canonical candidates already generated in wave-2A, and `unreviewed_db_marker` entries.

`crosscheck_status` is intentionally absent from wave-2B agent-visible files. Wave-2B rows are locked to `internal_research_gate`; they are identity-review inputs only and cannot promote until marker identity is resolved in the registry and a later wave regenerates them.

## Summary

- Marker files generated: `90`
- Range rows generated: `285`
- Audit issues: `0`

### Entity Counts

| Entity type | Count |
|---|---:|
| `evaluator` | 31 |
| `raw_input_marker` | 59 |

### Final Mode Counts

| Final mode | Count |
|---|---:|
| `legacy_sql_backfill_final` | 79 |
| `adult_single_site_interval_final` | 4 |
| `adult_interval_consensus_final` | 3 |
| `adult_mixed_scope_bundle_final` | 1 |
| `adult_consensus_bundle_final` | 1 |
| `adult_fragmented_multi_site_bundle_final` | 1 |
| `adult_population_table_final` | 1 |

### Exclusion Reasons

| Reason | Registry markers |
|---|---:|
| `binding_status_canonical_candidate` | 106 |
| `binding_status_unreviewed_db_marker` | 687 |
| `included` | 90 |
| `no_import_ready_rows` | 10 |
| `previous_wave_already_generated` | 217 |

### Use Counts

| Use | Row count |
|---|---:|
| `internal_research_gate` | 285 |

### Row Count Distribution

| Rows per marker | Marker count |
|---:|---:|
| 1 | 4 |
| 2 | 26 |
| 3 | 46 |
| 4 | 2 |
| 6 | 10 |
| 11 | 1 |
| 12 | 1 |

### Excluded Invalid Status Rows

Rows whose status is not in the allowlist are excluded from the agent-visible payload.

| Marker slug | Excluded status values |
|---|---|
| _none_ | _none_ |

### Row Unit Differences After Representation Normalization

| Top-level unit -> row unit | Row count |
|---|---:|
| _none_ | 0 |

## Candidate Manifest

| Marker slug | Name | Entity | Rows | Final mode | Unit |
|---|---|---|---:|---|---|
| `1-5-anhydroglucitol` | 1,5-Anhydroglucitol | `raw_input_marker` | 12 | `legacy_sql_backfill_final` | mcg/mL |
| `5-nt` | 5'-Nucleotidase | `evaluator` | 11 | `adult_interval_consensus_final` | IU/L |
| `5-nucleotidase` | 5'-Nucleotidase | `evaluator` | 2 | `legacy_sql_backfill_final` | IU/L |
| `adenosine-deaminase` | Adenosine deaminase | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | mU/g Hb |
| `adenosine-deaminase-csf` | Adenosine deaminase | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | IU/L |
| `adenosine-deaminase-pericardial-fluid` | Adenosine deaminase | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | IU/L |
| `adenosine-deaminase-peritoneal-fluid` | Adenosine deaminase | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | IU/L |
| `adenosine-deaminase-pleural-fluid` | Adenosine deaminase | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | IU/L |
| `albumin-2` | Albumin | `evaluator` | 6 | `legacy_sql_backfill_final` | mg/dL |
| `albumin-3` | Microalbumin | `evaluator` | 2 | `legacy_sql_backfill_final` | mg/dL |
| `aldosterone` | Aldosterone | `evaluator` | 2 | `adult_mixed_scope_bundle_final` | ng/dL |
| `aldosterone-2` | Aldosterone | `evaluator` | 3 | `legacy_sql_backfill_final` | µg/d |
| `alpha-1-fetoprotein` | Alpha-1-Fetoprotein | `raw_input_marker` | 1 | `adult_interval_consensus_final` | ng/mL |
| `alpha-1-fetoprotein-csf` | Alpha-1-Fetoprotein | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | ng/mL |
| `amikacin` | Amikacin | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | mcg/mL |
| `amikacin-peak` | Amikacin | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | mcg/mL |
| `amikacin-trough` | Amikacin | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | mcg/mL |
| `ammonia-4` | Ammonia | `raw_input_marker` | 6 | `legacy_sql_backfill_final` | ug/dL |
| `amylase` | Amylase | `raw_input_marker` | 6 | `legacy_sql_backfill_final` | IU/L |
| `amylase-2` | Amylase | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | U/g creatinine |
| `angiotensin-converting-enzyme` | Angiotensin converting enzyme | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | IU/L |
| `angiotensin-converting-enzyme-csf` | Angiotensin converting enzyme | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | IU/L |
| `beryllium-2` | Beryllium | `raw_input_marker` | 2 | `adult_consensus_bundle_final` | ng/mL |
| `beta-2-microglobulin-urine` | Beta-2-Microglobulin | `evaluator` | 2 | `legacy_sql_backfill_final` | ug/L |
| `beta2m` | Beta-2-Microglobulin | `evaluator` | 2 | `adult_fragmented_multi_site_bundle_final` | mg/L |
| `beta2m-2` | Beta-2-Microglobulin | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | mg/L |
| `bk-virus-dna` | BK virus DNA | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | copies/mL |
| `bk-virus-dna-urine` | BK virus DNA | `evaluator` | 2 | `legacy_sql_backfill_final` | copies/mL |
| `ca` | Calcium | `evaluator` | 3 | `adult_population_table_final` | mg/dL |
| `calcium-urine` | Calcium | `evaluator` | 3 | `legacy_sql_backfill_final` | mg/mg |
| `chloride-3` | Chloride | `evaluator` | 3 | `legacy_sql_backfill_final` | mmol/L |
| `choriogonadotropin-beta-subunit-csf` | Choriogonadotropin.beta subunit | `evaluator` | 2 | `legacy_sql_backfill_final` | IU/L |
| `chromium-2` | Chromium | `evaluator` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `cobalt-2` | Cobalt | `evaluator` | 3 | `legacy_sql_backfill_final` | ug/L |
| `coq10` | Coenzyme Q10 | `evaluator` | 1 | `adult_single_site_interval_final` | μg/mL |
| `cortisol-am` | Cortisol | `evaluator` | 3 | `legacy_sql_backfill_final` | ug/dL |
| `cortisol-saliva` | Cortisol | `evaluator` | 3 | `legacy_sql_backfill_final` | ug/dL |
| `cu` | Copper | `evaluator` | 4 | `adult_single_site_interval_final` | μg/dL |
| `cu-3` | Copper | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ug/dL |
| `eastern-equine-encephalitis-virus-ab-igg` | Eastern equine encephalitis virus IgG Ab | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | IV |
| `eastern-equine-encephalitis-virus-ab-igg-csf` | Eastern equine encephalitis virus IgG Ab | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | IV |
| `enolase-neuron-specific` | Enolase.neuron specific | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | ng/mL |
| `enolase-neuron-specific-csf` | Enolase.neuron specific | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `gentamicin` | Gentamicin | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | mcg/mL |
| `gentamicin-peak` | Gentamicin | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | mcg/mL |
| `gentamicin-trough` | Gentamicin | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | mcg/mL |
| `glucose-2` | Glucose | `evaluator` | 3 | `legacy_sql_backfill_final` | mg/dL |
| `glucose-csf` | Glucose | `evaluator` | 6 | `legacy_sql_backfill_final` | mg/dL |
| `glucose-post-cfst` | Fasting glucose | `evaluator` | 3 | `legacy_sql_backfill_final` | mg/dL |
| `glutamate-decarboxylase-65-ab-csf` | Glutamate decarboxylase 65 Ab | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | IU/mL |
| `hemoglobin-4` | Hemoglobin | `evaluator` | 3 | `legacy_sql_backfill_final` | g/dL |
| `histamine-2` | Histamine | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | nmol/L |
| `histamine-3` | Histamine | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | ng/mL |
| `iga` | IgA | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | mg/dL |
| `iga-csf` | IgA | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | mg/dL |
| `igg` | IgG | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | mg/dL |
| `igg-csf` | IgG | `raw_input_marker` | 4 | `legacy_sql_backfill_final` | mg/dL |
| `igm` | IgM | `raw_input_marker` | 6 | `legacy_sql_backfill_final` | mg/dL |
| `igm-csf` | IgM | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | mg/dL |
| `insulin-post-cfst` | Insulin | `evaluator` | 3 | `legacy_sql_backfill_final` | µIU/mL |
| `interleukin-10-csf` | Interleukin 10 | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | pg/mL |
| `lactate` | Lactate | `evaluator` | 1 | `adult_single_site_interval_final` | mg/dL |
| `lactate-2` | Lactate | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | mmol/L |
| `magnesium` | Magnesium | `evaluator` | 3 | `legacy_sql_backfill_final` | mg/dL |
| `magnesium-serum-2` | Magnesium | `evaluator` | 3 | `legacy_sql_backfill_final` | mg/d |
| `manganese-2` | Manganese | `evaluator` | 3 | `legacy_sql_backfill_final` | ug/L |
| `measles-virus-ab-igg` | Measles virus IgG Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | AU/mL |
| `measles-virus-ab-igg-csf` | Measles virus IgG Ab | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | AU/mL |
| `mma-2` | Creatinine | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | H |
| `molybdenum` | Molybdenum | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `molybdenum-2` | Molybdenum | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | ng/mL |
| `plasminogen-activator-inhibitor-1-ag` | Plasminogen activator inhibitor 1 Ag | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | IU/mL |
| `plasminogen-activator-inhibitor-1-ag-2` | Plasminogen activator inhibitor 1 Ag | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `procalcitonin` | Procalcitonin | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | ng/mL |
| `pyruvate` | Pyruvate | `evaluator` | 1 | `adult_single_site_interval_final` | mg/dL |
| `pyruvate-3` | Pyruvate | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | mmol/L |
| `selenium-2` | Selenium | `evaluator` | 3 | `legacy_sql_backfill_final` | ug/L |
| `serotonin` | Serotonin | `raw_input_marker` | 6 | `legacy_sql_backfill_final` | ng/mL |
| `serotonin-2` | Serotonin | `raw_input_marker` | 6 | `legacy_sql_backfill_final` | ng/mL |
| `somatotropin` | Somatotropin | `raw_input_marker` | 6 | `legacy_sql_backfill_final` | ng/mL |
| `somatotropin-baseline` | Somatotropin | `raw_input_marker` | 6 | `legacy_sql_backfill_final` | ng/mL |
| `tobramycin` | Tobramycin | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | mcg/mL or ug/mL |
| `tobramycin-peak` | Tobramycin | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | mcg/mL |
| `tobramycin-trough` | Tobramycin | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | mcg/mL |
| `ubiquinone-10` | Coenzyme Q10 | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | mg/L |
| `vancomycin` | Vancomycin | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | mcg/mL |
| `vancomycin-peak` | Vancomycin | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | mcg/mL |
| `vancomycin-trough` | Vancomycin | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | mcg/mL |
| `zn` | Zinc | `evaluator` | 3 | `adult_interval_consensus_final` | μg/dL |
| `zn-2` | Zinc | `raw_input_marker` | 6 | `legacy_sql_backfill_final` | ug/dL |

## Locked Generation Rules

- Marker universe comes from the marker identity registry, not the filesystem bundle list.
- Numeric rows come from local import-ready SM bundles only after registry filtering.
- Wave-2B row schema is kept compatible with wave-1: raw `variant` and `population_scope` are not exposed.
- Age-like source variants are parsed into structured `age_min` / `age_max` when those fields are otherwise null; no-op `variant: all` is dropped.
- All wave-2B rows are `internal_research_gate`; no row is comparison-only or display eligible until marker identity is resolved.
- Promotion path: human review confirms marker identity and row semantics; crosscheck/promotion pass records readiness; only then can a row be regenerated into a less restricted use tier.
- `crosscheck_status` is omitted from wave-2B files until the promotion pass exists; it remains a wave-1 frozen-summary concept for now.
- Rows with non-allowlisted status values are excluded from the agent-visible payload and counted in the internal report.
- Representation-equivalent unit spellings are normalized using the marker identity registry plus local typography variants; real unit differences remain row-level `unit` values.
- Agent-visible files omit provider names, provider URLs, local paths, raw extraction values, and source collection details.
- Public IDs are exposed only when PMID/PMCID/DOI can be extracted from a source URL.
