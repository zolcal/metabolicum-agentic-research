#!/usr/bin/env python3
"""DB-free contract check: the agentic marker-category taxonomy stays aligned to
the metasync production snapshot, and no agentic slug orphans production.

Guards against the category strip + slug drift (production is the arbiter):
  - every category slug in marker_categories.yaml exists in test_categories
  - every category member marker exists in production markers (or resolves via alias)
  - every agentic SM-range slug resolves in production markers/aliases (slug guard)
Uses the committed read-only snapshot under input/categories/_prod_snapshot/.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import yaml  # noqa: E402

SNAP = PROJECT_ROOT / "input" / "categories" / "_prod_snapshot"
CATS = PROJECT_ROOT / "input" / "marker_categories.yaml"


def main() -> None:
    prod_markers = {r["slug"] for r in json.loads((SNAP / "markers.json").read_text())}
    alias = {r["alias_lower"] for r in json.loads((SNAP / "biomarker_aliases.json").read_text())}
    cat_slugs = {c["slug"] for c in json.loads((SNAP / "test_categories.json").read_text())}

    def resolves(slug: str) -> bool:
        return slug in prod_markers or (slug or "").lower() in alias

    doc = yaml.safe_load(CATS.read_text())
    assert doc.get("schema_version") == 2, "marker_categories.yaml must be the prod-synced schema 2"
    cats = doc["categories"]
    assert cats, "no categories"

    # 1) category slugs are canonical (in test_categories)
    bad_cat = [c["slug"] for c in cats if c["slug"] not in cat_slugs]
    assert not bad_cat, f"category slugs not in test_categories: {bad_cat}"

    # 2) every member marker exists in production
    phantom = sorted({m for c in cats for m in c.get("markers", []) if not resolves(m)})
    assert not phantom, f"category members not in production markers: {phantom[:20]}"

    # 3) slug guard — every agentic SM-range slug resolves in production
    sm = sorted(p.stem for p in (PROJECT_ROOT / "input" / "sm-ranges").rglob("*.yaml"))
    unresolved = [s for s in sm if not resolves(s)]
    assert not unresolved, f"{len(unresolved)} SM-range slugs orphan production: {unresolved[:20]}"

    # 4) sanity — glycemic-insulin carries the insulin practitioners
    gi = next((c for c in cats if c["slug"] == "glycemic-insulin"), None)
    assert gi and gi["practitioner_count"] >= 20, "glycemic-insulin must carry the insulin practitioners"
    assert "person:benjamin-bikman" in gi["practitioners"], "Bikman missing from glycemic-insulin"

    print(f"check_marker_categories_contract: {len(cats)} categories, "
          f"{len({m for c in cats for m in c.get('markers', [])})} markers, "
          f"0 phantom, 0 slug orphans, glycemic-insulin practitioners={gi['practitioner_count']}")


if __name__ == "__main__":
    main()
