"""Stage-B MO content writer.

Generates the MO-specific prose sections (`interpretation`, `limitations`)
grounded in the council-approved MO claims + their sources, for injection into
assembly.build_marker_export via its `extra_sections` hook. The generic sections
(why_matters, mechanism) are deliberately NOT produced here — they are
marker-level content reused from the SM/RC pipelines.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROMPT_PATH = PROJECT_ROOT / "prompts" / "06-mo-content-writer.md"

_SECTIONS = ("interpretation", "limitations")  # section_order 2, 3 (after evidence_badge)


def _content_hash(content: dict) -> str:
    return hashlib.sha256(json.dumps(content, sort_keys=True, default=str).encode()).hexdigest()


def build_mo_content_sections(
    marker: str,
    claims: list[dict],
    sm_rows: list[dict],
    *,
    role_caller: Any,
    marker_type: str = "marker",
    language: str = "en",
) -> list[dict]:
    """Return the MO-specific prose content sections (0-2 rows). One LLM call.

    `role_caller(role, system, user) -> dict` performs the LLM call (injected, so
    this is testable without a live model). Returns [] if no claims or the model
    yields no usable body — never fabricates a section.
    """
    if not claims:
        return []
    system = PROMPT_PATH.read_text(encoding="utf-8")
    user = {
        "marker": marker,
        "mo_claims": [
            {k: c.get(k) for k in ("verbatim_quote", "target_value", "target_range_low",
                                   "target_range_high", "units", "direction",
                                   "speaker_or_author", "source_id")}
            for c in claims
        ],
        "sm_reference_rows": sm_rows or [],
    }
    out = role_caller("content_writer", system, user) or {}

    sections = []
    for order, section_type in enumerate(_SECTIONS, start=2):
        block = out.get(section_type) or {}
        body = (block.get("body") or "").strip()
        if not body:
            continue  # no usable prose -> emit nothing (never fabricate)
        content = {
            "title": block.get("title") or section_type.capitalize(),
            "body": body,
            "citations": block.get("citations") or [],
        }
        sections.append({
            "marker_slug": marker, "marker_type": marker_type, "language": language,
            "section_type": section_type, "section_order": order,
            "paradigm": "metabolic-optimization", "content": content,
            "source_type": "pipeline", "evidence_grade": None, "source_url": None,
            "content_hash": _content_hash(content), "status": "draft", "version": 1,
        })
    return sections
