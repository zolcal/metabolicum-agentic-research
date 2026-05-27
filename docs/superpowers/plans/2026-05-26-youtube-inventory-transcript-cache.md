# YouTube Inventory and Transcript Cache Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a conservative YouTube Stage 1 pipeline that inventories every registry YouTube surface, ranks videos by marker/category relevance, and caches transcripts for high-value videos in the existing source fixture format.

**Architecture:** Keep Stage 2 unchanged: it consumes cached transcript fixtures only. Add a Stage 1 YouTube module that reads `input/practitioner_registry.json`, expands YouTube surfaces into channel/video inventory, ranks videos using marker aliases and `input/marker_categories.yaml`, and writes only selected transcripts as `source_type: video` fixtures. Bulk inventory is default; transcript acquisition is targeted and budgeted.

**Tech Stack:** Python 3.11, `requests`, `pyyaml`, `jsonschema`, existing `code.discovery.web` marker-term utilities, YouTube Data API or `youtube-mcp` for metadata, `youtube-mcp transcripts_getTranscript` or approved caption provider for transcripts, existing `code/schemas/source_fixture.schema.json` for cache validation.

---

## Decisions

- Inventory every registry YouTube channel before fetching transcripts.
  Rationale: metadata is cheap, improves ranking immediately, and avoids processing 1,000+ low-value videos per large channel.
  Status: decided.

- Transcript only ranked subsets by default.
  Rationale: transcript acquisition has quota, ToS, storage, and processing implications. Ranked subsets provide the same discovery benefit with lower waste.
  Status: decided.

- Cache YouTube transcripts as normal Stage 2 source fixtures.
  Rationale: Stage 2 already enforces source-first extraction from immutable transcripts. YouTube should produce the same contract as web and podcast discovery.
  Status: decided.

- Do not download audio or video files.
  Rationale: the legal docs already classify authenticated downloads and access-control bypass as avoided. This plan uses metadata and caption/transcript surfaces only.
  Status: decided.

- Anthony Chaffee is the bootstrap channel.
  Rationale: his channel has large volume and clear MO relevance; if the pipeline works for Chaffee, it will work for smaller YouTube-first practitioners.
  Status: decided.

## Files

Create:
- `code/discovery/youtube.py` — deterministic YouTube inventory, ranking, transcript cache writer, and CLI.
- `code/acceptance/check_youtube_inventory.py` — local validation for YouTube inventory/ranking/transcript fixture artifacts.
- `fixtures/youtube/anthony-chaffee-sample-inventory.json` — small offline metadata sample for acceptance tests.
- `docs/agentic-workflow/youtube-transcript-discovery.md` — operator-facing contract for YouTube inventory, ranking, transcript methods, and legal posture.

Modify:
- `config/tools.yaml` — document that `youtube-mcp` supports two distinct Stage 1 modes: metadata inventory and transcript cache fill.
- `docs/agentic-workflow/03-social-agents-spec.md` — align the YouTube section with the inventory-first design.
- `docs/agentic-workflow/07-legal-and-ip-agent.md` — record allowed transcript methods and quote limits for cached YouTube transcripts.
- `docs/agentic-workflow/10-orchestration-and-filesystem.md` — add `runs/<run_id>/discovery/youtube_inventory.jsonl`, `youtube_ranked.jsonl`, and `youtube_transcripts.jsonl` to the Stage 1 layout.

Do not modify:
- Stage 2 prompts for this task.
- Stage 3 council prompts for this task.
- Production database migrations. The first implementation writes filesystem artifacts and source fixtures.

---

### Task 1: Add Offline Acceptance Sample

**Files:**
- Create: `fixtures/youtube/anthony-chaffee-sample-inventory.json`

- [ ] **Step 1: Create the sample inventory file**

Create `fixtures/youtube/anthony-chaffee-sample-inventory.json` with this content:

```json
{
  "schema_version": "1",
  "channel": {
    "practitioner_id": "person:anthony-chaffee",
    "canonical_name": "Anthony Chaffee",
    "channel_url": "https://www.youtube.com/@anthonychaffeemd",
    "channel_handle": "@anthonychaffeemd",
    "channel_id": "UCzoRyR_nlesKZuOlEjWRXQQ"
  },
  "videos": [
    {
      "video_id": "sample_apob_001",
      "url": "https://www.youtube.com/watch?v=sample_apob_001",
      "title": "Carnivore, Cholesterol, ApoB and Heart Disease Risk",
      "description": "Dr Anthony Chaffee discusses LDL, ApoB, triglycerides, HDL and insulin resistance on a carnivore diet.",
      "published_at": "2024-01-10T00:00:00Z",
      "duration_seconds": 4200,
      "view_count": 250000,
      "channel_id": "UCzoRyR_nlesKZuOlEjWRXQQ",
      "channel_title": "Anthony Chaffee MD"
    },
    {
      "video_id": "sample_insulin_001",
      "url": "https://www.youtube.com/watch?v=sample_insulin_001",
      "title": "Insulin Resistance, HbA1c and Reversing Diabetes with a Carnivore Diet",
      "description": "Fasting insulin, A1c, glucose and HOMA-IR are discussed as metabolic health markers.",
      "published_at": "2023-11-02T00:00:00Z",
      "duration_seconds": 3600,
      "view_count": 190000,
      "channel_id": "UCzoRyR_nlesKZuOlEjWRXQQ",
      "channel_title": "Anthony Chaffee MD"
    },
    {
      "video_id": "sample_general_001",
      "url": "https://www.youtube.com/watch?v=sample_general_001",
      "title": "Why Plants Do Not Want To Be Eaten",
      "description": "A general plant-toxin discussion without numeric biomarker targets.",
      "published_at": "2023-05-06T00:00:00Z",
      "duration_seconds": 5400,
      "view_count": 410000,
      "channel_id": "UCzoRyR_nlesKZuOlEjWRXQQ",
      "channel_title": "Anthony Chaffee MD"
    }
  ]
}
```

