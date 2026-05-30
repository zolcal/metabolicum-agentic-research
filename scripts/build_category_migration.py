#!/usr/bin/env python3
"""Build the PROPOSED production marker_categories migration from the grounded
cross-reference workflow output (validated against the ground truth).

Output: docs/handoff-to-metasync/2026-05-30-marker-categories.sql (additive,
idempotent, with rollback). This is a PROPOSAL for metasync sign-off — it is NOT
applied here; production is the arbiter.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from code import ground_truth as gt  # noqa: E402

WF = "/tmp/claude-1000/-home-zoltan-Projects-metabolicum-research/9caab50c-6143-4483-8516-76417b2dcce7/tasks/w0eq23ppy.output"
OUT = ROOT / "docs" / "handoff-to-metasync" / "2026-05-30-marker-categories.sql"

NEURO = {
    "slug": "neurological-cognitive",
    "name": "Neurological & Cognitive",
    "description": "Brain health, neurodegeneration, and cognitive biomarkers (NfL, NSE, S100B, p-tau, amyloid, GFAP)",
    "markers": ["neurofilament-light-chain", "enolase-neuron-specific",
                "enolase-neuron-specific-csf", "s100-calcium-binding-protein-b"],
}


def main() -> int:
    res = json.load(open(WF))["result"]
    if isinstance(res, str):
        res = json.loads(res)
    xrefs = res["cross_references"]["cross_references"]
    cat_slugs = {c["slug"] for c in gt.categories()}
    m = {x["slug"]: x for x in gt.markers()}

    # validate + dedup: canonical marker, category in 25, not already a member
    add = defaultdict(set)
    dropped = []
    for c in xrefs:
        canon = gt.resolve_slug(c["marker_slug"])
        if not canon:
            dropped.append((c["marker_slug"], "not in ground truth")); continue
        cur = set(m[canon].get("categories") or [])
        for a in c.get("add_to_categories", []):
            if a not in cat_slugs:
                dropped.append((canon, f"bad category {a}"))
            elif a in cur:
                dropped.append((canon, f"already in {a}"))
            else:
                add[canon].add(a)

    rows = sorted((mk, cat) for mk, cats in add.items() for cat in cats)

    L = []
    L.append("-- PROPOSED migration: MO multi-category memberships + Neurological category")
    L.append("-- Source: metabolicum-agentic-research findings 2026-05-30 (grounded cross-ref workflow).")
    L.append("-- ADDITIVE + idempotent. Production is the arbiter — review before applying.")
    L.append(f"-- {len(rows)} secondary memberships across {len(add)} markers + 1 new category ({len(NEURO['markers'])} neuro markers).")
    L.append("")
    L.append("BEGIN;")
    L.append("")
    L.append("-- 1) New category: Neurological & Cognitive")
    L.append("INSERT INTO test_categories (name, slug, description, display_order)")
    L.append(f"VALUES ('{NEURO['name']}', '{NEURO['slug']}', '{NEURO['description']}', 26)")
    L.append("ON CONFLICT (slug) DO NOTHING;")
    L.append("")
    L.append("-- 2) Multi-category memberships (secondary; is_primary=false). Each is a standard,")
    L.append("--    guideline/landmark-cited clinical multi-membership (see findings doc).")
    L.append("INSERT INTO marker_categories (marker_slug, category_slug, is_primary) VALUES")
    vals = [f"  ('{mk}', '{cat}', false)" for mk, cat in rows]
    L.append(",\n".join(vals))
    L.append("ON CONFLICT (marker_slug, category_slug) DO NOTHING;")
    L.append("")
    L.append("-- 3) Neuro memberships. NOTE: these 4 markers have questionable PRIMARY categories")
    L.append("--    (e.g. s100b in 'electrolytes', NfL in 'specialty'). This migration only ADDS the")
    L.append("--    neuro membership; reassigning is_primary is left to metasync's review (see findings).")
    L.append("INSERT INTO marker_categories (marker_slug, category_slug, is_primary) VALUES")
    L.append(",\n".join(f"  ('{s}', '{NEURO['slug']}', false)" for s in NEURO["markers"]))
    L.append("ON CONFLICT (marker_slug, category_slug) DO NOTHING;")
    L.append("")
    L.append("COMMIT;")
    L.append("")
    L.append("-- ─── ROLLBACK ───")
    L.append("-- BEGIN;")
    allrows = rows + [(s, NEURO["slug"]) for s in NEURO["markers"]]
    pairs = ", ".join(f"('{mk}','{cat}')" for mk, cat in allrows)
    L.append(f"--   DELETE FROM marker_categories WHERE (marker_slug, category_slug) IN ({pairs});")
    L.append(f"--   DELETE FROM test_categories WHERE slug = '{NEURO['slug']}';")
    L.append("-- COMMIT;")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(L) + "\n")
    print(f"wrote {OUT}")
    print(f"  {len(rows)} secondary memberships, {len(add)} markers, +1 neuro category, {len(NEURO['markers'])} neuro rows")
    print(f"  dropped {len(dropped)} (already-member/invalid)")
    # dump validated set for the findings doc
    (OUT.parent / "_validated_crossrefs.json").write_text(json.dumps(
        {"memberships": [[mk, cat] for mk, cat in rows], "neuro": NEURO}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
