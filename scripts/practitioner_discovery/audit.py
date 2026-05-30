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
