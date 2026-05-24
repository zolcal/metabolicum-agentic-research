"""Shared pipeline stages for extraction, tagging, and structuring.

This module is the single source of truth for the Stage 2 LLM chain:
  extractor -> tagger -> structurer

Both the acceptance harness (code/acceptance/run_acceptance.py) and the
production ingestion pipeline (code/pipeline/ingest.py) import from here.
"""

from code.pipeline.stages import (
    llm_call,
    run_extractor,
    run_tagger,
    run_structurer,
    load_schema,
    load_prompt,
    SCHEMAS_DIR,
    PROMPTS_DIR,
    GLOSSARY_PATH,
    PROJECT_ROOT,
)

__all__ = [
    "llm_call",
    "run_extractor",
    "run_tagger",
    "run_structurer",
    "load_schema",
    "load_prompt",
    "SCHEMAS_DIR",
    "PROMPTS_DIR",
    "GLOSSARY_PATH",
    "PROJECT_ROOT",
]
