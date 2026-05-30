"""Phrase-based discovery terms for a marker.

Uses only the specific T1 (primary phrase) and T2 (qualified alias) tiers from
the alias policy, minus any excluded terms. Bare single-word generic terms
(T3/T4 — 'testosterone', 'blood', 'free') are deliberately NOT used: they are
the source of the false-positive explosion fixed on 2026-05-30.
"""
from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALIAS_POLICY = PROJECT_ROOT / "input" / "research-assets" / "alias-policy.json"


def load_policy(path: Path | None = None) -> dict:
    return json.loads((path or ALIAS_POLICY).read_text(encoding="utf-8"))


def marker_terms(marker_slug: str, policy: dict) -> list[str]:
    data = policy.get(marker_slug, {})
    tiers = data.get("tiers", {})
    excluded = {t.lower() for t in data.get("excluded_terms", [])}
    out: list[str] = []
    seen: set[str] = set()
    for tier in ("T1", "T2"):
        for term in tiers.get(tier, []):
            tl = (term or "").lower()
            if tl and tl not in excluded and tl not in seen:
                seen.add(tl)
                out.append(tl)
    return out
