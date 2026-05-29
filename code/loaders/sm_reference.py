"""Resolve council-only SM references from Hermes briefs.

Hermes briefs carry only an ``sm_reference`` pointer. Discovery and extraction
can read the brief safely because the SM numbers are absent. Stage 3 council is
the only stage that should call this resolver.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SM_RANGES_DIR = PROJECT_ROOT / "input" / "sm-ranges"


def _require_string(ref: dict[str, Any], field: str) -> str:
    value = ref.get(field)
    if not isinstance(value, str) or not value:
        raise ValueError(f"sm_reference.{field} must be a non-empty string")
    return value


def resolve_sm_reference(sm_reference: dict[str, Any]) -> dict[str, Any]:
    """Load the canonical SM range YAML for a council-only reference."""
    if not isinstance(sm_reference, dict):
        raise ValueError("sm_reference must be an object")

    wave = _require_string(sm_reference, "wave")
    marker_slug = _require_string(sm_reference, "marker_slug")
    visibility = _require_string(sm_reference, "visibility")
    if visibility != "council_only":
        raise ValueError("sm_reference.visibility must be council_only")

    sm_path = SM_RANGES_DIR / wave / f"{marker_slug}.yaml"
    if not sm_path.exists():
        raise FileNotFoundError(f"SM range file not found for sm_reference: {sm_path}")

    data = yaml.safe_load(sm_path.read_text(encoding="utf-8")) or {}
    resolved_marker = data.get("marker_slug", marker_slug)
    if resolved_marker != marker_slug:
        raise ValueError(
            f"sm_reference marker_slug {marker_slug!r} does not match SM file marker_slug {resolved_marker!r}"
        )

    resolved = dict(data)
    resolved["sm_reference"] = {
        "wave": wave,
        "marker_slug": marker_slug,
        "visibility": visibility,
    }
    resolved["source_path"] = str(Path("input") / "sm-ranges" / wave / f"{marker_slug}.yaml")
    resolved["evidence_weight"] = 0
    resolved["scope"] = "council_only_alignment_reference"
    return resolved


def write_council_alignment_reference(sm_reference: dict[str, Any], run_dir: Path) -> Path:
    """Write the resolved SM reference to the council-scoped run artifact."""
    resolved = resolve_sm_reference(sm_reference)
    path = Path(run_dir) / "council" / "sm_alignment_reference.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(resolved, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return path
