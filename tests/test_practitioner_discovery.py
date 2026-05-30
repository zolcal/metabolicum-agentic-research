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

from scripts.practitioner_discovery import extract_candidates


def test_extract_groups_by_channel_and_excludes_registry():
    signals = [
        {"source": "inventory", "marker": "total-testosterone", "video_id": "v1",
         "channel_id": "UCnew", "channel": "Hormone MD", "title": "T1", "url": "u1",
         "term": "total testosterone", "where": "title"},
        {"source": "inventory", "marker": "total-testosterone", "video_id": "v2",
         "channel_id": "UCnew", "channel": "Hormone MD", "title": "T2", "url": "u2",
         "term": "total testosterone", "where": "title"},
        {"source": "inventory", "marker": "cortisol-am", "video_id": "v3",
         "channel_id": "UCknown", "channel": "Known Doc", "title": "T3", "url": "u3",
         "term": "morning cortisol", "where": "title"},
    ]
    registry = {"practitioners": [
        {"id": "person:known", "surfaces": [
            {"platform": "youtube", "handle_or_url": "https://www.youtube.com/channel/UCknown"}]}
    ]}

    candidates = extract_candidates.extract_candidates(signals, registry)

    assert len(candidates) == 1  # UCknown excluded
    c = candidates[0]
    assert c["entity_key"] == "channel:UCnew"
    assert c["display_name"] == "Hormone MD"
    assert c["surfaces"][0]["discovery_mode"] == "auto_discovered"
    assert len(c["evidence"]["total-testosterone"]) == 2
    assert c["evidence"]["total-testosterone"][0]["ref"] == "yt:v1"


def test_extract_excludes_by_channel_id_field():
    signals = [{"source": "inventory", "marker": "dhea", "video_id": "v9",
                "channel_id": "UCz", "channel": "Z", "title": "t", "url": "u",
                "term": "dhea", "where": "title"}]
    registry = {"practitioners": [{"id": "p", "surfaces": [
        {"platform": "youtube", "handle_or_url": "x", "channel_id": "UCz"}]}]}
    assert extract_candidates.extract_candidates(signals, registry) == []

from scripts.practitioner_discovery import threshold


def _cand(channel_id, evidence):
    return {"entity_key": f"channel:{channel_id}", "channel_id": channel_id,
            "display_name": "X", "entity_type": "channel", "surfaces": [],
            "evidence": evidence}


def test_threshold_qualifies_marker_at_n_and_holds_below():
    ev = {"total-testosterone": [{"ref": "yt:a"}, {"ref": "yt:b"}],   # 2 -> qualifies
          "dhea": [{"ref": "yt:c"}]}                                  # 1 -> dropped
    qualifying, held = threshold.apply_threshold([_cand("UC1", ev)], n=2)
    assert len(qualifying) == 1 and held == []
    q = qualifying[0]
    assert q["marker_affinity"] == ["total-testosterone"]
    assert set(q["evidence"].keys()) == {"total-testosterone"}  # sub-threshold marker pruned


def test_threshold_holds_candidate_with_no_qualifying_marker():
    ev = {"dhea": [{"ref": "yt:c"}]}  # only 1 -> below n=2
    qualifying, held = threshold.apply_threshold([_cand("UC2", ev)], n=2)
    assert qualifying == []
    assert len(held) == 1 and held[0]["channel_id"] == "UC2"

from scripts.practitioner_discovery import ingest


def _qual(channel_id, name, affinity, evidence):
    return {"entity_key": f"channel:{channel_id}", "channel_id": channel_id,
            "display_name": name, "entity_type": "channel",
            "surfaces": [{"platform": "youtube",
                          "handle_or_url": f"https://www.youtube.com/channel/{channel_id}",
                          "channel_id": channel_id, "discovery_mode": "auto_discovered"}],
            "marker_affinity": affinity, "evidence": evidence}


def test_to_registry_record_carries_evidence_provenance_and_conservative_grade():
    q = _qual("UC1", "Hormone MD", ["total-testosterone"],
              {"total-testosterone": [{"ref": "yt:a"}, {"ref": "yt:b"}]})
    rec = ingest.to_registry_record(q)
    assert rec["id"] == "channel:UC1"
    assert rec["marker_affinity"] == ["total-testosterone"]
    assert rec["source_grade"] == "E2"
    assert rec["surfaces"][0]["discovery_mode"] == "auto_discovered"
    prov = {p["marker"]: p for p in rec["discovery_provenance"]}
    assert prov["total-testosterone"]["evidence_count"] == 2
    assert prov["total-testosterone"]["evidence"] == ["yt:a", "yt:b"]


def test_merge_adds_new_and_unions_existing_affinity():
    registry = {"practitioners": [
        {"id": "channel:UC1", "marker_affinity": ["dhea"], "surfaces": []}]}
    recs = [
        ingest.to_registry_record(_qual("UC1", "MD", ["total-testosterone"],
            {"total-testosterone": [{"ref": "yt:a"}, {"ref": "yt:b"}]})),
        ingest.to_registry_record(_qual("UC2", "New", ["cortisol-am"],
            {"cortisol-am": [{"ref": "yt:c"}, {"ref": "yt:d"}]})),
    ]
    merged = ingest.merge_into_registry(registry, recs)
    by_id = {p["id"]: p for p in merged["practitioners"]}
    assert by_id["channel:UC1"]["marker_affinity"] == ["dhea", "total-testosterone"]
    assert "channel:UC2" in by_id

from scripts.practitioner_discovery import audit


def test_audit_report_summarizes_qualifying_and_held():
    qualifying = [{"entity_key": "channel:UC1", "display_name": "Hormone MD",
                   "marker_affinity": ["total-testosterone"],
                   "evidence": {"total-testosterone": [{"ref": "yt:a"}, {"ref": "yt:b"}]}}]
    held = [{"entity_key": "channel:UC2", "display_name": "Maybe",
             "evidence": {"dhea": [{"ref": "yt:c"}]}}]
    md = audit.render_report(qualifying, held, n=2)
    assert "Hormone MD" in md
    assert "total-testosterone (2)" in md
    assert "Held" in md and "Maybe" in md
    assert "threshold N=2" in md
