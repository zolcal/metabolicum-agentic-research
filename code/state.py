"""Run state management per §10 filesystem layout.

Manages the per-run directory structure and state.json files that serve
as canonical handoff between pipeline stages.

Usage:
    from code.state import PipelineRun

    run = PipelineRun.create()  # creates runs/<timestamp>/
    run.write_stage_state("discovery", status="running", metrics={"sources_found": 5})
    run.complete_stage("discovery", output_files=["discovery/ranked_sources.json"])
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = PROJECT_ROOT / "runs"


class StageState:
    """Represents the state.json for a single pipeline stage."""

    def __init__(self, data: dict[str, Any]):
        self.data = data

    @property
    def status(self) -> str:
        return self.data.get("status", "pending")

    @property
    def is_complete(self) -> bool:
        return self.status == "completed"

    @property
    def is_failed(self) -> bool:
        return self.status in ("failed", "quarantined")

    def to_dict(self) -> dict[str, Any]:
        return self.data

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.data, indent=indent, default=str)


class PipelineRun:
    """Manages a single pipeline run's filesystem state.

    Directory layout per §10:
        runs/<run_id>/
            discovery/
            sources/<source_id>/
            council/
            provenance/
            legal/
            assembly/<marker>/
            run.log
    """

    def __init__(self, run_dir: Path):
        self.run_dir = run_dir
        self.run_id = run_dir.name

    @classmethod
    def create(cls, run_id: str | None = None) -> PipelineRun:
        """Create a new run directory with timestamp-based ID."""
        if run_id is None:
            run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_dir = RUNS_DIR / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        # Create stage directories
        for stage in ["discovery", "sources", "council", "provenance", "legal", "assembly"]:
            (run_dir / stage).mkdir(exist_ok=True)

        # Initialize run log
        run_log = run_dir / "run.log"
        if not run_log.exists():
            run_log.write_text(
                f"# Pipeline Run: {run_id}\n"
                f"# Created: {datetime.now(timezone.utc).isoformat()}\n\n"
            )

        return cls(run_dir)

    @classmethod
    def load(cls, run_id: str) -> PipelineRun:
        """Load an existing run directory."""
        run_dir = RUNS_DIR / run_id
        if not run_dir.is_dir():
            raise FileNotFoundError(f"Run directory not found: {run_dir}")
        return cls(run_dir)

    # ── Stage state management ───────────────────────────────────

    def stage_dir(self, stage: str) -> Path:
        """Get the directory for a stage."""
        return self.run_dir / stage

    def source_dir(self, source_id: str) -> Path:
        """Get the directory for a specific source."""
        d = self.run_dir / "sources" / source_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def marker_dir(self, marker: str) -> Path:
        """Get the assembly directory for a specific marker."""
        d = self.run_dir / "assembly" / marker
        d.mkdir(parents=True, exist_ok=True)
        return d

    def write_stage_state(
        self,
        stage: str,
        *,
        status: str = "pending",
        input_files: list[str] | None = None,
        output_files: list[str] | None = None,
        model_endpoints: list[str] | None = None,
        tool_manifest: str | None = None,
        metrics: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> StageState:
        """Write or update state.json for a stage."""
        stage_dir = self.stage_dir(stage)
        stage_dir.mkdir(parents=True, exist_ok=True)

        state_path = stage_dir / "state.json"
        existing: dict[str, Any] = {}
        if state_path.exists():
            existing = json.loads(state_path.read_text())

        now = datetime.now(timezone.utc).isoformat()

        state_data = {
            "schema_version": "1",
            "run_id": self.run_id,
            "stage": stage,
            "status": status,
            "input_files": input_files or existing.get("input_files", []),
            "output_files": output_files or existing.get("output_files", []),
            "started_at": existing.get("started_at", now),
            "completed_at": now if status in ("completed", "failed", "quarantined") else None,
            "model_endpoints": model_endpoints or existing.get("model_endpoints", []),
            "tool_manifest": tool_manifest or existing.get("tool_manifest", stage),
            "metrics": metrics or existing.get("metrics", {}),
            "error": error,
        }

        state_path.write_text(json.dumps(state_data, indent=2, default=str))
        return StageState(state_data)

    def read_stage_state(self, stage: str) -> StageState | None:
        """Read state.json for a stage, or None if it doesn't exist."""
        state_path = self.stage_dir(stage) / "state.json"
        if not state_path.exists():
            return None
        return StageState(json.loads(state_path.read_text()))

    def complete_stage(
        self,
        stage: str,
        *,
        output_files: list[str] | None = None,
        metrics: dict[str, Any] | None = None,
    ) -> StageState:
        """Mark a stage as completed."""
        return self.write_stage_state(
            stage,
            status="completed",
            output_files=output_files,
            metrics=metrics,
        )

    def fail_stage(self, stage: str, *, error: str, metrics: dict | None = None) -> StageState:
        """Mark a stage as failed."""
        return self.write_stage_state(
            stage,
            status="failed",
            error=error,
            metrics=metrics,
        )

    def quarantine_stage(
        self, stage: str, *, error: str, metrics: dict | None = None
    ) -> StageState:
        """Mark a stage as quarantined."""
        return self.write_stage_state(
            stage,
            status="quarantined",
            error=error,
            metrics=metrics,
        )

    # ── Run log ──────────────────────────────────────────────────

    def log(self, message: str, *, stage: str | None = None) -> None:
        """Append a message to run.log."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        prefix = f"[{stage}] " if stage else ""
        line = f"{now} {prefix}{message}\n"
        with open(self.run_dir / "run.log", "a") as f:
            f.write(line)

    # ── Discovery outputs ────────────────────────────────────────

    def write_discovery_output(self, platform: str, data: Any) -> Path:
        """Write a discovery platform output (e.g., youtube.json)."""
        path = self.stage_dir("discovery") / f"{platform}.json"
        path.write_text(json.dumps(data, indent=2, default=str))
        return path

    def write_ranked_sources(self, sources: list[dict]) -> Path:
        """Write the ranked_sources.json summary."""
        path = self.stage_dir("discovery") / "ranked_sources.json"
        path.write_text(json.dumps(sources, indent=2, default=str))
        return path

    def write_sanitized_envelopes(self, envelopes: list[dict]) -> Path:
        """Write research_target_envelopes.sanitized.json for this run."""
        path = self.run_dir / "research_target_envelopes.sanitized.json"
        path.write_text(json.dumps(envelopes, indent=2, default=str))
        return path

    # ── Source outputs ────────────────────────────────────────────

    def write_source_transcript(self, source_id: str, transcript: str) -> Path:
        """Write a source transcript."""
        path = self.source_dir(source_id) / "transcript.txt"
        path.write_text(transcript)
        return path

    def write_source_metadata(self, source_id: str, metadata: dict) -> Path:
        """Write source.json metadata."""
        path = self.source_dir(source_id) / "source.json"
        path.write_text(json.dumps(metadata, indent=2, default=str))
        return path

    def write_extracted_claims(self, source_id: str, claims: list[dict]) -> Path:
        """Write extracted_claims.jsonl for a source."""
        path = self.source_dir(source_id) / "extracted_claims.jsonl"
        lines = [json.dumps(c, default=str) for c in claims]
        path.write_text("\n".join(lines) + "\n" if lines else "")
        return path

    # ── Council outputs ──────────────────────────────────────────

    def write_council_accepted(self, claims: list[dict]) -> Path:
        """Write accepted_claims.jsonl."""
        path = self.stage_dir("council") / "accepted_claims.jsonl"
        lines = [json.dumps(c, default=str) for c in claims]
        path.write_text("\n".join(lines) + "\n" if lines else "")
        return path

    def write_council_rejected(self, claims: list[dict]) -> Path:
        """Write rejected_claims.jsonl."""
        path = self.stage_dir("council") / "rejected_claims.jsonl"
        lines = [json.dumps(c, default=str) for c in claims]
        path.write_text("\n".join(lines) + "\n" if lines else "")
        return path

    def write_claim_envelope_evaluations(self, evaluations: list[dict]) -> Path:
        """Write council claim-envelope alignment evaluations."""
        path = self.stage_dir("council") / "claim_envelope_evaluations.jsonl"
        lines = [json.dumps(e, default=str) for e in evaluations]
        path.write_text("\n".join(lines) + "\n" if lines else "")
        return path

    # ── Assembly outputs ─────────────────────────────────────────

    def write_artifact_sql(self, marker: str, sql: str) -> Path:
        """Write the terminal artifact.sql for a marker."""
        path = self.marker_dir(marker) / "artifact.sql"
        path.write_text(sql)
        return path

    # ── Run status ───────────────────────────────────────────────

    def all_stages_complete(self) -> bool:
        """Check if all pipeline stages are completed."""
        for stage in ["discovery", "sources", "council", "provenance", "legal", "assembly"]:
            state = self.read_stage_state(stage)
            if state is None or not state.is_complete:
                return False
        return True

    def summary(self) -> dict[str, Any]:
        """Get a summary of the run's stage states."""
        result = {"run_id": self.run_id, "stages": {}}
        for stage in ["discovery", "sources", "council", "provenance", "legal", "assembly"]:
            state = self.read_stage_state(stage)
            if state:
                result["stages"][stage] = {
                    "status": state.status,
                    "metrics": state.data.get("metrics", {}),
                    "error": state.data.get("error"),
                }
            else:
                result["stages"][stage] = {"status": "not_started"}
        return result


# ── CLI ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "create":
        run = PipelineRun.create()
        print(f"Created run: {run.run_id}")
        print(f"Directory: {run.run_dir}")
    elif len(sys.argv) > 1 and sys.argv[1] == "list":
        if RUNS_DIR.exists():
            for d in sorted(RUNS_DIR.iterdir()):
                if d.is_dir() and not d.name.startswith("."):
                    print(f"  {d.name}")
        else:
            print("No runs directory found.")
    else:
        print("Usage: python -m code.state [create|list]")
