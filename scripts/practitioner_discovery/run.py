"""Orchestrate the discovery pipeline for a list of markers (inventory source).

Pure core (`run_pipeline`) returns data; the CLI (`main`) loads real files,
writes outputs to output/practitioner-discovery/<run-id>/, and persists the
updated registry.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.practitioner_discovery import (
    audit, extract_candidates, harvest_inventory, ingest, terms, threshold,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = PROJECT_ROOT / "input" / "practitioner_registry.json"
OUTPUT_ROOT = PROJECT_ROOT / "output" / "practitioner-discovery"


def run_pipeline(markers, registry, policy, inventory_dir, n=2):
    terms_by_marker = {m: terms.marker_terms(m, policy) for m in markers}
    terms_by_marker = {m: t for m, t in terms_by_marker.items() if t}
    signals = harvest_inventory.scan_inventory(terms_by_marker, inventory_dir=inventory_dir)
    new_candidates = extract_candidates.extract_candidates(signals, registry)
    enrichments = extract_candidates.extract_enrichments(signals, registry)
    q_new, held_new = threshold.apply_threshold(new_candidates, n=n)
    q_enr, held_enr = threshold.apply_threshold(enrichments, n=n)
    qualifying = q_new + q_enr
    held = held_new + held_enr
    records = [ingest.to_registry_record(q) for q in qualifying]
    merged = ingest.merge_into_registry(registry, records)
    audit_md = audit.render_report(q_new, q_enr, held, n=n)
    return {
        "registry": merged,
        "qualifying": qualifying,
        "held": held,
        "audit_md": audit_md,
        "summary": {"signals": len(signals), "new_practitioners": len(q_new),
                    "enriched": len(q_enr), "held": len(held)},
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Practitioner gap discovery (inventory source)")
    parser.add_argument("markers", nargs="+", help="marker slugs to discover for")
    parser.add_argument("--run-id", required=True, help="output subdir under output/practitioner-discovery/")
    parser.add_argument("-n", "--threshold", type=int, default=2)
    parser.add_argument("--write-registry", action="store_true",
                        help="persist the merged registry back to practitioner_registry.json")
    args = parser.parse_args(argv)

    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    policy = terms.load_policy()
    result = run_pipeline(args.markers, registry, policy,
                          inventory_dir=harvest_inventory.INVENTORY_DIR, n=args.threshold)

    out_dir = OUTPUT_ROOT / args.run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "qualifying.json").write_text(json.dumps(result["qualifying"], indent=2), encoding="utf-8")
    (out_dir / "held.json").write_text(json.dumps(result["held"], indent=2), encoding="utf-8")
    (out_dir / "audit.md").write_text(result["audit_md"], encoding="utf-8")
    print(json.dumps(result["summary"]))

    if args.write_registry:
        REGISTRY_PATH.write_text(json.dumps(result["registry"], indent=2), encoding="utf-8")
        print(f"registry updated: {REGISTRY_PATH}")


if __name__ == "__main__":
    main()
