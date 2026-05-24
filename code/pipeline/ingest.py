"""Phase 1 ingestion pipeline - orchestrates Stage 2 extraction chain.

Wraps the shared stages (code/pipeline/stages.py) with:
  - State management via PipelineRun (code/state.py)
  - DB writes for sources, claims, and marker links (code/db.py)
  - Multi-source batching
  - Error handling with quarantine records
  - Tool call logging (tool_call_log.jsonl)
  - Role-based LLM routing via LLMClient (DashScope by default)

Usage:
    # DashScope (default, production quality):
    python -m code.pipeline.ingest fixtures/sources/apob-peter-attia-source.json
    
    # Local llama-server (development, free):
    python -m code.pipeline.ingest --local fixtures/sources/apob-peter-attia-source.json
    
    # Multiple sources:
    python -m code.pipeline.ingest fixtures/sources/*.json

This module does NOT replace the acceptance harness. It builds orchestration
around the same extraction core that run_acceptance.py tests.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openai import OpenAI

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from code.pipeline.stages import (
    run_extractor,
    run_tagger,
    run_structurer,
    load_prompt,
)
from code.state import PipelineRun
from code.canonicalizer import canonical_json
from code.llm_client import LLMClient


# ── Cost tracking ─────────────────────────────────────────────────────────

class CostTracker:
    """Tracks token usage and estimates cost based on endpoint pricing."""

    def __init__(self):
        self.usage: dict[str, dict] = {}  # role -> {input_tokens, output_tokens, calls}

    def record(self, role: str, input_tokens: int | None, output_tokens: int | None):
        if role not in self.usage:
            self.usage[role] = {"input_tokens": 0, "output_tokens": 0, "calls": 0}
        self.usage[role]["input_tokens"] += input_tokens or 0
        self.usage[role]["output_tokens"] += output_tokens or 0
        self.usage[role]["calls"] += 1

    def estimate_cost(self, llm_config: LLMClient) -> dict[str, Any]:
        """Estimate total cost based on endpoint pricing in config."""
        total_input = 0
        total_output = 0
        total_cost_usd = 0.0
        by_role = {}

        for role, counts in self.usage.items():
            try:
                ec = llm_config.endpoint_for(role)
                cost_in = ec.get("cost_per_million_in", 0)
                cost_out = ec.get("cost_per_million_out", 0)
                role_cost = (
                    (counts["input_tokens"] / 1_000_000 * cost_in)
                    + (counts["output_tokens"] / 1_000_000 * cost_out)
                )
            except Exception:
                cost_in = cost_out = 0
                role_cost = 0.0

            total_input += counts["input_tokens"]
            total_output += counts["output_tokens"]
            total_cost_usd += role_cost

            by_role[role] = {
                "calls": counts["calls"],
                "input_tokens": counts["input_tokens"],
                "output_tokens": counts["output_tokens"],
                "cost_usd": round(role_cost, 4),
            }

        return {
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_cost_usd": round(total_cost_usd, 4),
            "by_role": by_role,
        }


# ── Single-source ingestion ───────────────────────────────────────────────

def ingest_source(
    fixture: dict[str, Any],
    clients: dict[str, OpenAI],
    db: Any,
    run: PipelineRun,
    *,
    seed: int = 42,
    models: dict[str, str] | None = None,
    dry_run: bool = False,
    cost_tracker: CostTracker | None = None,
) -> dict[str, Any]:
    """Process a single source through the Stage 2 chain.

    Args:
        fixture: Source fixture dict (must have transcript_text, source_id, etc.)
        clients: Dict of OpenAI clients keyed by role: {"extractor": ..., "tagger": ..., "structurer": ...}
        db: DBClient or LocalDBClient instance.
        run: PipelineRun for state management.
        seed: Random seed for determinism.
        models: Dict of model names keyed by role (default: all "qwen" for local).
        dry_run: If True, skip DB writes.
        cost_tracker: Optional CostTracker to record token usage.

    Returns:
        Dict with summary: source_id, claims_count, recommendations_count,
        elapsed_s, errors.
    """
    if models is None:
        models = {"extractor": "qwen", "tagger": "qwen", "structurer": "qwen"}
    source_id = fixture["source_id"]
    source_url = fixture["source_url"]
    source_dir = run.source_dir(source_id)
    tool_log: list[dict] = []

    result: dict[str, Any] = {
        "source_id": source_id,
        "source_url": source_url,
        "claims_count": 0,
        "recommendations_count": 0,
        "elapsed_s": 0.0,
        "errors": [],
    }

    t_start = time.time()

    try:
        # ── Step 1: Register source in DB ────────────────────────────
        if not dry_run:
            source_row = {
                "id": source_id,
                "url": source_url,
                "source_type": fixture.get("source_type", "unknown"),
                "platform": fixture.get("platform", ""),
                "title": fixture.get("title", ""),
                "author": fixture.get("speaker_or_author", ""),
                "fetched_at": fixture.get("retrieved_at"),
                "published_at": fixture.get("published_at"),
                "license": fixture.get("license", ""),
                "transcript_method": fixture.get("transcript_method", ""),
                "transcript_text": fixture.get("transcript_text", ""),
                "raw_sha256": fixture.get("transcript_sha256", ""),
            }
            db.upsert_source(source_row)
            run.log(f"Source registered: {source_url}", stage="sources")

        # Write transcript and metadata to run dir
        run.write_source_transcript(source_id, fixture["transcript_text"])
        run.write_source_metadata(source_id, {
            "source_id": source_id,
            "source_url": source_url,
            "source_type": fixture.get("source_type"),
            "platform": fixture.get("platform"),
            "speaker_or_author": fixture.get("speaker_or_author"),
            "retrieved_at": fixture.get("retrieved_at"),
            "source_language": fixture.get("source_language"),
            "speaker_registry_id": fixture.get("speaker_registry_id"),
        })

        # ── Step 2: Stage 2a — Content Extractor ─────────────────────
        run.log("Stage 2a: extractor starting", stage="sources")
        ext_result = run_extractor(clients["extractor"], fixture, seed=seed, model=models["extractor"])
        claims = ext_result["content"].get("claims", [])
        result["claims_count"] = len(claims)

        # Write stage artifact
        (source_dir / "stage_2a_extractor.json").write_text(
            json.dumps(ext_result["content"], indent=2)
        )
        tool_log.append({
            "stage": "stage_2_extraction",
            "tool": "llm_call",
            "role": "extractor",
            "model": ext_result["model"],
            "turn": 1,
            "input_tokens": ext_result["input_tokens"],
            "output_tokens": ext_result["output_tokens"],
            "elapsed_s": ext_result["elapsed_s"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        if cost_tracker:
            cost_tracker.record("extractor", ext_result["input_tokens"], ext_result["output_tokens"])
        run.log(
            f"Stage 2a: {len(claims)} claims extracted in {ext_result['elapsed_s']}s",
            stage="sources",
        )

        # ── Step 3: Stage 2b — Marker Tagger ─────────────────────────
        run.log(f"Stage 2b: tagger starting ({len(claims)} claims)", stage="sources")
        tagged = run_tagger(clients["tagger"], claims, fixture, seed=seed, model=models["tagger"])

        (source_dir / "stage_2b_tagger.json").write_text(
            json.dumps(tagged, indent=2)
        )
        tool_log.append({
            "stage": "stage_2_tagging",
            "tool": "llm_call",
            "role": "tagger",
            "model": ext_result["model"],
            "turn": 2,
            "calls": len(claims),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        if cost_tracker:
            # Tagger makes one call per claim; estimate tokens
            cost_tracker.record("tagger", len(claims) * 1500, len(claims) * 400)
        run.log(f"Stage 2b: {len(claims)} claims tagged", stage="sources")

        # ── Step 4: Stage 2c — Demographic Structurer ────────────────
        run.log("Stage 2c: structurer starting", stage="sources")
        recommendations = run_structurer(clients["structurer"], claims, tagged, fixture, seed=seed, model=models["structurer"])
        result["recommendations_count"] = len(recommendations)

        (source_dir / "stage_2c_structurer.json").write_text(
            json.dumps(recommendations, indent=2)
        )
        tool_log.append({
            "stage": "stage_2_structuring",
            "tool": "llm_call",
            "role": "structurer",
            "model": ext_result["model"],
            "turn": 3,
            "recommendations": len(recommendations),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        if cost_tracker:
            # Structurer makes one call per claim; estimate tokens
            cost_tracker.record("structurer", len(claims) * 2000, len(recommendations) * 800)
        run.log(
            f"Stage 2c: {len(recommendations)} recommendations structured",
            stage="sources",
        )

        # ── Step 5: Write claims to DB ───────────────────────────────
        if not dry_run and recommendations:
            claims_written = 0
            markers_written = 0
            for rec in recommendations:
                # Split target_range array into low/high columns
                target_range = rec.get("target_range")
                target_range_low = None
                target_range_high = None
                if isinstance(target_range, list) and len(target_range) == 2:
                    target_range_low = target_range[0]
                    target_range_high = target_range[1]

                claim_data = {
                    "source_id": source_id,
                    "verbatim_quote": rec.get("verbatim_quote", ""),
                    "paradigm": rec.get("paradigm", "SM"),
                    "population": rec.get("population", {}),
                    "units": rec.get("units", ""),
                    "direction": rec.get("direction"),
                    "target_value": rec.get("target_value"),
                    "target_range_low": target_range_low,
                    "target_range_high": target_range_high,
                    "claim_polarity": rec.get("claim_polarity", "supports"),
                    "speaker_or_author": rec.get("speaker_or_author", ""),
                    "speaker_registry_id": rec.get("speaker_registry_id"),
                    "source_language": rec.get("source_language", "en"),
                    "translated_quote": rec.get("translated_quote"),
                    "translation_method": rec.get("translation_method", "none"),
                    "cited_paper": rec.get("cited_paper"),
                    "extraction_model": rec.get("extraction_model", ""),
                    "extractor_confidence": rec.get("extractor_confidence", 0.8),
                }
                try:
                    db_row = db.insert_claim(claim_data)
                    claim_db_id = db_row.get("id")
                    claims_written += 1

                    # Write marker links
                    for marker in rec.get("applies_to_markers", []):
                        db.upsert_claim_markers(claim_db_id, [
                            {"marker": marker, "confidence": rec.get("extractor_confidence", 0.8)}
                        ])
                        markers_written += 1
                except Exception as e:
                    result["errors"].append(f"DB write error for claim: {e}")

            run.log(
                f"DB: {claims_written} claims, {markers_written} marker links written",
                stage="sources",
            )

        # Write claims JSONL to run dir
        run.write_extracted_claims(source_id, recommendations)

        # ── Step 6: Write tool call log ──────────────────────────────
        log_path = source_dir / "tool_call_log.jsonl"
        with open(log_path, "w") as f:
            for entry in tool_log:
                f.write(json.dumps(entry) + "\n")

    except Exception as e:
        result["errors"].append(str(e))
        run.log(f"Source ingestion error: {e}", stage="sources")
        if not dry_run:
            try:
                db.insert_quarantine({
                    "source_id": source_id,
                    "rejection_stage": "ingestion",
                    "rejection_reason": str(e),
                    "rejection_codes": ["stage_2_failure"],
                    "payload": {"source_url": source_url},
                })
            except Exception:
                pass  # quarantine write is best-effort

    result["elapsed_s"] = round(time.time() - t_start, 2)
    return result


# ── Batch ingestion ───────────────────────────────────────────────────────

def ingest_batch(
    fixture_paths: list[Path],
    clients: dict[str, OpenAI],
    db: Any,
    run: PipelineRun,
    *,
    seed: int = 42,
    models: dict[str, str] | None = None,
    dry_run: bool = False,
    cost_tracker: CostTracker | None = None,
) -> list[dict[str, Any]]:
    """Process multiple source fixtures sequentially.

    Args:
        fixture_paths: List of paths to source fixture JSON files.
        clients: Dict of OpenAI clients keyed by role.
        db: DBClient or LocalDBClient.
        run: PipelineRun for state management.
        seed: Random seed.
        models: Dict of model names keyed by role.
        dry_run: Skip DB writes.
        cost_tracker: Optional CostTracker to record token usage.

    Returns:
        List of result dicts (one per source).
    """
    results = []

    run.write_stage_state(
        "sources",
        status="running",
        metrics={"total_sources": len(fixture_paths)},
    )
    run.log(f"Batch ingestion starting: {len(fixture_paths)} sources", stage="sources")

    for i, fpath in enumerate(fixture_paths, 1):
        print(f"  [{i}/{len(fixture_paths)}] {fpath.name}...", end=" ", flush=True)
        fixture = json.loads(fpath.read_text())

        source_result = ingest_source(
            fixture, clients, db, run,
            seed=seed, models=models, dry_run=dry_run, cost_tracker=cost_tracker,
        )

        status = "OK" if not source_result["errors"] else "ERROR"
        print(
            f"{source_result['claims_count']} claims, "
            f"{source_result['recommendations_count']} recs, "
            f"{source_result['elapsed_s']}s [{status}]"
        )

        if source_result["errors"]:
            for err in source_result["errors"]:
                print(f"    ! {err}")

        results.append(source_result)

    # Complete or fail the stage
    total_claims = sum(r["claims_count"] for r in results)
    total_recs = sum(r["recommendations_count"] for r in results)
    total_errors = sum(len(r["errors"]) for r in results)

    if total_errors > 0 and total_recs == 0:
        run.fail_stage(
            "sources",
            error=f"All {len(fixture_paths)} sources failed",
            metrics={
                "sources_processed": len(results),
                "total_claims": total_claims,
                "total_recommendations": total_recs,
                "total_errors": total_errors,
            },
        )
    else:
        run.complete_stage(
            "sources",
            metrics={
                "sources_processed": len(results),
                "total_claims": total_claims,
                "total_recommendations": total_recs,
                "total_errors": total_errors,
            },
        )

    return results


# ── CLI ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Phase 1 Ingestion Pipeline — Stage 2 extraction chain with DB writes"
    )
    parser.add_argument(
        "fixtures",
        nargs="+",
        type=Path,
        help="Source fixture JSON files to ingest",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--local", action="store_true", default=True,
                       help="Use local psycopg2 DB (default)")
    group.add_argument("--remote", action="store_true",
                       help="Use remote Supabase DB")
    parser.add_argument("--local-llm", action="store_true",
                        help="Use local llama-server instead of DashScope (free, slower)")
    parser.add_argument("--base-url", type=str, default=None,
                        help="Override LLM base URL (for custom endpoints)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for determinism")
    parser.add_argument("--run-id", type=str, default=None,
                        help="Run ID (default: UTC timestamp)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Skip DB writes, only run LLM chain and write artifacts")
    args = parser.parse_args()

    # Validate fixtures exist
    for fpath in args.fixtures:
        if not fpath.is_file():
            sys.exit(f"Fixture not found: {fpath}")

    # Load secrets/.env into os.environ (for LLMClient API keys)
    env_file = PROJECT_ROOT / "secrets" / ".env"
    if env_file.is_file():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                if v and k.strip() not in os.environ:
                    os.environ[k.strip()] = v.strip()

    # Initialize DB
    if args.remote:
        from code.db import remote as get_db
        db = get_db()
    else:
        from code.db import local_psycopg
        db = local_psycopg()

    # Initialize LLM clients (role-based routing)
    llm_config = LLMClient()
    cost_tracker = CostTracker()

    if args.base_url:
        # Explicit override: single client for all roles
        base_url = args.base_url
        client = OpenAI(base_url=base_url, api_key="not-needed")
        clients = {"extractor": client, "tagger": client, "structurer": client}
        models = {"extractor": "qwen", "tagger": "qwen", "structurer": "qwen"}
        llm_label = f"custom ({base_url})"
    elif args.local_llm:
        # Local llama-server for all roles (free, dev mode)
        base_url = "http://127.0.0.1:8080/v1"
        client = OpenAI(base_url=base_url, api_key="not-needed")
        clients = {"extractor": client, "tagger": client, "structurer": client}
        models = {"extractor": "qwen", "tagger": "qwen", "structurer": "qwen"}
        llm_label = f"local ({base_url})"
    else:
        # DashScope (production, role-based routing from config)
        clients = {
            "extractor": llm_config.chat_client("extractor"),
            "tagger": llm_config.chat_client("tagger"),
            "structurer": llm_config.chat_client("structurer"),
        }
        models = {
            "extractor": llm_config.model_name_for("extractor"),
            "tagger": llm_config.model_name_for("tagger"),
            "structurer": llm_config.model_name_for("structurer"),
        }
        extractor_ec = llm_config.endpoint_for("extractor")
        llm_label = f"DashScope ({extractor_ec['model']})"

    # Create pipeline run
    run = PipelineRun.create(run_id=args.run_id)

    print(f"{'='*60}")
    print(f"  Phase 1 Ingestion Pipeline")
    print(f"  Run ID: {run.run_id}")
    print(f"  DB: {db.label}")
    print(f"  LLM: {llm_label}")
    print(f"  Sources: {len(args.fixtures)}")
    print(f"  Seed: {args.seed}")
    print(f"  Dry run: {args.dry_run}")
    print(f"{'='*60}\n")

    results = ingest_batch(
        args.fixtures, clients, db, run,
        seed=args.seed, models=models, dry_run=args.dry_run, cost_tracker=cost_tracker,
    )

    # Summary
    total_claims = sum(r["claims_count"] for r in results)
    total_recs = sum(r["recommendations_count"] for r in results)
    total_errors = sum(len(r["errors"]) for r in results)
    total_time = sum(r["elapsed_s"] for r in results)

    # Cost estimate
    cost_estimate = cost_tracker.estimate_cost(llm_config)

    print(f"\n{'='*60}")
    print(f"  Summary")
    print(f"  Sources processed: {len(results)}")
    print(f"  Total claims extracted: {total_claims}")
    print(f"  Total recommendations: {total_recs}")
    print(f"  Total errors: {total_errors}")
    print(f"  Total time: {total_time:.1f}s")
    if cost_estimate["total_cost_usd"] > 0:
        print(f"  Estimated cost: ${cost_estimate['total_cost_usd']:.4f}")
        print(f"    Input tokens: {cost_estimate['total_input_tokens']:,}")
        print(f"    Output tokens: {cost_estimate['total_output_tokens']:,}")
    print(f"  Run directory: {run.run_dir}")
    print(f"{'='*60}")

    # Write batch summary
    summary = {
        "run_id": run.run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "db": db.label,
        "llm": llm_label,
        "seed": args.seed,
        "sources": [
            {
                "source_id": r["source_id"],
                "source_url": r["source_url"],
                "claims": r["claims_count"],
                "recommendations": r["recommendations_count"],
                "elapsed_s": r["elapsed_s"],
                "errors": r["errors"],
            }
            for r in results
        ],
        "totals": {
            "sources": len(results),
            "claims": total_claims,
            "recommendations": total_recs,
            "errors": total_errors,
            "elapsed_s": round(total_time, 1),
        },
        "cost_estimate": cost_estimate,
    }
    summary_path = run.run_dir / "ingest_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))

    if total_errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
