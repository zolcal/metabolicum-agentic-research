"""Canonicalization helpers for Hermes acceptance artifacts."""

from __future__ import annotations

import json
import re
from typing import Any

_ORDERLESS_ARRAY_KEYS = {"applies_to_markers", "rejection_codes"}
_WHITESPACE_KEYS = {"verbatim_quote", "translated_quote"}


def normalize_whitespace(value: str) -> str:
    """Collapse all whitespace to single spaces and trim ends."""
    return re.sub(r"\s+", " ", value).strip()


def canonicalize(value: Any, *, key: str | None = None) -> Any:
    """Return a deterministic representation for acceptance comparisons.

    Rules are intentionally narrow:
    - JSON object keys are sorted by `canonical_json`.
    - Arrays whose order is not semantically meaningful are sorted only for known keys.
    - Verbatim quote fields are whitespace-normalized but not reworded.
    """
    if isinstance(value, dict):
        return {k: canonicalize(v, key=k) for k, v in sorted(value.items())}
    if isinstance(value, list):
        items = [canonicalize(v, key=key) for v in value]
        if key in _ORDERLESS_ARRAY_KEYS:
            return sorted(items, key=lambda item: json.dumps(item, sort_keys=True, ensure_ascii=False))
        return items
    if isinstance(value, str) and key in _WHITESPACE_KEYS:
        return normalize_whitespace(value)
    return value


def canonical_json(value: Any) -> str:
    """Serialize a value after canonicalization."""
    return json.dumps(canonicalize(value), sort_keys=True, ensure_ascii=False, separators=(",", ":"))
