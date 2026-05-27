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
import uuid
from pathlib import Path
from typing import Any

import jsonschema

from code.pipeline.semantic_fallback import batch_semantic_fallback

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


def _get_model_context_window(client, model: str) -> int | None:
    """Query the model's context window from the /v1/models endpoint."""
    try:
        resp = client.models.list()
        for m in resp.data:
            if m.id == model:
                return getattr(m, "max_context_length", None) or getattr(m, "n_ctx", None)
    except Exception:
        pass
    return None


def _truncate_transcript_for_context(
    transcript: str,
    system_prompt: str,
    user_wrapper: str,
    max_tokens: int,
    context_window: int,
    chars_per_token: float = 3.5,
) -> str:
    """Truncate transcript so prompt + max_tokens fits within context_window.

    Uses a conservative char-per-token estimate. Falls back to no truncation
    if context_window is unknown or large enough.
    """
    if context_window is None or context_window >= 32000:
        return transcript
    fixed_tokens = int(len(system_prompt) / chars_per_token) + int(len(user_wrapper) / chars_per_token)
    available_tokens = context_window - fixed_tokens - max_tokens
    if available_tokens <= 0:
        available_tokens = context_window // 3  # desperate fallback
    max_chars = int(available_tokens * chars_per_token)
    if len(transcript) <= max_chars:
        return transcript
    # Truncate at paragraph boundary if possible
    truncated = transcript[:max_chars]
    last_para = truncated.rfind("\n\n")
    if last_para > max_chars * 0.7:
        truncated = truncated[:last_para]
    return truncated.strip() + "\n\n[TRANSCRIPT TRUNCATED FOR CONTEXT WINDOW]"


def _chunk_transcript(transcript: str, chunk_size: int = 12000, overlap: int = 1000) -> list[str]:
    """Split transcript into overlapping chunks at paragraph boundaries.

    Each chunk gets a [PART X/Y] header so the model knows it's partial.
    """
    if len(transcript) <= chunk_size:
        return [transcript]
    chunks: list[str] = []
    start = 0
    total = len(transcript)
    part = 1
    while start < total:
        end = min(start + chunk_size, total)
        if end < total:
            # Prefer paragraph boundary; fallback to sentence boundary
            para_break = transcript.rfind("\n\n", start, end)
            sent_break = transcript.rfind(". ", start, end)
            boundary = max(para_break, sent_break)
            if boundary > start + chunk_size // 2:
                end = boundary + 1
        chunk_text = transcript[start:end]
        chunks.append(f"[PART {part}]\n{chunk_text.strip()}")
        if end >= total:
            break
        start = end - overlap
        part += 1
    return chunks


def _deduplicate_claims(claims: list[dict]) -> list[dict]:
    """Remove duplicate claims based on verbatim_quote exact match."""
    seen: set[str] = set()
    unique: list[dict] = []
    for claim in claims:
        quote = claim.get("verbatim_quote", "").strip()
        if quote and quote not in seen:
            seen.add(quote)
            unique.append(claim)
    return unique


def glossary_markers() -> set[str]:
    """Return canonical marker slugs from the marker glossary."""
    glossary = json.loads(GLOSSARY_PATH.read_text())
    return {entry["marker"] for entry in glossary.get("entries", []) if entry.get("marker")}


def _normalize_extractor_output(content: Any) -> dict[str, list[dict]]:
    """Handle common malformed extractor shapes.

    The contracted shape is {"claims": [...]}. In practice, some models return
    a list directly or a single claim object. Unknown shapes are errors, not
    successful zero-claim outputs.
    """
    if isinstance(content, list):
        return {"claims": content}
    if isinstance(content, dict):
        if "claims" in content and isinstance(content["claims"], list):
            return {"claims": content["claims"]}
        for key in ("extracted_claims", "raw_claims", "numeric_claims", "results"):
            if isinstance(content.get(key), list):
                return {"claims": content[key]}
        if "claim_id" in content and "verbatim_quote" in content and "numeric_values" in content:
            return {"claims": [content]}
    raise ValueError(f"Unrecognized extractor output shape: {type(content).__name__}")


