"""Stage 6 assembly — deterministic §18 range_fact projection.

Projects APPROVED biomarker_claims into §18 range_facts. No LLM, no reinterpretation:
status is derived from direction + claim_polarity + bounds (§18 rules), color from
range_color_policy.canonical_color(status), and every range_fact carries the
biomarker_claim_id it came from. refutes claims emit no range_fact. The export
surface is `range_facts`, not the legacy `paradigm_ranges`.
"""

from __future__ import annotations

from typing import Any

from code import range_color_policy

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
    if direction == "below" and target_range_high is not None and target_range_low is None:
        return "target"
    if direction == "above" and target_range_low is not None and target_range_high is None:
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

    lo, hi = bc.get("target_range_low"), bc.get("target_range_high")
    if bc.get("direction") == "at" and bc.get("target_value") is not None:
        lo = hi = bc.get("target_value")

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
