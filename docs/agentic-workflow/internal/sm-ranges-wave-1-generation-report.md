# SM Agent-Visible Input Generation Report — 108 Wave-1 Markers

**Date:** 2026-05-18
**Source:** `sm-next/outputs/clean-ranges/` frozen exports
**Generator:** `scripts/generate_sm_agent_input.py` (also serves as audit script: `--audit` flag)
**Output:** `docs/agentic-workflow/input/sm-ranges/wave-1/`
**Status:** v2.2 — canonical agent-visible SM input contract for wave-1 (108 markers)

**Internal-only document.** This report exposes the generator path, source path,
field mappings, and hidden-field names. It must NOT ship inside the agent-visible
`wave-1/` payload. Its home is `docs/agentic-workflow/internal/`.

---

## What was generated

108 agent-visible SM anchor YAML files were generated from the frozen clean-ranges inventory (`build_sm_freeze_inventory.py` reports 108 frozen markers). Each file follows the canonical shape defined in `REVIEW-2026-05-17-frozen-anchored.md`.

### Mapping rules applied (v2)

| Frozen field | Agent-visible field | Rule |
|-------------|---------------------|------|
| `slug` | `marker_slug` | direct |
| `name` | `marker_name` | direct (preserves frozen casing) |
| `unit` | `unit` | direct |
| `db_rows[]` | `rows[]` | transformed per row |
| `db_rows[].stratum` | `rows[].stratum` | direct; disambiguated with a `display_role` label (`primary` / `supporting` / `international_variant`) or `variant` if duplicate; falls back to `_orderN` last. **Never uses `source_family`** (would leak derivation) |
| `db_rows[].gender` | `rows[].sex` | `null` → `all`; otherwise direct |
| `db_rows[].age_min/max` | `rows[].age_min/max` | direct |
| `db_rows[].min/max` | `rows[].min/max` | direct |
| `db_rows[].status` | `rows[].status` | direct |
| `db_rows[].primary_display` + `crosscheck_status` | `rows[].use` | `display_eligible` when `primary_display == true` AND row's `crosscheck_status IN {passed, not_applicable, not_available}`. `comparison_only` when `primary_display == true` AND `crosscheck_status NOT IN` that set (typically `not_performed` or `not_covered`). Else `internal_research_gate`. The freeze's flag alone does not mean display-ready; crosscheck must clear the row. |
| `db_rows[].source_id` + `source_url` | `rows[].public_source_ids` | PMCID extracted from `source_id` (e.g. `scirep:PMC8115101:bun`) AND `source_url`; PMID/DOI from `source_url` |
| `export_reason` | `reviewer_note` | **NOT used** — replaced with neutral boilerplate to prevent derivation leakage |
| `hidden fields` | — | **omitted**: `source_url`, `source_family`, `license`, `raw_artifact_ref`, `raw_sha256`, `retrieved_at`, `review_status`, `method_note`, `derivation_note`, `evidence_grade`, `validation_grade`, `validation_tier`, `variant`, `source_id`, `sources`, `label`, `color` |

### Top-level `crosscheck_status`

Included as a **uniformity summary** when **all rows share the same `crosscheck_status`**. If rows are mixed, the field is omitted and the consumer should inspect per-row values.

| Value | # markers |
|-------|-----------|
| `not_performed` | 61 |
| `not_applicable` | 24 |
| `passed` | 16 |
| `not_covered` | 2 |
| `not_available` | 1 |
| absent (mixed/null) | 4 |

### `use` enum distribution (v2.2 — crosscheck-aware)

| `use` value | row count | meaning |
|---|---:|---|
| `internal_research_gate` | 454 | not flagged as primary; council comparison only |
| `comparison_only` | 23 | freeze flagged as primary BUT crosscheck pending (`not_performed`); council may compare, must not display |
| `display_eligible` | 136 | freeze flagged as primary AND crosscheck cleared (`passed`, `not_applicable`, or `not_available`); may be surfaced |

**Display-eligible row distribution per marker:**

| # display_eligible rows | # markers |
|------------------------|-----------|
| 0 | 77 |
| 1 | 12 |
| 2 | 8 |
| 3 | 2 |
| 4 | 2 |
| 6 | 1 |
| 8 | 3 |
| 12 | 1 |
| 26 | 2 |

