#!/usr/bin/env python3
"""Contract for run_legal_review — deterministic hard pre-gates + LLM reviewer.

No network. A fake reviewer_caller stands in for the LLM legal reviewer. Asserts
hard-gate failures short-circuit WITHOUT calling the LLM (reject/quarantine), and
rows that clear the hard gates get the LLM's final decision; the review row is a
valid legal_reviews subset either way.
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from code.acceptance.check_db_helpers_contract import assert_subset, enum_values  # noqa: E402


def main() -> None:
    from code.pipeline import legal

    claim = {"verbatim_quote": "ApoB optimal is under 80 mg/dL.", "marker": "apob"}
    calls = []

    def make_caller(decision):
        def caller(role, system, user):
            calls.append(role)
            return {"decision": decision, "rationale": f"LLM says {decision}",
                    "feist_compilation_risk": "low", "reviewer_model": "dashscope-qwen-max"}
        return caller

    # hard-gate reject (shadow library) -> reject WITHOUT calling the LLM
    calls.clear()
    r = legal.run_legal_review(claim, source_url="https://libgen.is/x", license_value=None,
                               reviewer_caller=make_caller("approve"), biomarker_claim_id="bc-1")
    assert r["decision"] == "reject" and r["called_llm"] is False
    assert_subset("legal_reviews", r["legal_review_row"])

    # cleared hard gates + LLM approve -> approve (LLM called)
    calls.clear()
    r2 = legal.run_legal_review(claim, source_type="paper",
                                source_url="https://pmc.ncbi.nlm.nih.gov/articles/PMC1/", license_value="CC BY",
                                reviewer_caller=make_caller("approve"), biomarker_claim_id="bc-1")
    assert r2["decision"] == "approve" and r2["called_llm"] is True
    assert "legal_reviewer" in calls
    assert_subset("legal_reviews", r2["legal_review_row"])
    assert r2["legal_review_row"]["decision"] in enum_values("legal_reviews", "decision")

    # cleared hard gates + LLM quarantine -> quarantine (LLM authoritative downgrade)
    r3 = legal.run_legal_review(claim, source_type="paper",
                                source_url="https://pmc.ncbi.nlm.nih.gov/articles/PMC1/", license_value="CC BY",
                                reviewer_caller=make_caller("quarantine"), biomarker_claim_id="bc-1")
    assert r3["decision"] == "quarantine" and r3["called_llm"] is True

    print("check_legal_live_contract: all assertions passed")


if __name__ == "__main__":
    main()