def _normalize_tagger_output(content: Any, claim: dict, model: str, allowed_markers: set[str]) -> dict:
    """Normalize tagger output and ensure only glossary markers pass through."""
    if not isinstance(content, dict):
        raise ValueError(f"Unrecognized tagger output shape: {type(content).__name__}")
    markers = content.get("applies_to_markers") or []
    if not isinstance(markers, list):
        markers = []
    unknown = content.get("unknown_markers") or []
    if not isinstance(unknown, list):
        unknown = [str(unknown)]
    allowed = []
    for marker in markers:
        if marker in allowed_markers:
            allowed.append(marker)
        elif marker not in {"no_marker_match", "unknown_marker", "none", "null"}:
            unknown.append(str(marker))
    content["claim_id"] = content.get("claim_id") or claim.get("claim_id", "ex_unknown")
    content["applies_to_markers"] = allowed
    content["unknown_markers"] = sorted(set(str(x) for x in unknown if x))
    content["no_marker_match"] = not bool(allowed)
    content["tagger_model"] = model
    content.setdefault("marker_matches", [])
    content.setdefault("ambiguous_references", [])
    content.setdefault("speaker_attribution", {"name": claim.get("speaker_or_author"), "alias_match": None, "ambiguous": False})
    return content

# ── Core LLM call ────────────────────────────────────────────────────────


def _llm_call_with_fallback(
    primary_client: OpenAI,
    primary_model: str,
    system: str,
    user: str,
    *,
    secondary_client: OpenAI | None = None,
    secondary_model: str | None = None,
    schema: dict | None = None,
    max_tokens: int = 4096,
    seed: int = 42,
) -> dict[str, Any]:
    """Call llm_call on primary; on JSON/ValueError parse failure, retry once
    on secondary if provided. Adds `routed_to` to the result dict.

    Used by run_tagger and run_structurer for per-claim defensive fallback,
    mirroring run_extractor's hybrid mode. Primary should be the role's
    assigned endpoint (gemma4-local); secondary should be that role's
    `failover_for` endpoint (typically dashscope-qwen-max).
    """
    try:
        result = llm_call(primary_client, system, user, schema=schema, seed=seed, model=primary_model, max_tokens=max_tokens)
        result["routed_to"] = primary_model
        return result
    except (json.JSONDecodeError, ValueError) as e:
        if secondary_client is not None and secondary_model is not None:
            result = llm_call(secondary_client, system, user, schema=schema, seed=seed, model=secondary_model, max_tokens=max_tokens)
            result["routed_to"] = secondary_model
            result["routed_reason"] = f"primary_parse_failed ({type(e).__name__}: {str(e)[:80]})"
            return result
        raise


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

