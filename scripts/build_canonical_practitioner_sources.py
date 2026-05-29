#!/usr/bin/env python3
"""Build canonical practitioner source files from the legacy registry.

The canonical practitioner maintenance model is split by responsibility:
identity, marker affinity, web resources, and social resources. The legacy
registry remains as a compatibility input until all consumers migrate.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REGISTRY = PROJECT_ROOT / "input" / "practitioner_registry.json"
DEFAULT_ALIASES = PROJECT_ROOT / "input" / "practitioner_aliases.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "input" / "practitioners"
SCHEMA_VERSION = "2026-05-29"

SOCIAL_PLATFORMS = {
    "facebook",
    "instagram",
    "linkedin",
    "substack",
    "tiktok",
    "twitter",
    "x",
    "youtube",
}
WEB_PLATFORMS = {
    "blog",
    "institutional_profile",
    "podcast",
    "rss",
    "website",
}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _stable_unique(values: list[Any]) -> list[Any]:
    seen = set()
    unique = []
    for value in values:
        key = json.dumps(value, sort_keys=True, ensure_ascii=False)
        if key in seen:
            continue
        seen.add(key)
        unique.append(value)
    return unique


def _alias_map(path: Path | None) -> dict[str, list[str]]:
    if not path or not path.exists():
        return {}
    data = _load_json(path)
    aliases: dict[str, list[str]] = {}
    for record in data.get("aliases", []):
        practitioner_id = record.get("practitioner_id")
        if not practitioner_id:
            continue
        aliases[practitioner_id] = sorted(
            _stable_unique([alias for alias in record.get("aliases", []) if isinstance(alias, str)])
        )
    return aliases


def _metadata(generated_at: str, source_inputs: list[Path]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "canonical_source": True,
        "source_inputs": [str(path) for path in source_inputs if path.exists()],
    }


def _identity_record(practitioner: dict[str, Any], aliases_by_id: dict[str, list[str]]) -> dict[str, Any]:
    practitioner_id = practitioner["id"]
    aliases = aliases_by_id.get(practitioner_id, practitioner.get("aliases", []))
    return {
        "id": practitioner_id,
        "canonical_name": practitioner["canonical_name"],
        "aliases": sorted(_stable_unique([alias for alias in aliases if isinstance(alias, str)])),
        "entity_type": practitioner.get("entity_type", "person"),
        "country": practitioner.get("country"),
        "region": practitioner.get("region"),
        "languages": practitioner.get("languages", []),
        "credentials": practitioner.get("credentials"),
        "source_tier": practitioner.get("source_tier"),
        "source_grade": practitioner.get("source_grade"),
        "commercial_interests": practitioner.get("commercial_interests", []),
    }


def _marker_record(practitioner: dict[str, Any]) -> dict[str, Any]:
    return {
        "practitioner_id": practitioner["id"],
        "canonical_name": practitioner["canonical_name"],
        "marker_affinity": practitioner.get("marker_affinity", []),
        "paradigm_affinity": practitioner.get("paradigm_affinity", []),
        "key_contribution": practitioner.get("key_contribution"),
    }



def _social_platform_from_value(value: str) -> str | None:
    lowered = value.strip().lower()
    if lowered.startswith('@'):
        return 'twitter'
    host = urlparse(lowered).netloc.replace('www.', '')
    if not host:
        return None
    if host in {'twitter.com', 'x.com'} or host.endswith('.twitter.com') or host.endswith('.x.com'):
        return 'twitter'
    if host == 'youtube.com' or host.endswith('.youtube.com') or host == 'youtu.be':
        return 'youtube'
    if host == 'linkedin.com' or host.endswith('.linkedin.com'):
        return 'linkedin'
    if host == 'instagram.com' or host.endswith('.instagram.com'):
        return 'instagram'
    if host == 'facebook.com' or host.endswith('.facebook.com'):
        return 'facebook'
    if host == 'tiktok.com' or host.endswith('.tiktok.com'):
        return 'tiktok'
    if host == 'substack.com' or host.endswith('.substack.com'):
        return 'substack'
    return None

def _surface_record(practitioner: dict[str, Any], surface: dict[str, Any], *, web: bool) -> dict[str, Any]:
    handle_or_url = surface.get("handle_or_url")
    platform = str(surface.get("platform", "")).strip().lower()
    if not web:
        platform = _social_platform_from_value(str(handle_or_url or "")) or platform
    record = {
        "practitioner_id": practitioner["id"],
        "canonical_name": practitioner["canonical_name"],
        "platform": platform,
        "priority": surface.get("priority", "secondary"),
        "discovery_mode": surface.get("discovery_mode", "manual_seed"),
        "notes": surface.get("notes"),
    }
    if web:
        record["url"] = handle_or_url
        if surface.get("rss_feed_url"):
            record["rss_feed_url"] = surface.get("rss_feed_url")
    else:
        record["handle_or_url"] = handle_or_url
    return {key: value for key, value in record.items() if value not in (None, "", [])}


def _is_web_surface(surface: dict[str, Any]) -> bool:
    platform = str(surface.get("platform", "")).strip().lower()
    value = str(surface.get("handle_or_url", "")).strip()
    return (
        platform in WEB_PLATFORMS
        and value.startswith(("http://", "https://"))
        and _social_platform_from_value(value) is None
    )


def _is_social_surface(surface: dict[str, Any]) -> bool:
    platform = str(surface.get("platform", "")).strip().lower()
    value = str(surface.get("handle_or_url", "")).strip()
    return bool(value) and (platform in SOCIAL_PLATFORMS or _social_platform_from_value(value) is not None)


def build_canonical_sources(
    registry_path: Path = DEFAULT_REGISTRY,
    aliases_path: Path | None = DEFAULT_ALIASES,
    *,
    generated_at: str | None = None,
) -> dict[str, dict[str, Any]]:
    generated = generated_at or datetime.now(timezone.utc).isoformat()
    registry = _load_json(registry_path)
    practitioners = registry.get("practitioners", [])
    aliases_by_id = _alias_map(aliases_path)
    source_inputs = [registry_path]
    if aliases_path:
        source_inputs.append(aliases_path)

    identity = [_identity_record(practitioner, aliases_by_id) for practitioner in practitioners]
    marker_affinity = [_marker_record(practitioner) for practitioner in practitioners]
    web_resources = []
    social_resources = []
    for practitioner in practitioners:
        for surface in practitioner.get("surfaces", []):
            if not isinstance(surface, dict):
                continue
            if _is_web_surface(surface):
                web_resources.append(_surface_record(practitioner, surface, web=True))
            if _is_social_surface(surface):
                social_resources.append(_surface_record(practitioner, surface, web=False))

    identity.sort(key=lambda item: item["id"])
    marker_affinity.sort(key=lambda item: item["practitioner_id"])
    web_resources.sort(key=lambda item: (item["practitioner_id"], item["platform"], item.get("url", "")))
    social_resources.sort(
        key=lambda item: (item["practitioner_id"], item["platform"], item.get("handle_or_url", ""))
    )

    return {
        "practitioners": {
            **_metadata(generated, source_inputs),
            "description": "Canonical practitioner identity, aliases, credentials, region, tier, grade, and COI.",
            "practitioners": identity,
        },
        "marker_affinity": {
            **_metadata(generated, source_inputs),
            "description": "Canonical practitioner marker and paradigm affinity.",
            "marker_affinities": marker_affinity,
        },
        "web_resources": {
            **_metadata(generated, source_inputs),
            "description": "Canonical official/searchable practitioner web resources.",
            "web_resources": web_resources,
        },
        "social_resources": {
            **_metadata(generated, source_inputs),
            "description": "Canonical practitioner social and distribution channels for future discovery.",
            "social_resources": social_resources,
        },
    }


def _readme() -> str:
    return """# Canonical Practitioner Sources

