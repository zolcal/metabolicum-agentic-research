#!/usr/bin/env python3
"""Build THE ground-truth document from the metasync production DB.

ONE filesystem document, in total harmony with the production DB, that drives
EVERY derivative (marker_categories, briefs, registry reconciliation, slug
resolution). Read-only export + consolidation; re-runnable. Harmony is enforced
by code/acceptance/check_ground_truth_harmony.py (re-export + diff).

Production is the arbiter (it owns the deployed SM data). This document mirrors
it faithfully; derivatives never read the DB directly and never fork their own
slug/category copies.
"""
from __future__ import annotations

import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "input" / "ground-truth" / "metabolicum-marker-ground-truth.v1.yaml"
PSQL = ["docker", "exec", "-i", "supabase_db_metasync", "psql", "-U", "postgres", "-d", "postgres", "-t", "-A", "-c"]


def q(sql: str):
    r = subprocess.run(PSQL + [sql], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"DB error: {r.stderr}")
    out = r.stdout.strip()
    return json.loads(out) if out else []


def jagg(inner: str) -> str:
    return f"SELECT coalesce(json_agg(row_to_json(t)),'[]'::json) FROM ({inner}) t;"


def main() -> int:
    exported_at = subprocess.run(PSQL + ["SELECT now();"], capture_output=True, text=True).stdout.strip()

    categories = q(jagg(
        "SELECT slug,name,description,display_order,icon,color FROM test_categories ORDER BY display_order,slug"))
    markers = q(jagg(
        "SELECT slug,name,short_name,primary_unit,secondary_unit,conversion_factor,slug_authority,"
        "marker_page_type,deprecated_by,public_content_status,standard_medical_status,display_order "
        "FROM markers ORDER BY slug"))
    mcats = q(jagg("SELECT marker_slug,category_slug,is_primary FROM marker_categories"))
    aliases = q(jagg("SELECT marker_slug,alias,alias_type,language FROM biomarker_aliases"))
    redirects = q(jagg("SELECT old_slug,new_slug FROM marker_slug_aliases"))

    cat_by_marker = defaultdict(list)
    for r in mcats:
        cat_by_marker[r["marker_slug"]].append((r["category_slug"], bool(r["is_primary"])))
    alias_by_marker = defaultdict(lambda: defaultdict(set))
    for r in aliases:
        alias_by_marker[r["marker_slug"]][r["alias_type"]].add(r["alias"])

    marker_docs = []
    for m in markers:
        s = m["slug"]
        cm = sorted(cat_by_marker.get(s, []), key=lambda x: (not x[1], x[0]))  # primary first
        primary = next((c for c, p in cm if p), (cm[0][0] if cm else None))
        al = {t: sorted(v) for t, v in alias_by_marker.get(s, {}).items()}
        marker_docs.append({
            "slug": s,
            "name": m["name"],
            "short_name": m.get("short_name"),
            "primary_unit": m.get("primary_unit"),
            "secondary_unit": m.get("secondary_unit"),
            "conversion_factor": m.get("conversion_factor"),
            "slug_authority": m.get("slug_authority"),
            "marker_page_type": m.get("marker_page_type"),
            "deprecated_by": m.get("deprecated_by"),
            "public_content_status": m.get("public_content_status"),
            "standard_medical_status": m.get("standard_medical_status"),
            "primary_category": primary,
            "categories": [c for c, _ in cm],
            "aliases": al or None,
        })

    doc = {
        "schema_version": 1,
        "provenance": {
            "source": "metasync production DB (public schema), read-only export",
            "exported_at": exported_at,
            "tables": ["markers", "test_categories", "marker_categories", "biomarker_aliases", "marker_slug_aliases"],
            "counts": {"markers": len(markers), "categories": len(categories),
                       "category_assignments": len(mcats), "aliases": len(aliases),
                       "slug_redirects": len(redirects)},
            "harmony_check": "code/acceptance/check_ground_truth_harmony.py",
            "note": ("THE ground truth — in harmony with the production DB, drives every derivative "
                     "(marker_categories, briefs, slug resolution). Do NOT hand-edit; re-run "
                     "scripts/build_ground_truth.py."),
        },
        "slug_redirects": {r["old_slug"]: r["new_slug"] for r in redirects},
        "categories": categories,
        "markers": marker_docs,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, default_flow_style=False, width=200))
    c = doc["provenance"]["counts"]
    print(f"wrote {OUT}")
    print(f"  markers={c['markers']} categories={c['categories']} assignments={c['category_assignments']} "
          f"aliases={c['aliases']} slug_redirects={c['slug_redirects']}")
    print(f"  exported_at={exported_at}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