- [ ] **Step 2: Run JSON validation**

Run:

```bash
python -m json.tool fixtures/youtube/anthony-chaffee-sample-inventory.json >/tmp/youtube-sample.json
```

Expected: exit code `0` and `/tmp/youtube-sample.json` exists.

- [ ] **Step 3: Commit**

```bash
git add fixtures/youtube/anthony-chaffee-sample-inventory.json
git commit -m "test: add youtube inventory sample"
```

---

### Task 2: Implement YouTube Ranking Core

**Files:**
- Create: `code/discovery/youtube.py`
- Create: `code/acceptance/check_youtube_inventory.py`

- [ ] **Step 1: Write the failing acceptance check**

Create `code/acceptance/check_youtube_inventory.py`:

```python
"""Acceptance checks for YouTube inventory and transcript-cache artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from code.discovery.youtube import load_inventory_sample, rank_videos

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "fixtures" / "youtube" / "anthony-chaffee-sample-inventory.json"


def main() -> int:
    sample = load_inventory_sample(SAMPLE)
    ranked = rank_videos(sample["videos"], markers=["apob", "fasting-insulin", "hba1c", "tg-hdl-ratio"])
    ids = [row["video_id"] for row in ranked]
    if ids[:2] != ["sample_insulin_001", "sample_apob_001"]:
        raise SystemExit(f"unexpected ranking order: {ids}")
    if ranked[0]["keyword_score"] <= ranked[2]["keyword_score"]:
        raise SystemExit("marker videos must outrank general videos")
    print(json.dumps({"checked": len(ranked), "top_video_id": ranked[0]["video_id"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run the check and confirm it fails before implementation**

Run:

```bash
python code/acceptance/check_youtube_inventory.py
```

Expected: fails with `ModuleNotFoundError: No module named 'code.discovery.youtube'`.

- [ ] **Step 3: Implement ranking functions**

Create `code/discovery/youtube.py` with these functions:

```python
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


@dataclass(frozen=True)
class YouTubeChannelSeed:
    practitioner_id: str
    canonical_name: str
    source_tier: str
    channel_url: str
    priority: str
    marker_affinity: list[str]


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_inventory_sample(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text())
    if data.get("schema_version") != "1":
        raise ValueError(f"{path}: schema_version must be '1'")
    if not isinstance(data.get("videos"), list):
        raise ValueError(f"{path}: videos must be a list")
    return data


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
        terms[marker] = MARKER_TERMS.get(marker, [marker.replace("-", " "), marker])
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


def keyword_score_video(video: dict[str, Any], marker_terms: dict[str, list[str]]) -> tuple[int, list[str]]:
    title = str(video.get("title", "")).lower()
    description = str(video.get("description", "")).lower()
    haystack = f"{title}\n{description}"
    score = 0
    matched_markers: list[str] = []
    for marker, terms in marker_terms.items():
        marker_score = 0
        for term in terms:
            normalized = term.lower()
            if normalized and normalized in title:
                marker_score += 5
            elif normalized and normalized in haystack:
                marker_score += 2
        if marker_score:
            matched_markers.append(marker)
            score += marker_score
    duration = parse_duration_seconds(video.get("duration_seconds"))
    if duration and duration >= 600:
        score += 1
    views = video.get("view_count") or 0
    if isinstance(views, int) and views >= 100000:
        score += 1
    return score, sorted(matched_markers)


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
    ranked.sort(key=lambda row: (row["keyword_score"], row.get("view_count") or 0, row.get("published_at") or ""), reverse=True)
    return ranked
```

- [ ] **Step 4: Run the acceptance check**

Run:

```bash
python code/acceptance/check_youtube_inventory.py
```

Expected output contains:

```text
{"checked": 3, "top_video_id": "sample_insulin_001"}
```

- [ ] **Step 5: Commit**

```bash
git add code/discovery/youtube.py code/acceptance/check_youtube_inventory.py
git commit -m "feat: rank youtube inventory by marker relevance"
```

---

### Task 3: Load YouTube Channel Seeds from the Registry

**Files:**
- Modify: `code/discovery/youtube.py`
- Modify: `code/acceptance/check_youtube_inventory.py`

- [ ] **Step 1: Add seed assertions**

Add this block to `main()` in `code/acceptance/check_youtube_inventory.py` before the final print:

```python
    from code.discovery.youtube import load_youtube_channel_seeds

    seeds = load_youtube_channel_seeds(ROOT / "input" / "practitioner_registry.json")
    chaffee = [seed for seed in seeds if seed.practitioner_id == "person:anthony-chaffee"]
    if not chaffee:
        raise SystemExit("person:anthony-chaffee youtube seed missing")
    if chaffee[0].channel_url != "https://www.youtube.com/@anthonychaffeemd":
        raise SystemExit(f"unexpected Chaffee channel URL: {chaffee[0].channel_url}")
