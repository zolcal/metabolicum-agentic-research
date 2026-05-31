"""Shared marker-phrase matcher for the discovery harvesters.

Non-word-boundary phrase matching (no term splitting). Uses non-word
lookarounds rather than ``\\b`` so terms whose own edges are non-word
characters (e.g. ``cortisol (am)``, ``lp(a)``) still match, while
substring-in-word matches are still rejected. Both ``harvest_inventory`` and
``harvest_fresh`` import this so the matcher lives in exactly one place.
"""
from __future__ import annotations

import re


def first_match(text: str, terms: list[str]) -> str | None:
    for term in terms:
        if re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", text, re.IGNORECASE):
            return term
    return None
