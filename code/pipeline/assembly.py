"""Stage 6 assembly — deterministic §18 range_fact projection.

Projects APPROVED biomarker_claims into §18 range_facts. No LLM, no reinterpretation:
status is derived from direction + claim_polarity + bounds (§18 rules), color from
range_color_policy.canonical_color(status), and every range_fact carries the
biomarker_claim_id it came from. refutes claims emit no range_fact. The export
surface is `range_facts`, not the legacy `paradigm_ranges`.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from code import range_color_policy

_SOURCE_FAMILIES = {"pubmed", "pmc", "doi", "guideline", "practitioner_surface",
                    "podcast", "video", "blog", "social"}

_PARADIGM_LABEL = {
    "SM": "standard-medical",
    "RC": "research-consensus",
    "MO": "metabolic-optimization",
}


def paradigm_label(paradigm: str | None) -> str | None:
    return _PARADIGM_LABEL.get(paradigm)


def derive_status(
    *,
    direction: str | None,
    claim_polarity: str | None,
    target_range_low: float | None,
    target_range_high: float | None,
    target_value: float | None,
    paradigm: str | None,
) -> str | None:
    """§18 status-derivation. Returns a status alias or None when no range_fact
    should be emitted (refutes; or an unmappable shape held back for the report)."""
    if claim_polarity == "refutes":
        return None
    # one-sided bound, expressed either as target_range_* or as target_value+direction
    # (the extractor's native shape, e.g. "ApoB below 60" -> target_value=60)
    if direction == "below" and target_range_low is None and (
        target_range_high is not None or target_value is not None
    ):
        return "target"
    if direction == "above" and target_range_high is None and (
        target_range_low is not None or target_value is not None
    ):
        return "target"
    if direction == "between" and target_range_low is not None and target_range_high is not None:
        return "optimal" if paradigm == "MO" else "normal"
    if direction == "at" and target_value is not None:
        return "target"
    if claim_polarity == "qualifies" and (
        target_range_low is not None or target_range_high is not None or target_value is not None
    ):
        return "target"
    return None  # unmappable -> caller holds it back (never invent a status)


def build_range_fact(
    bc: dict,
    *,
    biomarker_claim_id: str,
    range_order: int,
    range_version: str = "v1",
    entity_type: str = "marker",
) -> dict[str, Any] | None:
    """Project one approved biomarker_claims row into a §18 range_fact dict, or
    None when no range_fact should be emitted."""
    status = derive_status(
        direction=bc.get("direction"),
        claim_polarity=bc.get("claim_polarity", "supports"),
        target_range_low=bc.get("target_range_low"),
        target_range_high=bc.get("target_range_high"),
        target_value=bc.get("target_value"),
        paradigm=bc.get("paradigm"),
    )
    if status is None:
        return None

    direction, tv = bc.get("direction"), bc.get("target_value")
    lo, hi = bc.get("target_range_low"), bc.get("target_range_high")
    if direction == "at" and tv is not None:
        lo = hi = tv
    elif direction == "below" and hi is None and tv is not None:
        hi = tv   # one-sided upper bound -> min:null, max:tv
    elif direction == "above" and lo is None and tv is not None:
        lo = tv   # one-sided lower bound -> min:tv, max:null

    pop = bc.get("population") or {}
    sub_grade = bc.get("evidence_sub_grade")
    public_ok = bc.get("legal_status") == "approved" and bc.get("approval_status") == "approved"
    cited = bc.get("cited_paper") or {}

    return {
        "subject_slug": bc["marker"],
        "entity_type": entity_type,
        "paradigm": paradigm_label(bc.get("paradigm")),
        "range_version": range_version,
        "range_order": range_order,
        "min_value": lo,
        "max_value": hi,
        "unit": bc.get("units"),
        "status": status,
        "color": range_color_policy.canonical_color(status),
        "gender": pop.get("gender"),
        "sex_for_lab_reference": pop.get("sex_for_lab_reference") or pop.get("sex"),
        "stratum": pop.get("stratum"),
        "age_min": pop.get("age_min"),
        "age_max": pop.get("age_max"),
        "evidence_sub_grade": sub_grade,
        "evidence_grade": sub_grade[0] if sub_grade else None,
        "review_status": bc.get("approval_status"),
        "public_display_approved": public_ok,
        "source_ids": [bc["source_id"]] if bc.get("source_id") else [],
        "biomarker_claim_id": biomarker_claim_id,
        "provenance": {
            "verbatim_quote": bc.get("verbatim_quote"),
            "source_pmid": cited.get("pmid"),
            "source_doi": cited.get("doi"),
        },
    }


# ── §18 MO export projection (revised-A: deterministic, no LLM) ────────

def _source_family(source_type: str | None) -> str:
    st = (source_type or "").lower()
    return st if st in _SOURCE_FAMILIES else "other"


def _supports_bound(rf: dict) -> str:
    lo, hi = rf.get("min_value"), rf.get("max_value")
    if lo is not None and hi is not None:
        return "value" if lo == hi else "both"
    if hi is not None:
        return "max"
    if lo is not None:
        return "min"
    return "none"


def _content_hash(content: dict) -> str:
    return hashlib.sha256(json.dumps(content, sort_keys=True, default=str).encode()).hexdigest()


def _prune(obj: Any) -> Any:
    """Recursively drop None values, empty dicts, and empty lists so the export
    carries only fields that actually have data — no null/{}/[] placeholder litter."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            pv = _prune(v)
            if pv is None or pv == {} or pv == []:
                continue
            out[k] = pv
        return out
    if isinstance(obj, list):
        return [pv for pv in (_prune(x) for x in obj) if pv not in (None, {}, [])]
    return obj


