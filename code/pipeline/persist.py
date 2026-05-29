"""Persist a single-marker pipeline result to Supabase via DBClient.

FK-safe write order: biomarker_claims and research_studies first (FK targets),
then provenance / legal_reviews / claim_envelope_evaluations that reference them,
then quarantine. `dry_run` makes no writes but reports the planned counts. The db
object is any DBClient (real or fake) exposing the Stage 3-6 insert helpers.
"""

from __future__ import annotations

from typing import Any

# (result key, db method) in FK-safe order
_WRITES = [
    ("biomarker_claims", "insert_biomarker_claim"),
    ("research_studies", "upsert_research_study"),
    ("provenance", "insert_provenance"),
    ("legal_reviews", "insert_legal_review"),
    ("claim_envelope_evaluations", "insert_claim_envelope_evaluation"),
    ("quarantine", "insert_quarantine"),
]


def persist_marker_result(db: Any, result: dict, *, dry_run: bool = False) -> dict[str, Any]:
    """Write a marker result's rows through `db`. Returns {dry_run, counts, written}."""
    counts = {key: len(result.get(key, []) or []) for key, _ in _WRITES}
    if dry_run:
        return {"dry_run": True, "counts": counts, "written": 0}

    written = 0
    for key, method in _WRITES:
        writer = getattr(db, method)
        for row in result.get(key, []) or []:
            writer(row)
            written += 1
    return {"dry_run": False, "counts": counts, "written": written}
