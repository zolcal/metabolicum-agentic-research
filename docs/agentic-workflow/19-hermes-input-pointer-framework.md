# Hermes input pointer framework

## What this document records

This document defines the Hermes trigger input contract. Hermes does not read the raw SM range YAMLs directly. Hermes reads generated **research briefs** that contain stripped SM anchor data plus compact pointer fields. The brief is the single trigger file per marker.

## Final decision

`input/sm-ranges/` files are **read-only anchors**. They are never modified by the pipeline. The Hermes trigger is a separate generated file:

```text
input/hermes-briefs/<wave>/<marker>.yaml
```

The brief is produced by `scripts/prepare_hermes_briefs.py`. It contains:

1. **Stripped SM anchor data** — marker slug, name, units, reference rows, `known_research_context` public IDs, and `anchor_provenance`. Bloat fields (`sample_status`, `source_policy`, `anchor_version`, `reviewer_note`, display flags) are removed.
2. **Six pointer fields** — compact lists that tell Hermes where to start research:

```yaml
schema_version: hermes-brief-1
recommended_youtube_video_ids:
- mDeqg6i9CxQ
recommended_practitioner_ids:
- person:peter-attia
recommended_pubmed_ids:
- "23584084"
recommended_dois:
- 10.1001/example
recommended_source_urls:
- https://pmc.ncbi.nlm.nih.gov/articles/PMC10498001/
recommended_search_queries:
- apolipoprotein B practitioner optimal range
```

Empty lists are valid when no reliable pointer is available for that class. The fields are populated incrementally as evidence is available.

## Why the brief is the right trigger

The brief separates two concerns:

- **SM YAMLs** (`input/sm-ranges/`) remain canonical, untouched reference anchors. They provide sanity-check ranges, units, and public research IDs. They are not proof sources for MO claims.
- **Briefs** (`input/hermes-briefs/`) are disposable, regenerable trigger files. They combine SM anchor context with dynamic pointers (practitioners, videos, papers) that change as the registry and inventory grow.

If a brief's pointers are stale or noisy, delete it and rerun `prepare_hermes_briefs.py`. The SM YAMLs are unaffected.

## Brief generation pipeline

```text
input/sm-ranges/<wave>/<marker>.yaml
    ↓
scripts/prepare_hermes_briefs.py
    ↓
input/hermes-briefs/<wave>/<marker>.yaml
```

The generator is deterministic: same inputs produce the same output. It does not call LLMs or fetch URLs.

### Inputs consumed by the generator

| Input | Purpose |
|-------|---------|
| `input/sm-ranges/<wave>/<marker>.yaml` | Anchor data (rows, units, known research IDs) |
| `input/practitioner_registry.json` | Practitioner directory with surfaces, COI, marker affinity |
| `input/marker_glossary.json` | Marker aliases for matching |
| `input/registry/marker-identity-registry.v1.yaml` | Canonical aliases and equivalent payload groups for thesaurus building |
| `input/topic_descriptors.yaml` | Marker descriptors for e5 semantic fallback |
| `input/youtube-video-inventory/videos/*.json` | Video metadata for title/description matching (optional) |

### Thesaurus + semantic practitioner matching

Practitioners are matched to markers in two stages:

1. **Thesaurus matching** (primary) — exact/alias/partial matching using:
   - `marker_glossary.json` aliases
   - `marker-identity-registry.v1.yaml` canonical aliases
   - Equivalent payload groups (e.g. `igf-1` ↔ `insulin-like-growth-factor-i`)
   - Explicit slug mappings (e.g. `crp-standard` → `hs-crp`)
   - Practitioner `key_contribution` and `specialty_focus` text search

2. **Semantic fallback** (activates only when thesaurus returns zero matches) — `intfloat/multilingual-e5-large` embeddings comparing marker topic descriptors against practitioner metadata. Threshold: 0.82 cosine similarity, top-k: 10.

### YouTube video matching

Videos are matched by searching marker glossary terms against `title + full raw description`. No transcripts are fetched during brief generation. Hermes fetches transcripts inline later, only for the selected video IDs.

## YouTube inventory status

The video metadata inventory lives at:

```text
input/youtube-video-inventory/videos/*.json
```

Each JSON file contains: `video_id`, `url`, `title`, `description`, `channel`, `channel_id`, `published_at`, `duration_seconds`, `fetched_at`, and `discovered_via` (practitioner linkage).

### Current inventory (as of 2026-05-28)

- **26,621 video metadata files** fetched across **32 resolved channels** via the YouTube Data API
- **Total fetched**: 27,638 videos (some writes may have been deduplicated or failed, leaving 26,621 JSON files)
- **Quota used**: 1,161 units
- **Channels not found**: 10 channel IDs from the registry returned "channel not found" errors
- **Match rate to qualification markers** (10 markers, by title/description keyword against full inventory):
  - `vitamin-d`: 1,123 videos
  - `hba1c`: 210 videos
  - `uric-acid`: 149 videos
  - `crp-standard`: 62 videos
  - `apob`: 55 videos
  - `fasting-insulin`: 56 videos
  - `igf-1`: 46 videos
  - `hdl-cholesterol`: 24 videos
  - `lpa`: 15 videos
  - `fructosamine`: 1 video

### Assessment

The channel-upload scraping produced a large inventory with strong coverage for frequently-discussed markers (`vitamin-d`, `hba1c`, `uric-acid`) and moderate coverage for most others. Only `fructosamine` (1 match) and `lpa` (15 matches) are thin. The inventory is viable for the qualification batch.

### Video ranking and capping

The brief generator does not return all matched videos. It applies a **composite scoring post-processing step** after matching to rank videos by relevance and cap the output.

**Scoring dimensions:**

| Dimension | Signal | Weight |
|-----------|--------|--------|
| Match base | slug in title | +10 |
| | slug in description | +5 |
| | alias in title | +7 |
| | alias in description | +3 |
| Title bonus | marker appears in title | +5 |
| Depth | duration 15–120 min | +3 |
| | duration >120 min | +1 |
| | duration 3–15 min | 0 |
| | duration <3 min (shorts) | –5 |
| Authority | practitioner source_tier A | +5 |
| | practitioner source_tier B | +3 |
| | practitioner source_tier C | +1 |
| Recency | <2 years old | +2 |
| | 2–5 years old | 0 |
| | 5–7 years old | –2 |
| | >7 years old | –4 |
| Citation | description contains PMID or DOI | +8 |
| Frequency | term occurs 2–5× | +1 |
| | term occurs 6–15× | +2 |
| | term occurs >15× | +3 |

Citation is among the strongest signals, on par with a title match: a PMID or DOI in the description strongly indicates the video points to resolvable primary literature, which is exactly what the MO provenance chain needs.

**Channel diversity:** after sorting by score, a post-filter ensures no single channel exceeds 30% of the cap. For cap=30, no channel contributes more than 9 videos.

**Default cap:** 30 videos per brief. Configurable via `--video-cap`.

### Diagnostics sidecar (not part of the brief)

The composite scores, per-video match terms, and ranking rationale are generator diagnostics, not Hermes input. They are written to a sidecar next to the brief:

```text
input/hermes-briefs/<wave>/<marker>.index.json
```

The sidecar exists for human review and regeneration tuning. The brief itself stays clean — no scores, match terms, titles, or descriptions. The ranked order of `recommended_youtube_video_ids` already carries the rank Hermes needs: Hermes works down the list in order. Anything stored in the brief is something the agent may over-read, so diagnostics are kept out of the trigger by contract.

### Optional enhancement: search-mode discovery

For markers with thin coverage (`fructosamine`, `lpa`), a search-based mode using `youtube.search.list` with marker-specific queries (e.g. `"Lp(a) optimal range"`, `"fructosamine lab"`) could find additional videos regardless of channel. This is a future enhancement, not a blocker.

## Hermes runtime workflow

When Hermes researches a marker (one of the markers in the wave being run), the brief is consumed in two visibility scopes that the orchestrator keeps separate.

**Discovery and extraction — pointers only, SM rows withheld:**