The rule pairs the freeze's `primary_display` flag with the row's `crosscheck_status`. The freeze's flag alone marks a row as preferred; crosscheck additionally vouches for it. Rows with crosscheck `not_performed` (the v2.1 over-promotion bug that Codex flagged) now correctly resolve to `comparison_only`, not `display_eligible`.

---

## Audit results

### Automated audit (`scripts/generate_sm_agent_input.py --audit`)

The audit is built into the generator. Each run validates its own output for:

- hidden-derivation leakage strings (e.g., `nhanes`, `source_family`, `raw_sha256`, `sm-clean-frozen`, internal paths)
- forbidden keys in row data (`source_url`, `license`, `validation_grade`, `display_role`, etc.)
- duplicate stratum names within a single marker
- invalid `use` or `sex` enum values
- byte-identical row payloads across markers (duplicate-canonicalization signal)

Most recent run on the wave-1 set:

- **108 files scanned**
- **0 issues**
- **4 marker pairs with byte-identical row payloads** (see Known issues §1)

### Rule refinements landed (v2.1, 2026-05-17)

Two corrections applied to the generator during convergence to a single canonical set:

1. **`primary_population_reference_interval` promotion.** An earlier rule string-matched only `primary_reference_interval`, missing the more common variant `primary_population_reference_interval` that the freeze uses for 156 rows across 41 markers. Rule simplified to "trust `primary_display: true`" (no `display_role` string-matching required). Display_eligible rows went from 3 → 159; markers went from 2 → 43.
2. **ALT/AST stratum disambiguation.** An earlier suffix used `source_family` (e.g., `male_nhanes_population_distribution`), which leaked the source. Replaced with a neutral `display_role`-derived label (`male_supporting`, `female_supporting`). Verified: zero `nhanes` / `source_family` strings in any of 108 files.

### Edge-cases documented to prevent regression

| Edge-case | Wrong behavior to avoid | Correct behavior in v2.2 |
|---|---|---|
| Frozen `gender: null` (8 markers including calcium, chloride, ck-mb, ldh, phosphorus, potassium, sodium, total-protein) | preserve `sex: null` — violates `sex: male \| female \| all` enum | map to `sex: all` |
| ALT/AST collision: two rows per sex from different `display_role` values | duplicate `stratum: male`/`female` | disambiguate with `display_role`-derived suffix (`_supporting`, `_international_variant`) — never with `source_family` |
| PMCID extraction | extract only from `source_url` (misses 25 IDs that live in `source_id`) | extract from `source_id` first, then `source_url` |
| `reviewer_note` | copy frozen `export_reason` (leaks source family + method) | use neutral boilerplate |
| `display_role` string-matching | accept only `primary_reference_interval` (misses 156 rows) | trust `primary_display: true` flag, no role string-matching |
| `display_eligible` semantics | promote any `primary_display: true` row regardless of crosscheck — implies display readiness without crosscheck completion (Codex finding 2026-05-18) | require `primary_display: true` AND `crosscheck_status ∈ {passed, not_applicable, not_available}`; uncleared primary rows become `comparison_only` |
| Report placement | ship generation report alongside agent-visible YAMLs (leaks source path, generator path, hidden-field names, derivation mechanics) | keep this report in `docs/agentic-workflow/internal/`; `wave-1/` directory contains only the 108 YAMLs |
| Audit script | reference a separate `audit_agent_input.py` that doesn't exist | fold audit into generator: `scripts/generate_sm_agent_input.py --audit` runs all checks on the output dir |

### Public ID extraction

- At least one `public_source_ids` block on **149 rows** across multiple markers
- **149 non-empty `pmcids` references** total (up from 124 in v1, now extracting from `source_id` as well as `source_url`)
- **0 non-empty `pmids` blocks**
- **0 non-empty `dois` blocks**

---

## Known issues and open questions

### 1. Duplicate slug pairs in the frozen ledger (4 pairs)

The audit found four marker pairs with byte-identical row payloads — the same data exposed under two slugs:

| Pair | Row count each |
|---|---:|
| `cholesterol-in-ldl` / `ldl-cholesterol` | identical |
| `crp-standard` / `hscrp` | identical |
| `igf-1` / `insulin-like-growth-factor-i` | 26 rows each |
| `testosterone` / `total-testosterone` | identical |

