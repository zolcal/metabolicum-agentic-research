# Practitioner Gap Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Discover practitioners who actually discuss under-covered markers (pilot: hormones), gate them by retrievable evidence (≥N sources), and auto-ingest them into `input/practitioner_registry.json` so empty/thin MO briefs gain practitioner + website pointers.

**Architecture:** A 6-stage pipeline. Stage 1 harvests raw signals (local 26k-video inventory scan first, then reused `social_pipeline` YouTube/podcast search). Stages 2–5 (new) group signals by channel, exclude known practitioners, gate by evidence count, ingest into the registry, and re-assemble briefs. Build the inventory-only path end-to-end first; add fresh search last.

**Tech Stack:** Python 3.10+, stdlib only (json, re, pathlib, collections, argparse), pytest. Reuses `scripts/build_canonical_practitioner_sources.py` and `scripts/assemble_hermes_briefs.py`.

---

## File Structure

```
scripts/practitioner_discovery/
  __init__.py
  terms.py              # phrase-based marker terms from alias-policy (T1+T2)
  harvest_inventory.py  # scan local 26k inventory -> signals
  extract_candidates.py # group signals by channel, exclude registry, attach evidence
  threshold.py          # apply N-evidence gate -> qualifying/held
  ingest.py             # build registry records + merge with provenance
  audit.py              # write run report
  run.py                # orchestrator: marker list -> all stages -> outputs
  harvest_fresh.py      # (Task 8) YouTube/podcast fresh search via social_pipeline
tests/
  test_practitioner_discovery.py
output/practitioner-discovery/<run-id>/   # candidates.json, qualifying.json, held.json, audit.md
```

Each module has one responsibility and is pure (data in → data out) except `run.py`/`ingest.py` which touch disk. All stage functions take their inputs as arguments (registry, policy, signals) so tests pass fixtures and never depend on real project files.

**Shared data shapes** (used across tasks — keep names exact):

```python
# signal (harvest output)
{"source": "inventory", "marker": "total-testosterone", "video_id": "abc123",
 "channel_id": "UCxxxx", "channel": "Some MD", "title": "...", "url": "...",
 "term": "total testosterone", "where": "title"}

# candidate (extract output)
{"entity_key": "channel:UCxxxx", "channel_id": "UCxxxx", "display_name": "Some MD",
 "entity_type": "channel",
 "surfaces": [{"platform": "youtube", "handle_or_url": "https://www.youtube.com/channel/UCxxxx",
               "channel_id": "UCxxxx", "discovery_mode": "auto_discovered"}],
 "evidence": {"total-testosterone": [{"source": "inventory", "ref": "yt:abc123",
              "title": "...", "term": "total testosterone", "where": "title"}]}}

# qualifying candidate adds: "marker_affinity": ["total-testosterone"]  (evidence pruned to qualifying markers)
```

---

## Task 1: Package skeleton + phrase-based marker terms

**Files:**
- Create: `scripts/practitioner_discovery/__init__.py` (empty)
- Create: `scripts/practitioner_discovery/terms.py`
- Test: `tests/test_practitioner_discovery.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_practitioner_discovery.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `env TMPDIR=$PWD/.pytest-tmp python3 -m pytest tests/test_practitioner_discovery.py -q`
Expected: FAIL with `ModuleNotFoundError: scripts.practitioner_discovery`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/practitioner_discovery/__init__.py
```

