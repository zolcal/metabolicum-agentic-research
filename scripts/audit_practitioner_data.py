#!/usr/bin/env python3
"""Audit practitioner data sources across local Metabolicum projects.

This is intentionally read-only for source data. It inventories likely
practitioner files and writes reports in this project for migration planning.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROJECTS = [
    Path("/home/zoltan/Projects/metasync"),
    Path("/home/zoltan/Projects/metabolicum-research"),
    Path("/home/zoltan/Projects/metabolicum-agentic-research"),
]
DEFAULT_OUTPUT_JSON = PROJECT_ROOT / "input" / "research-assets" / "practitioner-data-inventory.json"
DEFAULT_OUTPUT_MD = PROJECT_ROOT / "docs" / "practitioner-data-audit.md"

SUPPORTED_SUFFIXES = {".json", ".yaml", ".yml", ".md", ".csv", ".html"}
PATH_KEYWORDS = {
    "practitioner",
    "practitioners",
    "clinician",
    "clinicians",
    "researcher",
    "researchers",
    "doctor",
    "doctors",
}
CONTENT_PATTERNS = [
    re.compile(r"\bpractitioner(s)?\b", re.IGNORECASE),
    re.compile(r"\bmarker_affinity\b"),
    re.compile(r"\bsource_tier\b"),
    re.compile(r"\bsource_grade\b"),
    re.compile(r"\bcanonical_name\b"),
    re.compile(r"\bevidence_grade\b"),
    re.compile(r"\byoutube_channel_id\b"),
    re.compile(r"\btwitter_handle\b"),
]
SKIP_PARTS = {
    ".git",
    ".next",
    ".nuxt",
    ".pytest_cache",
    ".claude-temp",
    "__pycache__",
    "node_modules",
    "vendor",
    "youtube-video-inventory",
    "hermes-briefs",
    "sm-ranges",
    "signals",
    "narratives",
}
GENERATED_PATH_HINTS = {
    "backup-",
    "fixtures/expected",
    "research-assets/wave-",
    "practitioner-data-inventory.json",
    "practitioner-data-audit.md",
}
ALLOWED_OUTPUT_PREFIXES = {
    ("output", "social-discovery"),
    ("output", "mo-research-2026"),
}
SKIP_TOP_LEVEL_DIRS = {"research-database", "runs", "dist", "build", "coverage"}
SOCIAL_PLATFORMS = {"twitter", "x", "instagram", "facebook", "tiktok", "linkedin", "youtube"}


def _read_text(path: Path, limit: int = 400_000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:limit]
    except Exception:
        return ""


def _path_has_keyword(path: Path) -> bool:
    lowered = str(path).lower()
    return any(keyword in lowered for keyword in PATH_KEYWORDS)


def _is_skipped(path: Path) -> bool:
    parts = set(path.parts)
    if parts & SKIP_PARTS:
        return True
    lowered = str(path).lower()
    return any(hint in lowered for hint in GENERATED_PATH_HINTS)


def is_candidate_file(path: Path) -> bool:
    if path.suffix.lower() not in SUPPORTED_SUFFIXES:
        return False
    if _is_skipped(path):
        return False
    if _path_has_keyword(path):
        return True
    text = _read_text(path)
    return any(pattern.search(text) for pattern in CONTENT_PATTERNS)


def _should_prune_dir(root: Path, child: Path) -> bool:
    name = child.name
    if name in SKIP_PARTS or name.startswith("backup-"):
        return True
    try:
        rel_parts = child.relative_to(root).parts
    except ValueError:
        rel_parts = child.parts
    if rel_parts and rel_parts[0] in SKIP_TOP_LEVEL_DIRS:
        return True
    if rel_parts and rel_parts[0] == "output":
        return not any(rel_parts[: len(prefix)] == prefix for prefix in ALLOWED_OUTPUT_PREFIXES)
    if len(rel_parts) > 8:
        return True
    return False




def _scan_targets_for_root(root: Path) -> list[Path]:
    if root.name == "metasync":
        rels = [
            "docs/research/practitioners",
            "docs/research/templates",
            "docs/plans/practitioners",
            "docs/plans/2026-01-16-practitioners-page-design.md",
            "supabase/migrations/042_practitioner_applications.sql",
        ]
    elif root.name == "metabolicum-research":
        rels = [
            "config/practitioners.yaml",
            "scripts/mo-practitioners.json",
            "output/social-discovery",
            "output/mo-research-2026/control/practitioner-directory-sync.yaml",
            "output/mo-research-2026/reviews/batch-001-detailed-practitioner-source-review.md",
            "output/mo-research-2026/work-orders/approved-practitioner-roster.yaml",
            "research/practitioners",
        ]
    elif root.name == "metabolicum-agentic-research":
        rels = [
            "input/practitioners",
            "input/practitioner_registry.json",
            "input/practitioner_aliases.json",
            "docs/agentic-workflow/03-social-agents-spec.md",
            "docs/agentic-workflow/16-practitioner-directory-system.md",
            "docs/agentic-workflow/20-semantic-practitioner-matching.md",
            "docs/agentic-workflow/practitioner-registry-sync-report-2026-05-26.md",
            "docs/ALIAS-HANDLING-REDESIGN-PROPOSAL.md",
        ]
    else:
        return [root]
    return [root / rel for rel in rels if (root / rel).exists()]

def discover_candidate_files(project_roots: list[Path]) -> list[Path]:
    candidates: list[Path] = []
    for root in project_roots:
        if not root.exists():
            continue
        for target in _scan_targets_for_root(root):
            if target.is_file():
                if is_candidate_file(target):
                    candidates.append(target)
                continue
            for dirpath, dirnames, filenames in os.walk(target):
                current = Path(dirpath)
                dirnames[:] = [
                    d for d in dirnames
                    if not _should_prune_dir(root, current / d)
                ]
                for filename in filenames:
                    path = current / filename
                    if not path.is_file():
                        continue
                    if is_candidate_file(path):
                        candidates.append(path)
    return sorted(set(candidates))


def _load_structured(path: Path) -> Any:
    try:
        if path.suffix.lower() == ".json":
            return json.loads(path.read_text(encoding="utf-8"))
        if path.suffix.lower() in {".yaml", ".yml"}:
            return yaml.safe_load(path.read_text(encoding="utf-8"))
        if path.suffix.lower() == ".csv":
            with open(path, newline="", encoding="utf-8") as f:
                return list(csv.DictReader(f))
    except Exception:
        return None
    return None


def _looks_like_person_record(record: Any) -> bool:
    if not isinstance(record, dict):
        return False
    keys = set(record)
    return bool(keys & {"id", "name", "canonical_name", "full_name", "short_name"}) and bool(
        keys & {
            "aliases",
            "credential",
            "credentials",
            "evidence_grade",
            "grade",
            "source_tier",
            "source_grade",
            "marker_affinity",
            "surfaces",
            "website",
            "youtube_channel",
            "twitter_handle",
            "topics",
            "categories",
        }
    )


def _extract_records(data: Any) -> list[dict]:
    if isinstance(data, dict):
        practitioners = data.get("practitioners")
        if isinstance(practitioners, list):
            return [p for p in practitioners if isinstance(p, dict)]
        for value in data.values():
            if isinstance(value, list) and value and all(isinstance(item, dict) for item in value):
                person_like = [item for item in value if _looks_like_person_record(item)]
                if len(person_like) >= 2:
                    return person_like
    if isinstance(data, list):
        return [item for item in data if _looks_like_person_record(item)]
    return []


def _record_name(record: dict) -> str:
    for field in ("canonical_name", "full_name", "short_name", "name"):
        value = record.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _record_id(record: dict) -> str:
    value = record.get("id")
    if isinstance(value, str) and value.strip():
        return value.strip()
    name = _record_name(record)
    return name


def _surface_counts(records: list[dict]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for record in records:
        for surface in record.get("surfaces") or []:
            if isinstance(surface, dict):
                platform = str(surface.get("platform", "")).strip().lower()
                if platform:
                    counts[platform] += 1
        if record.get("website"):
            counts["website"] += 1
        if record.get("podcast_feed"):
            counts["podcast"] += 1
        if record.get("twitter_handle"):
            counts["twitter"] += 1
        if record.get("youtube_channel") or record.get("youtube_channel_id") or record.get("channel"):
            counts["youtube"] += 1
    return dict(sorted(counts.items()))


def _resource_buckets(data: Any, records: list[dict], text: str) -> list[str]:
    keys = set()
    for record in records:
        keys.update(record.keys())
    if isinstance(data, dict):
        keys.update(data.keys())
    text_lower = text.lower()

    buckets = []
    if keys & {
        "id",
        "name",
        "canonical_name",
        "full_name",
        "short_name",
        "aliases",
        "credential",
        "credentials",
        "source_tier",
        "source_grade",
        "evidence_grade",
        "grade",
        "tier",
    }:
        buckets.append("identity")
    if keys & {"marker_affinity", "categories", "topics", "specialty_focus", "key_contribution"}:
        buckets.append("marker_affinity")
    if keys & {"website", "podcast_feed", "global_site_sources", "surfaces"} or "http" in text_lower:
        buckets.append("web_resources")
    if keys & {"twitter_handle", "youtube_channel", "youtube_channel_id", "channels_to_search", "channel"}:
        buckets.append("social_resources")
    if any(platform in text_lower for platform in SOCIAL_PLATFORMS):
        if "social_resources" not in buckets:
            buckets.append("social_resources")
    return buckets


def analyze_file(path: Path) -> dict:
    text = _read_text(path)
    data = _load_structured(path)
    records = _extract_records(data)
    fields = sorted({field for record in records for field in record.keys()})
    detected_terms = sorted({pattern.pattern for pattern in CONTENT_PATTERNS if pattern.search(text)})

    return {
        "path": str(path),
        "project": _project_name(path),
        "format": path.suffix.lower().lstrip("."),
        "size_bytes": path.stat().st_size,
        "line_count": text.count("\n") + (1 if text else 0),
        "practitioner_count": len(records),
        "fields_present": fields,
        "sample_ids": [_record_id(record) for record in records[:5] if _record_id(record)],
        "sample_names": [_record_name(record) for record in records[:5] if _record_name(record)],
        "surface_counts": _surface_counts(records),
        "resource_buckets": _resource_buckets(data, records, text),
        "detected_terms": detected_terms,
        "canonical_score": _canonical_score(path, records, fields, text),
    }


def _project_name(path: Path) -> str:
    parts = path.parts
    try:
        idx = parts.index("Projects")
        return parts[idx + 1]
    except Exception:
        return path.anchor or "unknown"


def _canonical_score(path: Path, records: list[dict], fields: list[str], text: str) -> int:
    score = 0
    lowered = str(path).lower()
    if records:
        score += min(len(records), 200)
    if "practitioner_registry" in lowered or "practitioners.yaml" in lowered:
        score += 60
    if "single source of truth" in text.lower():
        score += 50
    if {"id", "aliases", "surfaces"} & set(fields):
        score += 30
    if {"marker_affinity", "source_tier", "source_grade"} & set(fields):
        score += 30
    return score


def build_inventory(project_roots: list[Path] | None = None) -> dict:
    roots = project_roots or DEFAULT_PROJECTS
    files = [analyze_file(path) for path in discover_candidate_files(roots)]
    project_counts = Counter(item["project"] for item in files)
    bucket_counts = Counter(bucket for item in files for bucket in item["resource_buckets"])
    surface_counts = Counter()
    for item in files:
        surface_counts.update(item["surface_counts"])

    canonical_candidates = sorted(
        [item for item in files if item["practitioner_count"] > 0],
        key=lambda item: item["canonical_score"],
        reverse=True,
    )[:10]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project_roots": [str(root) for root in roots],
        "summary": {
            "candidate_files": len(files),
            "structured_files": sum(1 for item in files if item["practitioner_count"] > 0),
            "structured_practitioner_records": sum(item["practitioner_count"] for item in files),
            "by_project": dict(sorted(project_counts.items())),
            "by_resource_bucket": dict(sorted(bucket_counts.items())),
            "surface_counts": dict(sorted(surface_counts.items())),
        },
        "canonical_candidates": canonical_candidates,
        "files": files,
    }


def render_markdown_report(inventory: dict) -> str:
    summary = inventory["summary"]
    canonical = inventory.get("canonical_candidates", [])
    top = canonical[0] if canonical else None
    lines = [
        "# Practitioner Data Audit",
        "",
        f"Generated: {inventory['generated_at']}",
        "",
        "## Summary",
        "",
        f"- Candidate files: {summary['candidate_files']}",
        f"- Structured files: {summary['structured_files']}",
        f"- Structured practitioner records across files: {summary['structured_practitioner_records']}",
        f"- Projects: {', '.join(f'{k}={v}' for k, v in summary['by_project'].items())}",
        f"- Resource buckets: {', '.join(f'{k}={v}' for k, v in summary['by_resource_bucket'].items())}",
        f"- Surface counts: {', '.join(f'{k}={v}' for k, v in summary['surface_counts'].items())}",
        "",
        "## Active Canonical Sources",
        "",
        "The maintained practitioner sources now live in `/home/zoltan/Projects/metabolicum-agentic-research/input/practitioners/`.",
        "",
        "- `practitioners.json`: identity, aliases, credentials, region, source tier/grade, and COI.",
        "- `practitioner-marker-affinity.json`: marker affinities, paradigm affinities, and contribution notes.",
        "- `practitioner-web-resources.json`: official/searchable websites, blogs, profiles, and podcast feeds.",
        "- `practitioner-social-resources.json`: YouTube, X/Twitter, LinkedIn, Instagram, Facebook, Substack/newsletter handles.",
        "",
        "## Best Legacy Consolidated Input",
        "",
    ]
    if top:
        lines.extend([
            f"- Path: `{top['path']}`",
            f"- Practitioner records: {top['practitioner_count']}",
            f"- Buckets: {', '.join(top['resource_buckets'])}",
            f"- Fields: {', '.join(top['fields_present'][:24])}",
            "",
        ])
    else:
        lines.extend(["No structured practitioner source was detected.", ""])

    lines.extend([
        "## Canonical Split Status",
        "",
        "The four-file split has been implemented. Legacy files are retained only for compatibility and historical traceability.",
        "",
        "## Candidate Files",
        "",
        "| Project | Records | Buckets | Path |",
        "| --- | ---: | --- | --- |",
    ])
    for item in sorted(inventory["files"], key=lambda x: (x["project"], -x["practitioner_count"], x["path"])):
        buckets = ", ".join(item["resource_buckets"])
        lines.append(f"| {item['project']} | {item['practitioner_count']} | {buckets} | `{item['path']}` |")

    lines.extend([
        "",
        "## Migration Notes",
        "",
        "- This report is audit-only; source practitioner files were not modified.",
        "- Generated Hermes briefs, SM ranges, YouTube inventory, vendor folders, and wave-specific generated research assets are skipped.",
        "- Files with zero structured records may still contain useful narrative context or old directory versions.",
    ])
    return "\n".join(lines) + "\n"


def write_outputs(inventory: dict, output_json: Path, output_md: Path) -> None:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(inventory, indent=2, ensure_ascii=False), encoding="utf-8")
    output_md.write_text(render_markdown_report(inventory), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit practitioner data sources across local projects")
    parser.add_argument("--project", action="append", dest="projects", help="Project root to scan; repeatable")
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON))
    parser.add_argument("--output-md", default=str(DEFAULT_OUTPUT_MD))
    args = parser.parse_args()

    projects = [Path(p) for p in args.projects] if args.projects else DEFAULT_PROJECTS
    inventory = build_inventory(projects)
    write_outputs(inventory, Path(args.output_json), Path(args.output_md))
    print(f"Candidate files: {inventory['summary']['candidate_files']}")
    print(f"Structured files: {inventory['summary']['structured_files']}")
    print(f"Structured practitioner records: {inventory['summary']['structured_practitioner_records']}")
    print(f"Written: {args.output_json}")
    print(f"Written: {args.output_md}")


if __name__ == "__main__":
    main()
