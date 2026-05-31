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

import json
import uuid
from pathlib import Path
from typing import Any, Callable

from code import state as _state
from code.loaders.sm_reference import resolve_sm_reference
from code.pipeline import assembly, brief, council, council_llm, legal, persist, provenance

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BRIEFS_DIR = PROJECT_ROOT / "input" / "hermes-briefs"

_LEGAL_APPROVALS = {"approve", "approve_with_modification"}
_SM_BEARING_KEYS = {"rows", "min", "max", "anchor_provenance", "sm_reference",
                    "target_range_low", "target_range_high"}


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


def _discovery_is_clean(discovery_payload: dict) -> bool:
    """True iff the discovery payload carries no SM-bearing keys (firewall)."""
    return not (_SM_BEARING_KEYS & set(discovery_payload.keys()))


def run_wave_offline(
    wave: str,
    *,
    claims_by_marker: dict[str, list[dict]],
    role_outputs_fn: Callable[[dict], dict],
    legal_inputs_fn: Callable[[dict], dict],
    briefs_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Run the offline pipeline across every marker brief in a wave.

    Each brief is split into a discovery payload (SM-free) and council-only SM
    rows; the single-marker pipeline runs per marker. Deterministic (markers
    sorted). $0 — no DB, no network, no LLM.
    """
    wave_dir = Path(briefs_dir or BRIEFS_DIR) / wave
    markers = sorted(p.stem for p in wave_dir.glob("*.yaml"))

    results: dict[str, Any] = {}
    summary = {"wave": wave, "markers_processed": 0, "range_facts": 0,
               "approved": 0, "quarantined": 0, "firewall_ok": True}

    for marker in markers:
        b = brief.load_brief(wave_dir / f"{marker}.yaml")
        discovery = brief.discovery_payload(b)
        if not _discovery_is_clean(discovery):
            summary["firewall_ok"] = False
        sm_rows = brief.resolve_council_sm_rows(b)
        r = run_single_marker_offline(
            marker, claims_by_marker.get(marker, []), sm_rows,
            role_outputs_fn=role_outputs_fn, legal_inputs_fn=legal_inputs_fn,
        )
        results[marker] = r
        summary["markers_processed"] += 1
        summary["range_facts"] += len(r["range_facts"])
        summary["approved"] += len(r["biomarker_claims"])
        summary["quarantined"] += len(r["quarantine"])

    return {"summary": summary, "markers": results}


# ── Live per-marker + per-wave orchestration ─────────────────────────

def run_marker_live(
    marker: str,
    claims: list[dict],
    sm_rows: list[dict],
    *,
    source_for: Callable[[dict], dict],
    role_caller: Any,
    legal_reviewer_caller: Any,
    fetcher: Any,
    legal_inputs_for: Callable[[dict], dict],
    mo_supported: bool | None = None,
    mo_rationale: str | None = None,
) -> dict[str, Any]:
    """Live per-marker chain: council (LLM) -> provenance (live fetch) -> legal
    (LLM) -> assembly. SM rows go only to the council via run_council_pass.

    The brief's binary MO-support determination (mo_supported/mo_rationale) is recorded
    as `mo_determination` on the result — Hermes creates this record on its run. When
    mo_supported is False the marker is a pass-through: the determination is set and the
    council/research chain is SKIPPED (no claims processed). mo_supported=None (callers
    that don't carry the determination, e.g. offline contracts) runs unchanged.
    """
    out: dict[str, Any] = {
        "marker": marker, "biomarker_claims": [], "range_facts": [], "provenance": [],
        "legal_reviews": [], "research_studies": [], "quarantine": [],
    }
    if mo_supported is not None:
        out["mo_determination"] = {
            "marker_slug": marker, "mo_supported": bool(mo_supported), "mo_rationale": mo_rationale,
        }
    if mo_supported is False:
        return out  # not_supported pass-through — honor the determination, run no research
    range_order = 0
    for i, claim in enumerate(claims):
        # Live ids must be real UUIDs (biomarker_claims.id is uuid; provenance/
        # legal rows FK to it). The offline core uses deterministic ids instead.
        bcid = str(uuid.uuid4())
        source = source_for(claim)

        outcome = council_llm.run_council_pass(claim, source, sm_rows, role_caller=role_caller)
        if outcome["outcome"] != "approved":
            out["quarantine"].append(outcome["quarantine_row"])
            continue
        bc = dict(outcome["biomarker_claim_row"])

        locator = provenance.extract_locator(claim.get("cited_paper"))
        resolved = provenance.resolve_locator(locator, fetcher=fetcher)
        bc["provenance_status"] = resolved["resolution_status"]
        out["provenance"].append(provenance.build_provenance_row(
            biomarker_claim_id=bcid, locator=locator, resolution_status=resolved["resolution_status"]))
        if resolved["research_study_row"]:
            out["research_studies"].append(resolved["research_study_row"])

        li = legal_inputs_for(claim)
        lr = legal.run_legal_review(
            claim, source_type=li.get("source_type"), source_url=li.get("source_url"),
            license_value=li.get("license_value"), reviewer_caller=legal_reviewer_caller,
            biomarker_claim_id=bcid, source=source)
        out["legal_reviews"].append(lr["legal_review_row"])
        if lr["decision"] not in _LEGAL_APPROVALS:
            out["quarantine"].append(council.build_quarantine_row(
                claim, rejection_stage="legal", rejection_reason=lr["legal_review_row"]["rationale"],
                rejection_codes=lr["legal_review_row"].get("applicable_rules", []),
                source_id=claim.get("source_id"), biomarker_claim_id=bcid))
            continue

        bc["legal_status"] = "approved"
        bc["approval_status"] = "approved"
        out["biomarker_claims"].append({**bc, "id": bcid})
        range_order += 1
        fact = assembly.build_range_fact(bc, biomarker_claim_id=bcid, range_order=range_order)
        if fact is not None:
            out["range_facts"].append(fact)
    return out


def run_wave_live(
    wave: str,
    *,
    claims_by_marker: dict[str, list[dict]],
    role_caller: Any,
    legal_reviewer_caller: Any,
    fetcher: Any,
    source_for: Callable[[dict], dict],
    legal_inputs_for: Callable[[dict], dict],
    runs_dir: str | Path,
    run_id: str | None = None,
    briefs_dir: str | Path | None = None,
    db: Any = None,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Live per-wave orchestrator: writes the §10 runs/<id>/ layout, materializes
    the council-only sm_alignment_reference per marker, runs the live chain, and
    (when db given and not dry_run) persists. Returns {run_dir, summary, markers}."""
    wave_dir = Path(briefs_dir or BRIEFS_DIR) / wave
    markers = sorted(p.stem for p in wave_dir.glob("*.yaml"))

    orig_runs = _state.RUNS_DIR
    _state.RUNS_DIR = Path(runs_dir)
    try:
        run = _state.PipelineRun.create(run_id)
    finally:
        _state.RUNS_DIR = orig_runs

    summary = {"wave": wave, "run_id": run.run_id, "markers_processed": 0, "range_facts": 0,
               "approved": 0, "quarantined": 0, "research_studies": 0, "firewall_ok": True}
    results: dict[str, Any] = {}
    accepted_all: list[dict] = []
    rejected_all: list[dict] = []

    for marker in markers:
        b = brief.load_brief(wave_dir / f"{marker}.yaml")
        discovery = brief.discovery_payload(b)
        if not _discovery_is_clean(discovery):
            summary["firewall_ok"] = False
        (run.run_dir / "discovery" / f"{marker}.json").write_text(json.dumps(discovery, indent=2))

        cdir = run.run_dir / "council" / marker
        cdir.mkdir(parents=True, exist_ok=True)
        (cdir / "sm_alignment_reference.json").write_text(
            json.dumps(resolve_sm_reference(b["sm_reference"]), indent=2, sort_keys=True, default=str))
        sm_rows = brief.resolve_council_sm_rows(b)

        res = run_marker_live(
            marker, claims_by_marker.get(marker, []), sm_rows,
            source_for=source_for, role_caller=role_caller,
            legal_reviewer_caller=legal_reviewer_caller, fetcher=fetcher,
            legal_inputs_for=legal_inputs_for,
            mo_supported=b.get("mo_supported"), mo_rationale=b.get("mo_rationale"))
        results[marker] = res
        accepted_all.extend(res["biomarker_claims"])
        rejected_all.extend(res["quarantine"])
        if res["range_facts"]:
            (run.marker_dir(marker) / "range_facts.json").write_text(
                json.dumps(res["range_facts"], indent=2, default=str))
        if db is not None and not dry_run:
            persist.persist_marker_result(db, res, dry_run=False)

        summary["markers_processed"] += 1
        summary["range_facts"] += len(res["range_facts"])
        summary["approved"] += len(res["biomarker_claims"])
        summary["quarantined"] += len(res["quarantine"])
        summary["research_studies"] += len(res["research_studies"])

    run.write_council_accepted(accepted_all)
    run.write_council_rejected(rejected_all)
    for stage in ("discovery", "sources", "council", "provenance", "legal", "assembly"):
        run.write_stage_state(stage, status="completed",
                              metrics={"markers": summary["markers_processed"]})

    return {"run_dir": str(run.run_dir), "summary": summary, "markers": results}
