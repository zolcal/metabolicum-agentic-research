# HANDOVER-SESSION-4.md — Stage 1 Discovery + Stage 2 Recovery

**Date:** 2026-05-25  
**Status:** Stage 1 implemented; table extraction stack installed; real fixtures created/validated; Stage 2 marker-context bug fixed; targeted TG/HDL + Lp(a) run succeeded.

---

## High-level outcome

The pipeline now has a working source-discovery path and a repaired Stage 2 extraction chain for marker-context-sensitive numeric claims.

Most important result:

- TG/HDL recovery succeeded in targeted run `targeted-tghdl-lpa-stage2-001`.
- The previous failure mode — extractor emitting `Above 3 is a significant red flag` without the `Triglyceride-to-HDL Ratio` heading — is fixed at prompt/schema/code level.
- Tagger now emits canonical marker `tg-hdl-ratio` under schema constraint.
- No fake markers leaked into `source_claim_marker`.

---

## Files created or materially changed

### New / changed handover and docs

- `HANDOVER-STAGE2-PATCHES-2026-05-25.md`
  - Documents the Stage 2 anti-hallucination / marker-recovery patch set.
- `HANDOVER-SESSION-4.md`
  - This file.

### Stage 1 discovery

- `code/discovery/__init__.py`
- `code/discovery/web.py`
- `code/discovery/tables.py`

### Stage 2 code/prompts/schemas

- `code/pipeline/stages.py`
- `prompts/01-content-extractor.md`
- `prompts/02-marker-tagger.md`
- `code/schemas/marker_tagger.schema.json`

### Config

- `config/llm-endpoints.yaml`
  - Stage 2 roles restored to known-working DashScope `qwen3.7-max`.

### Environment/docs from Kimi + follow-up verification

- `code/environment.yml`
- `docs/TABLE-EXTRACTION-TOOLS.md`

---

## Stage 1 source discovery implementation

Implemented public web discovery in:

- `code/discovery/web.py`

Features:

- Loads seeds from `input/practitioner_registry.json`.
- Uses public HTTP(S) website/substack-like surfaces only.
- Skips manual-only, non-HTTP, do-not-crawl, login/cart/account/privacy/terms/admin-like URLs.
- Fetches public pages with `requests`.
- Extracts article/body text using:
  - `trafilatura.extract(..., include_tables=True, include_comments=False)` when available.
  - deterministic stdlib parser fallback.
- Extracts links/title/meta dates.
- Appends explicitly labelled HTML table blocks via `code/discovery/tables.py`.
- Emits source fixtures validating against `code/schemas/source_fixture.schema.json`.
- Fixture fields include:
  - `synthetic: false`
  - `verification_status: verified_real_source`
  - real `transcript_sha256` from fetched text.

Discovery artifact layout:

- `runs/stage1-web-discovery/discovery/web.json`
- `runs/stage1-web-discovery/discovery/ranked_sources.json`
- `runs/stage1-web-discovery/discovery/state.json`

---

## Fixture naming fixed

Initial generated filenames were too long. Fixed writer to use:

`<primary-marker>-<platform-slug>-NN.json`

Current fixtures:

- `fixtures/sources/apob-peter-attia-source.json`
- `fixtures/sources/fasting-insulin-benbikman-com-01.json`
- `fixtures/sources/fasting-insulin-benbikman-com-02.json`
- `fixtures/sources/hba1c-benbikman-com-01.json`
- `fixtures/sources/lpa-peterattiamd-com-01.json`

All fixtures currently validate against schema and SHA-256.

---

## Real fixtures currently available

| Fixture | URL | Expected markers | Numeric suitability |
|---|---|---|---|
| `apob-peter-attia-source.json` | `https://peterattiamd.com/early-and-aggressive-lowering-of-apob/` | `apob` | Good; produced 4 ApoB recommendations |
| `fasting-insulin-benbikman-com-01.json` | `https://benbikman.com/nad-nadh-insulin-resistance/` | `fasting-insulin` | Poor for numeric fasting-insulin; deterministic scan found no fasting-insulin/HOMA threshold |
| `fasting-insulin-benbikman-com-02.json` | `https://benbikman.com/heart-disease-markers-that-matter/` | `fasting-insulin`, `tg-hdl-ratio` | Good for TG/HDL; produced 1 TG/HDL recommendation |
| `hba1c-benbikman-com-01.json` | `https://benbikman.com/neuropathy-not-just-blood-sugar/` | `hba1c`, `fasting-insulin` | Poor for numeric HbA1c; A1c mention exists but no HbA1c numeric threshold found |
| `lpa-peterattiamd-com-01.json` | `https://peterattiamd.com/high-lpa-risk-factors/` | `lpa` | Good; produced 3 Lp(a) recommendations, one questionable |

