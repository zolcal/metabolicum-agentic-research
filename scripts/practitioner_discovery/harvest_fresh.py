"""Fresh YouTube/podcast search via an injected harvester, normalized to the
same signal shape as ``harvest_inventory.scan_inventory``.

The harvester is injected (a callable ``harvester(marker, terms) -> list[dict]``)
so tests run with no network and the cross-project social_pipeline import only
happens when the controller wires in the real one. Phrase matching uses the
shared ``match.first_match`` lookaround matcher (not ``\\b``) so it behaves
identically to the inventory scan.
"""
from __future__ import annotations

import json
from pathlib import Path

from scripts.practitioner_discovery.match import first_match


def video_from_signal(signal: dict) -> dict:
    """Map a social_pipeline ``SocialSignal`` dict (as written by its harvesters:
    ``{source, source_id, url, title, text, author, raw}``) to the video dict
    shape ``scan_fresh`` expects. ``channel_id`` lives in the signal's ``raw``."""
    raw = signal.get("raw") or {}
    return {
        "video_id": raw.get("video_id") or signal.get("source_id", "") or "",
        "channel_id": raw.get("channel_id") or raw.get("channelId", "") or "",
        "channel": signal.get("author", "") or raw.get("channel", "") or "",
        "title": signal.get("title", "") or "",
        "description": signal.get("text", "") or "",
        "url": signal.get("url", "") or "",
    }


def signals_dir_harvester(signals_dir):
    """Build a ``harvester(marker, terms)`` that reads pre-harvested social_pipeline
    signals from ``<signals_dir>/<marker>.json`` (a list of SocialSignal dicts, or
    ``{"signals": [...]}``). Decouples the live API harvest (run in the
    metabolicum-research project with a YouTube key) from this offline pipeline."""
    base = Path(signals_dir)

    def harvester(marker: str, terms: list[str]) -> list[dict]:
        f = base / f"{marker}.json"
        if not f.exists():
            return []
        data = json.loads(f.read_text(encoding="utf-8"))
        sigs = data.get("signals", []) if isinstance(data, dict) else data
        return [video_from_signal(s) for s in sigs]

    return harvester


def scan_fresh(terms_by_marker: dict[str, list[str]], harvester,
               source: str = "youtube") -> list[dict]:
    signals: list[dict] = []
    for marker, marker_terms in terms_by_marker.items():
        for v in harvester(marker, marker_terms) or []:
            title = v.get("title", "") or ""
            desc = v.get("description", "") or ""
            # Compute the title match once and reuse it to set `where`,
            # mirroring harvest_inventory (avoids a double-match call).
            term = first_match(title, marker_terms)
            where = "title"
            if not term:
                term = first_match(desc, marker_terms)
                where = "description"
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
                "where": where,
            })
    return signals
