#!/usr/bin/env python3
"""DB-free contract check for the Stage 3 council deterministic core.

No DB, no network, no LLM. Exercises the pure functions in
code/pipeline/council.py and asserts row builders are strict column-subsets of
supabase/migrations/0001_initial.sql with valid enums. The two judgment rules
(consensus score, envelope geometry) are pinned here as explicit, reviewable
cases — not buried in implementation.
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from code.acceptance.check_db_helpers_contract import (  # noqa: E402
    assert_subset,
    enum_values,
)


def main() -> None:
    from code.pipeline import council

    # 1) verbatim_present — whitespace-normalized substring (the #1 council gate)
    assert council.verbatim_present("ApoB under 80", "the ApoB   under\n80 mg/dL") is True
    assert council.verbatim_present("ApoB under 80", "nothing relevant here") is False

    # 2) council_consensus_score — fraction of the 3 roles agreeing with the
    #    Stage-2 claim on (normalized quote, marker, paradigm). No prompt emits
    #    this; the rule is defined here.
    s2 = {"verbatim_quote": "q", "marker": "apob", "paradigm": "MO"}
    agree = {"verbatim_quote": "q", "marker": "apob", "paradigm": "MO"}
    disagree = {"verbatim_quote": "q", "marker": "apob", "paradigm": "RC"}
    assert council.council_consensus_score(s2, agree, agree, agree) == 1.0
    mid = council.council_consensus_score(s2, agree, agree, disagree)
    assert 0.66 <= mid <= 0.67, mid
    assert council.council_consensus_score(s2, disagree, disagree, disagree) == 0.0

    # 3) evaluate_envelope_alignment — geometric overlap vs the SM band
    #    (council-only; SM band = [min(mins), max(maxes)] across resolved rows).
    sm_rows = [{"min": 80, "max": 110}, {"min": 50, "max": 150}]  # band [50,150]
    inside = council.evaluate_envelope_alignment(
        {"target_range_low": 60, "target_range_high": 90}, sm_rows
    )
    assert inside["alignment_status"] == "narrower_than_envelope"
    assert inside["alignment_status"] in enum_values("claim_envelope_evaluations", "alignment_status")
    assert inside["paradigm_divergence_flag"] in {"none", "moderate", "extreme"}

    wider = council.evaluate_envelope_alignment(
        {"target_range_low": 20, "target_range_high": 200}, sm_rows
    )
    assert wider["alignment_status"] == "wider_than_envelope"

    contra = council.evaluate_envelope_alignment(
        {"target_range_low": 200, "target_range_high": 300}, sm_rows
    )
    assert contra["alignment_status"] == "contradictory"
    assert contra["paradigm_divergence_flag"] == "extreme"

    nocmp = council.evaluate_envelope_alignment(
        {"target_range_low": None, "target_range_high": None}, sm_rows
    )
    assert nocmp["alignment_status"] == "not_comparable"
    assert council.evaluate_envelope_alignment(
        {"target_range_low": 60, "target_range_high": 90}, []
    )["alignment_status"] == "not_comparable"

    # 4) build_biomarker_claim_row — strict subset of biomarker_claims, approved,
    #    never sets the GENERATED evidence_grade column.
    s2_claim = {
        "verbatim_quote": "ApoB optimal under 80 mg/dL",
        "marker": "apob", "paradigm": "MO",
        "target_range_low": None, "target_range_high": 80, "units": "mg/dL",
        "direction": "below", "claim_polarity": "supports",
        "speaker_or_author": "Peter Attia", "speaker_registry_id": "person:peter-attia",
        "cited_paper": {"pmid": "123"}, "population": {"stratum": "all_adults"},
        "claim_id": "claim-1",
    }
    row = council.build_biomarker_claim_row(
        s2_claim,
        {"decision": "approve", "evidence_sub_grade": "E2"},
        source_id="src-1",
        council_consensus_score=1.0,
        alignment={"alignment_status": "narrower_than_envelope",
                   "paradigm_divergence_flag": "moderate", "envelope_id": None},
        financial_conflict=(False, "generic"),
    )
    assert_subset("biomarker_claims", row)
    assert "evidence_grade" not in row, "evidence_grade is GENERATED — never insert it"
    assert row["approval_status"] == "approved"
    assert row["marker"] == "apob" and row["paradigm"] == "MO"
    assert row["verbatim_quote"], "verbatim_quote is NOT NULL"
    assert row["evidence_sub_grade"] in enum_values("biomarker_claims", "evidence_sub_grade")
    assert row["primary_envelope_alignment_status"] in enum_values(
        "biomarker_claims", "primary_envelope_alignment_status"
    )
    assert 0.0 <= row["council_consensus_score"] <= 1.0

    # 5) build_quarantine_row — council disagreement path
    q = council.build_quarantine_row(
        s2_claim,
        rejection_stage="decider",
        rejection_reason="material disagreement on paradigm",
        rejection_codes=["council_disagreement"],
        source_id="src-1",
    )
    assert_subset("quarantine", q)
    assert q["rejection_stage"] in enum_values("quarantine", "rejection_stage")
    assert "council_disagreement" in q["rejection_codes"]

    print("check_council_contract: all assertions passed")


if __name__ == "__main__":
    main()
