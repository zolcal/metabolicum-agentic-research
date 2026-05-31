"""No-quarantine, iterate-until-verdict MO runtime loop.

Implements docs/superpowers/specs/2026-05-30-hermes-no-quarantine-iterate-discovery-design.md.

Per marker: discover sources -> extract (Stage 2) -> judge each MO claim. A claim
is APPROVED only if it clears the SM sanity bound AND the council/legal chain;
otherwise it is REJECTED and written to a terminal rejection_log (no quarantine
limbo). If approved claims < STOP_COUNT, widen discovery and retry, up to a
bounded cap (MAX_ROUNDS / MAX_SOURCES). A marker that never reaches the target
simply ends with what it has (0 = "no MO support found").

SM ranges are a sanity bound (sign / 10x / absurd), never a conformance target.

Usage:
    python -m code.pipeline.iterate fasting-insulin --wave wave-0            # dry-run
    python -m code.pipeline.iterate fasting-insulin --wave wave-0 --write    # persist + export
    python -m code.pipeline.iterate fasting-insulin --fixtures-dir fixtures/sources  # reuse fixtures (fast test)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from code.discovery import web
from code.llm_client import LLMClient
from code.pipeline import brief, council, ingest, persist
from code.pipeline.live_run import run_marker_live_session
from code.state import PipelineRun

BRIEFS = PROJECT_ROOT / "input" / "hermes-briefs"
OUT = PROJECT_ROOT / "output" / "markers"

STOP_COUNT = 2      # approved MO claims that ends the search
MAX_ROUNDS = 3      # widening rounds
MAX_SOURCES = 12    # new sources fetched per marker (whichever cap hits first)


def _stage2_clients(llm: LLMClient):
    """Build the Stage-2 role clients + the extractor's DeepSeek failover."""
    clients = {r: llm.chat_client(r) for r in ("extractor", "tagger", "structurer")}
    models = {r: llm.model_name_for(r) for r in ("extractor", "tagger", "structurer")}
    ec = llm.endpoint_for("extractor")
    sec = ec.get("failover_to")
    if sec and sec in llm.endpoints:
        clients["extractor_secondary"] = llm.chat_client_for_endpoint(sec)
        models["extractor_secondary"] = llm.endpoints[sec]["model"]
        models["extractor_hybrid_threshold"] = str(int(ec.get("hybrid_size_threshold_chars", 8000)))
    return clients, models


def _rec_to_claim(rec: dict, marker: str, fx: dict) -> dict:
    tr = rec.get("target_range")
    lo = tr[0] if isinstance(tr, list) and len(tr) == 2 else None
    hi = tr[1] if isinstance(tr, list) and len(tr) == 2 else None
    return {
        **rec, "marker": marker, "target_range_low": lo, "target_range_high": hi,
        "claim_id": None, "source_id": fx["source_id"], "source_url": fx.get("source_url"),
        "transcript_text": fx.get("transcript_text"), "source_type": fx.get("source_type", "blog"),
        "license": fx.get("license", "all_rights_reserved_public_web_page"),
    }


def _extract(fixtures: list[dict], run: PipelineRun, clients, models) -> list[tuple[dict, dict]]:
    """Stage 2 (dry-run) over fixtures; return (recommendation, fixture) pairs."""
    out = []
    for fx in fixtures:
        try:
            ingest.ingest_source(fx, clients, None, run, models=models, dry_run=True)
        except Exception as e:
            print(f"    extract error {fx.get('source_id')}: {e}")
            continue
        f = run.source_dir(fx["source_id"]) / "stage_2c_structurer.json"
        if f.exists():
            for rec in json.loads(f.read_text()):
                out.append((rec, fx))
    return out


