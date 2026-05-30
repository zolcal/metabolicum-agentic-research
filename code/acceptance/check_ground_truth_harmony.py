#!/usr/bin/env python3
"""Contract: the ground-truth document is in TOTAL HARMONY with the metasync DB.

Re-exports the authoritative counts + identity spot-checks from production and
asserts the committed ground-truth document matches exactly. Any divergence fails
the build -> rebuild with scripts/build_ground_truth.py. Requires DB access
(docker exec supabase_db_metasync); this is the one consumer allowed to read prod.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from code import ground_truth  # noqa: E402

PSQL = ["docker", "exec", "-i", "supabase_db_metasync", "psql", "-U", "postgres", "-d", "postgres", "-t", "-A", "-c"]


def scalar(sql: str) -> str:
    r = subprocess.run(PSQL + [sql], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"DB unreachable (harmony cannot be verified): {r.stderr}")
    return r.stdout.strip()


def main() -> None:
    d = ground_truth.load()
    c = d["provenance"]["counts"]
    db = {
        "markers": int(scalar("SELECT count(*) FROM markers;")),
        "categories": int(scalar("SELECT count(*) FROM test_categories;")),
        "category_assignments": int(scalar("SELECT count(*) FROM marker_categories;")),
        "aliases": int(scalar("SELECT count(*) FROM biomarker_aliases;")),
        "slug_redirects": int(scalar("SELECT count(*) FROM marker_slug_aliases;")),
    }
    for k, v in db.items():
        assert c[k] == v, f"HARMONY BREAK: {k} doc={c[k]} db={v} — rebuild ground truth (scripts/build_ground_truth.py)"

    # identity spot-check: canonical slug + unit + primary category match the DB
    for slug in ("fasting-insulin", "bilirubin-total", "apob", "tsh", "hba1c"):
        unit = scalar(f"SELECT primary_unit FROM markers WHERE slug='{slug}';")
        cat = scalar(f"SELECT category_slug FROM marker_categories WHERE marker_slug='{slug}' AND is_primary LIMIT 1;")
        m = next((x for x in d["markers"] if x["slug"] == slug), None)
        assert m, f"{slug} missing from ground truth"
        assert m["primary_unit"] == unit, f"{slug} unit doc={m['primary_unit']!r} db={unit!r}"
        if cat:
            assert m["primary_category"] == cat, f"{slug} category doc={m['primary_category']!r} db={cat!r}"

    # slug-arbitration layer honors the production redirect
    assert ground_truth.resolve_slug("total-bilirubin") == "bilirubin-total", "redirect total-bilirubin not honored"
    assert ground_truth.resolve_slug("apob") == "apob"
    assert ground_truth.resolve_slug("not-a-real-slug-xyz") is None

    print(f"check_ground_truth_harmony: doc IN HARMONY with DB "
          f"(markers={db['markers']}, categories={db['categories']}, assignments={db['category_assignments']}, "
          f"aliases={db['aliases']}, redirects={db['slug_redirects']})")


if __name__ == "__main__":
    main()
