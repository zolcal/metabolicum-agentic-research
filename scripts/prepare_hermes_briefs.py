#!/usr/bin/env python3
"""Generate Hermes research briefs from SM range YAMLs + practitioner registry + YouTube inventory.

Uses a thesaurus (marker identity registry aliases + explicit slug mappings) AND
semantic embedding similarity (e5) to match practitioners to markers even when
their marker_affinity uses different slugs or when they discuss the marker in
key_contribution text without explicit affinity.

Reads:
  - input/sm-ranges/<wave>/<marker>.yaml
  - input/practitioner_registry.json
  - input/marker_glossary.json
  - input/registry/marker-identity-registry.v1.yaml (for thesaurus)
  - input/topic_descriptors.yaml (for semantic matching)
  - input/youtube-video-inventory/videos/*.json (optional)

Writes:
  - input/hermes-briefs/<wave>/<marker>.yaml

Does NOT call LLMs or fetch URLs. Deterministic: same inputs -> same output.
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

import numpy as np
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

SM_RANGES_DIR = PROJECT_ROOT / "input" / "sm-ranges"
PRACTITIONER_REGISTRY = PROJECT_ROOT / "input" / "practitioner_registry.json"
MARKER_GLOSSARY = PROJECT_ROOT / "input" / "marker_glossary.json"
MARKER_IDENTITY_REGISTRY = PROJECT_ROOT / "input" / "registry" / "marker-identity-registry.v1.yaml"
TOPIC_DESCRIPTORS = PROJECT_ROOT / "input" / "topic_descriptors.yaml"
YOUTUBE_INVENTORY_DIR = PROJECT_ROOT / "input" / "youtube-video-inventory" / "videos"
BRIEFS_DIR = PROJECT_ROOT / "input" / "hermes-briefs"

QUALIFICATION_MARKERS = [
    "apob", "hba1c", "fasting-insulin", "lpa", "igf-1",
    "vitamin-d", "crp-standard", "hdl-cholesterol", "uric-acid", "fructosamine",
]

EXPLICIT_SLUG_MAPPINGS = {
    "crp-standard": ["hs-crp", "hscrp"],
}

# ── Video ranking weights ───────────────────────────────────────────────────

# match_base: slug vs alias, title vs description
SCORE_SLUG_TITLE = 10
SCORE_SLUG_DESC = 5
SCORE_ALIAS_TITLE = 7
SCORE_ALIAS_DESC = 3

SCORE_TITLE_BONUS = 5

# depth_bonus: duration-based
SCORE_DURATION_SHORT = -5      # < 3 min
SCORE_DURATION_MEDIUM = 0      # 3–15 min
SCORE_DURATION_LONG = 3        # 15–120 min
SCORE_DURATION_VLONG = 1       # > 120 min

# authority_bonus: source_tier mapping
TIER_SCORES = {"A": 5, "B": 3, "C": 1}

# recency_bonus: age-based
SCORE_RECENCY_FRESH = 2        # < 2 years
SCORE_RECENCY_MATURE = 0       # 2–5 years
SCORE_RECENCY_STALE = -2       # 5–7 years
SCORE_RECENCY_OLD = -4         # > 7 years

SCORE_CITATION = 8

# frequency_bonus: term occurrence count
SCORE_FREQ_SINGLE = 0
SCORE_FREQ_LOW = 1             # 2–5
SCORE_FREQ_MED = 2             # 6–15
SCORE_FREQ_HIGH = 3            # > 15

# capping and diversity
DEFAULT_VIDEO_CAP = 30
CHANNEL_DIVERSITY_MAX_RATIO = 0.30

# citation patterns
PMID_RE = re.compile(r"\b\d{7,8}\b")
DOI_RE = re.compile(r"10\.\d{4,}/[^\s]+")

# ── Embedding model (lazy singleton) ────────────────────────────────────────

_EMBED_MODEL = None


def _get_embed_model():
    global _EMBED_MODEL
    if _EMBED_MODEL is None:
        from sentence_transformers import SentenceTransformer
        _EMBED_MODEL = SentenceTransformer("intfloat/multilingual-e5-large", device="cpu")
    return _EMBED_MODEL


# ── IO helpers ──────────────────────────────────────────────────────────────

def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_yaml(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, sort_keys=False, allow_unicode=True, default_flow_style=False)


# ── Thesaurus ───────────────────────────────────────────────────────────────

def build_thesaurus() -> dict[str, list[str]]:
    thesaurus: dict[str, set[str]] = {m: set() for m in QUALIFICATION_MARKERS}

    # 1. Marker glossary terms
    glossary = load_json(MARKER_GLOSSARY)
    for entry in glossary.get("entries", []):
        slug = entry.get("marker", "")
        if slug in thesaurus:
            thesaurus[slug].add(entry.get("term", "").lower())

    # 2. Marker identity registry aliases + equivalent groups
    if MARKER_IDENTITY_REGISTRY.exists():
        identity = load_yaml(MARKER_IDENTITY_REGISTRY)
        for marker in identity.get("markers", []):
            slug = marker.get("marker_slug", "")
            if slug in thesaurus:
                for alias in marker.get("aliases", {}).get("canonical_aliases", []):
                    thesaurus[slug].add(alias.lower())
                thesaurus[slug].add(marker.get("canonical_name", "").lower())
                thesaurus[slug].add(marker.get("display_name", "").lower())

        for group in identity.get("known_equivalent_payload_groups", {}).get("stale_alias_payload_groups", []):
            winner = group.get("winner", "")
            if winner in thesaurus:
                for member in group.get("members", []):
                    thesaurus[winner].add(member.lower())

        for group in identity.get("known_equivalent_payload_groups", {}).get("equivalent_payload_due_to_data_bug", []):
            members = group.get("members", [])
            for slug in members:
                if slug in thesaurus:
                    for other in members:
                        if other != slug:
                            thesaurus[slug].add(other.lower())

    # 3. Explicit slug mappings
    for slug, mapped in EXPLICIT_SLUG_MAPPINGS.items():
        if slug in thesaurus:
            for m in mapped:
                thesaurus[slug].add(m.lower())

    for slug in thesaurus:
        thesaurus[slug].add(slug.lower())
        thesaurus[slug].add(slug.lower().replace("-", " "))
        thesaurus[slug].add(slug.lower().replace("-", ""))

    return {k: sorted(v for v in vals if v) for k, vals in thesaurus.items()}


# ── Thesaurus-based practitioner search ─────────────────────────────────────

def find_practitioners_thesaurus(marker_slug: str, practitioners: list[dict], thesaurus: dict) -> list[dict]:
    search_terms = thesaurus.get(marker_slug, [marker_slug.lower()])
    term_patterns = [re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE) for term in search_terms]

    matched = []
    seen_ids = set()

    for p in practitioners:
        pid = p["id"]
        if pid in seen_ids:
            continue

        affinities = p.get("marker_affinity", [])
        affinity_match = False
        for term in search_terms:
            for aff in affinities:
                if term.lower() == aff.lower() or aff.lower() in term.lower() or term.lower() in aff.lower():
                    affinity_match = True
                    break
            if affinity_match:
                break

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
                "name": p["canonical_name"],
                "tier": p.get("source_tier"),
                "grade": p.get("source_grade"),
                "surfaces": p.get("surfaces", []),
            })

    return matched


# ── Semantic embedding practitioner search ──────────────────────────────────

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
    """Find practitioners by embedding similarity to marker topic descriptors.

    Efficient: embeds all practitioners and all descriptors once, then
    computes the full similarity matrix.

    Returns a dict mapping marker_slug -> list of matched practitioners.
    """
    valid_slugs = [s for s in marker_slugs if s in descriptors]
    if not valid_slugs:
        return {s: [] for s in marker_slugs}

    model = _get_embed_model()

    # Embed all practitioners once
    practitioner_texts = [_practitioner_text(p) for p in practitioners]
    practitioner_embs = model.encode(
        practitioner_texts, normalize_embeddings=True, show_progress_bar=False
    )

    # Embed all marker descriptors once
    marker_texts = [_marker_text(descriptors[s]) for s in valid_slugs]
    marker_embs = model.encode(
        marker_texts, normalize_embeddings=True, show_progress_bar=False
    )

    # Full similarity matrix: (n_practitioners, n_markers)
    scores = np.dot(practitioner_embs, marker_embs.T)

    results: dict[str, list[dict]] = {s: [] for s in marker_slugs}
    for m_idx, slug in enumerate(valid_slugs):
        for p_idx, score in enumerate(scores[:, m_idx]):
            if score >= threshold:
                p = practitioners[p_idx]
                results[slug].append({
                    "id": p["id"],
                    "name": p["canonical_name"],
                    "tier": p.get("source_tier"),
                    "grade": p.get("source_grade"),
                    "surfaces": p.get("surfaces", []),
                })

    return results


# ── YouTube inventory ───────────────────────────────────────────────────────

def load_youtube_inventory() -> list[dict]:
    videos = []
    if not YOUTUBE_INVENTORY_DIR.exists():
        return videos
    for path in sorted(YOUTUBE_INVENTORY_DIR.glob("*.json")):
        try:
            videos.append(load_json(path))
        except Exception as e:
            print(f"  ⚠️  Failed to load inventory {path.name}: {e}", file=sys.stderr)
    return videos


# ── Video scoring helpers ───────────────────────────────────────────────────

def _build_channel_practitioner_map(registry: dict) -> dict[str, str]:
    """Map YouTube channel IDs/handles to practitioner IDs from registry surfaces."""
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
    """Map practitioner ID to source_tier."""
    return {
        p["id"]: p.get("source_tier", "")
        for p in registry.get("practitioners", [])
    }


def _score_match_base(video: dict, marker_slug: str, terms: list[str]) -> tuple[int, str]:
    """Return (score, matched_term) based on slug vs alias and title vs description."""
    title = video.get("title", "")
    description = video.get("description", "")
    slug_lower = marker_slug.lower()
    slug_variants = {slug_lower, slug_lower.replace("-", " "), slug_lower.replace("-", "")}

    # Check title first
    for variant in slug_variants:
        if re.search(r"\b" + re.escape(variant) + r"\b", title, re.IGNORECASE):
            return SCORE_SLUG_TITLE, variant
    # Check description for slug
    for variant in slug_variants:
        if re.search(r"\b" + re.escape(variant) + r"\b", description, re.IGNORECASE):
            return SCORE_SLUG_DESC, variant

    # Check aliases
    for term in terms:
        if term.lower() in slug_variants:
            continue
        if re.search(r"\b" + re.escape(term) + r"\b", title, re.IGNORECASE):
            return SCORE_ALIAS_TITLE, term
        if re.search(r"\b" + re.escape(term) + r"\b", description, re.IGNORECASE):
            return SCORE_ALIAS_DESC, term

    return 0, ""


def _score_depth(video: dict) -> int:
    """Duration-based depth score."""
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
    """Authority score based on practitioner source_tier."""
    # Primary: discovered_via practitioner_id
    discovered = video.get("discovered_via", {})
    pid = discovered.get("practitioner_id", "")
    if pid and pid in tier_map:
        tier = tier_map[pid]
        return TIER_SCORES.get(tier, 0)

    # Fallback: channel_id -> registry mapping
    channel_id = video.get("channel_id", "")
    if channel_id and channel_id in channel_map:
        pid = channel_map[channel_id]
        tier = tier_map.get(pid, "")
        return TIER_SCORES.get(tier, 0)

    return 0


def _score_recency(video: dict) -> int:
    """Recency score based on published_at age."""
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
    """Citation bonus if description contains PMID or DOI."""
    desc = video.get("description", "")
    if PMID_RE.search(desc) or DOI_RE.search(desc):
        return SCORE_CITATION
    return 0


def _score_frequency(video: dict, terms: list[str]) -> int:
    """Frequency bonus based on total term occurrences in title + description."""
    text = f"{video.get('title', '')} {video.get('description', '')}"
    count = 0
    for term in terms:
        count += len(re.findall(r"\b" + re.escape(term) + r"\b", text, re.IGNORECASE))
    if count <= 1:
        return SCORE_FREQ_SINGLE
    if count <= 5:
        return SCORE_FREQ_LOW
    if count <= 15:
        return SCORE_FREQ_MED
    return SCORE_FREQ_HIGH


def _apply_channel_diversity(videos: list[dict], cap: int, max_ratio: float = CHANNEL_DIVERSITY_MAX_RATIO) -> list[dict]:
    """Post-sort filter: ensure no single channel exceeds max_ratio of the cap."""
    max_per_channel = max(1, int(cap * max_ratio))
    selected = []
    channel_counts: dict[str, int] = {}
    for v in videos:
        channel = v.get("channel", "unknown")
        if channel_counts.get(channel, 0) >= max_per_channel:
            continue
        selected.append(v)
        channel_counts[channel] = channel_counts.get(channel, 0) + 1
        if len(selected) >= cap:
            break
    return selected


def rank_videos_for_marker(
    marker_slug: str,
    terms: list[str],
    videos: list[dict],
    registry: dict,
    cap: int = DEFAULT_VIDEO_CAP,
) -> list[dict]:
    """Two-phase post-processing: collect matches, then score, rank, cap, and diversity-filter."""
    channel_map = _build_channel_practitioner_map(registry)
    tier_map = _practitioner_tier_map(registry)

    # Phase 1: collect all matches
    matched = []
    term_patterns = [re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE) for term in terms]
    for video in videos:
        text = f"{video.get('title', '')} {video.get('description', '')}"
        if not any(pat.search(text) for pat in term_patterns):
            continue

        base_score, match_term = _score_match_base(video, marker_slug, terms)
        if base_score == 0:
            continue

        title_bonus = SCORE_TITLE_BONUS if video.get("title") and any(
            re.search(r"\b" + re.escape(t) + r"\b", video["title"], re.IGNORECASE) for t in terms
        ) else 0

        depth = _score_depth(video)
        authority = _score_authority(video, channel_map, tier_map)
        recency = _score_recency(video)
        citation = _score_citation(video)
        frequency = _score_frequency(video, terms)

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
            "published_at": video.get("published_at", "")[:10] if video.get("published_at") else "",
            "duration_seconds": video.get("duration_seconds") or 0,
            "score": score,
            "match_term": match_term,
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

    # Phase 2: sort by score descending, then apply diversity filter
    matched.sort(key=lambda v: v["score"], reverse=True)
    selected = _apply_channel_diversity(matched, cap)

    return selected


def get_marker_terms(marker_slug: str, glossary: dict) -> list[str]:
    entries = glossary.get("entries", [])
    terms = set()
    for entry in entries:
        if entry.get("marker") == marker_slug:
            terms.add(entry.get("term", "").lower())
    terms.add(marker_slug.lower())
    terms.add(marker_slug.lower().replace("-", " "))
    return sorted(t for t in terms if t)


# ── Brief assembly ──────────────────────────────────────────────────────────

def build_pointer_brief_identity(marker_slug: str, wave: str, sm_data: dict) -> dict:
    brief = {
        "marker_slug": sm_data.get("marker_slug") or marker_slug,
        "marker_name": sm_data.get("marker_name") or marker_slug,
        "schema_version": "hermes-brief-1",
        "sm_reference": {
            "wave": wave,
            "marker_slug": marker_slug,
            "visibility": "council_only",
        },
    }
    if sm_data.get("unit") is not None:
        brief["unit"] = sm_data.get("unit")
    for field in ("direction", "risk_direction"):
        value = sm_data.get(field)
        if isinstance(value, str) and value:
            brief[field] = value
    return brief


def build_brief(marker_slug: str, wave: str, sm_data: dict, practitioners: list[dict],
                ranked_videos: list[dict], glossary: dict) -> dict:
    brief = build_pointer_brief_identity(marker_slug, wave, sm_data)

    known = sm_data.get("known_research_context", {})
    pmids = [str(p) for p in known.get("pmids", []) if p]
    dois = [str(d) for d in known.get("dois", []) if d]
    source_urls = []
    for pmcid in known.get("pmcids", []):
        if pmcid:
            pmcid_text = str(pmcid)
            if not pmcid_text.upper().startswith("PMC"):
                pmcid_text = f"PMC{pmcid_text}"
            source_urls.append(f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid_text}/")

    marker_name = sm_data.get("marker_name", marker_slug)
    search_queries = [
        f"{marker_name} practitioner optimal range",
        f"{marker_name} metabolic optimization",
    ]

    video_ids = [v["video_id"] for v in ranked_videos]
    brief["recommended_youtube_video_ids"] = video_ids
    brief["recommended_practitioner_ids"] = sorted({p["id"] for p in practitioners})
    brief["recommended_pubmed_ids"] = sorted(set(pmids))
    brief["recommended_dois"] = sorted(set(dois))
    brief["recommended_source_urls"] = sorted(set(source_urls))
    brief["recommended_search_queries"] = search_queries

    return brief


# ── Main generation ─────────────────────────────────────────────────────────

def generate_briefs_for_wave(wave: str, markers: list[str] | None = None,
                              use_semantic: bool = True,
                              semantic_threshold: float = 0.72,
                              video_cap: int = DEFAULT_VIDEO_CAP) -> dict:
    wave_dir = SM_RANGES_DIR / wave
    if not wave_dir.exists():
        raise FileNotFoundError(f"SM ranges wave not found: {wave_dir}")

    registry = load_json(PRACTITIONER_REGISTRY)
    practitioners = registry.get("practitioners", [])
    glossary = load_json(MARKER_GLOSSARY)
    thesaurus = build_thesaurus()
    descriptors = load_yaml(TOPIC_DESCRIPTORS) if TOPIC_DESCRIPTORS.exists() else {}
    videos = load_youtube_inventory()

    target_markers = markers or [p.stem for p in sorted(wave_dir.glob("*.yaml"))]
    summary = {"wave": wave, "generated": [], "skipped": [], "errors": []}

    # Batch semantic matching for all target markers at once
    semantic_matches: dict[str, list[dict]] = {s: [] for s in target_markers}
    if use_semantic:
        try:
            semantic_matches = find_practitioners_semantic(
                target_markers, practitioners, descriptors, threshold=semantic_threshold
            )
            print(f"  [semantic] computed for {len(target_markers)} markers")
        except Exception as e:
            print(f"  ⚠️  Batch semantic match failed: {e}", file=sys.stderr)

    for marker_slug in target_markers:
        sm_path = wave_dir / f"{marker_slug}.yaml"
        if not sm_path.exists():
            found = False
            for other_wave in SM_RANGES_DIR.glob("wave-*"):
                alt_path = other_wave / f"{marker_slug}.yaml"
                if alt_path.exists():
                    sm_path = alt_path
                    found = True
                    break
            if not found:
                summary["errors"].append(f"{marker_slug}: SM YAML not found in any wave")
                continue

        try:
            sm_data = load_yaml(sm_path)
            terms = get_marker_terms(marker_slug, glossary)
            ranked_videos = rank_videos_for_marker(marker_slug, terms, videos, registry, cap=video_cap)

            # Thesaurus-based matching
            rel_thesaurus = find_practitioners_thesaurus(marker_slug, practitioners, thesaurus)

            # Semantic fallback: only for markers with zero thesaurus matches,
            # and only keep top-ranked semantic matches to avoid noise.
            if len(rel_thesaurus) == 0:
                semantic_for_marker = semantic_matches.get(marker_slug, [])
                # Sort by a rough relevance signal and keep top 10
                # (practitioners from semantic match are already above threshold)
                rel_thesaurus = semantic_for_marker[:10]

            brief = build_brief(marker_slug, sm_path.parent.name, sm_data, rel_thesaurus, ranked_videos, glossary)

            out_path = BRIEFS_DIR / wave / f"{marker_slug}.yaml"
            save_yaml(out_path, brief)
            summary["generated"].append({
                "marker": marker_slug,
                "path": str(out_path.relative_to(PROJECT_ROOT)),
                "practitioners": len(rel_thesaurus),
                "youtube_videos": len(ranked_videos),
                "video_cap": video_cap,
                "top_score": ranked_videos[0]["score"] if ranked_videos else 0,
            })
            print(f"✓ {marker_slug}: {len(rel_thesaurus)} practitioners, {len(ranked_videos)} videos (cap={video_cap})")
        except Exception as e:
            summary["errors"].append(f"{marker_slug}: {e}")
            print(f"✗ {marker_slug}: {e}")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Generate Hermes research briefs from SM ranges")
    parser.add_argument("--wave", default="wave-0", help="Wave directory under input/sm-ranges/")
    parser.add_argument("--markers", nargs="+", help="Limit to specific marker slugs")
    parser.add_argument("--qualification", action="store_true",
                        help="Generate for all 10 qualification markers")
    parser.add_argument("--no-semantic", action="store_true",
                        help="Disable semantic embedding matching (thesaurus only)")
    parser.add_argument("--semantic-threshold", type=float, default=0.72,
                        help="Cosine similarity threshold for semantic matching")
    parser.add_argument("--video-cap", type=int, default=DEFAULT_VIDEO_CAP,
                        help="Maximum YouTube videos per brief (default: 30)")
    args = parser.parse_args()

    markers = args.markers
    if args.qualification:
        markers = QUALIFICATION_MARKERS

    summary = generate_briefs_for_wave(
        args.wave, markers,
        use_semantic=not args.no_semantic,
        semantic_threshold=args.semantic_threshold,
        video_cap=args.video_cap,
    )

    summary_path = BRIEFS_DIR / args.wave / "_generation_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSummary written to: {summary_path}")

    if summary["errors"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