1. Read the six pointer fields from `input/hermes-briefs/<wave>/<marker>.yaml`.
2. Fetch transcripts inline for `recommended_youtube_video_ids`.
3. Use `recommended_practitioner_ids` to prioritise practitioner-specific public surfaces.
4. Resolve `recommended_pubmed_ids` and `recommended_dois` through PubMed/PMC/Crossref metadata.
5. Fetch only permissive/public `recommended_source_urls`.
6. Use `recommended_search_queries` as fallback discovery prompts when curated pointers are absent, fail, or are insufficient.
7. Extract practitioner claims, citations, named studies, PMIDs, DOIs, and context — grounding every value byte-for-byte in a fetched source. The SM anchor rows are not in this context.

**Evaluation — SM rows revealed:**

8. Only at the validation council, after extraction, are the brief's SM anchor rows revealed, and only to classify each already-extracted claim's alignment against them: `aligned`, `wider_than_envelope`, `narrower_than_envelope`, `contradictory`, or `not_comparable` (section 17).

### SM rows are withheld until evaluation

The SM anchor rows ride inside the brief, but the orchestrator injects them only into the council prompt — never into discovery or extraction. They are an alignment reference, not an input range: `evidence_weight: 0`, never a proof source, never raising a grade or score, never entering a claim's value. The comparison is stored as a separate `alignment_status` annotation. The firewall is structural: a number the extractor never sees is a number it cannot anchor on or fabricate toward. This is the primary defense against SM-adjacent fabrication.

## Pointer field roles

The pointer fields support the MO provenance chain:

```text
practitioner/source claim
-> cited paper, named study, DOI, or PMID if present
-> resolved PubMed/PMC/Crossref record
-> study quality classification
-> accepted claim or quarantine
```

### `recommended_youtube_video_ids`

- Starting points for practitioner claims;
- Hermes fetches transcripts inline;
- Hermes looks for explicit claims, cited papers, named studies, PMIDs, and DOIs;
- Generated from `input/youtube-video-inventory/` metadata matches.

### `recommended_practitioner_ids`

- Tells Hermes which MO practitioners are plausible for this marker;
- Helps route discovery toward practitioner-specific public surfaces and conflict-of-interest context;
- Generated from thesaurus + semantic matching against the practitioner registry.

### `recommended_pubmed_ids` and `recommended_dois`

- Provide sanity/context and possible cited-study resolution targets;
- Strongest when practitioner-cited or when they identify high-quality cohort, RCT, systematic review, or meta-analysis evidence;
- Sourced from `known_research_context` in the SM YAML plus any resolved citations.

### `recommended_source_urls`

- Public/permissive pages that may contain practitioner claims or citations;
- Must not point to gated or terms-restricted lab pages.

### `recommended_search_queries`

- Fallback prompts for finding practitioner claims and cited papers when no curated pointer exists;
- Generated deterministically from marker name, aliases, and practitioner context.

## General ranking rule

For every pointer field, prefer recommendations that reduce Hermes uncertainty about MO provenance:

1. Practitioner-cited identifiers or pages that contain an explicit claim plus a cited paper, named study, DOI, or PMID.
2. Practitioner surfaces strongly associated with the marker, even when the citation must be extracted later by Hermes.
3. High-quality direct biomedical context for the marker: cohort studies, RCTs, systematic reviews, meta-analyses, guidelines, or major named studies.
4. Authoritative public context that helps Hermes disambiguate marker identity, unit, specimen, assay, or risk direction.
5. Fallback search queries when no curated pointer is available.

Prefer empty lists over noisy recommendations. If later review shows noisy pointers, regenerate the brief.

## Where enhanced information comes from

Use only sources that are suitable as Hermes inputs. The generator may use richer intermediate data, but the brief stores only compact pointer lists.

### `recommended_youtube_video_ids`

Source: YouTube Data API metadata inventory.

Generation inputs:

- practitioner registry channel IDs and handles;
- video title;
- full raw video description;
- marker aliases from `input/marker_glossary.json`.

Selection rule: match marker terms against `title + full raw description`. Do not fetch transcripts during brief generation. Hermes fetches transcripts inline later.

### `recommended_practitioner_ids`

Source: practitioner registry and marker/practitioner association data.

