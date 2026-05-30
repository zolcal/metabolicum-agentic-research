#!/usr/bin/env python3
"""Hermes write step: persist the binary MO-support determination for EVERY marker
to the agentic DB (marker_mo_determination).

mo_supported = the marker has a Metabolic-Optimization dimension. Determined from the
ground-truth categories + the MO scope policy, plus the 8 QA-confirmed false-exclusions
the excluded-markers assessment surfaced. Binary, overridable: re-research rewrites the row.

Pass-through for out-of-scope markers (no research), but the record is created here,
through the pipeline DB layer — so every marker has a uniform, traceable MO determination.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from code import db as dbmod  # noqa: E402
from code import ground_truth as gt  # noqa: E402

# Excluded-markers assessment (2026-05-30): MO-supported despite an out-of-scope
# primary category — these flip to true.
FALSE_EXCLUSIONS = {
    "nlr": "neutrophil-lymphocyte ratio — systemic-inflammation marker tracked in MO",
    "plr": "platelet-lymphocyte ratio — systemic-inflammation marker tracked in MO",
    "sii": "systemic immune-inflammation index — used by MO clinicians",
    "magnesium-serum": "magnesium actively optimized by MO practitioners",
    "rbc-magnesium": "RBC magnesium — functional tissue-Mg status, MO-optimized",
    "urine-iodine": "iodine micronutrient — functional/thyroid optimization target",
    "calprotectin": "fecal calprotectin — targeted low by functional-medicine",
    "cortisol-saliva": "salivary cortisol — HPA-axis / cortisol-awakening optimization",
}


def main() -> int:
    in_scope = gt._in_scope_categories()
    flips = {gt.resolve_slug(k) or k: v for k, v in FALSE_EXCLUSIONS.items()}

    db = dbmod.LocalDBClient()
    supported = not_supported = 0
    for m in gt.markers():
        slug = m["slug"]
        cats = set(m.get("categories") or [])
        hit = sorted(cats & in_scope)
        if hit:
            ok, why = True, f"MO-relevant: category '{hit[0]}'"
        elif slug in flips:
            ok, why = True, f"MO-relevant (false-exclusion corrected): {flips[slug]}"
        else:
            pc = m.get("primary_category") or "uncategorized"
            ok, why = False, f"no MO dimension — category '{pc}' (taxonomy assessment 2026-05-30)"
        db.upsert_mo_determination({"marker_slug": slug, "mo_supported": ok, "mo_rationale": why})
        supported += ok
        not_supported += not ok

    print(f"wrote {supported + not_supported} determinations: "
          f"{supported} mo_supported, {not_supported} not_supported")
    db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