```python
# scripts/practitioner_discovery/terms.py
"""Phrase-based discovery terms for a marker.

Uses only the specific T1 (primary phrase) and T2 (qualified alias) tiers from
the alias policy, minus any excluded terms. Bare single-word generic terms
(T3/T4 — 'testosterone', 'blood', 'free') are deliberately NOT used: they are
the source of the false-positive explosion fixed on 2026-05-30.
"""
from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALIAS_POLICY = PROJECT_ROOT / "input" / "research-assets" / "alias-policy.json"


def load_policy(path: Path | None = None) -> dict:
    return json.loads((path or ALIAS_POLICY).read_text(encoding="utf-8"))


def marker_terms(marker_slug: str, policy: dict) -> list[str]:
    data = policy.get(marker_slug, {})
    tiers = data.get("tiers", {})
    excluded = {t.lower() for t in data.get("excluded_terms", [])}
    out: list[str] = []
    seen: set[str] = set()
    for tier in ("T1", "T2"):
        for term in tiers.get(tier, []):
            tl = (term or "").lower()
            if tl and tl not in excluded and tl not in seen:
                seen.add(tl)
                out.append(tl)
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `env TMPDIR=$PWD/.pytest-tmp python3 -m pytest tests/test_practitioner_discovery.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/practitioner_discovery/__init__.py scripts/practitioner_discovery/terms.py tests/test_practitioner_discovery.py
git commit -m "feat(discovery): phrase-based marker terms (T1+T2, no generic tokens)"
```

---

## Task 2: Scan local inventory into signals

**Files:**
- Create: `scripts/practitioner_discovery/harvest_inventory.py`
- Test: `tests/test_practitioner_discovery.py` (append)

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_practitioner_discovery.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `env TMPDIR=$PWD/.pytest-tmp python3 -m pytest tests/test_practitioner_discovery.py -k scan_inventory -q`
Expected: FAIL with `ModuleNotFoundError` / `AttributeError: scan_inventory`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/practitioner_discovery/harvest_inventory.py
"""Scan the local YouTube video inventory for marker phrase matches.

Free, no API. Word-boundary phrase matching (no term splitting) over each
video's title and description.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INVENTORY_DIR = PROJECT_ROOT / "input" / "youtube-video-inventory" / "videos"


def _first_match(text: str, terms: list[str]) -> str | None:
    for term in terms:
        if re.search(r"\b" + re.escape(term) + r"\b", text, re.IGNORECASE):
            return term
    return None


def scan_inventory(terms_by_marker: dict[str, list[str]],
                   inventory_dir: Path = INVENTORY_DIR) -> list[dict]:
    signals: list[dict] = []
    for f in sorted(Path(inventory_dir).glob("*.json")):
        try:
            v = json.loads(f.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        title = v.get("title", "") or ""
        desc = v.get("description", "") or ""
        for marker, marker_terms in terms_by_marker.items():
            term = _first_match(title, marker_terms)
            where = "title"
            if not term:
                term = _first_match(desc, marker_terms)
                where = "description"
            if not term:
                continue
            signals.append({
                "source": "inventory",
                "marker": marker,
                "video_id": v.get("video_id", ""),
                "channel_id": v.get("channel_id", ""),
                "channel": v.get("channel", ""),
                "title": title,
                "url": v.get("url", ""),
                "term": term,
                "where": where,
            })
    return signals
```

- [ ] **Step 4: Run test to verify it passes**

Run: `env TMPDIR=$PWD/.pytest-tmp python3 -m pytest tests/test_practitioner_discovery.py -k scan_inventory -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/practitioner_discovery/harvest_inventory.py tests/test_practitioner_discovery.py
git commit -m "feat(discovery): local inventory scan -> phrase-matched signals"
```

---

## Task 3: Extract candidates (group by channel, exclude registry)

**Files:**
- Create: `scripts/practitioner_discovery/extract_candidates.py`
- Test: `tests/test_practitioner_discovery.py` (append)

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_practitioner_discovery.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `env TMPDIR=$PWD/.pytest-tmp python3 -m pytest tests/test_practitioner_discovery.py -k extract -q`
Expected: FAIL with `ModuleNotFoundError` / `AttributeError`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/practitioner_discovery/extract_candidates.py
"""Group harvested signals into candidate practitioners, excluding any channel
already represented in the registry."""
from __future__ import annotations

import re
from collections import defaultdict


def registry_channel_ids(registry: dict) -> set[str]:
    ids: set[str] = set()
    for p in registry.get("practitioners", []):
        for s in p.get("surfaces", []) or []:
            cid = s.get("channel_id")
            if cid:
                ids.add(cid)
            m = re.search(r"/channel/([A-Za-z0-9_-]+)", str(s.get("handle_or_url", "")))
            if m:
                ids.add(m.group(1))
    return ids


