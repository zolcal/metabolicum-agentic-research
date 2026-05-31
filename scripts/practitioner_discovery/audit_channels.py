"""Audit registry YouTube channel IDs against the local video inventory.

Free, no API: the inventory pairs every channel_id with the real channel name,
so a registry practitioner whose channel_id appears in the inventory under a
clearly different name is a mismatched mapping. camelCase handles
(KenDBerryMD, DavidPerlmutterMD) are split before comparison to avoid false
positives.

Usage: python -m scripts.practitioner_discovery.audit_channels
"""
from __future__ import annotations

import glob
import json
import re
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INVENTORY_DIR = PROJECT_ROOT / "input" / "youtube-video-inventory" / "videos"
REGISTRY = PROJECT_ROOT / "input" / "practitioner_registry.json"

_STOP = {"dr", "md", "phd", "the", "mph", "dc", "health", "with", "and",
         "official", "tv", "show", "podcast"}


def _tokens(text: str) -> set[str]:
    # split on non-alphanumeric AND camelCase boundaries
    spaced = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)
    return {t for t in re.split(r"[^a-z0-9]+", spaced.lower()) if len(t) >= 3 and t not in _STOP}


def inventory_channel_names(inventory_dir: Path = INVENTORY_DIR) -> dict[str, set[str]]:
    names: dict[str, set[str]] = defaultdict(set)
    for f in glob.glob(str(inventory_dir / "*.json")):
        try:
            v = json.loads(Path(f).read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        cid, nm = v.get("channel_id"), v.get("channel")
        if cid and nm:
            names[cid].add(nm)
    return names


def channel_id_of(practitioner: dict) -> str | None:
    for s in practitioner.get("surfaces", []) or []:
        if s.get("channel_id"):
            return s["channel_id"]
        m = re.search(r"/channel/([A-Za-z0-9_-]+)", str(s.get("handle_or_url", "")))
        if m:
            return m.group(1)
    return None


def audit(registry: dict, inv_names: dict[str, set[str]]) -> list[dict]:
    """Return one row per practitioner with a youtube channel: verdict in
    {ok, mismatch, unverifiable}."""
    rows = []
    for p in registry.get("practitioners", []):
        cid = channel_id_of(p)
        if not cid:
            continue
        names = inv_names.get(cid)
        if not names:
            rows.append({"id": p["id"], "verdict": "unverifiable", "channel_id": cid})
            continue
        ptok = _tokens(p.get("canonical_name", ""))
        for a in p.get("aliases", []) or []:
            ptok |= _tokens(a)
        verdict = "ok" if any(_tokens(n) & ptok for n in names) else "mismatch"
        rows.append({"id": p["id"], "verdict": verdict, "channel_id": cid,
                     "inventory_names": sorted(names)})
    return rows


def main() -> None:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    rows = audit(registry, inventory_channel_names())
    mism = [r for r in rows if r["verdict"] == "mismatch"]
    for r in mism:
        print(f"MISMATCH {r['id']:30} channel={r['channel_id']} -> {', '.join(r['inventory_names'])}")
    counts = defaultdict(int)
    for r in rows:
        counts[r["verdict"]] += 1
    print(f"\nok={counts['ok']} mismatch={counts['mismatch']} unverifiable={counts['unverifiable']}")


if __name__ == "__main__":
    main()