```

- [ ] **Step 2: Run the check and confirm it fails before implementation**

Run:

```bash
python code/acceptance/check_youtube_inventory.py
```

Expected: fails with `ImportError` for `load_youtube_channel_seeds`.

- [ ] **Step 3: Implement `load_youtube_channel_seeds`**

Add this function to `code/discovery/youtube.py`:

```python
def load_youtube_channel_seeds(registry_path: Path) -> list[YouTubeChannelSeed]:
    registry = json.loads(registry_path.read_text())
    seeds: list[YouTubeChannelSeed] = []
    for practitioner in registry.get("practitioners", []):
        affinity = practitioner.get("marker_affinity", []) or []
        for surface in practitioner.get("surfaces", []) or []:
            if surface.get("platform") != "youtube":
                continue
            if surface.get("discovery_mode") == "do_not_crawl":
                continue
            if surface.get("priority") == "manual_only":
                continue
            url = surface.get("handle_or_url", "")
            if not url.startswith(("https://www.youtube.com/", "https://youtube.com/", "https://youtu.be/")):
                continue
            seeds.append(YouTubeChannelSeed(
                practitioner_id=practitioner["id"],
                canonical_name=practitioner["canonical_name"],
                source_tier=practitioner.get("source_tier", "D"),
                channel_url=normalize_url(url),
                priority=surface.get("priority", "secondary"),
                marker_affinity=affinity,
            ))
    seeds.sort(key=lambda seed: (seed.source_tier, seed.priority, seed.canonical_name))
    return seeds
```

- [ ] **Step 4: Run acceptance check**

Run:

```bash
python code/acceptance/check_youtube_inventory.py
```

Expected: same JSON output as Task 2 and no seed failure.

- [ ] **Step 5: Commit**

```bash
git add code/discovery/youtube.py code/acceptance/check_youtube_inventory.py
git commit -m "feat: load youtube seeds from practitioner registry"
```

---

### Task 4: Write Inventory and Ranked Artifacts

**Files:**
- Modify: `code/discovery/youtube.py`
- Modify: `code/acceptance/check_youtube_inventory.py`

- [ ] **Step 1: Add artifact writer assertions**

Add this block to `main()` in `code/acceptance/check_youtube_inventory.py`:

```python
    from code.discovery.youtube import write_inventory_artifacts

    with TemporaryDirectory() as tmp:
        out_dir = Path(tmp)
        write_inventory_artifacts(sample["channel"], ranked, out_dir)
        inventory_path = out_dir / "youtube_inventory.jsonl"
        ranked_path = out_dir / "youtube_ranked.jsonl"
        if not inventory_path.exists() or not ranked_path.exists():
            raise SystemExit("youtube inventory artifacts were not written")
        ranked_rows = [json.loads(line) for line in ranked_path.read_text().splitlines() if line.strip()]
        if ranked_rows[0]["video_id"] != "sample_insulin_001":
            raise SystemExit("ranked artifact did not preserve ranking order")
```

- [ ] **Step 2: Run the check and confirm it fails before implementation**

Run:

```bash
python code/acceptance/check_youtube_inventory.py
```

Expected: fails with `ImportError` for `write_inventory_artifacts`.

- [ ] **Step 3: Implement JSONL artifact writing**

Add these functions to `code/discovery/youtube.py`:

```python
def jsonl_write(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows))


