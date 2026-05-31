"""Fresh YouTube/podcast search via an injected harvester, normalized to the
same signal shape as ``harvest_inventory.scan_inventory``.

The harvester is injected (a callable ``harvester(marker, terms) -> list[dict]``)
so tests run with no network and the cross-project social_pipeline import only
happens when the controller wires in the real one. Phrase matching uses the
shared ``match.first_match`` lookaround matcher (not ``\\b``) so it behaves
identically to the inventory scan.
"""
from __future__ import annotations

from scripts.practitioner_discovery.match import first_match


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
