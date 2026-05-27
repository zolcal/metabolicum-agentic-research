"""Quality-check the council extractor on a single fixture.

Compares minimax-anthropic (currently active for council_extractor) vs
dashscope-qwen-max (currently demoted) on the same apob source artifact
with the same prompt, same temperature=0, same max_tokens. Tolerates
markdown-fenced or prose-wrapped JSON output (MiniMax's Anthropic surface
does not enforce native JSON-schema decoding).

Usage:
    python code/acceptance/quality_check_council_extractor.py

Exit code:
    0 if both endpoints pass all checks
    1 if either endpoint fails any check
    2 on infrastructure error (network, missing key, etc.)
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "code"))

from llm_client import LLMClient  # noqa: E402

FIXTURES_DIR = PROJECT_ROOT / "fixtures" / "sources"
PROMPT_PATH = PROJECT_ROOT / "prompts" / "04a-council-extractor.md"

# Each case provides:
#   fixture                — filename under fixtures/sources/
#   marker                 — expected marker tag in the output
#   expected_numeric       — None if the source contains NO numeric claim for
#                            this marker (model should emit null);
#                            (lo, hi) tuple otherwise
#   stub                   — fabricated Stage-2 MarkerRecommendation handed to
#                            the council extractor to re-verify
TEST_CASES = [
    {
        "fixture": "apob-peter-attia-source.json",
        "marker": "apob",
        "expected_numeric": (55, 65),
        "stub": {
            "claim_id": "test-claim-apob-attia-001",
            "marker": "apob",
            "verbatim_quote": (
                "I just don't see a reason to have an ApoB ever north of 60 "
                "milligrams per deciliter."
            ),
            "numeric_value": 60,
            "units": "mg/dL",
            "direction": "above",
            "claim_polarity": "supports",
            "speaker_or_author": "Peter Attia",
        },
    },
    {
        "fixture": "lpa-peterattiamd-com-01.json",
        "marker": "lpa",
        "expected_numeric": (160, 180),  # 168 nmol/L = 90th-percentile cutoff
        "stub": {
            "claim_id": "test-claim-lpa-attia-001",
            "marker": "lpa",
            "verbatim_quote": (
                "168 nmol/L and <19 nmol/L for high and low cutoffs, "
                "respectively."
            ),
            "numeric_value": 168,
            "units": "nmol/L",
            "direction": "above",
            "claim_polarity": "supports",
            "speaker_or_author": "Peter Attia",
        },
    },
    {
        "fixture": "fasting-insulin-benbikman-com-01.json",
        "marker": "fasting-insulin",
        # Source is a NAD+/insulin-resistance qualitative discussion with NO
        # numeric fasting-insulin threshold. Correct council behaviour:
        # numeric_value: null (no invention) per prompt rule #5.
        "expected_numeric": None,
        "stub": {
            "claim_id": "test-claim-fastingins-bikman-001",
            "marker": "fasting-insulin",
            "verbatim_quote": (
                "Insulin resistance is not a lack-of-energy problem—"
                "it's an energy overload problem."
            ),
            "numeric_value": None,
            "units": None,
            "direction": None,
            "claim_polarity": "qualifies",
            "speaker_or_author": "Benjamin Bikman",
        },
    },
]

REQUIRED_FIELDS = [
    "claim_id",
    "marker",
    "source_quote_found",
    "verbatim_quote",
    "numeric_value",
    "units",
    "direction",
    "claim_polarity",
    "speaker_or_author",
]


def extract_json(text: str) -> dict | None:
    """Tolerant JSON extraction: bare JSON, ```json fences, or first {…} block."""
    if not text:
        return None
    # Direct
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Fenced
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # First brace-balanced block (greedy)
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
    expected_marker: str,
    expected_numeric: tuple[float, float] | None,
) -> dict:
    """Grade one output. expected_numeric=None means the source has NO numeric
    claim and the model is expected to emit `numeric_value: null` (no invention).
    """
    g: dict = {
        "label": label,
        "raw_chars": len(raw_output or ""),
        "parseable": False,
        "fields_present": [],
        "fields_missing": list(REQUIRED_FIELDS),
        "quote_grounded": False,
        "marker_match": False,
        "numeric_ok": False,
        "passed": False,
        "data": None,
    }
    data = extract_json(raw_output)
    if data is None:
        return g
    g["parseable"] = True
    g["data"] = data
    g["fields_present"] = [f for f in REQUIRED_FIELDS if f in data]
    g["fields_missing"] = [f for f in REQUIRED_FIELDS if f not in data]

    quote = normalize(data.get("verbatim_quote") or "")
    tx = normalize(transcript)
    # Council prompt allows `verbatim_quote: ""` together with
    # `source_quote_found: false` when no matching quote exists.
    quote_found_flag = data.get("source_quote_found")
    if quote:
        g["quote_grounded"] = quote in tx
    else:
        # Empty quote is OK only if model explicitly flagged no-quote-found
        g["quote_grounded"] = quote_found_flag is False

    g["marker_match"] = data.get("marker") == expected_marker

    nv = data.get("numeric_value")
    if expected_numeric is None:
        # No numeric claim expected — null is the right answer
        g["numeric_ok"] = nv is None
    else:
        lo, hi = expected_numeric
        g["numeric_ok"] = isinstance(nv, (int, float)) and lo <= nv <= hi

    g["passed"] = (
        g["parseable"]
        and not g["fields_missing"]
        and g["quote_grounded"]
        and g["marker_match"]
        and g["numeric_ok"]
    )
    return g


def call_endpoint(llm: LLMClient, endpoint_id: str, system_prompt: str, user_msg: str) -> tuple[str, float, str | None]:
    """Return (raw_text, elapsed_s, error_or_None)."""
    ec = llm.endpoints[endpoint_id]
    client = llm.chat_client_for_endpoint(endpoint_id)
    t0 = time.monotonic()
    try:
        r = client.chat.completions.create(
            model=ec["model"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=2048,
            temperature=0,
        )
    except Exception as e:  # noqa: BLE001
        return "", time.monotonic() - t0, f"{type(e).__name__}: {e}"
    elapsed = time.monotonic() - t0
    content = r.choices[0].message.content or ""
    return content, elapsed, None


def print_grade(g: dict, elapsed: float, error: str | None, model_name: str) -> None:
    print(f"    --- {g['label']}  ({model_name})  [{elapsed:.2f}s] ---")
    if error:
        print(f"      ERROR: {error}")
        return
    print(f"      raw output:       {g['raw_chars']} chars")
    print(f"      parseable JSON:   {g['parseable']}")
    print(f"      fields present:   {len(g['fields_present'])}/{len(REQUIRED_FIELDS)}")
    if g["fields_missing"]:
        print(f"      fields MISSING:   {g['fields_missing']}")
    print(f"      quote grounded:   {g['quote_grounded']}")
    print(f"      marker match:     {g['marker_match']}")
    print(f"      numeric OK:       {g['numeric_ok']}")
    if g["data"]:
        d = g["data"]
        nv = d.get("numeric_value")
        nv_disp = "null" if nv is None else nv
        print(
            f"      → marker={d.get('marker')!r}, value={nv_disp}, "
            f"units={d.get('units')!r}, direction={d.get('direction')!r}"
        )
        vq = d.get("verbatim_quote") or ""
        if len(vq) > 100:
            vq = vq[:97] + "..."
        print(f"      → quote={vq!r}")
    print(f"      PASSED: {g['passed']}")


def main() -> int:
    llm = LLMClient()
    system_prompt = PROMPT_PATH.read_text()
    endpoints = (
        "dashscope-qwen-max",          # baseline (currently passing)
        "openrouter-deepseek-v4-flash", # candidate replacement
        "minimax-anthropic",            # for reference (known non-deterministic)
    )

    print("=" * 78)
    print("Council Extractor Quality Check — multi-fixture")
    print(f"  prompt:  {PROMPT_PATH.name}")
    print(f"  fixtures: {len(TEST_CASES)}")
    print(f"  endpoints: {list(endpoints)}")
    print("=" * 78)

    # results matrix: case_idx -> endpoint_id -> (model_name, grade, elapsed, err)
    all_results: list[dict] = []
    overall_pass = True

    for case in TEST_CASES:
        fixture = json.loads((FIXTURES_DIR / case["fixture"]).read_text())
        transcript = fixture["transcript_text"]
        expected_marker = case["marker"]
        expected_numeric = case["expected_numeric"]

        user_payload = {
            "marker_recommendation": case["stub"],
            "source_artifact": fixture,
            "reviewer_model_config": {"model": "<INJECTED>", "endpoint": "<INJECTED>"},
        }
        user_msg = (
            f"Re-extract the {expected_marker} claim from the source artifact "
            "below. Respond with ONLY the JSON object described in the system "
            "prompt — no markdown, no preamble, no explanation. If the source "
            "contains no numeric value for this marker, set numeric fields to "
            "null per prompt rule #5.\n\n"
            + json.dumps(user_payload, indent=2)
        )

        print(f"\n[fixture] {case['fixture']}  (marker={expected_marker}, "
              f"expected_numeric={expected_numeric})  transcript={len(transcript)}ch")

        per_case = {"fixture": case["fixture"], "marker": expected_marker, "by_endpoint": {}}
        for endpoint_id in endpoints:
            ec = llm.endpoints[endpoint_id]
            raw, elapsed, err = call_endpoint(llm, endpoint_id, system_prompt, user_msg)
            g = grade(endpoint_id, raw, transcript, expected_marker, expected_numeric)
            per_case["by_endpoint"][endpoint_id] = {
                "model": ec["model"], "grade": g, "elapsed": elapsed, "err": err
            }
            print_grade(g, elapsed, err, ec["model"])
            if err is not None or not g["passed"]:
                overall_pass = False
        all_results.append(per_case)

    # Summary matrix
    print("\n" + "=" * 78)
    print("SUMMARY")
    print("=" * 78)
    header = f"  {'fixture':<42s} | " + " | ".join(f"{e:^25s}" for e in endpoints)
    print(header)
    print(f"  {'-' * 42} | " + " | ".join("-" * 25 for _ in endpoints))
    for r in all_results:
        cells = []
        for e in endpoints:
            x = r["by_endpoint"][e]
            if x["err"]:
                cells.append(f"{'ERROR':^25s}")
            else:
                tag = "PASS" if x["grade"]["passed"] else "FAIL"
                cells.append(f"{tag:^7s} {x['elapsed']:>5.2f}s {x['grade']['raw_chars']:>5d}ch")
        print(f"  {r['fixture']:<42s} | " + " | ".join(cells))

    print("\n" + "=" * 78)
    if overall_pass:
        print(f"VERDICT: ALL {len(TEST_CASES)} FIXTURES × {len(endpoints)} ENDPOINTS PASS")
    else:
        print("VERDICT: AT LEAST ONE FAIL — see per-case detail above")
    print("=" * 78 + "\n")

    return 0 if overall_pass else 1


if __name__ == "__main__":
    sys.exit(main())