def write_inventory_artifacts(channel: dict[str, Any], ranked_videos: list[dict[str, Any]], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    inventory_rows: list[dict[str, Any]] = []
    ranked_rows: list[dict[str, Any]] = []
    for rank, video in enumerate(ranked_videos, start=1):
        base = {
            "schema_version": "1",
            "practitioner_id": channel.get("practitioner_id") or video.get("practitioner_id"),
            "canonical_name": channel.get("canonical_name") or video.get("canonical_name"),
            "channel_url": channel.get("channel_url"),
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
        ranked_row.update({
            "rank": rank,
            "keyword_score": video.get("keyword_score", 0),
            "matched_markers": video.get("matched_markers", []),
            "rank_reason": video.get("rank_reason", "no_marker_keyword_match"),
        })
        ranked_rows.append(ranked_row)
    jsonl_write(output_dir / "youtube_inventory.jsonl", inventory_rows)
    jsonl_write(output_dir / "youtube_ranked.jsonl", ranked_rows)
```

- [ ] **Step 4: Run acceptance check**

Run:

```bash
python code/acceptance/check_youtube_inventory.py
```

Expected: output contains `"top_video_id": "sample_insulin_001"`.

- [ ] **Step 5: Commit**

```bash
git add code/discovery/youtube.py code/acceptance/check_youtube_inventory.py
git commit -m "feat: write youtube inventory artifacts"
```

---

### Task 5: Build YouTube Source Fixtures from Transcripts

**Files:**
- Modify: `code/discovery/youtube.py`
- Modify: `code/acceptance/check_youtube_inventory.py`

- [ ] **Step 1: Add transcript fixture assertions**

Add this block to `main()` in `code/acceptance/check_youtube_inventory.py`:

```python
    from code.discovery.youtube import build_youtube_fixture, validate_source_fixture

    transcript = "Dr Anthony Chaffee says fasting insulin and HbA1c improve when carbohydrate exposure falls. A fasting insulin above 10 mIU/L suggests insulin resistance."
    fixture = build_youtube_fixture(
        video=ranked[0],
        channel=sample["channel"],
        transcript_text=transcript,
        transcript_method="youtube_mcp_transcript",
        expected_markers=["fasting-insulin", "hba1c"],
    )
    validate_source_fixture(fixture)
    if fixture["source_type"] != "video":
        raise SystemExit("YouTube fixture source_type must be video")
    if fixture["speaker_registry_id"] != "person:anthony-chaffee":
        raise SystemExit("YouTube fixture must preserve practitioner id")
```

- [ ] **Step 2: Run the check and confirm it fails before implementation**

Run:

```bash
python code/acceptance/check_youtube_inventory.py
```

Expected: fails with `ImportError` for `build_youtube_fixture` or `validate_source_fixture`.

- [ ] **Step 3: Implement fixture builder**

Add these functions to `code/discovery/youtube.py`:

```python
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
        "speaker_or_author": channel.get("canonical_name") or video.get("channel_title") or "Unknown YouTube speaker",
        "speaker_registry_id": channel.get("practitioner_id"),
        "license": "youtube_public_caption_fair_use_quote_only",
        "transcript_method": transcript_method,
        "transcript_text": text,
        "transcript_sha256": digest,
        "expected_markers": expected_markers,
        "notes": "Stage 1 YouTube transcript fixture. Transcript text is cached for source-first extraction; quote publication remains limited by legal review.",
        "synthetic": False,
        "verification_status": "verified_real_source",
    }


def validate_source_fixture(fixture: dict[str, Any]) -> None:
    schema = json.loads(SCHEMA_PATH.read_text())
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(fixture), key=lambda e: list(e.path))
    if errors:
        detail = "; ".join(f"{list(e.path)}: {e.message}" for e in errors)
        raise ValueError(f"fixture schema validation failed: {detail}")
    digest = hashlib.sha256(fixture["transcript_text"].encode()).hexdigest()
    if digest != fixture["transcript_sha256"]:
        raise ValueError("fixture transcript_sha256 mismatch")
```

- [ ] **Step 4: Run acceptance checks**

Run:

```bash
python code/acceptance/check_youtube_inventory.py
python code/acceptance/check_fixture_contract.py
```

Expected: first command prints the YouTube acceptance JSON; second command prints a line beginning with `checked ` and ending with ` source fixture(s)`.

- [ ] **Step 5: Commit**

```bash
git add code/discovery/youtube.py code/acceptance/check_youtube_inventory.py
git commit -m "feat: build youtube transcript fixtures"
```

---

### Task 6: Add Budgeted Transcript Fixture Writer

**Files:**
- Modify: `code/discovery/youtube.py`
- Modify: `code/acceptance/check_youtube_inventory.py`

- [ ] **Step 1: Add budgeted writer assertion**

Add this block to `main()` in `code/acceptance/check_youtube_inventory.py`:

```python
    from code.discovery.youtube import write_transcript_fixtures

    transcript_by_video_id = {
        "sample_insulin_001": "Fasting insulin above 10 mIU/L suggests insulin resistance. HbA1c improves when glucose exposure falls.",
        "sample_apob_001": "ApoB, LDL cholesterol and triglycerides can rise on low carbohydrate diets, while HDL often rises too.",
    }
    with TemporaryDirectory() as tmp:
        paths = write_transcript_fixtures(
            channel=sample["channel"],
            ranked_videos=ranked,
            transcript_by_video_id=transcript_by_video_id,
            output_dir=Path(tmp),
            max_transcripts=2,
            min_keyword_score=1,
            transcript_method="youtube_mcp_transcript",
        )
        if len(paths) != 2:
            raise SystemExit(f"expected 2 transcript fixtures, got {len(paths)}")
```

- [ ] **Step 2: Run the check and confirm it fails before implementation**

Run:

```bash
python code/acceptance/check_youtube_inventory.py
```

Expected: fails with `ImportError` for `write_transcript_fixtures`.

- [ ] **Step 3: Implement `write_transcript_fixtures`**

Add this function to `code/discovery/youtube.py`:

```python
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
    for video in ranked_videos:
        if len(paths) >= max_transcripts:
            break
        if int(video.get("keyword_score", 0)) < min_keyword_score:
            continue
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
        filename = f"{slugify('-'.join(fixture.get('expected_markers') or ['youtube']), 32)}-youtube-{slugify(video_id, 24)}.json"
        path = output_dir / filename
        path.write_text(json.dumps(fixture, indent=2, ensure_ascii=False) + "\n")
        paths.append(path)
    return paths