These four files are the practitioner source of truth for ongoing Metabolicum
research maintenance:

- `practitioners.json` - identity, aliases, credentials, location, tier/grade, and COI.
- `practitioner-marker-affinity.json` - marker and paradigm relevance.
- `practitioner-web-resources.json` - official/searchable websites, blogs, profiles, and podcast feeds.
- `practitioner-social-resources.json` - YouTube, X/Twitter, LinkedIn, Instagram, Facebook, Substack, and similar distribution surfaces.

Legacy practitioner files in `input/practitioner_registry.json`,
`input/practitioner_aliases.json`, `metabolicum-research/config/practitioners.yaml`,
and the old markdown practitioner directories should be treated as compatibility
or historical inputs. New maintenance work should update this directory first.
"""


def write_canonical_sources(bundle: dict[str, dict[str, Any]], output_dir: Path = DEFAULT_OUTPUT_DIR) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "practitioners.json": bundle["practitioners"],
        "practitioner-marker-affinity.json": bundle["marker_affinity"],
        "practitioner-web-resources.json": bundle["web_resources"],
        "practitioner-social-resources.json": bundle["social_resources"],
    }
    for filename, payload in files.items():
        (output_dir / filename).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    (output_dir / "README.md").write_text(_readme(), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build canonical practitioner source files")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--aliases", type=Path, default=DEFAULT_ALIASES)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    bundle = build_canonical_sources(args.registry, args.aliases)
    write_canonical_sources(bundle, args.output_dir)
    print(f"Wrote canonical practitioner sources to {args.output_dir}")
    print(f"Practitioners: {len(bundle['practitioners']['practitioners'])}")
    print(f"Marker affinities: {len(bundle['marker_affinity']['marker_affinities'])}")
    print(f"Web resources: {len(bundle['web_resources']['web_resources'])}")
    print(f"Social resources: {len(bundle['social_resources']['social_resources'])}")


if __name__ == "__main__":
    main()