def run_extractor(
    client: OpenAI,
    fixture: dict,
    seed: int = 42,
    model: str = "qwen",
    max_tokens: int = 4096,
    *,
    secondary_client: OpenAI | None = None,
    secondary_model: str | None = None,
    hybrid_size_threshold_chars: int = 8000,
) -> dict[str, Any]:
    """Extract verbatim claims from a source transcript.

    Hybrid routing (2026-05-26): when `secondary_client` is provided and the
    transcript is at or above `hybrid_size_threshold_chars`, route to the
    secondary. Used to keep small extractions on a fast local model
    (gemma4-local, free, 219 tok/s) while sending long sources to a more
    capable cloud endpoint (deepseek-direct-chat, $0.14/$0.28 per M, 128K
    context). Primary is preferred whenever feasible to minimize cost.

    Args:
        client: Primary OpenAI-compatible client (local gemma4-local).
        fixture: Source fixture dict with transcript_text, source_id, etc.
        seed: Random seed for determinism.
        model: Primary model name.
        max_tokens: Output token budget (default 4096; covers ~6-12 claims).
        secondary_client: Optional fallback for large transcripts.
        secondary_model: Model name to send to the secondary endpoint.
        hybrid_size_threshold_chars: Transcript char count at/above which the
            secondary is used. Default 8000 (~2K tokens) — keeps Gemma's
            quality risks bounded to small inputs.

    Returns:
        LLM call result dict; content has {"claims": [ExtractedRawClaim, ...]}.
        Extra fields: `routed_to` (model name actually used), `routed_reason`
        (human string explaining the routing decision).
    """
    system = load_prompt("01-content-extractor.md")
    transcript = fixture["transcript_text"]

    # Hybrid routing decision
    use_secondary = (
        secondary_client is not None
        and secondary_model is not None
        and len(transcript) >= hybrid_size_threshold_chars
    )
    chosen_client = secondary_client if use_secondary else client
    chosen_model = secondary_model if use_secondary else model
    chosen_reason = (
        f"secondary (transcript {len(transcript)}ch >= threshold {hybrid_size_threshold_chars}ch)"
        if use_secondary
        else f"primary (transcript {len(transcript)}ch < threshold {hybrid_size_threshold_chars}ch)"
    )

    ctx = _get_model_context_window(chosen_client, chosen_model)
    if ctx and ctx < 32000:
        # Local small-context model: cap max_tokens and truncate transcript
        max_tokens = min(max_tokens, ctx // 3)
        user_wrapper = json.dumps({
            "source_transcript": "",
            "expected_markers": fixture.get("expected_markers", []),
            "source_metadata": {},
        }, indent=2)
        transcript = _truncate_transcript_for_context(
            transcript, system, user_wrapper, max_tokens, ctx
        )

    # Chunking for very long transcripts (even on large-context models,
    # JSON output can truncate or corrupt on single-shot extraction).
    chunk_threshold = 15000
    chunks = _chunk_transcript(transcript, chunk_size=12000, overlap=1000) if len(transcript) > chunk_threshold else [transcript]

    raw_schema = load_schema("extracted_raw_claim.schema.json")
    wrapper = {
        "type": "object",
        "properties": {"claims": {"type": "array", "items": raw_schema}},
        "required": ["claims"],
        "additionalProperties": False,
    }

    all_claims: list[dict] = []
    total_input_tokens = 0
    total_output_tokens = 0
    total_elapsed = 0.0

    for idx, chunk in enumerate(chunks):
        user = json.dumps({
            "source_transcript": chunk,
            "expected_markers": fixture.get("expected_markers", []),
            "source_metadata": {
                "source_id": fixture["source_id"],
                "source_url": fixture["source_url"],
                "source_type": fixture["source_type"],
                "platform": fixture.get("platform"),
                "speaker_or_author": fixture.get("speaker_or_author"),
                "retrieved_at": fixture.get("retrieved_at"),
                "source_language": fixture.get("source_language"),
            }
        }, indent=2)

        try:
            chunk_result = llm_call(chosen_client, system, user, schema=None, seed=seed, model=chosen_model, max_tokens=max_tokens)
            chunk_result["content"] = _normalize_extractor_output(chunk_result["content"])
        except (json.JSONDecodeError, ValueError) as e:
            if not use_secondary and secondary_client is not None and secondary_model is not None:
                chunk_result = llm_call(secondary_client, system, user, schema=None, seed=seed, model=secondary_model, max_tokens=max_tokens)
                chunk_result["content"] = _normalize_extractor_output(chunk_result["content"])
                chosen_model = secondary_model
                chosen_reason = f"chunk_{idx+1}_parse_failed; fell back to secondary"
            else:
                raise

        claims = chunk_result["content"].get("claims", [])
        for claim in claims:
            if isinstance(claim, dict):
                claim["extraction_model"] = chosen_model
                cid = (claim.get("claim_id") or "").strip()
                if not cid or cid == "ex_" or not re.match(r"^ex_[A-Za-z0-9-]+$", cid):
                    claim["claim_id"] = f"ex_{uuid.uuid4().hex[:12]}"
                all_claims.append(claim)

        total_input_tokens += chunk_result.get("input_tokens") or 0
        total_output_tokens += chunk_result.get("output_tokens") or 0
        total_elapsed += chunk_result.get("elapsed_s", 0)

    all_claims = _deduplicate_claims(all_claims)

    # Build a synthetic result dict matching the single-shot shape
    result = {
        "content": {"claims": all_claims},
        "raw": json.dumps({"claims": all_claims}),
        "elapsed_s": round(total_elapsed, 2),
        "input_tokens": total_input_tokens if total_input_tokens > 0 else None,
        "output_tokens": total_output_tokens if total_output_tokens > 0 else None,
        "finish_reason": "stop",
        "model": chosen_model,
        "routed_to": chosen_model,
        "routed_reason": f"{chosen_reason}; chunks={len(chunks)}" if len(chunks) > 1 else chosen_reason,
    }

    # Post-hoc full-schema validation — catches what API-layer enforcement
    # cannot. Raises jsonschema.ValidationError on the first violation, which
    # propagates to the caller's existing retry/quarantine logic (the prompt
    # documents 3 retries before quarantine; honored by run_acceptance/ingest).
    jsonschema.validate(result["content"], wrapper)

    return result


# ── Stage 2b: Marker Tagger ──────────────────────────────────────────────

def run_tagger(
    client: OpenAI,
    claims: list[dict],
    fixture: dict,
    seed: int = 42,
    model: str = "qwen",
    use_semantic_fallback: bool = True,
    semantic_threshold: float = 0.78,
    *,
    secondary_client: OpenAI | None = None,
    secondary_model: str | None = None,
) -> list[dict]:
    """Tag each extracted claim with marker glossary matches.

    First tries rigid glossary matching via LLM. For claims that get
    no_marker_match, optionally falls back to e5 embedding similarity against
    topic descriptors.

    Args:
        client: OpenAI-compatible client.
        claims: List of ExtractedRawClaim dicts from run_extractor.
        fixture: Source fixture dict (used for context).
        seed: Random seed for determinism.
        model: Model name to use (default: "qwen" for local, "qwen3.7-max" for DashScope).
        use_semantic_fallback: If True, run e5 embedding fallback on unmatched claims.
        semantic_threshold: Cosine similarity threshold for semantic fallback.

    Returns:
        List of tagger output dicts, one per claim.
    """
    system = load_prompt("02-marker-tagger.md")
    full_glossary = json.loads(GLOSSARY_PATH.read_text())
    allowed_markers = glossary_markers()
    schema = load_schema("marker_tagger.schema.json")

    # Filter glossary to relevant markers only (stay within context limits)
    expected = set(fixture.get("expected_markers", []))
    # Also include markers whose terms appear in any claim text
    claim_text = " ".join(c.get("verbatim_quote", "") for c in claims).lower()
    for entry in full_glossary.get("entries", []):
        if entry.get("term", "").lower() in claim_text:
            expected.add(entry.get("marker"))
    # Safety: always include a few common metabolic markers in case the
    # extractor found cross-marker claims
    expected.update(["apob", "lpa", "fasting-insulin", "hba1c", "tg-hdl-ratio"])

    filtered_entries = [e for e in full_glossary.get("entries", []) if e.get("marker") in expected]
    filtered_glossary = {"entries": filtered_entries}

    # Phase 1: rigid glossary tagging
    tagged = []
    for claim in claims:
        user = json.dumps({
            "verbatim_claim": claim,
            "marker_glossary": filtered_glossary,
        }, indent=2)
        resp = _llm_call_with_fallback(
            client, model, system, user,
            secondary_client=secondary_client, secondary_model=secondary_model,
            seed=seed,
        )
        tagged.append(_normalize_tagger_output(resp["content"], claim, resp.get("routed_to", model), allowed_markers))

    # Phase 2: semantic fallback for unmatched claims
    if use_semantic_fallback:
        unmatched_indices = [
            i for i, t in enumerate(tagged) if t.get("no_marker_match")
        ]
        if unmatched_indices:
            unmatched_claims = [claims[i] for i in unmatched_indices]
            fallback_results = batch_semantic_fallback(
                unmatched_claims, threshold=semantic_threshold, top_k=1
            )
            for idx, fallback in zip(unmatched_indices, fallback_results):
                if fallback["markers"]:
                    tag = tagged[idx]
                    tag["applies_to_markers"].extend(fallback["markers"])
                    tag["no_marker_match"] = False
                    tag.setdefault("semantic_fallback", []).append(fallback)

    return tagged


# ── Stage 2c: Demographic Structurer ─────────────────────────────────────

def run_structurer(
    client: OpenAI,
    claims: list[dict],
    tagged: list[dict],
    fixture: dict,
    seed: int = 42,
    model: str = "qwen",
    *,
    secondary_client: OpenAI | None = None,
    secondary_model: str | None = None,
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
        resp = _llm_call_with_fallback(
            client, model, system, user,
            secondary_client=secondary_client, secondary_model=secondary_model,
            seed=seed,
        )
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
        allowed_markers = glossary_markers()
        for rec in recs:
            if not isinstance(rec, dict):
                continue
            # Fix model identity hallucination: MarkerRecommendation also has
            # extraction_model, and cheaper models may hallucinate another
            # provider/model name. The runner is the source of truth.
            rec["extraction_model"] = model
            markers = [m for m in rec.get('applies_to_markers', []) if m in allowed_markers]
            rec['applies_to_markers'] = markers
            if not markers:
                # This claim couldn't be matched to any known glossary marker - skip it
                # In production, these should be quarantined for manual review
                quote = rec.get('verbatim_quote', '')[:60]
                print(f"    ⚠️  Skipping claim with no known markers: {quote}...")
            else:
                valid_recs.append(rec)
        
        structured.extend(valid_recs)
    return structured
