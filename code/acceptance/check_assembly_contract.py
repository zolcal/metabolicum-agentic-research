#!/usr/bin/env python3
"""DB-free contract check for the Stage 6 assembly projection (§18 range_facts).

No DB. Asserts derive_status follows the §18 status-derivation rules, build_range_fact
projects an approved biomarker_claims row into a §18 range_fact that traces back to a
biomarker_claim_id, derives color via range_color_policy, sets public_display_approved
only when legal+approval are both approved, drops refutes claims, and is deterministic.
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


def main() -> None:
    from code.pipeline import assembly
    from code import range_color_policy as rcp

    # 1) paradigm label rename (§18)
    assert assembly.paradigm_label("MO") == "metabolic-optimization"
    assert assembly.paradigm_label("SM") == "standard-medical"
    assert assembly.paradigm_label("RC") == "research-consensus"

    # 2) derive_status — §18 status-derivation rules
    ds = assembly.derive_status
    assert ds(direction="below", claim_polarity="supports", target_range_low=None,
              target_range_high=80, target_value=None, paradigm="MO") == "target"
    assert ds(direction="above", claim_polarity="supports", target_range_low=10,
              target_range_high=None, target_value=None, paradigm="MO") == "target"
    assert ds(direction="between", claim_polarity="supports", target_range_low=60,
              target_range_high=90, target_value=None, paradigm="MO") == "optimal"
    assert ds(direction="between", claim_polarity="supports", target_range_low=60,
              target_range_high=90, target_value=None, paradigm="SM") == "normal"
    assert ds(direction="at", claim_polarity="supports", target_range_low=None,
              target_range_high=None, target_value=5, paradigm="RC") == "target"
    assert ds(direction="below", claim_polarity="refutes", target_range_low=None,
              target_range_high=80, target_value=None, paradigm="MO") is None
    # one-sided bound carried in target_value + direction (extractor's native shape)
    assert ds(direction="below", claim_polarity="supports", target_range_low=None,
              target_range_high=None, target_value=60, paradigm="MO") == "target"
    assert ds(direction="above", claim_polarity="supports", target_range_low=None,
              target_range_high=None, target_value=50, paradigm="MO") == "target"

    # 3) build_range_fact — projection + traceability + color + display gate
    bc = {
        "marker": "apob", "paradigm": "MO", "direction": "below", "claim_polarity": "supports",
        "target_range_low": None, "target_range_high": 80, "target_value": None, "units": "mg/dL",
        "population": {"stratum": "all_adults", "sex": "all", "age_min": 18, "age_max": None},
        "evidence_sub_grade": "E2", "source_id": "src-1", "verbatim_quote": "ApoB under 80",
        "cited_paper": {"pmid": "123"}, "legal_status": "approved", "approval_status": "approved",
    }
    f = assembly.build_range_fact(bc, biomarker_claim_id="bc-1", range_order=1)
    assert f["subject_slug"] == "apob"
    assert f["paradigm"] == "metabolic-optimization"
    assert f["status"] == "target"
    assert f["color"] == "#22c55e" and f["color"] in set(rcp.BUCKET_TO_HEX.values())
    assert f["min_value"] is None and f["max_value"] == 80
    assert f["unit"] == "mg/dL"
    assert f["evidence_sub_grade"] == "E2" and f["evidence_grade"] == "E"
    assert f["public_display_approved"] is True
    assert f["review_status"] == "approved"
    assert f["source_ids"] == ["src-1"]
    assert f["biomarker_claim_id"] == "bc-1", "every range_fact must trace to a biomarker_claim_id"
    assert f["provenance"]["verbatim_quote"] == "ApoB under 80"
    assert f["provenance"]["source_pmid"] == "123"

    # one-sided upper bound expressed as target_value + direction='below' (Attia "ApoB < 60")
    bc_below = {**bc, "target_range_high": None, "target_value": 60, "verbatim_quote": "ApoB under 60"}
    fb = assembly.build_range_fact(bc_below, biomarker_claim_id="bc-3", range_order=2)
    assert fb is not None, "one-sided 'below' claim with bound in target_value must project"
    assert fb["min_value"] is None and fb["max_value"] == 60, fb
    assert fb["status"] == "target"
    # one-sided lower bound expressed as target_value + direction='above'
    bc_above = {**bc, "direction": "above", "target_range_high": None, "target_value": 50}
    fa = assembly.build_range_fact(bc_above, biomarker_claim_id="bc-4", range_order=3)
    assert fa is not None and fa["min_value"] == 50 and fa["max_value"] is None, fa

    # not approved -> not public-display-approved
    f2 = assembly.build_range_fact({**bc, "legal_status": "pending"}, biomarker_claim_id="bc-1", range_order=1)
    assert f2["public_display_approved"] is False

    # refutes -> no range_fact
    assert assembly.build_range_fact({**bc, "claim_polarity": "refutes"},
                                     biomarker_claim_id="bc-2", range_order=1) is None

    # deterministic
    assert assembly.build_range_fact(bc, biomarker_claim_id="bc-1", range_order=1) == f

    print("check_assembly_contract: all assertions passed")


if __name__ == "__main__":
    main()
