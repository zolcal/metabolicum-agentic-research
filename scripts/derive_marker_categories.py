#!/usr/bin/env python3
"""Derive input/marker_categories.yaml FROM the ground-truth document.

Pure derivation — the ground-truth doc is the single driver:
  - categories + marker membership come from the ground truth (mirrors production)
  - practitioners per category = exact set-union of practitioner_registry
    marker_affinity over the category's markers (NO substring matching)
No DB access; reads only the ground-truth doc + practitioner_registry.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from code import ground_truth as gt  # noqa: E402

OUT = ROOT / "input" / "marker_categories.yaml"


def main() -> int:
    cats = gt.categories()
    by_cat = gt.markers_by_category()

    preg = json.loads((ROOT / "input" / "practitioner_registry.json").read_text())
    entries = preg if isinstance(preg, list) else preg.get("practitioners") or list(preg.values())
    aff = defaultdict(set)
    for e in entries:
        if isinstance(e, dict):
            for m in (e.get("marker_affinity") or []):
                aff[m].add(e.get("id"))

    out_cats = []
    for c in sorted(cats, key=lambda x: (x.get("display_order") or 0, x["slug"])):
        cs = c["slug"]
        markers = by_cat.get(cs, [])
        pracs = sorted({pid for m in markers for pid in aff.get(m, set())})
        out_cats.append({
            "slug": cs,
            "name": c.get("name"),
            "description": (c.get("description") or "").strip() or None,
            "marker_count": len(markers),
            "markers": markers,
            "practitioner_count": len(pracs),
            "practitioners": pracs,
        })

    doc = {
        "schema_version": 2,
        "source": ("DERIVED from input/ground-truth/metabolicum-marker-ground-truth.v1.yaml; "
                   "practitioners = exact set-union of practitioner_registry marker_affinity over category markers"),
        "exported_at": gt.load()["provenance"]["exported_at"],
        "categories": out_cats,
    }
    OUT.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, default_flow_style=False))
    print(f"wrote {OUT}: {len(out_cats)} categories, {sum(c['marker_count'] for c in out_cats)} memberships")
    gi = next(c for c in out_cats if c["slug"] == "glycemic-insulin")
    print(f"  glycemic-insulin: {gi['marker_count']} markers, {gi['practitioner_count']} practitioners "
          f"(Bikman: {'person:benjamin-bikman' in gi['practitioners']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
