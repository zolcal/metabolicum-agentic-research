"""Live fasting-insulin run from the verified Stage-2a DeepSeek extraction.

The Stage-2b marker tagger failed to map the unit-only signal ("5-20 mIU/L") to
fasting-insulin and dropped a real, source-grounded MO claim (the tagger glossary
is term-based; the quote never says the word "insulin"). This runner does that
marker assignment — objectively correct from the verbatim quote — and runs the
REAL back half unchanged: council (re-verifies the verbatim quote against the
source) -> provenance -> legal (fair-use lane) -> assembly -> §18 range_facts ->
persist -> export. Nothing is rubber-stamped; the council can still reject.

Usage:
    python runs/run_fasting_insulin_live.py            # dry-run (no DB, no export)
    python runs/run_fasting_insulin_live.py --write    # persist to agentic Supabase + export
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))  # project root first so `code` is our pkg, not stdlib

from code.pipeline import brief
from code.pipeline.live_run import run_marker_live_session
BRIEFS = PROJECT_ROOT / "input" / "hermes-briefs"
FIXTURE = PROJECT_ROOT / "fixtures" / "sources" / "fasting-insulin-defeatdiabetes-com-au-01.json"
OUT = PROJECT_ROOT / "output" / "markers" / "fasting-insulin"

# The exact verbatim quote DeepSeek extracted at Stage 2a (confirmed present in
# the fetched source transcript).
QUOTE = (
    "While labs often list a “normal” range of 5-20 mIU/L, experts "
    "including Dr Brukner recommend aiming for less than 8 mIU/L, with under "
    "5 mIU/L being ideal."
)


def build_claims(transcript: str, source_id: str, source_url: str) -> list[dict]:
    base = dict(
        marker="fasting-insulin",
        applies_to_markers=["fasting-insulin"],
        paradigm="MO",
        units="mIU/L",
        verbatim_quote=QUOTE,
        claim_polarity="supports",
        speaker_or_author="Defeat Diabetes",
        source_id=source_id,
        source_url=source_url,
        transcript_text=transcript,
        source_type="blog",
        license="all_rights_reserved_public_web_page",
    )
    # claim_id is a nullable FK to the Stage-2 `claims` table (skipped here); leave
    # it NULL — traceability is via source_id + verbatim_quote.
    return [
        {**base, "claim_id": None, "target_value": 5, "direction": "below"},
        {**base, "claim_id": None, "target_value": 8, "direction": "below"},
    ]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true",
                    help="persist to the agentic Supabase + export to output/")
    args = ap.parse_args()

    fx = json.loads(FIXTURE.read_text())
    claims = build_claims(fx["transcript_text"], fx["source_id"], fx["source_url"])

    b = brief.load_brief(BRIEFS / "wave-0" / "fasting-insulin.yaml")
    sm_rows = brief.resolve_council_sm_rows(b)
    print(f"claims={len(claims)}  sm_rows={len(sm_rows)}  mo_supported={b.get('mo_supported')}")

    db = None
    if args.write:
        from code import db as dbmod
        db = dbmod.remote()
        # biomarker_claims.source_id FK -> sources(id); ensure the source row exists
        # (Stage-2 ran dry-run so it was never registered).
        db.upsert_source({
            "id": fx["source_id"], "url": fx["source_url"],
            "source_type": fx.get("source_type", "blog"), "platform": fx.get("platform", ""),
            "title": fx.get("title", ""), "author": fx.get("speaker_or_author", ""),
            "fetched_at": fx.get("retrieved_at"), "published_at": fx.get("published_at"),
            "license": fx.get("license", ""), "transcript_method": fx.get("transcript_method", ""),
            "transcript_text": fx.get("transcript_text", ""), "raw_sha256": fx.get("transcript_sha256", ""),
        })
        print(f"source upserted: {fx['source_id']}")

    res, persisted = run_marker_live_session(
        "fasting-insulin", claims, sm_rows, db=db, dry_run_persist=not args.write,
        mo_supported=b.get("mo_supported"), mo_rationale=b.get("mo_rationale"),
    )

    print(json.dumps({
        "approved": len(res["biomarker_claims"]),
        "range_facts": len(res["range_facts"]),
        "quarantined": len(res["quarantine"]),
        "provenance": [(p.get("target_locator"), p.get("resolution_status")) for p in res["provenance"]],
        "persist": persisted,
    }, indent=2, default=str))
    for rf in res["range_facts"]:
        print("\n=== range_fact ===")
        print(json.dumps(rf, indent=2, default=str))
    for q in res["quarantine"]:
        print("\n=== rejected ===")
        print(json.dumps({k: q.get(k) for k in ("rejection_stage", "rejection_reason", "rejection_codes")}, default=str))

    if args.write and res["range_facts"]:
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "range_facts.json").write_text(json.dumps(res["range_facts"], indent=2, default=str))
        (OUT / "result.json").write_text(json.dumps(res, indent=2, default=str))
        print(f"\nexported -> {OUT}")


if __name__ == "__main__":
    main()
