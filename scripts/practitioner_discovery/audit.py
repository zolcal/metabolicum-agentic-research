"""Human-readable audit report for one discovery run."""
from __future__ import annotations


def _markers_line(q: dict) -> str:
    return ", ".join(f"{m} ({len(q['evidence'][m])})" for m in q["marker_affinity"])


def render_report(new_qualifying: list[dict], enriched: list[dict],
                  held: list[dict], n: int) -> str:
    lines = [f"# Practitioner Discovery Audit (threshold N={n})", ""]
    lines.append(
        f"New: {len(new_qualifying)} | Enriched: {len(enriched)} | Held: {len(held)}")
    lines.append("")
    lines.append("## Newly discovered practitioners")
    for q in new_qualifying:
        lines.append(f"- **{q['display_name']}** (`{q['entity_key']}`) — {_markers_line(q)}")
    lines.append("")
    lines.append("## Enriched existing practitioners")
    for q in enriched:
        lines.append(f"- **{q['display_name']}** (`{q['entity_key']}`) — {_markers_line(q)}")
    lines.append("")
    lines.append("## Held (below threshold, not ingested)")
    for h in held:
        markers = ", ".join(f"{m} ({len(ev)})" for m, ev in h["evidence"].items())
        lines.append(f"- {h['display_name']} (`{h['entity_key']}`) — {markers}")
    return "\n".join(lines) + "\n"
