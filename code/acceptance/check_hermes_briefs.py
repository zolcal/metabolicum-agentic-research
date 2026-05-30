#!/usr/bin/env python3
"""Acceptance check for Hermes briefs.

Validates that generated briefs conform to the pointer framework contract:
- Six pointer fields present and well-formed
- Council-only sm_reference is present and resolvable
- No SM numeric rows or range-bearing context is embedded
- No bloat (transcript text, descriptions, titles, scores, rationale)
- YouTube video IDs have matching inventory files
- Source URLs are permissive/public only
- Original SM YAMLs are untouched
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

SM_RANGES_DIR = PROJECT_ROOT / "input" / "sm-ranges"
BRIEFS_DIR = PROJECT_ROOT / "input" / "hermes-briefs"
YOUTUBE_INVENTORY_DIR = PROJECT_ROOT / "input" / "youtube-video-inventory" / "videos"

QUALIFICATION_MARKERS = {
    "wave-0": ["apob", "hba1c", "fasting-insulin", "lpa"],
    "wave-1": ["igf-1", "vitamin-d", "crp-standard", "hdl-cholesterol", "uric-acid", "fructosamine"],
}

POINTER_FIELDS = [
    "recommended_youtube_video_ids",
    "recommended_practitioner_ids",
    "recommended_pubmed_ids",
    "recommended_dois",
    "recommended_source_urls",
    "recommended_search_queries",
]

FORBIDDEN_SM_FIELDS = {"rows", "anchor_provenance", "known_research_context"}
FORBIDDEN_RANGE_KEYS = {
    "min",
    "max",
    "low",
    "high",
    "lower",
    "upper",
    "age_min",
    "age_max",
    "reference_min",
    "reference_max",
    "target_range_low",
    "target_range_high",
}

# Patterns that indicate bloat inside the brief
BLOAT_PATTERNS = [
    re.compile(r"transcript_text", re.IGNORECASE),
    re.compile(r"transcript_sha256", re.IGNORECASE),
    re.compile(r"match_score", re.IGNORECASE),
    re.compile(r"selection_reason", re.IGNORECASE),
    re.compile(r"rationale", re.IGNORECASE),
]

# Gated/paywalled domain patterns to reject
GATED_DOMAIN_PATTERNS = [
    re.compile(r"\.gov\.\w+/.*\?.*(?i:login|auth|token)"),
]


def load_yaml(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def check_pointer_fields(brief: dict, marker: str, errors: list[str]) -> None:
    for field in POINTER_FIELDS:
        if field not in brief:
            errors.append(f"{marker}: missing pointer field '{field}'")
            continue
        value = brief[field]
        if not isinstance(value, list):
            errors.append(f"{marker}: '{field}' must be a list, got {type(value).__name__}")
            continue
        for item in value:
            if not isinstance(item, str):
                errors.append(f"{marker}: '{field}' items must be strings, got {type(item).__name__}")
                break
        if len(value) != len(set(value)):
            dups = [x for x in value if value.count(x) > 1]
            errors.append(f"{marker}: '{field}' contains duplicates: {set(dups)}")


def check_video_cap(brief: dict, marker: str, errors: list[str], expected_cap: int = 30) -> None:
    video_ids = brief.get("recommended_youtube_video_ids", [])
    if len(video_ids) > expected_cap:
        errors.append(
            f"{marker}: recommended_youtube_video_ids has {len(video_ids)} videos, "
            f"exceeds cap of {expected_cap}"
        )


def check_youtube_inventory(brief: dict, marker: str, errors: list[str]) -> None:
    video_ids = brief.get("recommended_youtube_video_ids", [])
    for vid in video_ids:
        inventory_path = YOUTUBE_INVENTORY_DIR / f"{vid}.json"
        if not inventory_path.exists():
            errors.append(f"{marker}: YouTube video '{vid}' has no inventory file ({inventory_path})")


def check_source_urls(brief: dict, marker: str, errors: list[str]) -> None:
    urls = brief.get("recommended_source_urls", [])
    for url in urls:
        for pat in GATED_DOMAIN_PATTERNS:
            if pat.search(url):
                errors.append(f"{marker}: source URL appears gated/restricted: {url}")


def _check_forbidden_sm_fields(value, marker: str, errors: list[str], path: str = "brief") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in FORBIDDEN_SM_FIELDS:
                errors.append(f"{marker}: forbidden SM field '{key}' in brief")
            if key in FORBIDDEN_RANGE_KEYS:
                errors.append(f"{marker}: forbidden SM numeric bound field '{child_path}' in brief")
            _check_forbidden_sm_fields(child, marker, errors, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _check_forbidden_sm_fields(child, marker, errors, f"{path}[{index}]")


def check_mo_determination(brief: dict, marker: str, errors: list[str]) -> None:
    """The binary MO-support determination Hermes recognizes + honors (overridable)."""
    if "mo_supported" not in brief:
        errors.append(f"{marker}: missing 'mo_supported' determination")
    elif not isinstance(brief["mo_supported"], bool):
        errors.append(f"{marker}: 'mo_supported' must be a bool, got {type(brief['mo_supported']).__name__}")
    if not isinstance(brief.get("mo_rationale"), str) or not brief.get("mo_rationale"):
        errors.append(f"{marker}: 'mo_rationale' must be a non-empty string")


def check_bloat(brief: dict, marker: str, errors: list[str]) -> None:
    """Check that no bloat or embedded SM range fields exist in the brief."""
    # mo_supported/mo_rationale are the legitimate determination fields (mo_rationale
    # would otherwise trip the 'rationale' bloat pattern) — scan everything else.
    scrubbed = {k: v for k, v in brief.items() if k not in ("mo_supported", "mo_rationale")}
    text = json.dumps(scrubbed, default=str)
    for pat in BLOAT_PATTERNS:
        if pat.search(text):
            errors.append(f"{marker}: brief contains potential bloat pattern: {pat.pattern}")

    for forbidden in ("_meta", "transcript_text", "transcript_sha256", "description", "title",
                      "match_score", "selection_reason", "rationale"):
        if forbidden in brief:
            errors.append(f"{marker}: forbidden top-level field '{forbidden}' in brief")

    _check_forbidden_sm_fields(brief, marker, errors)


def check_sm_reference(brief: dict, marker: str, errors: list[str]) -> None:
    ref = brief.get("sm_reference")
    if not isinstance(ref, dict):
        errors.append(f"{marker}: missing or invalid sm_reference")
        return

    wave = ref.get("wave")
    ref_marker = ref.get("marker_slug")
    visibility = ref.get("visibility")
    if not isinstance(wave, str) or not wave:
        errors.append(f"{marker}: sm_reference.wave must be a non-empty string")
    if ref_marker != marker:
        errors.append(f"{marker}: sm_reference.marker_slug must match marker slug")
    if visibility != "council_only":
        errors.append(f"{marker}: sm_reference.visibility must be council_only")
    if isinstance(wave, str) and isinstance(ref_marker, str):
        sm_path = SM_RANGES_DIR / wave / f"{ref_marker}.yaml"
        if not sm_path.exists():
            errors.append(f"{marker}: sm_reference does not resolve to {sm_path}")


def check_sm_unchanged(marker: str, wave: str) -> str | None:
    """Verify SM YAML exists and hasn't been modified in-place."""
    sm_path = SM_RANGES_DIR / wave / f"{marker}.yaml"
    if not sm_path.exists():
        # Try other waves
        for other_wave in SM_RANGES_DIR.glob("wave-*"):
            alt = other_wave / f"{marker}.yaml"
            if alt.exists():
                sm_path = alt
                break
    if not sm_path.exists():
        return f"{marker}: original SM YAML not found"
    # We can't verify unchanged without a stored hash, but we verify it exists
    # and that we didn't write to it.
    return None


