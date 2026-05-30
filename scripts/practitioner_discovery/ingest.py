"""Turn qualifying candidates into practitioner_registry.json records and merge
them in. Auto-discovered records are tagged + conservatively graded so a later
audit can demote or remove them with a single filter."""
from __future__ import annotations


def to_registry_record(candidate: dict) -> dict:
    return {
        "id": candidate["entity_key"],
        "canonical_name": candidate["display_name"],
        "aliases": [candidate["display_name"]] if candidate["display_name"] else [],
        "entity_type": candidate.get("entity_type", "channel"),
        "languages": ["en"],
        "paradigm_affinity": ["MO"],
        "source_tier": "C",
        "source_grade": "E2",
        "marker_affinity": list(candidate["marker_affinity"]),
        "surfaces": candidate["surfaces"],
        "discovery_provenance": [
            {"marker": m, "evidence_count": len(ev), "evidence": [e["ref"] for e in ev]}
            for m, ev in candidate["evidence"].items()
        ],
        "commercial_interests": [],
    }


def merge_into_registry(registry: dict, records: list[dict]) -> dict:
    registry.setdefault("practitioners", [])
    by_id = {p["id"]: p for p in registry["practitioners"]}
    for r in records:
        existing = by_id.get(r["id"])
        if existing:
            existing["marker_affinity"] = sorted(
                set(existing.get("marker_affinity", [])) | set(r["marker_affinity"]))
            existing.setdefault("discovery_provenance", [])
            existing["discovery_provenance"].extend(r["discovery_provenance"])
        else:
            registry["practitioners"].append(r)
            by_id[r["id"]] = r
    return registry
