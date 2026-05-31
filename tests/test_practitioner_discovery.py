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


def test_scan_inventory_matches_parenthesized_term(tmp_path):
    inv = tmp_path / "videos"; inv.mkdir()
    _write_video(inv, "v1", "Doc", "UCp", "All about cortisol (am) testing")
    signals = harvest_inventory.scan_inventory(
        {"cortisol-am": ["cortisol (am)"]}, inventory_dir=inv)
    assert len(signals) == 1
    assert signals[0]["term"] == "cortisol (am)"


def test_scan_inventory_rejects_substring_in_word(tmp_path):
    inv = tmp_path / "videos"; inv.mkdir()
    _write_video(inv, "v2", "Doc", "UCq", "I love testosterones plural")
    assert harvest_inventory.scan_inventory(
        {"total-testosterone": ["testosterone"]}, inventory_dir=inv) == []

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

def test_extract_enrichments_keys_by_existing_practitioner_id():
    signals = [
        # matched by surface channel_id field
        {"source": "inventory", "marker": "total-testosterone", "video_id": "v1",
         "channel_id": "UCberg", "channel": "Dr Berg Live", "title": "T1", "url": "u1",
         "term": "total testosterone", "where": "title"},
        {"source": "inventory", "marker": "total-testosterone", "video_id": "v2",
         "channel_id": "UCberg", "channel": "Dr Berg Live", "title": "T2", "url": "u2",
         "term": "total testosterone", "where": "title"},
        # matched by /channel/<id> URL form of a different surface
        {"source": "inventory", "marker": "cortisol-am", "video_id": "v3",
         "channel_id": "UCbergUrl", "channel": "Dr Berg Live", "title": "T3", "url": "u3",
         "term": "morning cortisol", "where": "title"},
        # unregistered channel -> ignored by enrichments
        {"source": "inventory", "marker": "dhea", "video_id": "v4",
         "channel_id": "UCnew", "channel": "New Doc", "title": "T4", "url": "u4",
         "term": "dhea", "where": "title"},
    ]
    registry = {"practitioners": [
        {"id": "person:eric-berg", "canonical_name": "Eric Berg", "entity_type": "person",
         "surfaces": [
             {"platform": "youtube", "handle_or_url": "https://youtube.com/@drberg",
              "channel_id": "UCberg"},
             {"platform": "youtube",
              "handle_or_url": "https://www.youtube.com/channel/UCbergUrl"}]},
    ]}

    enrichments = extract_candidates.extract_enrichments(signals, registry)

    assert len(enrichments) == 1  # one existing practitioner, unregistered channel absent
    e = enrichments[0]
    assert e["entity_key"] == "person:eric-berg"
    assert e["display_name"] == "Eric Berg"
    assert e["entity_type"] == "person"
    assert e["surfaces"] == []  # must not overwrite existing record's surfaces
    assert len(e["evidence"]["total-testosterone"]) == 2
    assert e["evidence"]["total-testosterone"][0]["ref"] == "yt:v1"
    assert len(e["evidence"]["cortisol-am"]) == 1  # matched via /channel/<id> URL
    # the unregistered channel is not part of any enrichment
    assert "dhea" not in e["evidence"]


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


def test_audit_report_summarizes_new_enriched_and_held():
    new_qualifying = [{"entity_key": "channel:UC1", "display_name": "Hormone MD",
                       "marker_affinity": ["total-testosterone"],
                       "evidence": {"total-testosterone": [{"ref": "yt:a"}, {"ref": "yt:b"}]}}]
    enriched = [{"entity_key": "person:eric-berg", "display_name": "Eric Berg",
                 "marker_affinity": ["cortisol-am"],
                 "evidence": {"cortisol-am": [{"ref": "yt:c"}, {"ref": "yt:d"}]}}]
    held = [{"entity_key": "channel:UC2", "display_name": "Maybe",
             "evidence": {"dhea": [{"ref": "yt:c"}]}}]
    md = audit.render_report(new_qualifying, enriched, held, n=2)
    # newly discovered section
    assert "Newly discovered practitioners" in md
    assert "Hormone MD" in md
    assert "total-testosterone (2)" in md
    # enriched section, with marker + count, under an "Enriched" heading
    assert "Enriched existing practitioners" in md
    assert "Eric Berg" in md
    assert "person:eric-berg" in md
    assert "cortisol-am (2)" in md
    # held section
    assert "Held" in md and "Maybe" in md
    assert "threshold N=2" in md

from scripts.practitioner_discovery import run as discovery_run


def test_run_pipeline_end_to_end_inventory_only(tmp_path):
    inv = tmp_path / "videos"; inv.mkdir()
    _write_video(inv, "v1", "Hormone MD", "UCnew", "Total Testosterone deep dive")
    _write_video(inv, "v2", "Hormone MD", "UCnew", "More on total testosterone")
    _write_video(inv, "v3", "Known Doc", "UCknown", "total testosterone basics")

    registry = {"practitioners": [{"id": "person:known", "surfaces": [
        {"platform": "youtube", "handle_or_url": "x", "channel_id": "UCknown"}]}]}
    policy = {"total-testosterone": {"tiers": {"T1": ["total testosterone"], "T2": []},
                                     "excluded_terms": []}}

    result = discovery_run.run_pipeline(
        markers=["total-testosterone"], registry=registry, policy=policy,
        inventory_dir=inv, n=2)

    # UCnew has 2 evidence -> qualifies; UCknown excluded
    ids = [r["id"] for r in result["registry"]["practitioners"]]
    assert "channel:UCnew" in ids
    new = next(r for r in result["registry"]["practitioners"] if r["id"] == "channel:UCnew")
    assert new["marker_affinity"] == ["total-testosterone"]
    assert "Total Testosterone" in result["audit_md"] or "Hormone MD" in result["audit_md"]
    assert result["summary"]["new_practitioners"] == 1


