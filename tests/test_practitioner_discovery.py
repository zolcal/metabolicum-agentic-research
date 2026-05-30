from scripts.practitioner_discovery import terms


def test_marker_terms_uses_t1_t2_phrases_and_drops_excluded():
    policy = {
        "total-testosterone": {
            "tiers": {
                "T1": ["total testosterone"],
                "T2": ["testosterone (total)", "serum testosterone"],
                "T3": ["testosterone"],
                "T4": ["testo"],
            },
            "excluded_terms": ["testo"],
        }
    }
    out = terms.marker_terms("total-testosterone", policy)
    assert out == ["total testosterone", "testosterone (total)", "serum testosterone"]
    # bare generic T3/T4 terms are never used for discovery
    assert "testosterone" not in out
    assert "testo" not in out


def test_marker_terms_unknown_marker_is_empty():
    assert terms.marker_terms("nope", {}) == []

import json
from scripts.practitioner_discovery import harvest_inventory


def _write_video(d, vid, channel, channel_id, title, desc=""):
    (d / f"{vid}.json").write_text(json.dumps({
        "video_id": vid, "channel": channel, "channel_id": channel_id,
        "title": title, "description": desc,
        "url": f"https://www.youtube.com/watch?v={vid}",
    }), encoding="utf-8")


def test_scan_inventory_emits_signal_on_phrase_match(tmp_path):
    inv = tmp_path / "videos"; inv.mkdir()
    _write_video(inv, "v1", "Hormone MD", "UCaaa", "Total Testosterone explained")
    _write_video(inv, "v2", "Keto Guy", "UCbbb", "What I ate today")  # no match
    terms_by_marker = {"total-testosterone": ["total testosterone"]}

    signals = harvest_inventory.scan_inventory(terms_by_marker, inventory_dir=inv)

    assert len(signals) == 1
    s = signals[0]
    assert s["marker"] == "total-testosterone"
    assert s["channel_id"] == "UCaaa"
    assert s["video_id"] == "v1"
    assert s["term"] == "total testosterone"
    assert s["where"] == "title"
    assert s["source"] == "inventory"


def test_scan_inventory_matches_description_word_boundary(tmp_path):
    inv = tmp_path / "videos"; inv.mkdir()
    _write_video(inv, "v3", "Doc", "UCccc", "Q&A", desc="we discuss serum testosterone levels")
    # 'testosterone' alone must NOT match (not a provided phrase term)
    signals = harvest_inventory.scan_inventory(
        {"total-testosterone": ["serum testosterone"]}, inventory_dir=inv)
    assert len(signals) == 1
    assert signals[0]["where"] == "description"
