"""Load marker glossary from input/marker_glossary.json into marker_glossary table.

Source format: JSON with schema_version, entries[].
Each entry: {marker, language, term, term_type}.
DB table: marker_glossary (PK: marker, language, term).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
GLOSSARY_PATH = PROJECT_ROOT / "input" / "marker_glossary.json"


def load_glossary(target, *, dry_run: bool = False) -> dict:
    """Load marker glossary entries into the target DB.

    Args:
        target: DBClient or LocalDBClient instance.
        dry_run: If True, print what would be loaded without writing.

    Returns:
        Dict with counts: total, inserted, skipped.
    """
    if not GLOSSARY_PATH.exists():
        print(f"  ERROR: {GLOSSARY_PATH} not found")
        return {"total": 0, "inserted": 0, "skipped": 0}

    data = json.loads(GLOSSARY_PATH.read_text())
    entries = data.get("entries", [])

    print(f"  Source: {GLOSSARY_PATH.name}")
    print(f"  Schema version: {data.get('schema_version', '?')}")
    print(f"  Entries: {len(entries)}")

    if dry_run:
        markers = set(e["marker"] for e in entries)
        print(f"  [DRY RUN] Would load {len(entries)} entries for {len(markers)} markers")
        for m in sorted(markers):
            count = sum(1 for e in entries if e["marker"] == m)
            print(f"    {m}: {count} terms")
        return {"total": len(entries), "inserted": 0, "skipped": 0}

    # Prepare rows for upsert
    rows = []
    for e in entries:
        rows.append({
            "marker": e["marker"],
            "language": e.get("language", data.get("language_default", "en")),
            "term": e["term"],
            "term_type": e.get("term_type", "alias"),
        })

    result = target.upsert_glossary_entries(rows)

    markers = set(e["marker"] for e in entries)
    print(f"  ✓ Loaded {len(result)} glossary entries for {len(markers)} markers")

    return {"total": len(entries), "inserted": len(result), "skipped": 0}


if __name__ == "__main__":
    from code.loaders import get_target, parse_target_args

    args = parse_target_args()
    target = get_target(use_local=not args.remote)

    print("═══ Marker Glossary Loader ═══")
    print(f"  Target: {target.label}")
    result = load_glossary(target, dry_run=args.dry_run)
    print(f"  Result: {result}")
