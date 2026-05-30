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


def _registry_channel_owners(registry: dict) -> dict[str, dict]:
    """Map each registered channel_id (surface field AND /channel/<id> URL form)
    to the full practitioner record that owns it."""
    owners: dict[str, dict] = {}
    for p in registry.get("practitioners", []):
        for s in p.get("surfaces", []) or []:
            cid = s.get("channel_id")
            if cid:
                owners.setdefault(cid, p)
            m = re.search(r"/channel/([A-Za-z0-9_-]+)", str(s.get("handle_or_url", "")))
            if m:
                owners.setdefault(m.group(1), p)
    return owners


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


def extract_enrichments(signals: list[dict], registry: dict) -> list[dict]:
    """Group signals whose channel belongs to an already-registered practitioner,
    keyed by the existing practitioner's id, so their evidence can ADD markers to
    the existing marker_affinity. Unregistered channels are ignored here (they are
    handled by extract_candidates), so the two functions partition the signals by
    registry membership."""
    owners = _registry_channel_owners(registry)
    grouped: dict[str, dict] = {}
    evidence: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for s in signals:
        cid = s.get("channel_id") or ""
        owner = owners.get(cid)
        if not owner:
            continue
        pid = owner["id"]
        grouped.setdefault(pid, owner)
        evidence[pid][s["marker"]].append({
            "source": s["source"], "ref": f"yt:{s['video_id']}",
            "title": s["title"], "term": s["term"], "where": s["where"],
        })
    out: list[dict] = []
    for pid, owner in grouped.items():
        out.append({
            "entity_key": pid,
            "channel_id": "",
            "display_name": owner.get("canonical_name", ""),
            "entity_type": owner.get("entity_type", "person"),
            "surfaces": [],
            "evidence": {m: ev for m, ev in evidence[pid].items()},
        })
    return out
