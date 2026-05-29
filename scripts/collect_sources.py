#!/usr/bin/env python3
"""Collect public source pointers per marker into a wave-specific index.

Reads:
  - input/sm-ranges/<wave>/<marker>.yaml
  - input/research-assets/<wave>/practitioner-index.json

Writes:
  - input/research-assets/<wave>/source-index.json
  - input/research-assets/<wave>/source-index-summary.json

This script does not fetch the web. It projects already-known public IDs and
registered practitioner surfaces into an auditable reusable asset.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

SM_RANGES_DIR = PROJECT_ROOT / "input" / "sm-ranges"
OUTPUT_DIR = PROJECT_ROOT / "input" / "research-assets"

SOCIAL_PLATFORMS = {"twitter", "x", "instagram", "facebook", "tiktok", "linkedin"}


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_yaml(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _dedupe(items: list[dict]) -> list[dict]:
    seen = set()
    deduped = []
    for item in items:
        key = (
            item.get("type", ""),
            item.get("id", ""),
            item.get("doi", ""),
            item.get("url", ""),
            item.get("practitioner_id", ""),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _normalize_pmid(value) -> str:
    text = str(value).strip()
    return text if re.fullmatch(r"\d{7,8}", text) else ""


def _normalize_pmcid(value) -> str:
    text = str(value).strip()
    if not text:
        return ""
    if re.fullmatch(r"\d+", text):
        return f"PMC{text}"
    if re.fullmatch(r"PMC\d+", text, flags=re.IGNORECASE):
        return "PMC" + text[3:]
    return ""


def _normalize_doi(value) -> str:
    text = unquote(str(value).strip())
    if not text:
        return ""
    text = re.sub(r"^https?://(dx\.)?doi\.org/", "", text, flags=re.IGNORECASE)
    text = text.strip().rstrip(".")
    return text if text.lower().startswith("10.") else ""


def _collect_public_ids(sm: dict) -> tuple[list[str], list[str], list[str]]:
    pmids: list[str] = []
    pmcids: list[str] = []
    dois: list[str] = []

    def add_ids(container: dict) -> None:
        for value in _as_list(container.get("pmids")):
            pmid = _normalize_pmid(value)
            if pmid:
                pmids.append(pmid)
        for value in _as_list(container.get("pmcids")):
            pmcid = _normalize_pmcid(value)
            if pmcid:
                pmcids.append(pmcid)
        for value in _as_list(container.get("dois")):
            doi = _normalize_doi(value)
            if doi:
                dois.append(doi)

    add_ids(sm.get("known_research_context") or {})
    for row in sm.get("rows") or []:
        if isinstance(row, dict):
            add_ids(row.get("public_source_ids") or {})

    return (
        list(dict.fromkeys(pmids)),
        list(dict.fromkeys(pmcids)),
        list(dict.fromkeys(dois)),
    )


def _is_public_surface(surface: dict) -> bool:
    platform = str(surface.get("platform", "")).lower()
    if platform == "youtube" or platform in SOCIAL_PLATFORMS:
        return False
    url = str(surface.get("handle_or_url", "")).strip()
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def collect_sources_for_marker(marker_slug: str, sm: dict, practitioners: list[dict]) -> list[dict]:
    items: list[dict] = []
    pmids, pmcids, dois = _collect_public_ids(sm)

    for pmid in pmids:
        items.append({
            "type": "pubmed",
            "id": pmid,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        })

    for pmcid in pmcids:
        items.append({
            "type": "pmc_article",
            "id": pmcid,
            "url": f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/",
        })

    for doi in dois:
        items.append({
            "type": "doi",
            "doi": doi,
            "url": f"https://doi.org/{doi}",
        })

    for practitioner in practitioners:
        pid = practitioner.get("id", "")
        for surface in practitioner.get("surfaces") or []:
            if not isinstance(surface, dict) or not _is_public_surface(surface):
                continue
            platform = str(surface.get("platform", "")).lower() or "website"
            source_type = "practitioner_website" if platform == "website" else f"practitioner_{platform}"
            items.append({
                "type": source_type,
                "url": surface["handle_or_url"],
                "platform": platform,
                "practitioner_id": pid,
            })

    return _dedupe(items)


def collect_sources_for_wave(wave: str, markers: list[str] | None = None) -> dict:
    wave_dir = SM_RANGES_DIR / wave
    if not wave_dir.exists():
        raise FileNotFoundError(f"SM ranges wave not found: {wave_dir}")

    target_markers = markers or [p.stem for p in sorted(wave_dir.glob("*.yaml"))]
    asset_wave_dir = OUTPUT_DIR / wave
    practitioner_index_path = asset_wave_dir / "practitioner-index.json"
    practitioner_index = load_json(practitioner_index_path) if practitioner_index_path.exists() else {}

    result: dict[str, list[dict]] = {}
    summary = {"wave": wave, "markers_processed": 0, "total_sources": 0, "markers": {}}

    for marker_slug in target_markers:
        sm_path = wave_dir / f"{marker_slug}.yaml"
        sm = load_yaml(sm_path)
        practitioners = practitioner_index.get(marker_slug, [])
        sources = collect_sources_for_marker(marker_slug, sm, practitioners)
        result[marker_slug] = sources

        counts = {}
        for source in sources:
            source_type = source.get("type", "unknown")
            counts[source_type] = counts.get(source_type, 0) + 1

        summary["markers_processed"] += 1
        summary["total_sources"] += len(sources)
        summary["markers"][marker_slug] = {
            "sources": len(sources),
            "by_type": counts,
        }
        print(f"✓ {marker_slug}: {len(sources)} sources")

    out_path = asset_wave_dir / "source-index.json"
    save_json(out_path, result)
    print(f"\nWritten: {out_path}")

    summary_path = asset_wave_dir / "source-index-summary.json"
    save_json(summary_path, summary)
    print(f"Written: {summary_path}")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Collect public source pointers per marker")
    parser.add_argument("--wave", default="wave-0", help="Wave directory under input/sm-ranges/")
    parser.add_argument("--markers", nargs="+", help="Limit to specific marker slugs")
    args = parser.parse_args()

    summary = collect_sources_for_wave(args.wave, args.markers)
    print(f"\nTotal markers: {summary['markers_processed']}")
    print(f"Total sources: {summary['total_sources']}")


if __name__ == "__main__":
    main()
