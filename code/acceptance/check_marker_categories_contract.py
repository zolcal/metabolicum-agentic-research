#!/usr/bin/env python3
"""DB-free contract: marker_categories.yaml is a faithful derivation of THE
ground-truth document, and no agentic slug orphans the ground truth.

  - every category slug exists in the ground-truth categories
  - every category member marker is canonical in the ground truth
  - every agentic SM-range slug resolves via the ground-truth slug-arbitration
    layer (redirect -> canonical -> alias)
  - glycemic-insulin carries the insulin practitioners (Bikman present)
The ground-truth doc is the single driver; its harmony with the DB is enforced
separately by check_ground_truth_harmony.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import yaml  # noqa: E402

from code import ground_truth as gt  # noqa: E402

CATS = PROJECT_ROOT / "input" / "marker_categories.yaml"


def main() -> None:
    gt_cat_slugs = {c["slug"] for c in gt.categories()}
    gt_canon = {m["slug"] for m in gt.markers()}

    doc = yaml.safe_load(CATS.read_text())
    assert doc.get("schema_version") == 2, "marker_categories.yaml must be ground-truth-derived schema 2"
    cats = doc["categories"]
    assert cats, "no categories"

    bad_cat = [c["slug"] for c in cats if c["slug"] not in gt_cat_slugs]
    assert not bad_cat, f"category slugs not in ground truth: {bad_cat}"

    phantom = sorted({m for c in cats for m in c.get("markers", []) if m not in gt_canon})
    assert not phantom, f"category members not canonical in ground truth: {phantom[:20]}"

    # slug guard via the arbitration layer (redirect -> canonical -> alias)
    sm = sorted(p.stem for p in (PROJECT_ROOT / "input" / "sm-ranges").rglob("*.yaml"))
    unresolved = [s for s in sm if gt.resolve_slug(s) is None]
    assert not unresolved, f"{len(unresolved)} SM-range slugs orphan the ground truth: {unresolved[:20]}"

    gi = next((c for c in cats if c["slug"] == "glycemic-insulin"), None)
    assert gi and gi["practitioner_count"] >= 20, "glycemic-insulin must carry the insulin practitioners"
    assert "person:benjamin-bikman" in gi["practitioners"], "Bikman missing from glycemic-insulin"

    print(f"check_marker_categories_contract: {len(cats)} categories derived from ground truth, "
          f"0 phantom, 0 slug orphans, glycemic-insulin practitioners={gi['practitioner_count']}")


if __name__ == "__main__":
    main()
