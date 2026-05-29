#!/usr/bin/env python3
"""Contract: the brief->pipeline bridge enforces the SM firewall structurally.

Loads a real committed pointer-only brief and asserts the discovery payload
carries marker identity + pointer fields but NO SM-bearing keys, while the SM
numbers are obtainable ONLY by resolving sm_reference (council-only). Offline,
$0 — uses committed input/hermes-briefs + input/sm-ranges files.
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

BRIEF = PROJECT_ROOT / "input" / "hermes-briefs" / "wave-0" / "apob.yaml"


def main() -> None:
    from code.pipeline import brief

    b = brief.load_brief(BRIEF)
    # brief is pointer-only
    assert "rows" not in b and "anchor_provenance" not in b, "brief must carry no SM numbers"
    assert b["sm_reference"]["visibility"] == "council_only"

    # discovery payload: identity + pointers, but NO SM-bearing keys
    dp = brief.discovery_payload(b)
    assert dp["marker_slug"] == "apob" and dp["unit"] == "mg/dL"
    assert isinstance(dp["recommended_youtube_video_ids"], list)
    assert isinstance(dp["recommended_search_queries"], list)
    for k in ("sm_reference", "rows", "min", "max", "anchor_provenance",
              "target_range_low", "target_range_high"):
        assert k not in dp, f"{k} must not reach discovery/extraction"

    # SM numbers are obtainable ONLY by the council-only resolution
    sm_rows = brief.resolve_council_sm_rows(b)
    assert len(sm_rows) >= 1, "council must be able to resolve SM rows"
    assert any(
        isinstance(r.get("min"), (int, float)) and isinstance(r.get("max"), (int, float))
        for r in sm_rows
    ), "resolved SM rows must carry numeric bounds (council-only)"

    print("check_brief_bridge_contract: all assertions passed")


if __name__ == "__main__":
    main()
