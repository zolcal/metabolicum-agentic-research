"""Live council I/O layer — prompt inputs + LLM-output bridge.

Builds the role-specific prompt inputs for 04a/04b/04c and maps the raw LLM role
outputs into the shape `council.decide_claim` consumes, so the live council reuses
the verified deterministic decision core (verbatim/consensus/envelope/row builders).

SM firewall: `build_extractor_input` (04a) takes NO sm_rows argument and emits no
SM keys/numbers — the extractor is structurally blind. Only the reviewer (04b)
and decider (04c) inputs carry `sm_anchor_rows`. The actual LLM call orchestration
(role_caller -> llm_client) layers on top of these pure builders.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from code.pipeline import council

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROMPTS_DIR = PROJECT_ROOT / "prompts"

_APPROVE = {"approve", "approve_with_modification"}
_PROMPTS = {
    "council_extractor": "04a-council-extractor.md",
    "council_reviewer": "04b-council-reviewer.md",
    "council_decider": "04c-council-decider.md",
}


def build_extractor_input(claim: dict, source: dict) -> dict[str, Any]:
    """04a input — the Stage-2 claim + cached source only. No SM, ever."""
    return {
        "marker_recommendation": claim,
        "source_artifact": source,
    }


def build_reviewer_input(
    claim: dict,
    extractor_output: dict,
    sm_rows: list[dict],
    *,
    source: dict | None = None,
    envelopes: list[dict] | None = None,
) -> dict[str, Any]:
    """04b input — adds the council extractor output + SM anchor rows (council-only)."""
    return {
        "marker_recommendation": claim,
        "council_extractor_output": extractor_output,
        "sm_anchor_rows": sm_rows,
        "research_target_envelopes": envelopes or [],
        "source_artifact": source or {},
    }


def build_decider_input(
    claim: dict,
    extractor_output: dict,
    reviewer_output: dict,
    sm_rows: list[dict],
    *,
    envelopes: list[dict] | None = None,
    practitioner_registry: list[dict] | None = None,
) -> dict[str, Any]:
    """04c input — claim + SM rows + extractor/reviewer outputs + registry (council-only)."""
    return {
        "marker_recommendation": claim,
        "sm_anchor_rows": sm_rows,
        "research_target_envelopes": envelopes or [],
        "council_extractor_output": extractor_output,
        "council_reviewer_output": reviewer_output,
        "practitioner_registry": practitioner_registry or [],
    }


def map_role_outputs(
    claim: dict, extractor_output: dict, reviewer_output: dict, decider_output: dict
) -> dict[str, Any]:
    """Bridge raw 04a/04b/04c JSON outputs into council.decide_claim's role_outputs."""
    return {
        "extractor": {
            "verbatim_quote": extractor_output.get("verbatim_quote"),
            "marker": extractor_output.get("marker"),
            "paradigm": extractor_output.get("paradigm", claim.get("paradigm")),
        },
        "reviewer": {
            "verbatim_quote": claim.get("verbatim_quote"),
            "marker": claim.get("marker"),
            "paradigm": claim.get("paradigm"),
            "quote_verified": reviewer_output.get("verbatim_quote_verified"),
        },
        "decider": {
            "verbatim_quote": claim.get("verbatim_quote"),
            "marker": claim.get("marker"),
            "paradigm": decider_output.get("paradigm_assigned", claim.get("paradigm")),
            "evidence_sub_grade": decider_output.get("evidence_sub_grade"),
            "decision": decider_output.get("decision"),
        },
    }


def _read_prompt(role: str) -> str:
    return (PROMPTS_DIR / _PROMPTS[role]).read_text(encoding="utf-8")


def run_council_pass(
    claim: dict,
    source: dict,
    sm_rows: list[dict],
    *,
    role_caller: Any,
    financial_conflict: tuple[bool, str] = (False, "generic"),
) -> dict[str, Any]:
    """Run the live council: call 04a/04b/04c via `role_caller`, map to the
    deterministic decision core, and apply both-must-approve.

    `role_caller(role, system, user) -> dict` performs the LLM call (injected so
    the orchestration is testable without a real model). Approval requires BOTH
    council.decide_claim (reviewer-verified + extractor agreement) AND the LLM
    decider's approve/approve_with_modification; either quarantine → quarantine.
    """
    ext_out = role_caller("council_extractor", _read_prompt("council_extractor"),
                          build_extractor_input(claim, source))
    rev_out = role_caller("council_reviewer", _read_prompt("council_reviewer"),
                          build_reviewer_input(claim, ext_out, sm_rows, source=source))
    dec_out = role_caller("council_decider", _read_prompt("council_decider"),
                          build_decider_input(claim, ext_out, rev_out, sm_rows))

    role_outputs = map_role_outputs(claim, ext_out, rev_out, dec_out)
    outcome = council.decide_claim(
        claim, role_outputs, sm_rows,
        source_id=claim.get("source_id"), financial_conflict=financial_conflict,
    )

    decider_decision = (dec_out or {}).get("decision")
    if outcome["outcome"] == "approved" and decider_decision not in _APPROVE:
        return {
            "outcome": "quarantined",
            "biomarker_claim_row": None,
            "quarantine_row": council.build_quarantine_row(
                claim, rejection_stage="decider",
                rejection_reason=f"LLM decider decision={decider_decision!r} did not approve",
                rejection_codes=["council_decider_quarantine"],
                source_id=claim.get("source_id"), financial_conflict=financial_conflict,
            ),
            "envelope_evaluation": outcome.get("envelope_evaluation"),
            "consensus_score": outcome.get("consensus_score"),
        }
    return outcome
