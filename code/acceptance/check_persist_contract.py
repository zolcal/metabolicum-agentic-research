#!/usr/bin/env python3
"""Contract for persist_marker_result — DB writes via a FakeDB (no real DB).

Asserts persistence writes each result list through the right DBClient helper in
FK-safe order (biomarker_claims before provenance/legal that reference it;
research_studies before provenance), and that dry_run makes zero writes while
still reporting the planned counts.
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


class FakeDB:
    def __init__(self):
        self.calls = []

    def insert_biomarker_claim(self, d):
        self.calls.append(("biomarker_claims", d)); return d

    def upsert_research_study(self, d):
        self.calls.append(("research_studies", d)); return d

    def insert_provenance(self, d):
        self.calls.append(("provenance", d)); return d

    def insert_legal_review(self, d):
        self.calls.append(("legal_reviews", d)); return d

    def insert_claim_envelope_evaluation(self, d):
        self.calls.append(("claim_envelope_evaluations", d)); return d

    def insert_quarantine(self, d):
        self.calls.append(("quarantine", d)); return d


def main() -> None:
    from code.pipeline import persist

    result = {
        "marker": "apob",
        "biomarker_claims": [{"id": "bc-1", "marker": "apob"}],
        "research_studies": [],
        "provenance": [{"biomarker_claim_id": "bc-1", "resolution_status": "ambiguous"}],
        "legal_reviews": [{"biomarker_claim_id": "bc-1", "decision": "approve"}],
        "claim_envelope_evaluations": [],
        "quarantine": [{"rejection_stage": "legal", "rejection_reason": "x"}],
    }

    db = FakeDB()
    out = persist.persist_marker_result(db, result, dry_run=False)
    assert out["written"] == 4, out
    assert out["counts"]["biomarker_claims"] == 1 and out["counts"]["quarantine"] == 1
    tables = [t for t, _ in db.calls]
    assert tables[0] == "biomarker_claims", "biomarker_claims must be written first (FK target)"
    assert tables == ["biomarker_claims", "provenance", "legal_reviews", "quarantine"], tables

    # dry-run: zero writes, planned counts reported
    db2 = FakeDB()
    out2 = persist.persist_marker_result(db2, result, dry_run=True)
    assert out2["written"] == 0 and db2.calls == []
    assert out2["counts"] == out["counts"]

    print("check_persist_contract: all assertions passed")


if __name__ == "__main__":
    main()
