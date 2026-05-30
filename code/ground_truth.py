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
ENRICH = ROOT / "input" / "mo-category-enrichment.yaml"   # local multi-category overlay (ahead of prod)
SCOPE = ROOT / "input" / "mo-scope-policy.yaml"


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
def _enrichment() -> dict[str, set]:
    """Local multi-category overlay (the curated cross-refs proposed to metasync),
    applied AHEAD of prod so the agentic input is correct now. Reconciled when prod
    applies the migration and build_ground_truth re-syncs."""
    if not ENRICH.exists():
        return {}
    d = yaml.safe_load(ENRICH.read_text()) or {}
    return {k: set(v) for k, v in (d.get("enrichment") or {}).items()}


@functools.lru_cache(maxsize=1)
def _marker_cats() -> dict[str, list[str]]:
    enr = _enrichment()
    return {mm["slug"]: sorted(set(mm.get("categories") or []) | enr.get(mm["slug"], set()))
            for mm in load()["markers"]}


def categories_for(slug: str) -> list[str]:
    """Full category set for a marker = ground-truth categories ∪ enrichment overlay."""
    canon = resolve_slug(slug) or slug
    return _marker_cats().get(canon, [])


@functools.lru_cache(maxsize=1)
def _in_scope_categories() -> set:
    if not SCOPE.exists():
        return set()
    d = yaml.safe_load(SCOPE.read_text()) or {}
    return {c["slug"] for c in d.get("categories", []) if c.get("in_scope")}


def in_scope(slug: str) -> bool:
    """A marker is in MO research scope iff ANY of its (enriched) categories is in-scope."""
    return bool(set(categories_for(slug)) & _in_scope_categories())


# QA-confirmed false exclusions (excluded-markers assessment 2026-05-30): MO-supported
# despite an out-of-scope primary category.
_FALSE_EXCLUSIONS = {
    "nlr": "neutrophil-lymphocyte ratio — systemic-inflammation marker tracked in MO",
    "plr": "platelet-lymphocyte ratio — systemic-inflammation marker tracked in MO",
    "sii": "systemic immune-inflammation index — used by MO clinicians",
    "magnesium-serum": "magnesium actively optimized by MO practitioners",
    "rbc-magnesium": "RBC magnesium — functional tissue-Mg status, MO-optimized",
    "urine-iodine": "iodine micronutrient — functional/thyroid optimization target",
    "calprotectin": "fecal calprotectin — targeted low by functional-medicine",
    "cortisol-saliva": "salivary cortisol — HPA-axis / cortisol-awakening optimization",
}


def mo_status(slug: str) -> tuple[bool, str]:
    """Binary MO-paradigm support determination + one-line rationale (overridable).

    Supported iff a ground-truth category is MO-in-scope, or the marker is a QA-confirmed
    false-exclusion. The brief carries this; the Hermes pipeline writes it to the DB.
    """
    canon = resolve_slug(slug) or slug
    cats = set(next((m.get("categories") or [] for m in load()["markers"] if m["slug"] == canon), []))
    hit = sorted(cats & _in_scope_categories())
    if hit:
        return True, f"MO-relevant: category '{hit[0]}'"
    if canon in _FALSE_EXCLUSIONS:
        return True, f"MO-relevant (false-exclusion corrected): {_FALSE_EXCLUSIONS[canon]}"
    pc = next((m.get("primary_category") for m in load()["markers"] if m["slug"] == canon), None) or "uncategorized"
    return False, f"no MO dimension — category '{pc}' (taxonomy assessment 2026-05-30)"


@functools.lru_cache(maxsize=1)
def markers_by_category() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for slug, cats in _marker_cats().items():
        for c in cats:
            out.setdefault(c, []).append(slug)
    return {k: sorted(v) for k, v in out.items()}
