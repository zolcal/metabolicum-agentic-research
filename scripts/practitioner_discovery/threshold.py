"""Evidence-count gate. A candidate earns marker_affinity[marker] only when it
has >= n evidence items for that marker."""
from __future__ import annotations


def apply_threshold(candidates: list[dict], n: int = 2) -> tuple[list[dict], list[dict]]:
    qualifying: list[dict] = []
    held: list[dict] = []
    for c in candidates:
        kept = {m: ev for m, ev in c["evidence"].items() if len(ev) >= n}
        if kept:
            q = dict(c)
            q["evidence"] = kept
            q["marker_affinity"] = sorted(kept.keys())
            qualifying.append(q)
        else:
            held.append(c)
    return qualifying, held
