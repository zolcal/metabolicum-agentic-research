"""MetaSync MO handoff package writer.

Implements the file-based handoff contract in the metasync MO handoff process doc
(2026-05-31): a frozen, reviewable, hashable package — NOT SQL, NOT a DB write.

    output/mo-handoffs/{batch_slug}/
      manifest.json                         # identity, counts, per-file SHA-256
      markers/{subject_slug}/mo_export.json  # per-marker export (per-marker layout)
      rejected-items.jsonl                  # batch-aggregated rejects (optional)

mo_export.json is kept timestamp-free so it is byte-reproducible; the run
timestamp lives only in manifest.json.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HANDOFFS_DIR = PROJECT_ROOT / "output" / "mo-handoffs"
SCHEMA_VERSION = "1"
EXPORTER_VERSION = "mo-export-v1"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _pipeline_version() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=PROJECT_ROOT,
                             capture_output=True, text=True, timeout=5)
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def write_marker_export(batch_slug: str, marker: str, mo_export: dict) -> Path:
    """Write one marker's mo_export.json into the batch package (per-marker layout)."""
    d = HANDOFFS_DIR / batch_slug / "markers" / marker
    d.mkdir(parents=True, exist_ok=True)
    path = d / "mo_export.json"
    path.write_text(json.dumps(mo_export, indent=2, sort_keys=True, default=str))
    return path


def build_manifest(batch_slug: str, *, source_run_id: str | None = None) -> dict[str, Any]:
    """Scan the batch's per-marker exports and (re)write manifest.json with counts
    and a SHA-256 for every exported file. Returns the manifest dict."""
    batch_dir = HANDOFFS_DIR / batch_slug
    files = sorted(batch_dir.glob("markers/*/mo_export.json"))

    subject_count = rf_count = sa_count = rej_count = 0
    rejected_all: list[dict] = []
    file_entries: list[dict] = []
    for f in files:
        e = json.loads(f.read_text())
        subject_count += 1
        rf_count += len(e.get("range_facts", []) or [])
        sa_count += len(e.get("range_source_artifacts", []) or [])
        rej = e.get("rejected_items", []) or []
        rej_count += len(rej)
        rejected_all.extend(rej)
        file_entries.append({"path": str(f.relative_to(batch_dir)), "sha256": _sha256(f)})

    if rejected_all:
        rj = batch_dir / "rejected-items.jsonl"
        rj.write_text("\n".join(json.dumps(r, sort_keys=True, default=str) for r in rejected_all) + "\n")
        file_entries.append({"path": "rejected-items.jsonl", "sha256": _sha256(rj)})

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "batch_slug": batch_slug,
        "paradigm": "metabolic-optimization",
        "source_project": str(PROJECT_ROOT),
        "source_database": "metabolicum-agentic-research",
        "source_run_id": source_run_id or batch_slug,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "pipeline_version": _pipeline_version(),
        "exporter_version": EXPORTER_VERSION,
        "subject_count": subject_count,
        "range_fact_count": rf_count,
        "source_artifact_count": sa_count,
        "rejected_item_count": rej_count,
        "files": file_entries,
    }
    (batch_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str))
    return manifest
