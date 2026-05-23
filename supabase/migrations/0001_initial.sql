-- metabolicum-agentic-research initial schema
-- Source of truth: docs/agentic-workflow/04-research-agents-spec.md (post-2026-05-22 precision fixes)
-- Executable in order. Two cross-table foreign keys whose targets are declared
-- later in the block (biomarker_claims.primary_envelope_id and
-- citation_edges.cited_study_id) are attached via ALTER TABLE at the end.

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
    )),
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
    eu_database_flag boolean,
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

CREATE TABLE provenance (
    id uuid PRIMARY KEY,
    biomarker_claim_id uuid REFERENCES biomarker_claims(id),
    edge_type text CHECK (edge_type IN ('surface_to_paper', 'paper_to_pmid', 'paper_to_doi')),
    source_locator text,
    target_locator text,
    research_study_id uuid REFERENCES research_studies(id),
    confidence float CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
    resolution_status text CHECK (resolution_status IN ('resolved', 'ambiguous', 'unresolvable')),
    resolved_at timestamptz,
    resolver_agent text
);

CREATE INDEX idx_provenance_claim ON provenance(biomarker_claim_id);
CREATE INDEX idx_provenance_study ON provenance(research_study_id);
CREATE INDEX idx_provenance_status ON provenance(resolution_status);

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