Primary local inputs:

- `input/practitioner_registry.json`;
- `input/marker_glossary.json` aliases;
- `input/registry/marker-identity-registry.v1.yaml` canonical aliases and equivalent payload groups;
- practitioner `marker_affinity`, `key_contribution`, `specialty_focus`;
- practitioner `surfaces`, `source_tier`, `source_grade`, `paradigm_affinity`, and `commercial_interests`;
- e5 semantic fallback when thesaurus yields zero matches.

Selection signals:

- direct `marker_affinity` match to the marker slug or a known alias;
- practitioner has public surfaces Hermes can inspect;
- practitioner is MO-relevant for the marker or adjacent physiology;
- practitioner has previously made claims about this marker or related topics;
- practitioner is likely to cite primary literature rather than only repeat generic advice.

Reject signals:

- no marker affinity, no surface, and no known topic association;
- only generic wellness association with no marker-specific reason;
- source is a lab/provider page that Hermes should not fetch;
- identity cannot be resolved to a registry ID.

Ranking rule: rank registry-backed practitioners with stronger marker affinity and inspectable public surfaces first. Carry COI context from the registry, but do not treat practitioner presence as proof of a claim.

Hermes use: prioritise this practitioner's public surfaces, connect extracted claims to the practitioner ID, and carry registry COI context into claim review.

### `recommended_pubmed_ids`

Source: local SM range research context, PubMed, PMC, and practitioner-cited references.

Primary inputs:

- existing `known_research_context.pmids` in SM YAMLs;
- PMIDs in YouTube descriptions, practitioner pages, podcast notes, or public articles.

Selection signals:

- PMID was explicitly cited by a practitioner or source page;
- study directly concerns the marker, target threshold, risk direction, or intervention response;
- study type is strong for the claim class;
- article resolves cleanly and has enough metadata for Hermes to classify quality.

Reject signals:

- marker mention is incidental;
- animal-only, in-vitro-only, or small uncontrolled evidence unless no stronger human evidence exists;
- paper is about a different analyte, specimen, unit, disease population, or assay.

Ranking rule: practitioner-cited PMIDs first, then high-quality human evidence directly tied to the marker. Keep the list short enough that Hermes starts focused.

### `recommended_dois`

Source: Crossref, PubMed records, PMC records, and practitioner-cited references.

Primary inputs:

- DOI fields linked from selected PMIDs;
- DOI strings in practitioner pages, video descriptions, podcast notes, and public articles.

Selection signals:

- DOI identifies a practitioner-cited paper;
- DOI is the cleanest resolver for a paper without PMID;
- DOI points to major study relevant to the marker.

Reject signals:

- DOI only resolves to a supplement, correction, editorial, or unrelated article;
- DOI points to inaccessible full text with no usable public metadata.

### `recommended_source_urls`

Source: permissive public web pages only.

Allowed source classes:

- practitioner-owned public pages with marker claims or reference lists;
- public podcast episode pages or show notes with citations;
- YouTube watch pages only when needed as a source URL; the preferred YouTube pointer remains the video ID;
- PMC article pages, preferably OA and commercial-use-compatible;
- PubMed abstract pages;
- Crossref DOI landing metadata pages;
- government, public-health, society, or guideline pages where access and terms allow.

Required URL value:

- the page should plausibly contain a practitioner claim, citation list, study metadata, guideline context, or marker disambiguation;
- the URL must be stable enough for Hermes to fetch later;
- the page must be public without login, cookies, auth walls, or paywall-only content;
- the page must not be a gated lab or restricted lab reference page.

Reject signals:

- lab/provider reference pages with restricted terms;
- pages requiring login, subscription, cookies, or scripted consent;
- generic consumer pages with no claim source and no citations;
- search result pages;
- pages whose only useful content is already represented by a PMID, DOI, or YouTube video ID.

### `recommended_search_queries`

Source: deterministic query generation from marker identity, aliases, practitioner context, and missing pointer classes.

Primary inputs:

