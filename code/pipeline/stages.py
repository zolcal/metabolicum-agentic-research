"""Stage 2 extraction chain: extractor -> tagger -> structurer.

Single source of truth for the three LLM sub-stages that transform a raw
source transcript into structured MarkerRecommendation objects.

Imported by:
  - code/acceptance/run_acceptance.py  (acceptance harness)
  - code/pipeline/ingest.py            (production ingestion pipeline)

Functions preserve the original acceptance-harness signatures so existing
tests remain valid without modification.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore


# ── Path constants ────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCHEMAS_DIR = PROJECT_ROOT / "code" / "schemas"
PROMPTS_DIR = PROJECT_ROOT / "prompts"
GLOSSARY_PATH = PROJECT_ROOT / "input" / "marker_glossary.json"


# ── Helpers ───────────────────────────────────────────────────────────────

def load_schema(name: str) -> dict:
    """Load a JSON schema from code/schemas/."""
    return json.loads((SCHEMAS_DIR / name).read_text())


def load_prompt(name: str) -> str:
    """Load a prompt template from prompts/."""
    return (PROMPTS_DIR / name).read_text()


# ── Core LLM call ────────────────────────────────────────────────────────

def llm_call(
    client: OpenAI,
    system: str,
    user: str,
    schema: dict | None = None,
    model: str = "qwen",
    max_tokens: int = 4096,
    seed: int = 42,
) -> dict[str, Any]:
    """Single LLM call with optional JSON Schema constrained decoding.

    Returns a dict with keys:
      content          - parsed JSON dict/list from the model
      raw              - the stripped text before JSON parse
      elapsed_s        - wall-clock seconds
      input_tokens     - prompt token count (may be None)
      output_tokens    - completion token count (may be None)
      finish_reason    - stop/length/content_filter
      model            - model id echoed back

    Handles:
      - Qwen <think>...</think> tag stripping
      - Markdown ```json ... ``` fence extraction
      - Empty content detection
    """
    kwargs: dict[str, Any] = dict(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0,
        seed=seed,
        max_tokens=max_tokens,
    )
    if schema:
        kwargs["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": "output", "strict": True, "schema": schema},
        }
    else:
        kwargs["response_format"] = {"type": "json_object"}

    t0 = time.time()
    resp = client.chat.completions.create(**kwargs)
    elapsed = time.time() - t0
    content = resp.choices[0].message.content or ""
    usage = resp.usage

    # Strip Qwen thinking tags if present
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
    # Extract JSON from markdown fences if present
    fence = re.search(r"```(?:json)?\s*\n(.*?)```", content, re.DOTALL)
    if fence:
        content = fence.group(1).strip()
    if not content:
        raise ValueError(
            f"LLM returned empty content after stripping think tags. "
            f"finish_reason={resp.choices[0].finish_reason}"
        )

    return {
        "content": json.loads(content),
        "raw": content,
        "elapsed_s": round(elapsed, 2),
        "input_tokens": usage.prompt_tokens if usage else None,
        "output_tokens": usage.completion_tokens if usage else None,
        "finish_reason": resp.choices[0].finish_reason,
        "model": resp.model,
    }


# ── Stage 2a: Content Extractor ──────────────────────────────────────────

def run_extractor(client: OpenAI, fixture: dict, seed: int = 42, model: str = "qwen") -> dict[str, Any]:
    """Extract verbatim claims from a source transcript.

    Args:
        client: OpenAI-compatible client.
        fixture: Source fixture dict with transcript_text, source_id, etc.
        seed: Random seed for determinism.
        model: Model name to use (default: "qwen" for local, "qwen3.7-max" for DashScope).

    Returns:
        LLM call result dict; content has {"claims": [ExtractedRawClaim, ...]}.
    """
    system = load_prompt("01-content-extractor.md")
    user = json.dumps({
        "source_transcript": fixture["transcript_text"],
        "source_metadata": {
            "source_id": fixture["source_id"],
            "source_url": fixture["source_url"],
            "source_type": fixture["source_type"],
            "platform": fixture["platform"],
            "speaker_or_author": fixture["speaker_or_author"],
            "retrieved_at": fixture["retrieved_at"],
            "source_language": fixture["source_language"],
        }
    }, indent=2)
    raw_schema = load_schema("extracted_raw_claim.schema.json")
    wrapper = {
        "type": "object",
        "properties": {"claims": {"type": "array", "items": raw_schema}},
        "required": ["claims"],
        "additionalProperties": False,
    }
    result = llm_call(client, system, user, schema=wrapper, seed=seed, model=model)
    
    # Handle case where model returns list directly instead of {"claims": [...]}
    content = result["content"]
    if isinstance(content, list):
        result["content"] = {"claims": content}
    
    # Fix model identity hallucination: override extraction_model with actual model name
    # LLMs often hallucinate "gpt-4o" or other models when the schema says "<injected>"
    claims = result["content"]["claims"]
    for claim in claims:
        if isinstance(claim, dict):
            claim["extraction_model"] = model
    
    return result


# ── Stage 2b: Marker Tagger ──────────────────────────────────────────────

def run_tagger(client: OpenAI, claims: list[dict], fixture: dict, seed: int = 42, model: str = "qwen") -> list[dict]:
    """Tag each extracted claim with marker glossary matches.

    Args:
        client: OpenAI-compatible client.
        claims: List of ExtractedRawClaim dicts from run_extractor.
        fixture: Source fixture dict (used for context).
        seed: Random seed for determinism.
        model: Model name to use (default: "qwen" for local, "qwen3.7-max" for DashScope).

    Returns:
        List of tagger output dicts, one per claim.
    """
    system = load_prompt("02-marker-tagger.md")
    glossary = json.loads(GLOSSARY_PATH.read_text())
    tagged = []
    for claim in claims:
        user = json.dumps({
            "verbatim_claim": claim,
            "marker_glossary": glossary,
        }, indent=2)
        resp = llm_call(client, system, user, seed=seed, model=model)
        tagged.append(resp["content"])
    return tagged


# ── Stage 2c: Demographic Structurer ─────────────────────────────────────

def run_structurer(
    client: OpenAI,
    claims: list[dict],
    tagged: list[dict],
    fixture: dict,
    seed: int = 42,
    model: str = "qwen",
) -> list[dict]:
    """Structure each tagged claim into MarkerRecommendation objects.

    Args:
        client: OpenAI-compatible client.
        claims: List of ExtractedRawClaim dicts.
        tagged: List of tagger output dicts (same length as claims).
        fixture: Source fixture dict.
        seed: Random seed for determinism.
        model: Model name to use (default: "qwen" for local, "qwen3.7-max" for DashScope).

    Returns:
        Flat list of MarkerRecommendation dicts.
    """
    system = load_prompt("03-demographic-structurer.md")
    schema = load_schema("extracted_claim.schema.json")
    wrapper = {
        "type": "object",
        "properties": {"recommendations": {"type": "array", "items": schema}},
        "required": ["recommendations"],
        "additionalProperties": False,
    }
    structured = []
    for claim, tags in zip(claims, tagged):
        user = json.dumps({
            "verbatim_claim": claim,
            "marker_tags": tags,
            "source_metadata": {
                "source_id": fixture["source_id"],
                "source_url": fixture["source_url"],
                "source_type": fixture["source_type"],
                "retrieved_at": fixture["retrieved_at"],
                "speaker_or_author": fixture["speaker_or_author"],
                "source_language": fixture["source_language"],
            }
        }, indent=2)
        resp = llm_call(client, system, user, schema=wrapper, seed=seed, model=model)
        content = resp["content"]
        
        # Handle different response formats:
        # 1. List directly: [rec1, rec2, ...]
        # 2. Single recommendation: {"applies_to_markers": [...], ...}
        # 3. Wrapped: {"recommendations": [rec1, rec2, ...]}
        if isinstance(content, list):
            recs = content
        elif isinstance(content, dict):
            if "recommendations" in content:
                recs = content["recommendations"]
            elif "applies_to_markers" in content:
                # Single recommendation returned directly
                recs = [content]
            else:
                recs = []
        else:
            recs = []
        
        # Validate: filter out recommendations with empty marker arrays
        # Schema requires minItems: 1 for applies_to_markers
        valid_recs = []
        for rec in recs:
            markers = rec.get('applies_to_markers', [])
            if not markers:
                # This claim couldn't be matched to any marker - skip it
                # In production, these should be quarantined for manual review
                quote = rec.get('verbatim_quote', '')[:60]
                print(f"    ⚠️  Skipping claim with no markers: {quote}...")
            else:
                valid_recs.append(rec)
        
        structured.extend(valid_recs)
    return structured
