#!/usr/bin/env python3
"""Offline per-wave dry-run gate (the Step-8 acceptance over a real wave).

Runs orchestrate.run_wave_offline on the committed wave-0 briefs with one
injected apob claim. Asserts all 5 markers are processed, the firewall holds for
every marker (discovery payload carries no SM-bearing keys), apob yields a
traceable range_fact, markers with no claims still process cleanly, and the whole
wave run is deterministic. $0 — no DB, no network, no LLM.
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


def main() -> None:
    from code.pipeline import orchestrate

    claim = {
        "verbatim_quote": "ApoB optimal is under 80 mg/dL.",
        "marker": "apob", "paradigm": "MO",
        "direction": "below", "claim_polarity": "supports",
        "target_range_low": None, "target_range_high": 80, "units": "mg/dL",
        "population": {"stratum": "all_adults"}, "cited_paper": {"pmid": "123"},
        "source_id": "src-1", "claim_id": "c1", "speaker_registry_id": "person:peter-attia",
    }

    def role_outputs_fn(c):
        return {"extractor": dict(c), "reviewer": {**c, "quote_verified": True},
                "decider": {**c, "evidence_sub_grade": "E2"}}

    def legal_inputs_fn(c):
        return {"source_type": "paper",
                "source_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC1/", "license_value": "CC BY"}

    kwargs = dict(claims_by_marker={"apob": [claim]},
                  role_outputs_fn=role_outputs_fn, legal_inputs_fn=legal_inputs_fn)
    res = orchestrate.run_wave_offline("wave-0", **kwargs)
    s = res["summary"]

    assert s["markers_processed"] == 5, f"wave-0 has 5 markers, got {s['markers_processed']}"
    assert s["firewall_ok"] is True, "discovery payload leaked an SM-bearing key"
    assert s["range_facts"] >= 1

    apob = res["markers"]["apob"]
    assert len(apob["biomarker_claims"]) == 1 and len(apob["range_facts"]) == 1
    assert apob["range_facts"][0]["biomarker_claim_id"] == apob["biomarker_claims"][0]["id"]

    # a marker with no injected claims still processes cleanly with no facts
    assert "hba1c" in res["markers"]
    assert res["markers"]["hba1c"]["range_facts"] == []
    assert res["markers"]["hba1c"]["quarantine"] == []

    # deterministic
    assert orchestrate.run_wave_offline("wave-0", **kwargs) == res, "wave run must be deterministic"

    print(f"check_orchestrator_dryrun: wave-0 dry-run green — "
          f"{s['markers_processed']} markers, {s['range_facts']} range_facts, firewall_ok={s['firewall_ok']}")


if __name__ == "__main__":
    main()