def extract_candidates(signals: list[dict], registry: dict) -> list[dict]:
    known = registry_channel_ids(registry)
    grouped: dict[str, dict] = {}
    evidence: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for s in signals:
        cid = s.get("channel_id") or ""
        if not cid or cid in known:
            continue
        grouped.setdefault(cid, {"channel": s.get("channel", "")})
        evidence[cid][s["marker"]].append({
            "source": s["source"], "ref": f"yt:{s['video_id']}",
            "title": s["title"], "term": s["term"], "where": s["where"],
        })
    out: list[dict] = []
    for cid, meta in grouped.items():
        out.append({
            "entity_key": f"channel:{cid}",
            "channel_id": cid,
            "display_name": meta["channel"],
            "entity_type": "channel",
            "surfaces": [{
                "platform": "youtube",
                "handle_or_url": f"https://www.youtube.com/channel/{cid}",
                "channel_id": cid,
                "discovery_mode": "auto_discovered",
            }],
            "evidence": {m: ev for m, ev in evidence[cid].items()},
        })
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `env TMPDIR=$PWD/.pytest-tmp python3 -m pytest tests/test_practitioner_discovery.py -k extract -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/practitioner_discovery/extract_candidates.py tests/test_practitioner_discovery.py
git commit -m "feat(discovery): group signals into registry-excluded candidates"
```

---

## Task 4: Threshold gate

**Files:**
- Create: `scripts/practitioner_discovery/threshold.py`
- Test: `tests/test_practitioner_discovery.py` (append)

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_practitioner_discovery.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `env TMPDIR=$PWD/.pytest-tmp python3 -m pytest tests/test_practitioner_discovery.py -k threshold -q`
Expected: FAIL with `ModuleNotFoundError` / `AttributeError`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/practitioner_discovery/threshold.py
"""Evidence-count gate. A candidate earns marker_affinity[marker] only when it
has >= n evidence items for that marker."""
from __future__ import annotations


def apply_threshold(candidates: list[dict], n: int = 2) -> tuple[list[dict], list[dict]]:
    qualifying: list[dict] = []
    held: list[dict] = []
    for c in candidates:
        kept = {m: ev for m, ev in c["evidence"].items() if len(ev) >= n}
        if kept:
            q = dict(c)
            q["evidence"] = kept
            q["marker_affinity"] = sorted(kept.keys())
            qualifying.append(q)
        else:
            held.append(c)
    return qualifying, held
```

- [ ] **Step 4: Run test to verify it passes**

Run: `env TMPDIR=$PWD/.pytest-tmp python3 -m pytest tests/test_practitioner_discovery.py -k threshold -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/practitioner_discovery/threshold.py tests/test_practitioner_discovery.py
git commit -m "feat(discovery): N-evidence threshold gate (qualifying/held)"
```

---

## Task 5: Build registry records + merge with provenance

**Files:**
- Create: `scripts/practitioner_discovery/ingest.py`
- Test: `tests/test_practitioner_discovery.py` (append)

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_practitioner_discovery.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `env TMPDIR=$PWD/.pytest-tmp python3 -m pytest tests/test_practitioner_discovery.py -k "registry_record or merge" -q`
Expected: FAIL with `ModuleNotFoundError` / `AttributeError`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/practitioner_discovery/ingest.py
"""Turn qualifying candidates into practitioner_registry.json records and merge
them in. Auto-discovered records are tagged + conservatively graded so a later
audit can demote or remove them with a single filter."""
from __future__ import annotations


def to_registry_record(candidate: dict) -> dict:
    return {
        "id": candidate["entity_key"],
        "canonical_name": candidate["display_name"],
        "aliases": [candidate["display_name"]] if candidate["display_name"] else [],
        "entity_type": candidate.get("entity_type", "channel"),
        "languages": ["en"],
        "paradigm_affinity": ["MO"],
        "source_tier": "C",
        "source_grade": "E2",
        "marker_affinity": list(candidate["marker_affinity"]),
        "surfaces": candidate["surfaces"],
        "discovery_provenance": [
            {"marker": m, "evidence_count": len(ev), "evidence": [e["ref"] for e in ev]}
            for m, ev in candidate["evidence"].items()
        ],
        "commercial_interests": [],
    }


def merge_into_registry(registry: dict, records: list[dict]) -> dict:
    registry.setdefault("practitioners", [])
    by_id = {p["id"]: p for p in registry["practitioners"]}
    for r in records:
        existing = by_id.get(r["id"])
        if existing:
            existing["marker_affinity"] = sorted(
                set(existing.get("marker_affinity", [])) | set(r["marker_affinity"]))
            existing.setdefault("discovery_provenance", [])
            existing["discovery_provenance"].extend(r["discovery_provenance"])
        else:
            registry["practitioners"].append(r)
            by_id[r["id"]] = r
    return registry
```

