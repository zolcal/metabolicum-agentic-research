"""Quality-check the Stage 2 content extractor on cached source fixtures.

Compares dashscope-qwen-max (current incumbent for `extractor` role) vs
openrouter-deepseek-v4-flash (candidate replacement) on the same 3 fixtures
with the same prompt and the same constrained-decoding settings.

Grading checks per output:
  - Output is parseable JSON
  - Wrapper has `claims: [...]` shape
  - Every claim validates against extracted_raw_claim.schema.json
  - Every claim's verbatim_quote is a substring of the source transcript
    (whitespace-normalized)
  - Claim count is plausible (>= expected minimum)

Two runs per endpoint × fixture for determinism check (same gate that
disqualified MiniMax on the council test).

Usage:
    python code/acceptance/quality_check_stage2_extractor.py

Exit code: 0 if both endpoints pass all fixtures across both runs, 1 otherwise.
"""

from __future__ import annotations

import json
import re
import sys
import time
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "code"))

from llm_client import LLMClient  # noqa: E402

try:
    import jsonschema
except ImportError:
    print("ERROR: jsonschema not installed. Install with: pip install jsonschema", file=sys.stderr)
    sys.exit(2)

FIXTURES_DIR = PROJECT_ROOT / "fixtures" / "sources"
PROMPT_PATH = PROJECT_ROOT / "prompts" / "01-content-extractor.md"
SCHEMA_PATH = PROJECT_ROOT / "code" / "schemas" / "extracted_raw_claim.schema.json"

CLAIM_SCHEMA = json.loads(SCHEMA_PATH.read_text())
WRAPPER_SCHEMA = {
    "type": "object",
    "required": ["claims"],
    "additionalProperties": False,
    "properties": {
        "claims": {"type": "array", "items": CLAIM_SCHEMA},
    },
}

TEST_CASES = [
    {
        "fixture": "apob-peter-attia-source.json",
        "expect_claims_min": 1,    # Attia source has ~3 numeric claims (60, 80, 20th, 5th percentile)
        "expect_claims_max": 10,
    },
    {
        "fixture": "lpa-peterattiamd-com-01.json",
        "expect_claims_min": 2,    # Lp(a) article has many: 168, 19, HRs, %, etc.
        "expect_claims_max": 30,
    },
    {
        "fixture": "fasting-insulin-benbikman-com-01.json",
        "expect_claims_min": 0,    # NAD+/insulin-resistance article has no specific numerics
        "expect_claims_max": 5,
    },
]

ENDPOINTS = (
    "gemma4-local",                  # current incumbent (post 2026-05-26)
    "deepseek-direct-chat",          # cloud fallback / failover target
)
RUNS_PER_PAIR = 2  # determinism check

# Toggle to enable response_format constrained decoding.
# - False: prompt-only JSON instruction, parse tolerantly. Matches the
#          production extractor path post-2026-05-26 switch to json_object mode.
# - True:  pass response_format={"type":"json_schema", "json_schema":...,
#          "strict":True}. Causes DeepSeek V4 Flash to return {"claims": []}
#          on cold-start large transcripts — kept as a toggle for future
#          provider evaluations, not the production setting.
USE_STRICT_JSON_SCHEMA = False


# OpenAI's strict json_schema mode rejects these keywords. Other providers
# (OpenRouter passthrough, DashScope) usually follow the same rules. We strip
# them to produce a strict-safe schema variant — semantic content stays the
# same, only the soft constraints we'd otherwise validate post-hoc are removed.
_STRICT_FORBIDDEN_KEYWORDS = {
    "pattern", "minLength", "maxLength",
    "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum",
    "minItems", "maxItems", "uniqueItems",
    "default", "format", "examples",
}


def to_strict_schema(node):
    """Strip OpenAI-strict-incompatible keywords. Force additionalProperties:false
    on every object. Ensure `required` lists every property name."""
    if isinstance(node, dict):
        out = {k: v for k, v in node.items() if k not in _STRICT_FORBIDDEN_KEYWORDS}
        for k in list(out.keys()):
            out[k] = to_strict_schema(out[k])
        if out.get("type") == "object":
            out["additionalProperties"] = False
            if "properties" in out:
                out["required"] = list(out["properties"].keys())
        return out
    if isinstance(node, list):
        return [to_strict_schema(x) for x in node]
    return node


STRICT_WRAPPER_SCHEMA = to_strict_schema(WRAPPER_SCHEMA)