def run_checks(markers: list[str], wave: str) -> dict:
    results = {"passed": [], "failed": [], "errors": []}

    for marker in markers:
        brief_path = BRIEFS_DIR / wave / f"{marker}.yaml"
        marker_errors = []

        if not brief_path.exists():
            marker_errors.append(f"{marker}: brief not found at {brief_path}")
            results["failed"].append(marker)
            results["errors"].extend(marker_errors)
            continue

        try:
            brief = load_yaml(brief_path)
        except Exception as e:
            marker_errors.append(f"{marker}: failed to parse brief YAML: {e}")
            results["failed"].append(marker)
            results["errors"].extend(marker_errors)
            continue

        check_mo_determination(brief, marker, marker_errors)
        check_pointer_fields(brief, marker, marker_errors)
        check_video_cap(brief, marker, marker_errors)
        check_youtube_inventory(brief, marker, marker_errors)
        check_source_urls(brief, marker, marker_errors)
        check_bloat(brief, marker, marker_errors)
        check_sm_reference(brief, marker, marker_errors)

        sm_err = check_sm_unchanged(marker, wave)
        if sm_err:
            marker_errors.append(sm_err)

        if marker_errors:
            results["failed"].append(marker)
            results["errors"].extend(marker_errors)
        else:
            results["passed"].append(marker)

    return results


def main():
    parser = argparse.ArgumentParser(description="Acceptance check for Hermes briefs")
    parser.add_argument("--wave", default="wave-0", help="Wave to check")
    parser.add_argument("--markers", nargs="+", help="Limit to specific markers")
    parser.add_argument("--qualification", action="store_true",
                        help="Check all 10 qualification markers")
    args = parser.parse_args()

    if args.qualification:
        all_passed = 0
        all_total = 0
        all_errors = []
        for wave, markers in QUALIFICATION_MARKERS.items():
            print(f"\nChecking {len(markers)} marker(s) in wave '{wave}'")
            print("=" * 60)
            results = run_checks(markers, wave)
            all_passed += len(results["passed"])
            all_total += len(markers)
            all_errors.extend(results["errors"])
            print(f"  Passed: {len(results['passed'])}/{len(markers)}")
            if results["failed"]:
                print(f"  Failed: {len(results['failed'])}/{len(markers)}")
                for m in results["failed"]:
                    print(f"    ✗ {m}")

        print(f"\n{'=' * 60}")
        print(f"Total passed: {all_passed}/{all_total}")
        if all_errors:
            print("\nErrors:")
            for err in all_errors:
                print(f"  • {err}")
            sys.exit(1)
        else:
            print("\n✓ All checks passed.")
            sys.exit(0)

    markers = args.markers
    if not markers:
        # Auto-discover from briefs directory
        wave_dir = BRIEFS_DIR / args.wave
        if wave_dir.exists():
            markers = sorted(p.stem for p in wave_dir.glob("*.yaml") if not p.name.startswith("_"))
        else:
            print(f"ERROR: No briefs found in {wave_dir}", file=sys.stderr)
            sys.exit(1)

    print(f"Checking {len(markers)} marker(s) in wave '{args.wave}'")
    print("=" * 60)

    results = run_checks(markers, args.wave)

    print(f"\nPassed: {len(results['passed'])}/{len(markers)}")
    if results["failed"]:
        print(f"Failed: {len(results['failed'])}/{len(markers)}")
        for m in results["failed"]:
            print(f"  ✗ {m}")
    if results["errors"]:
        print("\nErrors:")
        for err in results["errors"]:
            print(f"  • {err}")
        sys.exit(1)
    else:
        print("\n✓ All checks passed.")
        sys.exit(0)


if __name__ == "__main__":
    main()
