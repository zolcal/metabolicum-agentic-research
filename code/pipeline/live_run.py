"""Live single-marker runner — wires real LLM callers + live PubMed/Crossref
into orchestrate.run_marker_live. This is the live integration boundary; the
underlying decision/projection logic is covered by the offline contracts.

Usage:
    python -m code.pipeline.live_run --marker apob --wave wave-0 \
        --claims <extracted_claims.jsonl> [--write]   # default: persist dry-run
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from code.llm_client import LLMClient
from code.pipeline import brief, orchestrate, persist, provenance
from code.pipeline.stages import llm_call

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BRIEFS_DIR = PROJECT_ROOT / "input" / "hermes-briefs"


def make_role_caller(llm: LLMClient):
    """role_caller(role, system, user) -> parsed JSON dict, via the real LLM client."""
    def caller(role: str, system: str, user: dict) -> dict:
        client = llm.chat_client(role)
        resp = llm_call(
            client, system, json.dumps(user, default=str), schema=None,
            model=llm.model_name_for(role), max_tokens=llm.default_max_tokens_for(role), seed=42,
        )
        content = resp.get("content")
        return content if isinstance(content, dict) else {}
    return caller


def _default_source_for(claim: dict) -> dict:
    cited = claim.get("cited_paper") or {}
    return {
        "transcript_text": claim.get("transcript_text") or claim.get("verbatim_quote", ""),
        "source_url": claim.get("source_url") or cited.get("url", ""),
    }


def _default_legal_inputs_for(claim: dict) -> dict:
    return {
        "source_type": claim.get("source_type", "podcast"),
        "source_url": claim.get("source_url"),
        "license_value": claim.get("license"),
    }


def run_marker_live_session(
    marker: str, claims: list[dict], sm_rows: list[dict], *,
    llm: LLMClient | None = None, fetcher=None, db=None, dry_run_persist: bool = True,
    mo_supported: bool | None = None, mo_rationale: str | None = None,
):
    llm = llm or LLMClient()
    caller = make_role_caller(llm)
    res = orchestrate.run_marker_live(
        marker, claims, sm_rows,
        source_for=_default_source_for, role_caller=caller, legal_reviewer_caller=caller,
        fetcher=fetcher or provenance.live_fetcher, legal_inputs_for=_default_legal_inputs_for,
        mo_supported=mo_supported, mo_rationale=mo_rationale,
    )
    persisted = (persist.persist_marker_result(db, res, dry_run=dry_run_persist)
                 if db is not None else {"skipped": "no db client"})
    return res, persisted


def _load_claims(path: Path, marker: str, limit: int) -> list[dict]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        c = json.loads(line)
        markers = c.get("applies_to_markers") or [c.get("marker")]
        if marker in markers:
            c.setdefault("marker", marker)
            out.append(c)
        if len(out) >= limit:
            break
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--marker", default="apob")
    ap.add_argument("--wave", default="wave-0")
    ap.add_argument("--claims", required=True, help="extracted_claims.jsonl to source claims from")
    ap.add_argument("--limit", type=int, default=1)
    ap.add_argument("--write", action="store_true", help="actually write to Supabase (default: dry-run)")
    args = ap.parse_args()

    b = brief.load_brief(BRIEFS_DIR / args.wave / f"{args.marker}.yaml")
    sm_rows = brief.resolve_council_sm_rows(b)
    claims = _load_claims(Path(args.claims), args.marker, args.limit)
    print(f"loaded {len(claims)} {args.marker} claim(s); SM rows resolved: {len(sm_rows)}; "
          f"mo_supported={b.get('mo_supported')}")

    db = None
    if args.write:
        from code import db as dbmod
        db = dbmod.remote()

    res, persisted = run_marker_live_session(
        args.marker, claims, sm_rows, db=db, dry_run_persist=not args.write,
        mo_supported=b.get("mo_supported"), mo_rationale=b.get("mo_rationale"))

    print(json.dumps({
        "marker": args.marker,
        "approved": len(res["biomarker_claims"]),
        "range_facts": len(res["range_facts"]),
        "provenance": [(p.get("target_locator"), p.get("resolution_status")) for p in res["provenance"]],
        "research_studies": [s.get("slug") for s in res["research_studies"]],
        "quarantined": len(res["quarantine"]),
        "persist": persisted,
    }, indent=2, default=str))
    if res["range_facts"]:
        print("\n=== first range_fact ===")
        print(json.dumps(res["range_facts"][0], indent=2, default=str))


if __name__ == "__main__":
    main()