```

- [ ] **Step 4: Run checks**

Run:

```bash
python code/acceptance/check_youtube_inventory.py
python code/acceptance/check_fixture_contract.py
```

Expected: both pass.

- [ ] **Step 5: Commit**

```bash
git add code/discovery/youtube.py code/acceptance/check_youtube_inventory.py
git commit -m "feat: write budgeted youtube transcript fixtures"
```

---

### Task 7: Add CLI for Offline and Live Metadata Inventory

**Files:**
- Modify: `code/discovery/youtube.py`
- Modify: `code/acceptance/check_youtube_inventory.py`

- [ ] **Step 1: Add CLI smoke assertion**

Add this block to `main()` in `code/acceptance/check_youtube_inventory.py`:

```python
    from code.discovery.youtube import main as youtube_main

    with TemporaryDirectory() as tmp:
        exit_code = youtube_main([
            "--inventory-sample", str(SAMPLE),
            "--markers", "apob", "fasting-insulin", "hba1c", "tg-hdl-ratio",
            "--output-dir", tmp,
            "--rank-only",
        ])
        if exit_code != 0:
            raise SystemExit(f"youtube CLI returned {exit_code}")
        if not (Path(tmp) / "youtube_ranked.jsonl").exists():
            raise SystemExit("youtube CLI did not write ranked artifact")
```

- [ ] **Step 2: Implement provider interface and CLI**

Add this code to `code/discovery/youtube.py`:

```python
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
        response.raise_for_status()
        return response.json()

    def resolve_channel_id(self, seed: YouTubeChannelSeed) -> str:
        parsed = urlparse(seed.channel_url)
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) >= 2 and parts[0] == "channel":
            return parts[1]
        if parts and parts[0].startswith("@"):
            data = self._get("https://www.googleapis.com/youtube/v3/search", {
                "part": "snippet",
                "type": "channel",
                "q": parts[0],
                "maxResults": 1,
            })
            items = data.get("items", [])
            if not items:
                raise ValueError(f"channel handle not resolved: {seed.channel_url}")
            return items[0]["snippet"]["channelId"]
        raise ValueError(f"unsupported youtube channel URL: {seed.channel_url}")

    def list_channel_videos(self, seed: YouTubeChannelSeed, *, max_results: int) -> list[dict[str, Any]]:
        channel_id = self.resolve_channel_id(seed)
        search = self._get("https://www.googleapis.com/youtube/v3/search", {
            "part": "snippet",
            "channelId": channel_id,
            "type": "video",
            "order": "date",
            "maxResults": min(max_results, 50),
        })
        video_ids = [item["id"]["videoId"] for item in search.get("items", [])]
        if not video_ids:
            return []
        details = self._get("https://www.googleapis.com/youtube/v3/videos", {
            "part": "snippet,contentDetails,statistics",
            "id": ",".join(video_ids),
            "maxResults": len(video_ids),
        })
        rows: list[dict[str, Any]] = []
        for item in details.get("items", []):
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            rows.append({
                "video_id": item["id"],
                "url": youtube_video_url(item["id"]),
                "title": snippet.get("title", ""),
                "description": snippet.get("description", ""),
                "published_at": snippet.get("publishedAt"),
                "duration_seconds": parse_duration_seconds(item.get("contentDetails", {}).get("duration")),
                "view_count": int(stats.get("viewCount", 0)) if str(stats.get("viewCount", "")).isdigit() else None,
                "channel_id": channel_id,
                "channel_title": snippet.get("channelTitle"),
                "practitioner_id": seed.practitioner_id,
                "canonical_name": seed.canonical_name,
            })
        return rows