- [ ] **Step 4: Run test to verify it passes**

Run: `env TMPDIR=$PWD/.pytest-tmp python3 -m pytest tests/test_practitioner_discovery.py -k "registry_record or merge" -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/practitioner_discovery/ingest.py tests/test_practitioner_discovery.py
git commit -m "feat(discovery): build + merge registry records with evidence provenance"
```

---

## Task 6: Audit report

**Files:**
- Create: `scripts/practitioner_discovery/audit.py`
- Test: `tests/test_practitioner_discovery.py` (append)

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_practitioner_discovery.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `env TMPDIR=$PWD/.pytest-tmp python3 -m pytest tests/test_practitioner_discovery.py -k audit -q`
Expected: FAIL with `ModuleNotFoundError` / `AttributeError`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/practitioner_discovery/audit.py
"""Human-readable audit report for one discovery run."""
from __future__ import annotations


def render_report(qualifying: list[dict], held: list[dict], n: int) -> str:
    lines = [f"# Practitioner Discovery Audit (threshold N={n})", ""]
    lines.append(f"Qualifying: {len(qualifying)} | Held: {len(held)}")
    lines.append("")
    lines.append("## Ingested practitioners")
    for q in qualifying:
        markers = ", ".join(f"{m} ({len(q['evidence'][m])})" for m in q["marker_affinity"])
        lines.append(f"- **{q['display_name']}** (`{q['entity_key']}`) — {markers}")
    lines.append("")
    lines.append("## Held (below threshold, not ingested)")
    for h in held:
        markers = ", ".join(f"{m} ({len(ev)})" for m, ev in h["evidence"].items())
        lines.append(f"- {h['display_name']} (`{h['entity_key']}`) — {markers}")
    return "\n".join(lines) + "\n"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `env TMPDIR=$PWD/.pytest-tmp python3 -m pytest tests/test_practitioner_discovery.py -k audit -q`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/practitioner_discovery/audit.py tests/test_practitioner_discovery.py
git commit -m "feat(discovery): audit report renderer"
```

---

## Task 7: Orchestrator (`run.py`) + end-to-end run

**Files:**
- Create: `scripts/practitioner_discovery/run.py`
- Test: `tests/test_practitioner_discovery.py` (append)

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_practitioner_discovery.py
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
    assert result["summary"]["qualifying"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `env TMPDIR=$PWD/.pytest-tmp python3 -m pytest tests/test_practitioner_discovery.py -k run_pipeline -q`
Expected: FAIL with `ModuleNotFoundError` / `AttributeError`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/practitioner_discovery/run.py
"""Orchestrate the discovery pipeline for a list of markers (inventory source).

Pure core (`run_pipeline`) returns data; the CLI (`main`) loads real files,
writes outputs to output/practitioner-discovery/<run-id>/, and persists the
updated registry.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.practitioner_discovery import (
    audit, extract_candidates, harvest_inventory, ingest, terms, threshold,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = PROJECT_ROOT / "input" / "practitioner_registry.json"
OUTPUT_ROOT = PROJECT_ROOT / "output" / "practitioner-discovery"


def run_pipeline(markers, registry, policy, inventory_dir, n=2):
    terms_by_marker = {m: terms.marker_terms(m, policy) for m in markers}
    terms_by_marker = {m: t for m, t in terms_by_marker.items() if t}
    signals = harvest_inventory.scan_inventory(terms_by_marker, inventory_dir=inventory_dir)
    candidates = extract_candidates.extract_candidates(signals, registry)
    qualifying, held = threshold.apply_threshold(candidates, n=n)
    records = [ingest.to_registry_record(q) for q in qualifying]
    merged = ingest.merge_into_registry(registry, records)
    audit_md = audit.render_report(qualifying, held, n=n)
    return {
        "registry": merged,
        "qualifying": qualifying,
        "held": held,
        "audit_md": audit_md,
        "summary": {"signals": len(signals), "candidates": len(candidates),
                    "qualifying": len(qualifying), "held": len(held)},
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Practitioner gap discovery (inventory source)")
    parser.add_argument("markers", nargs="+", help="marker slugs to discover for")
    parser.add_argument("--run-id", required=True, help="output subdir under output/practitioner-discovery/")
    parser.add_argument("-n", "--threshold", type=int, default=2)
    parser.add_argument("--write-registry", action="store_true",
                        help="persist the merged registry back to practitioner_registry.json")
    args = parser.parse_args(argv)

    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    policy = terms.load_policy()
    result = run_pipeline(args.markers, registry, policy,
                          inventory_dir=harvest_inventory.INVENTORY_DIR, n=args.threshold)

    out_dir = OUTPUT_ROOT / args.run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "qualifying.json").write_text(json.dumps(result["qualifying"], indent=2), encoding="utf-8")
    (out_dir / "held.json").write_text(json.dumps(result["held"], indent=2), encoding="utf-8")
    (out_dir / "audit.md").write_text(result["audit_md"], encoding="utf-8")
    print(json.dumps(result["summary"]))

    if args.write_registry:
        REGISTRY_PATH.write_text(json.dumps(result["registry"], indent=2), encoding="utf-8")
        print(f"registry updated: {REGISTRY_PATH}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `env TMPDIR=$PWD/.pytest-tmp python3 -m pytest tests/test_practitioner_discovery.py -q`
Expected: PASS (all tests green)

- [ ] **Step 5: Commit**

```bash
git add scripts/practitioner_discovery/run.py tests/test_practitioner_discovery.py
git commit -m "feat(discovery): inventory-source pipeline orchestrator + CLI"
```

---

## Task 8: Pilot dry-run on real hormone markers (no registry write)

**Files:** none (verification task)

- [ ] **Step 1: Run discovery on two mainstream hormone markers, inspect output**

Run:
```bash
env TMPDIR=$PWD/.pytest-tmp python3 -m scripts.practitioner_discovery.run \
  total-testosterone cortisol-am --run-id pilot-dryrun -n 2
