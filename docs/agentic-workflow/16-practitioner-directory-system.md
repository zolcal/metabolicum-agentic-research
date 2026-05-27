# Practitioner directory system

This document defines the practitioner, researcher, organization, and media-source registry used by the agentic research pipeline. It is the source contract for discovery, scoring, conflict flagging, and manual review.

The registry answers two different questions:

1. Who is an approved metabolic-health source?
2. Where does that source publish material the pipeline can legally and practically inspect?

The first question is handled by `PractitionerEntry`. The second is handled by `SourceSurface`.

`PractitionerEntry.id` is the stable registry identity used across source attribution, citation edges, conflict checks, and review screens. It is a lowercase slug with an entity prefix: `person:peter-attia`, `company:virta-health`, `network:public-health-collaboration`, `media:diet-doctor`. IDs are never recycled. If two entries are merged, the losing ID becomes an alias that redirects to the surviving ID.

## Entity-id prefix mapping

Each `entity_type` has exactly one allowed `id` prefix. New ids must use the matching prefix; existing ids are not migrated retroactively. The §04 regex (`^[a-z]+:[a-z0-9-]+$`) is a sanity guard; this table is the authoritative mapping for registry maintenance.

| `entity_type` | id prefix |
| --- | --- |
| person | `person:` |
| clinic | `clinic:` |
| company | `company:` |
| professional_network | `network:` |
| research_group | `research:` |
| media_platform | `media:` |
| conference | `conference:` |
| patient_organization | `patient:` |

## Marker categorisation (marker · evaluator · calculator · index)

In this project's vocabulary, **"marker"** is the umbrella term for any subject that has reference ranges in the system. The §04 `marker_type` / `entity_type` enum sub-categorises markers into four buckets:

| Enum value | Meaning |
| --- | --- |
| `evaluator` | Directly-measured biomarkers with reference ranges. Default for lab analytes (ApoB, HbA1c, Lp(a), fasting insulin, magnesium, vitamin D, etc.). |
| `calculator` | Formula-derived values whose inputs are other markers (HOMA-IR from fasting insulin + fasting glucose; TG/HDL ratio from triglycerides + HDL-C; WHtR from waist + height). |
| `index` | Composite scores combining multiple weighted inputs (FLI, NAFLD score, NLR, AIP). |
| `marker` | Fallback for entries that don't cleanly fit `evaluator`, `calculator`, or `index`. Use sparingly; prefer the specific sub-type. |

The convention is intentional: in prose throughout this document set, "marker" usually means the umbrella category, and when the project assigns `entity_type` (or `marker_type`) to a row, the specific sub-type is used. The same word appearing as both an umbrella term and a fallback enum value is a known tension; it is preserved because clinical convention also uses "marker" loosely as an umbrella.

ApoB, HbA1c, Lp(a), and fasting insulin are `evaluator` (directly-measured analytes). HOMA-IR and TG/HDL ratio are `calculator` (formula-derived). The marker identity registry follows this convention; consumers that expect ApoB to be `marker` should treat the registry's `evaluator` value as the authoritative sub-type and read "marker" as the umbrella in surrounding prose.

## Grade separation

Practitioner grades are not claim evidence grades.

`source_grade` describes the strength of a practitioner's or organization's body of work, credentialed contribution, implementation record, or field influence. It can use range notation such as `B1-C2` because a source's contribution can span multiple evidence levels across a career. It is display and review context only; it does not enter scoring as a claim evidence grade.

`evidence_sub_grade` is assigned per claim by the validation council. It is always a single discrete value from the section-fifteen scale. The decider may use the practitioner's `source_grade` as context, but it assigns the claim's grade based on the specific evidence cited in the claim, not on the practitioner's overall reputation. A practitioner with `source_grade: B1-C2` who makes an uncited clinical-observation claim can still produce a `D` or `E` claim. A lower-tier practitioner citing a strong paper can still produce a high-evidence claim if provenance verifies the citation.

## Canonical schema

This is contract notation, not a commitment to a specific runtime framework.

