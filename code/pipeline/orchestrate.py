"""Per-marker pipeline orchestration (deterministic offline core).

`run_single_marker_offline` chains the Stage 3-6 deterministic helpers for one
marker with no DB, no network, and no LLM (role outputs and legal inputs are
supplied by injected callables). This is the critical-path integration: an
approved claim becomes a §18 range_fact that traces to its biomarker_claim id.

SM firewall: the SM rows are passed ONLY into council.decide_claim — never into
the extraction input. The live orchestrator (file IO, sm_reference resolution,
LLM roles, DB writes) wraps this pure core in a later increment.
"""

from __future__ import annotations

from typing import Any, Callable

from code.pipeline import assembly, council, legal, provenance

_LEGAL_APPROVALS = {"approve", "approve_with_modification"}


def run_single_marker_offline(
    marker: str,
    stage2_claims: list[dict],
    sm_rows: list[dict],
    *,
    role_outputs_fn: Callable[[dict], dict],
    legal_inputs_fn: Callable[[dict], dict],
) -> dict[str, Any]:
    """Run council -> provenance -> legal -> assembly for one marker, offline.

    Returns a deterministic dict of biomarker_claims, range_facts, provenance,
    legal_reviews, research_studies (always empty offline — never fabricated),
    and quarantine rows.
    """
    out: dict[str, Any] = {
        "marker": marker,
        "biomarker_claims": [],
        "range_facts": [],
        "provenance": [],
        "legal_reviews": [],
        "research_studies": [],
        "quarantine": [],
    }
    range_order = 0

    for i, claim in enumerate(stage2_claims):
        bcid = f"{marker}-bc-{i + 1}"  # deterministic id for the offline run
        source_id = claim.get("source_id")

        # Stage 3 — council (SM rows enter ONLY here)
        outcome = council.decide_claim(
            claim, role_outputs_fn(claim), sm_rows, source_id=source_id
        )
        if outcome["outcome"] != "approved":
            out["quarantine"].append(outcome["quarantine_row"])
            continue
        bc_row = dict(outcome["biomarker_claim_row"])

        # Stage 4 — provenance (offline: parsed, not live-confirmed -> ambiguous)
        locator = provenance.extract_locator(claim.get("cited_paper"))
        resolution = provenance.classify_resolution(locator, confirmed=False)
        out["provenance"].append(provenance.build_provenance_row(
            biomarker_claim_id=bcid, locator=locator, resolution_status=resolution,
        ))
        bc_row["provenance_status"] = resolution
        # research_studies stay empty offline — never fabricate without confirmation

        # Stage 5 — legal
        li = legal_inputs_fn(claim)
        decision = legal.legal_pregate(
            claim, source_type=li.get("source_type"), source_url=li.get("source_url"),
            license_value=li.get("license_value"), is_envelope_fact=li.get("is_envelope_fact", False),
        )
        out["legal_reviews"].append(
            legal.build_legal_review_row(bcid, decision, reviewer_model="deterministic-pre-gate")
        )
        if decision["decision"] not in _LEGAL_APPROVALS:
            out["quarantine"].append(council.build_quarantine_row(
                claim, rejection_stage="legal", rejection_reason=decision["rationale"],
                rejection_codes=decision["applicable_rules"], source_id=source_id,
                biomarker_claim_id=bcid,
            ))
            continue

        bc_row["legal_status"] = "approved"
        bc_row["approval_status"] = "approved"
        out["biomarker_claims"].append({**bc_row, "id": bcid})

        # Stage 6 — assembly (§18 range_fact)
        range_order += 1
        fact = assembly.build_range_fact(bc_row, biomarker_claim_id=bcid, range_order=range_order)
        if fact is not None:
            out["range_facts"].append(fact)

    return out