Important fixture caveat:

- If the contract remains numeric threshold/range recommendations only, replace the HbA1c and fasting-insulin fixtures before expecting output for those markers.
- If conceptual claims are desired, Stage 2 schema must expand beyond `direction`/`units`/threshold structure.

---

## Table extraction stack

Implemented in:

- `code/discovery/tables.py`

Installed/verified in Hermes env:

- `trafilatura 2.0.0`
- `pdf2image 1.17.0`
- `pdfplumber 0.11.9`
- `pymupdf 1.27.2.3`
- `camelot-py 1.0.9`
- `tabula-py 2.10.0`
- `pytesseract 0.3.13`
- `pillow 12.2.0`
- `opencv-python-headless 4.13.0`
- `pandas 3.0.3`
- `openpyxl 3.1.5`
- `jsonschema 4.26.0`

System tools verified:

- `tesseract`
- `pdftotext`
- `java`
- `gs`
- `convert`

Extraction priority:

HTML:

1. `pandas.read_html`
2. BeautifulSoup/lxml
3. stdlib HTMLParser fallback

PDF:

1. pdfplumber
2. PyMuPDF `page.find_tables()`
3. Camelot lattice/stream
4. Tabula lattice/stream
5. `pdftotext -layout`
6. `pdf2image + pytesseract` OCR fallback

Image:

1. OpenCV preprocessing + pytesseract
2. tesseract CLI fallback

Tables are appended to transcripts as labelled source-derived blocks. The extractor does not interpret or invent table content.

---

## DB reset performed

The Supabase CLI is **not installed** on this host, so `supabase db reset` was unavailable.

Local DB reset was done directly through psycopg2 using `SUPABASE_DB_URL`:

- dropped all public tables
- reapplied `supabase/migrations/0001_initial.sql`
- reloaded Phase 0 seed data via Python loaders

Reload commands used:

```bash
/home/zoltan/miniconda3/envs/hermes/bin/python -m code.loaders.practitioner_registry --local
/home/zoltan/miniconda3/envs/hermes/bin/python -m code.loaders.marker_glossary --local
/home/zoltan/miniconda3/envs/hermes/bin/python -m code.loaders.sm_anchors --local --waves wave-0 wave-1
/home/zoltan/miniconda3/envs/hermes/bin/python -m code.loaders.envelope_facts --local --waves wave-0 wave-1
```

Post-reset Phase 0 state:

```text
sources: 0
claims: 0
biomarker_claims: 0
sm_anchors: 618
practitioners: 44
marker_glossary: 35
research_target_envelopes: 618
quarantine: 0
research_studies: 0
```

---

## Stage 2 model config

`config/llm-endpoints.yaml` now routes Stage 2 to known-working DashScope model:

- extractor → `qwen3.7-max`
- tagger → `qwen3.7-max`
- structurer → `qwen3.7-max`

`dashscope-qwen3-max` / `qwen3.6-max-preview` is deactivated because it returned 403.

---

## Stage 2 anti-hallucination / recovery patches

Patched in:

- `code/pipeline/stages.py`
- `prompts/01-content-extractor.md`
- `prompts/02-marker-tagger.md`
- `code/schemas/marker_tagger.schema.json`

### A. Extractor normalization helper

Added:

```python
def _normalize_extractor_output(content: Any) -> dict[str, list[dict]]
```

Handles:

- list of claims
- `{ "claims": [...] }`
- synonym arrays: `extracted_claims`, `raw_claims`, `numeric_claims`, `results`
- single top-level raw claim object with `claim_id`, `verbatim_quote`, and `numeric_values`

Unknown shapes now raise `ValueError` instead of silently becoming zero claims.