```python
class PractitionerEntry:
    id: str
    canonical_name: str
    aliases: list[str] = []
    entity_type: Literal[
        "person",
        "clinic",
        "company",
        "professional_network",
        "research_group",
        "media_platform",
        "conference",
        "patient_organization",
    ]
    credentials: str | None = None
    country: str | None = None
    region: str | None = None
    languages: list[str] = []
    paradigm_affinity: list[Literal["SM", "RC", "MO", "PM"]] = []
    source_tier: Literal["A", "B", "C", "D"]
    source_grade: str | None = None
    specialty_focus: list[str] = []
    marker_affinity: list[str] = []
    key_contribution: str
    surfaces: list[SourceSurface] = []
    commercial_interests: list[CommercialInterest] = []
    status: Literal["active", "deceased", "organization", "watchlist", "archived"] = "active"
    notes: str | None = None

class SourceSurface:
    platform: Literal[
        "website",
        "x",
        "youtube",
        "podcast",
        "reddit",
        "telegram",
        "linkedin",
        "substack",
        "pubmed",
        "book",
        "conference",
        "other",
    ]
    handle_or_url: str
    rss_feed_url: str | None = None
    feed_verified_at: datetime | None = None
    subreddit: str | None = None
    post_type: Literal["submission", "comment"] | None = None
    discovery_mode: Literal[
        "native_api",
        "native_model_ingestion",
        "public_preview",
        "manual_seed",
        "metadata_only",
        "do_not_crawl",
    ]
    priority: Literal["primary", "secondary", "manual_only"]
    notes: str | None = None

class CommercialInterest:
    domain: Literal[
        "supplements",
        "lab_testing",
        "clinic_services",
        "digital_health",
        "books",
        "courses",
        "devices",
        "food_products",
        "pharmaceutical_or_industry_funding",
        "other",
    ]
    product_or_service: str
    related_markers: list[str] = []
    disclosure_quality: Literal["transparent", "partial", "opaque", "unknown"]
    severity: Literal["generic", "marker_specific", "direct_competitor", "undisclosed"]
    notes: str | None = None
```

The SQL persistence shape for this registry is defined in section four as `practitioners`, `practitioner_surfaces`, and `practitioner_commercial_interests`. The Python-style classes above are the semantic contract; the SQL tables are the canonical query surface for discovery, council conflict checks, and review dashboards.

## Source tiers

`source_tier` is the discovery and signal-weighting tier. It is manually assigned and must not be inferred from social-media bios, follower counts, or self-description.

| Tier | Default weight | Meaning |
| --- | ---: | --- |
| A | 1.00 | Foundational source. Strong credentials, repeated relevance, high signal, or field-defining contribution. |
| B | 0.75 | Specialty source. Useful in a marker domain, strong regional source, implementation source, or credentialed researcher. |
| C | 0.50 | Emerging or supporting source. Useful for discovery but requires stronger verification before downstream use. |
| D | 0.25 | Watchlist or low-confidence source. Manual-review only unless corroborated by stronger sources. |

Follower count is not a tiering rule. Engagement affects source ranking within a run, not source credibility.

## Source grade

`source_grade` is displayed in practitioner profiles and internal review screens. It captures the strongest relevant contribution associated with the source, not the quality of every claim made by that source.

Examples:

| Source grade | Meaning in practitioner registry |
| --- | --- |
| B1 | Associated with strong clinical trial or high-quality research contribution |
| B2-C1 | Strong research or implementation record with some indirectness |
| C1-D1 | Real-world implementation, clinical protocol, or observational contribution |
| D1-E2 | Early clinical practice signal, protocol source, or named practitioner view |
| E2 | Named practitioner or organization opinion without strong direct study support |

When a source has a range, scoring uses `source_tier` for source signal and stores `source_grade` for display and review context.

`source_grade` values must never be inserted into `evidence_sub_grade`. The database contract in section four enforces this with a discrete sub-grade check.

## Commercial conflict policy

Commercial conflicts are surfaced, not used as automatic rejection.

A claim receives `financial_conflict_flag = true` when the claim marker overlaps with any `commercial_interests.related_markers` entry for the source. The flag is informational. It does not reduce the composite score by default, because commercial presence is common among MO practitioners and can coexist with accurate claims.

`severity` is required so reviewers can distinguish generic commercial presence from marker-specific conflicts:

| Severity | Meaning |
| --- | --- |
| generic | The source has commercial activity, but it is not directly tied to the claim marker. |
| marker_specific | The source sells, promotes, or profits from a product or service directly tied to the claim marker. |
| direct_competitor | The source criticizes a competing product, test, or intervention while selling an alternative. |
| undisclosed | The conflict was found by the pipeline or reviewer, not disclosed by the source. |

Review surfaces must show:

- conflict domain
- product or service
- related markers
- disclosure quality
- severity

If the same claim is supported by multiple independent sources without overlapping commercial interests, the review UI should show that corroboration separately.

## Discovery ranking

Stage 1 ranks candidate sources with:

```
discovery_score = source_tier_weight * surface_priority_weight * engagement_score * recency_decay
```

