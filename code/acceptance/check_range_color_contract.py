#!/usr/bin/env python3
"""Contract check for code/range_color_policy.py against docs/policies/RANGE-STATUS-COLOR-POLICY.md.

Asserts the alias table maps the documented statuses to the right canonical
bucket/hex, preserves the policy quirks (low->elevated, critical->severe bucket,
very_high/deficient->critical), and that the 7 hexes exactly match the
biomarker_claims.color CHECK set. canonical_color raises on unmapped (so
assembly can quarantine instead of crashing).
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


def main() -> None:
    from code import range_color_policy as rc

    # canonical buckets self-map — EXCEPT 'critical', which is itself an alias
    # for the 'severe' bucket (policy quirk). The critical bucket is reached via
    # very_high/very_low/deficient, asserted below.
    for bucket in ("optimal", "near_optimal", "borderline", "elevated", "severe", "indeterminate"):
        assert rc.normalize_status(bucket) == bucket, bucket

    # aliases -> bucket
    assert rc.normalize_status("normal") == "optimal"
    assert rc.normalize_status("target") == "optimal"
    assert rc.normalize_status("lmhr") == "optimal"
    assert rc.normalize_status("adequate") == "near_optimal"
    assert rc.normalize_status("high") == "elevated"
    assert rc.normalize_status("low") == "elevated"            # policy: low -> elevated by default
    assert rc.normalize_status("optimal_low") == "optimal"     # low-is-good explicit
    assert rc.normalize_status("very_high") == "critical"
    assert rc.normalize_status("deficient") == "critical"
    assert rc.normalize_status("critical") == "severe"         # the documented alias quirk
    assert rc.normalize_status("N/A") == "indeterminate"
    assert rc.normalize_status("near-optimal") == "near_optimal"  # hyphen/underscore tolerance

    # canonical_color
    assert rc.canonical_color("optimal") == "#22c55e"
    assert rc.canonical_color("normal") == "#22c55e"
    assert rc.canonical_color("critical") == "#dc2626"   # critical -> severe bucket
    assert rc.canonical_color("very_high") == "#ef4444"  # -> critical bucket

    # unmapped -> raise (assembly quarantines, never crashes)
    try:
        rc.canonical_color("not_a_status_xyz")
        raise AssertionError("canonical_color must raise on unmapped status")
    except rc.UnmappedStatusError:
        pass

    # the 7 hexes match the biomarker_claims.color CHECK set
    assert set(rc.BUCKET_TO_HEX.values()) == {
        "#22c55e", "#84cc16", "#eab308", "#f97316", "#ef4444", "#dc2626", "#9ca3af"
    }

    print("check_range_color_contract: all assertions passed")


if __name__ == "__main__":
    main()
