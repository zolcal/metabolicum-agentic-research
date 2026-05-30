#!/usr/bin/env python3
"""Contract for the live council I/O layer (code/pipeline/council_llm.py).

No DB, no network, no LLM. Asserts the firewall on the prompt inputs (the 04a
extractor input carries NO SM anchors/numbers; 04b/04c inputs do), and that
map_role_outputs bridges raw LLM role outputs into the shape council.decide_claim
consumes so the live council reuses the verified deterministic decision core.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


def main() -> None:
    from code.pipeline import council, council_llm

    claim = {
        "marker": "apob", "paradigm": "MO", "verbatim_quote": "ApoB optimal is under 80 mg/dL.",
        "direction": "below", "claim_polarity": "supports",
        "target_range_low": None, "target_range_high": 80, "units": "mg/dL",
        "claim_id": "c1", "source_id": "src-1", "speaker_registry_id": "person:peter-attia",
    }
    source = {"source_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC1/",
              "transcript_text": "Attia: ApoB optimal is under 80 mg/dL."}
    sm_rows = [{"min": 50, "max": 150}, {"min": 80, "max": 110}]  # SM-only numbers 50/110/150

    # 1) FIREWALL — 04a extractor input carries no SM keys/numbers
    ext_in = council_llm.build_extractor_input(claim, source)
    assert "marker_recommendation" in ext_in and "source_artifact" in ext_in
    for k in ("sm_anchor_rows", "research_target_envelopes", "sm_min", "sm_max"):
        assert k not in ext_in
    ext_text = json.dumps(ext_in)
    for n in ("50", "110", "150"):
        assert n not in ext_text, f"SM-only number {n} leaked into the extractor input"

    # 2) 04b/04c inputs DO carry the SM rows (council-only)
    rev_in = council_llm.build_reviewer_input(
        claim, {"verbatim_quote": claim["verbatim_quote"], "marker": "apob"}, sm_rows, source=source)
    assert rev_in["sm_anchor_rows"] == sm_rows
    dec_in = council_llm.build_decider_input(
        claim, {"marker": "apob"}, {"verbatim_quote_verified": True}, sm_rows)
    assert dec_in["sm_anchor_rows"] == sm_rows
    assert "council_extractor_output" in dec_in and "council_reviewer_output" in dec_in

    # 3) map_role_outputs bridges LLM outputs -> decide_claim shape; reuse the
    #    verified deterministic decision core.
    ext_out = {"verbatim_quote": claim["verbatim_quote"], "marker": "apob", "paradigm": "MO"}
    rev_out = {"verbatim_quote_verified": True,
               "primary_envelope_alignment_status": "narrower_than_envelope"}
    dec_out = {"decision": "approve", "evidence_sub_grade": "E2", "paradigm_assigned": "MO"}
    ro = council_llm.map_role_outputs(claim, ext_out, rev_out, dec_out)
    assert set(ro) == {"extractor", "reviewer", "decider"}
    assert ro["reviewer"]["quote_verified"] is True
    assert ro["decider"]["evidence_sub_grade"] == "E2"

    outcome = council.decide_claim(claim, ro, sm_rows, source_id="src-1")
    assert outcome["outcome"] == "approved"
    assert outcome["biomarker_claim_row"]["evidence_sub_grade"] == "E2"

    # decider quarantine maps through to a non-verified/disagreeing decision
    ro_q = council_llm.map_role_outputs(
        claim, ext_out, {"verbatim_quote_verified": False}, {"decision": "quarantine"})
    assert ro_q["reviewer"]["quote_verified"] is False
    assert council.decide_claim(claim, ro_q, sm_rows, source_id="src-1")["outcome"] == "quarantined"

    print("check_council_llm_contract: all assertions passed")


if __name__ == "__main__":
    main()
