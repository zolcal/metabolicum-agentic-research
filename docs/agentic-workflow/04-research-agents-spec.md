# Research agents specification — source-first extraction

Stage 2 takes the ranked source list from Stage 1 and processes each source exactly once, producing claims that can serve multiple markers. Three agents inside Stage 2 cooperate. The content extractor handles verbatim text — transcript segments, post text, blog body — walking the entire source and identifying every numeric metabolic claim. The runtime may use cloud or local models, but the contract is model-neutral: every extraction records the model identity so quality, routing, and fallback behavior remain auditable. The marker tagger, given a verbatim claim, identifies which markers it discusses. A sentence like "Apolipoprotein B above 80 mg/dL is concerning" tags `ApoB`, while a sentence like "When ApoB is high and Lp(a) is also elevated, risk multiplies" tags both `ApoB` and `Lp(a)`. The tagger refuses to invent marker tags not grounded in the verbatim text. The demographic structurer takes the verbatim claim and its tags and produces a `MarkerRecommendation` with target value or range, units, population, sex, age band, weight band, comorbidity, and citation. The `applies_to_markers` field is mandatory and must contain at least one marker.

The marker tagger normalizes marker names before matching. It lowercases text, normalizes separators (`-`, `_`, `:`, `/`, and spaces), expands known abbreviations, and matches against canonical marker IDs plus the marker glossary. For example, `TG HDL ratio`, `TG/HDL`, `tg_hdl_ratio`, and `tg-hdl` all normalize to the same canonical marker family. The tagger also uses practitioner aliases from section sixteen for attribution. If an alias is ambiguous, such as a first name shared by multiple practitioners, the claim is flagged as ambiguous rather than guessed.

Separating these three roles prevents the extractor from "helpfully" inferring demographic qualifiers or marker tags that the speaker did not actually state. The output contract looks like this:

```python
class PopulationQualifier:
    applies_to: str                           # "unspecified" when the source does not say
    sex: str | None = None                    # female, male, all, or source wording
    age_min: float | None = None
    age_max: float | None = None
    weight_min: float | None = None
    weight_max: float | None = None
    bmi_min: float | None = None
    bmi_max: float | None = None
    ethnicity: str | None = None
    cohort: str | None = None
    pregnancy_status: str | None = None
    comorbidity: str | None = None
    specimen: str | None = None
    method: str | None = None
    stratum: str | None = None
    population_scope: str | None = None

class CitedPaper:
    raw_reference: str                        # verbatim citation phrase from the source
    pmid: str | None = None
    doi: str | None = None
    title: str | None = None
    authors_short: str | None = None
    year: int | None = None
    journal: str | None = None
    resolved: bool = False                    # provenance agent sets true only after resolution

class MarkerRecommendation:
    applies_to_markers: list[str]            # at least one, multi-marker aware
    target_value: float | None
    target_range: tuple[float, float] | None
    units: str
    direction: Literal["below", "above", "between", "at"]
    claim_polarity: Literal["supports", "refutes", "qualifies"] = "supports"
    population: PopulationQualifier
    verbatim_quote: str                      # required, at least one sentence
    source_id: uuid.UUID                     # foreign key to sources table
    source_url: str
    source_type: Literal["post", "video", "podcast", "blog", "paper"]
    source_language: str = "en"
    translated_quote: str | None = None
    translation_method: Literal["deepl", "local_model", "human", "none"] = "none"
    retrieved_at: datetime
    speaker_or_author: str
    speaker_registry_id: str | None = None
    cited_paper: CitedPaper | None
    paradigm: Literal["SM", "RC", "MO"]
    extraction_model: str
    extractor_confidence: float
```

