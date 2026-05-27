#!/usr/bin/env python3
"""10-marker validation runner with hybrid tagger (rigid + semantic fallback).

Processes all existing fixtures + discovers sources for missing markers,
then runs Stage 2 (extractor → tagger → structurer) on each.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from openai import OpenAI

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from code.pipeline.stages import run_extractor, run_tagger, run_structurer
from code.pipeline.semantic_fallback import batch_semantic_fallback

FIXTURES_DIR = PROJECT_ROOT / "fixtures" / "sources"
RUNS_DIR = PROJECT_ROOT / "runs" / "10-marker-validation"
RUNS_DIR.mkdir(parents=True, exist_ok=True)

MARKERS = [
    "apob", "hba1c", "fasting-insulin", "lpa", "igf-1",
    "vitamin-d", "crp-standard", "hdl-cholesterol", "uric-acid", "fructosamine",
]

# Clients — choose local (free, slow) or cloud (fast, paid)
LOCAL_CLIENT = OpenAI(base_url="http://127.0.0.1:8080/v1", api_key="dummy")
DASHSCOPE_CLIENT = OpenAI(
    base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    api_key=os.environ.get("DASHSCOPE_API_KEY", "dummy"),
)
OPENROUTER_CLIENT = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY", "dummy"),
    default_headers={"HTTP-Referer": "https://metabolicum.com", "X-Title": "Metabolicum Research"},
)
DEEPSEEK_CLIENT = OpenAI(
    base_url="https://api.deepseek.com/v1",
    api_key=os.environ.get("DEEPSEEK_API_KEY", "dummy"),
)


def load_fixtures() -> list[dict]:
    fixtures = []
    for p in FIXTURES_DIR.glob("*.json"):
        if p.name.startswith("."):
            continue
        try:
            fixtures.append(json.loads(p.read_text()))
        except Exception as e:
            print(f"  ⚠️  Failed to load {p.name}: {e}")
    return fixtures


def run_fixture(fixture: dict, run_id: str, client, model: str, extractor_client=None, extractor_model=None) -> dict:
    """Run full Stage 2 on a single fixture.

    Args:
        extractor_client: Optional separate client for Stage 2a (extractor).
            If provided, used instead of `client` for extraction.
        extractor_model: Optional separate model for Stage 2a.
    """
    extract_cli = extractor_client or client
    extract_mdl = extractor_model or model
    result = {
        "fixture_id": fixture["source_id"],
        "title": fixture.get("title", ""),
        "expected_markers": fixture.get("expected_markers", []),
        "run_id": run_id,
        "model": model,
        "extractor_model": extract_mdl,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        print(f"\n🔬 [{fixture['source_id']}] {fixture.get('title', '')[:60]}...")
        print(f"   Expected: {fixture.get('expected_markers', [])}")

        # Stage 2a: Extractor
        print(f"   → Extractor ({extract_mdl})...", end="", flush=True)
        extracted = run_extractor(extract_cli, fixture, seed=42, model=extract_mdl)
        claims = extracted["content"]["claims"]
        print(f" {len(claims)} claims")

        # Stage 2b: Tagger (with semantic fallback)
        print(f"   → Tagger ({model})...", end="", flush=True)
        tagged = run_tagger(
            client, claims, fixture, seed=42, model=model,
            use_semantic_fallback=True, semantic_threshold=0.85,
        )
        rigid_matched = sum(1 for t in tagged if not t.get("no_marker_match") and not t.get("semantic_fallback"))
        fallback_matched = sum(1 for t in tagged if t.get("semantic_fallback"))
        unmatched = sum(1 for t in tagged if t.get("no_marker_match"))
        print(f" rigid={rigid_matched}, fallback={fallback_matched}, unmatched={unmatched}")

        # Stage 2c: Structurer
        print(f"   → Structurer ({model})...", end="", flush=True)
        recs = run_structurer(client, claims, tagged, fixture, seed=42, model=model)
        print(f" {len(recs)} recommendations")

        result.update({
            "status": "success",
            "claims_count": len(claims),
            "rigid_matched": rigid_matched,
            "fallback_matched": fallback_matched,
            "unmatched": unmatched,
            "recommendations_count": len(recs),
            "recommendations": recs,
            "tagged": tagged,
            "finished_at": datetime.now(timezone.utc).isoformat(),
        })

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        result["finished_at"] = datetime.now(timezone.utc).isoformat()
        print(f"   ❌ ERROR: {e}")

    return result


def main():
    parser = argparse.ArgumentParser(description="10-marker validation runner")
    parser.add_argument("--cloud", action="store_true", help="Use default cloud model")
    parser.add_argument("--local", action="store_true", help="Use local LLM (free, fast with Gemma 4)")
    parser.add_argument("--hybrid", action="store_true", help="Hybrid: cloud extractor + local tagger/structurer")
    parser.add_argument("--local-model", default="gemma4-dflash", help="Model ID for local inference")
    parser.add_argument("--model", default="deepseek-chat", help="Model ID to use")
    parser.add_argument("--provider", choices=["dashscope", "openrouter", "deepseek"], default="deepseek", help="Cloud provider")
    args = parser.parse_args()

    extractor_client = None
    extractor_model = None

    if args.hybrid:
        client = LOCAL_CLIENT
        model = args.local_model
        if args.provider == "dashscope":
            extractor_client = DASHSCOPE_CLIENT
        elif args.provider == "openrouter":
            extractor_client = OPENROUTER_CLIENT
        else:
            extractor_client = DEEPSEEK_CLIENT
        extractor_model = args.model
        print(f"HYBRID mode: extractor={args.model} ({args.provider}), tagger/structurer={model} (local)")
    elif args.local:
        client = LOCAL_CLIENT
        model = args.local_model
        print(f"Using LOCAL {model} (free, fast)")
    elif args.provider == "dashscope":
        client = DASHSCOPE_CLIENT
        model = args.model
        print(f"Using DASHSCOPE {model} (fast, paid)")
    elif args.provider == "openrouter":
        client = OPENROUTER_CLIENT
        model = args.model
        print(f"Using OPENROUTER {model} (fast, paid)")
    else:
        client = DEEPSEEK_CLIENT
        model = args.model
        print(f"Using DIRECT DEEPSEEK {model} (fast, paid)")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    print(f"Run ID: {run_id}")
    print(f"Output: {run_dir}")

    fixtures = load_fixtures()
    print(f"Loaded {len(fixtures)} fixtures")

    # Group by expected marker
    by_marker: dict[str, list[dict]] = {m: [] for m in MARKERS}
    for f in fixtures:
        for m in f.get("expected_markers", []):
            if m in by_marker:
                by_marker[m].append(f)

    print("\nFixture coverage:")
    for m in MARKERS:
        count = len(by_marker[m])
        status = "✅" if count > 0 else "❌"
        print(f"  {status} {m}: {count} fixture(s)")

    results = []
    for marker in MARKERS:
        fixtures_for_marker = by_marker[marker]
        if not fixtures_for_marker:
            print(f"\n⏭️  Skipping {marker} — no fixtures")
            results.append({
                "marker": marker,
                "status": "skipped",
                "reason": "no_fixtures",
            })
            continue

        for fixture in fixtures_for_marker:
            res = run_fixture(fixture, run_id, client, model, extractor_client, extractor_model)
            res["marker"] = marker
            results.append(res)

            # Save individual result
            safe_title = "".join(c if c.isalnum() else "_" for c in fixture.get("title", "untitled"))[:40]
            out_path = run_dir / f"{marker}_{safe_title}_{fixture['source_id'][:8]}.json"
            out_path.write_text(json.dumps(res, indent=2, default=str))

    # Summary
    summary = {
        "run_id": run_id,
        "markers_total": len(MARKERS),
        "fixtures_processed": len([r for r in results if r.get("status") == "success"]),
        "errors": len([r for r in results if r.get("status") == "error"]),
        "skipped": len([r for r in results if r.get("status") == "skipped"]),
        "total_recommendations": sum(r.get("recommendations_count", 0) for r in results),
        "results": results,
    }
    summary_path = run_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, default=str))

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Fixtures processed: {summary['fixtures_processed']}")
    print(f"Errors: {summary['errors']}")
    print(f"Skipped (no fixtures): {summary['skipped']}")
    print(f"Total recommendations: {summary['total_recommendations']}")
    print(f"Output dir: {run_dir}")


if __name__ == "__main__":
    main()