def build_marker_export(
    marker: str,
    result: dict,
    source_fixtures: dict[str, dict] | None = None,
    *,
    batch_slug: str | None = None,
    generated_at: str | None = None,
    marker_type: str = "marker",
    language: str = "en",
    extra_sections: list[dict] | None = None,
) -> dict[str, Any]:
    """Deterministic §18 MO export object for one marker (revised-A scope).

    Projects the pipeline result + source fixtures into the export contract — no
    LLM, no reinterpretation: range_facts (already built), range_source_artifacts,
    range_fact_sources, deterministic content sections (evidence_badge, references),
    research_studies, research_citations. `extra_sections` lets Stage-B inject the
    MO-specific prose sections (interpretation/limitations). Translations are NOT
    produced here — MetaSync localizes after ingestion. paradigm_thresholds is NOT
    produced — it is a downstream cross-paradigm render of range_facts.
    """
    source_fixtures = source_fixtures or {}
    claims = result.get("biomarker_claims", []) or []
    range_facts = result.get("range_facts", []) or []
    studies = result.get("research_studies", []) or []
    rejected = result.get("rejection_log") or result.get("quarantine") or []

    # one source_artifact per source referenced by an approved claim
    source_artifacts, seen = [], []
    for sid in (c.get("source_id") for c in claims):
        if not sid or sid in seen:
            continue
        seen.append(sid)
        fx = source_fixtures.get(sid, {})
        pub = fx.get("published_at") or ""
        source_artifacts.append({
            "source_id": sid,
            "source_family": _source_family(fx.get("source_type")),
            "source_url": fx.get("source_url"),
            "source_title": fx.get("title"),
            "source_authors": fx.get("speaker_or_author"),
            "source_year": pub[:4] if isinstance(pub, str) and len(pub) >= 4 else None,
            "source_license": fx.get("license"),
            "raw_artifact_ref": None,
            "raw_sha256": fx.get("transcript_sha256"),
            "retrieved_at": fx.get("retrieved_at"),
            "review_status": "unreviewed",
            "evidence_grade": None,
            "source_quality": None,
            "source_bounds": {"supports_min": None, "supports_max": None, "supports_value": None},
            "provenance": {},
        })

    range_fact_sources = [
        {"range_order": rf.get("range_order"), "source_id": sid,
         "source_role": "supports_range", "supports_bound": _supports_bound(rf),
         "evidence_grade": rf.get("evidence_grade")}
        for rf in range_facts for sid in (rf.get("source_ids") or [])
    ]

    # deterministic content sections: evidence_badge + references
    content_sections = []
    graded = sorted(c["evidence_sub_grade"] for c in claims if c.get("evidence_sub_grade"))
    sub = graded[0] if graded else None
    speakers = sorted({c.get("speaker_or_author") for c in claims if c.get("speaker_or_author")})
    if claims:
        badge = {
            "grade": sub[0] if sub else None, "sub_grade": sub, "label": None,
            "rationale": (f"{len(claims)} council-approved, legal-cleared MO claim(s) from "
                          f"{', '.join(speakers) or 'practitioner sources'}; graded {sub or 'ungraded'}."),
        }
        content_sections.append({
            "marker_slug": marker, "marker_type": marker_type, "language": language,
            "section_type": "evidence_badge", "section_order": 1, "paradigm": "metabolic-optimization",
            "content": badge, "source_type": "pipeline", "evidence_grade": sub[0] if sub else None,
            "source_url": None, "content_hash": _content_hash(badge), "status": "draft", "version": 1,
        })
    for s in (extra_sections or []):  # Stage-B prose (interpretation/limitations)
        content_sections.append(s)
    refs = {"title": "References", "entries": [{"citation_key": s.get("slug"), "study_slug": s.get("slug")} for s in studies]}
    content_sections.append({
        "marker_slug": marker, "marker_type": marker_type, "language": language,
        "section_type": "references", "section_order": len(content_sections) + 1,
        "paradigm": "metabolic-optimization", "content": refs, "source_type": "pipeline",
        "evidence_grade": None, "source_url": None, "content_hash": _content_hash(refs),
        "status": "draft", "version": 1,
    })

    research_citations = [
        {"study_slug": s.get("slug"), "source_page": f"/learn/markers/{marker}",
         "display_order": i + 1, "citation_context": None, "citation_key": s.get("slug")}
        for i, s in enumerate(studies)
    ]

    return _prune({
        "schema_version": "1",
        "batch": {"batch_slug": batch_slug, "paradigm": "metabolic-optimization",
                  "status": "review", "generated_at": generated_at},
        "range_facts": range_facts,
        "range_source_artifacts": source_artifacts,
        "range_fact_sources": range_fact_sources,
        "marker_content_sections": content_sections,
        "research_studies": studies,
        "research_citations": research_citations,
        "rejected_items": rejected,
    })
