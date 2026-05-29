#!/usr/bin/env python3
"""DB-free contract check for the Stage 4 provenance deterministic core.

No DB, no network. Exercises code/pipeline/provenance.py locator parsing, slug
derivation, resolution classification, and row builders. The load-bearing
anti-fabrication rule (Session-34: 64% of LLM PMIDs were fabricated) is pinned
here: a research_study is NEVER built from an unconfirmed locator or without a
real title, and a parsed-but-unconfirmed locator is 'ambiguous', not 'resolved'.
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from code.acceptance.check_db_helpers_contract import assert_subset, enum_values  # noqa: E402


def main() -> None:
    from code.pipeline import provenance as p

    # 1) extract_locator — pmid/doi/none, pmid preferred
    assert p.extract_locator({"pmid": "123"})["target_locator"] == "pmid:123"
    assert p.extract_locator({"pmid": "123"})["edge_type"] == "paper_to_pmid"
    assert p.extract_locator({"doi": "10.1001/JAMA.2020"})["target_locator"] == "doi:10.1001/JAMA.2020"
    assert p.extract_locator({"doi": "10.1001/JAMA.2020"})["edge_type"] == "paper_to_doi"
    assert p.extract_locator({})["kind"] == "none"
    assert p.extract_locator({"pmid": "1", "doi": "10.1/x"})["kind"] == "pmid"

    # 2) slug_for_study — deterministic, pmid preferred, doi slugified
    assert p.slug_for_study("123", None, None) == "pmid-123"
    assert p.slug_for_study(None, "10.1001/JAMA.2020", None) == "doi-10-1001-jama-2020"

    # 3) classify_resolution — the anti-fabrication status mapping
    assert p.classify_resolution(p.extract_locator({}), confirmed=False) == "unresolvable"
    assert p.classify_resolution(p.extract_locator({"pmid": "1"}), confirmed=True) == "resolved"
    assert p.classify_resolution(p.extract_locator({"pmid": "1"}), confirmed=False) == "ambiguous"

    # 4) build_provenance_row — subset of provenance, valid enums
    loc = p.extract_locator({"pmid": "123"})
    row = p.build_provenance_row(
        biomarker_claim_id="bc-1", locator=loc, resolution_status="resolved",
        research_study_id="rs-1", source_locator="surface:peterattiamd.com",
    )
    assert_subset("provenance", row)
    assert row["edge_type"] in enum_values("provenance", "edge_type")
    assert row["resolution_status"] in enum_values("provenance", "resolution_status")
    assert row["target_locator"] == "pmid:123"

    # 5) build_research_study_row — only from a confirmed locator + real title
    study = p.build_research_study_row(
        locator=loc, metadata={"title": "Real Study", "authors_short": "Smith et al.", "year": 2020},
    )
    assert_subset("research_studies", study)
    assert "evidence_grade" not in study, "evidence_grade is GENERATED — never insert it"
    assert study["pmid"] == "123" and study["original_title"] == "Real Study"
    assert study["slug"], "slug is NOT NULL"

    # 5a) refuse to fabricate: no title -> ValueError
    try:
        p.build_research_study_row(locator=loc, metadata={})
        raise AssertionError("must refuse to build a study without a real title")
    except ValueError:
        pass

    # 5b) refuse to fabricate: no resolvable locator -> ValueError
    try:
        p.build_research_study_row(locator=p.extract_locator({}), metadata={"title": "x"})
        raise AssertionError("must refuse to build a study with no PMID/DOI")
    except ValueError:
        pass

    print("check_provenance_contract: all assertions passed")


if __name__ == "__main__":
    main()
