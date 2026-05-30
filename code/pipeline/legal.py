"""Stage 5 legal/IP review — deterministic pre-gates.

Two-tier design (§07): these pure hard-gates run first and short-circuit on a
reject/quarantine; only rows that clear them go to the LLM legal_reviewer
(layered on later). Posture is conservative throughout. Only `approve` /
`approve_with_modification` may set biomarker_claims.approval_status='approved'.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LEGAL_PROMPT = PROJECT_ROOT / "prompts" / "05-legal-reviewer.md"
_APPROVALS = {"approve", "approve_with_modification"}

# Shadow libraries — "inherently, irredeemably infringing" (§07; Bartz v. Anthropic).
_SHADOW = ("libgen", "library.lol", "z-lib", "zlibrary", "z-library", "pilimi", "books3", "annas-archive")

# Fair-use quotation lane (§07: Feist facts-not-copyrightable + §107 fair use).
# These license tags mean "no reuse license granted, but the content is publicly
# visible and eligible for SHORT, attributed, line-level factual quotation" — NOT
# wholesale ingestion. Discovery stamps them on practitioner web/YouTube sources
# (code/discovery/web.py -> all_rights_reserved_public_web_page;
#  code/discovery/youtube.py -> youtube_public_caption_fair_use_quote_only).
# The license hard-quarantine is lifted for these because a short fair-use quote of
# a non-copyrightable fact does not depend on the source's reuse license; the claim
# still passes the quote-length pre-gate AND the LLM legal reviewer (§107 call).
_FAIR_USE_QUOTE_PREFIXES = ("all_rights_reserved_public_web",)
_FAIR_USE_QUOTE_MARKERS = ("fair_use_quote_only",)


def is_fair_use_quote_license(license_value: str | None) -> bool:
    """True for practitioner public-web / fair-use-quote-only license tags whose
    content is eligible for short attributed factual quotation (not wholesale reuse)."""
    lv = (license_value or "").strip().lower()
    if not lv:
        return False
    return lv.startswith(_FAIR_USE_QUOTE_PREFIXES) or any(m in lv for m in _FAIR_USE_QUOTE_MARKERS)


def word_count(quote: str | None) -> int:
    return len((quote or "").split())


def classify_quote_length(quote: str | None, *, source_type: str | None = None) -> dict[str, Any]:
    """Long-form quote policy (§07): default shortest excerpt, normally ≤80 words.

    ≤80 → approve; 81–120 → approve_with_modification (truncate to ≤80);
    >120 → quarantine (excessive excerpt). Empty → reject.
    """
    n = word_count(quote)
    if n == 0:
        return {"words": 0, "decision": "reject", "reason": "empty quote", "check": False}
    if n <= 80:
        return {"words": n, "decision": "approve", "reason": f"{n} words ≤ 80", "check": True}
    if n <= 120:
        return {"words": n, "decision": "approve_with_modification",
                "reason": f"{n} words; truncate to ≤ 80", "check": True}
    return {"words": n, "decision": "quarantine",
            "reason": f"{n} words > 120; excessive excerpt", "check": False}


def classify_license(license_value: str | None) -> dict[str, Any]:
    """CC compatibility matrix (§07) + fair-use quotation lane.

    Non-commercial CC → reject (commercial use); CC0 / public domain / CC BY[-SA/-ND]
    → approve (wholesale ingestion). Public-web / fair-use-quote-only tags → approve
    with fair_use=True (short attributed factual quotation only; quote-length gate and
    LLM reviewer still apply). Truly no/custom/unknown license → deny pending manual
    review (quarantine)."""
    lv = (license_value or "").strip().lower()
    if not lv:
        return {"decision": "quarantine", "reason": "no license — deny pending manual review", "check": False}
    # non-commercial CC variants must be checked before the permissive CC BY match
    if "nc" in lv and ("cc" in lv or "creative commons" in lv):
        return {"decision": "reject",
                "reason": "non-commercial CC license incompatible with commercial use", "check": False}
    if lv.startswith("cc0") or "public domain" in lv or "cc by" in lv:
        return {"decision": "approve", "reason": f"permissive license: {license_value}", "check": True}
    # fair-use lane: no reuse license, but content eligible for short attributed quotes
    if is_fair_use_quote_license(license_value):
        return {"decision": "approve", "fair_use": True, "check": True,
                "reason": f"fair-use quotation lane (no reuse license granted): {license_value}"}
    if "custom" in lv:
        return {"decision": "quarantine", "reason": "custom license — deny pending manual review", "check": False}
    return {"decision": "quarantine", "reason": f"unrecognized license '{license_value}' — manual review", "check": False}


def is_shadow_library(url: str | None) -> bool:
    u = (url or "").lower()
    return any(s in u for s in _SHADOW)


def _decision(
    decision: str, rationale: str, applicable_rules: list[str], *,
    quote_length_check: bool | None = None, license_check: bool | None = None,
    tos_check: bool | None = None, feist: str = "none", eu_db: bool | None = None,
) -> dict[str, Any]:
    return {
        "decision": decision, "rationale": rationale, "applicable_rules": applicable_rules,
        "quote_length_check": quote_length_check, "license_check": license_check,
        "tos_check": tos_check, "feist_compilation_risk": feist, "eu_database_flag": eu_db,
    }


def legal_pregate(
    claim: dict,
    *,
    source_type: str | None = None,
    source_url: str | None = None,
    license_value: str | None = None,
    is_envelope_fact: bool = False,
) -> dict[str, Any]:
    """Deterministic hard pre-gate. Order: empty quote → envelope-fact → shadow
    library → license → quote length. Returns a legal-decision dict."""
    quote = claim.get("verbatim_quote")
    if not quote or not quote.strip():
        return _decision("reject", "empty or missing verbatim_quote", ["empty_quote"],
                         quote_length_check=False)
    if is_envelope_fact:
        return _decision("reject", "research target envelope facts are never legal evidence (§17)",
                         ["envelope_not_evidence"])
    if is_shadow_library(source_url):
        return _decision("reject", "source is a shadow library (LibGen/Z-Library/PiLiMi/Books3)",
                         ["shadow_library"], tos_check=False)
    lic = classify_license(license_value)
    if lic["decision"] in ("reject", "quarantine"):
        codes = ["non_commercial_license"] if lic["decision"] == "reject" else ["license_review_required"]
        return _decision(lic["decision"], lic["reason"], codes, license_check=lic["check"])
    ql = classify_quote_length(quote, source_type=source_type)
    if ql["decision"] == "approve":
        codes: list[str] = []
    elif ql["decision"] == "approve_with_modification":
        codes = ["quote_truncation_required"]
    else:
        codes = ["quote_too_long"]
    # record the fair-use basis so the audit trail shows WHY a no-reuse-license
    # source cleared the license gate (the LLM reviewer still makes the §107 call)
    if lic.get("fair_use"):
        codes = ["fair_use_line_quotation", *codes]
    return _decision(ql["decision"], f"{lic['reason']}; {ql['reason']}", codes,
                     quote_length_check=ql["check"], license_check=lic["check"], tos_check=True)


def build_legal_review_row(
    biomarker_claim_id: str, decision: dict, *, reviewer_model: str
) -> dict[str, Any]:
    """Project a legal decision into a `legal_reviews` row (id/reviewed_at/
    updated_at stamped by DBClient.insert_legal_review)."""
    row = {
        "biomarker_claim_id": biomarker_claim_id,
        "reviewer_model": reviewer_model,
        "decision": decision["decision"],
        "rationale": decision["rationale"],
        "applicable_rules": list(decision.get("applicable_rules") or []),
        "quote_length_check": decision.get("quote_length_check"),
        "license_check": decision.get("license_check"),
        "tos_check": decision.get("tos_check"),
        "feist_compilation_risk": decision.get("feist_compilation_risk"),
        "eu_database_flag": decision.get("eu_database_flag"),
    }
    return {k: v for k, v in row.items() if v is not None}


def run_legal_review(
    claim: dict,
    *,
    source_type: str | None = None,
    source_url: str | None = None,
    license_value: str | None = None,
    is_envelope_fact: bool = False,
    reviewer_caller,
    biomarker_claim_id: str | None = None,
    source: dict | None = None,
) -> dict[str, Any]:
    """Deterministic hard pre-gates first; only rows that clear them go to the
    LLM legal reviewer (prompt 05) via `reviewer_caller`. The LLM is authoritative
    for cleared rows (it may downgrade approve→quarantine/reject), but can never
    rescue a hard-gate failure. Returns the final decision + a legal_reviews row."""
    gate = legal_pregate(claim, source_type=source_type, source_url=source_url,
                         license_value=license_value, is_envelope_fact=is_envelope_fact)
    if gate["decision"] not in _APPROVALS:
        row = build_legal_review_row(biomarker_claim_id, gate, reviewer_model="deterministic-pre-gate")
        return {"decision": gate["decision"], "legal_review_row": row, "via": "pre-gate", "called_llm": False}

    system = LEGAL_PROMPT.read_text(encoding="utf-8")
    user = {
        "marker_recommendation": claim,
        "source_artifact": source or {},
        "license": license_value,
        "source_type": source_type,
    }
    llm = reviewer_caller("legal_reviewer", system, user) or {}
    final = {
        "decision": llm.get("decision", gate["decision"]),
        "rationale": llm.get("rationale") or gate["rationale"],
        "applicable_rules": list(dict.fromkeys(
            (gate.get("applicable_rules") or []) + (llm.get("applicable_rules") or []))),
        "quote_length_check": gate.get("quote_length_check"),
        "license_check": gate.get("license_check"),
        "tos_check": gate.get("tos_check", True),
        "feist_compilation_risk": llm.get("feist_compilation_risk", gate.get("feist_compilation_risk", "none")),
        "eu_database_flag": llm.get("eu_database_flag", gate.get("eu_database_flag")),
    }
    row = build_legal_review_row(biomarker_claim_id, final, reviewer_model=llm.get("reviewer_model", "legal_reviewer"))
    return {"decision": final["decision"], "legal_review_row": row, "via": "llm", "called_llm": True}
