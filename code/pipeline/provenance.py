"""Stage 4 provenance — deterministic core.

Parses citation locators (PMID/DOI) off post-council biomarker_claims and builds
provenance edges + research_studies rows. The live PubMed/Crossref confirmation
(network) is layered on top of these pure helpers in a later increment.

Anti-fabrication rule (Session-34: 64% of LLM-assigned PMIDs were fabricated):
a research_study is NEVER created from an unconfirmed locator or without a
live-confirmed title. A parsed-but-unconfirmed locator is `ambiguous`, never
`resolved`; a claim with no locator is `unresolvable`.
"""

from __future__ import annotations

import re
from typing import Any


def _slugify(s: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s.lower())).strip("-")


def extract_locator(cited_paper: dict | None) -> dict[str, Any]:
    """Parse a cited_paper jsonb into a locator. PMID takes precedence over DOI."""
    cp = cited_paper or {}
    pmid = cp.get("pmid")
    doi = cp.get("doi")
    if pmid:
        return {"kind": "pmid", "value": str(pmid),
                "target_locator": f"pmid:{pmid}", "edge_type": "paper_to_pmid"}
    if doi:
        return {"kind": "doi", "value": str(doi),
                "target_locator": f"doi:{doi}", "edge_type": "paper_to_doi"}
    return {"kind": "none", "value": None, "target_locator": None, "edge_type": "surface_to_paper"}


def slug_for_study(pmid: str | None, doi: str | None, title: str | None) -> str:
    """Deterministic study slug; PMID preferred, then DOI, then title."""
    if pmid:
        return f"pmid-{pmid}"
    if doi:
        return f"doi-{_slugify(doi)}"
    if title:
        return _slugify(title)
    raise ValueError("cannot derive a study slug without pmid, doi, or title")


def classify_resolution(locator: dict, *, confirmed: bool) -> str:
    """Map a locator + live-confirmation flag to a provenance resolution_status.

    No locator -> 'unresolvable'. Parsed but not live-confirmed -> 'ambiguous'
    (do NOT write a study). Live-confirmed -> 'resolved'.
    """
    if locator["kind"] == "none":
        return "unresolvable"
    return "resolved" if confirmed else "ambiguous"


def build_provenance_row(
    *,
    biomarker_claim_id: str,
    locator: dict,
    resolution_status: str,
    research_study_id: str | None = None,
    source_locator: str | None = None,
    confidence: float | None = None,
    resolver_agent: str = "provenance",
) -> dict[str, Any]:
    """Build a `provenance` edge row (id/resolved_at stamped by the DB layer)."""
    return {
        "biomarker_claim_id": biomarker_claim_id,
        "edge_type": locator["edge_type"],
        "source_locator": source_locator,
        "target_locator": locator["target_locator"],
        "research_study_id": research_study_id,
        "confidence": confidence,
        "resolution_status": resolution_status,
        "resolver_agent": resolver_agent,
    }


def build_research_study_row(*, locator: dict, metadata: dict | None) -> dict[str, Any]:
    """Build a `research_studies` row from a CONFIRMED locator + live metadata.

    Refuses (ValueError) without a resolvable PMID/DOI locator or a real title —
    never fabricates a study. `evidence_grade` is GENERATED and never set.
    """
    if locator["kind"] not in ("pmid", "doi"):
        raise ValueError("cannot build a research_study without a resolvable PMID or DOI locator")
    meta = metadata or {}
    title = meta.get("title")
    if not title:
        raise ValueError("refusing to build a research_study without a live-confirmed title (anti-fabrication)")

    pmid = locator["value"] if locator["kind"] == "pmid" else meta.get("pmid")
    doi = locator["value"] if locator["kind"] == "doi" else meta.get("doi")
    row: dict[str, Any] = {
        "slug": slug_for_study(pmid, doi, title),
        "pmid": pmid,
        "doi": doi,
        "original_title": title,
        "authors_short": meta.get("authors_short"),
        "journal": meta.get("journal"),
        "publication_year": meta.get("year"),
        "study_type": meta.get("study_type"),
        "pubmed_url": meta.get("pubmed_url"),
        "doi_url": meta.get("doi_url"),
        "auto_graded": True,
        "status": "draft",
    }
    return {k: v for k, v in row.items() if v is not None}
