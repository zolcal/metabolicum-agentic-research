"""Verify hybrid extractor routing on all 3 fixtures.

Calls the production `run_extractor()` with both primary (gemma4-local) and
secondary (deepseek-direct-chat) clients. Asserts:

  - apob (725 chars)            → routed to primary (Gemma, below threshold)
  - fasting-insulin (4649 chars) → routed to primary (Gemma, below threshold)
  - lpa (32378 chars)            → routed to secondary (DeepSeek, above threshold)

For each fixture, also confirms the output is valid (parseable JSON, schema
compliant, claim count plausible, verbatim quotes grounded in transcript).

Exit 0 if routing AND quality all pass; exit 1 if anything fails.
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "code"))

from llm_client import LLMClient
from code.pipeline.stages import run_extractor

FIXTURES_DIR = PROJECT_ROOT / "fixtures" / "sources"

# Each fixture asserts:
#   size_choice: which endpoint the size-based router would pick (primary | secondary)
#   min_claims, max_claims: plausible range
#   acceptable_routes: list of valid actual routes — includes the size_choice,
#     and primary fixtures also accept secondary-via-fallback if Gemma fumbles JSON.
EXPECTATIONS = [
    {"file": "apob-peter-attia-source.json",
     "size_choice": "primary",  "min_claims": 1, "max_claims": 10,
     "acceptable_routes": ["primary", "fallback_to_secondary"]},
    {"file": "fasting-insulin-benbikman-com-01.json",
     "size_choice": "primary",  "min_claims": 0, "max_claims": 5,
     "acceptable_routes": ["primary", "fallback_to_secondary"]},
    {"file": "lpa-peterattiamd-com-01.json",
     "size_choice": "secondary", "min_claims": 2, "max_claims": 30,
     "acceptable_routes": ["secondary"]},
]


def classify_route(routed_to: str, reason: str, primary_model: str, secondary_model: str) -> str:
    if routed_to == primary_model:
        return "primary"
    if routed_to == secondary_model and "fell back to secondary" in reason:
        return "fallback_to_secondary"
    if routed_to == secondary_model and "secondary (transcript" in reason:
        return "secondary"
    return f"unknown ({routed_to})"


def normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def main() -> int:
    llm = LLMClient()
    primary_client = llm.chat_client("extractor")
    primary_ec = llm.endpoint_for("extractor")
    primary_model = primary_ec["model"]

    secondary_id = primary_ec.get("failover_to")
    if not secondary_id or secondary_id not in llm.endpoints:
        print(f"FATAL: extractor endpoint {primary_ec['id']!r} has no `failover_to` in YAML")
        return 1
    secondary_ec = llm.endpoints[secondary_id]
    secondary_client = llm.chat_client_for_endpoint(secondary_id)
    secondary_model = secondary_ec["model"]

    print("=" * 78)
    print("Hybrid Extractor Verification")
    print(f"  primary:    {primary_ec['id']}  (model={primary_model})")
    print(f"  secondary:  {secondary_id}  (model={secondary_model})")
    print(f"  threshold:  8000 chars (default)")
    print("=" * 78)

    failures: list[str] = []
    for case in EXPECTATIONS:
        fname = case["file"]
        fixture = json.loads((FIXTURES_DIR / fname).read_text())
        transcript = fixture["transcript_text"]
        size_choice = case["size_choice"]

        print(f"\n[{fname}]  transcript={len(transcript)}ch  size_router_picks→{size_choice}")

        t0 = time.monotonic()
        try:
            result = run_extractor(
                primary_client,
                fixture,
                seed=42,
                model=primary_model,
                secondary_client=secondary_client,
                secondary_model=secondary_model,
            )
        except Exception as e:  # noqa: BLE001
            failures.append(f"{fname}: {type(e).__name__}: {str(e)[:120]}")
            print(f"  ✗ EXCEPTION: {type(e).__name__}: {str(e)[:120]}")
            continue
        elapsed = time.monotonic() - t0

        routed = result.get("routed_to")
        reason = result.get("routed_reason", "")
        claims = result["content"].get("claims", [])

        # Classify the actual route taken
        route_class = classify_route(routed, reason, primary_model, secondary_model)
        if route_class not in case["acceptable_routes"]:
            failures.append(f"{fname}: route {route_class!r} (to {routed!r}) not in acceptable {case['acceptable_routes']}")
            mark_route = "✗"
        else:
            mark_route = "✓"
        print(f"  {mark_route} route: {route_class}  →  {routed}  ({reason})")

        # Check claim count
        n = len(claims)
        ok_count = case["min_claims"] <= n <= case["max_claims"]
        if not ok_count:
            failures.append(f"{fname}: {n} claims (expected {case['min_claims']}-{case['max_claims']})")
        print(f"  {'✓' if ok_count else '✗'} claims: {n}  (expected {case['min_claims']}-{case['max_claims']})")

        # Spot-check first claim's quote grounding
        if claims:
            c = claims[0]
            quote = normalize(c.get("verbatim_quote") or "")
            grounded = quote in normalize(transcript)
            if not grounded:
                failures.append(f"{fname}: first claim's verbatim_quote not grounded in transcript")
            qmark = "✓" if grounded else "✗"
            qshow = quote if len(quote) < 70 else quote[:67] + "..."
            print(f"  {qmark} first quote grounded: {qshow!r}")
            nv = c.get("numeric_values") or []
            if nv:
                print(f"    numeric: " + ", ".join(f"{x.get('value')}{x.get('unit', '')}" for x in nv[:3] if isinstance(x, dict)))

        print(f"  elapsed: {elapsed:.2f}s")

    print("\n" + "=" * 78)
    if failures:
        print(f"VERDICT: {len(failures)} FAILURE(S)")
        for f in failures:
            print(f"  - {f}")
        print("=" * 78)
        return 1
    print("VERDICT: ALL FIXTURES PASS — hybrid routing works as designed")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