def extract_json(text: str) -> dict | None:
    """Tolerant JSON extraction: bare JSON, ```json fences, or first balanced {…}."""
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    start = text.find("{")
    if start >= 0:
        depth = 0
        for i, ch in enumerate(text[start:], start=start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except json.JSONDecodeError:
                        return None
    return None


def normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def grade(
    label: str,
    raw_output: str,
    transcript: str,
    expect_min: int,
    expect_max: int,
) -> dict:
    g: dict = {
        "label": label,
        "raw_chars": len(raw_output or ""),
        "parseable": False,
        "wrapper_ok": False,
        "schema_ok": False,
        "schema_errors": [],
        "claims_count": 0,
        "count_in_range": False,
        "quotes_grounded": 0,
        "quotes_ungrounded": 0,
        "all_quotes_grounded": False,
        "passed": False,
        "first_claim": None,
    }
    data = extract_json(raw_output)
    if data is None:
        return g
    g["parseable"] = True

    if not isinstance(data, dict) or "claims" not in data or not isinstance(data["claims"], list):
        return g
    g["wrapper_ok"] = True

    claims = data["claims"]
    # Apply the same runner-side normalization that code/pipeline/stages.py
    # `run_extractor` does in production. This mirrors the patch landed
    # 2026-05-25 to cover OpenAI-strict-mode gaps (pattern/minLength can't
    # be enforced at the API layer for either provider).
    for c in claims:
        if isinstance(c, dict):
            if not (c.get("extraction_model") or "").strip():
                c["extraction_model"] = label  # endpoint id as proxy for model
            cid = (c.get("claim_id") or "").strip()
            if not cid or cid == "ex_" or not re.match(r"^ex_[A-Za-z0-9-]+$", cid):
                c["claim_id"] = f"ex_{uuid.uuid4().hex[:12]}"
    g["claims_count"] = len(claims)
    g["count_in_range"] = expect_min <= len(claims) <= expect_max

    # Validate against wrapper schema (which validates each claim too)
    try:
        jsonschema.validate(data, WRAPPER_SCHEMA)
        g["schema_ok"] = True
    except jsonschema.ValidationError as e:
        g["schema_errors"].append(f"{e.json_path}: {e.message[:120]}")

    # Verbatim quote grounding — every claim's quote must appear in source
    tx_norm = normalize(transcript)
    grounded = 0
    ungrounded = 0
    for c in claims:
        if not isinstance(c, dict):
            ungrounded += 1
            continue
        q = normalize(c.get("verbatim_quote") or "")
        if q and q in tx_norm:
            grounded += 1
        else:
            ungrounded += 1
    g["quotes_grounded"] = grounded
    g["quotes_ungrounded"] = ungrounded
    g["all_quotes_grounded"] = (ungrounded == 0 and grounded > 0) or (len(claims) == 0)

    if claims:
        g["first_claim"] = claims[0]

    g["passed"] = (
        g["parseable"]
        and g["wrapper_ok"]
        and g["schema_ok"]
        and g["count_in_range"]
        and g["all_quotes_grounded"]
    )
    return g


def call_endpoint(llm: LLMClient, endpoint_id: str, system_prompt: str, user_msg: str) -> tuple[str, float, str | None]:
    ec = llm.endpoints[endpoint_id]
    client = llm.chat_client_for_endpoint(endpoint_id)
    kwargs: dict = {
        "model": ec["model"],
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ],
        "max_tokens": 4096,
        "temperature": 0,
    }
    # 4096 output tokens covers any realistic Stage 2 extraction (~6-12 claims
    # at ~300 tokens each). Previously 16384 was used as headroom for the
    # OpenRouter `deepseek/deepseek-v4-flash` thinking-mode burn; current routing
    # (gemma4-local + deepseek-direct-chat) is non-thinking, no headroom needed.
    # At Gemma 16K context, max_tokens=16384 guaranteed "exceeds context window"
    # because prompt + transcript leaves ~5K for output.
    kwargs["max_tokens"] = 4096
    if USE_STRICT_JSON_SCHEMA:
        kwargs["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": "extracted_raw_claims_wrapper",
                "schema": STRICT_WRAPPER_SCHEMA,
                "strict": True,
            },
        }
    t0 = time.monotonic()
    try:
        r = client.chat.completions.create(**kwargs)
    except Exception as e:  # noqa: BLE001
        return "", time.monotonic() - t0, f"{type(e).__name__}: {e}"
    elapsed = time.monotonic() - t0
    content = r.choices[0].message.content or ""
    return content, elapsed, None


