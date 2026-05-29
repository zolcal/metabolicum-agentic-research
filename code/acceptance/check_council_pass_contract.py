#!/usr/bin/env python3
"""Contract for run_council_pass — the live council orchestration (no real LLM).

Uses a fake role_caller that records inputs and returns canned role outputs.
Asserts: the 04a extractor input is SM-free (firewall); a verified+agreeing+
decider-approve claim is approved; and the both-must-approve rule holds — if the
LLM decider quarantines (or the reviewer fails verification), the outcome is
quarantined even when the deterministic gate would otherwise pass.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


def main() -> None:
    from code.pipeline import council_llm

    claim = {
        "marker": "apob", "paradigm": "MO", "verbatim_quote": "ApoB optimal is under 80 mg/dL.",
        "direction": "below", "claim_polarity": "supports",
        "target_range_low": None, "target_range_high": 80, "units": "mg/dL",
        "claim_id": "c1", "source_id": "src-1", "speaker_registry_id": "person:peter-attia",
    }
    source = {"source_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC1/",
              "transcript_text": "Attia: ApoB optimal is under 80 mg/dL."}
    sm_rows = [{"min": 50, "max": 150}, {"min": 80, "max": 110}]

    def make_caller(decider_decision="approve", quote_verified=True):
        calls = []

        def caller(role, system, user):
            calls.append({"role": role, "user": user})
            if role == "council_extractor":
                return {"verbatim_quote": claim["verbatim_quote"], "marker": "apob", "paradigm": "MO",
                        "source_quote_found": True}
            if role == "council_reviewer":
                return {"verbatim_quote_verified": quote_verified,
                        "primary_envelope_alignment_status": "narrower_than_envelope"}
            return {"decision": decider_decision, "evidence_sub_grade": "E2", "paradigm_assigned": "MO",
                    "verbatim_quote_verified": quote_verified}

        caller.calls = calls
        return caller

    # 1) happy path — verified + agree + decider approve => approved
    caller = make_caller()
    outcome = council_llm.run_council_pass(claim, source, sm_rows, role_caller=caller)
    assert outcome["outcome"] == "approved", outcome
    assert outcome["biomarker_claim_row"]["evidence_sub_grade"] == "E2"

    # firewall: the 04a extractor call carried no SM rows/numbers
    ext_call = next(c for c in caller.calls if c["role"] == "council_extractor")
    ext_text = json.dumps(ext_call["user"])
    assert "sm_anchor_rows" not in ext_call["user"]
    for n in ("50", "110", "150"):
        assert n not in ext_text, f"SM-only number {n} leaked into the extractor call"

    # 2) both-must-approve: decider quarantines => quarantined despite deterministic pass
    outcome_q = council_llm.run_council_pass(claim, source, sm_rows, role_caller=make_caller(decider_decision="quarantine"))
    assert outcome_q["outcome"] == "quarantined", outcome_q

    # 3) reviewer fails verbatim verification => quarantined
    outcome_v = council_llm.run_council_pass(claim, source, sm_rows, role_caller=make_caller(quote_verified=False))
    assert outcome_v["outcome"] == "quarantined", outcome_v

    print("check_council_pass_contract: all assertions passed")


if __name__ == "__main__":
    main()
