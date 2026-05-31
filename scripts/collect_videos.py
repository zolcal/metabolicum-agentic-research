#!/usr/bin/env python3
"""Collect ranked video matches per marker into a wave-specific index.

Reads:
  - input/youtube-video-inventory/videos/*.json
  - input/research-assets/alias-policy.json
  - input/practitioner_registry.json

Writes:
  - input/research-assets/<wave>/video-index.json

Logic:
  - Tiered alias matching (T1/T2 primary, T3 guarded, T4 excluded)
  - Composite scoring (match base, title, depth, authority, recency, citation, frequency)
  - NO capping — all ranked matches are preserved; capping happens at assembly time.
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

ALIAS_POLICY = PROJECT_ROOT / "input" / "research-assets" / "alias-policy.json"
PRACTITIONER_REGISTRY = PROJECT_ROOT / "input" / "practitioner_registry.json"
SM_RANGES_DIR = PROJECT_ROOT / "input" / "sm-ranges"
YOUTUBE_INVENTORY_DIR = PROJECT_ROOT / "input" / "youtube-video-inventory" / "videos"
OUTPUT_DIR = PROJECT_ROOT / "input" / "research-assets"

# ── Scoring constants ───────────────────────────────────────────────────────

SCORE_SLUG_TITLE = 10
SCORE_SLUG_DESC = 5
SCORE_ALIAS_TITLE = 7
SCORE_ALIAS_DESC = 3
SCORE_TITLE_BONUS = 5

SCORE_DURATION_SHORT = -5      # < 3 min
SCORE_DURATION_MEDIUM = 0      # 3–15 min
SCORE_DURATION_LONG = 3        # 15–120 min
SCORE_DURATION_VLONG = 1       # > 120 min

TIER_SCORES = {"A": 5, "B": 3, "C": 1}

SCORE_RECENCY_FRESH = 2        # < 2 years
SCORE_RECENCY_MATURE = 0       # 2–5 years
SCORE_RECENCY_STALE = -2       # 5–7 years
SCORE_RECENCY_OLD = -4         # > 7 years

SCORE_CITATION = 8

SCORE_FREQ_SINGLE = 0
SCORE_FREQ_LOW = 1             # 2–5
SCORE_FREQ_MED = 2             # 6–15
SCORE_FREQ_HIGH = 3            # > 15

PMID_RE = re.compile(r"\b\d{7,8}\b")
DOI_RE = re.compile(r"10\.\d{4,}/[^\s]+")

# ── IO helpers ──────────────────────────────────────────────────────────────


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ── Registry helpers ────────────────────────────────────────────────────────


def _build_channel_practitioner_map(registry: dict) -> dict[str, str]:
    """Map YouTube channel IDs/handles to practitioner IDs."""
    mapping: dict[str, str] = {}
    for p in registry.get("practitioners", []):
        pid = p["id"]
        for s in p.get("surfaces", []):
            url = s.get("handle_or_url", "")
            m = re.search(r"youtube\.com/channel/([A-Za-z0-9_-]+)", url)
            if m:
                mapping[m.group(1)] = pid
            m = re.search(r"youtube\.com/@([A-Za-z0-9_.-]+)", url)
            if m:
                mapping[m.group(1)] = pid
    return mapping


def _practitioner_tier_map(registry: dict) -> dict[str, str]:
    return {
        p["id"]: p.get("source_tier", "")
        for p in registry.get("practitioners", [])
    }


def _practitioner_marker_affinity(registry: dict) -> dict[str, set[str]]:
    """Map practitioner_id -> set of marker slugs they discuss."""
    mapping: dict[str, set[str]] = {}
    for p in registry.get("practitioners", []):
        pid = p["id"]
        affinities = set(a.lower() for a in p.get("marker_affinity", []))
        mapping[pid] = affinities
    return mapping


# ── Alias policy loading ────────────────────────────────────────────────────


def load_alias_policy(path: Path = ALIAS_POLICY) -> dict[str, dict]:
    if not path.exists():
        raise FileNotFoundError(f"Alias policy not found: {path}")
    return load_json(path)


def get_marker_terms(marker_slug: str, policy: dict) -> dict[str, list[str]]:
    """Return terms grouped by tier for a marker."""
    data = policy.get(marker_slug, {})
    tiers = data.get("tiers", {})
    return {
        "T1": tiers.get("T1", []),
        "T2": tiers.get("T2", []),
        "T3": tiers.get("T3", []),
        "T4": tiers.get("T4", []),
        "excluded": data.get("excluded_terms", []),
    }


# ── Video scoring helpers ───────────────────────────────────────────────────


def _score_depth(video: dict) -> int:
    dur = video.get("duration_seconds") or 0
    if dur <= 0:
        return 0
    minutes = dur / 60
    if minutes < 3:
        return SCORE_DURATION_SHORT
    if minutes < 15:
        return SCORE_DURATION_MEDIUM
    if minutes <= 120:
        return SCORE_DURATION_LONG
    return SCORE_DURATION_VLONG


def _score_authority(video: dict, channel_map: dict[str, str], tier_map: dict[str, str]) -> int:
    discovered = video.get("discovered_via", {})
    pid = discovered.get("practitioner_id", "")
    if pid and pid in tier_map:
        return TIER_SCORES.get(tier_map[pid], 0)

    channel_id = video.get("channel_id", "")
    if channel_id and channel_id in channel_map:
        pid = channel_map[channel_id]
        tier = tier_map.get(pid, "")
        return TIER_SCORES.get(tier, 0)

    return 0


def _score_recency(video: dict) -> int:
    pub = video.get("published_at", "")
    if not pub:
        return 0
    try:
        dt = datetime.datetime.fromisoformat(pub.replace("Z", "+00:00"))
        age_days = (datetime.datetime.now().replace(tzinfo=dt.tzinfo) - dt).days
        age_years = age_days / 365.25
        if age_years < 2:
            return SCORE_RECENCY_FRESH
        if age_years < 5:
            return SCORE_RECENCY_MATURE
        if age_years < 7:
            return SCORE_RECENCY_STALE
        return SCORE_RECENCY_OLD
    except Exception:
        return 0


def _score_citation(video: dict) -> int:
    desc = video.get("description", "")
    if PMID_RE.search(desc) or DOI_RE.search(desc):
        return SCORE_CITATION
    return 0


def _score_frequency(video: dict, allowed_terms: list[str]) -> int:
    text = f"{video.get('title', '')} {video.get('description', '')}"
    count = 0
    for term in allowed_terms:
        count += len(re.findall(r"\b" + re.escape(term) + r"\b", text, re.IGNORECASE))
    if count <= 1:
        return SCORE_FREQ_SINGLE
    if count <= 5:
        return SCORE_FREQ_LOW
    if count <= 15:
        return SCORE_FREQ_MED
    return SCORE_FREQ_HIGH


# ── Tiered matching ─────────────────────────────────────────────────────────


def _build_term_patterns(terms: list[str]) -> list[re.Pattern]:
    return [re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE) for term in terms if term]


def _find_best_match(video: dict, marker_slug: str, terms_by_tier: dict[str, list[str]]) -> tuple[int, str, str]:
    """Return (base_score, match_term, match_tier) using best-match-wins logic.

    Priority: T1 > T2 > T3 (with guards). T4/excluded are ignored.
    """
    title = video.get("title", "")
    description = video.get("description", "")
    text = f"{title} {description}"
    slug_lower = marker_slug.lower()
    slug_variants = {slug_lower, slug_lower.replace("-", " "), slug_lower.replace("-", "")}

    # T1: slug-native variants
    for variant in sorted(slug_variants, key=len, reverse=True):
        if re.search(r"\b" + re.escape(variant) + r"\b", title, re.IGNORECASE):
            return SCORE_SLUG_TITLE, variant, "T1"
    for variant in sorted(slug_variants, key=len, reverse=True):
        if re.search(r"\b" + re.escape(variant) + r"\b", description, re.IGNORECASE):
            return SCORE_SLUG_DESC, variant, "T1"

    # T2: specific synonyms
    for term in terms_by_tier.get("T2", []):
        if re.search(r"\b" + re.escape(term) + r"\b", title, re.IGNORECASE):
            return SCORE_ALIAS_TITLE, term, "T2"
        if re.search(r"\b" + re.escape(term) + r"\b", description, re.IGNORECASE):
            return SCORE_ALIAS_DESC, term, "T2"

    return 0, "", ""


def _t3_guard_passes(video: dict, marker_slug: str, terms_by_tier: dict[str, list[str]],
                     channel_map: dict[str, str], affinity_map: dict[str, set[str]]) -> bool:
    """T3 terms require at least one guard to pass."""
    title = video.get("title", "")
    description = video.get("description", "")
    text = f"{title} {description}"

    # Guard 1: co-occurrence — a T1/T2 term appears somewhere in the video
    t1_t2_terms = terms_by_tier.get("T1", []) + terms_by_tier.get("T2", [])
    for term in t1_t2_terms:
        if re.search(r"\b" + re.escape(term) + r"\b", text, re.IGNORECASE):
            return True

    # Guard 2: channel-practitioner — video channel maps to a practitioner
    # who has this marker in their affinity. (Strengthened by practitioner-gap
    # enrichment, which added evidence-backed affinities to many practitioners.)
    channel_id = video.get("channel_id", "")
    if channel_id and channel_id in channel_map:
        pid = channel_map[channel_id]
        if marker_slug.lower() in affinity_map.get(pid, set()):
            return True

    # NOTE: a former "duration >= 15 min" guard was removed — long-form content is
    # extremely common (podcasts, lectures), so it let off-topic videos pass on a
    # casual T3-term mention (e.g. a 21-min autism video matching free-carnitine via
    # "carnitine"). T3 now requires a real signal: T1/T2 co-occurrence or an
    # affinity-matched practitioner channel.
    return False


def _find_t3_match(video: dict, marker_slug: str, terms_by_tier: dict[str, list[str]],
                   channel_map: dict[str, str], affinity_map: dict[str, set[str]]) -> tuple[int, str, str]:
    """Try T3 matching with guards. Returns (base_score, match_term, 'T3') or zeros."""
    if not _t3_guard_passes(video, marker_slug, terms_by_tier, channel_map, affinity_map):
        return 0, "", ""

    title = video.get("title", "")
    description = video.get("description", "")

    for term in terms_by_tier.get("T3", []):
        if re.search(r"\b" + re.escape(term) + r"\b", title, re.IGNORECASE):
            return SCORE_ALIAS_TITLE, term, "T3"
        if re.search(r"\b" + re.escape(term) + r"\b", description, re.IGNORECASE):
            return SCORE_ALIAS_DESC, term, "T3"

    return 0, "", ""


def _title_bonus(video: dict, allowed_terms: list[str]) -> int:
    title = video.get("title", "")
    if not title:
        return 0
    for term in allowed_terms:
        if re.search(r"\b" + re.escape(term) + r"\b", title, re.IGNORECASE):
            return SCORE_TITLE_BONUS
    return 0


# ── Core collection logic ───────────────────────────────────────────────────


def rank_videos_for_marker(
    marker_slug: str,
    terms_by_tier: dict[str, list[str]],
    videos: list[dict],
    channel_map: dict[str, str],
    tier_map: dict[str, str],
    affinity_map: dict[str, set[str]],
) -> list[dict]:
    """Collect and score all video matches for a single marker."""
    matched = []

    # Pre-build allowed term lists for each tier combination
    t1_terms = terms_by_tier.get("T1", [])
    t2_terms = terms_by_tier.get("T2", [])
    t3_terms = terms_by_tier.get("T3", [])
    all_active = t1_terms + t2_terms + t3_terms

    # Pre-build patterns for fast filtering
    filter_patterns = _build_term_patterns(all_active)
    if not filter_patterns:
        return matched

    for video in videos:
        text = f"{video.get('title', '')} {video.get('description', '')}"
        if not any(pat.search(text) for pat in filter_patterns):
            continue

        # Best-match-wins: try T1/T2 first, then T3 with guards
        base_score, match_term, match_tier = _find_best_match(video, marker_slug, terms_by_tier)

        if base_score == 0:
            base_score, match_term, match_tier = _find_t3_match(
                video, marker_slug, terms_by_tier, channel_map, affinity_map
            )

        if base_score == 0:
            continue

        # Determine which terms are allowed for frequency scoring
        if match_tier == "T1":
            freq_allowed = t1_terms + t2_terms
        elif match_tier == "T2":
            freq_allowed = t1_terms + t2_terms
        else:  # T3
            freq_allowed = t1_terms + t2_terms + t3_terms

        title_bonus = _title_bonus(video, all_active)
        depth = _score_depth(video)
        authority = _score_authority(video, channel_map, tier_map)
        recency = _score_recency(video)
        citation = _score_citation(video)
        frequency = _score_frequency(video, freq_allowed)

        score = (
            base_score
            + title_bonus
            + depth
            + authority
            + recency
            + citation
            + frequency
        )

        matched.append({
            "video_id": video.get("video_id", ""),
            "url": video.get("url", ""),
            "title": video.get("title", ""),
            "channel": video.get("channel", "unknown"),
            "channel_id": video.get("channel_id", ""),
            "published_at": video.get("published_at", "")[:10] if video.get("published_at") else "",
            "duration_seconds": video.get("duration_seconds") or 0,
            "score": score,
            "match_term": match_term,
            "match_tier": match_tier,
            "breakdown": {
                "match_base": base_score,
                "title_bonus": title_bonus,
                "depth": depth,
                "authority": authority,
                "recency": recency,
                "citation": citation,
                "frequency": frequency,
            },
        })

    matched.sort(key=lambda v: v["score"], reverse=True)
    return matched


# ── Main ────────────────────────────────────────────────────────────────────


def collect_videos_for_wave(wave: str, markers: list[str] | None = None) -> dict:
    wave_dir = SM_RANGES_DIR / wave
    if not wave_dir.exists():
        raise FileNotFoundError(f"SM ranges wave not found: {wave_dir}")

    target_markers = markers or [p.stem for p in sorted(wave_dir.glob("*.yaml"))]
    if not target_markers:
        raise ValueError(f"No markers found for wave: {wave}")

    print(f"Loading alias policy...")
    policy = load_alias_policy()

    print(f"Loading practitioner registry...")
    registry = load_json(PRACTITIONER_REGISTRY)
    channel_map = _build_channel_practitioner_map(registry)
    tier_map = _practitioner_tier_map(registry)
    affinity_map = _practitioner_marker_affinity(registry)

    print(f"Loading YouTube inventory...")
    videos = []
    if YOUTUBE_INVENTORY_DIR.exists():
        for path in sorted(YOUTUBE_INVENTORY_DIR.glob("*.json")):
            try:
                videos.append(load_json(path))
            except Exception as e:
                print(f"  ⚠️  Failed to load inventory {path.name}: {e}", file=sys.stderr)
    print(f"  videos loaded: {len(videos)}")

    result: dict[str, list[dict]] = {}
    summary = {"wave": wave, "markers_processed": 0, "total_matches": 0, "markers": {}}

    for marker_slug in target_markers:
        terms_by_tier = get_marker_terms(marker_slug, policy)
        ranked = rank_videos_for_marker(
            marker_slug, terms_by_tier, videos, channel_map, tier_map, affinity_map
        )
        result[marker_slug] = ranked

        match_count = len(ranked)
        summary["markers_processed"] += 1
        summary["total_matches"] += match_count
        summary["markers"][marker_slug] = {
            "matches": match_count,
            "top_score": ranked[0]["score"] if ranked else 0,
            "top_term": ranked[0]["match_term"] if ranked else "",
            "top_tier": ranked[0]["match_tier"] if ranked else "",
        }

        tier_counts = {"T1": 0, "T2": 0, "T3": 0}
        for v in ranked:
            tier_counts[v["match_tier"]] = tier_counts.get(v["match_tier"], 0) + 1

        print(
            f"✓ {marker_slug}: {match_count} matches "
            f"(T1={tier_counts['T1']} T2={tier_counts['T2']} T3={tier_counts['T3']}) "
            f"top={ranked[0]['score'] if ranked else 0}"
        )

    # Write index
    out_path = OUTPUT_DIR / wave / "video-index.json"
    save_json(out_path, result)
    print(f"\nWritten: {out_path}")

    # Write summary
    summary_path = OUTPUT_DIR / wave / "video-index-summary.json"
    save_json(summary_path, summary)
    print(f"Written: {summary_path}")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Collect ranked video matches per marker")
    parser.add_argument("--wave", default="wave-0", help="Wave directory under input/sm-ranges/")
    parser.add_argument("--markers", nargs="+", help="Limit to specific marker slugs")
    args = parser.parse_args()

    summary = collect_videos_for_wave(args.wave, args.markers)
    print(f"\nTotal markers: {summary['markers_processed']}")
    print(f"Total matches: {summary['total_matches']}")


if __name__ == "__main__":
    main()