The standalone `metabolicum-agentic-research` database layout reflects this design. There is a `sources` table keyed by URL, holding the canonical fetched-and-transcribed source plus replay metadata. There is a `claims` table holding pre-council extracted claims with their verbatim quotes and structured fields, foreign-keyed to sources. There is a `source_claim_marker` link table that handles the many-to-many relationship between extracted claims and markers. The validation council emits post-council rows into `biomarker_claims`, one row per claim-marker pair. Rejected or blocked records go to `quarantine`, not to silent deletion. Reference-library and marker-content tables are included here so every field projected by section eighteen has a canonical home in the research database.

The SQL below is executable in order. Cross-table foreign keys whose targets are declared later in the block (`biomarker_claims.primary_envelope_id` and `citation_edges.cited_study_id`) are attached via `ALTER TABLE` statements at the end of the block.

```sql
CREATE TABLE sources (
    id uuid PRIMARY KEY,
    source_type text NOT NULL,
    url text UNIQUE NOT NULL,
    fetched_at timestamptz NOT NULL,
    transcript_text text,
    transcript_method text,
    author text,
    published_at timestamptz,
    platform text NOT NULL,
    title text,
    license text,
    raw_artifact_ref text,
    raw_sha256 text
);

CREATE TABLE practitioners (
    id text PRIMARY KEY,
    canonical_name text NOT NULL,
    aliases text[] DEFAULT '{}',
    entity_type text NOT NULL CHECK (entity_type IN (
        'person',
        'clinic',
        'company',
        'professional_network',
        'research_group',
        'media_platform',
        'conference',
        'patient_organization'
    )),
    credentials text,
    country text,
    region text,
    languages text[] DEFAULT '{}',
    paradigm_affinity text[] DEFAULT '{}' CHECK (
        paradigm_affinity <@ ARRAY['SM','RC','MO','PM']::text[]
    ),
    source_tier text NOT NULL CHECK (source_tier IN ('A', 'B', 'C', 'D')),
    source_grade text,
    specialty_focus text[] DEFAULT '{}',
    marker_affinity text[] DEFAULT '{}',
    key_contribution text,
    status text DEFAULT 'active' CHECK (status IN ('active', 'deceased', 'organization', 'watchlist', 'archived')),
    notes text,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    CHECK (id ~ '^[a-z]+:[a-z0-9-]+$')
);

CREATE TABLE practitioner_surfaces (
    id uuid PRIMARY KEY,
    practitioner_id text NOT NULL REFERENCES practitioners(id) ON DELETE CASCADE,
    platform text NOT NULL CHECK (platform IN (
        'website',
        'x',
        'youtube',
        'podcast',
        'reddit',
        'telegram',
        'linkedin',
        'substack',
        'pubmed',
        'book',
        'conference',
        'other'
    )),
    handle_or_url text NOT NULL,
    rss_feed_url text,
    feed_verified_at timestamptz,
    subreddit text,
    post_type text CHECK (post_type IS NULL OR post_type IN ('submission', 'comment')),
    discovery_mode text NOT NULL CHECK (discovery_mode IN (
        'native_api',
        'native_model_ingestion',
        'public_preview',
        'manual_seed',
        'metadata_only',
        'do_not_crawl'
    )),
    priority text NOT NULL CHECK (priority IN ('primary', 'secondary', 'manual_only')),
    notes text,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    UNIQUE (practitioner_id, platform, handle_or_url)
);

CREATE TABLE practitioner_commercial_interests (
    id uuid PRIMARY KEY,
    practitioner_id text NOT NULL REFERENCES practitioners(id) ON DELETE CASCADE,
    domain text NOT NULL CHECK (domain IN (
        'supplements',
        'lab_testing',
        'clinic_services',
        'digital_health',
        'books',
        'courses',
        'devices',
        'food_products',
        'pharmaceutical_or_industry_funding',
        'other'
    )),
    product_or_service text NOT NULL,
    related_markers text[] DEFAULT '{}',
    disclosure_quality text NOT NULL CHECK (disclosure_quality IN ('transparent', 'partial', 'opaque', 'unknown')),
    severity text NOT NULL CHECK (severity IN ('generic', 'marker_specific', 'direct_competitor', 'undisclosed')),
    notes text,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL
);

CREATE INDEX idx_practitioners_aliases ON practitioners USING gin(aliases);
CREATE INDEX idx_practitioners_marker_affinity ON practitioners USING gin(marker_affinity);
CREATE INDEX idx_practitioner_surfaces_lookup ON practitioner_surfaces(platform, handle_or_url);
CREATE INDEX idx_practitioner_commercial_markers ON practitioner_commercial_interests USING gin(related_markers);

CREATE TABLE claims (
    id uuid PRIMARY KEY,
    source_id uuid REFERENCES sources(id),
    speaker_or_author text,
    speaker_registry_id text REFERENCES practitioners(id),
    verbatim_quote text NOT NULL,
    paradigm text CHECK (paradigm IN ('SM', 'RC', 'MO')),
    target_value numeric,
    target_range_low numeric,
    target_range_high numeric,
    units text,
    direction text,
    claim_polarity text DEFAULT 'supports' CHECK (claim_polarity IN ('supports', 'refutes', 'qualifies')),
    population jsonb,
    cited_paper jsonb,
    source_language text DEFAULT 'en',
    translated_quote text,
    translation_method text DEFAULT 'none' CHECK (translation_method IN ('deepl', 'local_model', 'human', 'none')),
    extraction_model text NOT NULL,
    extractor_confidence float CHECK (extractor_confidence >= 0 AND extractor_confidence <= 1),
    extracted_at timestamptz NOT NULL
);

CREATE TABLE marker_glossary (
    marker text NOT NULL,
    language text NOT NULL,
    term text NOT NULL,
    term_type text CHECK (term_type IN ('primary', 'alias', 'colloquial', 'abbreviation')),
    PRIMARY KEY (marker, language, term)
);

CREATE TABLE source_claim_marker (
    claim_id uuid REFERENCES claims(id),
    marker text NOT NULL,
    confidence float,
    PRIMARY KEY (claim_id, marker)
);

CREATE INDEX idx_scm_marker ON source_claim_marker(marker);

CREATE TABLE biomarker_claims (
    id uuid PRIMARY KEY,
    claim_id uuid REFERENCES claims(id),
    source_id uuid REFERENCES sources(id),
    speaker_or_author text,
    speaker_registry_id text REFERENCES practitioners(id),
    marker text NOT NULL,
    verbatim_quote text NOT NULL,
    paradigm text CHECK (paradigm IN ('SM', 'RC', 'MO')),
    target_value numeric,
    target_range_low numeric,
    target_range_high numeric,
    units text,
    direction text,
    claim_polarity text DEFAULT 'supports' CHECK (claim_polarity IN ('supports', 'refutes', 'qualifies')),
    population jsonb,
    cited_paper jsonb,
    label text,
    color text CHECK (color IS NULL OR color IN (
        '#22c55e','#84cc16','#eab308','#f97316','#ef4444','#dc2626','#9ca3af'
    )),                              -- canonical palette per metasync's RANGE-STATUS-COLOR-POLICY.md;
                                     -- assembly resolves via canonical_color(status); same constraint on range_facts.
    display_role text CHECK (display_role IN (
        'primary_standard_medical_anchor',
        'primary_research_consensus_range',
        'primary_metabolic_optimization_target',
        'supporting',
        'comparison_only',
        'internal_research_gate'
    )),
    method_note text,
    derivation_note text,
    context_note text,
    reviewer_quote_verified boolean,
    reviewer_fetched_at timestamptz,
    reviewer_fetched_url text,
    reviewer_fetch_status text CHECK (reviewer_fetch_status IN (
        'verified_present',
        'verified_absent',
        'source_unreachable',
        'cached_only',
        'not_attempted'
    )),
    evidence_sub_grade text NOT NULL CHECK (evidence_sub_grade IN (
        'A1','A2','A3','B1','B2','B3','C1','C2','C3','C4',
        'D1','D2','D3','P1','P2','E1','E2','E3'
    )),
    evidence_grade text GENERATED ALWAYS AS (LEFT(evidence_sub_grade, 1)) STORED,
    council_consensus_score float CHECK (council_consensus_score >= 0 AND council_consensus_score <= 1),
    financial_conflict_flag boolean DEFAULT false,
    financial_conflict_severity text DEFAULT 'generic' CHECK (financial_conflict_severity IN ('generic', 'marker_specific', 'direct_competitor', 'undisclosed')),
    paradigm_divergence_flag text DEFAULT 'none' CHECK (paradigm_divergence_flag IN ('none', 'moderate', 'extreme')),
    primary_envelope_id uuid,
    primary_envelope_alignment_status text DEFAULT 'not_evaluated' CHECK (primary_envelope_alignment_status IN (
        'not_evaluated',
        'aligned',
        'narrower_than_envelope',
        'wider_than_envelope',
        'contradictory',
        'not_comparable',
        'no_envelope_exists',
        'multiple_envelopes'
    )),
    provenance_status text DEFAULT 'pending' CHECK (provenance_status IN ('pending', 'resolved', 'ambiguous', 'unresolvable')),
    legal_status text DEFAULT 'pending' CHECK (legal_status IN ('pending', 'approved', 'approved_with_modification', 'quarantined', 'rejected')),
    approval_status text DEFAULT 'pending' CHECK (approval_status IN ('pending', 'approved', 'quarantined')),
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    approved_at timestamptz,
    exported_at timestamptz
);

CREATE INDEX idx_biomarker_claims_marker ON biomarker_claims(marker);
CREATE INDEX idx_biomarker_claims_approval ON biomarker_claims(approval_status);
CREATE INDEX idx_biomarker_claims_primary_envelope_alignment ON biomarker_claims(primary_envelope_alignment_status);

CREATE TABLE sm_anchors (
    id uuid PRIMARY KEY,
    marker text NOT NULL,
    target_value numeric,
    target_range_low numeric,
    target_range_high numeric,
    units text NOT NULL,
    population jsonb DEFAULT '{"applies_to":"general_adult"}'::jsonb,
    guideline_source text NOT NULL,
    source_url text,
    citation text NOT NULL,
    anchor_grade text CHECK (anchor_grade IN ('guideline', 'consensus', 'systematic_review')),
    curated_at timestamptz NOT NULL,
    notes text
);

CREATE INDEX idx_sm_anchors_marker ON sm_anchors(marker);

CREATE TABLE research_target_envelopes (
    id uuid PRIMARY KEY,
    marker text NOT NULL,
    paradigm text CHECK (paradigm IN ('SM', 'RC', 'MO')),
    envelope_version text NOT NULL,
    range_order smallint NOT NULL,
    units text NOT NULL,
    specimen text,
    method text,
    variant text,
    direction text CHECK (direction IN ('below', 'above', 'between', 'at')),
    target_value numeric,
    target_range_low numeric,
    target_range_high numeric,
    tolerance_range_low numeric,
    tolerance_range_high numeric,
    sex_for_lab_reference text,
    gender text,
    stratum text,
    age_min smallint,
    age_max smallint,
    weight_min numeric,
    weight_max numeric,
    bmi_min numeric,
    bmi_max numeric,
    ethnicity text,
    altitude_meters numeric,
    cohort text,
    pregnancy_status text,
    population_scope text,
    population jsonb DEFAULT '{}'::jsonb,
    display_role text,
    primary_goal boolean NOT NULL DEFAULT false,
    readiness_state text DEFAULT 'draft' CHECK (readiness_state IN ('ready', 'draft', 'insufficient')),
    generation_method text NOT NULL,
    context_note text,
    derivation_hash text,
    publishable boolean NOT NULL DEFAULT false CHECK (publishable = false),
    evidence_weight numeric NOT NULL DEFAULT 0 CHECK (evidence_weight = 0),
    disclose_origin_to_agents boolean NOT NULL DEFAULT false CHECK (disclose_origin_to_agents = false),
    export_to_metasync boolean NOT NULL DEFAULT false CHECK (export_to_metasync = false),
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    notes text,
    CHECK (target_range_low IS NULL OR target_range_high IS NULL OR target_range_low <= target_range_high),
    CHECK (tolerance_range_low IS NULL OR tolerance_range_high IS NULL OR tolerance_range_low <= tolerance_range_high),
    CHECK (age_min IS NULL OR age_max IS NULL OR age_min <= age_max),
    CHECK (weight_min IS NULL OR weight_max IS NULL OR weight_min <= weight_max),
    CHECK (bmi_min IS NULL OR bmi_max IS NULL OR bmi_min <= bmi_max)
);

CREATE INDEX idx_research_target_envelopes_marker ON research_target_envelopes(marker, paradigm, readiness_state);
CREATE INDEX idx_research_target_envelopes_context ON research_target_envelopes(marker, paradigm, units, sex_for_lab_reference, age_min, age_max);

CREATE TABLE claim_envelope_evaluations (
    biomarker_claim_id uuid REFERENCES biomarker_claims(id),
    envelope_id uuid REFERENCES research_target_envelopes(id),
    alignment_status text NOT NULL CHECK (alignment_status IN (
        'aligned',
        'narrower_than_envelope',
        'wider_than_envelope',
        'contradictory',
        'not_comparable'
    )),
    evaluated_at timestamptz NOT NULL,
    evaluator_model text NOT NULL,
    notes text,
    PRIMARY KEY (biomarker_claim_id, envelope_id)
);

CREATE INDEX idx_claim_envelope_evaluations_status ON claim_envelope_evaluations(alignment_status);

CREATE TABLE quarantine (
    id uuid PRIMARY KEY,
    source_id uuid REFERENCES sources(id),
    claim_id uuid REFERENCES claims(id),
    biomarker_claim_id uuid REFERENCES biomarker_claims(id),
    verbatim_quote text,
    rejection_stage text CHECK (rejection_stage IN ('extractor', 'reviewer', 'decider', 'provenance', 'legal', 'assembly')),
    rejection_reason text NOT NULL,
    rejection_codes text[] DEFAULT '{}',
    reviewer_notes text,
    financial_conflict_flag boolean,
    financial_conflict_severity text,
    quarantined_at timestamptz NOT NULL,
    review_outcome text DEFAULT 'pending' CHECK (review_outcome IN ('pending', 'approved_on_review', 'rejected_permanently', 'requires_source_re_fetch')),
    reviewed_at timestamptz,
    reviewed_by text,
    updated_at timestamptz NOT NULL
);

CREATE INDEX idx_quarantine_codes ON quarantine USING gin(rejection_codes);
CREATE INDEX idx_quarantine_review_outcome ON quarantine(review_outcome);

CREATE TABLE legal_reviews (
    id uuid PRIMARY KEY,
    biomarker_claim_id uuid REFERENCES biomarker_claims(id),
    decision text CHECK (decision IN ('approve', 'approve_with_modification', 'quarantine', 'reject')),
    rationale text NOT NULL,
    applicable_rules text[] DEFAULT '{}',
    quote_length_check boolean,
    license_check boolean,
    tos_check boolean,
    feist_compilation_risk text CHECK (feist_compilation_risk IN ('none', 'low', 'medium', 'high')),
    reviewed_at timestamptz NOT NULL,
    reviewer_model text NOT NULL,
    updated_at timestamptz NOT NULL
);

CREATE INDEX idx_legal_reviews_claim ON legal_reviews(biomarker_claim_id);

CREATE TABLE citation_edges (
    id uuid PRIMARY KEY,
    citing_source_id uuid REFERENCES sources(id),
    cited_registry_id text CHECK (cited_registry_id IS NULL OR cited_registry_id ~ '^[a-z]+:[a-z0-9-]+$'),
    cited_study_id uuid,
    citation_context text,
    extracted_at timestamptz NOT NULL,
    verified_by_reviewer boolean DEFAULT false
);

CREATE INDEX idx_citation_edges_cited ON citation_edges(cited_registry_id);


CREATE TABLE research_studies (
    id uuid PRIMARY KEY,
    slug text NOT NULL UNIQUE,
    pmid text UNIQUE,
    doi text UNIQUE,
    original_title text NOT NULL,
    authors_short text,
    journal text,
    publication_year smallint,
    study_type text,
    evidence_sub_grade text CHECK (evidence_sub_grade IN (
        'A1','A2','A3','B1','B2','B3','C1','C2','C3','C4',
        'D1','D2','D3','P1','P2','E1','E2','E3'
    )),
    evidence_grade text GENERATED ALWAYS AS (LEFT(evidence_sub_grade, 1)) STORED,
    sample_size integer,
    grading_confidence text CHECK (grading_confidence IN ('low', 'medium', 'high')),
    auto_graded boolean NOT NULL DEFAULT false,
    paradigm_standard boolean NOT NULL DEFAULT false,
    paradigm_research boolean NOT NULL DEFAULT false,
    paradigm_optimization boolean NOT NULL DEFAULT false,
    pubmed_url text,
    doi_url text,
    full_text_url text,
    topics text[] DEFAULT '{}',
    biomarkers text[] DEFAULT '{}',
    status text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'archived')),
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    CHECK (pmid IS NOT NULL OR doi IS NOT NULL)
);

CREATE INDEX idx_research_studies_pmid ON research_studies(pmid) WHERE pmid IS NOT NULL;
CREATE INDEX idx_research_studies_doi ON research_studies(doi) WHERE doi IS NOT NULL;
CREATE INDEX idx_research_studies_biomarkers ON research_studies USING gin(biomarkers);
CREATE INDEX idx_research_studies_status ON research_studies(status);

CREATE TABLE research_study_translations (
    id uuid PRIMARY KEY,
    study_id uuid NOT NULL REFERENCES research_studies(id) ON DELETE CASCADE,
    language text NOT NULL,
    title text NOT NULL,
    summary_plain text,
    key_finding text,
    key_findings text[] DEFAULT '{}',
    content jsonb DEFAULT '{}'::jsonb,
    content_source text NOT NULL CHECK (content_source IN ('pipeline_research', 'human', 'imported')),
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    UNIQUE (study_id, language)
);

CREATE INDEX idx_research_study_translations_study ON research_study_translations(study_id);

CREATE TABLE marker_content_sections (
    id uuid PRIMARY KEY,
    marker_slug text NOT NULL,
    marker_type text NOT NULL CHECK (marker_type IN ('marker', 'calculator', 'evaluator', 'index')),
    language text NOT NULL,
    section_type text NOT NULL CHECK (section_type IN (
        'why_matters',
        'paradigm_thresholds',
        'evidence_badge',
        'mechanism',
        'interpretation',
        'limitations',
        'references',
        'other'
    )),
    section_order smallint,
    paradigm text CHECK (paradigm IN ('SM', 'RC', 'MO')),
    content jsonb NOT NULL,
    source_type text NOT NULL CHECK (source_type IN ('pipeline', 'human', 'imported', 'generated_reviewed')),
    evidence_grade text,
    source_url text,
    content_hash text NOT NULL,
    status text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'review', 'published', 'rejected')),
    version smallint NOT NULL DEFAULT 1,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    published_at timestamptz,
    UNIQUE (marker_slug, language, section_type, paradigm, version)
);

CREATE INDEX idx_mcs_marker ON marker_content_sections(marker_slug, language);
CREATE INDEX idx_mcs_status ON marker_content_sections(status);
CREATE INDEX idx_mcs_hash ON marker_content_sections(content_hash);
CREATE UNIQUE INDEX idx_mcs_one_published ON marker_content_sections (marker_slug, language, section_type, COALESCE(paradigm, ''))
WHERE status = 'published';

CREATE TABLE content_section_claims (
    content_section_id uuid NOT NULL REFERENCES marker_content_sections(id) ON DELETE CASCADE,
    biomarker_claim_id uuid NOT NULL REFERENCES biomarker_claims(id) ON DELETE RESTRICT,
    relation_type text NOT NULL CHECK (relation_type IN ('supports', 'context', 'comparison')),
    created_at timestamptz NOT NULL,
    PRIMARY KEY (content_section_id, biomarker_claim_id)
);

CREATE INDEX idx_csc_claim ON content_section_claims(biomarker_claim_id);

CREATE TABLE content_section_citations (
    id uuid PRIMARY KEY,
    content_section_id uuid NOT NULL REFERENCES marker_content_sections(id) ON DELETE CASCADE,
    research_study_id uuid NOT NULL REFERENCES research_studies(id) ON DELETE RESTRICT,
    display_order smallint NOT NULL,
    citation_context text,
    citation_key text NOT NULL,
    created_at timestamptz NOT NULL,
    UNIQUE (content_section_id, citation_key),
    UNIQUE (content_section_id, research_study_id, display_order)
);

CREATE INDEX idx_csci_section ON content_section_citations(content_section_id);
CREATE INDEX idx_csci_study ON content_section_citations(research_study_id);

ALTER TABLE biomarker_claims
    ADD CONSTRAINT biomarker_claims_primary_envelope_fk
    FOREIGN KEY (primary_envelope_id) REFERENCES research_target_envelopes(id);

ALTER TABLE citation_edges
    ADD CONSTRAINT citation_edges_study_fk
    FOREIGN KEY (cited_study_id) REFERENCES research_studies(id);
```