def print_grade(g: dict, elapsed: float, error: str | None, model_name: str) -> None:
    print(f"      --- {g['label']}  ({model_name})  [{elapsed:.2f}s] ---")
    if error:
        print(f"        ERROR: {error}")
        return
    print(f"        raw:           {g['raw_chars']} chars")
    print(f"        parseable:     {g['parseable']}, wrapper_ok={g['wrapper_ok']}, schema_ok={g['schema_ok']}")
    if g["schema_errors"]:
        for err in g["schema_errors"][:3]:
            print(f"          schema_err: {err}")
    print(f"        claims:        {g['claims_count']} ({'in range' if g['count_in_range'] else 'OUT OF RANGE'})")
    print(f"        quotes:        {g['quotes_grounded']} grounded, {g['quotes_ungrounded']} UNGROUNDED")
    if g["first_claim"] and isinstance(g["first_claim"], dict):
        fc = g["first_claim"]
        nv = fc.get("numeric_values") or []
        nv_summary = ", ".join(
            f"{x.get('value')}{x.get('unit', '')}" for x in nv[:3] if isinstance(x, dict)
        )
        vq = normalize(fc.get("verbatim_quote") or "")
        if len(vq) > 80:
            vq = vq[:77] + "..."
        print(f"        first claim:   numeric=[{nv_summary}]  quote={vq!r}")
    print(f"        PASSED: {g['passed']}")


def main() -> int:
    llm = LLMClient()
    system_prompt = PROMPT_PATH.read_text()

    print("=" * 80)
    print("Stage 2 Extractor Quality Check — multi-fixture, multi-run")
    print(f"  prompt:    {PROMPT_PATH.name}")
    print(f"  schema:    {SCHEMA_PATH.name} (wrapped in claims: [])")
    print(f"  fixtures:  {len(TEST_CASES)}")
    print(f"  endpoints: {list(ENDPOINTS)}")
    print(f"  runs/pair: {RUNS_PER_PAIR}  (determinism check)")
    print(f"  strict_mode: {USE_STRICT_JSON_SCHEMA}  (response_format=json_schema)")
    print("=" * 80)

    matrix: dict = {}  # endpoint -> fixture -> list of grades
    for case in TEST_CASES:
        fixture = json.loads((FIXTURES_DIR / case["fixture"]).read_text())
        transcript = fixture["transcript_text"]
        print(f"\n[fixture] {case['fixture']}  transcript={len(transcript)}ch  "
              f"expect_claims=[{case['expect_claims_min']}-{case['expect_claims_max']}]")

        user_payload = {
            "source_transcript": transcript,
            "source_metadata": {
                k: fixture.get(k) for k in
                ("source_url", "source_type", "platform", "title",
                 "retrieved_at", "speaker_or_author", "source_language")
            },
            "expected_markers": fixture.get("expected_markers") or [],
        }
        user_msg = (
            "Extract every numeric metabolic claim from the source_transcript. "
            "Respond with ONLY a single JSON object of the form "
            "{\"claims\": [<ExtractedRawClaim>, ...]} as described in the "
            "system prompt — no markdown, no preamble. If the transcript has "
            "no numeric claims, respond with {\"claims\": []}.\n\n"
            + json.dumps(user_payload, indent=2)
        )

        for endpoint_id in ENDPOINTS:
            ec = llm.endpoints[endpoint_id]
            print(f"  endpoint: {endpoint_id} ({ec['model']})")
            matrix.setdefault(endpoint_id, {})[case["fixture"]] = []
            for run_idx in range(1, RUNS_PER_PAIR + 1):
                raw, elapsed, err = call_endpoint(llm, endpoint_id, system_prompt, user_msg)
                g = grade(
                    f"run {run_idx}",
                    raw,
                    transcript,
                    case["expect_claims_min"],
                    case["expect_claims_max"],
                )
                matrix[endpoint_id][case["fixture"]].append({
                    "grade": g, "elapsed": elapsed, "err": err
                })
                print_grade(g, elapsed, err, ec["model"])

    # Summary matrix
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"  {'endpoint':<32s} | " + " | ".join(f"{c['fixture'].split('-')[0]:^25s}" for c in TEST_CASES))
    print(f"  {'-' * 32} | " + " | ".join("-" * 25 for _ in TEST_CASES))
    overall_pass = True
    for endpoint_id in ENDPOINTS:
        cells = []
        for case in TEST_CASES:
            runs = matrix[endpoint_id][case["fixture"]]
            tags = []
            for r in runs:
                if r["err"]:
                    tags.append("ERR")
                    overall_pass = False
                elif r["grade"]["passed"]:
                    tags.append(f"PASS({r['grade']['claims_count']})")
                else:
                    tags.append(f"FAIL({r['grade']['claims_count']})")
                    overall_pass = False
            cells.append(f"{' / '.join(tags):^25s}")
        print(f"  {endpoint_id:<32s} | " + " | ".join(cells))

    print("\n" + "=" * 80)
    if overall_pass:
        print(f"VERDICT: ALL {len(TEST_CASES)} FIXTURES × {len(ENDPOINTS)} ENDPOINTS × {RUNS_PER_PAIR} RUNS PASS")
    else:
        print("VERDICT: AT LEAST ONE FAIL — see per-case detail above")
    print("=" * 80 + "\n")

    return 0 if overall_pass else 1


if __name__ == "__main__":
    sys.exit(main())
