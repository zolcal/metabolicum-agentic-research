# Practitioner Gap Discovery — Design Spec

**Date:** 2026-05-30
**Status:** Approved design, pre-implementation
**Pilot:** hormones category

## 1. Problem

10% of MO-supported Hermes briefs (25/230) are **fully empty** — no videos, practitioners, papers, or sources — because the markers belong to categories with **0 practitioners** in the registry. The single biggest cause is the `hormones` cohort being empty (18 of the 25). A registry audit confirmed the gap is real: **no practitioner in `input/practitioner_registry.json` has marker-affinity to any hormone, kidney, electrolyte, bone, or other under-covered marker** — the registry is metabolic/lipid/glycemic-scoped. Re-mapping existing practitioners cannot fill these cohorts; the practitioners must be discovered and added.

The 17 categories with a 0-practitioner cohort: `hormones, kidney-function, electrolytes, bone-metabolism, blood-count, coagulation, autoimmune, allergy, drug-levels, environmental, gut-health, microbiology, salivary, specialty, tumor-markers, urine, anthropometric`.

## 2. Goal

Discover practitioners who **actually discuss** under-covered markers, gated by **retrievable evidence**, and auto-ingest them into the registry the briefs read — so empty/thin briefs gain real practitioner and website pointers. Pilot on `hormones`; expand to other 0-cohort categories afterward.

Non-goal: deriving MO ranges, building search-mode discovery for briefs, or migrating the legacy→canonical practitioner model. This project only fills practitioner coverage.

## 3. Scope

- **Pilot:** the mainstream hormone markers a practitioner community plausibly covers — testosterone family (`total-testosterone`, `free-testosterone`, `bio-t`, `dht`, `shbg`), adrenal (`cortisol-am`, `cortisol-pm`, `dhea`, `dhea-s`), reproductive (`estradiol`, `progesterone`, `lh`, `fsh`, `prolactin`, `amh`). Obscure assays (e.g. `11-deoxycorticosterone`) are included in the run but expected to yield no candidates — that is the intended "discovery reveals what's fillable" behavior.
- **Expansion (future waves):** kidney-function, electrolytes, then the remaining 0-cohort categories, one wave at a time, reusing the same pipeline.

## 4. Architecture

Five stages. Stage 1 reuses the existing `social_pipeline`; stages 2–5 are new.

```
pilot marker list
  → [1] Harvest (reuse social_pipeline)         → raw signals per marker
  → [2] Candidate extraction (new)              → unregistered entities + evidence
  → [3] Threshold gate (new)                    → qualifying (entity, marker) affinities
  → [4] Ingest / bridge (new)                   → updated practitioner_registry.json
  → [5] Audit + re-assemble                      → audit report + regenerated briefs
```

### Stage 1 — Harvest (reuse + local inventory)
For each pilot marker, gather raw signals from three sources, all using the marker's **phrase-based** alias tiers (no term-splitting — per the 2026-05-30 alias fix):
1. **Local 26k-video inventory scan** (`input/youtube-video-inventory/videos/*.json`) — phrase-match marker terms against the cached video metadata; **free, no API**, runs first. Cheap recall over channels already crawled.
2. **YouTube fresh search** (`social_pipeline` YouTube harvester) — reaches channels *not* in the local inventory (the hormone/HRT communities the metabolic-focused inventory lacks).
3. **Podcast** (`social_pipeline` podcast harvester).
Reddit/Twitter excluded as too noisy for the pilot. Output: raw signals (channels, authors, video IDs, titles, descriptions, transcripts) per marker, normalized to one shape across sources. The local-inventory scan is new glue; the YouTube/podcast harvesters are reused unchanged.

### Stage 2 — Candidate extraction (new)
Group harvested signals by channel / author / disambiguated speaker. **Drop any entity already present in `practitioner_registry.json`** (match by channel ID, handle, and name aliases). For each remaining unregistered entity, collect its marker-relevant evidence items — the specific videos/episodes where the marker's phrase-based terms appear in title/description/transcript. Output: candidate entities, each with a per-marker evidence list.

### Stage 3 — Threshold gate (new)
A candidate earns `marker_affinity[marker]` only if it has **≥ N evidence items** for that marker. **Default N = 2.** Candidates below threshold for every marker are held (written to a `held/` report, not ingested). Evidence (video IDs / URLs) is retained as provenance on the affinity. No affinity is ever assigned from an LLM assertion — only from retrievable sources.