- marker slug and marker name from the SM YAML;
- aliases from `input/marker_glossary.json`;
- identity context from `input/registry/marker-identity-registry.v1.yaml`;
- practitioner names and aliases from selected `recommended_practitioner_ids`;
- claim-intent words: target, threshold, optimal, risk, intervention, outcome, guideline, cohort, RCT, trial, meta-analysis, PMID, DOI, named study.

Query templates:

- `<marker alias> <practitioner name> PMID DOI`;
- `<marker alias> <practitioner name> cohort study`;
- `<marker alias> optimal target practitioner cited study`;
- `<marker alias> threshold risk cohort PMID`;
- `<marker alias> intervention trial DOI`;
- `<marker alias> guideline threshold PMID`.

Reject signals:

- broad consumer-health queries with no provenance intent;
- queries that omit marker identity;
- queries that only search lab reference ranges;
- long natural-language prompts that are hard to reproduce or compare.

Hermes use: execute these only when curated pointers are absent, fail, or need expansion; convert discovered evidence back into concrete PMIDs, DOIs, URLs, or practitioner claims.

## Source constraints

Do not use gated or terms-restricted lab pages as Hermes input sources. Labs may be useful for separate inventory or reference work, but they are not appropriate source pointers for this framework.

Prefer:

- public YouTube metadata and selected inline transcripts;
- PubMed metadata;
- PMC OA commercial-use-allowed content;
- Crossref metadata;
- practitioner-owned public pages where terms allow;
- government or public-health pages where terms allow.

Avoid:

- gated lab pages;
- pages requiring login, cookies, or auth;
- paywalled full text;
- restricted lab reference pages as Hermes starting sources.

## MO provenance orientation

The target MO provenance chain is:

```text
practitioner/source claim
-> cited paper, named study, DOI, or PMID if present
-> resolved PubMed/PMC/Crossref record
-> study quality classification
-> accepted claim or quarantine
```

The most valuable YouTube videos are not merely videos that mention a marker. They are videos likely to contain practitioner claims and ideally references to studies, cohorts, PMIDs, DOIs, or named papers that Hermes can resolve.

YouTube video IDs are therefore starting points for MO claim discovery, not final evidence.

## Validation rules

A valid brief must satisfy:

- YAML parses successfully.
- `schema_version` is present (`hermes-brief-1`).
- Pointer fields are lists of strings.
- No duplicate values appear within a pointer field.
- `recommended_youtube_video_ids` values look like YouTube video IDs.
- `recommended_practitioner_ids` values match practitioner registry ID format.
- `recommended_pubmed_ids` values are numeric strings.
- `recommended_dois` values are DOI strings.
- `recommended_source_urls` contains only permissive/public URLs.
- `recommended_search_queries` contains concise query strings, not paragraphs.
- No transcript text, description, title, score, or rationale is stored inside the brief.
- The original SM YAML is untouched (verified by SHA-256 or file timestamp).

The acceptance check is `code/acceptance/check_hermes_briefs.py`.

## Non-goals

This framework does not require:

- bulk transcript caching;
- transcript cache manifests;
- downloading all transcripts before Hermes runs;
- storing descriptions or titles in briefs;
- storing match scores, ranking rationale, or generator diagnostics in briefs;
- using SM reference ranges as proof for MO claims;
- using gated lab pages as source pointers;
- modifying SM YAMLs in place.

## Implementation

The implementation is split into small deterministic scripts:

```text
scripts/build_youtube_video_inventory.py
    -> input/youtube-video-inventory/videos/*.json

scripts/prepare_hermes_briefs.py
    -> input/hermes-briefs/<wave>/<marker>.yaml

code/acceptance/check_hermes_briefs.py
    -> validates brief format, pointer validity, and SM YAML untouched status
```

`build_youtube_video_inventory.py` fetches YouTube metadata via the Data API. No transcripts. `prepare_hermes_briefs.py` generates the actual Hermes trigger briefs: it reads SM YAMLs, strips bloat, adds pointer fields, matches practitioners via thesaurus + e5 semantic fallback, and matches videos from the inventory. The acceptance check verifies YAML cleanliness, pointer format, source-policy constraints, and registry/identifier validity. Recommendation diagnostics may be printed during generation, but they are not part of the Hermes input contract.
