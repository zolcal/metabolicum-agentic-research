"""Verify pipeline routing isolation — defensive smoke test (Task #7).

The production pipeline (code/pipeline/ingest.py) resolves every LLM role
through `LLMClient.chat_client(role)`, which looks up the role in
config/llm-endpoints.yaml. There must be NO silent fallback to whatever
model the Hermes gateway has configured as "Main" (currently
openai/gpt-5.5, which is on the user's $100/mo subscription budget).

This test asserts:
  1. Each expected pipeline role resolves to a real, intended endpoint
  2. No role accidentally points at the gateway Main model
  3. An unassigned role raises NoEndpointForRole — does NOT default

Run:
    python code/acceptance/verify_routing_isolation.py

Exit: 0 if all assertions hold, 1 otherwise.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "code"))

from llm_client import LLMClient, NoEndpointForRole  # noqa: E402

# Roles the pipeline depends on, with expectations for each:
#   endpoint_id       — which endpoint id is acceptable (None = any)
#   forbidden_models  — substrings that, if present in the model id, indicate
#                       a routing leak (e.g. gateway Main model bleeding in)
EXPECTATIONS = {
    "extractor":         {"endpoint_id": "deepseek-direct-chat",       "forbidden_models": ["gpt-5", "gpt-5.5"]},
    "tagger":            {"endpoint_id": "dashscope-qwen-max",         "forbidden_models": ["gpt-5", "gpt-5.5"]},
    "structurer":        {"endpoint_id": "dashscope-qwen-max",         "forbidden_models": ["gpt-5", "gpt-5.5"]},
    "legal_reviewer":    {"endpoint_id": "dashscope-qwen-max",         "forbidden_models": ["gpt-5", "gpt-5.5"]},
    "council_extractor": {"endpoint_id": "openrouter-deepseek-v4-flash","forbidden_models": ["gpt-5.5"]},  # gpt-5-mini is correct for council_decider so we allow that family on other roles
    "council_reviewer":  {"endpoint_id": "openrouter-reviewer",        "forbidden_models": ["gpt-5.5"]},
    "council_decider":   {"endpoint_id": "openrouter-decider",         "forbidden_models": ["gpt-5.5"]},
    "embedding":         {"endpoint_id": "gemini-embeddings",          "forbidden_models": ["gpt-5", "gpt-5.5"]},
}


def main() -> int:
    llm = LLMClient()
    failures: list[str] = []

    print("=" * 72)
    print("Pipeline Routing Isolation — verification (Task #7)")
    print(f"  config: {llm.config_path}")
    print("=" * 72)

    # ── Test 1: every expected role resolves to the expected endpoint ──
    print("\n[1] Role → endpoint mapping:")
    for role, exp in EXPECTATIONS.items():
        try:
            ec = llm.endpoint_for(role)
        except NoEndpointForRole as e:
            failures.append(f"role {role!r}: NoEndpointForRole raised ({e})")
            print(f"  ✗ {role:<20s} → MISSING")
            continue

        eid = ec["id"]
        model = ec["model"]
        family = ec.get("family", "?")

        ok = True
        if eid != exp["endpoint_id"]:
            failures.append(f"role {role!r}: endpoint id {eid!r} != expected {exp['endpoint_id']!r}")
            ok = False
        for forbidden in exp["forbidden_models"]:
            if forbidden in (model or ""):
                failures.append(f"role {role!r}: model {model!r} contains forbidden substring {forbidden!r} (gateway-Main leak?)")
                ok = False

        mark = "✓" if ok else "✗"
        print(f"  {mark} {role:<20s} → {eid:<32s} ({family}, model={model})")

    # ── Test 2: unassigned role raises NoEndpointForRole (no silent fallback) ──
    print("\n[2] Unassigned role behavior:")
    sentinel_role = "nonexistent_pipeline_role_xyz_zzz"
    try:
        ec = llm.endpoint_for(sentinel_role)
        failures.append(
            f"unassigned role {sentinel_role!r} resolved to {ec['id']!r} "
            f"instead of raising — SILENT FALLBACK detected!"
        )
        print(f"  ✗ resolved to {ec['id']!r} — should have raised")
    except NoEndpointForRole as e:
        print(f"  ✓ correctly raised NoEndpointForRole")

    # ── Test 3: no endpoint serves gpt-5.5 (the gateway Main) ──
    print("\n[3] Gateway-Main isolation (no role serves gpt-5.5):")
    leaked = []
    for eid, ec in llm.endpoints.items():
        if not ec.get("active"):
            continue
        roles = ec.get("roles") or []
        if not roles:
            continue
        model = ec.get("model", "")
        if "gpt-5.5" in model:
            leaked.append((eid, model, roles))
    if leaked:
        for eid, model, roles in leaked:
            failures.append(f"endpoint {eid!r} (model={model!r}) serves pipeline roles {roles} — gpt-5.5 should be chat-only!")
            print(f"  ✗ {eid} → {model} on roles {roles}")
    else:
        print(f"  ✓ no active endpoint with gpt-5.5 in any pipeline role")

    # ── Verdict ──
    print("\n" + "=" * 72)
    if failures:
        print(f"VERDICT: {len(failures)} FAILURE(S)")
        for f in failures:
            print(f"  - {f}")
        print("=" * 72)
        return 1
    print(f"VERDICT: ALL CHECKS PASS — pipeline routing is isolated from gateway Main")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
