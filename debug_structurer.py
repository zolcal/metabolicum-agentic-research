#!/usr/bin/env python3
"""Debug script to test structurer with DashScope output."""

import json
import os
import sys
from pathlib import Path
from openai import OpenAI

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from code.llm_client import LLMClient
from code.pipeline.stages import load_prompt, load_schema

def main():
    # Load secrets/.env
    env_file = PROJECT_ROOT / "secrets" / ".env"
    if env_file.is_file():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                if v and k.strip() not in os.environ:
                    os.environ[k.strip()] = v.strip()
    
    # Load DashScope extractor and tagger outputs
    source_id = "8028a5ca-9003-5760-af4e-66bb155a77bd"
    extractor_path = PROJECT_ROOT / "runs" / "dashscope-test-003" / "sources" / source_id / "stage_2a_extractor.json"
    tagger_path = PROJECT_ROOT / "runs" / "dashscope-test-003" / "sources" / source_id / "stage_2b_tagger.json"
    
    extractor_output = json.loads(extractor_path.read_text())
    tagger_output = json.loads(tagger_path.read_text())
    
    # Take first claim
    claim = extractor_output["claims"][0]
    tags = tagger_output[0]
    
    print("=" * 70)
    print("CLAIM (from extractor):")
    print("=" * 70)
    print(json.dumps(claim, indent=2))
    print()
    
    print("=" * 70)
    print("TAGS (from tagger):")
    print("=" * 70)
    print(json.dumps(tags, indent=2))
    print()
    
    # Build user payload (same as in stages.py)
    user_payload = {
        "verbatim_claim": claim,
        "marker_tags": tags,
        "source_metadata": {
            "source_id": source_id,
            "source_url": "https://peterattiamd.com/early-and-aggressive-lowering-of-apob/",
            "source_type": "blog",
            "retrieved_at": "2026-05-23T00:00:00Z",
            "speaker_or_author": "Peter Attia",
            "source_language": "en",
        }
    }
    
    print("=" * 70)
    print("USER PAYLOAD (sent to structurer):")
    print("=" * 70)
    print(json.dumps(user_payload, indent=2))
    print()
    
    # Load prompt and schema
    system_prompt = load_prompt("03-demographic-structurer.md")
    schema = load_schema("extracted_claim.schema.json")
    wrapper = {
        "type": "object",
        "properties": {"recommendations": {"type": "array", "items": schema}},
        "required": ["recommendations"],
        "additionalProperties": False,
    }
    
    # Initialize DashScope client
    llm_config = LLMClient()
    client = llm_config.chat_client("structurer")
    model = llm_config.model_name_for("structurer")
    
    print("=" * 70)
    print(f"CALLING DASHSCOPE (model={model})...")
    print("=" * 70)
    
    # Make the call
    user_json = json.dumps(user_payload, indent=2)
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_json},
        ],
        temperature=0,
        seed=42,
        max_tokens=4096,
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "output", "strict": True, "schema": wrapper},
        },
    )
    
    content = response.choices[0].message.content
    print()
    print("=" * 70)
    print("RAW RESPONSE:")
    print("=" * 70)
    print(content)
    print()
    
    # Parse and show
    parsed = json.loads(content)
    print("=" * 70)
    print("PARSED RESPONSE:")
    print("=" * 70)
    print(json.dumps(parsed, indent=2))
    print()
    
    if isinstance(parsed, list):
        print(f"Result: list with {len(parsed)} items")
    else:
        recs = parsed.get("recommendations", [])
        print(f"Result: {len(recs)} recommendations")
        if recs:
            print("\nFirst recommendation:")
            print(json.dumps(recs[0], indent=2))

if __name__ == "__main__":
    main()
