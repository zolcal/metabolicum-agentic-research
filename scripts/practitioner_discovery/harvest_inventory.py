"""Scan the local YouTube video inventory for marker phrase matches.

Free, no API. Non-word-boundary phrase matching (no term splitting) over each
video's title and description. Uses non-word lookarounds rather than ``\b`` so
terms whose own edges are non-word characters (e.g. ``cortisol (am)``, ``lp(a)``)
still match, while substring-in-word matches are still rejected.
"""
from __future__ import annotations

import json
from pathlib import Path

from scripts.practitioner_discovery.match import first_match

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INVENTORY_DIR = PROJECT_ROOT / "input" / "youtube-video-inventory" / "videos"


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
            term = first_match(title, marker_terms)
            where = "title"
            if not term:
                term = first_match(desc, marker_terms)
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
