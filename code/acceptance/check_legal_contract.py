#!/usr/bin/env python3
"""DB-free contract check for the Stage 5 legal deterministic pre-gates.

No DB, no network, no LLM. Exercises code/pipeline/legal.py hard pre-gates
(empty quote, envelope-fact, shadow library, license, quote length) per §07,
and asserts build_legal_review_row is a subset of legal_reviews with valid enums.
The LLM legal_reviewer runs only on rows that clear these hard gates (later layer).
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from code.acceptance.check_db_helpers_contract import assert_subset, enum_values  # noqa: E402


def main() -> None:
    from code.pipeline import legal

    # 1) quote length (long-form policy: <=80 approve, 81-120 modify, >120 quarantine)
    assert legal.word_count("a b c") == 3
    assert legal.classify_quote_length("word " * 50)["decision"] == "approve"
    assert legal.classify_quote_length("word " * 100)["decision"] == "approve_with_modification"
    assert legal.classify_quote_length("word " * 130)["decision"] == "quarantine"

    # 2) license matrix
    assert legal.classify_license("CC BY")["decision"] == "approve"
    assert legal.classify_license("CC0")["decision"] == "approve"
    assert legal.classify_license("CC BY-SA")["decision"] == "approve"
    assert legal.classify_license("CC BY-NC")["decision"] == "reject"
    assert legal.classify_license("CC BY-NC-SA")["decision"] == "reject"
    assert legal.classify_license(None)["decision"] == "quarantine"
    assert legal.classify_license("custom")["decision"] == "quarantine"

    # 2b) fair-use quotation lane (§07 Feist + §107). Public-web all-rights-reserved
    # and YouTube fair-use-quote-only sources grant NO reuse license, but their
    # CONTENT is eligible for short, attributed, line-level factual quotation. These
    # route to approve with a fair_use flag; quote length + the LLM reviewer still gate.
    assert legal.classify_license("all_rights_reserved_public_web_page")["decision"] == "approve"
    assert legal.classify_license("all_rights_reserved_public_web_page").get("fair_use") is True
    assert legal.classify_license("all_rights_reserved_public_web_excerpt")["decision"] == "approve"
    assert legal.classify_license("youtube_public_caption_fair_use_quote_only")["decision"] == "approve"
    assert legal.classify_license("youtube_public_caption_fair_use_quote_only").get("fair_use") is True
    # truly-unknown / custom / none stay conservative — NOT fair-use
    assert legal.classify_license(None).get("fair_use") is not True
    assert legal.classify_license("custom").get("fair_use") is not True

    # 3) shadow libraries
    assert legal.is_shadow_library("https://libgen.is/book/x") is True
    assert legal.is_shadow_library("https://z-lib.org/x") is True
    assert legal.is_shadow_library("https://pmc.ncbi.nlm.nih.gov/articles/PMC1/") is False

    # 4) legal_pregate — combined hard decision (order: empty -> envelope -> shadow -> license -> length)
    claim = {"verbatim_quote": "ApoB under 80 mg/dL is optimal.", "marker": "apob"}
    g_ok = legal.legal_pregate(
        claim, source_type="paper",
        source_url="https://pmc.ncbi.nlm.nih.gov/articles/PMC1/", license_value="CC BY",
        is_envelope_fact=False,
    )
    assert g_ok["decision"] in ("approve", "approve_with_modification")

    g_empty = legal.legal_pregate({"verbatim_quote": ""}, license_value="CC BY")
    assert g_empty["decision"] == "reject" and "empty_quote" in g_empty["applicable_rules"]

    g_shadow = legal.legal_pregate(claim, source_url="https://libgen.is/x", license_value=None)
    assert g_shadow["decision"] == "reject"

    g_nc = legal.legal_pregate(claim, source_url="https://blog.x", license_value="CC BY-NC")
    assert g_nc["decision"] == "reject"

    g_env = legal.legal_pregate(claim, source_url="https://pmc.x", license_value="CC BY", is_envelope_fact=True)
    assert g_env["decision"] in ("reject", "quarantine"), "envelope facts are never legal support"

    # 4b) fair-use lane: short attributed quote from an all-rights-reserved blog
    # passes the pre-gate (-> LLM reviewer) and records the fair_use_line_quotation basis.
    g_fu = legal.legal_pregate(
        claim, source_type="blog", source_url="https://peterattiamd.com/x",
        license_value="all_rights_reserved_public_web_page",
    )
    assert g_fu["decision"] in ("approve", "approve_with_modification"), g_fu
    assert "fair_use_line_quotation" in g_fu["applicable_rules"], g_fu
    # the fair-use lane still enforces quote length: >120 words -> quarantine
    g_fu_long = legal.legal_pregate(
        {"verbatim_quote": "word " * 130}, source_type="blog",
        source_url="https://peterattiamd.com/x", license_value="all_rights_reserved_public_web_page",
    )
    assert g_fu_long["decision"] == "quarantine", g_fu_long
    # a fair-use tag from a shadow library still REJECTS (shadow precedes license)
    g_fu_shadow = legal.legal_pregate(
        claim, source_url="https://libgen.is/x",
        license_value="all_rights_reserved_public_web_page",
    )
    assert g_fu_shadow["decision"] == "reject", g_fu_shadow

    # 5) build_legal_review_row — subset, valid enums, rationale NOT NULL
    row = legal.build_legal_review_row("bc-1", g_ok, reviewer_model="deterministic-pre-gate")
    assert_subset("legal_reviews", row)
    assert row["decision"] in enum_values("legal_reviews", "decision")
    assert row["rationale"], "rationale is NOT NULL"
    assert row["reviewer_model"], "reviewer_model is NOT NULL"
    assert row["feist_compilation_risk"] in enum_values("legal_reviews", "feist_compilation_risk")

    print("check_legal_contract: all assertions passed")


if __name__ == "__main__":
    main()