Projection completeness is enforced by keeping export-facing fields in these canonical homes:

| Export surface | Canonical source |
|---|---|
| `range_fact.label`, `color`, `display_role`, `method_note`, `derivation_note`, `context_note` | `biomarker_claims` |
| `range_fact.provenance.verified_present` | `biomarker_claims.reviewer_quote_verified` |
| `source_artifact.source_title`, `source_license`, `raw_artifact_ref`, `raw_sha256` | `sources` |
| practitioner aliases, surfaces, and commercial interests | `practitioners`, `practitioner_surfaces`, `practitioner_commercial_interests` |
| `research_study.*` | `research_studies` |
| `research_study_translation.*` | `research_study_translations` |
| `marker_content_section.*` | `marker_content_sections` |
| `research_citation.*` | `content_section_citations` |

`research_studies` is the canonical reference-library entity. One row exists per resolved PMID or DOI, with deterministic `slug` creation (`pmid-<id>` preferred, otherwise a DOI-derived slug). `paradigm_*`, `topics[]`, and `biomarkers[]` are denormalized for filtering and maintained from approved claims and resolved provenance edges. `research_study_translations` stores one localized summary row per study and language.

`marker_content_sections` is the canonical narrative-content entity. Pipeline-generated or reviewed sections must link back to approved claims through `content_section_claims` before publication. `content_section_citations` is the canonical home for section-to-study citations; each in-content `citation_key` resolves to exactly one `research_studies` row within the section.