### B. Marker context required in extractor prompt

`prompts/01-content-extractor.md` now requires marker-bearing context in `verbatim_quote`.

This fixed the TG/HDL issue:

Bad old quote:

`Above 3 is a significant red flag`

Good new quote:

`The Triglyceride-to-HDL Ratio Triglycerides ÷ HDL cholesterol Using mg/dL units: Above 2 suggests metabolic dysfunction Above 3 is a significant red flag Around 3.5 or higher strongly suggests insulin resistance`

### C. expected_markers passed into extractor

`run_extractor()` now passes:

```json
"expected_markers": fixture.get("expected_markers", [])
```

Prompt makes clear these are search hints only, not evidence.

### D. Tagger schema and normalization

Added:

- `code/schemas/marker_tagger.schema.json`

`run_tagger()` now:

- uses JSON schema constrained decoding
- injects actual `tagger_model`
- allows only glossary marker IDs in `applies_to_markers`
- moves non-glossary terms into `unknown_markers`
- uses boolean `no_marker_match`
- prevents fake markers like `no_marker_match`, `unknown_marker`, `ldl_c`, `hdl_c` from leaking into marker links

### Structurer model identity fix

`run_structurer()` now overwrites each output recommendation’s `extraction_model` with the actual model argument.

---

## Cheap tests run before paid targeted test

Command family:

```bash
/home/zoltan/miniconda3/envs/hermes/bin/python -m py_compile code/pipeline/stages.py
```

Unit-style checks passed for:

- `_normalize_extractor_output()` list wrapper
- normal `{claims: [...]}` wrapper
- synonym-key wrapper
- single top-level claim object wrapper
- unknown shape raising `ValueError`
- `_normalize_tagger_output()` filtering `ldl_c` out of `applies_to_markers`
- `marker_tagger.schema.json` loading

---

## Clean full pilot run before final patches

Run:

- `clean-real-fixtures-stage2-001`

Summary:

- sources: 5
- extracted claims: 16
- recommendations: 4
- errors: 0
- cost: `$0.3966`

Only ApoB produced DB-linked final recommendations:

- `apob`: 4

This was not acceptable and led to the Stage 2 patch set above.

---

## Targeted paid run after patches

Run:

- `targeted-tghdl-lpa-stage2-001`

Command:

```bash
/home/zoltan/miniconda3/envs/hermes/bin/python -m code.pipeline.ingest --run-id targeted-tghdl-lpa-stage2-001 fixtures/sources/fasting-insulin-benbikman-com-02.json fixtures/sources/lpa-peterattiamd-com-01.json
```

Summary:

```text
Sources processed: 2
Total claims extracted: 8
Total recommendations: 4
Total errors: 0
Total time: 560.5s
Estimated cost: $0.2259
```

### TG/HDL result — success

Source:

- `https://benbikman.com/heart-disease-markers-that-matter/`

Output:

- extracted claims: 4
- structured recommendations: 1
- marker: `tg-hdl-ratio`
- DB marker link: yes
- model: `qwen3.7-max`

Recovered quote:

```text
The Triglyceride-to-HDL Ratio Triglycerides ÷ HDL cholesterol Using mg/dL units: Above 2 suggests metabolic dysfunction Above 3 is a significant red flag Around 3.5 or higher strongly suggests insulin resistance
```

Structured recommendation:

```text
applies_to_markers: ["tg-hdl-ratio"]
target_value: 2
units: ratio
direction: below
paradigm: MO
extraction_model: qwen3.7-max
```

Nuance:

- The quote contains the full threshold ladder (>2, >3, ~3.5).
- Structurer emitted one recommendation for the first threshold (`below 2`).
- Later improvement: emit multiple recommendations from one threshold ladder if needed.

### Lp(a) result — mostly success, one questionable claim

Source:

- `https://peterattiamd.com/high-lpa-risk-factors/`

Output:

- extracted claims: 4
- structured recommendations: 3
- marker: `lpa`
- DB marker links: 3
- model: `qwen3.7-max`

Good Lp(a) outputs:

1. High Lp(a) cutoff

```text
Participants were classified as having “high Lp(a)” if their Lp(a) levels exceeded the 90th percentile ... corresponding to >168 nmol/L and <19 nmol/L for high and low cutoffs, respectively.
```

