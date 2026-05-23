# SM Agent-Visible Input Generation Report — Wave-2A

**Date:** 2026-05-18
**Source universe:** internal marker identity registry (`identity_ground_truth`)
**Value-row source:** local `output/import-ready-sm/*/bundle.yaml` files
**Generator:** `scripts/agentic_workflow/generate_sm_wave2_agent_input.py`
**Output:** `/home/zoltan/Projects/metabolicum-research/docs/agentic-workflow/input/sm-ranges/wave-2`
**Status:** generated review sample; rows are either `comparison_only` or `internal_research_gate` pending human promotion

Internal-only report. Do not ship this report inside the agent-visible payload.

## Scope

Wave-2A includes registry-approved canonical candidates with local import-ready SM rows. It excludes wave-1 files, superseded aliases, `needs_identity_review`, and `unreviewed_db_marker` entries.

`crosscheck_status` is intentionally absent from wave-2A agent-visible files. In wave-1 it summarized frozen crosscheck state; in wave-2A rows are locked to `internal_research_gate` or `comparison_only` until a later human-review plus crosscheck/promotion pass creates promoted rows.

## Summary

- Marker files generated: `109`
- Range rows generated: `436`
- Audit issues: `0`

### Entity Counts

| Entity type | Count |
|---|---:|
| `calculator` | 2 |
| `evaluator` | 107 |

### Final Mode Counts

| Final mode | Count |
|---|---:|
| `legacy_sql_backfill_final` | 60 |
| `adult_single_site_interval_final` | 19 |
| `adult_interval_consensus_final` | 14 |
| `adult_population_table_final` | 8 |
| `adult_fragmented_multi_site_bundle_final` | 7 |
| `adult_mixed_scope_bundle_final` | 1 |

### Exclusion Reasons

| Reason | Registry markers |
|---|---:|
| `binding_status_needs_identity_review` | 100 |
| `binding_status_unreviewed_db_marker` | 687 |
| `included` | 109 |
| `no_import_ready_rows` | 106 |
| `wave_1_already_generated` | 108 |

### Use Counts

| Use | Row count |
|---|---:|
| `comparison_only` | 251 |
| `internal_research_gate` | 185 |

### Row Count Distribution

| Rows per marker | Marker count |
|---:|---:|
| 1 | 22 |
| 2 | 30 |
| 3 | 39 |
| 4 | 1 |
| 5 | 4 |
| 6 | 2 |
| 8 | 2 |
| 9 | 1 |
| 10 | 1 |
| 12 | 2 |
| 13 | 2 |
| 14 | 1 |
| 22 | 1 |
| 80 | 1 |

### Excluded Invalid Status Rows

Rows whose status is not in the allowlist are excluded from the agent-visible payload.

| Marker slug | Excluded status values |
|---|---|
| `remnant-c` | `high-density-lipoprotein-hdl-cholesterol` (1) |

### Row Unit Differences After Representation Normalization

| Top-level unit -> row unit | Row count |
|---|---:|
| `ng/mL -> ug/L` | 1 |
| `ng/mL -> μg/L` | 1 |
| `nmol/min/mL -> U/mL` | 1 |
| `ug/L -> μg/L` | 2 |

## Candidate Manifest

