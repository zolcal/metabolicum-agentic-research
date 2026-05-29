import json
from pathlib import Path

import yaml


def test_practitioner_audit_detects_structured_sources_and_skips_generated_outputs(tmp_path):
    from scripts import audit_practitioner_data

    project = tmp_path / "project-a"
    registry = project / "input" / "practitioner_registry.json"
    generated = project / "input" / "hermes-briefs" / "wave-0" / "apob.yaml"
    directory = project / "docs" / "research" / "practitioners" / "directory.md"
    registry.parent.mkdir(parents=True)
    generated.parent.mkdir(parents=True)
    directory.parent.mkdir(parents=True)

    registry.write_text(
        json.dumps(
            {
                "practitioners": [
                    {
                        "id": "person:peter-attia",
                        "canonical_name": "Peter Attia",
                        "marker_affinity": ["apob"],
                        "surfaces": [
                            {"platform": "website", "handle_or_url": "https://peterattiamd.com/"},
                            {"platform": "twitter", "handle_or_url": "@PeterAttiaMD"},
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    generated.write_text(
        yaml.safe_dump({"recommended_practitioner_ids": ["person:peter-attia"]}),
        encoding="utf-8",
    )
    directory.write_text(
        "# Practitioner Directory\n\nThis directory is the single source of truth.\n\n"
        "| Name | Evidence Grade | Contact |\n"
        "| --- | --- | --- |\n"
        "| **Dr. Peter Attia, MD** | B1 | peterattiamd.com |\n",
        encoding="utf-8",
    )

    inventory = audit_practitioner_data.build_inventory([project])
    paths = {item["path"] for item in inventory["files"]}

    assert str(registry) in paths
    assert str(directory) in paths
    assert str(generated) not in paths
    assert inventory["summary"]["candidate_files"] == 2
    assert inventory["summary"]["structured_practitioner_records"] == 1

    registry_item = next(item for item in inventory["files"] if item["path"] == str(registry))
    assert registry_item["format"] == "json"
    assert registry_item["practitioner_count"] == 1
    assert registry_item["sample_ids"] == ["person:peter-attia"]
    assert registry_item["resource_buckets"] == [
        "identity",
        "marker_affinity",
        "web_resources",
        "social_resources",
    ]
    assert registry_item["surface_counts"] == {"twitter": 1, "website": 1}

    report = audit_practitioner_data.render_markdown_report(inventory)
    assert "Practitioner Data Audit" in report
    assert "Active Canonical Sources" in report
    assert "Best Legacy Consolidated Input" in report
    assert str(registry) in report