def main(argv: list[str] | None = None) -> int:
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Inventory and rank registry YouTube channels for Stage 1 discovery.")
    parser.add_argument("--inventory-sample", type=Path, help="Offline inventory JSON sample for acceptance and dry runs")
    parser.add_argument("--registry", type=Path, default=PROJECT_ROOT / "input" / "practitioner_registry.json")
    parser.add_argument("--markers", nargs="+", required=True, help="Marker ids used for ranking")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_DISCOVERY_DIR, help="Directory for youtube_inventory.jsonl and youtube_ranked.jsonl")
    parser.add_argument("--rank-only", action="store_true", help="Rank metadata without transcript fetching")
    parser.add_argument("--live", action="store_true", help="Use YouTube Data API metadata; requires YOUTUBE_API_KEY")
    parser.add_argument("--max-videos-per-channel", type=int, default=50)
    args = parser.parse_args(argv)

    if args.live:
        api_key = os.environ.get("YOUTUBE_API_KEY")
        if not api_key:
            raise SystemExit("YOUTUBE_API_KEY is required for --live")
        provider = YouTubeDataApiProvider(api_key)
        seeds = load_youtube_channel_seeds(args.registry)
        videos: list[dict[str, Any]] = []
        for seed in seeds:
            videos.extend(provider.list_channel_videos(seed, max_results=args.max_videos_per_channel))
        ranked = rank_videos(videos, markers=args.markers)
        channel = {"practitioner_id": None, "canonical_name": "multiple", "channel_url": "multiple", "channel_id": None}
        write_inventory_artifacts(channel, ranked, args.output_dir)
        print(json.dumps({"channels": len(seeds), "ranked_videos": len(ranked), "output_dir": str(args.output_dir)}, sort_keys=True))
        return 0

    if args.inventory_sample is None:
        raise SystemExit("--inventory-sample is required unless --live is set")
    sample = load_inventory_sample(args.inventory_sample)
    ranked = rank_videos(sample["videos"], markers=args.markers)
    write_inventory_artifacts(sample["channel"], ranked, args.output_dir)
    print(json.dumps({"ranked_videos": len(ranked), "output_dir": str(args.output_dir)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Run offline and live guard checks**

Run:

```bash
python code/acceptance/check_youtube_inventory.py
python -m code.discovery.youtube --inventory-sample fixtures/youtube/anthony-chaffee-sample-inventory.json --markers apob fasting-insulin hba1c tg-hdl-ratio --output-dir /tmp/metabolicum-youtube-plan --rank-only
python -m code.discovery.youtube --live --markers apob --output-dir /tmp/metabolicum-youtube-live-guard
```

Expected: first two commands pass; third command fails with `YOUTUBE_API_KEY is required for --live` when the env var is absent.

- [ ] **Step 4: Run live metadata inventory when credentials are available**

Run:

```bash
YOUTUBE_API_KEY="$YOUTUBE_API_KEY" python -m code.discovery.youtube --live --markers apob fasting-insulin hba1c tg-hdl-ratio --max-videos-per-channel 50 --output-dir runs/youtube-discovery/discovery
```

Expected: prints JSON with `channels` greater than `0`, writes `runs/youtube-discovery/discovery/youtube_inventory.jsonl`, and writes `runs/youtube-discovery/discovery/youtube_ranked.jsonl`.

- [ ] **Step 5: Commit**

```bash
git add code/discovery/youtube.py code/acceptance/check_youtube_inventory.py
git commit -m "feat: add youtube discovery cli"
```

---

### Task 8: Add Transcript Provider Boundary

**Files:**
- Modify: `code/discovery/youtube.py`
- Modify: `config/tools.yaml`
- Create: `docs/agentic-workflow/youtube-transcript-discovery.md`

- [ ] **Step 1: Add transcript provider interfaces**

Add this code to `code/discovery/youtube.py`:

```python
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
```

- [ ] **Step 2: Extend CLI with transcript JSON input**

Add CLI args:

```python
    parser.add_argument("--transcript-json", type=Path, help="JSON mapping video_id to transcript text")
    parser.add_argument("--max-transcripts", type=int, default=25)
    parser.add_argument("--min-keyword-score", type=int, default=5)
    parser.add_argument("--fixture-dir", type=Path, default=DEFAULT_FIXTURE_DIR)
```

After ranking in sample mode and live mode, call `JsonTranscriptProvider` when `--transcript-json` is present:

```python
    if args.transcript_json:
        provider = JsonTranscriptProvider(args.transcript_json)
        transcript_by_video_id = {
            video["video_id"]: provider.get_transcript(video["video_id"])
            for video in ranked
        }
        transcript_by_video_id = {key: value for key, value in transcript_by_video_id.items() if value}
        paths = write_transcript_fixtures(
            channel=sample["channel"] if args.inventory_sample else channel,
            ranked_videos=ranked,
            transcript_by_video_id=transcript_by_video_id,
            output_dir=args.fixture_dir,
            max_transcripts=args.max_transcripts,
            min_keyword_score=args.min_keyword_score,
            transcript_method=provider.transcript_method,
        )
        print(json.dumps({"transcript_fixtures": len(paths)}, sort_keys=True))
```

- [ ] **Step 3: Update `youtube-mcp` notes in `config/tools.yaml`**

Add this paragraph to the `youtube-mcp` notes block:

```yaml
    Runtime integration rule: metadata inventory may run as a Python CLI with
    YouTube Data API credentials; transcript retrieval should run through
    youtube-mcp `transcripts_getTranscript` or another explicitly approved
    provider. Retrieved transcripts are cached as source fixtures before Stage 2.
```

- [ ] **Step 4: Commit**

```bash
git add code/discovery/youtube.py config/tools.yaml
git commit -m "feat: add youtube transcript provider boundary"
```

---

### Task 9: Document Operational Policy

**Files:**
- Create: `docs/agentic-workflow/youtube-transcript-discovery.md`
- Modify: `docs/agentic-workflow/03-social-agents-spec.md`
- Modify: `docs/agentic-workflow/07-legal-and-ip-agent.md`
- Modify: `docs/agentic-workflow/10-orchestration-and-filesystem.md`

- [ ] **Step 1: Create `docs/agentic-workflow/youtube-transcript-discovery.md`**

```markdown
# YouTube Transcript Discovery

YouTube is a primary discovery surface for practitioner-heavy MO claims. The pipeline handles it in two phases.

## Phase 1: Channel inventory

The inventory step reads `platform: youtube` surfaces from `input/practitioner_registry.json`, resolves each channel, and records video metadata into `runs/<run_id>/discovery/youtube_inventory.jsonl`. Metadata includes video id, URL, title, description, upload timestamp, duration, view count, channel id, channel title, practitioner id, and practitioner name.

Inventory is allowed to run across every registry YouTube channel because it stores metadata only and uses sanctioned YouTube API access.

## Phase 2: Ranked transcript cache fill

The ranking step scores video title and description against marker aliases plus marker-category expansions from `input/marker_categories.yaml`. The transcript step fetches only ranked videos above the configured threshold and writes normal source fixtures under `fixtures/sources/` or `runs/<run_id>/sources/<source_id>/`.

Default transcript limits:

| Setting | Default |
| --- | ---: |
| max videos per channel inventory | 50 |
| min transcript keyword score | 5 |
| max transcripts per run | 25 |
| max transcripts per practitioner per run | 10 |

## Allowed transcript methods

| Method | `transcript_method` value | Use |
| --- | --- | --- |
| YouTube MCP transcript | `youtube_mcp_transcript` | Preferred transcript cache fill when available. |
| Gemini native URL ingestion | `gemini_native_youtube_url` | Allowed for direct source analysis when transcript export is unavailable. |
| Operator supplied JSON transcript | `operator_supplied_json_transcript` | Allowed for fixtures and manually reviewed cache fills. |

The pipeline does not download video or audio files for this task. It does not use authenticated pages, private videos, member-only videos, or access-control bypasses.

## Stage 2 boundary

Stage 2 never calls YouTube directly. It receives cached transcript fixtures with `source_type: video`, `platform: youtube`, `source_url`, `transcript_method`, `transcript_text`, and `transcript_sha256`.

## Bootstrap target

`person:anthony-chaffee` is the first high-volume channel used to validate this workflow. The initial production run inventories his channel, ranks videos for `apob`, `fasting-insulin`, `hba1c`, and `tg-hdl-ratio`, and caches transcripts for the top ranked videos that have available captions.
```

- [ ] **Step 2: Update `03-social-agents-spec.md`**

Add this paragraph under `## YouTube — Gemini agent`:

```markdown
Implementation uses an inventory-first workflow. The Stage 1 YouTube path first records channel/video metadata for every registry `platform: youtube` surface, then ranks videos by marker aliases and marker-category membership before fetching transcripts. This keeps high-volume channels such as Anthony Chaffee MD tractable: a 1,000+ video channel is inventoried once, but only ranked videos above the configured threshold are cached as transcripts for Stage 2.
```

- [ ] **Step 3: Update `07-legal-and-ip-agent.md`**

Add this paragraph after the existing YouTube transcript paragraph:

```markdown
Bulk YouTube channel inventory stores metadata only. Transcript cache fill is targeted by ranking and budget limits. Cached transcripts are internal source artifacts for quote verification and extraction; downstream publication remains limited to short fair-use excerpts selected by the legal reviewer.
```

- [ ] **Step 4: Update `10-orchestration-and-filesystem.md`**

Add these Stage 1 artifacts to the run-folder layout description:

```text
/discovery/youtube_inventory.jsonl    video metadata rows from registry YouTube surfaces
/discovery/youtube_ranked.jsonl       ranked video candidates with marker/category matches
/discovery/youtube_transcripts.jsonl  transcript cache-fill ledger with method and fixture path
```

- [ ] **Step 5: Commit**

```bash
git add docs/agentic-workflow/youtube-transcript-discovery.md docs/agentic-workflow/03-social-agents-spec.md docs/agentic-workflow/07-legal-and-ip-agent.md docs/agentic-workflow/10-orchestration-and-filesystem.md
git commit -m "docs: define youtube transcript discovery workflow"
```

---

### Task 10: Bootstrap Anthony Chaffee Inventory

**Files:**
- Runtime artifacts: `runs/youtube-discovery/discovery/youtube_inventory.jsonl`
- Runtime artifacts: `runs/youtube-discovery/discovery/youtube_ranked.jsonl`
- Runtime artifacts: `fixtures/sources/*.json` only when transcripts are available and selected.

- [ ] **Step 1: Run metadata inventory for registry YouTube channels**

Run:

```bash
YOUTUBE_API_KEY="$YOUTUBE_API_KEY" python -m code.discovery.youtube --live --markers apob fasting-insulin hba1c tg-hdl-ratio --max-videos-per-channel 50 --output-dir runs/youtube-discovery/discovery
```

Expected: `runs/youtube-discovery/discovery/youtube_ranked.jsonl` exists and contains at least one row with `person:anthony-chaffee`.

- [ ] **Step 2: Inspect top Chaffee candidates**

Run:

```bash
python - <<'PY'
import json
from pathlib import Path
rows = [json.loads(line) for line in Path('runs/youtube-discovery/discovery/youtube_ranked.jsonl').read_text().splitlines() if line.strip()]
for row in rows:
    if row.get('practitioner_id') == 'person:anthony-chaffee':
        print(row['rank'], row['keyword_score'], row['matched_markers'], row['title'], row['source_url'])
PY
```

Expected: prints ranked Chaffee rows. Top rows should mention at least one of ApoB, LDL, triglycerides, HDL, insulin, HbA1c, glucose, HOMA-IR, or diabetes.

- [ ] **Step 3: Fetch transcripts for the selected subset through the approved runtime path**

Use `youtube-mcp transcripts_getTranscript` from the Hermes Stage 1 task runner for selected `video_id` values. Write the returned transcript map to `/tmp/chaffee-youtube-transcripts.json` in this shape:

```json
{
  "sample_insulin_001": "Transcript text returned by the approved provider for that selected video id."
}
```

- [ ] **Step 4: Write source fixtures from selected transcripts**

Run:

```bash
python -m code.discovery.youtube --inventory-sample fixtures/youtube/anthony-chaffee-sample-inventory.json --markers apob fasting-insulin hba1c tg-hdl-ratio --transcript-json /tmp/chaffee-youtube-transcripts.json --max-transcripts 10 --min-keyword-score 5 --fixture-dir fixtures/sources --output-dir runs/youtube-discovery/discovery
```

Expected: writes up to 10 `source_type: video` fixtures under `fixtures/sources/`.

- [ ] **Step 5: Validate fixtures**

Run:

```bash
python code/acceptance/check_fixture_contract.py
```

Expected: prints a line beginning with `checked ` and ending with ` source fixture(s)`, with no hash mismatch.

- [ ] **Step 6: Commit durable code/docs and reviewed fixtures**

```bash
git add code/discovery/youtube.py code/acceptance/check_youtube_inventory.py docs/agentic-workflow/youtube-transcript-discovery.md config/tools.yaml docs/agentic-workflow/03-social-agents-spec.md docs/agentic-workflow/07-legal-and-ip-agent.md docs/agentic-workflow/10-orchestration-and-filesystem.md fixtures/sources
git commit -m "feat: add youtube transcript discovery pipeline"
```

---

### Task 11: Final Verification

**Files:**
- All files changed by Tasks 1-10.

- [ ] **Step 1: Run local acceptance checks**

```bash
python code/acceptance/check_youtube_inventory.py
python code/acceptance/check_fixture_contract.py
```

Expected: both commands exit `0`.

- [ ] **Step 2: Compile edited Python files**

```bash
python -m py_compile code/discovery/youtube.py code/acceptance/check_youtube_inventory.py code/discovery/web.py code/pipeline/stages.py
```

Expected: exit code `0`.

- [ ] **Step 3: Check JSON/YAML parseability**

```bash
python -m json.tool input/practitioner_registry.json >/tmp/practitioner_registry.json
python -m json.tool input/practitioner_aliases.json >/tmp/practitioner_aliases.json
python - <<'PY'
import yaml
for path in ['input/marker_categories.yaml', 'code/environment.yml', 'config/tools.yaml']:
    with open(path) as f:
        yaml.safe_load(f)
    print(path, 'ok')
PY
```

Expected: all commands exit `0` and the YAML script prints `ok` for all three files.

- [ ] **Step 4: Run diff checks**

```bash
git diff --check
git status --short
```

Expected: `git diff --check` exits `0`; `git status --short` shows only intentional files.

- [ ] **Step 5: Record rollout metrics**

After the first Chaffee run, record these values in the PR body or handover:

```text
youtube_channels_inventory_count=1
youtube_videos_inventory_count=50
youtube_ranked_video_count=50
youtube_transcript_fixture_count=10
youtube_transcript_method_counts=youtube_mcp_transcript:10
youtube_stage2_ready_fixture_count=10
```

Use the observed run counts in place of the example counts above.

---

## Rollout Policy

Run order:

1. Anthony Chaffee only, max 50 videos, max 10 transcripts.
2. All registry YouTube channels, max 50 videos per channel, max 25 transcripts total.
3. Top 5 high-volume YouTube practitioners, max 200 videos per channel, max 100 transcripts total.
4. Full registry YouTube inventory, transcript fill only for videos with `keyword_score >= 5` and at least one matched marker category.

Stop conditions:

- More than 20% of transcript fixtures fail `check_fixture_contract.py`.
- More than 10% of transcript fixtures produce no Stage 2 claims after extraction.
- The legal reviewer flags a transcript method as unacceptable.
- YouTube API quota usage exceeds the daily budget set by the operator.

## Self-Review

Spec coverage:
- Bulk inventory is covered by Tasks 4, 7, and 10.
- Targeted transcript cache fill is covered by Tasks 5, 6, 8, and 10.
- Stage 2 source-first boundary is preserved by Tasks 5 and 9.
- Anthony Chaffee bootstrap is covered by Tasks 1 and 10.
- Legal posture is covered by Tasks 8 and 9.
- Verification is covered by Task 11.

Placeholder scan:
- Final scan found no unresolved implementation markers or open-ended fill-in instructions.

Type consistency:
- `YouTubeChannelSeed`, `rank_videos`, `write_inventory_artifacts`, `build_youtube_fixture`, `validate_source_fixture`, and `write_transcript_fixtures` are defined before later tasks use them.
- Artifact names are consistent: `youtube_inventory.jsonl`, `youtube_ranked.jsonl`, and `youtube_transcripts.jsonl`.
- Fixture fields match `code/schemas/source_fixture.schema.json`.
