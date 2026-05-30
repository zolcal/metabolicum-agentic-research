"""THE ground-truth accessor.

Every derivative (marker_categories, briefs, slug guard, registry reconciliation)
reads marker identity, categories, and slug resolution from HERE — never from the
DB directly and never from a forked copy. The document is built by
scripts/build_ground_truth.py from the metasync production DB and kept in harmony
by code/acceptance/check_ground_truth_harmony.py.
"""
from __future__ import annotations

import functools
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "input" / "ground-truth" / "metabolicum-marker-ground-truth.v1.yaml"


@functools.lru_cache(maxsize=1)
def load() -> dict:
    return yaml.safe_load(DOC.read_text())


@functools.lru_cache(maxsize=1)
def _index():
    d = load()
    canonical = {m["slug"] for m in d["markers"]}
    redirects = dict(d.get("slug_redirects") or {})
    alias2canon: dict[str, str] = {}
    for m in d["markers"]:
        for _typ, vals in (m.get("aliases") or {}).items():
            for v in vals:
                alias2canon.setdefault(v.lower(), m["slug"])
    return canonical, redirects, alias2canon


def resolve_slug(slug: str | None) -> str | None:
    """Resolve any slug / variant / alias to its canonical marker slug, or None.

    Order: explicit redirect (old_slug→new_slug, from production marker_slug_aliases)
    → canonical marker → alias (any type). This IS the slug-arbitration layer.
    """
    if not slug:
        return None
    canonical, redirects, alias2canon = _index()
    s = redirects.get(slug.strip(), slug.strip())
    if s in canonical:
        return s
    hit = alias2canon.get(s.lower())
    if hit:
        return redirects.get(hit, hit)
    return None


def is_canonical(slug: str) -> bool:
    return slug in _index()[0]


def categories() -> list[dict]:
    return load()["categories"]


def markers() -> list[dict]:
    return load()["markers"]


@functools.lru_cache(maxsize=1)
def markers_by_category() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for m in load()["markers"]:
        for c in (m.get("categories") or []):
            out.setdefault(c, []).append(m["slug"])
    return {k: sorted(v) for k, v in out.items()}
