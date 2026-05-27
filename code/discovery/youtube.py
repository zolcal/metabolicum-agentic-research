"""Stage 1 YouTube inventory, ranking, and transcript cache utilities."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore

from jsonschema import Draft202012Validator

from code.discovery.web import MARKER_TERMS, PROJECT_ROOT, SCHEMA_PATH, normalize_url, slugify

CATEGORIES_PATH = PROJECT_ROOT / "input" / "marker_categories.yaml"
DEFAULT_FIXTURE_DIR = PROJECT_ROOT / "fixtures" / "sources"
DEFAULT_DISCOVERY_DIR = PROJECT_ROOT / "runs" / "youtube-discovery" / "discovery"

YOUTUBE_DISCOVERY_TERMS: dict[str, list[str]] = {
    "apob": ["apo b", "apolipoprotein b"],
    "fasting-insulin": [
        "high insulin",
        "insulin spike",
        "insulin spikes",
        "insulin sensitivity",
        "insulin resistant",
    ],
    "hba1c": ["diabetes", "blood sugar", "blood glucose"],
    "ldl-cholesterol": ["ldl", "ldl-c", "bad cholesterol"],
    "hdl-cholesterol": ["hdl", "hdl-c", "good cholesterol"],
    "tg-hdl-ratio": ["triglycerides", "triglyceride", "hdl ratio"],
    "total-cholesterol": ["cholesterol"],
}


@dataclass(frozen=True)
class YouTubeChannelSeed:
    practitioner_id: str
    canonical_name: str
    source_tier: str
    channel_url: str
    priority: str
    marker_affinity: tuple[str, ...]


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_inventory_sample(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text())
    if data.get("schema_version") != "1":
        raise ValueError(f"{path}: schema_version must be '1'")
    if not isinstance(data.get("videos"), list):
        raise ValueError(f"{path}: videos must be a list")
    return data


def is_youtube_channel_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host not in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
        return False
    parts = [part for part in parsed.path.split("/") if part]
    if not parts:
        return False
    if parts[0].startswith("@"):
        return True
    return len(parts) >= 2 and parts[0] in {"channel", "c", "user"}


def load_youtube_channel_seeds(registry_path: Path) -> list[YouTubeChannelSeed]:
    registry = json.loads(registry_path.read_text())
    seeds: list[YouTubeChannelSeed] = []
    for practitioner in registry.get("practitioners", []):
        affinity = tuple(practitioner.get("marker_affinity", []) or ())
        for surface in practitioner.get("surfaces", []) or []:
            if surface.get("platform") != "youtube":
                continue
            if surface.get("discovery_mode") == "do_not_crawl":
                continue
            if surface.get("priority") == "manual_only":
                continue
            url = surface.get("handle_or_url", "")
            if not is_youtube_channel_url(url):
                continue
            seeds.append(
                YouTubeChannelSeed(
                    practitioner_id=practitioner["id"],
                    canonical_name=practitioner["canonical_name"],
                    source_tier=practitioner.get("source_tier", "D"),
                    channel_url=normalize_url(url),
                    priority=surface.get("priority", "secondary"),
                    marker_affinity=affinity,
                )
            )
    seeds.sort(key=lambda seed: (seed.source_tier, seed.priority, seed.canonical_name))
    return seeds


def load_marker_categories(path: Path = CATEGORIES_PATH) -> dict[str, list[str]]:
    if yaml is None or not path.exists():
        return {}
    data = yaml.safe_load(path.read_text()) or {}
    categories = data.get("categories", {})
    result: dict[str, list[str]] = {}
    for name, category in categories.items():
        result[name] = list(category.get("markers", []))
    return result


def expand_marker_terms(markers: list[str]) -> dict[str, list[str]]:
    terms: dict[str, list[str]] = {}
    category_markers = set(markers)
    for category_markers_list in load_marker_categories().values():
        if category_markers.intersection(category_markers_list):
            category_markers.update(category_markers_list)
    for marker in sorted(category_markers):
        base_terms = MARKER_TERMS.get(marker, [marker.replace("-", " "), marker])
        terms[marker] = list(dict.fromkeys([*base_terms, *YOUTUBE_DISCOVERY_TERMS.get(marker, [])]))
    return terms


def parse_duration_seconds(value: str | int | None) -> int | None:
    if value is None or isinstance(value, int):
        return value
    match = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", value)
    if not match:
        return None
    hours, minutes, seconds = (int(part or 0) for part in match.groups())
    return hours * 3600 + minutes * 60 + seconds


def youtube_video_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def video_id_from_url(url: str) -> str | None:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host.endswith("youtu.be"):
        return parsed.path.strip("/") or None
    if "youtube.com" in host:
        query_id = parse_qs(parsed.query).get("v", [None])[0]
        if query_id:
            return query_id
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) >= 2 and parts[0] in {"shorts", "embed", "live"}:
            return parts[1]
    return None


def term_matches(text: str, term: str) -> bool:
    normalized = term.lower()
    if not normalized:
        return False
    if normalized == "lpa":
        pattern = r"(?<![a-z0-9])lpa(?![a-z0-9])"
    else:
        escaped = re.escape(normalized)
        escaped = escaped.replace(r"\ ", r"[\s\-_/]*")
        escaped = escaped.replace(r"\(", r"\s*\(\s*")
        escaped = escaped.replace(r"\)", r"\s*\)\s*")
        pattern = r"(?<![a-z0-9])" + escaped + r"(?![a-z0-9])"
    return re.search(pattern, text.lower()) is not None


def keyword_score_video(video: dict[str, Any], marker_terms: dict[str, list[str]]) -> tuple[int, list[str]]:
    title = str(video.get("title", ""))
    description = str(video.get("description", ""))
    score = 0
    matched_markers: list[str] = []
    for marker, terms in marker_terms.items():
        marker_score = 0
        for term in terms:
            if term_matches(title, term):
                marker_score += 5
            elif term_matches(description, term):
                marker_score += 2
        if marker_score:
            matched_markers.append(marker)
            score += marker_score
    if not matched_markers:
        return 0, []
    duration = parse_duration_seconds(video.get("duration_seconds"))
    if duration and duration >= 600:
        score += 1
    views = video.get("view_count") or 0
    if isinstance(views, int) and views >= 100000:
        score += 1
    return score, sorted(matched_markers)


def source_id_for_youtube_video(video_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"youtube:{video_id}"))


def build_youtube_fixture(
    *,
    video: dict[str, Any],
    channel: dict[str, Any],
    transcript_text: str,
    transcript_method: str,
    expected_markers: list[str],
) -> dict[str, Any]:
    text = transcript_text.strip()
    digest = hashlib.sha256(text.encode()).hexdigest()
    video_id = video["video_id"]
    speaker_name = channel.get("canonical_name")
    if not speaker_name or speaker_name == "multiple":
        speaker_name = video.get("canonical_name") or video.get("channel_title") or "Unknown YouTube speaker"
    speaker_registry_id = channel.get("practitioner_id") or video.get("practitioner_id")
    return {
        "schema_version": "1",
        "source_id": source_id_for_youtube_video(video_id),
        "source_url": video.get("url") or youtube_video_url(video_id),
        "source_type": "video",
        "platform": "youtube",
        "title": video.get("title") or "Untitled YouTube video",
        "retrieved_at": now_utc(),
        "published_at": video.get("published_at"),
        "source_language": "en",
        "speaker_or_author": speaker_name,
        "speaker_registry_id": speaker_registry_id,
        "license": "youtube_public_caption_fair_use_quote_only",
        "transcript_method": transcript_method,
        "transcript_text": text,
        "transcript_sha256": digest,
        "expected_markers": expected_markers,
        "notes": (
            "Stage 1 YouTube transcript fixture. Transcript text is cached for source-first extraction; "
            "quote publication remains limited by legal review."
        ),
        "synthetic": False,
        "verification_status": "verified_real_source",
    }


def validate_source_fixture(fixture: dict[str, Any]) -> None:
    schema = json.loads(SCHEMA_PATH.read_text())
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(fixture), key=lambda error: list(error.path))
    if errors:
        detail = "; ".join(f"{list(error.path)}: {error.message}" for error in errors)
        raise ValueError(f"fixture schema validation failed: {detail}")
    digest = hashlib.sha256(fixture["transcript_text"].encode()).hexdigest()
    if digest != fixture["transcript_sha256"]:
        raise ValueError("fixture transcript_sha256 mismatch")
    if fixture.get("synthetic") is not False:
        raise ValueError("fixture synthetic must be false")
    if fixture.get("verification_status") != "verified_real_source":
        raise ValueError("fixture verification_status must be verified_real_source")


def select_transcript_candidates(
    ranked_videos: list[dict[str, Any]], *, max_transcripts: int, min_keyword_score: int
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for video in ranked_videos:
        if len(selected) >= max_transcripts:
            break
        if int(video.get("keyword_score", 0)) < min_keyword_score:
            continue
        selected.append(video)
    return selected


def write_transcript_fixtures(
    *,
    channel: dict[str, Any],
    ranked_videos: list[dict[str, Any]],
    transcript_by_video_id: dict[str, str],
    output_dir: Path,
    max_transcripts: int,
    min_keyword_score: int,
    transcript_method: str,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for video in select_transcript_candidates(
        ranked_videos, max_transcripts=max_transcripts, min_keyword_score=min_keyword_score
    ):
        video_id = video["video_id"]
        transcript = transcript_by_video_id.get(video_id)
        if not transcript:
            continue
        fixture = build_youtube_fixture(
            video=video,
            channel=channel,
            transcript_text=transcript,
            transcript_method=transcript_method,
            expected_markers=video.get("matched_markers", []),
        )
        validate_source_fixture(fixture)
        marker_slug = slugify("-".join(fixture.get("expected_markers") or ["youtube"]), 32)
        filename = f"{marker_slug}-youtube-{slugify(video_id, 24)}.json"
        path = output_dir / filename
        path.write_text(json.dumps(fixture, indent=2, ensure_ascii=False) + "\n")
        paths.append(path)
    return paths


def jsonl_write(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows))


def write_transcript_ledger(path: Path, fixture_paths: list[Path]) -> None:
    rows: list[dict[str, Any]] = []
    for fixture_path in fixture_paths:
        fixture = json.loads(fixture_path.read_text())
        rows.append(
            {
                "schema_version": "1",
                "source_id": fixture["source_id"],
                "source_url": fixture["source_url"],
                "source_type": fixture["source_type"],
                "platform": fixture.get("platform"),
                "speaker_registry_id": fixture.get("speaker_registry_id"),
                "title": fixture.get("title"),
                "transcript_method": fixture.get("transcript_method"),
                "transcript_sha256": fixture.get("transcript_sha256"),
                "expected_markers": fixture.get("expected_markers", []),
                "fixture_path": str(fixture_path),
            }
        )
    jsonl_write(path, rows)


def write_inventory_artifacts(channel: dict[str, Any], ranked_videos: list[dict[str, Any]], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    inventory_rows: list[dict[str, Any]] = []
    ranked_rows: list[dict[str, Any]] = []
    for rank, video in enumerate(ranked_videos, start=1):
        channel_name = channel.get("canonical_name")
        if not channel_name or channel_name == "multiple":
            channel_name = video.get("canonical_name")
        channel_url = channel.get("channel_url")
        if not channel_url or channel_url == "multiple":
            channel_url = video.get("channel_url")
        base = {
            "schema_version": "1",
            "practitioner_id": channel.get("practitioner_id") or video.get("practitioner_id"),
            "canonical_name": channel_name,
            "channel_url": channel_url,
            "channel_id": video.get("channel_id") or channel.get("channel_id"),
            "video_id": video["video_id"],
            "source_url": video.get("url") or youtube_video_url(video["video_id"]),
            "title": video.get("title", ""),
            "description": video.get("description", ""),
            "published_at": video.get("published_at"),
            "duration_seconds": parse_duration_seconds(video.get("duration_seconds")),
            "view_count": video.get("view_count"),
        }
        inventory_rows.append(base)
        ranked_row = dict(base)
        ranked_row.update(
            {
                "rank": rank,
                "keyword_score": video.get("keyword_score", 0),
                "matched_markers": video.get("matched_markers", []),
                "rank_reason": video.get("rank_reason", "no_marker_keyword_match"),
            }
        )
        ranked_rows.append(ranked_row)
    jsonl_write(output_dir / "youtube_inventory.jsonl", inventory_rows)
    jsonl_write(output_dir / "youtube_ranked.jsonl", ranked_rows)


def rank_videos(videos: list[dict[str, Any]], markers: list[str]) -> list[dict[str, Any]]:
    marker_terms = expand_marker_terms(markers)
    ranked: list[dict[str, Any]] = []
    for video in videos:
        score, matched_markers = keyword_score_video(video, marker_terms)
        row = dict(video)
        row["keyword_score"] = score
        row["matched_markers"] = matched_markers
        row["rank_reason"] = "marker_category_keyword_match" if score else "no_marker_keyword_match"
        ranked.append(row)
    ranked.sort(
        key=lambda row: (row["keyword_score"], row.get("view_count") or 0, row.get("published_at") or ""),
        reverse=True,
    )
    return ranked


class YouTubeMetadataProvider:
    def list_channel_videos(self, seed: YouTubeChannelSeed, *, max_results: int) -> list[dict[str, Any]]:
        raise NotImplementedError


class YouTubeDataApiProvider(YouTubeMetadataProvider):
    def __init__(self, api_key: str, session: Any | None = None):
        import requests

        self.api_key = api_key
        self.session = session or requests.Session()

    def _get(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        merged = dict(params)
        merged["key"] = self.api_key
        response = self.session.get(url, params=merged, timeout=25)
        try:
            response.raise_for_status()
        except Exception as exc:
            message = str(exc)
            try:
                payload = response.json()
                message = payload.get("error", {}).get("message", message)
            except Exception:
                pass
            raise RuntimeError(
                json.dumps(
                    {
                        "youtube_api_error": message,
                        "status_code": getattr(response, "status_code", None),
                        "endpoint": url,
                    },
                    sort_keys=True,
                )
            ) from exc
        return response.json()

    def resolve_channel_id(self, seed: YouTubeChannelSeed) -> str:
        parsed = urlparse(seed.channel_url)
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) >= 2 and parts[0] == "channel":
            return parts[1]
        if parts and parts[0].startswith("@"):
            data = self._get(
                "https://www.googleapis.com/youtube/v3/channels",
                {"part": "id", "forHandle": parts[0]},
            )
            return self._extract_channel_id(data, seed.channel_url)
        if len(parts) >= 2 and parts[0] == "user":
            data = self._get(
                "https://www.googleapis.com/youtube/v3/channels",
                {"part": "id", "forUsername": parts[1]},
            )
            return self._extract_channel_id(data, seed.channel_url)
        if len(parts) >= 2 and parts[0] == "c":
            data = self._get(
                "https://www.googleapis.com/youtube/v3/search",
                {
                    "part": "snippet",
                    "type": "channel",
                    "q": parts[1],
                    "maxResults": 1,
                },
            )
            return self._extract_channel_id(data, seed.channel_url)
        raise ValueError(f"unsupported youtube channel URL: {seed.channel_url}")

    @staticmethod
    def _extract_channel_id(data: dict[str, Any], channel_url: str) -> str:
        items = data.get("items", [])
        if not items:
            raise ValueError(f"channel URL not resolved: {channel_url}")
        first = items[0]
        channel_id = first.get("id")
        if isinstance(channel_id, dict):
            channel_id = channel_id.get("channelId")
        if not channel_id:
            channel_id = first.get("snippet", {}).get("channelId")
        if not channel_id:
            raise ValueError(f"channel URL not resolved: {channel_url}")
        return str(channel_id)

    def list_channel_videos(self, seed: YouTubeChannelSeed, *, max_results: int) -> list[dict[str, Any]]:
        channel_id = self.resolve_channel_id(seed)
        search = self._get(
            "https://www.googleapis.com/youtube/v3/search",
            {
                "part": "snippet",
                "channelId": channel_id,
                "type": "video",
                "order": "date",
                "maxResults": min(max_results, 50),
            },
        )
        video_ids = [item["id"]["videoId"] for item in search.get("items", [])]
        if not video_ids:
            return []
        details = self._get(
            "https://www.googleapis.com/youtube/v3/videos",
            {
                "part": "snippet,contentDetails,statistics",
                "id": ",".join(video_ids),
                "maxResults": len(video_ids),
            },
        )
        rows: list[dict[str, Any]] = []
        for item in details.get("items", []):
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            view_count = stats.get("viewCount")
            rows.append(
                {
                    "video_id": item["id"],
                    "url": youtube_video_url(item["id"]),
                    "title": snippet.get("title", ""),
                    "description": snippet.get("description", ""),
                    "published_at": snippet.get("publishedAt"),
                    "duration_seconds": parse_duration_seconds(item.get("contentDetails", {}).get("duration")),
                    "view_count": int(view_count) if str(view_count or "").isdigit() else None,
                    "channel_id": channel_id,
                    "channel_url": seed.channel_url,
                    "channel_title": snippet.get("channelTitle"),
                    "practitioner_id": seed.practitioner_id,
                    "canonical_name": seed.canonical_name,
                }
            )
        return rows


class YouTubeTranscriptProvider:
    transcript_method = "unconfigured_transcript_provider"

    def get_transcript(self, video_id: str) -> str | None:
        raise NotImplementedError


class JsonTranscriptProvider(YouTubeTranscriptProvider):
    transcript_method = "operator_supplied_json_transcript"

    def __init__(self, path: Path):
        self.data = json.loads(path.read_text())

    def get_transcript(self, video_id: str) -> str | None:
        value = self.data.get(video_id)
        if isinstance(value, str):
            return value
        if isinstance(value, dict) and isinstance(value.get("transcript_text"), str):
            return value["transcript_text"]
        return None


class YouTubeTranscriptApiProvider(YouTubeTranscriptProvider):
    transcript_method = "third_party_caption_api"

    def __init__(self, languages: list[str] | None = None):
        from youtube_transcript_api import YouTubeTranscriptApi

        self.api = YouTubeTranscriptApi()
        self.languages = languages or ["en"]

    def get_transcript(self, video_id: str) -> str | None:
        try:
            transcript = self.api.fetch(video_id, languages=self.languages)
        except Exception as exc:  # pragma: no cover - depends on live YouTube caption state
            print(json.dumps({"video_id": video_id, "transcript_error": str(exc)}, sort_keys=True))
            return None
        return " ".join(segment.text for segment in transcript if segment.text).strip() or None


def main(argv: list[str] | None = None) -> int:
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Inventory and rank registry YouTube channels for Stage 1 discovery.")
    parser.add_argument("--inventory-sample", type=Path, help="Offline inventory JSON sample for acceptance and dry runs")
    parser.add_argument("--registry", type=Path, default=PROJECT_ROOT / "input" / "practitioner_registry.json")
    parser.add_argument("--markers", nargs="+", required=True, help="Marker ids used for ranking")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_DISCOVERY_DIR,
        help="Directory for youtube_inventory.jsonl and youtube_ranked.jsonl",
    )
    parser.add_argument("--rank-only", action="store_true", help="Rank metadata without transcript fetching")
    parser.add_argument("--live", action="store_true", help="Use YouTube Data API metadata; requires YOUTUBE_API_KEY")
    parser.add_argument("--max-videos-per-channel", type=int, default=50)
    parser.add_argument("--transcript-json", type=Path, help="JSON mapping video_id to transcript text")
    parser.add_argument(
        "--transcript-provider",
        choices=["operator-json", "youtube-transcript-api"],
        help="Transcript provider to use when filling fixtures",
    )
    parser.add_argument("--transcript-languages", nargs="+", default=["en"], help="Caption languages to request")
    parser.add_argument("--max-transcripts", type=int, default=25)
    parser.add_argument("--min-keyword-score", type=int, default=5)
    parser.add_argument("--fixture-dir", type=Path, default=DEFAULT_FIXTURE_DIR)
    args = parser.parse_args(argv)

    def write_optional_transcripts(channel: dict[str, Any], ranked: list[dict[str, Any]]) -> int:
        if args.rank_only:
            return 0
        if args.transcript_json:
            provider: YouTubeTranscriptProvider = JsonTranscriptProvider(args.transcript_json)
        elif args.transcript_provider == "youtube-transcript-api":
            provider = YouTubeTranscriptApiProvider(languages=args.transcript_languages)
        else:
            return 0
        selected = select_transcript_candidates(
            ranked, max_transcripts=args.max_transcripts, min_keyword_score=args.min_keyword_score
        )
        transcript_by_video_id = {
            video["video_id"]: transcript
            for video in selected
            if (transcript := provider.get_transcript(video["video_id"]))
        }
        paths = write_transcript_fixtures(
            channel=channel,
            ranked_videos=selected,
            transcript_by_video_id=transcript_by_video_id,
            output_dir=args.fixture_dir,
            max_transcripts=args.max_transcripts,
            min_keyword_score=args.min_keyword_score,
            transcript_method=provider.transcript_method,
        )
        write_transcript_ledger(args.output_dir / "youtube_transcripts.jsonl", paths)
        return len(paths)

    if args.live:
        api_key = os.environ.get("YOUTUBE_API_KEY")
        if not api_key:
            raise SystemExit("YOUTUBE_API_KEY is required for --live")
        provider = YouTubeDataApiProvider(api_key)
        seeds = load_youtube_channel_seeds(args.registry)
        videos: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        for seed in seeds:
            try:
                videos.extend(provider.list_channel_videos(seed, max_results=args.max_videos_per_channel))
            except Exception as exc:
                errors.append(
                    {
                        "schema_version": "1",
                        "practitioner_id": seed.practitioner_id,
                        "canonical_name": seed.canonical_name,
                        "channel_url": seed.channel_url,
                        "error": str(exc),
                    }
                )
        if errors:
            jsonl_write(args.output_dir / "youtube_errors.jsonl", errors)
        ranked = rank_videos(videos, markers=args.markers)
        channel = {"practitioner_id": None, "canonical_name": "multiple", "channel_url": "multiple", "channel_id": None}
        write_inventory_artifacts(channel, ranked, args.output_dir)
        transcript_count = write_optional_transcripts(channel, ranked)
        print(
            json.dumps(
                {
                    "channels": len(seeds),
                    "ranked_videos": len(ranked),
                    "output_dir": str(args.output_dir),
                    "transcript_fixtures": transcript_count,
                    "channel_errors": len(errors),
                },
                sort_keys=True,
            )
        )
        return 0

    if args.inventory_sample is None:
        raise SystemExit("--inventory-sample is required unless --live is set")
    sample = load_inventory_sample(args.inventory_sample)
    ranked = rank_videos(sample["videos"], markers=args.markers)
    write_inventory_artifacts(sample["channel"], ranked, args.output_dir)
    transcript_count = write_optional_transcripts(sample["channel"], ranked)
    print(
        json.dumps(
            {
                "ranked_videos": len(ranked),
                "output_dir": str(args.output_dir),
                "transcript_fixtures": transcript_count,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

