# Taxonomy findings for metasync — 2026-05-30

**From:** metabolicum-agentic-research (MO pipeline; consumer of the metasync production DB)
**To:** metasync (owner of the production biomarker DB — the arbiter)
**Status:** PROPOSAL for review. Nothing has been applied to production. The agentic
project never writes production; it proposes via this channel.

## Why this exists
While building the MO research pipeline we treat the metasync DB as the single source
of truth for marker identity, slugs, and categories (mirrored read-only into our
ground-truth document). Two research passes (one auditing our 25 categories against
authoritative taxonomies; one grounding marker↔category multi-memberships) surfaced
**additive** taxonomy refinements. The taxonomy is fundamentally sound — these are
enrichments, not corrections.

## Validation result (reassuring)
Our 25 categories were compared against **LOINC class system, Quest/LabCorp test menus,
Tietz clinical chemistry, and functional/longevity panels** (cheap-model survey + an
adversarial critic that required a citation per claim). Outcome: **one genuine missing
top-level category** (Neurological & Cognitive). Everything else the survey raised maps
cleanly into existing categories (see Awareness notes). Slug arbitration is clean: a
single redirect `total-bilirubin → bilirubin-total` already in `marker_slug_aliases`.

## Change 1 — Multi-category memberships (44 across 35 markers)
`marker_categories` is many-to-many but **under-populated** (1112 rows / 1110 markers ≈
one each). Many markers are standard members of more than one category. Each membership
below is backed by a guideline / landmark trial / authoritative review and was validated
to resolve to a canonical slug in a real category. **Additive only — primary categories
are untouched.** Full SQL: `2026-05-30-marker-categories.sql`.

Representative, high-confidence:
- **`tg-hdl-ratio`** → +cardiovascular, +glycemic-insulin — insulin-resistance surrogate *and* ASCVD-risk marker (McLaughlin 2003; NHANES PMID 41824825; Framingham).
- **`apob`** → +cardiovascular (+liver-function) — primary ASCVD risk metric (ESC/EAS, ACC/AHA; Copenhagen JAMA Cardiol 2026).
- **`lpa`, `non-hdl-c`, `hdl-cholesterol`** → +cardiovascular (guideline-endorsed ASCVD markers).
- **`hscrp`** → +cardiovascular (JUPITER; ACC/AHA risk enhancers).
- **`uric-acid`** → +cardiovascular, +glycemic-insulin (URRAH PMID 36837863; URAT1/insulin PMID 41521685).
- **`homa-ir`, `tyg-index`, `fli`, `nafld-fibrosis-score`** → metabolic/CV cross-links.
- **Kidney cluster (KDIGO 2024 CKD-MBD, PMID 39299913):** `renin`, `aldosterone`, `pth`, `phosphorus`, `potassium`, `homocysteine`, `calcitriol` → +kidney-function.
- **Iron/micronutrient:** `ferritin`, `serum-iron`, `transferrin`, `transferrin-saturation`, `stfr`, `selenium`, `rbc-folate` → +micronutrients.
- **Endocrine:** `leptin`, `adiponectin`, `c-peptide-fasting/-stimulated`, `calcitriol` → +hormones.
- **Vascular inflammation:** `lp-pla2`, `oxidized-ldl` → +inflammatory; `platelet-count` → +liver-function (FIB-4/APRI).

⚠️ **Flagged for your pruning (weaker / critic was inconsistent):** `adiponectin→thyroid`,
`homa-ir→thyroid`, `ferritin→thyroid`, `triglycerides→liver-function`. Recommend dropping
these unless you see a clear basis — they're in the SQL but called out here.

## Change 2 — New category: `neurological-cognitive`
The one genuine gap. Blood-based neuro markers (NfL, NSE, S100B, p-tau217, GFAP) are now
routine on Quest/LabCorp. We have **4 such markers already in the DB, mis-shelved:**

| marker | current primary | issue |
|---|---|---|
| `neurofilament-light-chain` (NfL) | `specialty` | should be neuro |
| `enolase-neuron-specific` (NSE) | `tumor-markers` | legit dual (NSE *is* a tumor marker) — add neuro |
| `enolase-neuron-specific-csf` | `tumor-markers` | add neuro |
| `s100-calcium-binding-protein-b` (S100B) | **`electrolytes`** | clearly wrong — brain-injury marker |

The migration **creates the category and adds neuro membership** to these 4. It does **not**
reassign their `is_primary` — that's your call (we'd recommend neuro as primary for NfL and
S100B; keep tumor-markers primary for NSE). `s100b` in `electrolytes` looks like a plain
mis-tag worth fixing regardless.

## Awareness notes (no action requested)
The category survey raised these; all map into existing categories, listed only so you
have the rationale on record:
- Genetics / molecular pathology (LOINC MOLPATH) → `specialty` (genotypic; doesn't fit a range model).
- Infectious-disease serology → `microbiology`. Acute cardiac markers (troponin/BNP) → `cardiovascular`. Blood gases → `electrolytes`.
- Rejected as non-standard (functional-medicine-only, no LOINC/lab basis): "Advanced Aging/Longevity", "Sleep/Circadian".
- Out of scope for a biomarker-research DB: body-fluid analysis (CSF/synovial), blood-bank/transfusion.

## Apply + verify
1. Review/prune (esp. the flagged `→thyroid` items + the neuro `is_primary` decisions).
2. Apply `2026-05-30-marker-categories.sql` to production (additive, idempotent, has rollback).
3. We re-run `scripts/build_ground_truth.py` (re-sync the mirror) and
   `code/acceptance/check_ground_truth_harmony.py` confirms doc⟺DB harmony.
4. Our derivations become multi-category-aware (in-scope if *any* category is in-scope;
   practitioner cohort = union over all a marker's categories), so `cardiovascular` then
   carries ApoB/Lp(a)/TG-HDL and their practitioners automatically.
