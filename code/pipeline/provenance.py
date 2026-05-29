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


def resolve_locator(locator: dict, *, fetcher) -> dict[str, Any]:
    """Resolve a locator via an injected `fetcher(locator) -> metadata | None`.

    Confirmed (fetcher returns metadata with a real title) -> resolved + a
    research_study row. Otherwise -> unresolvable with NO study. The fetcher is
    not called for a missing locator. Injection keeps this testable offline; the
    live HTTP fetcher is `live_fetcher` below.
    """
    if locator["kind"] == "none":
        return {"resolution_status": "unresolvable", "metadata": None, "research_study_row": None}
    meta = fetcher(locator)
    if not meta or not meta.get("title"):
        return {"resolution_status": "unresolvable", "metadata": meta, "research_study_row": None}
    return {
        "resolution_status": "resolved",
        "metadata": meta,
        "research_study_row": build_research_study_row(locator=locator, metadata=meta),
    }


def live_fetcher(locator: dict, *, ncbi_api_key: str | None = None, mailto: str | None = None,
                 timeout: float = 15.0) -> dict[str, Any] | None:
    """Live PubMed (E-utilities) / Crossref metadata fetch. Returns None on any
    failure so resolve_locator falls back to 'unresolvable' (never fabricates).
    Used only on a live run; not exercised by the offline contracts."""
    import json as _json
    import urllib.parse
    import urllib.request

    def _get(url: str) -> dict | None:
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                return _json.loads(r.read().decode("utf-8"))
        except Exception:
            return None

    if locator["kind"] == "pmid":
        pmid = locator["value"]
        q = {"db": "pubmed", "id": pmid, "retmode": "json"}
        if ncbi_api_key:
            q["api_key"] = ncbi_api_key
        data = _get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?" + urllib.parse.urlencode(q))
        rec = (((data or {}).get("result") or {}).get(pmid)) if data else None
        if not rec or not rec.get("title"):
            return None
        year = (rec.get("pubdate") or "")[:4]
        authors = rec.get("authors") or []
        return {
            "title": rec.get("title"),
            "authors_short": (authors[0]["name"] + " et al." if authors else None),
            "journal": rec.get("fulljournalname") or rec.get("source"),
            "year": int(year) if year.isdigit() else None,
            "pubmed_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        }

    if locator["kind"] == "doi":
        doi = locator["value"]
        url = "https://api.crossref.org/works/" + urllib.parse.quote(doi)
        if mailto:
            url += "?mailto=" + urllib.parse.quote(mailto)
        data = _get(url)
        msg = (data or {}).get("message") if data else None
        title = (msg.get("title") or [None])[0] if msg else None
        if not title:
            return None
        parts = (msg.get("published-print") or msg.get("published-online") or {}).get("date-parts") or [[None]]
        return {
            "title": title,
            "authors_short": ((msg.get("author") or [{}])[0].get("family", "") + " et al.") if msg.get("author") else None,
            "journal": (msg.get("container-title") or [None])[0],
            "year": parts[0][0],
            "doi_url": f"https://doi.org/{doi}",
        }

    return None
