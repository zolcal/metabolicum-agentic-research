# Provenance and chain of evidence

Every claim entering the research database carries an auditable chain of evidence with three links. The first link is the public surface itself — the X post, YouTube video, podcast episode, blog post, or Telegram post — captured as URL plus retrieval timestamp plus verbatim quote, and stored in the `sources` table. The second link is the cited paper, optional, capturing what the speaker referenced; this can be partial, such as "a 2019 Lancet paper," or full, with DOI. The third link is the ingested canonical reference, which is the PMID or DOI resolved to a structured PubMed or PMC record, with the abstract always available and the full text available only where the paper is in the PMC Open Access Commercial-Use-Allowed subset under a permissive Creative Commons license.

The provenance agent runs after the council and before the legal vet. Its tools are the PubMed E-utilities (free, from NIH), the DOI resolver (doi.org), the PMC FTP service for OA-subset full text, and the Crossref API. For each cited paper, there are three possible outcomes: resolved, meaning the PMID or DOI is confirmed; ambiguous, meaning multiple candidates exist and `biomarker_claims.provenance_status` is set to `ambiguous`; or unresolvable, meaning no match was found and `biomarker_claims.provenance_status` is set to `unresolvable`.

The PMC Open Access situation deserves careful attention because it is the boundary between what we can ingest in full and what we can only cite. Per the PMC Open Access page (retrieved 2026-05-13), the subset has three groupings: Commercial Use Allowed, covering CC0, CC BY, CC BY-SA, and CC BY-ND licenses; Non-Commercial Use Only, covering CC BY-NC and its variants; and Other, covering papers with no machine-readable Creative Commons license, no license at all, or a custom license. Per PMC's copyright notice (retrieved 2026-05-13), "Systematic downloading of batches of articles from the main PMC web site, in any way, is prohibited because of copyright restrictions. PMC makes certain subsets of articles (i.e., the PMC Article Datasets) accessible through auxiliary services that may be used for automated retrieval and downloading. These are: PMC Cloud Service, PMC OAI-PMH Service, PMC FTP Service, E-Utilities and BioC API."

`[JUDGMENT]` The conservative default is abstract-only ingestion for any paper not in the Commercial Use Allowed subset. We cite by PMID and link, not by reproducing text. We use only the PMC FTP, OAI-PMH, BioC API, or AWS RODA services for any bulk retrieval — never the main web site.

Auditability and queryability are first-class. The provenance table holds edges of the chain:

```sql
CREATE TABLE provenance (
    id uuid PRIMARY KEY,
    biomarker_claim_id uuid REFERENCES biomarker_claims(id),
    edge_type text CHECK (edge_type IN ('surface_to_paper', 'paper_to_pmid', 'paper_to_doi')),
    source_locator text,
    target_locator text,
    research_study_id uuid REFERENCES research_studies(id),
    confidence float,
    resolution_status text CHECK (resolution_status IN ('resolved', 'ambiguous', 'unresolvable')),
    resolved_at timestamptz,
    resolver_agent text
);
```

A query like "show me claims whose evidence chain reaches a peer-reviewed PMID" is one SQL join. Reverse traversal — finding all claims that derive from a particular paper — is equally simple. `research_study_id` is populated when a resolved PMID or DOI has a canonical `research_studies` row; `target_locator` remains for ambiguous or unresolved edges. The `biomarker_claim_id` here refers to the BiomarkerClaim row produced post-council, not the pre-council extraction row in the `claims` table.
