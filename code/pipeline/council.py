"""Stage 3 validation council — deterministic core.

This module holds the pure, side-effect-free decision logic for the council:
verbatim grounding, consensus scoring, SM-envelope alignment, and the row
builders that project a decided claim into the `biomarker_claims` / `quarantine`
shapes (subset of supabase/migrations/0001_initial.sql).

SM-firewall note: the SM numbers reach the council ONLY via the resolved
`council/sm_alignment_reference.json` (see code/loaders/sm_reference.py). They
are passed to `evaluate_envelope_alignment` as an explicit argument here — never
to discovery or extraction. The LLM-role wiring (04a/04b/04c) is layered on top
of these helpers in a later increment.
"""

from __future__ import annotations

import re
from typing import Any

_APPROVE_DECISIONS = {"approve", "approve_with_modification"}


# ── Verbatim grounding ────────────────────────────────────────────────

def normalize_ws(s: str | None) -> str:
    """Collapse all whitespace runs to single spaces and strip ends."""
    return re.sub(r"\s+", " ", (s or "").strip())


def verbatim_present(quote: str, fetched_text: str) -> bool:
    """True iff `quote` appears in `fetched_text` after whitespace normalization."""
    if not quote:
        return False
    return normalize_ws(quote) in normalize_ws(fetched_text)


# ── Consensus scoring ─────────────────────────────────────────────────

def _agrees(stage2: dict, role: dict) -> bool:
    return (
        normalize_ws(role.get("verbatim_quote")) == normalize_ws(stage2.get("verbatim_quote"))
        and role.get("marker") == stage2.get("marker")
        and role.get("paradigm") == stage2.get("paradigm")
    )


def council_consensus_score(stage2: dict, *role_outputs: dict) -> float:
    """Fraction of council role outputs agreeing with the Stage-2 claim on
    (normalized quote, marker, paradigm). No prompt emits this — it is defined
    here as the deterministic consensus rule. Range [0, 1]."""
    if not role_outputs:
        return 0.0
    agree = sum(1 for r in role_outputs if _agrees(stage2, r))
    return agree / len(role_outputs)


# ── SM-envelope alignment (council-only firewall comparison) ──────────

def _sm_band(sm_rows: list[dict]) -> tuple[float, float] | None:
    mins = [r["min"] for r in sm_rows if r.get("min") is not None]
    maxs = [r["max"] for r in sm_rows if r.get("max") is not None]
    if not mins or not maxs:
        return None
    return min(mins), max(maxs)


def evaluate_envelope_alignment(claim: dict, sm_rows: list[dict]) -> dict[str, Any]:
    """Classify an already-extracted claim against the SM band.

    Geometric MVP: SM band = [min(mins), max(maxs)] across resolved SM rows;
    overlap geometry decides the `alignment_status`. Tolerance-band tuning is a
    separate decision (left to council review). Returns alignment_status (the
    §04 5-value enum), a paradigm_divergence_flag, and a denormalized
    primary_envelope_alignment_status for the claim row.
    """
    band = _sm_band(sm_rows or [])
    lo = claim.get("target_range_low")
    hi = claim.get("target_range_high")
    if lo is None and hi is None:
        tv = claim.get("target_value")
        if tv is not None:
            lo = hi = tv

    if band is None or (lo is None and hi is None):
        return {
            "alignment_status": "not_comparable",
            "paradigm_divergence_flag": "none",
            "primary_envelope_alignment_status": "not_comparable",
            "envelope_id": None,
        }

    sm_lo, sm_hi = band
    clo = lo if lo is not None else sm_lo  # one-sided claims bounded by SM on the open side
    chi = hi if hi is not None else sm_hi

    if chi < sm_lo or clo > sm_hi:
        status, flag = "contradictory", "extreme"
    elif clo >= sm_lo and chi <= sm_hi:
        status, flag = "narrower_than_envelope", "none"  # MO tighter than SM is expected
    elif clo <= sm_lo and chi >= sm_hi:
        status, flag = "wider_than_envelope", "moderate"
    else:
        status, flag = "aligned", "none"

    return {
        "alignment_status": status,
        "paradigm_divergence_flag": flag,
        "primary_envelope_alignment_status": status,
        "envelope_id": None,
    }


# ── Row builders (project into the migration shapes) ──────────────────

def build_biomarker_claim_row(
    stage2_claim: dict,
    decision: dict,
    *,
    source_id: str,
    council_consensus_score: float,
    alignment: dict,
    financial_conflict: tuple[bool, str] = (False, "generic"),
) -> dict[str, Any]:
    """Project a decided claim into a `biomarker_claims` row (content columns only).

    `id`/`created_at`/`updated_at` are stamped by DBClient.insert_biomarker_claim;
    `evidence_grade` is a GENERATED column and is never set here.
    """
    has_conflict, severity = financial_conflict
    return {
        "claim_id": stage2_claim.get("claim_id"),
        "source_id": source_id,
        "speaker_or_author": stage2_claim.get("speaker_or_author"),
        "speaker_registry_id": stage2_claim.get("speaker_registry_id"),
        "marker": stage2_claim["marker"],
        "verbatim_quote": stage2_claim["verbatim_quote"],
        "paradigm": stage2_claim.get("paradigm"),
        "target_value": stage2_claim.get("target_value"),
        "target_range_low": stage2_claim.get("target_range_low"),
        "target_range_high": stage2_claim.get("target_range_high"),
        "units": stage2_claim.get("units"),
        "direction": stage2_claim.get("direction"),
        "claim_polarity": stage2_claim.get("claim_polarity", "supports"),
        "population": stage2_claim.get("population"),
        "cited_paper": stage2_claim.get("cited_paper"),
        "evidence_sub_grade": decision["evidence_sub_grade"],
        "council_consensus_score": council_consensus_score,
        "financial_conflict_flag": has_conflict,
        "financial_conflict_severity": severity,
        "paradigm_divergence_flag": alignment.get("paradigm_divergence_flag", "none"),
        "primary_envelope_id": alignment.get("envelope_id"),
        "primary_envelope_alignment_status": alignment.get("alignment_status", "not_evaluated"),
        "provenance_status": "pending",
        "legal_status": "pending",
        "approval_status": "approved" if decision.get("decision") in _APPROVE_DECISIONS else "quarantined",
    }


def build_quarantine_row(
    stage2_claim: dict,
    *,
    rejection_stage: str,
    rejection_reason: str,
    rejection_codes: list[str],
    source_id: str | None = None,
    biomarker_claim_id: str | None = None,
    financial_conflict: tuple[bool, str] = (False, "generic"),
) -> dict[str, Any]:
    """Build a `quarantine` row for a council rejection (fail-safe path)."""
    has_conflict, severity = financial_conflict
    return {
        "source_id": source_id,
        "claim_id": stage2_claim.get("claim_id"),
        "biomarker_claim_id": biomarker_claim_id,
        "verbatim_quote": stage2_claim.get("verbatim_quote"),
        "rejection_stage": rejection_stage,
        "rejection_reason": rejection_reason,
        "rejection_codes": list(rejection_codes),
        "financial_conflict_flag": has_conflict,
        "financial_conflict_severity": severity,
    }
