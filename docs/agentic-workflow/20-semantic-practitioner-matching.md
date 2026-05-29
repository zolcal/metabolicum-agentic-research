# Semantic practitioner matching

## Purpose

The practitioner index builder (`scripts/collect_practitioners.py`) must populate `input/research-assets/<wave>/practitioner-index.json`; `scripts/assemble_hermes_briefs.py` then projects those IDs into `recommended_practitioner_ids` for every marker. The primary matching mechanism is a thesaurus built from:

- `input/marker_glossary.json` aliases
- `input/registry/marker-identity-registry.v1.yaml` canonical aliases and equivalent-payload groups
- explicit slug mappings (e.g. `crp-standard` → `hs-crp`)
- full-text search across practitioner `marker_affinity`, `key_contribution`, `specialty_focus`, and `canonical_name`

The thesaurus captures explicit and near-explicit relationships. It fails when a practitioner discusses a marker conceptually without using any of its known aliases — for example, a longevity researcher who discusses growth-hormone optimization without ever writing "IGF-1" or "insulin-like growth factor" in their registry metadata.

Semantic embedding similarity closes this gap by matching practitioner metadata against marker topic descriptors at the conceptual level, not the lexical level.

## Architecture

```text
┌─────────────────────────────────────┐
│  Practitioner metadata (text)       │
│  canonical_name + key_contribution  │
│  + specialty_focus + marker_affinity│
└──────────────┬──────────────────────┘
               │
               ▼ e5 encode (batch)
┌─────────────────────────────────────┐
│  Practitioner embedding matrix      │
│  shape: (n_practitioners, 1024)     │
└──────────────┬──────────────────────┘
               │ dot product
               ▼
┌─────────────────────────────────────┐
│  Marker descriptor embedding matrix │
│  shape: (n_markers, 1024)           │
│  from input/topic_descriptors.yaml  │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Similarity matrix                  │
│  shape: (n_practitioners, n_markers)│
│  threshold >= 0.82                  │
└─────────────────────────────────────┘
```

### Model

- **Model:** `intfloat/multilingual-e5-large` (1024-dimension)
- **Library:** `sentence-transformers`
- **Device:** CPU (lazy-loaded singleton)
- **Query prefix:** `passage:` (asymmetric retrieval for practitioner texts and marker descriptors)

### Batch computation

All practitioners are embedded once per wave. All marker descriptors are embedded once per wave. The full similarity matrix is computed with a single `np.dot()` call. This keeps runtime under 60 seconds for 10 markers × 125 practitioners on a typical development workstation.

## Integration with brief generator

Semantic matching is a **fallback**, not a replacement for the thesaurus.

```python
# Primary: thesaurus (exact, alias, keyword)
practitioners = find_practitioners_thesaurus(marker, registry, thesaurus)

# Fallback: semantic (conceptual similarity)
if len(practitioners) == 0:
    practitioners = semantic_matches[marker][:10]
```

This preserves precision for well-covered markers (thesaurus finds 14–59 practitioners for `apob`, `hba1c`, `fasting-insulin`, `lpa`) while rescuing under-covered markers (`igf-1`, `fructosamine`) from zero-match failure.

## Configuration

| Parameter | Default | Description |
|---|---|---|
| `semantic_threshold` | 0.82 | Minimum cosine similarity to accept a practitioner–marker pair. Calibrated to produce ~10 matches for zero-thesaurus markers without flooding well-covered markers. |
| `semantic_top_k` | 10 | Maximum semantic matches added when thesaurus returns zero. |
| `use_semantic` | `True` | Toggle. When `False`, only thesaurus matching runs. |

## Technology stack

| Component | Role | Version |
|---|---|---|
| `intfloat/multilingual-e5-large` | Embedding model | HuggingFace snapshot |
| `sentence-transformers` | Model loading + encoding | >= 3.0 |
| `numpy` | Dot-product similarity | >= 1.24 |
| `input/topic_descriptors.yaml` | Marker descriptor source | Maintained per marker |

The model is the same one used by the Stage 2 tagger semantic fallback (`code/pipeline/semantic_fallback.py`), so the runtime environment needs only one embedding model loaded.

## Results (10-marker qualification set)

| Marker | Thesaurus | + Semantic fallback | Source of semantic matches |
|---|---|---|---|
| apob | 14 | 14 | — |
| hba1c | 41 | 41 | — |
| fasting-insulin | 50 | 50 | — |
| lpa | 59 | 59 | — |
| **igf-1** | **0** | **10** | Longevity, hormone-optimization, aging researchers |
| vitamin-d | 7 | 7 | — |
| crp-standard | 5 | 5 | — |
| hdl-cholesterol | 18 | 18 | — |
| uric-acid | 1 | 1 | — |
| **fructosamine** | **0** | **10** | Diabetes, glycemic-control researchers |

## Validation

The acceptance check (`code/acceptance/check_hermes_briefs.py`) verifies:

- `recommended_practitioner_ids` is a list of strings.
- No duplicate IDs within the list.
- Original SM YAMLs are untouched.

It does **not** verify semantic match correctness directly; that is covered by the deterministic generator script and normal git diff on the generated briefs.

## Non-goals

- Semantic matching is **not** used for YouTube video ranking. Video ranking uses title + description keyword matching.
- Semantic matching is **not** used for claim tagging. Claim tagging uses the existing `code/pipeline/semantic_fallback.py` path.
- Semantic matching does **not** modify the practitioner registry. If a practitioner is conceptually related but not in the registry, the match cannot occur.

## Future calibration

If the 0.82 threshold produces too many or too few matches for a new wave, adjust `semantic_threshold` in `scripts/collect_practitioners.py` and re-run the practitioner index, then rerun `scripts/assemble_hermes_briefs.py`. The batch design means re-running all markers in a wave is a single command.