```
Expected: prints a JSON summary; writes `output/practitioner-discovery/pilot-dryrun/{qualifying,held}.json` + `audit.md`. **No registry write** (no `--write-registry`).

- [ ] **Step 2: Manually inspect the audit**

Run: `cat output/practitioner-discovery/pilot-dryrun/audit.md`
Expected: a list of channels with ≥2 testosterone/cortisol videos that are NOT already in the registry. Sanity-check that names look like real practitioners/channels, not garbage.

- [ ] **Step 3: STOP for human review**

Per the spec's auto-ingest-with-audit decision, a human eyeballs this first pilot before any `--write-registry`. Do not proceed to Task 9 until the dry-run candidates look correct. If they are noisy, raise N or narrow terms and re-run.

---

## Task 9: Ingest + regenerate canonical + re-assemble briefs

**Files:**
- Modify (data, via scripts): `input/practitioner_registry.json`, `input/practitioners/*`, `input/hermes-briefs/wave-*/*.yaml`

- [ ] **Step 1: Run the full hormones pilot with registry write**

Run:
```bash
env TMPDIR=$PWD/.pytest-tmp python3 -m scripts.practitioner_discovery.run \
  total-testosterone free-testosterone bio-t dht shbg cortisol-am cortisol-pm \
  dhea dhea-s estradiol progesterone lh fsh prolactin amh \
  --run-id hormones-pilot -n 2 --write-registry
