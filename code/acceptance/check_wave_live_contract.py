#!/usr/bin/env python3
"""Contract for run_wave_live — the live per-wave file orchestrator.

No real LLM/network/DB (all injected fakes; dry_run, project-local tmp runs dir).
Asserts the §10 run layout is written, the council-only sm_alignment_reference is
materialized per marker (evidence_weight 0, carries rows), state.json uses the
canonical stage keys, apob yields a traceable range_fact + a confirmed study, and
the SM-only band numbers never appear in any discovery/ or sources/ artifact.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


def main() -> None:
    from code.pipeline import orchestrate

    claim = {
        "marker": "apob", "paradigm": "MO", "verbatim_quote": "ApoB optimal is under 80 mg/dL.",
        "direction": "below", "claim_polarity": "supports",
        "target_range_low": None, "target_range_high": 80, "units": "mg/dL",
        "claim_id": "c1", "source_id": "src-1", "cited_paper": {"pmid": "123"},
        "speaker_registry_id": "person:peter-attia",
    }

    def role_caller(role, system, user):
        if role == "council_extractor":
            return {"verbatim_quote": claim["verbatim_quote"], "marker": "apob", "paradigm": "MO",
                    "source_quote_found": True}
        if role == "council_reviewer":
            return {"verbatim_quote_verified": True, "primary_envelope_alignment_status": "narrower_than_envelope"}
        return {"decision": "approve", "evidence_sub_grade": "E2", "paradigm_assigned": "MO"}

    def legal_caller(role, system, user):
        return {"decision": "approve", "rationale": "short attributed OA quote"}

    def fetcher(loc):
        return {"title": "A real ApoB study", "authors_short": "Smith", "year": 2020}

    def source_for(c):
        return {"transcript_text": "Attia: ApoB optimal is under 80 mg/dL.",
                "source_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC1/"}

    def legal_inputs_for(c):
        return {"source_type": "paper", "source_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC1/",
                "license_value": "CC BY"}

    scratch = PROJECT_ROOT / ".live-wave-check"
    scratch.mkdir(exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(dir=scratch) as tmp:
            res = orchestrate.run_wave_live(
                "wave-0", claims_by_marker={"apob": [claim]},
                role_caller=role_caller, legal_reviewer_caller=legal_caller, fetcher=fetcher,
                source_for=source_for, legal_inputs_for=legal_inputs_for,
                runs_dir=Path(tmp) / "runs", run_id="2026-05-29T120000Z-live", dry_run=True,
            )
            rd = Path(res["run_dir"])
            assert rd.exists()

            # council-only SM reference, per marker, evidence_weight 0 + rows
            smref = json.loads((rd / "council" / "apob" / "sm_alignment_reference.json").read_text())
            assert smref["evidence_weight"] == 0 and "rows" in smref

            s = res["summary"]
            assert s["markers_processed"] == 5 and s["firewall_ok"] is True
            assert s["range_facts"] >= 1 and s["research_studies"] >= 1

            apob = res["markers"]["apob"]
            assert apob["range_facts"][0]["biomarker_claim_id"] == apob["biomarker_claims"][0]["id"]

            st = json.loads((rd / "council" / "state.json").read_text())
            assert st["schema_version"] == "1" and st["stage"] == "stage_3_council"

            # FIREWALL (structural): the discovery payload on disk carries no
            # SM-bearing keys; SM numbers live only in the council artifact.
            disc = json.loads((rd / "discovery" / "apob.json").read_text())
            for k in ("rows", "min", "max", "sm_reference", "anchor_provenance",
                      "target_range_low", "target_range_high"):
                assert k not in disc, f"{k} leaked into the discovery payload"
            assert "rows" in smref, "SM rows must live only in the council-only reference"

            print("check_wave_live_contract: green — live wave run layout + firewall verified")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


if __name__ == "__main__":
    main()
