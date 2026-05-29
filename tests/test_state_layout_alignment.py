import json

import jsonschema

from pathlib import Path


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


def _state_schema():
    return json.loads(Path("code/schemas/state.schema.json").read_text(encoding="utf-8"))


def _validate_state_file(path):
    jsonschema.validate(
        json.loads(path.read_text(encoding="utf-8")),
        _state_schema(),
        format_checker=jsonschema.FormatChecker(),
    )


def test_pipeline_run_state_files_validate_against_schema(tmp_path, monkeypatch):
    from code import state

    monkeypatch.setattr(state, "RUNS_DIR", tmp_path / "runs")

    run = state.PipelineRun.create()
    run.write_stage_state("discovery", status="completed")
    run.write_stage_state("sources", status="completed")
    run.write_stage_state("council", status="completed")
    run.write_stage_state("provenance", status="completed")
    run.fail_stage("legal", error="legal review failed")
    run.quarantine_stage("assembly", error="assembly quarantined")

    for state_path in sorted(run.run_dir.glob("*/state.json")):
        _validate_state_file(state_path)


def test_web_discovery_state_validates_against_schema(tmp_path, monkeypatch):
    from code.discovery import web

    project_root = tmp_path / "project"
    registry_path = project_root / "input" / "practitioners" / "practitioners.json"
    registry_path.parent.mkdir(parents=True)
    registry_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(web, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(web, "REGISTRY_PATH", registry_path)

    discovery_dir = project_root / "runs" / "2026-05-29T120000Z-align" / "discovery"
    web.write_discovery_artifacts([], [], discovery_dir)

    _validate_state_file(discovery_dir / "state.json")


def test_state_contract_acceptance_check_builds_and_validates_default_run(tmp_path):
    from code.acceptance import check_state_contract

    validated = check_state_contract.run_contract_check(tmp_path / "contract-check")

    assert len(validated) == 6
    assert all(path.name == "state.json" for path in validated)
