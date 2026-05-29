"""Stage 5 legal/IP review — deterministic pre-gates.

Two-tier design (§07): these pure hard-gates run first and short-circuit on a
reject/quarantine; only rows that clear them go to the LLM legal_reviewer
(layered on later). Posture is conservative throughout. Only `approve` /
`approve_with_modification` may set biomarker_claims.approval_status='approved'.
"""

from __future__ import annotations

from typing import Any

# Shadow libraries — "inherently, irredeemably infringing" (§07; Bartz v. Anthropic).
_SHADOW = ("libgen", "library.lol", "z-lib", "zlibrary", "z-library", "pilimi", "books3", "annas-archive")


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
    """CC compatibility matrix (§07). Non-commercial CC → reject (commercial use);
    no/custom/unknown license → deny pending manual review (quarantine);
    CC0 / public domain / CC BY[-SA/-ND] → approve."""
    lv = (license_value or "").strip().lower()
    if not lv:
        return {"decision": "quarantine", "reason": "no license — deny pending manual review", "check": False}
    # non-commercial CC variants must be checked before the permissive CC BY match
    if "nc" in lv and ("cc" in lv or "creative commons" in lv):
        return {"decision": "reject",
                "reason": "non-commercial CC license incompatible with commercial use", "check": False}
    if lv.startswith("cc0") or "public domain" in lv or "cc by" in lv:
        return {"decision": "approve", "reason": f"permissive license: {license_value}", "check": True}
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