def run_marker_iterative(marker: str, wave: str, *, write: bool = False,
                         fixtures_dir: str | None = None,
                         max_sources: int = MAX_SOURCES) -> dict:
    b = brief.load_brief(BRIEFS / wave / f"{marker}.yaml")
    sm_rows = brief.resolve_council_sm_rows(b)
    llm = LLMClient()
    clients, models = _stage2_clients(llm)

    combined = {k: [] for k in ("biomarker_claims", "range_facts", "provenance",
                                "legal_reviews", "research_studies", "quarantine")}
    rejection_log: list[dict] = []
    sources_by_id: dict[str, dict] = {}
    seen: set[str] = set()
    approved = 0

    # Optional fast path: reuse fixtures already on disk (skip live discovery).
    preset = None
    if fixtures_dir:
        preset = []
        for p in sorted(Path(fixtures_dir).glob(f"{marker}*.json")):
            try:
                preset.append(json.loads(p.read_text()))
            except Exception:
                continue

    rnd = 0
    while approved < STOP_COUNT and rnd < MAX_ROUNDS and len(seen) < max_sources:
        if preset is not None:
            fixtures = [fx for fx in preset if fx.get("source_id") not in seen]
        else:
            per = min(max_sources, (rnd + 1) * 4)  # widen each round
            fixtures, _ = web.discover_real_fixtures([marker], per_marker=per)
            fixtures = [fx for fx in fixtures if fx.get("source_id") not in seen]
        fixtures = [fx for fx in fixtures if fx.get("source_id")][: max_sources - len(seen)]
        if not fixtures:
            print(f"round {rnd}: no new sources — stopping")
            break
        for fx in fixtures:
            seen.add(fx["source_id"])
            sources_by_id[fx["source_id"]] = fx

        run = PipelineRun.create(run_id=f"iter-{marker}-r{rnd}")
        pairs = _extract(fixtures, run, clients, models)
        mo = [(rec, fx) for rec, fx in pairs
              if rec.get("paradigm") == "MO" and marker in (rec.get("applies_to_markers") or [])]
        print(f"round {rnd}: {len(fixtures)} sources -> {len(pairs)} recs, {len(mo)} MO/{marker}")

        for rec, fx in mo:
            claim = _rec_to_claim(rec, marker, fx)
            # SM sanity bound — cheap terminal reject before spending a council pass
            reason = council.sm_sanity_check(claim, sm_rows)
            if reason:
                rejection_log.append({"reason_code": "sm_sanity_fail", "detail": reason,
                                      "verbatim_quote": claim.get("verbatim_quote"),
                                      "source_id": claim.get("source_id")})
                continue
            res, _ = run_marker_live_session(
                marker, [claim], sm_rows, db=None, dry_run_persist=True,
                mo_supported=b.get("mo_supported"), mo_rationale=b.get("mo_rationale"))
            for k in combined:
                combined[k].extend(res.get(k, []))
            approved += len(res["biomarker_claims"])
            for q in res["quarantine"]:  # council/legal "quarantine" -> terminal reject (logged)
                rejection_log.append({"reason_code": (q.get("rejection_codes") or ["rejected"])[0],
                                      "detail": q.get("rejection_reason"),
                                      "verbatim_quote": q.get("verbatim_quote"),
                                      "source_id": q.get("source_id")})
            if approved >= STOP_COUNT:
                break
        rnd += 1

    combined.pop("quarantine", None)  # no quarantine concept in this runtime
    summary = {"marker": marker, "approved": approved, "range_facts": len(combined["range_facts"]),
               "rejected": len(rejection_log), "rounds": rnd, "sources_seen": len(seen),
               "terminal": "no_mo_support_found" if approved == 0 else "ok"}

    # Export (always) + persist (when --write)
    OUT.joinpath(marker).mkdir(parents=True, exist_ok=True)
    (OUT / marker / "range_facts.json").write_text(json.dumps(combined["range_facts"], indent=2, default=str))
    (OUT / marker / "rejection_log.json").write_text(json.dumps(rejection_log, indent=2, default=str))
    (OUT / marker / "iterate_summary.json").write_text(json.dumps(summary, indent=2, default=str))

    if write and combined["biomarker_claims"]:
        from code import db as dbmod
        db = dbmod.remote()
        for sid in {c.get("source_id") for c in combined["biomarker_claims"] if c.get("source_id")}:
            fx = sources_by_id.get(sid)
            if fx:
                db.upsert_source({
                    "id": sid, "url": fx.get("source_url"), "source_type": fx.get("source_type", "blog"),
                    "platform": fx.get("platform", ""), "title": fx.get("title", ""),
                    "author": fx.get("speaker_or_author", ""), "fetched_at": fx.get("retrieved_at"),
                    "published_at": fx.get("published_at"), "license": fx.get("license", ""),
                    "transcript_method": fx.get("transcript_method", ""),
                    "transcript_text": fx.get("transcript_text", ""), "raw_sha256": fx.get("transcript_sha256", ""),
                })
        persisted = persist.persist_marker_result(db, {**combined, "quarantine": []}, dry_run=False)
        summary["persisted"] = persisted

    return summary


def main() -> None:
    ap = argparse.ArgumentParser(description="No-quarantine iterate-discovery MO loop")
    ap.add_argument("marker")
    ap.add_argument("--wave", default="wave-0")
    ap.add_argument("--write", action="store_true", help="persist to agentic Supabase")
    ap.add_argument("--fixtures-dir", help="reuse existing fixtures instead of live discovery (fast test)")
    ap.add_argument("--max-sources", type=int, default=MAX_SOURCES)
    args = ap.parse_args()
    summary = run_marker_iterative(args.marker, args.wave, write=args.write,
                                   fixtures_dir=args.fixtures_dir, max_sources=args.max_sources)
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
