#!/usr/bin/env python3
"""Contract for resolve_locator — provenance resolution via an injected fetcher.

No network. A fake fetcher stands in for PubMed/Crossref. Asserts the
anti-fabrication rule end to end: a confirmed locator (fetcher returns a real
title) -> resolution_status='resolved' + a research_study row; an unconfirmed
locator (fetcher returns None/no title) -> 'unresolvable' with NO study; a
missing locator -> 'unresolvable' without even calling the fetcher.
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from code.acceptance.check_db_helpers_contract import assert_subset  # noqa: E402


def main() -> None:
    from code.pipeline import provenance as p

    # confirmed PMID
    loc = p.extract_locator({"pmid": "123"})
    confirmed = p.resolve_locator(loc, fetcher=lambda l: {"title": "A real study", "authors_short": "Smith", "year": 2020})
    assert confirmed["resolution_status"] == "resolved"
    assert confirmed["research_study_row"] is not None
    assert_subset("research_studies", confirmed["research_study_row"])
    assert confirmed["research_study_row"]["pmid"] == "123"
    assert "evidence_grade" not in confirmed["research_study_row"]

    # fetcher finds nothing -> unresolvable, NO study (never fabricate)
    miss = p.resolve_locator(loc, fetcher=lambda l: None)
    assert miss["resolution_status"] == "unresolvable" and miss["research_study_row"] is None

    # fetcher returns a row without a title -> still refuse
    notitle = p.resolve_locator(loc, fetcher=lambda l: {"authors_short": "X"})
    assert notitle["resolution_status"] == "unresolvable" and notitle["research_study_row"] is None

    # no locator -> unresolvable, fetcher never called
    called = []
    none_loc = p.extract_locator({})
    res = p.resolve_locator(none_loc, fetcher=lambda l: called.append(l) or {"title": "x"})
    assert res["resolution_status"] == "unresolvable" and res["research_study_row"] is None
    assert called == [], "fetcher must not be called for a missing locator"

    print("check_provenance_live_contract: all assertions passed")


if __name__ == "__main__":
    main()
