"""Load practitioner registry from input/practitioner_registry.json.

Populates three tables:
  - practitioners (core identity, tier, paradigm affinity)
  - practitioner_surfaces (platform handles, RSS feeds, discovery mode)
  - practitioner_commercial_interests (COI domains, related markers, severity)

Source format: JSON with practitioners[], each containing nested
surfaces[] and commercial_interests[].
"""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
REGISTRY_PATH = PROJECT_ROOT / "input" / "practitioner_registry.json"


def load_practitioners(target, *, dry_run: bool = False) -> dict:
    """Load practitioner registry into the target DB.

    Returns dict with counts: practitioners, surfaces, commercial_interests.
    """
    if not REGISTRY_PATH.exists():
        print(f"  ERROR: {REGISTRY_PATH} not found")
        return {"practitioners": 0, "surfaces": 0, "commercial_interests": 0}

    data = json.loads(REGISTRY_PATH.read_text())
    practitioners = data.get("practitioners", [])

    print(f"  Source: {REGISTRY_PATH.name}")
    print(f"  Schema version: {data.get('schema_version', '?')}")
    print(f"  Practitioners: {len(practitioners)}")

    # Count nested items
    total_surfaces = sum(len(p.get("surfaces", [])) for p in practitioners)
    total_coi = sum(len(p.get("commercial_interests", [])) for p in practitioners)

    if dry_run:
        print(f"  [DRY RUN] Would load:")
        print(f"    {len(practitioners)} practitioners")
        print(f"    {total_surfaces} surfaces")
        print(f"    {total_coi} commercial interests")
        return {"practitioners": len(practitioners), "surfaces": total_surfaces, "commercial_interests": total_coi}

    p_count = 0
    s_count = 0
    c_count = 0

    for p in practitioners:
        # Extract nested lists before building the practitioner row
        surfaces = p.pop("surfaces", [])
        commercial_interests = p.pop("commercial_interests", [])

        # Insert practitioner (DB expects text[] for arrays)
        # Ensure array fields are lists (psycopg2 handles lists natively)
        row = {
            "id": p["id"],
            "canonical_name": p["canonical_name"],
            "aliases": p.get("aliases", []),
            "entity_type": p.get("entity_type", "person"),
            "country": p.get("country"),
            "region": p.get("region"),
            "languages": p.get("languages", []),
            "paradigm_affinity": p.get("paradigm_affinity", []),
            "source_tier": p.get("source_tier", "D"),
            "source_grade": p.get("source_grade"),
            "specialty_focus": p.get("specialty_focus", []),
            "marker_affinity": p.get("marker_affinity", []),
            "key_contribution": p.get("key_contribution"),
            "status": p.get("status", "active"),
            "notes": p.get("notes"),
        }
        target.upsert_practitioner(row)
        p_count += 1

        # Insert surfaces
        for s in surfaces:
            s_row = {
                "practitioner_id": p["id"],
                "platform": s["platform"],
                "handle_or_url": s["handle_or_url"],
                "discovery_mode": s.get("discovery_mode", "manual_seed"),
                "priority": s.get("priority", "secondary"),
                "rss_feed_url": s.get("rss_feed_url"),
                "subreddit": s.get("subreddit"),
                "post_type": s.get("post_type"),
                "notes": s.get("notes"),
            }
            target.upsert_practitioner_surface(s_row)
            s_count += 1

        # Insert commercial interests
        for c in commercial_interests:
            c_row = {
                "practitioner_id": p["id"],
                "domain": c["domain"],
                "product_or_service": c["product_or_service"],
                "related_markers": c.get("related_markers", []),
                "disclosure_quality": c.get("disclosure_quality", "unknown"),
                "severity": c.get("severity", "generic"),
                "notes": c.get("notes"),
            }
            target.upsert_commercial_interest(c_row)
            c_count += 1

    print(f"  ✓ Loaded {p_count} practitioners, {s_count} surfaces, {c_count} COI records")

    return {"practitioners": p_count, "surfaces": s_count, "commercial_interests": c_count}


if __name__ == "__main__":
    from code.loaders import get_target, parse_target_args

    args = parse_target_args()
    target = get_target(use_local=not args.remote)

    print("═══ Practitioner Registry Loader ═══")
    print(f"  Target: {target.label}")
    result = load_practitioners(target, dry_run=args.dry_run)
    print(f"  Result: {result}")