def test_run_pipeline_enriches_existing_practitioner(tmp_path):
    inv = tmp_path / "videos"; inv.mkdir()
    # Two matching videos on a channel owned by an already-registered practitioner.
    _write_video(inv, "v1", "Known Doc", "UCknown", "Total Testosterone explained")
    _write_video(inv, "v2", "Known Doc", "UCknown", "deep dive on total testosterone")

    registry = {"practitioners": [
        {"id": "person:known", "canonical_name": "Known Doc", "entity_type": "person",
         "marker_affinity": ["dhea"], "surfaces": [
             {"platform": "youtube", "handle_or_url": "x", "channel_id": "UCknown"}]}]}
    policy = {"total-testosterone": {"tiers": {"T1": ["total testosterone"], "T2": []},
                                     "excluded_terms": []}}

    result = discovery_run.run_pipeline(
        markers=["total-testosterone"], registry=registry, policy=policy,
        inventory_dir=inv, n=2)

    # existing practitioner gains the new marker; no new channel record created
    ids = [r["id"] for r in result["registry"]["practitioners"]]
    assert ids == ["person:known"]
    known = next(r for r in result["registry"]["practitioners"] if r["id"] == "person:known")
    assert known["marker_affinity"] == ["dhea", "total-testosterone"]
    # surfaces preserved (not overwritten by an empty enrichment surface list)
    assert known["surfaces"][0]["channel_id"] == "UCknown"
    assert result["summary"]["new_practitioners"] == 0
    assert result["summary"]["enriched"] == 1
    assert "Enriched existing practitioners" in result["audit_md"]

from scripts.practitioner_discovery import harvest_fresh


def test_scan_fresh_normalizes_harvester_output_to_signal_shape():
    def fake_harvester(marker, terms):
        # mimics social_pipeline returning raw video dicts
        return [{"video_id": "vf1", "channel_id": "UCfresh", "channel": "Fresh MD",
                 "title": "total testosterone optimization", "url": "uf1"}]
    signals = harvest_fresh.scan_fresh(
        {"total-testosterone": ["total testosterone"]}, harvester=fake_harvester)
    assert len(signals) == 1
    s = signals[0]
    assert s["source"] == "youtube"
    assert s["channel_id"] == "UCfresh"
    assert s["marker"] == "total-testosterone"
    assert s["term"] == "total testosterone"
    assert s["where"] == "title"


def test_scan_fresh_matches_description_and_skips_unmatched():
    def fake_harvester(marker, terms):
        return [
            {"video_id": "vf2", "channel_id": "UCa", "channel": "A",
             "title": "Q&A", "description": "we cover serum testosterone here", "url": "u2"},
            {"video_id": "vf3", "channel_id": "UCb", "channel": "B",
             "title": "random video", "description": "nothing relevant", "url": "u3"},
        ]
    signals = harvest_fresh.scan_fresh(
        {"total-testosterone": ["serum testosterone"]}, harvester=fake_harvester)
    assert len(signals) == 1
    assert signals[0]["video_id"] == "vf2"
    assert signals[0]["where"] == "description"


def test_scan_fresh_uses_lookaround_matcher_for_parenthesized_terms():
    def fake_harvester(marker, terms):
        return [{"video_id": "vf4", "channel_id": "UCc", "channel": "C",
                 "title": "All about cortisol (am) testing", "url": "u4"}]
    signals = harvest_fresh.scan_fresh(
        {"cortisol-am": ["cortisol (am)"]}, harvester=fake_harvester, source="podcast")
    assert len(signals) == 1
    assert signals[0]["term"] == "cortisol (am)"
    assert signals[0]["source"] == "podcast"


def test_run_pipeline_threads_fresh_signals_into_new_practitioner(tmp_path):
    inv = tmp_path / "videos"; inv.mkdir()  # empty inventory -> all evidence comes from fresh
    fresh_signals = [
        {"source": "youtube", "marker": "total-testosterone", "video_id": "vf1",
         "channel_id": "UCfresh", "channel": "Fresh MD", "title": "T1", "url": "uf1",
         "term": "total testosterone", "where": "title"},
        {"source": "youtube", "marker": "total-testosterone", "video_id": "vf2",
         "channel_id": "UCfresh", "channel": "Fresh MD", "title": "T2", "url": "uf2",
         "term": "total testosterone", "where": "title"},
    ]
    registry = {"practitioners": []}
    policy = {"total-testosterone": {"tiers": {"T1": ["total testosterone"], "T2": []},
                                     "excluded_terms": []}}

    result = discovery_run.run_pipeline(
        markers=["total-testosterone"], registry=registry, policy=policy,
        inventory_dir=inv, n=2, fresh_signals=fresh_signals)

    ids = [r["id"] for r in result["registry"]["practitioners"]]
    assert "channel:UCfresh" in ids
    new = next(r for r in result["registry"]["practitioners"] if r["id"] == "channel:UCfresh")
    assert new["marker_affinity"] == ["total-testosterone"]
    assert result["summary"]["new_practitioners"] == 1
    assert result["summary"]["signals"] == 2