```
Expected: summary JSON; registry updated with new `channel:*` practitioners carrying `marker_affinity` + `discovery_provenance`.

- [ ] **Step 2: Sync the canonical practitioner files from the updated registry**

Run: `python3 scripts/build_canonical_practitioner_sources.py`
Expected: `input/practitioners/{practitioners,practitioner-marker-affinity,practitioner-web-resources,practitioner-social-resources}.json` regenerated.

- [ ] **Step 3: Re-assemble the affected wave(s)**

Run: `python3 scripts/assemble_hermes_briefs.py --wave wave-2 --collect-sources`
(Repeat for any wave whose hormone markers changed; bio-t is wave-2.)
Expected: briefs regenerated.

- [ ] **Step 4: Verify a previously-empty brief is now populated**

Run:
```bash
python3 -c "import yaml; d=yaml.safe_load(open('input/hermes-briefs/wave-2/bio-t.yaml')); print('practitioners:', len(d['recommended_practitioner_ids'])); print('sources:', len(d['recommended_source_urls']))"
```
Expected: practitioners > 0 (was 0) if discovery found testosterone practitioners with bio-t evidence.

- [ ] **Step 5: Run acceptance + full test suite**

Run:
```bash
env TMPDIR=$PWD/.pytest-tmp python3 -m pytest tests/test_practitioner_discovery.py -q
python3 code/acceptance/check_hermes_briefs.py --wave wave-2
```
Expected: tests pass; acceptance passes.

- [ ] **Step 6: Commit**

```bash
git add scripts/practitioner_discovery/ input/practitioner_registry.json input/practitioners/ input/hermes-briefs/ output/practitioner-discovery/
git commit -m "feat(discovery): hormones pilot — ingest discovered practitioners + re-assemble briefs"
```

---

## Task 10 (additive, after pilot validated): fresh YouTube/podcast search

**Files:**
- Create: `scripts/practitioner_discovery/harvest_fresh.py`
- Test: `tests/test_practitioner_discovery.py` (append)

Adds the second/third Stage-1 sources so discovery reaches channels not in the local inventory. `harvest_fresh.scan_fresh(terms_by_marker)` must return signals in the **same shape** as `harvest_inventory.scan_inventory` (so `extract_candidates` consumes them unchanged), with `"source": "youtube"` or `"source": "podcast"`. It wraps the metabolicum-research `scripts/social_pipeline` YouTube/podcast harvesters.

- [ ] **Step 1: Write the failing test** (with a fake harvester injected — no network)

```python
# append to tests/test_practitioner_discovery.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `env TMPDIR=$PWD/.pytest-tmp python3 -m pytest tests/test_practitioner_discovery.py -k scan_fresh -q`
Expected: FAIL with `ModuleNotFoundError` / `AttributeError`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/practitioner_discovery/harvest_fresh.py
"""Fresh YouTube/podcast search via the metabolicum-research social_pipeline,
normalized to the same signal shape as the inventory scan.

The default harvester is injected lazily so tests run with no network and the
cross-project import only happens when actually used.
"""
from __future__ import annotations

import re


def _first_match(text: str, terms: list[str]) -> str | None:
    for term in terms:
        if re.search(r"\b" + re.escape(term) + r"\b", text, re.IGNORECASE):
            return term
    return None


def scan_fresh(terms_by_marker: dict[str, list[str]], harvester, source: str = "youtube") -> list[dict]:
    signals: list[dict] = []
    for marker, marker_terms in terms_by_marker.items():
        for v in harvester(marker, marker_terms) or []:
            title = v.get("title", "") or ""
            desc = v.get("description", "") or ""
            term = _first_match(title, marker_terms) or _first_match(desc, marker_terms)
            if not term:
                continue
            signals.append({
                "source": source,
                "marker": marker,
                "video_id": v.get("video_id", ""),
                "channel_id": v.get("channel_id", ""),
                "channel": v.get("channel", ""),
                "title": title,
                "url": v.get("url", ""),
                "term": term,
                "where": "title" if _first_match(title, marker_terms) else "description",
            })
    return signals
```

- [ ] **Step 4: Run test to verify it passes**

Run: `env TMPDIR=$PWD/.pytest-tmp python3 -m pytest tests/test_practitioner_discovery.py -k scan_fresh -q`
Expected: PASS

- [ ] **Step 5: Wire into `run.py`** — add an optional `fresh_signals` source to `run_pipeline` (concatenate inventory + fresh signals before `extract_candidates`), and a `--with-fresh` CLI flag that imports the real social_pipeline harvester. Keep the inventory-only path the default.

```python
# in run.py run_pipeline signature: add fresh_signals=None
    signals = harvest_inventory.scan_inventory(terms_by_marker, inventory_dir=inventory_dir)
    if fresh_signals:
        signals = signals + fresh_signals
```

- [ ] **Step 6: Commit**

```bash
git add scripts/practitioner_discovery/harvest_fresh.py scripts/practitioner_discovery/run.py tests/test_practitioner_discovery.py
git commit -m "feat(discovery): fresh YouTube/podcast search source (additive)"
```

---

## Expansion (post-pilot)

Once hormones is validated, run the same pipeline for the next 0-cohort category by changing only the marker list (kidney-function, then electrolytes, then the rest). No code change required for additional categories.
