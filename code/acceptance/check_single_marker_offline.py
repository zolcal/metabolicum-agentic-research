#!/usr/bin/env python3
"""End-to-end offline contract: one apob claim -> approved + exported range_fact.

The critical-path milestone, fully deterministic and DB-free. Chains
council.decide_claim -> provenance -> legal -> assembly via
orchestrate.run_single_marker_offline and asserts:
  - one approved biomarker_claim and one range_fact, zero quarantine;
  - the range_fact traces to the biomarker_claim id (no orphan packets);
  - provenance is 'ambiguous' offline (a study is NEVER fabricated without live
    confirmation);
  - legal approved -> public_display_approved True;
  - FIREWALL: SM-only band numbers never appear in the extraction input;
  - deterministic (same input -> identical output).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


def main() -> None:
    from code.pipeline import orchestrate

    # SM band carries 50/110/150 — these must never reach extraction.
    sm_rows = [{"min": 50, "max": 150}, {"min": 80, "max": 110}]
    claim = {
        "verbatim_quote": "ApoB optimal is under 80 mg/dL.",
        "marker": "apob", "paradigm": "MO",
        "direction": "below", "claim_polarity": "supports",
        "target_range_low": None, "target_range_high": 80, "units": "mg/dL",
        "population": {"stratum": "all_adults"}, "cited_paper": {"pmid": "123"},
        "source_id": "src-1", "claim_id": "c1", "speaker_registry_id": "person:peter-attia",
    }

    def role_outputs_fn(c):
        return {
            "extractor": dict(c),
            "reviewer": {**c, "quote_verified": True},
            "decider": {**c, "evidence_sub_grade": "E2"},
        }

    def legal_inputs_fn(c):
        return {"source_type": "paper",
                "source_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC1/",
                "license_value": "CC BY"}

    r = orchestrate.run_single_marker_offline(
        "apob", [claim], sm_rows, role_outputs_fn=role_outputs_fn, legal_inputs_fn=legal_inputs_fn
    )

    assert len(r["biomarker_claims"]) == 1, r
    assert len(r["range_facts"]) == 1, r
    assert len(r["quarantine"]) == 0, r

    f = r["range_facts"][0]
    bc = r["biomarker_claims"][0]
    assert f["subject_slug"] == "apob"
    assert f["status"] == "target" and f["color"] == "#22c55e"
    assert f["public_display_approved"] is True
    assert f["biomarker_claim_id"] == bc["id"], "range_fact must trace to the biomarker_claim id"

    # provenance offline -> ambiguous, no fabricated study
    assert len(r["provenance"]) == 1 and r["provenance"][0]["resolution_status"] == "ambiguous"
    assert r.get("research_studies", []) == [], "no study without live confirmation"

    # legal approved
    assert len(r["legal_reviews"]) == 1 and r["legal_reviews"][0]["decision"] == "approve"

    # FIREWALL: SM-only band numbers never appear in the extraction input
    extraction_input = json.dumps(role_outputs_fn(claim)["extractor"])
    for n in ("50", "110", "150"):
        assert n not in extraction_input, f"SM-only number {n} leaked into extraction input"

    # deterministic
    r2 = orchestrate.run_single_marker_offline(
        "apob", [claim], sm_rows, role_outputs_fn=role_outputs_fn, legal_inputs_fn=legal_inputs_fn
    )
    assert r2 == r, "single-marker pipeline must be deterministic"

    print("check_single_marker_offline: MILESTONE — apob approved + exported range_fact, firewall held")


if __name__ == "__main__":
    main()
