"""Load research target envelope facts from SM anchor YAMLs.

Generates sanitized atomic envelope facts from the SM anchor data.
Per §17, envelopes are internal research goals, not evidence.
Only sanitized atomic facts are loaded — no derivation material.

Each SM anchor row becomes one or more envelope facts:
  - display_eligible rows → readiness_state = "ready"
  - internal_research_gate rows → readiness_state = "draft"

The envelope table has strict constraints:
  - publishable = false (never exported)
  - evidence_weight = 0 (never scored as evidence)
  - disclose_origin_to_agents = false (origin hidden)
  - export_to_metasync = false (never reaches production)
"""

from __future__ import annotations

import glob
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SM_RANGES_DIR = PROJECT_ROOT / "input" / "sm-ranges"


def load_envelope_facts(
    target,
    *,
    waves: list[str] | None = None,
    paradigm: str = "SM",
    dry_run: bool = False,
) -> dict:
    """Generate research target envelope facts from SM anchor YAMLs.

    Args:
        target: DBClient or LocalDBClient instance.
        waves: Which waves to process. Default: ["wave-0"].
        paradigm: Paradigm for envelope facts. Default: "SM".
        dry_run: If True, print what would be loaded without writing.

    Returns:
        Dict with counts: markers, envelopes_ready, envelopes_draft.
    """
    if waves is None:
        waves = ["wave-0"]

    yaml_files = []
    for wave in waves:
        pattern = str(SM_RANGES_DIR / wave / "*.yaml")
        yaml_files.extend(sorted(glob.glob(pattern)))

    print(f"  Source: {SM_RANGES_DIR}")
    print(f"  Waves: {', '.join(waves)}")
    print(f"  Paradigm: {paradigm}")
    print(f"  YAML files found: {len(yaml_files)}")

    if not yaml_files:
        print("  ERROR: No YAML files found")
        return {"markers": 0, "envelopes_ready": 0, "envelopes_draft": 0}

    total_markers = 0
    total_ready = 0
    total_draft = 0

    for yaml_path in yaml_files:
        path = Path(yaml_path)
        data = yaml.safe_load(path.read_text())

        marker_slug = data.get("marker_slug", path.stem)
        unit = data.get("unit", "")
        anchor_version = data.get("anchor_version", "unknown")
        rows = data.get("rows", [])

        if dry_run:
            ready = sum(1 for r in rows if r.get("use") == "display_eligible")
            draft = len(rows) - ready
            print(f"    {marker_slug}: {ready} ready, {draft} draft")
            total_markers += 1
            total_ready += ready
            total_draft += draft
            continue

        range_order = 0
        for row in rows:
            range_order += 1
            use = row.get("use", "display_eligible")
            readiness = "ready" if use == "display_eligible" else "draft"

            envelope = {
                "marker": marker_slug,
                "paradigm": paradigm,
                "envelope_version": f"env_{anchor_version}",
                "range_order": range_order,
                "units": unit,
                "direction": "between",
                "target_range_low": row.get("min"),
                "target_range_high": row.get("max"),
                # Tolerance bounds: ±10% of target range as initial envelope
                "tolerance_range_low": (
                    round(row["min"] * 0.9, 2) if row.get("min") is not None else None
                ),
                "tolerance_range_high": (
                    round(row["max"] * 1.1, 2) if row.get("max") is not None else None
                ),
                "sex_for_lab_reference": (
                    row.get("sex") if row.get("sex") and row["sex"] != "all" else None
                ),
                "age_min": row.get("age_min"),
                "age_max": row.get("age_max"),
                "stratum": (
                    row.get("stratum") if row.get("stratum") != "all_adults" else None
                ),
                "population": {"applies_to": row.get("stratum", "general_adult")},
                "display_role": (
                    "primary_standard_medical_anchor"
                    if use == "display_eligible"
                    else "comparison_only"
                ),
                "primary_goal": use == "display_eligible",
                "readiness_state": readiness,
                "generation_method": "sm_anchor_derived",
                "context_note": f"Derived from SM anchor {anchor_version}, "
                                f"stratum={row.get('stratum', 'all_adults')}",
                # §17 enforcement: private research goals, never evidence
                "publishable": False,
                "evidence_weight": 0,
                "disclose_origin_to_agents": False,
                "export_to_metasync": False,
            }

            target.insert_envelope(envelope)

            if readiness == "ready":
                total_ready += 1
            else:
                total_draft += 1

        total_markers += 1

    action = "Would generate" if dry_run else "Generated"
    print(f"  ✓ {action} {total_ready} ready + {total_draft} draft envelopes "
          f"for {total_markers} markers")

    return {
        "markers": total_markers,
        "envelopes_ready": total_ready,
        "envelopes_draft": total_draft,
    }


if __name__ == "__main__":
    import argparse
    from code.loaders import get_target, parse_target_args

    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--local", action="store_true", default=True)
    group.add_argument("--remote", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--waves", nargs="+", default=["wave-0", "wave-1"],
                        help="Which waves to process (default: wave-0 wave-1)")
    args = parser.parse_args()

    target = get_target(use_local=not args.remote)

    print("═══ Research Target Envelope Facts Loader ═══")
    print(f"  Target: {target.label}")
    result = load_envelope_facts(target, waves=args.waves, dry_run=args.dry_run)
    print(f"  Result: {result}")
