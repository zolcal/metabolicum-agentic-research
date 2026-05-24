"""Load SM anchor YAMLs from input/sm-ranges/ into sm_anchors table.

Reads all wave-0 and wave-1 YAML files. Each YAML contains multiple
rows (strata), each becoming one sm_anchors row.

Source format: YAML with marker_slug, unit, rows[].
Each row: {stratum, sex, age_min, age_max, min, max, status, use}.
DB table: sm_anchors (one row per stratum per marker).
"""

from __future__ import annotations

import glob
from pathlib import Path
from uuid import uuid4

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SM_RANGES_DIR = PROJECT_ROOT / "input" / "sm-ranges"


def load_sm_anchors(target, *, waves: list[str] | None = None, dry_run: bool = False) -> dict:
    """Load SM anchor rows into the target DB.

    Args:
        target: DBClient or LocalDBClient instance.
        waves: Which waves to load. Default: ["wave-0"] (pilot markers only).
        dry_run: If True, print what would be loaded without writing.

    Returns:
        Dict with counts: markers, rows, skipped.
    """
    if waves is None:
        waves = ["wave-0"]

    yaml_files = []
    for wave in waves:
        pattern = str(SM_RANGES_DIR / wave / "*.yaml")
        yaml_files.extend(sorted(glob.glob(pattern)))

    print(f"  Source: {SM_RANGES_DIR}")
    print(f"  Waves: {', '.join(waves)}")
    print(f"  YAML files found: {len(yaml_files)}")

    if not yaml_files:
        print("  ERROR: No YAML files found")
        return {"markers": 0, "rows": 0, "skipped": 0}

    total_markers = 0
    total_rows = 0
    total_skipped = 0

    for yaml_path in yaml_files:
        path = Path(yaml_path)
        data = yaml.safe_load(path.read_text())

        marker_slug = data.get("marker_slug", path.stem)
        marker_name = data.get("marker_name", marker_slug)
        unit = data.get("unit", "")
        anchor_version = data.get("anchor_version", "unknown")
        rows = data.get("rows", [])

        if dry_run:
            print(f"    {marker_slug}: {len(rows)} rows, unit={unit}")
            total_markers += 1
            total_rows += len(rows)
            continue

        for row in rows:
            # Build population JSONB
            population = {"applies_to": "general_adult"}
            if row.get("stratum") and row["stratum"] != "all_adults":
                population["stratum"] = row["stratum"]
            if row.get("sex") and row["sex"] != "all":
                population["sex"] = row["sex"]
            if row.get("age_min") is not None:
                population["age_min"] = row["age_min"]
            if row.get("age_max") is not None:
                population["age_max"] = row["age_max"]

            # Build guideline source from anchor provenance
            provenance = data.get("anchor_provenance", {})
            known_context = data.get("known_research_context", {})

            # Collect citation info
            pmids = known_context.get("pmids", [])
            pmcids = known_context.get("pmcids", [])
            dois = known_context.get("dois", [])

            citation_parts = []
            if pmids:
                citation_parts.extend([f"PMID:{p}" for p in pmids])
            if pmcids:
                citation_parts.extend([f"PMCID:{p}" for p in pmcids])
            if dois:
                citation_parts.extend([f"DOI:{d}" for d in dois])
            citation = ", ".join(citation_parts) if citation_parts else f"SM anchor {anchor_version}"

            # Source URL from first available ID
            source_url = None
            if pmids:
                source_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmids[0]}/"
            elif dois:
                source_url = f"https://doi.org/{dois[0]}"
            elif pmcids:
                source_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcids[0]}/"

            anchor_row = {
                "marker": marker_slug,
                "target_range_low": row.get("min"),
                "target_range_high": row.get("max"),
                "units": unit,
                "population": population,
                "guideline_source": f"sm_anchor:{anchor_version}",
                "source_url": source_url,
                "citation": citation,
                "anchor_grade": "consensus",
                "notes": f"stratum={row.get('stratum', 'all_adults')}, "
                         f"use={row.get('use', 'display_eligible')}, "
                         f"status={row.get('status', 'normal')}",
            }

            target.upsert_sm_anchor(anchor_row)
            total_rows += 1

        total_markers += 1

    action = "Would load" if dry_run else "Loaded"
    print(f"  ✓ {action} {total_rows} anchor rows for {total_markers} markers")

    return {"markers": total_markers, "rows": total_rows, "skipped": total_skipped}


if __name__ == "__main__":
    import argparse
    from code.loaders import get_target, parse_target_args

    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--local", action="store_true", default=True)
    group.add_argument("--remote", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--waves", nargs="+", default=["wave-0", "wave-1"],
                        help="Which waves to load (default: wave-0 wave-1)")
    args = parser.parse_args()

    target = get_target(use_local=not args.remote)

    print("═══ SM Anchors Loader ═══")
    print(f"  Target: {target.label}")
    result = load_sm_anchors(target, waves=args.waves, dry_run=args.dry_run)
    print(f"  Result: {result}")
