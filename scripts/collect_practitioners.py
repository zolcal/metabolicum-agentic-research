#!/usr/bin/env python3
"""Collect matched practitioners per marker into a wave-specific index.

Reads:
  - input/practitioner_registry.json
  - input/research-assets/alias-policy.json
  - input/topic_descriptors.yaml (for semantic fallback)

Writes:
  - input/research-assets/<wave>/practitioner-index.json

Logic:
  - Thesaurus matching using T1/T2/T3 terms from alias policy
  - Semantic e5 fallback for markers with zero thesaurus matches
  - Full practitioner metadata preserved for transparency
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

PRACTITIONER_REGISTRY = PROJECT_ROOT / "input" / "practitioner_registry.json"
ALIAS_POLICY = PROJECT_ROOT / "input" / "research-assets" / "alias-policy.json"
TOPIC_DESCRIPTORS = PROJECT_ROOT / "input" / "topic_descriptors.yaml"
SM_RANGES_DIR = PROJECT_ROOT / "input" / "sm-ranges"
OUTPUT_DIR = PROJECT_ROOT / "input" / "research-assets"

_EMBED_MODEL = None


def _get_embed_model():
    global _EMBED_MODEL
    if _EMBED_MODEL is None:
        from sentence_transformers import SentenceTransformer
        _EMBED_MODEL = SentenceTransformer("intfloat/multilingual-e5-large", device="cpu")
    return _EMBED_MODEL


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ── Thesaurus matching ──────────────────────────────────────────────────────


def _build_term_patterns(terms: list[str]) -> list[re.Pattern]:
    return [re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE) for term in terms if term]


def _filter_surfaces(surfaces: list[dict]) -> list[dict]:
    """Exclude YouTube surfaces — videos are handled by video-index.json."""
    return [s for s in surfaces if s.get("platform") not in ("youtube",)]


def find_practitioners_thesaurus(marker_slug: str, practitioners: list[dict], terms_by_tier: dict[str, list[str]]) -> list[dict]:
    """Match practitioners using T1/T2/T3 terms from alias policy."""
    all_terms = (
        terms_by_tier.get("T1", [])
        + terms_by_tier.get("T2", [])
        + terms_by_tier.get("T3", [])
    )
    if not all_terms:
        all_terms = [marker_slug.lower()]

    term_patterns = _build_term_patterns(all_terms)
    matched = []
    seen_ids = set()

    for p in practitioners:
        pid = p["id"]
        if pid in seen_ids:
            continue

        # Check marker_affinity
        affinity_match = False
        affinities = [a.lower() for a in p.get("marker_affinity", [])]
        for term in all_terms:
            t = term.lower()
            for aff in affinities:
                if t == aff or aff in t or t in aff:
                    affinity_match = True
                    break
            if affinity_match:
                break

        # Check text fields
        text_fields = [
            p.get("canonical_name", ""),
            p.get("key_contribution", ""),
            " ".join(p.get("specialty_focus", [])),
            " ".join(p.get("aliases", [])),
        ]
        text = " ".join(text_fields).lower()
        text_match = any(pat.search(text) for pat in term_patterns)

        if affinity_match or text_match:
            seen_ids.add(pid)
            matched.append({
                "id": p["id"],
                "name": p.get("canonical_name", ""),
                "aliases": p.get("aliases", []),
                "tier": p.get("source_tier"),
                "grade": p.get("source_grade"),
                "marker_affinity": p.get("marker_affinity", []),
                "surfaces": _filter_surfaces(p.get("surfaces", [])),
                "match_method": "thesaurus",
                "match_tier": "T1" if affinity_match else "T2",
            })

    return matched


# ── Semantic fallback ───────────────────────────────────────────────────────


def _practitioner_text(p: dict) -> str:
    parts = [
        f"passage: {p.get('canonical_name', '')}",
        p.get("key_contribution", ""),
        " ".join(p.get("specialty_focus", [])),
        " ".join(p.get("marker_affinity", [])),
    ]
    return " ".join(filter(None, parts)).strip()


def _marker_text(descriptor: str) -> str:
    return f"passage: {descriptor}".strip()


def find_practitioners_semantic(
    marker_slugs: list[str],
    practitioners: list[dict],
    descriptors: dict[str, str],
    threshold: float = 0.82,
) -> dict[str, list[dict]]:
    valid_slugs = [s for s in marker_slugs if s in descriptors]
    if not valid_slugs:
        return {s: [] for s in marker_slugs}

    model = _get_embed_model()
    practitioner_texts = [_practitioner_text(p) for p in practitioners]
    practitioner_embs = model.encode(practitioner_texts, normalize_embeddings=True, show_progress_bar=False)

    marker_texts = [_marker_text(descriptors[s]) for s in valid_slugs]
    marker_embs = model.encode(marker_texts, normalize_embeddings=True, show_progress_bar=False)

    scores = np.dot(practitioner_embs, marker_embs.T)

    results: dict[str, list[dict]] = {s: [] for s in marker_slugs}
    for m_idx, slug in enumerate(valid_slugs):
        for p_idx, score in enumerate(scores[:, m_idx]):
            if score >= threshold:
                p = practitioners[p_idx]
                results[slug].append({
                    "id": p["id"],
                    "name": p.get("canonical_name", ""),
                    "aliases": p.get("aliases", []),
                    "tier": p.get("source_tier"),
                    "grade": p.get("source_grade"),
                    "marker_affinity": p.get("marker_affinity", []),
                    "surfaces": _filter_surfaces(p.get("surfaces", [])),
                    "match_method": "semantic",
                    "match_score": round(float(score), 4),
                })

    return results


# ── Main ────────────────────────────────────────────────────────────────────


def collect_practitioners_for_wave(wave: str, markers: list[str] | None = None,
                                    use_semantic: bool = True,
                                    semantic_threshold: float = 0.72) -> dict:
    wave_dir = SM_RANGES_DIR / wave
    if not wave_dir.exists():
        raise FileNotFoundError(f"SM ranges wave not found: {wave_dir}")

    target_markers = markers or [p.stem for p in sorted(wave_dir.glob("*.yaml"))]

    print("Loading practitioner registry...")
    registry = load_json(PRACTITIONER_REGISTRY)
    practitioners = registry.get("practitioners", [])
    print(f"  practitioners: {len(practitioners)}")

    print("Loading alias policy...")
    policy = load_json(ALIAS_POLICY)

    descriptors = {}
    if TOPIC_DESCRIPTORS.exists():
        descriptors = yaml.safe_load(TOPIC_DESCRIPTORS.read_text(encoding="utf-8"))
        print(f"  topic descriptors: {len(descriptors)}")

    # Batch semantic matching for all target markers
    semantic_matches: dict[str, list[dict]] = {s: [] for s in target_markers}
    if use_semantic:
        try:
            semantic_matches = find_practitioners_semantic(
                target_markers, practitioners, descriptors, threshold=semantic_threshold
            )
            print(f"  [semantic] computed for {len(target_markers)} markers")
        except Exception as e:
            print(f"  ⚠️  Batch semantic match failed: {e}", file=sys.stderr)

    result: dict[str, list[dict]] = {}
    summary = {"wave": wave, "markers_processed": 0, "total_matches": 0, "markers": {}}

    for marker_slug in target_markers:
        terms_by_tier = policy.get(marker_slug, {}).get("tiers", {})
        rel_thesaurus = find_practitioners_thesaurus(marker_slug, practitioners, terms_by_tier)

        # Semantic fallback for markers with zero thesaurus matches
        if len(rel_thesaurus) == 0:
            semantic_for_marker = semantic_matches.get(marker_slug, [])
            rel_thesaurus = semantic_for_marker[:10]

        result[marker_slug] = rel_thesaurus
        match_count = len(rel_thesaurus)
        summary["markers_processed"] += 1
        summary["total_matches"] += match_count
        summary["markers"][marker_slug] = {
            "matches": match_count,
            "thesaurus": sum(1 for p in rel_thesaurus if p.get("match_method") == "thesaurus"),
            "semantic": sum(1 for p in rel_thesaurus if p.get("match_method") == "semantic"),
        }

        methods = "/".join(
            sorted(set(p.get("match_method", "?") for p in rel_thesaurus)) or ["none"]
        )
        print(f"✓ {marker_slug}: {match_count} practitioners ({methods})")

    out_path = OUTPUT_DIR / wave / "practitioner-index.json"
    save_json(out_path, result)
    print(f"\nWritten: {out_path}")

    summary_path = OUTPUT_DIR / wave / "practitioner-index-summary.json"
    save_json(summary_path, summary)
    print(f"Written: {summary_path}")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Collect matched practitioners per marker")
    parser.add_argument("--wave", default="wave-0", help="Wave directory under input/sm-ranges/")
    parser.add_argument("--markers", nargs="+", help="Limit to specific marker slugs")
    parser.add_argument("--no-semantic", action="store_true", help="Disable semantic embedding fallback")
    parser.add_argument("--semantic-threshold", type=float, default=0.72)
    args = parser.parse_args()

    summary = collect_practitioners_for_wave(
        args.wave, args.markers,
        use_semantic=not args.no_semantic,
        semantic_threshold=args.semantic_threshold,
    )
    print(f"\nTotal markers: {summary['markers_processed']}")
    print(f"Total matches: {summary['total_matches']}")


if __name__ == "__main__":
    main()