The practitioner registry tables are the SQL form of section sixteen. The council conflict check queries `speaker_registry_id` when present, then falls back to alias matching against `practitioners.aliases` when the source attribution is unresolved. If any `practitioner_commercial_interests.related_markers` entry overlaps the claim marker, the council sets `financial_conflict_flag = true` and copies the highest applicable `severity` into `financial_conflict_severity`.

The SQL block above is executable in order: tables are created in dependency order, and the two cross-table foreign keys (`biomarker_claims.primary_envelope_id` and `citation_edges.cited_study_id`) are added as `ALTER TABLE` statements after both target tables exist. Nullable canonical-completeness fields can be backfilled after the first run; no extractor output contract changes are required.

The link table is the design trick for pre-council extraction. Querying "all approved claims about TG/HDL" is one indexed lookup on `biomarker_claims.marker`. Querying "all claims this source produced" is one join. A source processed once feeds every assembly run thereafter.

The Standard Medical anchor table is a sanity-check contract, not a rejection rule. The council uses it to flag paradigm divergence when MO claims are far outside established SM reference ranges. Divergence flags are surfaced for review and dashboard filtering; they do not erase MO signal. Legal reviews are persisted separately so the approved claim row can carry the current legal status while the legal reasoning remains auditable.

`research_target_envelopes` are private research-goal contracts, not evidence-bearing contracts. Each row is one sanitized atomic envelope fact, analogous to a range fact: marker, paradigm, unit, specimen or method context, direction, population qualifiers, target bounds, tolerance bounds, readiness state, and use-policy flags. It is not a copied source table and not necessarily one row per marker. If the available source reality is age-, sex-, weight-, BMI-, ethnicity-, pregnancy-, specimen-, method-, or population-specific, the envelope data preserves that granularity as separate atomic facts. The table does not store source origins, proprietary notes, non-public provenance, or citations. The source-bearing derivation file is a private artifact described in section seventeen and is outside the agent input boundary.

