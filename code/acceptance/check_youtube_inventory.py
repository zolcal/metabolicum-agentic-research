"""Acceptance checks for YouTube inventory and transcript-cache artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import sys

ROOT = Path(__file__).resolve().parents[2]
# Direct script execution needs the repository root so imports resolve to this
# project-level `code` package instead of Python's stdlib module.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from code.discovery.youtube import (
    load_inventory_sample,
    load_youtube_channel_seeds,
    rank_videos,
    validate_source_fixture,
    write_inventory_artifacts,
    write_transcript_fixtures,
    select_transcript_candidates,
    main as youtube_main,
    YouTubeChannelSeed,
    YouTubeDataApiProvider,
    build_youtube_fixture,
)  # noqa: E402

SAMPLE = ROOT / "fixtures" / "youtube" / "anthony-chaffee-sample-inventory.json"


def main() -> int:
    sample = load_inventory_sample(SAMPLE)
    no_marker_video = {
        "video_id": "sample_general_high_signal_999",
        "title": "A very long popular APOBee general nutrition discussion",
        "description": "General physiology overview without target biomarkers.",
        "duration_seconds": 7200,
        "view_count": 1000000,
        "published_at": "2026-01-01T00:00:00Z",
    }
    youtube_style_video = {
        "video_id": "sample_high_insulin_001",
        "title": "This Is What High Insulin Does to Your Body",
        "description": "A YouTube-style shorthand title that should still enter transcript review.",
        "duration_seconds": 900,
        "view_count": 1000,
        "published_at": "2026-02-01T00:00:00Z",
    }
    ranked = rank_videos(
        [*sample["videos"], no_marker_video, youtube_style_video],
        markers=["apob", "fasting-insulin", "hba1c", "tg-hdl-ratio"],
    )
    ids = [row["video_id"] for row in ranked]
    if ids[:2] != ["sample_insulin_001", "sample_apob_001"]:
        raise SystemExit(f"unexpected ranking order: {ids}")
    no_marker_ranked = next(row for row in ranked if row["video_id"] == no_marker_video["video_id"])
    if no_marker_ranked["matched_markers"] != []:
        raise SystemExit(f"no-marker video matched markers: {no_marker_ranked['matched_markers']}")
    if no_marker_ranked["rank_reason"] != "no_marker_keyword_match":
        raise SystemExit(f"unexpected no-marker rank reason: {no_marker_ranked['rank_reason']}")
    if no_marker_ranked["keyword_score"] != 0:
        raise SystemExit(f"unexpected no-marker keyword score: {no_marker_ranked['keyword_score']}")
    marker_rows = [row for row in ranked if row["matched_markers"]]
    if any(ids.index(no_marker_video["video_id"]) < ids.index(row["video_id"]) for row in marker_rows):
        raise SystemExit(f"no-marker video outranked marker matches: {ids}")
    youtube_style_ranked = next(row for row in ranked if row["video_id"] == youtube_style_video["video_id"])
    if "fasting-insulin" not in youtube_style_ranked["matched_markers"]:
        raise SystemExit(f"YouTube-style insulin shorthand was not matched: {youtube_style_ranked}")
    if ranked[0]["keyword_score"] <= no_marker_ranked["keyword_score"]:
        raise SystemExit("marker videos must outrank general videos")
    transcript = (
        "Dr Anthony Chaffee says fasting insulin and HbA1c improve when carbohydrate exposure falls. "
        "A fasting insulin above 10 mIU/L suggests insulin resistance."
    )
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
    live_style_fixture = build_youtube_fixture(
        video={**ranked[0], "practitioner_id": "person:anthony-chaffee", "canonical_name": "Anthony Chaffee"},
        channel={"canonical_name": "multiple", "practitioner_id": None},
        transcript_text=transcript,
        transcript_method="operator_supplied_json_transcript",
        expected_markers=["fasting-insulin", "hba1c"],
    )
    if live_style_fixture["speaker_registry_id"] != "person:anthony-chaffee":
        raise SystemExit("live-style YouTube fixture must preserve video practitioner id")
    if live_style_fixture["speaker_or_author"] != "Anthony Chaffee":
        raise SystemExit("live-style YouTube fixture must preserve video canonical name")
    tampered_fixture = dict(fixture)
    tampered_fixture["synthetic"] = True
    tampered_fixture["verification_status"] = "unverified"
    try:
        validate_source_fixture(tampered_fixture)
    except ValueError:
        pass
    else:
        raise SystemExit("YouTube fixture validation accepted synthetic/unverified source")

    transcript_by_video_id = {
        "sample_insulin_001": (
            "Fasting insulin above 10 mIU/L suggests insulin resistance. "
            "HbA1c improves when glucose exposure falls."
        ),
        "sample_apob_001": (
            "ApoB, LDL cholesterol and triglycerides can rise on low carbohydrate diets, while HDL often rises too."
        ),
    }
    selected = select_transcript_candidates(ranked, max_transcripts=2, min_keyword_score=5)
    if [row["video_id"] for row in selected] != ["sample_insulin_001", "sample_apob_001"]:
        raise SystemExit(f"unexpected transcript candidate selection: {selected}")
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

    with TemporaryDirectory() as tmp:
        exit_code = youtube_main(
            [
                "--inventory-sample",
                str(SAMPLE),
                "--markers",
                "apob",
                "fasting-insulin",
                "hba1c",
                "tg-hdl-ratio",
                "--output-dir",
                tmp,
                "--rank-only",
            ]
        )
        if exit_code != 0:
            raise SystemExit(f"youtube CLI returned {exit_code}")
        if not (Path(tmp) / "youtube_ranked.jsonl").exists():
            raise SystemExit("youtube CLI did not write ranked artifact")

    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        transcript_json = tmp_path / "transcripts.json"
        transcript_json.write_text(json.dumps(transcript_by_video_id, sort_keys=True))
        exit_code = youtube_main(
            [
                "--inventory-sample",
                str(SAMPLE),
                "--markers",
                "apob",
                "fasting-insulin",
                "hba1c",
                "tg-hdl-ratio",
                "--output-dir",
                str(tmp_path / "discovery"),
                "--transcript-json",
                str(transcript_json),
                "--fixture-dir",
                str(tmp_path / "fixtures"),
                "--max-transcripts",
                "2",
                "--min-keyword-score",
                "1",
            ]
        )
        if exit_code != 0:
            raise SystemExit(f"youtube transcript CLI returned {exit_code}")
        if len(list((tmp_path / "fixtures").glob("*.json"))) != 2:
            raise SystemExit("youtube transcript CLI did not write expected fixtures")
        ledger_path = tmp_path / "discovery" / "youtube_transcripts.jsonl"
        if not ledger_path.exists():
            raise SystemExit("youtube transcript CLI did not write transcript ledger")
        ledger_rows = [json.loads(line) for line in ledger_path.read_text().splitlines() if line.strip()]
        if len(ledger_rows) != 2:
            raise SystemExit(f"expected 2 transcript ledger rows, got {len(ledger_rows)}")
        if any(row.get("transcript_method") != "operator_supplied_json_transcript" for row in ledger_rows):
            raise SystemExit(f"unexpected transcript ledger methods: {ledger_rows}")

    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        transcript_json = tmp_path / "transcripts.json"
        transcript_json.write_text(json.dumps(transcript_by_video_id, sort_keys=True))
        exit_code = youtube_main(
            [
                "--inventory-sample",
                str(SAMPLE),
                "--markers",
                "apob",
                "fasting-insulin",
                "hba1c",
                "tg-hdl-ratio",
                "--output-dir",
                str(tmp_path / "discovery"),
                "--transcript-json",
                str(transcript_json),
                "--fixture-dir",
                str(tmp_path / "fixtures"),
                "--rank-only",
            ]
        )
        if exit_code != 0:
            raise SystemExit(f"youtube rank-only transcript CLI returned {exit_code}")
        if (tmp_path / "fixtures").exists() and list((tmp_path / "fixtures").glob("*.json")):
            raise SystemExit("youtube rank-only CLI wrote transcript fixtures")
        if (tmp_path / "discovery" / "youtube_transcripts.jsonl").exists():
            raise SystemExit("youtube rank-only CLI wrote transcript ledger")

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
    seeds = load_youtube_channel_seeds(ROOT / "input" / "practitioner_registry.json")
    chaffee = [seed for seed in seeds if seed.practitioner_id == "person:anthony-chaffee"]
    if not chaffee:
        raise SystemExit("person:anthony-chaffee youtube seed missing")
    if chaffee[0].channel_url != "https://www.youtube.com/@anthonychaffeemd":
        raise SystemExit(f"unexpected Chaffee channel URL: {chaffee[0].channel_url}")
    if not isinstance(chaffee[0].marker_affinity, tuple):
        raise SystemExit(f"marker_affinity must be immutable tuple: {type(chaffee[0].marker_affinity)}")

    class FakeYouTubeSession:
        def get(self, url, params, timeout):  # noqa: ANN001
            class FakeResponse:
                def raise_for_status(self) -> None:
                    return None

                def json(self) -> dict[str, object]:
                    return {"items": [{"id": "UC_FAKE", "snippet": {"channelId": "UC_FAKE"}}]}

            return FakeResponse()

    class FakeErrorSession:
        def get(self, url, params, timeout):  # noqa: ANN001
            class FakeResponse:
                status_code = 429

                def raise_for_status(self) -> None:
                    raise RuntimeError("429 for https://example.test?key=SECRET")

                def json(self) -> dict[str, object]:
                    return {"error": {"message": "Too Many Requests"}}

            return FakeResponse()

    try:
        YouTubeDataApiProvider("secret-key", session=FakeErrorSession())._get("https://example.test/youtube", {})
    except RuntimeError as exc:
        error_text = str(exc)
        if "secret-key" in error_text or "key=SECRET" in error_text:
            raise SystemExit(f"YouTube API error was not sanitized: {error_text}")
        if "Too Many Requests" not in error_text:
            raise SystemExit(f"YouTube API error lost provider message: {error_text}")
    else:
        raise SystemExit("YouTube API error did not raise")

    fake_provider = YouTubeDataApiProvider("fake-key", session=FakeYouTubeSession())
    for channel_url in (
        "https://www.youtube.com/@validhandle",
        "https://www.youtube.com/c/ValidChannel",
        "https://www.youtube.com/user/ValidUser",
    ):
        seed = YouTubeChannelSeed(
            practitioner_id="person:test-youtube",
            canonical_name="Test YouTube",
            source_tier="A",
            channel_url=channel_url,
            priority="primary",
            marker_affinity=("apob",),
        )
        if fake_provider.resolve_channel_id(seed) != "UC_FAKE":
            raise SystemExit(f"channel URL did not resolve through provider: {channel_url}")

    with TemporaryDirectory() as tmp:
        bad_registry = Path(tmp) / "youtube-seed-bad-surfaces.json"
        bad_registry.write_text(
            json.dumps(
                {
                    "practitioners": [
                        {
                            "id": "person:test-youtube",
                            "canonical_name": "Test YouTube",
                            "source_tier": "A",
                            "marker_affinity": ["apob"],
                            "surfaces": [
                                {"platform": "youtube", "handle_or_url": "https://www.youtube.com/@validhandle"},
                                {"platform": "youtube", "handle_or_url": "https://www.youtube.com/watch?v=bad"},
                                {"platform": "youtube", "handle_or_url": "https://youtu.be/bad"},
                                {"platform": "youtube", "handle_or_url": "https://www.youtube.com/shorts/bad"},
                            ],
                        }
                    ]
                },
                sort_keys=True,
            )
        )
        bad_surface_seeds = load_youtube_channel_seeds(bad_registry)
        if [seed.channel_url for seed in bad_surface_seeds] != ["https://www.youtube.com/@validhandle"]:
            raise SystemExit(f"video surfaces accepted as channel seeds: {bad_surface_seeds}")
        try:
            bad_surface_seeds[0].marker_affinity.append("fasting-insulin")  # type: ignore[attr-defined]
        except AttributeError:
            pass
        else:
            raise SystemExit("marker_affinity must not be caller-mutable")
    print(json.dumps({"checked": len(ranked), "top_video_id": ranked[0]["video_id"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