### Stage 4 — Ingest / bridge (new)
For qualifying candidates, build/extend records in `input/practitioner_registry.json` (the file the briefs consume via `_practitioners_for` / `_practitioner_public_urls`):
- **identity:** `id` (`person:<slug>` or `channel:<slug>`), `canonical_name`, `aliases`, `entity_type`, `languages`.
- **surfaces:** discovered YouTube channel + any linked website/blog, each with `discovery_mode: auto_discovered`.
- **marker_affinity:** the qualifying markers, each carrying evidence provenance (video IDs/URLs, counts).
- **grading:** `source_tier`/`source_grade` conservative (MO / E2) to mark auto-discovered, downgradable entries.
Then run the existing `scripts/build_canonical_practitioner_sources.py` to sync the canonical split files (`input/practitioners/*`) from the updated legacy registry.

### Stage 5 — Audit + re-assemble
Emit an audit report: new practitioners, their markers, evidence counts, surfaces, held candidates. Re-run `scripts/assemble_hermes_briefs.py` for the affected waves so the new practitioners and their websites flow into the briefs. Report before/after coverage for the pilot markers.

## 5. Data contracts

**Candidate (stage 2 output):**
```json
{
  "entity_key": "channel:UCxxxx",
  "display_name": "...",
  "entity_type": "person|channel|company",
  "surfaces": [{"platform": "youtube", "handle_or_url": "...", "channel_id": "UCxxxx"}],
  "evidence": {
    "total-testosterone": [
      {"video_id": "abc123", "title": "...", "term": "total testosterone", "where": "title|description|transcript"}
    ]
  }
}
```

**Affinity provenance (on the registry record):**
```json
{"marker": "total-testosterone", "evidence_count": 4, "evidence": ["yt:abc123", "yt:def456"], "discovery_mode": "auto_discovered"}
```

## 6. Defaults (confirmed)

- Threshold **N = 2** evidence items per marker.
- Sources: **local 26k-video inventory scan + YouTube fresh search + podcast** (pilot). Inventory scan runs first (free); fresh search reaches new channels.
- Auto-ingest, with an audit report (no manual approval gate, per decision).
- Pilot shortlist: mainstream hormones (§3).

## 7. Quality & safety

- **No fabrication:** every assigned `marker_affinity` traces to retrievable evidence (video IDs/URLs). The threshold gate is the quality control.
- **Reversible:** auto-discovered records carry `discovery_mode: auto_discovered` + conservative grade, so a later audit can demote or remove them with a single filter.
- **Registry exclusion** prevents duplicating existing practitioners.
- **Held report** keeps below-threshold candidates visible for manual promotion without auto-ingesting them.

## 8. Units & interfaces

| Unit | Responsibility | Depends on |
|---|---|---|
| `harvest` | pull raw signals per marker from inventory scan + YouTube + podcast, normalized to one shape | local inventory (new scan), social_pipeline (reuse) |
| `extract_candidates` | group signals, exclude registry, attach evidence | registry, harvest output |
| `threshold_gate` | apply N, split qualifying/held | candidates |
| `ingest_canonical` | write registry records + provenance | registry, gate output |
| `regenerate_registry` | sync canonical split files | build_canonical_practitioner_sources.py (reuse) |
| `audit` | report + trigger brief re-assembly | assemble_hermes_briefs.py (reuse) |

## 9. Testing

- Unit: candidate extraction (group-by-channel, registry exclusion by id/handle/alias); threshold boundary (N−1 held vs N qualifies); ingest (schema-valid record, evidence provenance present, conservative grade); registry regeneration sync.
- End-to-end: run 2–3 mainstream hormone markers (`total-testosterone`, `cortisol-am`) on real harvested data; manually inspect candidates and evidence before the full hormones run.
- Regression: existing `check_hermes_briefs` acceptance still passes; existing metabolic briefs' practitioner lists unchanged.

## 10. Risks & mitigations

- **Noise from auto-ingest** → N-threshold + audit report + `auto_discovered` grade make every entry visible and reversible.
- **Cross-project run** (discovery lives in metabolicum-research, registry in agentic) → the bridge stages discovery output into the agentic project; the run script documents both paths.
- **Inventory bias** → the cached 26k inventory is metabolic-focused, so it is used as the cheap first-pass source but **paired with YouTube fresh search**, which reaches new hormone/HRT channels the inventory lacks. Neither source alone is relied on.
- **Speaker mis-attribution** (a guest discussing testosterone on a metabolic channel) → evidence is attributed to the channel; speaker disambiguation (reused) refines person-level attribution where transcripts allow.

## 11. Success criteria

- The hormones cohort gains ≥1 evidence-backed practitioner for the mainstream hormone markers.
- The previously-empty hormone briefs (e.g. `bio-t`) gain practitioner IDs + website source URLs after re-assembly.
- Zero affinities without retrievable evidence; audit report enumerates every new entry and its evidence.
- Pipeline reruns for the next category (kidney-function) with only a marker-list change.
