import json


def test_build_canonical_sources_splits_identity_marker_web_and_social(tmp_path):
    from scripts import build_canonical_practitioner_sources as builder

    registry = tmp_path / "practitioner_registry.json"
    aliases = tmp_path / "practitioner_aliases.json"

    registry.write_text(
        json.dumps(
            {
                "practitioners": [
                    {
                        "id": "person:peter-attia",
                        "canonical_name": "Peter Attia",
                        "aliases": ["Peter Attia"],
                        "entity_type": "person",
                        "country": "United States",
                        "region": "North America",
                        "languages": ["en"],
                        "paradigm_affinity": ["MO"],
                        "source_tier": "A",
                        "source_grade": "B1",
                        "marker_affinity": ["apob", "lpa"],
                        "key_contribution": "ApoB prevention framing",
                        "surfaces": [
                            {
                                "platform": "website",
                                "handle_or_url": "https://peterattiamd.com/",
                                "priority": "primary",
                            },
                            {
                                "platform": "youtube",
                                "handle_or_url": "https://www.youtube.com/@PeterAttiaMD",
                                "priority": "primary",
                            },
                            {
                                "platform": "twitter",
                                "handle_or_url": "@PeterAttiaMD",
                                "priority": "secondary",
                            },
                            {
                                "platform": "website",
                                "handle_or_url": "https://twitter.com/PeterAttiaMD",
                                "priority": "secondary",
                            },
                            {
                                "platform": "other",
                                "handle_or_url": "manual:person:peter-attia",
                                "priority": "manual_only",
                            },
                        ],
                        "commercial_interests": [
                            {
                                "domain": "membership",
                                "product_or_service": "subscription",
                                "severity": "generic",
                            }
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    aliases.write_text(
        json.dumps(
            {
                "aliases": [
                    {
                        "practitioner_id": "person:peter-attia",
                        "canonical_name": "Peter Attia",
                        "aliases": ["Dr. Peter Attia", "Peter Attia"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    bundle = builder.build_canonical_sources(registry, aliases, generated_at="2026-05-29T00:00:00+00:00")

    identity = bundle["practitioners"]["practitioners"][0]
    assert identity["id"] == "person:peter-attia"
    assert identity["aliases"] == ["Dr. Peter Attia", "Peter Attia"]
    assert "marker_affinity" not in identity
    assert "surfaces" not in identity

    marker = bundle["marker_affinity"]["marker_affinities"][0]
    assert marker == {
        "practitioner_id": "person:peter-attia",
        "canonical_name": "Peter Attia",
        "marker_affinity": ["apob", "lpa"],
        "paradigm_affinity": ["MO"],
        "key_contribution": "ApoB prevention framing",
    }

    web = bundle["web_resources"]["web_resources"]
    assert [resource["platform"] for resource in web] == ["website"]
    assert web[0]["url"] == "https://peterattiamd.com/"

    social = bundle["social_resources"]["social_resources"]
    assert [resource["platform"] for resource in social] == ["twitter", "twitter", "youtube"]
    assert "https://twitter.com/PeterAttiaMD" in [resource["handle_or_url"] for resource in social]
    assert all(resource["handle_or_url"] != "manual:person:peter-attia" for resource in social)


def test_write_canonical_sources_creates_expected_files(tmp_path):
    from scripts import build_canonical_practitioner_sources as builder

    bundle = {
        "practitioners": {"schema_version": "1", "practitioners": []},
        "marker_affinity": {"schema_version": "1", "marker_affinities": []},
        "web_resources": {"schema_version": "1", "web_resources": []},
        "social_resources": {"schema_version": "1", "social_resources": []},
    }

    builder.write_canonical_sources(bundle, tmp_path)

    assert (tmp_path / "practitioners.json").exists()
    assert (tmp_path / "practitioner-marker-affinity.json").exists()
    assert (tmp_path / "practitioner-web-resources.json").exists()
    assert (tmp_path / "practitioner-social-resources.json").exists()
    assert (tmp_path / "README.md").exists()
