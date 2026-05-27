# HANDOVER-STAGE2-PATCHES-2026-05-25.md

## Purpose

Document the Stage 2 anti-hallucination / marker-recovery patch set applied before the next paid LLM run.

## Problem observed

Clean run `clean-real-fixtures-stage2-001` produced valid ApoB outputs but failed the other pilot markers. Root causes were mixed:

1. Extractor output normalization silently accepted malformed output as zero claims.
2. Extractor quotes for table/heading-driven thresholds were under-contextualized, e.g. `Above 3 is a significant red flag` without the `Triglyceride-to-HDL Ratio` heading.
3. `expected_markers` from fixtures were not passed to the extractor, so full-page noise could distract it.
4. Tagger had no JSON schema and leaked pseudo-markers such as `no_marker_match`, `unknown_marker`, and non-glossary marker names into `applies_to_markers`.
5. Some fixtures are conceptual-only and may not contain numeric thresholds.

## Files changed

- `code/pipeline/stages.py`
- `code/schemas/marker_tagger.schema.json`
- `prompts/01-content-extractor.md`
- `prompts/02-marker-tagger.md`

## Code changes

### A. Explicit extractor normalization helper

Added `_normalize_extractor_output(content)` in `code/pipeline/stages.py`.

Supported shapes:

- `[{claim...}]` -> `{ "claims": [...] }`
- `{ "claims": [...] }` -> unchanged normalized wrapper
- synonym arrays: `extracted_claims`, `raw_claims`, `numeric_claims`, `results`
- single top-level raw claim object containing `claim_id`, `verbatim_quote`, and `numeric_values`

Unknown shapes now raise `ValueError` instead of silently becoming `claims: []`.

### C. expected_markers passed to extractor

`run_extractor()` now includes:

```json
"expected_markers": fixture.get("expected_markers", [])
```

The prompt says these are search hints only, not evidence.

### D. Tagger schema + normalization

Added `code/schemas/marker_tagger.schema.json`.

`run_tagger()` now:

- loads the schema
- calls `llm_call(..., schema=schema)`
- injects/overrides `tagger_model`
- normalizes output through `_normalize_tagger_output(...)`
- allows only glossary marker slugs in `applies_to_markers`
- moves unknown/non-glossary marker names to `unknown_markers`
- uses `no_marker_match: true` for no-match cases instead of fake marker slugs

### B. Marker context in extractor prompt

`prompts/01-content-extractor.md` now requires marker-bearing context in `verbatim_quote`.

For table/heading-driven thresholds, the extractor must include the marker heading/label plus numeric lines. This is intended to preserve claims like:

`The Triglyceride-to-HDL Ratio ... Above 2 ... Above 3 ... Around 3.5 ...`

instead of losing marker context by emitting only:

`Above 3 is a significant red flag`

## Cheap tests already run

Command family:

```bash
/home/zoltan/miniconda3/envs/hermes/bin/python -m py_compile code/pipeline/stages.py
```

Unit-style checks passed for:

- `_normalize_extractor_output()` list wrapper
- normal `{claims: [...]}` wrapper
- synonym list wrapper
- single top-level claim object wrapper
- unknown shape raising `ValueError`
- `_normalize_tagger_output()` filtering `ldl_c` out of `applies_to_markers`
- `marker_tagger.schema.json` loading

## Deterministic fixture scans before next LLM run

### TG/HDL fixture

File: `fixtures/sources/fasting-insulin-benbikman-com-02.json`

Source: `https://benbikman.com/heart-disease-markers-that-matter/`

Findings:

- TG/HDL heading/context: YES
- TG/HDL numeric thresholds: YES
- fasting insulin mention: YES

Key source passage exists:

`The Triglyceride-to-HDL Ratio Triglycerides ÷ HDL cholesterol Using mg/dL units: Above 2 suggests metabolic dysfunction Above 3 is a significant red flag Around 3.5 or higher strongly suggests insulin resistance`

This is the best targeted next-run fixture.

### Lp(a) fixture

File: `fixtures/sources/lpa-peterattiamd-com-01.json`

Source: `https://peterattiamd.com/high-lpa-risk-factors/`

Findings:

- Lp(a) mention: YES
- numeric/cutoff-like terms: YES, but simple regex also catches unrelated percentile text from page noise.

Targeted run is still warranted, but article-body noise remains a risk. If it fails again, implement focused snippet extraction around `Lp(a)` / `nmol/L` before spending another full-page call.

### HbA1c fixture

File: `fixtures/sources/hba1c-benbikman-com-01.json`

Source: `https://benbikman.com/neuropathy-not-just-blood-sugar/`

Findings:

- A1c mention: YES
- HbA1c numeric threshold: NO

Do not expect numeric HbA1c recommendations from this fixture unless the schema expands to conceptual claims.

### fasting-insulin fixture

File: `fixtures/sources/fasting-insulin-benbikman-com-01.json`

Source: `https://benbikman.com/nad-nadh-insulin-resistance/`

Findings:

- fasting insulin mention: NO
- fasting insulin numeric threshold: NO
- HOMA numeric threshold: NO

This is not a good numeric fasting-insulin pilot fixture.

## Recommended next run

Do not run all five fixtures yet.

Run a targeted paid test on:

1. `fixtures/sources/fasting-insulin-benbikman-com-02.json`
   - expected recovery target: `tg-hdl-ratio`
2. `fixtures/sources/lpa-peterattiamd-com-01.json`
   - expected recovery target: `lpa`

Only after those succeed, replace weak HbA1c/fasting-insulin numeric fixtures or explicitly change the schema to support conceptual claims.
