import json


def test_run_state_uses_brief_driven_layout_for_envelopes_and_council(tmp_path, monkeypatch):
    from code import state

    monkeypatch.setattr(state, "RUNS_DIR", tmp_path / "runs")

    run = state.PipelineRun.create("2026-05-29T120000Z-align")

    stage_state = run.write_stage_state("discovery", status="running")
    assert stage_state.data["schema_version"] == "1"

    envelopes_path = run.write_sanitized_envelopes([
        {
            "marker": "apob",
            "paradigm": "SM",
            "units": "mg/dL",
            "target_low": 60,
            "target_high": 120,
        }
    ])
    assert envelopes_path == run.run_dir / "research_target_envelopes.sanitized.json"
    assert not (run.stage_dir("discovery") / "research_target_envelopes.sanitized.json").exists()

    evaluations_path = run.write_claim_envelope_evaluations([
        {
            "claim_id": "claim-1",
            "envelope_id": "env-1",
            "alignment_status": "aligned",
            "evidence_weight": 0,
        }
    ])
    assert evaluations_path == run.stage_dir("council") / "claim_envelope_evaluations.jsonl"
    rows = [json.loads(line) for line in evaluations_path.read_text(encoding="utf-8").splitlines()]
    assert rows[0]["alignment_status"] == "aligned"
    assert rows[0]["evidence_weight"] == 0


def test_web_discovery_state_includes_schema_version(tmp_path):
    from code.discovery import web

    discovery_dir = tmp_path / "runs" / "2026-05-29T120000Z-align" / "discovery"
    web.write_discovery_artifacts(
        [
            {
                "source_id": "source-1",
                "source_url": "https://example.test/apob",
                "source_type": "web",
                "platform": "website",
                "title": "ApoB target discussion",
                "transcript_text": "ApoB target range discussion",
                "speaker_or_author": "Example Author",
                "speaker_registry_id": "person:example",
                "expected_markers": ["apob"],
                "retrieved_at": "2026-05-29T00:00:00+00:00",
                "transcript_sha256": "abc123",
            }
        ],
        [],
        discovery_dir,
    )

    state_data = json.loads((discovery_dir / "state.json").read_text(encoding="utf-8"))
    assert state_data["schema_version"] == "1"
