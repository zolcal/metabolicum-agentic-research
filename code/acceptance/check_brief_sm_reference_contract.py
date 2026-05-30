#!/usr/bin/env python3
"""DB-free contract check: EVERY Hermes brief's council-only sm_reference resolves.

Walks all briefs under input/hermes-briefs/ and calls resolve_sm_reference on each.
This catches the failures a filename-existence check misses — e.g. the
bilirubin-total canonical-slug drift where the SM file's internal marker_slug
disagreed with the pointer (Codex review 2026-05-29, finding #3). No DB / network / LLM.
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import yaml  # noqa: E402

from code.loaders.sm_reference import resolve_sm_reference  # noqa: E402

BRIEFS_DIR = PROJECT_ROOT / "input" / "hermes-briefs"


def main() -> None:
    briefs = sorted(p for p in BRIEFS_DIR.rglob("*.yaml") if not p.name.startswith("_"))
    if not briefs:
        print("check_brief_sm_reference: NO briefs found under input/hermes-briefs/", file=sys.stderr)
        sys.exit(1)

    failures: list[tuple[Path, str]] = []
    for p in briefs:
        try:
            data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            ref = data.get("sm_reference")
            if not isinstance(ref, dict):
                failures.append((p, "missing council-only sm_reference pointer"))
                continue
            resolve_sm_reference(ref)
        except Exception as e:  # FileNotFound, slug mismatch, bad visibility, etc.
            failures.append((p, str(e)))

    total = len(briefs)
    if failures:
        print(f"check_brief_sm_reference: {len(failures)}/{total} brief(s) FAILED sm_reference resolution:",
              file=sys.stderr)
        for p, msg in failures[:25]:
            print(f"  {p.relative_to(PROJECT_ROOT)}: {msg}", file=sys.stderr)
        sys.exit(1)

    print(f"check_brief_sm_reference: all {total} briefs resolve their council-only sm_reference")


if __name__ == "__main__":
    main()
