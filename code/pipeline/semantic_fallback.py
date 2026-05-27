"""Semantic fallback for marker tagging using e5 embeddings.

When the rigid glossary-based tagger returns no_marker_match, this module
computes cosine similarity between the claim text and each marker's topic
descriptor. If similarity >= threshold, the marker is assigned as a fallback.

Design goals:
  - Deterministic (no randomness in embedding computation)
  - Fast (batch embedding of claims, cached descriptors)
  - Transparent (records which matches came from semantic fallback)
  - Conservative (high threshold to avoid false positives)
"""

from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np

# ── Path constants ────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DESCRIPTORS_PATH = PROJECT_ROOT / "input" / "topic_descriptors.yaml"
GLOSSARY_PATH = PROJECT_ROOT / "input" / "marker_glossary.json"

# ── Lazy singleton model ──────────────────────────────────────────────────

_MODEL = None


def _get_model():
    """Lazy-load the e5 model."""
    global _MODEL
    if _MODEL is None:
        from sentence_transformers import SentenceTransformer

        _MODEL = SentenceTransformer("intfloat/multilingual-e5-large", device="cpu")
    return _MODEL


# ── Descriptor loading ────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _load_descriptors() -> dict[str, str]:
    """Load marker → topic_descriptor mapping from YAML."""
    import yaml

    data = yaml.safe_load(DESCRIPTORS_PATH.read_text())
    if data is None:
        return {}
    return {
        slug: entry["topic_descriptor"].strip()
        for slug, entry in data.items()
        if isinstance(entry, dict) and entry.get("topic_descriptor")
    }


@lru_cache(maxsize=1)
def _load_glossary_slugs() -> set[str]:
    """Load canonical marker slugs from glossary."""
    import json

    glossary = json.loads(GLOSSARY_PATH.read_text())
    return {e["marker"] for e in glossary.get("entries", []) if e.get("marker")}


@lru_cache(maxsize=1)
def _load_glossary_terms() -> dict[str, list[str]]:
    """Load marker → list of terms mapping from glossary."""
    import json

    glossary = json.loads(GLOSSARY_PATH.read_text())
    terms: dict[str, list[str]] = {}
    for entry in glossary.get("entries", []):
        marker = entry.get("marker")
        term = entry.get("term", "")
        if marker and term:
            terms.setdefault(marker, []).append(term.lower())
    return terms


def _claim_contains_marker_term(claim: dict[str, Any], marker: str) -> bool:
    """Check if claim text contains any glossary term for the marker.

    This is a conservative post-filter to prevent false positives from
    semantic fallback when the topic descriptors are semantically similar
    (e.g., age-stratified reference ranges for IGF-1 vs HbA1c).
    """
    text = (claim.get("verbatim_quote", "") + " " + claim.get("context_before", "") + " " + claim.get("context_after", "")).lower()
    terms = _load_glossary_terms().get(marker, [])
    # Always accept if the marker slug itself appears in the text
    if marker.replace("-", " ") in text or marker.replace("-", "") in text:
        return True
    for term in terms:
        if term in text:
            return True
    return False


# ── Embedding cache ───────────────────────────────────────────────────────

_DESCRIPTOR_EMBEDDINGS: dict[str, np.ndarray] | None = None


def _get_descriptor_embeddings() -> dict[str, np.ndarray]:
    """Return cached descriptor embeddings, computing them on first call."""
    global _DESCRIPTOR_EMBEDDINGS
    if _DESCRIPTOR_EMBEDDINGS is None:
        model = _get_model()
        descriptors = _load_descriptors()
        texts = [f"passage: {desc}" for desc in descriptors.values()]
        if texts:
            raw = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
            _DESCRIPTOR_EMBEDDINGS = {
                slug: raw[i] for i, slug in enumerate(descriptors.keys())
            }
        else:
            _DESCRIPTOR_EMBEDDINGS = {}
    return _DESCRIPTOR_EMBEDDINGS


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity of two L2-normalized vectors (range [-1, 1])."""
    # Both vectors are already normalized, so dot product = cosine similarity
    return float(np.dot(a, b))


# ── Public API ────────────────────────────────────────────────────────────

def semantic_fallback(
    claim: dict[str, Any],
    threshold: float = 0.78,
    top_k: int = 1,
) -> dict[str, Any]:
    """Try to assign a marker to a claim using semantic similarity.

    Args:
        claim: A single extracted claim dict with at least 'verbatim_quote'.
        threshold: Minimum cosine similarity to accept a match.
        top_k: Maximum number of markers to return (default 1 = best only).

    Returns:
        Dict with keys:
          markers        list of matched marker slugs (may be empty)
          scores         list of similarity scores (parallel to markers)
          threshold      the threshold used
          method         'semantic_fallback'
    """
    quote = claim.get("verbatim_quote", "").strip()
    context = claim.get("context_before", "") + " " + claim.get("context_after", "")
    text = (quote + " " + context).strip()
    if not text:
        return {"markers": [], "scores": [], "threshold": threshold, "method": "semantic_fallback"}

    model = _get_model()
    desc_embs = _get_descriptor_embeddings()
    glossary_slugs = _load_glossary_slugs()

    # e5 query prefix for asymmetric retrieval
    query_text = f"query: {text}"
    query_emb = model.encode([query_text], normalize_embeddings=True, show_progress_bar=False)[0]

    # Score against all descriptors, filter to glossary-known markers
    scored = []
    for slug, emb in desc_embs.items():
        if slug not in glossary_slugs:
            continue
        score = _cosine_similarity(query_emb, emb)
        scored.append((score, slug))

    scored.sort(reverse=True)

    markers = []
    scores = []
    for score, slug in scored[:top_k]:
        if score >= threshold:
            # Post-filter: claim must contain marker name or glossary term
            if _claim_contains_marker_term(claim, slug):
                markers.append(slug)
                scores.append(round(score, 4))

    return {
        "markers": markers,
        "scores": scores,
        "threshold": threshold,
        "method": "semantic_fallback",
    }


# ── Batch API (for efficiency when processing many claims) ────────────────

def batch_semantic_fallback(
    claims: list[dict[str, Any]],
    threshold: float = 0.78,
    top_k: int = 1,
) -> list[dict[str, Any]]:
    """Batch version of semantic_fallback for multiple claims.

    More efficient than calling semantic_fallback in a loop because
    descriptor embeddings are cached and query embeddings are batched.
    """
    if not claims:
        return []

    model = _get_model()
    desc_embs = _get_descriptor_embeddings()
    glossary_slugs = _load_glossary_slugs()

    # Prepare queries
    queries = []
    for claim in claims:
        quote = claim.get("verbatim_quote", "").strip()
        context = claim.get("context_before", "") + " " + claim.get("context_after", "")
        text = (quote + " " + context).strip()
        queries.append(f"query: {text}" if text else "query: ")

    # Batch encode
    query_embs = model.encode(queries, normalize_embeddings=True, show_progress_bar=False)

    results = []
    for idx, query_emb in enumerate(query_embs):
        scored = []
        for slug, emb in desc_embs.items():
            if slug not in glossary_slugs:
                continue
            score = _cosine_similarity(query_emb, emb)
            scored.append((score, slug))
        scored.sort(reverse=True)

        markers = []
        scores = []
        for score, slug in scored[:top_k]:
            if score >= threshold:
                # Post-filter: claim must contain marker name or glossary term
                if _claim_contains_marker_term(claims[idx], slug):
                    markers.append(slug)
                    scores.append(round(score, 4))

        results.append({
            "markers": markers,
            "scores": scores,
            "threshold": threshold,
            "method": "semantic_fallback",
        })

    return results