Structured:

```text
marker: lpa
target_value: 168
units: nmol/L
direction: above
```

2. PCSK9 reduction

```text
Some physicians use PCSK9 inhibitors off-label to lower Lp(a) by ~25% ...
```

Structured:

```text
marker: lpa
target_value: 25
units: %
direction: below
```

Questionable output:

- A claim about `non-Lp(a) dyslipidemia` was tagged/structured as `lpa`.
- This needs a negation/exclusion rule before full production runs.

Recommended rule:

- `non-Lp(a)` should not tag as `lpa` unless the claim is explicitly about Lp(a) itself.

---

## Current DB marker links after targeted run

```text
apob: 4
lpa: 3
tg-hdl-ratio: 1
```

Invalid marker links:

```text
none
```

---

## Current known issues / next work

### 1. Add tagger negation/exclusion rule

Patch `prompts/02-marker-tagger.md`:

- If phrase is `non-Lp(a)` / `non-[marker]`, do not tag the marker unless the numeric claim is explicitly about that marker.
- Put excluded term into `unknown_markers` or no-match context, not `applies_to_markers`.

Then rerun only Lp(a) source or inspect with council.

### 2. Multi-threshold ladder splitting

TG/HDL quote contains three thresholds:

- above 2
- above 3
- around 3.5+

Structurer emitted one recommendation (`below 2`). This is acceptable proof of pipeline recovery but may be incomplete for final data.

Possible improvement:

- Structurer should emit one recommendation per distinct threshold when a quote contains a threshold ladder.

### 3. HbA1c and fasting-insulin fixtures are weak for numeric-threshold contract

Deterministic scans found:

- `hba1c-benbikman-com-01.json`: A1c mention yes, HbA1c numeric threshold no.
- `fasting-insulin-benbikman-com-01.json`: fasting insulin mention no, numeric threshold no, HOMA threshold no.

Need replacement fixtures if numeric recommendations are required.

### 4. Conceptual claims need schema expansion if desired

Current Stage 2 schema is numeric threshold/range oriented. If conceptual practitioner claims should be captured, add claim types and allow null direction/units/targets.

---

## Commands likely needed next

Validate fixtures:

```bash
/home/zoltan/miniconda3/envs/hermes/bin/python - <<'PY'
import json, hashlib
from pathlib import Path
from jsonschema import Draft202012Validator
schema=json.loads(Path('code/schemas/source_fixture.schema.json').read_text())
validator=Draft202012Validator(schema)
for p in sorted(Path('fixtures/sources').glob('*.json')):
    d=json.loads(p.read_text())
    errors=sorted(validator.iter_errors(d), key=lambda e: list(e.path))
    digest=hashlib.sha256(d.get('transcript_text','').encode()).hexdigest()
    print(p.name, 'OK' if not errors and digest == d.get('transcript_sha256') else 'FAIL')
PY
```

Check DB marker links:

```bash
/home/zoltan/miniconda3/envs/hermes/bin/python - <<'PY'
from code.db import local_psycopg
db=local_psycopg()
print(db.health_check())
print(db._execute('select marker, count(*) from source_claim_marker group by marker order by marker'))
print(db._execute("""select scm.marker, count(*) from source_claim_marker scm left join marker_glossary mg on mg.marker=scm.marker where mg.marker is null group by scm.marker"""))
PY
```

Run targeted source again after tagger negation patch:

```bash
/home/zoltan/miniconda3/envs/hermes/bin/python -m code.pipeline.ingest --run-id targeted-lpa-negation-fix-001 fixtures/sources/lpa-peterattiamd-com-01.json
```

---

## Bottom line

The high-impact bug is fixed: TG/HDL marker-context extraction now works. The Stage 2 pipeline contract is much stronger:

- expected markers are passed as hints
- extractor preserves marker context
- tagger is schema-constrained
- fake markers are blocked
- model identity is forced by code
- invalid marker links are absent

Remaining work is refinement, not basic pipeline failure:

- Lp(a) negation rule for `non-Lp(a)`
- multi-threshold ladder splitting
- better numeric fixtures for HbA1c and fasting-insulin
