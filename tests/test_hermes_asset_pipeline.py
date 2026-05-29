from pathlib import Path

import yaml


def test_collect_sources_extracts_public_ids_and_practitioner_surfaces(tmp_path, monkeypatch):
    from scripts import collect_sources

    sm_root = tmp_path / "input" / "sm-ranges"
    asset_root = tmp_path / "input" / "research-assets"
    wave_dir = sm_root / "wave-test"
    wave_dir.mkdir(parents=True)
    (asset_root / "wave-test").mkdir(parents=True)

    (wave_dir / "apob.yaml").write_text(
        yaml.safe_dump(
            {
                "marker_slug": "apob",
                "marker_name": "Apolipoprotein B",
                "rows": [
                    {
                        "public_source_ids": {
                            "pmids": ["12345678"],
                            "pmcids": ["PMC10498001"],
                            "dois": ["10.1000/example"],
                        }
                    }
                ],
                "known_research_context": {
                    "pmids": ["33736827", "12345678"],
                    "pmcids": ["10498001"],
                    "dois": ["https://doi.org/10.1000/example"],
                },
            }
        ),
        encoding="utf-8",
    )
    (asset_root / "wave-test" / "practitioner-index.json").write_text(
        """
{
  "apob": [
    {
      "id": "person:peter-attia",
      "surfaces": [
        {"platform": "website", "handle_or_url": "https://peterattiamd.com/"},
        {"platform": "youtube", "handle_or_url": "https://youtube.com/@peterattia"},
        {"platform": "twitter", "handle_or_url": "@PeterAttiaMD"}
      ]
    }
  ]
}
""".strip(),
        encoding="utf-8",
    )

    monkeypatch.setattr(collect_sources, "SM_RANGES_DIR", sm_root)
    monkeypatch.setattr(collect_sources, "OUTPUT_DIR", asset_root)

    summary = collect_sources.collect_sources_for_wave("wave-test")
    source_index = collect_sources.load_json(asset_root / "wave-test" / "source-index.json")

    assert summary["markers_processed"] == 1
    assert summary["total_sources"] == 5
    assert [item["id"] for item in source_index["apob"] if item["type"] == "pubmed"] == [
        "33736827",
        "12345678",
    ]
    assert any(item["type"] == "pmc_article" and item["id"] == "PMC10498001" for item in source_index["apob"])
    assert any(item["type"] == "doi" and item["doi"] == "10.1000/example" for item in source_index["apob"])
    assert any(
        item["type"] == "practitioner_website"
        and item["practitioner_id"] == "person:peter-attia"
        and item["url"] == "https://peterattiamd.com/"
        for item in source_index["apob"]
    )
    assert not any(item.get("platform") == "youtube" for item in source_index["apob"])


def test_assemble_brief_projects_clean_pointer_fields(tmp_path, monkeypatch):
    from scripts import assemble_hermes_briefs

    sm_root = tmp_path / "input" / "sm-ranges"
    asset_root = tmp_path / "input" / "research-assets"
    brief_root = tmp_path / "input" / "hermes-briefs"
    wave_dir = sm_root / "wave-test"
    asset_wave = asset_root / "wave-test"
    wave_dir.mkdir(parents=True)
    asset_wave.mkdir(parents=True)

    (wave_dir / "apob.yaml").write_text(
        yaml.safe_dump(
            {
                "marker_slug": "apob",
                "marker_name": "Apolipoprotein B",
                "unit": "mg/dL",
                "rows": [
                    {
                        "stratum": "all_adults",
                        "sex": "all",
                        "age_min": 18,
                        "age_max": None,
                        "min": 80,
                        "max": 110,
                        "status": "normal",
                        "use": "display_eligible",
                        "primary_display": True,
                    }
                ],
                "known_research_context": {"pmids": ["33736827"], "pmcids": [], "dois": []},
                "reviewer_note": "internal note",
            }
        ),
        encoding="utf-8",
    )
    (asset_wave / "video-index.json").write_text(
        '{"apob": [{"video_id": "abc123", "score": 99}, {"video_id": "def456", "score": 50}]}',
        encoding="utf-8",
    )
    (asset_wave / "practitioner-index.json").write_text(
        '{"apob": [{"id": "person:peter-attia"}, {"id": "person:peter-attia"}, {"id": "person:allan-sniderman"}]}',
        encoding="utf-8",
    )
    (asset_wave / "source-index.json").write_text(
        """
{
  "apob": [
    {"type": "pubmed", "id": "33736827", "url": "https://pubmed.ncbi.nlm.nih.gov/33736827/"},
    {"type": "doi", "doi": "10.1000/example", "url": "https://doi.org/10.1000/example"},
    {"type": "practitioner_website", "url": "https://peterattiamd.com/", "practitioner_id": "person:peter-attia"}
  ]
}
""".strip(),
        encoding="utf-8",
    )

    monkeypatch.setattr(assemble_hermes_briefs, "SM_RANGES_DIR", sm_root)
    monkeypatch.setattr(assemble_hermes_briefs, "ASSET_DIR", asset_root)
    monkeypatch.setattr(assemble_hermes_briefs, "BRIEFS_DIR", brief_root)

    summary = assemble_hermes_briefs.assemble_wave("wave-test", video_cap=1)
    brief = yaml.safe_load((brief_root / "wave-test" / "apob.yaml").read_text(encoding="utf-8"))

    assert summary["markers_processed"] == 1
    assert brief["recommended_youtube_video_ids"] == ["abc123"]
    assert brief["recommended_practitioner_ids"] == ["person:peter-attia", "person:allan-sniderman"]
    assert brief["recommended_pubmed_ids"] == ["33736827"]
    assert brief["recommended_dois"] == ["10.1000/example"]
    assert brief["recommended_source_urls"] == ["https://peterattiamd.com/"]
    assert brief["recommended_search_queries"] == [
        "Apolipoprotein B practitioner optimal range",
        "Apolipoprotein B metabolic optimization",
    ]
    assert "_meta" not in brief
    assert "reviewer_note" not in brief
    assert "use" not in brief["rows"][0]
    assert "primary_display" not in brief["rows"][0]


def test_legacy_prepare_brief_does_not_embed_meta_scores():
    from scripts import prepare_hermes_briefs

    brief = prepare_hermes_briefs.build_brief(
        "apob",
        "wave-test",
        {
            "marker_slug": "apob",
            "marker_name": "ApoB",
            "known_research_context": {"pmids": ["12345678"], "dois": [], "pmcids": []},
            "rows": [{"low": 60, "high": 120, "use": "display", "primary_display": True}],
        },
        [{"id": "person:peter-attia"}],
        [{"video_id": "abc123", "score": 99, "match_term": "apob"}],
        {"entries": []},
    )

    assert brief["recommended_youtube_video_ids"] == ["abc123"]
    assert "_meta" not in brief
    assert "use" not in brief["rows"][0]
    assert "primary_display" not in brief["rows"][0]


def test_acceptance_check_rejects_meta_blocks():
    from code.acceptance import check_hermes_briefs

    errors = []
    check_hermes_briefs.check_bloat({"_meta": {"video_scores": {"abc123": 10}}}, "apob", errors)

    assert any("_meta" in error for error in errors)
