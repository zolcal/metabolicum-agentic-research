#!/usr/bin/env python3
"""Assemble clean Hermes briefs from SM ranges and collected research assets.

Reads:
  - input/sm-ranges/<wave>/<marker>.yaml
  - input/research-assets/<wave>/video-index.json
  - input/research-assets/<wave>/practitioner-index.json
  - input/research-assets/<wave>/source-index.json

Writes:
  - input/hermes-briefs/<wave>/<marker>.yaml

Assembly is a projection step. Scores, match terms, and collection metadata stay
in the research asset indices.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import functools  # noqa: E402

from code import ground_truth as gt  # noqa: E402

SM_RANGES_DIR = PROJECT_ROOT / "input" / "sm-ranges"
ASSET_DIR = PROJECT_ROOT / "input" / "research-assets"
BRIEFS_DIR = PROJECT_ROOT / "input" / "hermes-briefs"

POINTER_FIELDS = [
    "recommended_youtube_video_ids",
    "recommended_practitioner_ids",
    "recommended_pubmed_ids",
    "recommended_dois",
    "recommended_source_urls",
    "recommended_search_queries",
]

def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_yaml(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, sort_keys=False, allow_unicode=True, default_flow_style=False)


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(v for v in values if isinstance(v, str) and v))


def _brief_identity(marker_slug: str, wave: str, sm: dict) -> dict:
    brief = {
        "marker_slug": sm.get("marker_slug") or marker_slug,
        "marker_name": sm.get("marker_name") or marker_slug,
        "schema_version": "hermes-brief-1",
        "sm_reference": {
            "wave": wave,
            "marker_slug": marker_slug,
            "visibility": "council_only",
        },
    }
    if sm.get("unit") is not None:
        brief["unit"] = sm.get("unit")
    for field in ("direction", "risk_direction"):
        value = sm.get(field)
        if isinstance(value, str) and value:
            brief[field] = value
    return brief


def _ranked_videos(video_entries: list[dict], cap: int) -> list[dict]:
    """Top-`cap` videos in score order, KEEPING the rank metadata (score/title/channel).
    The old _video_ids() discarded scores; the rank is real signal Hermes should see."""
    ranked = sorted(video_entries, key=lambda v: -(v.get("score") or 0))
    seen: set[str] = set()
    out: list[dict] = []
    for v in ranked:
        vid = v.get("video_id")
        if not vid or vid in seen:
            continue
        seen.add(vid)
        out.append({"video_id": vid, "score": v.get("score"),
                    "title": v.get("title"), "channel": v.get("channel")})
        if len(out) >= cap:
            break
    return out


@functools.lru_cache(maxsize=1)
def _category_practitioners() -> dict[str, list[str]]:
    """category_slug -> practitioners, from the ground-truth-derived marker_categories.yaml."""
    cats = load_yaml(PROJECT_ROOT / "input" / "marker_categories.yaml").get("categories", [])
    return {c["slug"]: list(c.get("practitioners") or []) for c in cats}


@functools.lru_cache(maxsize=1)
def _direct_affinity() -> dict[str, list[str]]:
    """marker_slug -> practitioners whose marker_affinity contains it (EXACT, marker-specific).
    This is the real marker<->practitioner edge; the substring bug was in the matcher, not the data."""
    reg = load_json(PROJECT_ROOT / "input" / "practitioner_registry.json")
    entries = reg if isinstance(reg, list) else reg.get("practitioners") or list(reg.values())
    out: dict[str, set] = {}
    for e in entries:
        if isinstance(e, dict):
            for m in (e.get("marker_affinity") or []):
                out.setdefault(m, set()).add(e.get("id"))
    return {k: sorted(v) for k, v in out.items()}


def _primary_category(canonical_slug: str) -> str | None:
    return next((m.get("primary_category") for m in gt.markers() if m["slug"] == canonical_slug), None)


def _practitioners_for(canonical_slug: str) -> list[str]:
    """Union of exact marker-affinity practitioners and the category cohorts over all
    the marker's (enriched) categories. Direct affinity alone is too sparse (often 0-1
    practitioners), so the category cohort always supplements it rather than only when
    direct affinity is empty."""
    direct = set(_direct_affinity().get(canonical_slug) or [])
    cohorts = _category_practitioners()
    cohort = {p for c in gt.categories_for(canonical_slug) for p in cohorts.get(c, [])}
    return sorted(direct | cohort)


def _source_pointers(source_entries: list[dict]) -> tuple[list[str], list[str], list[str]]:
    pubmed_ids: list[str] = []
    dois: list[str] = []
    urls: list[str] = []

    for source in source_entries:
        source_type = source.get("type", "")
        if source_type == "pubmed":
            pubmed_ids.append(source.get("id", ""))
        elif source_type == "doi":
            dois.append(source.get("doi", ""))
        else:
            urls.append(source.get("url", ""))

    return _unique(pubmed_ids), _unique(dois), _unique(urls)


@functools.lru_cache(maxsize=1)
def _practitioner_public_urls() -> dict[str, list[str]]:
    """practitioner_id -> public website/blog surface URLs from the registry.

    Reuses collect_sources._is_public_surface so the social/YouTube exclusion rule
    lives in one place. These feed recommended_source_urls for the marker's matched
    practitioners — the SAME list as recommended_practitioner_ids — instead of the
    stale source-index, whose practitioner list diverged from the brief's."""
    from scripts.collect_sources import _is_public_surface

    reg = load_json(PROJECT_ROOT / "input" / "practitioner_registry.json")
    entries = reg if isinstance(reg, list) else reg.get("practitioners") or list(reg.values())
    out: dict[str, list[str]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        urls = [
            s["handle_or_url"]
            for s in (entry.get("surfaces") or [])
            if isinstance(s, dict) and _is_public_surface(s)
        ]
        if urls:
            out[entry.get("id")] = _unique(urls)
    return out


def _search_queries(brief: dict) -> list[str]:
    name = brief.get("marker_name") or brief.get("marker_slug") or "marker"
    return [
        f"{name} practitioner optimal range",
        f"{name} metabolic optimization",
    ]


def assemble_marker(
    marker_slug: str,
    wave: str,
    sm: dict,
    video_index: dict,
    source_index: dict,
    video_cap: int,
) -> dict:
    canonical = gt.resolve_slug(marker_slug) or marker_slug
    supported, rationale = gt.mo_status(canonical)
    brief = _brief_identity(marker_slug, wave, sm)
    # The condition Hermes recognizes + honors; the pipeline persists it as the
    # marker_mo_determination record on its run.
    brief["mo_supported"] = supported
    brief["mo_rationale"] = rationale

    if supported:
        # Recommendation packet — leads to bootstrap the agent's discovery.
        pubmed_ids, dois, source_urls = _source_pointers(source_index.get(marker_slug, []))
        ranked = _ranked_videos(video_index.get(marker_slug, []), video_cap)
        practitioner_ids = _practitioners_for(canonical)
        brief["recommended_youtube_video_ids"] = [v["video_id"] for v in ranked]
        brief["recommended_practitioner_ids"] = practitioner_ids
        brief["recommended_pubmed_ids"] = pubmed_ids
        brief["recommended_dois"] = dois
        # Practitioner websites/blogs come from the same matched practitioners the
        # brief recommends (registry surfaces), merged with the SM-anchor sources.
        practitioner_urls = [
            url for pid in practitioner_ids for url in _practitioner_public_urls().get(pid, [])
        ]
        brief["recommended_source_urls"] = _unique(source_urls + practitioner_urls)
        brief["recommended_search_queries"] = _search_queries(brief)
    else:
        # not_supported: pass-through — uniform schema, empty packet (no research run).
        brief["recommended_youtube_video_ids"] = []
        brief["recommended_practitioner_ids"] = []
        brief["recommended_pubmed_ids"] = []
        brief["recommended_dois"] = []
        brief["recommended_source_urls"] = []
        brief["recommended_search_queries"] = []
    return brief


def assemble_wave(wave: str, video_cap: int = 30, markers: list[str] | None = None) -> dict:
    wave_dir = SM_RANGES_DIR / wave
    if not wave_dir.exists():
        raise FileNotFoundError(f"SM ranges wave not found: {wave_dir}")

    # EVERY marker gets a brief carrying its mo_supported determination — the condition
    # Hermes recognizes and honors. Out-of-scope markers are NOT pruned; they get a brief
    # with mo_supported=false and no recommendation packet (pass-through on the pipeline run).
    target_markers = markers or [p.stem for p in sorted(wave_dir.glob("*.yaml"))]
    asset_wave_dir = ASSET_DIR / wave
    video_index = load_json(asset_wave_dir / "video-index.json")
    source_index = load_json(asset_wave_dir / "source-index.json")

    summary = {"wave": wave, "supported": 0, "not_supported": 0, "markers_processed": 0, "markers": {}}

    for marker_slug in target_markers:
        sm = load_yaml(wave_dir / f"{marker_slug}.yaml")
        brief = assemble_marker(marker_slug, wave, sm, video_index, source_index, video_cap)
        out_path = BRIEFS_DIR / wave / f"{marker_slug}.yaml"
        save_yaml(out_path, brief)

        supported = brief["mo_supported"]
        marker_summary = {
            "mo_supported": supported,
            "videos": len(brief.get("recommended_youtube_video_ids", [])),
            "practitioners": len(brief.get("recommended_practitioner_ids", [])),
            "pubmed_ids": len(brief.get("recommended_pubmed_ids", [])),
            "dois": len(brief.get("recommended_dois", [])),
            "source_urls": len(brief.get("recommended_source_urls", [])),
        }
        summary["supported" if supported else "not_supported"] += 1
        summary["markers_processed"] += 1
        summary["markers"][marker_slug] = marker_summary
        flag = "MO" if supported else "--"
        print(
            f"[{flag}] {marker_slug}: "
            f"videos={marker_summary['videos']} "
            f"practitioners={marker_summary['practitioners']} "
            f"pubmed={marker_summary['pubmed_ids']} "
            f"sources={marker_summary['source_urls']}"
        )

    summary_path = BRIEFS_DIR / wave / "_generation_summary.json"
    save_json(summary_path, summary)
    print(f"\nWritten: {summary_path}")
    print(f"Supported: {summary['supported']}  Not-supported: {summary['not_supported']}")
    return summary


def main():
    parser = argparse.ArgumentParser(description="Assemble clean Hermes briefs from collected assets")
    parser.add_argument("--wave", default="wave-0", help="Wave directory under input/sm-ranges/")
    parser.add_argument("--markers", nargs="+", help="Limit to specific marker slugs")
    parser.add_argument("--video-cap", type=int, default=30)
    parser.add_argument(
        "--collect-sources",
        action="store_true",
        help="Run source collection for the wave before assembly",
    )
    args = parser.parse_args()

    if args.collect_sources:
        from scripts.collect_sources import collect_sources_for_wave

        collect_sources_for_wave(args.wave, args.markers)

    summary = assemble_wave(args.wave, video_cap=args.video_cap, markers=args.markers)
    print(f"\nTotal markers: {summary['markers_processed']}")


if __name__ == "__main__":
    main()