`claim_envelope_evaluations` is the canonical many-to-many link between approved claim-marker rows and sanitized envelope facts. A single claim may be comparable to several envelope facts, and a single envelope fact may be evaluated against many claims. The `primary_envelope_id` and `primary_envelope_alignment_status` fields on `biomarker_claims` are dashboard conveniences for the most relevant comparison, not replacements for the link table.

`citation_edges` is populated opportunistically when a source names another practitioner, researcher, organization, framework, or paper. `cited_registry_id` must use the section-sixteen registry identifier shape, such as `person:peter-attia` or `organization:american-diabetes-association`; inserts that cannot resolve or conform to that shape stay unresolved until reviewed. When a citation edge resolves to a paper represented by `research_studies`, `cited_study_id` is populated. These edges are not used in first-implementation scoring. They preserve graph data so a later network-authority model can be evaluated without re-processing every source.

Negative and refutation claims are first-class. `direction` captures the numeric relationship being discussed; `claim_polarity` captures whether the source supports, refutes, or qualifies that relationship. For example, "ApoB above 80 is concerning" is `direction: "above"` and `claim_polarity: "supports"`, while "ApoB above 80 is not concerning in this subgroup" is `direction: "above"` and `claim_polarity: "refutes"` or `qualifies` depending on the source wording.

Anthropological qualifiers are mandatory through the `PopulationQualifier` field. If the speaker said "for women over 50," that goes in. If the speaker spoke generically, the field is `applies_to="unspecified"` and every unstated qualifier is `null`. The pipeline does not infer qualifiers; under-specified is preserved as under-specified, because the schema's job is to refuse to launder ambiguity into false precision. `speaker_or_author` is claim-level because podcasts, panels, interviews, and comment threads can have multiple speakers; `sources.author` remains source-level metadata only.

Citation chain extraction populates the `cited_paper` field with whatever the speaker actually said. "A 2019 Lancet paper on…" goes in as an unresolved reference. The provenance agent in Stage 5 resolves these to real PMIDs and DOIs where possible (the `provenance` schema is defined in section six). The `MarkerRecommendation` produced here is not yet a `BiomarkerClaim` — the council in Stage 3 converts it plus the validation outcomes into one or more `biomarker_claims` rows, one per marker the underlying claim serves, with evidence sub-grade, derived parent evidence grade, council consensus, financial conflict flag and severity, provenance status, and legal status.