Default `surface_priority_weight`:

| Priority | Weight |
| --- | ---: |
| primary | 1.00 |
| secondary | 0.70 |
| manual_only | 0.40 |

`engagement_score` and `recency_decay` use the default definitions in section eleven. Manual seeds can bypass ranking when the user explicitly selects them for a marker.

## First implementation seed size

The first implementation registry should start with:

- 30-50 core global sources across practitioners, researchers, clinics, companies, and organizations
- 10-20 marker-specific seeds for each pilot marker
- at least five Hungarian or Hungary-relevant entries for local anchoring
- at least five Australian or UK implementation sources for non-US validation

Pilot markers:

- TG/HDL ratio
- HbA1c
- ApoB
- Lp(a)
- fasting insulin / HOMA-IR

## Pilot marker seeds

| Marker | Required seed focus |
| --- | --- |
| TG/HDL ratio | insulin resistance practitioners, low-carb primary care, metabolic syndrome educators |
| HbA1c | diabetes reversal, CGM platforms, fasting and low-carb clinicians, implementation programs |
| ApoB | lipidologists, preventive cardiology, LMHR and low-carb lipid sources |
| Lp(a) | lipidologists, preventive cardiology, genetic-risk researchers |
| fasting insulin / HOMA-IR | insulin physiology, Kraft-pattern sources, HOMA-IR practitioner interpretation pages |

Recommended first-pass seeds:

| Marker | Seed sources |
| --- | --- |
| TG/HDL ratio | Ted Naiman, Benjamin Bikman, Jason Fung, David Unwin, Virta Health, Defeat Diabetes |
| HbA1c | Virta Health, Stephen Phinney, Jeff Volek, Jason Fung, David Unwin, Levels Health, Benjamin Bikman |
| ApoB | Thomas Dayspring, Allan Sniderman, Peter Attia, Nick Norwitz, Paul Mason |
| Lp(a) | Thomas Dayspring, Allan Sniderman, Peter Attia, preventive-cardiology sources |
| fasting insulin / HOMA-IR | Joseph Kraft, Benjamin Bikman, Ted Naiman, Jason Fung, Richard Maurer, Brian Lamkin |

## Initial global source roster

This is the minimum first implementation source roster. It is intentionally focused on sources already relevant to the first five markers and to the MO/RC boundary.

| Source | Entity | Region | Paradigm | Tier | Source grade | Primary contribution |
| --- | --- | --- | --- | --- | --- | --- |
| Peter Attia | person | United States | MO | A | B1-C2 | longevity framework, insulin-centric risk, ApoB emphasis |
| Ted Naiman | person | United States | MO | A | D1-E2 | protein-energy framework, minimalist metabolic testing |
| Dominic D'Agostino | person | United States | MO | A | B1 | ketone physiology and metabolic therapy research |
| Robert Lustig | person | United States | MO | A | B2 | fructose, uric acid, metabolic disease framework |
| Jason Fung | person | Canada | MO | A | C1-D1 | fasting and T2DM reversal framework |
| Thomas Dayspring | person | United States | RC/MO | A | B2-C1 | ApoB-centric lipidology and advanced lipid testing |
| Joseph Kraft | person | United States | MO | A | D2 | insulin-response patterns and post-prandial insulin framework |
| Benjamin Bikman | person | United States | MO | A | B2 | insulin signaling, metabolic syndrome, ketone physiology |
| Stephen Phinney | person | United States | MO | A | B1 | ketogenic nutrition and metabolic adaptation |
| Jeff Volek | person | United States | MO | A | B1 | carbohydrate restriction and performance physiology |
| David Ludwig | person | United States | RC/MO | A | B2 | carbohydrate-insulin model |
| Nick Norwitz | person | United States | MO | B | B2-C1 | LMHR phenotype, ketogenic lipidology |
| Allan Sniderman | person | Canada | RC/MO | A | B1 | ApoB causal and clinical-risk interpretation |
| David Unwin | person | United Kingdom | MO | A | C1 | low-carb primary-care implementation |
| Paul Mason | person | Australia | MO | A | D1 | LMHR and low-carb lipid interpretation |
| Anthony Chaffee | person | Australia / United States | MO | B | E2 | carnivore/plant-free clinical advocacy and dietary reversal claims |
| Peter Brukner | person | Australia | RC/MO | A | B1-C1 | public-health implementation and Defeat Diabetes |
| Tim Noakes | person | South Africa / UK influence | MO | A | B2 | low-carb metabolic syndrome reversal |
| Margaret Ashwell | person | United Kingdom | RC/MO | A | B2 | waist-to-height ratio research |
| Andreas Eenfeldt | person | Sweden | MO | B | C1 | Diet Doctor and global low-carb education |
| Megan Ramos | person | Canada | MO | B | C1 | fasting implementation and IDM/Fasting Method |
| Èvelyne Bourdua-Roy | person | Canada | MO | B | D1-E2 | low-carb clinical implementation in French Canada |
| Jonathan Little | person | Canada | RC/MO | B | B2 | low-carb diets, T2DM, exercise metabolism |
| David Harper | person | Canada | MO | B | D2 | ketogenic diets in cancer metabolism |
| William Davis | person | United States | MO | B | C1-D1 | grain elimination, small LDL, gut-health protocols |
| Michael Holick | person | United States | MO | B | B2 | vitamin D physiology and 25(OH)D framework |
| Richard Maurer | person | United States | MO | B | E2 | HOMA-IR clinical interpretation framework |
| Brian Lamkin | person | United States | MO | B | E2 | HOMA-IR functional medicine interpretation tiers |
| Virta Health | company | United States | MO | A | B1 | T2DM reversal at scale |
| Levels Health | company | United States | MO | B | C1 | CGM-centric metabolic education |
| Defeat Diabetes | company | Australia | MO | A | C1 | national virtual low-carb implementation |
| CSIRO | research_group | Australia | RC/MO | A | B1 | government-funded low-carb trials |
| Public Health Collaboration | professional_network | United Kingdom | MO | B | C1 | low-carb GP network |
| Low Carb Program | company | United Kingdom | MO | B | C1 | NHS-approved digital T2DM program |
| Diet Doctor | media_platform | Sweden | MO | B | C1 | low-carb education and practitioner network |
| Metabolic Health Summit | conference | United States | MO | B | C1 | metabolic health conference network |