| Marker slug | Name | Entity | Rows | Final mode | Unit |
|---|---|---|---:|---|---|
| `1-25-dihydroxyvitamin-d` | 1,25-Dihydroxyvitamin D | `evaluator` | 2 | `adult_mixed_scope_bundle_final` | pg/mL |
| `11-deoxycortisol` | 11-Deoxycortisol | `evaluator` | 3 | `legacy_sql_backfill_final` | ng/dL |
| `5-hydroxyindoleacetate-creatinine-urine` | 5-Hydroxyindoleacetate/Creatinine | `evaluator` | 4 | `legacy_sql_backfill_final` | mg/g creatinine |
| `5-hydroxyindoleacetate-urine` | 5-Hydroxyindoleacetate | `evaluator` | 2 | `legacy_sql_backfill_final` | mg/g creatinine |
| `acth` | ACTH (Adrenocorticotropic Hormone) | `evaluator` | 1 | `adult_interval_consensus_final` | pg/mL |
| `adiponectin` | Adiponectin | `evaluator` | 3 | `adult_population_table_final` | μg/mL |
| `alpha-galactosidase-a` | Alpha galactosidase A | `evaluator` | 3 | `legacy_sql_backfill_final` | IU/L |
| `alpha-melanocyte-stimulating-hormone` | Alpha melanocyte stimulating hormone | `evaluator` | 2 | `legacy_sql_backfill_final` | pg/mL |
| `aluminum-creatinine-urine` | Aluminum/Creatinine | `evaluator` | 3 | `legacy_sql_backfill_final` | ug/L |
| `amh` | Mullerian inhibiting substance | `evaluator` | 10 | `adult_single_site_interval_final` | ng/mL |
| `anti-dsdna` | Anti-dsDNA | `evaluator` | 1 | `adult_single_site_interval_final` | IU/mL |
| `aptt` | aPTT in Platelet poor plasma by Coagulation assay | `evaluator` | 3 | `legacy_sql_backfill_final` | seconds |
| `arsenic-creatinine-urine` | Arsenic/Creatinine | `evaluator` | 3 | `legacy_sql_backfill_final` | microg/L |
| `arsenic-inorganic-urine` | Arsenic.inorganic | `evaluator` | 2 | `legacy_sql_backfill_final` | ug/L |
| `bilirubin-glucuronidated-bilirubin-albumin-bound` | Bilirubin.direct | `evaluator` | 2 | `legacy_sql_backfill_final` | mg/dL |
| `bio-t` | Bioavailable Testosterone | `evaluator` | 22 | `adult_single_site_interval_final` | ng/dL |
| `bnp` | B-type Natriuretic Peptide | `evaluator` | 80 | `adult_interval_consensus_final` | pg/mL |
| `buspirone` | busPIRone | `evaluator` | 2 | `legacy_sql_backfill_final` | ng/mL |
| `c-peptide-fasting` | C-Peptide (Fasting) | `evaluator` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `c-peptide-urine` | C peptide | `evaluator` | 3 | `legacy_sql_backfill_final` | μg/24 hours |
| `calcium-ionized` | Calcium.ionized | `evaluator` | 3 | `adult_population_table_final` | mg/dL |
| `calprotectin` | Calprotectin | `evaluator` | 1 | `adult_fragmented_multi_site_bundle_final` | mcg/g |
| `cat` | Cat dander IgE Ab | `evaluator` | 3 | `legacy_sql_backfill_final` | kU/L |
| `cells-cd3-tcr-alpha-beta-cells` | CD3+TCR alpha beta+ cells/cells in Blood | `evaluator` | 2 | `legacy_sql_backfill_final` | cells/uL |
| `chloride-2` | Volume in Urine collected for unspecified duration | `evaluator` | 2 | `legacy_sql_backfill_final` | microg/dL |
| `chromium-creatinine-urine` | Chromium/Creatinine | `evaluator` | 2 | `legacy_sql_backfill_final` | ug/L |
| `ck` | Creatine Kinase | `evaluator` | 13 | `adult_population_table_final` | IU/L |
| `cobalt-creatinine-urine` | Cobalt/Creatinine | `evaluator` | 3 | `legacy_sql_backfill_final` | ug/L |
| `collagen-crosslinked-n-telopeptide-creatinine-urine` | Collagen crosslinked N-telopeptide/Creatinine | `evaluator` | 3 | `legacy_sql_backfill_final` | nM BCE/mM creatinine |
| `complement-alternate-pathway-ah50-actual-normal` | Complement alternate pathway AH50 actual/normal in Serum by Immunoassay | `evaluator` | 3 | `legacy_sql_backfill_final` | % |
| `cortisol-free-serum-whole-blood` | Cortisol Free | `evaluator` | 3 | `legacy_sql_backfill_final` | ug/dL |
| `ctni` | Troponin I | `evaluator` | 3 | `adult_single_site_interval_final` | ng/L |
| `ctnt` | Troponin T | `evaluator` | 5 | `adult_interval_consensus_final` | ng/L |
| `ctx` | Collagen crosslinked C-telopeptide | `evaluator` | 12 | `legacy_sql_backfill_final` | pg/mL |
| `delta-aminolevulinate-urine` | Delta aminolevulinate | `evaluator` | 3 | `legacy_sql_backfill_final` | umol/L |
| `dhea` | Dehydroepiandrosterone (DHEA) | `evaluator` | 6 | `legacy_sql_backfill_final` | ng/mL |
| `dhea-s` | DHEA-Sulfate | `evaluator` | 14 | `adult_population_table_final` | ug/dL |
| `e1` | Estrone (E1) | `evaluator` | 2 | `adult_interval_consensus_final` | pg/mL |
| `ecp` | Eosinophil cationic protein (ECP) | `evaluator` | 1 | `adult_interval_consensus_final` | ug/L |
| `elastase-pancreatic` | Elastase.pancreatic | `evaluator` | 3 | `legacy_sql_backfill_final` | µg/g |
| `fatty-acids-nonesterified` | Fatty acids.nonesterified | `evaluator` | 3 | `legacy_sql_backfill_final` | mmol/L |
| `fib-4` | FIB-4 Index | `calculator` | 1 | `adult_single_site_interval_final` | index |
| `fibrin-fibrinogen-fragments` | Fibrin+Fibrinogen fragments | `evaluator` | 2 | `legacy_sql_backfill_final` | mcg/mL |
| `fibrinogen-ag` | Fibrinogen Ag | `evaluator` | 3 | `legacy_sql_backfill_final` | mg/dL |
| `fibroblast-growth-factor-23-intact` | Fibroblast growth factor 23.intact | `evaluator` | 2 | `legacy_sql_backfill_final` | pg/mL |
| `free-carnitine` | Free Carnitine | `evaluator` | 8 | `adult_single_site_interval_final` | μmol/L |
| `galactose-1-phosphate` | Galactose 1 phosphate | `evaluator` | 2 | `legacy_sql_backfill_final` | mg/dL |
| `galectin-3` | Galectin-3 | `evaluator` | 1 | `adult_interval_consensus_final` | ng/mL |
| `galectin-3-2` | Galectin 3 | `evaluator` | 2 | `legacy_sql_backfill_final` | ng/mL |
| `gastrin` | Gastrin | `evaluator` | 2 | `legacy_sql_backfill_final` | pg/mL |
| `glucose-6-phosphate-dehydrogenase` | Glucose-6-Phosphate dehydrogenase | `evaluator` | 3 | `legacy_sql_backfill_final` | U/g Hb |
| `hemoglobin-pattern` | Hemoglobin pattern | `evaluator` | 2 | `legacy_sql_backfill_final` | % |
| `histoplasma-capsulatum-ag-urine` | Histoplasma capsulatum Ag | `evaluator` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `homovanillate-creatinine-urine` | Homovanillate/Creatinine | `evaluator` | 2 | `legacy_sql_backfill_final` | mg/d |
| `ibil` | Indirect Bilirubin | `evaluator` | 1 | `adult_single_site_interval_final` | mg/dL |
| `il-1beta` | IL-1 Beta | `evaluator` | 2 | `adult_fragmented_multi_site_bundle_final` | pg/mL |
| `il-6` | Interleukin 6 | `evaluator` | 1 | `adult_fragmented_multi_site_bundle_final` | pg/mL |
| `immunoglobulin-light-chains-lambda-free` | Lambda light chains.free | `evaluator` | 3 | `legacy_sql_backfill_final` | mg/L |
| `insulin-like-growth-factor-binding-protein-1` | Insulin-like growth factor binding protein 1 | `evaluator` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `insulin-like-growth-factor-binding-protein-3` | Insulin-like growth factor binding protein 3 | `evaluator` | 3 | `legacy_sql_backfill_final` | ug/L |
| `iron` | Iron | `evaluator` | 3 | `legacy_sql_backfill_final` | ug/dL |
| `ldl-particle-size` | LDL Particle Size | `evaluator` | 1 | `adult_single_site_interval_final` | nm |
| `leptin` | Leptin | `evaluator` | 2 | `adult_population_table_final` | ng/mL |
| `lipoprotein-associated-phospholipase-a2` | Lipoprotein associated phospholipase A2 | `evaluator` | 3 | `adult_single_site_interval_final` | nmol/min/mL |
| `lp-ir` | Lp-IR Score | `evaluator` | 1 | `adult_single_site_interval_final` | Score 0-100 |
| `lpa` | Lipoprotein(a) | `evaluator` | 5 | `adult_interval_consensus_final` | nmol/L |
| `mercury-blood` | Mercury/Creatinine | `evaluator` | 2 | `adult_interval_consensus_final` | ug/L |
| `mma` | Methylmalonate | `evaluator` | 3 | `adult_population_table_final` | nmol/L |
| `niacin` | Niacin | `evaluator` | 2 | `adult_fragmented_multi_site_bundle_final` | ng/mL |
| `nickel-creatinine-urine` | Nickel/Creatinine | `evaluator` | 3 | `legacy_sql_backfill_final` | mcg/g creatinine |
| `nt-probnp` | Natriuretic peptide.B prohormone N-Terminal | `evaluator` | 13 | `adult_single_site_interval_final` | pg/mL |
| `orotate-creatinine-urine` | Orotate/Creatinine | `evaluator` | 2 | `legacy_sql_backfill_final` | mmol/mol creatinine |
| `osteocalcin` | Osteocalcin | `evaluator` | 12 | `adult_population_table_final` | ng/mL |
| `oxidized-ldl` | Oxidized LDL | `evaluator` | 1 | `adult_single_site_interval_final` | IU/L |
| `p1np` | P1NP | `evaluator` | 3 | `adult_population_table_final` | ng/mL |
| `pancreastatin` | Pancreastatin | `evaluator` | 3 | `legacy_sql_backfill_final` | pg/mL |
| `ph-urine` | pH of Urine | `evaluator` | 3 | `legacy_sql_backfill_final` | pH units |
| `porphobilinogen-urine` | Porphobilinogen | `evaluator` | 3 | `legacy_sql_backfill_final` | µmol/d |
| `proinsulin` | Proinsulin | `evaluator` | 1 | `adult_interval_consensus_final` | pmol/L |
| `prostaglandin-d2-urine` | Prostaglandin D2 | `evaluator` | 2 | `legacy_sql_backfill_final` | ng/g Creatinine |
| `protein-creatinine-urine` | Protein/Creatinine | `evaluator` | 3 | `legacy_sql_backfill_final` | mg/d |
| `protein-urine` | Protein | `evaluator` | 3 | `legacy_sql_backfill_final` | mg/24 hours |
| `protoporphyrin-zinc-2` | Protoporphyrin.zinc | `evaluator` | 2 | `legacy_sql_backfill_final` | ug/dL |
| `pt` | Prothrombin Time | `evaluator` | 1 | `adult_single_site_interval_final` | seconds |
| `pth` | Parathyroid Hormone | `evaluator` | 1 | `adult_single_site_interval_final` | pg/mL |
| `remnant-c` | Remnant Cholesterol | `calculator` | 6 | `adult_single_site_interval_final` | mg/dL |
| `renin` | Renin | `evaluator` | 5 | `adult_single_site_interval_final` | ng/mL/hr |
| `reverse-t3` | Triiodothyronine (T3).reverse | `evaluator` | 2 | `adult_interval_consensus_final` | ng/dL |
| `rheumatoid-factor` | Rheumatoid factor | `evaluator` | 1 | `adult_interval_consensus_final` | IU/mL |
| `s100-calcium-binding-protein-b` | S100 calcium binding protein B | `evaluator` | 2 | `legacy_sql_backfill_final` | ng/L |
| `stfr` | Transferrin receptor.soluble | `evaluator` | 1 | `adult_interval_consensus_final` | mg/L |
| `sulfate-urine` | Sulfate | `evaluator` | 3 | `legacy_sql_backfill_final` | mEq/24 hours |
| `t3-uptake` | T3 Uptake | `evaluator` | 3 | `legacy_sql_backfill_final` | % |
| `testosterone-free` | Testosterone Free | `evaluator` | 9 | `legacy_sql_backfill_final` | pg/mL |
| `thallium-creatinine-urine` | Thallium/Creatinine | `evaluator` | 2 | `legacy_sql_backfill_final` | ug/L |
| `thyroglobulin` | Thyroglobulin | `evaluator` | 1 | `adult_fragmented_multi_site_bundle_final` | ng/mL |
| `thyroglobulin-antibodies` | Thyroglobulin Antibodies | `evaluator` | 1 | `adult_fragmented_multi_site_bundle_final` | IU/mL |
| `thyroxine-binding-globulin` | Thyroxine binding globulin | `evaluator` | 6 | `legacy_sql_backfill_final` | mcg/mL |
| `tmao` | TMAO | `evaluator` | 3 | `adult_single_site_interval_final` | μM |
| `tpo-antibodies` | TPO Antibodies | `evaluator` | 1 | `adult_interval_consensus_final` | IU/mL |
| `transferrin-carbohydrate-deficient-transferrin-total` | Transferrin.carbohydrate deficient/Transferrin.total in Serum or Plasma | `evaluator` | 3 | `legacy_sql_backfill_final` | % |
| `transferrin-saturation` | Transferrin Saturation | `evaluator` | 2 | `adult_single_site_interval_final` | % |
| `troponin-t-cardiac-2` | Troponin T.cardiac | `evaluator` | 8 | `legacy_sql_backfill_final` | ng/L |
| `tryptase` | Tryptase | `evaluator` | 1 | `adult_interval_consensus_final` | ng/mL |
| `tumor-necrosis-factor-alpha` | Tumor necrosis factor.alpha | `evaluator` | 2 | `legacy_sql_backfill_final` | pg/mL |
| `urea-nitrogen-urine` | Urea nitrogen | `evaluator` | 3 | `legacy_sql_backfill_final` | g/day |
| `vanillylmandelate-creatinine-urine` | Vanillylmandelate/Creatinine | `evaluator` | 2 | `legacy_sql_backfill_final` | mg/g CRT |
| `vitamin-b2` | Vitamin B2 (Riboflavin) | `evaluator` | 1 | `adult_single_site_interval_final` | ng/mL |
| `vitamin-e` | Vitamin E | `evaluator` | 1 | `adult_fragmented_multi_site_bundle_final` | mg/L |

## Locked Generation Rules

- Marker universe comes from the marker identity registry, not the filesystem bundle list.
- Numeric rows come from local import-ready SM bundles only after registry filtering.
- Wave-2A row schema is kept compatible with wave-1: raw `variant` and `population_scope` are not exposed.
- Age-like source variants are parsed into structured `age_min` / `age_max` when those fields are otherwise null; no-op `variant: all` is dropped.
- All wave-2A rows are `comparison_only`; no row is display eligible until human review promotes it.
- Promotion path: human review confirms marker identity and row semantics; crosscheck/promotion pass records readiness; only then can a row be regenerated as `display_eligible`.
- `crosscheck_status` is omitted from wave-2A files until the promotion pass exists; it remains a wave-1 frozen-summary concept for now.
- Rows with non-allowlisted status values are excluded from the agent-visible payload and counted in the internal report.
- Representation-equivalent unit spellings are normalized using the marker identity registry plus local typography variants; real unit differences remain row-level `unit` values.
- Agent-visible files omit provider names, provider URLs, local paths, raw extraction values, and source collection details.
- Public IDs are exposed only when PMID/PMCID/DOI can be extracted from a source URL.
