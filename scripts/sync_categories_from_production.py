#!/usr/bin/env python3
"""Sync the marker-category taxonomy FROM the metasync production DB.

Production (`test_categories` + `marker_categories` + `markers` + `biomarker_aliases`)
is the authoritative source for both the category taxonomy and the canonical slugs —
the agentic project aligns TO it (never the reverse), so existing SM data is never
orphaned. Regenerates input/marker_categories.yaml:
  - 25 canonical categories (from test_categories)
  - markers per category (from marker_categories, production canonical slugs)
  - practitioners per category (DERIVED: exact set-union of practitioner_registry
    marker_affinity over the category's markers — NO substring matching)

Slug guard: every agentic SM-range slug and every category member must exist in the
production `markers` table or resolve via `biomarker_aliases`; violations are reported
and (for category members) abort the write.

Reads snapshots from input/categories/_prod_snapshot/ (exported read-only).
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SNAP = ROOT / "input" / "categories" / "_prod_snapshot"
OUT = ROOT / "input" / "marker_categories.yaml"


def load(name):
    return json.loads((SNAP / f"{name}.json").read_text()) or []


def main() -> int:
    test_categories = load("test_categories")
    marker_categories = load("marker_categories")
    prod_markers = {r["slug"] for r in load("markers")}
    alias_map = {r["alias_lower"]: r["marker_slug"] for r in load("biomarker_aliases")}
    exported_at = (SNAP / "_exported_at.txt").read_text().strip()

    def resolve(slug):
        if slug in prod_markers:
            return slug
        return alias_map.get((slug or "").lower())

    # category -> markers (production canonical slugs)
    cat_markers = defaultdict(list)
    bad_members = []
    for r in marker_categories:
        ms, cs = r["marker_slug"], r["category_slug"]
        if ms not in prod_markers:
            bad_members.append((cs, ms))
        cat_markers[cs].append((ms, r.get("is_primary", False)))

    # practitioner affinity (exact set membership — no substring)
    preg = json.loads((ROOT / "input" / "practitioner_registry.json").read_text())
    entries = preg if isinstance(preg, list) else preg.get("practitioners") or list(preg.values())
    aff = defaultdict(set)  # marker_slug -> {practitioner_id}
    for e in entries:
        if isinstance(e, dict):
            for m in (e.get("marker_affinity") or []):
                aff[m].add(e.get("id"))

    # build categories
    cat_meta = {c["slug"]: c for c in test_categories}
    categories = []
    for c in sorted(test_categories, key=lambda x: (x.get("display_order") or 0, x["slug"])):
        cs = c["slug"]
        markers = sorted({m for m, _ in cat_markers.get(cs, [])})
        pracs = sorted({pid for m in markers for pid in aff.get(m, set())})
        categories.append({
            "slug": cs,
            "name": c.get("name"),
            "description": (c.get("description") or "").strip() or None,
            "marker_count": len(markers),
            "markers": markers,
            "practitioner_count": len(pracs),
            "practitioners": pracs,
        })

    # ── slug guard: agentic SM-range slugs vs production ──
    sm_slugs = sorted(p.stem for p in (ROOT / "input" / "sm-ranges").rglob("*.yaml"))
    sm_unresolved = [s for s in sm_slugs if resolve(s) is None]

    print(f"production export: {exported_at}")
    print(f"categories: {len(categories)} | markers mapped: {sum(c['marker_count'] for c in categories)} "
          f"(unique {len({m for c in categories for m in c['markers']})}) | prod markers: {len(prod_markers)}")
    print(f"category members NOT in prod markers: {len(bad_members)}")
    for cs, ms in bad_members[:15]:
        print(f"   {cs} <- {ms}")
    print(f"agentic SM-range slugs: {len(sm_slugs)} | UNRESOLVED vs prod (slug-safety violations): {len(sm_unresolved)}")
    for s in sm_unresolved[:25]:
        print(f"   UNRESOLVED: {s}")
    print()
    print("category -> markers / derived practitioners:")
    for c in categories:
        print(f"   {c['slug']:18s} markers={c['marker_count']:4d}  practitioners={c['practitioner_count']:3d}")

    if bad_members:
        print("\nABORT: category members not in production markers — fix before writing.", file=sys.stderr)
        return 1

    # back up old, write new
    if OUT.exists():
        bak = OUT.with_suffix(".yaml.prebak")
        bak.write_text(OUT.read_text())
        print(f"\nbacked up old -> {bak.name}")
    doc = {
        "schema_version": 2,
        "source": "metasync production (test_categories + marker_categories); practitioners derived from practitioner_registry marker_affinity (exact set-union)",
        "exported_at": exported_at,
        "categories": categories,
    }
    OUT.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, default_flow_style=False))
    print(f"wrote {OUT}  ({len(categories)} categories)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