This is a frozen-ledger issue, not a generator bug. **Recommendation:** Pick a canonical slug for each pair and either archive or alias the other before Supabase ingestion. Without canonical handling, downstream queries will double-count claims and the council's deduplication logic will see two anchor packages for the same biological quantity.

### 2. `marker_name` casing inconsistencies

Frozen `name` fields have inconsistent casing (e.g., `Hba1C` instead of `HbA1c`). Both generators preserve frozen casing. **Recommendation:** Normalize names via a canonical marker glossary table in the new project schema.

### 3. `reviewer_note` is generic boilerplate

All 108 files use the same neutral boilerplate to prevent derivation leakage. The hand-written pilot samples have richer doctrinal framing (e.g., RI width explanation, MO divergence framing). **Recommendation:** Human review of `display_eligible` markers to enrich notes before production use, but only with neutral language that does not reveal source families or derivation methods.

### 4. `annotations` empty for all 108

The frozen exports do not contain guideline cutoff annotations separate from reference-interval rows. The pilot samples have hand-curated annotations (e.g., ADA thresholds for HbA1c, NLA/ESC thresholds for ApoB). **Recommendation:** Annotations remain a human curation step; they cannot be generated from frozen data alone.

### 5. `known_research_context` placeholders

All 108 files have empty `pmids[]`, `pmcids[]`, `dois[]`. The review says these should be "populated from RC research effort." **Recommendation:** Backfill after RC PMID inventory is available.

### 6. Calculated surfaces and excluded markers not in 108

The pilot set includes:
- `tg-hdl-ratio` — **calculated_surface**, not in frozen wave-1
- `lpa` — **not_in_frozen_wave_1**, not in frozen wave-1

These require hand-crafted YAMLs (the existing `.sample.yaml` files in the parent directory are the canonical shapes). They are **not** in `wave-1/`.

### 7. Locked rule decisions

1. **`display_eligible` promotion rule (refined 2026-05-18):** `primary_display=true` AND `crosscheck_status ∈ {passed, not_applicable, not_available}`. Uncleared primary rows resolve to `comparison_only`.
2. **Top-level `crosscheck_status` rule:** uniformity summary — emitted only when all rows share the same value.
3. **Where canonical mapping rules live:** `scripts/generate_sm_agent_input.py` is the executable spec; `REVIEW-2026-05-17-frozen-anchored.md` is the human-readable contract. Both must stay in sync.
4. **Frozen-ledger duplicate handling:** pending freeze-side resolution for the 4 duplicate pairs (see §1).
5. **Stratum disambiguation source-of-truth:** v2.1+ maps frozen `display_role` to neutral labels (`primary` / `supporting` / `international_variant`). New `display_role` values in later freezes require updating the `DISPLAY_ROLE_LABEL` dict in the generator.
6. **Report-payload separation:** this report and any audit artifacts live under `docs/agentic-workflow/internal/`. The `wave-1/` directory contains only agent-visible YAMLs; nothing in that folder may name internal paths, scripts, generator field-mappings, source families, or other derivation hints.

---

## Files in the canonical set

Agent-visible payload (clean — no derivation, no internal references):
- `docs/agentic-workflow/input/sm-ranges/wave-1/*.yaml` — 108 agent-visible SM anchor files

Internal/audit artifacts (must not ship with the agent payload):
- `docs/agentic-workflow/internal/sm-ranges-wave-1-generation-report.md` — this report
- `scripts/generate_sm_agent_input.py` — generator + audit script (`--audit` flag)

---

## Next steps (per user plan)

1. ✅ **Finalize agent-visible SM input contract** — done; locked in review document + generator + 108 outputs
2. ✅ **Generate 108 files** — done
3. ✅ **Review for shape, leakage, public-ID usefulness** — done; 0 leakage, 149 pmcids, 159 display_eligible rows across 43 markers, 0 duplicate strata, sex enum compliant
4. ⏳ **Create new `metabolicum-agentic-research` project/git/Supabase** — pending user decision
5. ⏳ **Migrate spec + generator + 108 outputs to new repo with clean git history**
6. ⏳ **Human review of display-eligible markers and annotation curation**
7. ⏳ **Backfill `known_research_context` from RC PMID inventory**
8. ⏳ **Resolve IGF-1 slug duplication in frozen ledger**
