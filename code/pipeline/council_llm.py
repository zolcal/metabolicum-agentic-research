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

from typing import Any


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