## Hungary anchor roster

The Hungarian roster anchors local relevance and language coverage. These entries are allowed to be lower source-grade than global sources because their value is local clinical context, local language, and implementation pathways.

| Source | Entity | Region | Paradigm | Tier | Source grade | Primary contribution |
| --- | --- | --- | --- | --- | --- | --- |
| Metodic.hu / Bengédi Robi | media_platform | Hungary | MO | B | C1 | Hungarian metabolic-health education and media surface |
| Hungarian Diabetes Association | professional_network | Hungary | SM/RC | B | A1 | conservative diabetes guideline surface |
| Semmelweis metabolic research sources | research_group | Hungary | SM/RC | B | B2-C2 | population studies and insulin-resistance context |
| University of Debrecen metabolic research sources | research_group | Hungary | SM/RC | B | B2-C2 | NAFLD and metabolic-syndrome research |
| Hungarian low-carb clinician network | professional_network | Hungary | MO | C | E2 | local practitioner discovery and manual seed source |

## Source maintenance rules

New entries go through a deduplication check before insertion. The maintainer compares canonical name, aliases, known handles, organization affiliation, country, and source surfaces. If the candidate matches an existing entry, update the existing entry instead of creating a duplicate. If a split is needed, preserve both stable IDs and document the reason in `notes`.

Additions must include:

- source identity and country
- aliases for people and known informal references
- source tier
- source grade or rationale for leaving it blank
- at least one source surface or reason for manual-only status
- RSS feed URL and verification date for podcast surfaces, where available
- paradigm affinity
- marker affinity where known
- conflict disclosure status

Marker glossary maintenance follows the same review discipline. Glossary entries are seeded from canonical marker names, known abbreviations, local-language terms, and aliases observed in approved sources. Each term records language and term type in the `marker_glossary` table from section four. Ambiguous terms are allowed only when the tagger can preserve ambiguity instead of forcing a marker.

Podcast RSS feeds are a registry maintenance goal, not a free-text note. A podcast surface should carry `rss_feed_url` and `feed_verified_at` once verified. If the feed is unknown, the field stays null and the surface remains eligible for Podscan, Listen Notes, or manual discovery. Feed candidates are not considered verified until a parser can read the feed and identify relevant episodes from the expected show.

Removals must preserve an archived record with the reason for removal. Possible reasons:

- no longer public
- content quality below threshold
- platform unavailable
- repeated hallucination risk
- conflict disclosure unacceptable
- out of scope for the first implementation

The registry is reviewed after each marker run. If a marker produces fewer than thirty approved high-quality claims, the first response is to inspect the source roster and add marker-specific seeds before redesigning downstream extraction.
