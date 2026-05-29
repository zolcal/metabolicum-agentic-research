#!/usr/bin/env python3
"""Acceptance check for §10 state.json contract compliance."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

import jsonschema

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = PROJECT_ROOT / "code" / "schemas" / "state.schema.json"

sys.path.insert(0, str(PROJECT_ROOT))
from code import state  # noqa: E402


def _load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def validate_state_file(path: Path, schema: dict | None = None) -> None:
    jsonschema.validate(
        json.loads(path.read_text(encoding="utf-8")),
        schema or _load_schema(),
        format_checker=jsonschema.FormatChecker(),
    )


def run_contract_check(work_dir: Path | None = None) -> list[Path]:
    """Create a default run, write each stage state, and validate them."""
    schema = _load_schema()

    if work_dir is None:
        scratch_root = PROJECT_ROOT / ".state-contract-check"
        scratch_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="run-", dir=scratch_root) as temp_dir:
            return run_contract_check(Path(temp_dir))

    work_dir.mkdir(parents=True, exist_ok=True)
    original_runs_dir = state.RUNS_DIR
    try:
        state.RUNS_DIR = work_dir / "runs"
        run = state.PipelineRun.create()
        run.write_stage_state("discovery", status="completed")
        run.write_stage_state("sources", status="completed")
        run.write_stage_state("council", status="completed")
        run.write_stage_state("provenance", status="completed")
        run.fail_stage("legal", error="contract check legal failure sample")
        run.quarantine_stage("assembly", error="contract check assembly quarantine sample")

        state_paths = sorted(run.run_dir.glob("*/state.json"))
        for path in state_paths:
            validate_state_file(path, schema)
        return state_paths
    finally:
        state.RUNS_DIR = original_runs_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate generated stage state.json files against state.schema.json")
    parser.add_argument("--work-dir", type=Path, help="Project-local scratch directory for generated check run")
    args = parser.parse_args()

    try:
        state_paths = run_contract_check(args.work_dir)
    except Exception as exc:
        print(f"state contract check failed: {exc}", file=sys.stderr)
        raise

    print(f"Validated {len(state_paths)} state.json file(s)")
    for path in state_paths:
        print(path)


if __name__ == "__main__":
    main()
