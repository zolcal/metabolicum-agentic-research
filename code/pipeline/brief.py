"""Brief -> pipeline bridge with the SM firewall split.

A Hermes brief is pointer-only (no SM numbers). `discovery_payload` returns the
marker identity + pointer fields that discovery/extraction may see; the SM
numbers are obtainable ONLY via `resolve_council_sm_rows`, which dereferences the
council-only `sm_reference` through code/loaders/sm_reference.py. The orchestrator
passes the discovery payload to Stage 1/2 and the resolved rows to the council.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from code.loaders.sm_reference import resolve_sm_reference

POINTER_FIELDS = (
    "recommended_youtube_video_ids",
    "recommended_practitioner_ids",
    "recommended_pubmed_ids",
    "recommended_dois",
    "recommended_source_urls",
    "recommended_search_queries",
)


def load_brief(path: str | Path) -> dict[str, Any]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}


def discovery_payload(brief: dict) -> dict[str, Any]:
    """Marker identity + pointer fields only — never the SM numbers or the
    sm_reference pointer. This is what Stage 1 discovery / Stage 2 extraction get."""
    dp: dict[str, Any] = {
        "marker_slug": brief.get("marker_slug"),
        "marker_name": brief.get("marker_name"),
        "unit": brief.get("unit"),
    }
    for f in ("direction", "risk_direction"):
        if brief.get(f) is not None:
            dp[f] = brief[f]
    for f in POINTER_FIELDS:
        dp[f] = brief.get(f, [])
    return dp


def resolve_council_sm_rows(brief: dict) -> list[dict]:
    """Council-only: dereference sm_reference and return the SM rows (numbers)."""
    ref = brief.get("sm_reference")
    if not ref:
        return []
    resolved = resolve_sm_reference(ref)
    return resolved.get("rows", []) or []
