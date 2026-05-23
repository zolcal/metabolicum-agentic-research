# LLM Access Layer — Review Request

**Date:** 2026-05-21
**Reviewers requested:** Codex, Kimi K2
**Decision needed:** Sign-off on the LLM-access design before we wire the Hermes spike against it.
**Status:** Implementation complete and smoke-tested. Specific open questions in §8.

---

## 1. Context

The Hermes spike (`docs/agentic-workflow/hermes-spike-discussion.md` in `metabolicum-research`) needs a concrete LLM access layer before it can run. The spec §05 demands council diversity across three model families; the spec §03 needs search tools; the architecture demands stateless task execution with file-system handoffs and no agent-internal memory.

This pass:

1. Inventoried available LLM endpoints (5 direct API keys + 1 OpenRouter routing).
2. Picked minimum-viable models for each council role across three families.
3. Replaced Brave search with self-hosted SearXNG + MCP servers (cost-driven; Brave was expensive at our query volume).
4. Tightened llama-server binding from `0.0.0.0` to `127.0.0.1` since Hermes is co-located.
5. Wrote a thin Python adapter so agent code references roles, not URLs.

The work is all under `/home/zoltan/Projects/metabolicum-agentic-research/` (the Hermes-only project root, symlinked to the 4TB volume) and `/media/zoltan/4TSSD/ops/` (host infrastructure, no symlink — outside the project boundary).

---

## 2. Files added or modified

| Path | What | Status |
|---|---|---|
| `config/llm-endpoints.yaml` | Endpoint registry — 10 endpoints, role-tagged, env-var-only secrets | new |
| `config/tools.yaml` | Per-stage tool manifests (search, MCP, browsing) | new |
| `code/llm_client.py` | ~180 LOC adapter: `chat_client(role)`, `embed(role, text)`, `health_check(role)` | new |
| `docs/REVIEW-2026-05-21-llm-access.md` | This document | new |
| `/media/zoltan/4TSSD/ops/llama-server/launch-qwen-mtp.sh` | Bind changed from `0.0.0.0` → `127.0.0.1` | edited |

llama-server is running with the new bind; verified that `192.168.1.30:8080` no longer reachable but `127.0.0.1:8080` still serves.

---

## 3. Council design — three families, minimum viable

Per spec §05: three different model families. Settled on:

| Role | Endpoint | Model | Family | Cost/M out |
|---|---|---|---|---|
| **Extractor / Tagger / Structurer / Paradigm classifier / Legal reviewer** | `qwen-local` | Qwen 3.6 27B UD-Q4_K_XL MTP | Alibaba | $0 |
| **Extractor backup** (failover only) | `qwen-mac` | Qwen 3.6 27B OptiQ MLX | Alibaba | $0 |
| **Reviewer** | `openrouter-reviewer` | `google/gemini-2.5-flash` via OpenRouter | Google | $0.30 |
| **Decider** | `openrouter-decider` | `openai/gpt-5-mini` via OpenRouter | OpenAI | $2.00 |
| **Embedding** | `gemini-embeddings` | `gemini-embedding-2` direct | Google | $0 (free tier) |

Three distinct families for council: **Alibaba × Google × OpenAI**. All cloud calls go through one API key (OpenRouter), reducing secret surface.

**Why minimum viable**: the spike tests pipeline architecture, not model ceiling. If quality issues surface, the reserve tier (`openrouter-claude-cheap`, `openrouter-claude-strong`, `openrouter-deepseek-r1`, `openrouter-kimi`) is one YAML edit away.

**Cost forecast for the 5-marker pilot**: well under $10 cloud spend total.

---

## 4. Search architecture — no Brave

Brave Search was originally planned but is cost-prohibitive at our discovery query volume (we'd hit hundreds of queries per marker across the agent loop). Replaced with:

| Need | Tool |
|---|---|
| General web search | **SearXNG** (self-hosted Docker container `metabolicum-searxng`, port 8888, free, already running) |
| Academic papers | `paper-search-mcp` (PubMed, arxiv, biorxiv, medrxiv, Google Scholar) |
| Biomedical entities (drug, gene, variant, trial) | `biomcp` |
| Video discovery | `youtube-mcp` (10k unit/day free quota on user's YouTube API key) |
| X/Twitter | `twitter-mcp` |
| Browser automation | `playwright-mcp` (for JS-rendered pages only) |
| Podcasts | direct RSS (no API needed) |
| Translation | `deepl-mcp` (deferred per spec) |

**Memory MCPs explicitly excluded** per the Hermes statelessness doctrine. `tools.yaml` documents this.

Per-stage manifests in `tools.yaml`:
- Stage 1 (Discovery): searxng + paper-search + youtube + twitter + playwright
- Stage 2 (Extraction): playwright only
- Stage 3 (Council): paper-search + biomcp
- Stage 4 (Provenance): paper-search + biomcp
- Stage 5 (Legal): playwright
- Stage 6 (Assembly): none

---

## 5. Adapter design — `code/llm_client.py`

~180 LOC. Three public methods:

```python
client = LLMClient()                    # auto-finds config/llm-endpoints.yaml
oc = client.chat_client("extractor")    # → openai.OpenAI pointed at qwen-local
v  = client.embed("embedding", text)    # → list[float], 3072-dim
ok = client.health_check("decider")     # → bool
```

Design choices:

- **Stateless**: re-instantiate per Hermes task; no module-level state. YAML parse is cheap.
- **Env vars only for secrets**: API keys are read from `os.environ`; never printed; resolved via `api_key_env` field on each endpoint.
- **No transparent failover**: `failover_to` exists in config but the adapter doesn't auto-retry. Spike doctrine: fail-fast into quarantine, don't hide failures.
- **No retry/backoff in adapter**: that's the orchestration layer's job per Criterion #9.
- **Gemini-style API handling**: when `api_style: gemini`, the embed path uses Google's native `embedContent` shape; chat would use Google's OpenAI-compat shim at `/v1beta/openai/`.

Smoke-tested today against all four assigned roles:

- ✅ `extractor` → qwen-local (health pass; chat content empty due to Qwen 3.6 thinking-mode exhausting 32-token budget on internal CoT — real-world Hermes will set generous max_tokens)
- ✅ `reviewer` → openrouter-reviewer → returns "Ok."
- ✅ `decider` → openrouter-decider → 200 OK (content `None` due to gpt-5-mini reserving all 32 tokens for internal reasoning; `min_output_tokens: 16` documented in YAML; real use will set max_tokens ≥ 300)
- ✅ `embedding` → gemini-embeddings → 3072-dim L2-normalized vector

---

## 6. Security posture

| Surface | Before | After |
|---|---|---|
| llama-server binding | `0.0.0.0:8080` (whole LAN + tailnet) | `127.0.0.1:8080` (this machine only) |
| Cross-machine LLM access | open | only Mac → AI machine path was used for cross-machine; now blocked. AI machine → Mac (failover) still works because Mac is still on `0.0.0.0` |
| API key storage | env vars | env vars (unchanged). YAML never contains literal keys, only env-var names. |
| OpenRouter consolidation | n/a | single key for Gemini-via-OR + GPT-via-OR; reduces key sprawl |

The Mac is now the only one that's still LAN-exposed. That's intentional: the failover endpoint needs to be reachable from the AI machine. Tailscale ACL handles the authentication layer.

---

## 7. What is NOT done

- **JSON-schema-constrained decoding for Stage 2 extraction.** Llama-server supports `response_format: {type: json_schema, ...}` but we haven't written the BiomarkerClaim schema as a file yet. Deferred until we start writing Stage 2 agent prompts.
- **Local BGE-M3 embeddings on the 5060 Ti.** Stub entry `bge-m3-local` exists in the YAML but no roles assigned. Currently routing embeddings through Gemini (free tier). Defer to when Stage 1 semantic discovery becomes active.
- **Per-marker cost telemetry.** YAML has `cost_per_million_in/out` advisory fields and `cost_guardrails` block, but no Hermes-side accumulator. Add when actual cost matters (post-spike if at all).
- **Hermes itself.** No Hermes code yet. The spike charter is sign-off ready but execution hasn't started.

---

## 8. Open questions for reviewers

Numbered for easy cross-reference.

### Q1. Is `gpt-5-mini` the right minimum-viable Decider?

The spike tests architecture, not model ceiling. `gpt-5-mini` is cheap (~$2/M out) and from a distinct family vs Qwen + Gemini. Alternatives:

| Option | Cost (out) | Trade-off |
|---|---|---|
| `openai/gpt-5-mini` (current) | $2.00 | Cheapest gpt-5; reserves tokens for internal reasoning |
| `openai/o4-mini` | ~$4.40 | Reasoning-optimized; different reasoning style |
| `anthropic/claude-haiku-4.5` | ~$5.00 | Anthropic family instead of OpenAI — closes the "no Claude in council" historical gap differently |
| `openai/gpt-5-nano` | ~$0.50 | Even cheaper; may underperform on council judgment |

Either Codex or Kimi may have a strong opinion; please pick or veto.

### Q2. Is OpenRouter the right consolidation choice, or use direct provider APIs?

OpenRouter:
- Pro: single API key, single billing, easy A/B model swaps
- Pro: gives access to Claude (we don't have direct Anthropic API)
- Con: small markup over direct provider rates (~5-15%)
- Con: extra hop in the network path

Direct APIs (OpenAI + Google + Mistral keys we already have):
- Pro: zero markup, fewest network hops
- Con: more keys to manage, no Claude path

Current pick: OpenRouter for the council, direct Google for embeddings (free tier). Reasonable? Or push toward direct APIs for the providers where we have keys?

### Q3. Is the search architecture appropriate without Brave?

SearXNG (local) + MCP servers (free) for everything. No paid web-search API.

Risks: SearXNG aggregates other engines that may rate-limit; MCP servers depend on third-party APIs (PubMed quota, YouTube quota) but those have generous free tiers.

Reasonable? Or are there workloads in the pipeline that genuinely need a paid search API?

### Q4. Should we add a 4th council voice for tiebreakers?

3-family diversity is the spec minimum. Adding a 4th (e.g., DeepSeek R1 reasoning or Claude Haiku) for contested-marker tiebreaks adds depth at marginal cost. The reserve tier in YAML supports this with a one-line edit.

Recommend or skip?

### Q5. Should the YAML be split for clarity?

`llm-endpoints.yaml` is 200 lines. Some endpoints have many comments. Alternatives:
- Split into `llm-endpoints-active.yaml` (4 endpoints actually used) + `llm-endpoints-reserve.yaml` (6 stand-ins)
- Keep as one file

Vote?

### Q6. Adapter location: `code/llm_client.py` vs `code/lib/llm/client.py`?

Single flat file vs package layout. Single file is 180 LOC and clear. Package layout enables splitting Gemini-native handling into its own module if it grows. Recommendation?

### Q7. Per-stage tool manifests — gaps?

The `tools.yaml` per-stage assignments are based on a reading of agentic-workflow §02-§07. Specific concerns:

- Stage 2 (Extraction) gets only `playwright-mcp`. Should it also get `paper-search-mcp` for embedded paper citations?
- Stage 5 (Legal) gets only `playwright-mcp`. Anything else for license verification?

### Q8. Anything missing that we'd need before the Hermes spike can actually start?

The spike charter calls for a single-source Stage 2 extraction test. With the work above:

- ✅ LLM endpoints reachable
- ✅ Adapter resolves role → endpoint
- ✅ Local llama-server binds securely
- ✅ Search/tool architecture defined per stage
- ⏳ JSON schema for ExtractedClaim — not written yet
- ⏳ Hermes itself — not installed yet
- ⏳ State.json contract for stage handoffs — not defined yet

Is there other infrastructure we should land before installing Hermes?

---

## 9. Trust-but-verify notes

- The `cost_per_million_in/out` figures in `llm-endpoints.yaml` are approximate (verified against provider pricing at time of writing but not pinned to a snapshot). OpenRouter's markup over direct provider rates is included but exact deltas should be confirmed when cost actually matters.
- `gemini-embedding-2` was verified live today (3072-dim, L2-norm 1.0).
- `gemini-2.5-flash` and `gpt-5-mini` via OpenRouter were both health-checked and round-tripped a tiny prompt.
- The `text-embedding-004` placeholder from my first draft was confirmed deprecated by Google and replaced with `gemini-embedding-2`.
- llama-server is built from llama.cpp commit `bb28c1fe2` (recorded in `ops/llama-server/README.md`). MTP is enabled via `--spec-type draft-mtp`.

---

## 10. Decision rollup

Reviewers, please respond with one of:

- **Sign off as-is** → I proceed to writing the ExtractedClaim JSON schema and stubbing the first Hermes spike test.
- **Sign off with changes** → list the specific edits (mapping to Q1–Q8 helpful).
- **Request rework** → flag the load-bearing concerns; I'll redraft.

---

## 11. Outcome (2026-05-21)

Both Codex and Kimi returned **Sign off with changes**. The convergent
load-bearing fixes were applied this session.

### 11.1 Applied — `config/llm-endpoints.yaml`

- **Role taxonomy disambiguated (Codex H1).** Stage 2 keeps `extractor`,
  `tagger`, `structurer`, `paradigm_classifier`. Stage 3 council now uses
  distinct role names — `council_extractor`, `council_reviewer`,
  `council_decider` — wired to three families per spec §05:
  Alibaba (qwen-local) × Google (openrouter-reviewer) × OpenAI (openrouter-decider).
- **Gemini 2.5 Flash pricing corrected (Codex M4).** $0.30 in / $2.50 out
  (was $0.075 / $0.30). Verified against OpenRouter model page.
- **`active:` flag added per endpoint.** Promote a reserve endpoint by setting
  `active: true` and adding it to `roles:`. No other code change required.
- **`default_max_tokens` added per endpoint (Kimi A).** Closes the 32-token
  footgun: qwen-local 4096, openrouter-decider 4096, openrouter-reviewer 2048.
  Adapter exposes `default_max_tokens_for(role)`.
- **Mac MLX security note recorded (Codex H2).** Recommended rebind to
  tailnet IP `--host 100.119.217.94`. Manual user action; documented inline
  with link back here (§11.5).
- **`failover_to:` documented as advisory only (Codex H3).** Adapter does NOT
  auto-retry; the field is for orchestration-layer policy.
- **Pricing note in `cost_guardrails.note` updated** to record the correction.

### 11.2 Applied — `code/llm_client.py`

- **Docstring fix (Codex H3).** Removed the false claim that
  `chat_client(role, allow_failover=True)` exists. Adapter is explicit
  fail-fast.
- **New helper `default_max_tokens_for(role)` (Kimi A).** Reads
  `default_max_tokens` from the endpoint config, falls back to 1024.
- **Smoke-test (`__main__`) tightened (Codex M5).**
  - Uses `default_max_tokens_for(role)` instead of the unsafe 32.
  - Prompt now elicits a concrete sentence (`apoB measures atherogenic
    particle count.`) instead of "Reply with one word" — provides
    something to actually inspect.
  - Prints `finish_reason` and exits non-zero if `content` is empty/whitespace,
    so token-starvation failures are loud rather than silent.

### 11.3 Applied — `config/tools.yaml`

- **Playwright removed from Stage 2 (Codex M6 + Kimi Q7).** `stage_2_extraction`
  is now empty: Stage 2 operates exclusively on cached source transcripts
  produced by Stage 1. JS-rendered pages are fetched once during discovery
  and the cached transcript is what Stage 2 sees. Eliminates duplicate fetches
  and aligns with spec §03/§07 ToS discipline.

### 11.4 Verified live (2026-05-21)

All five active roles round-tripped a real sentence with `temperature=0`:

| Role | Endpoint | finish_reason | Output |
|---|---|---|---|
| `extractor` (Stage 2 bulk) | qwen-local (Qwen 3.6 27B MTP)          | `stop` | `'apoB measures atherogenic particle count.'` |
| `council_extractor`        | dashscope-qwen-max (qwen3.7-max, Singapore) | `stop` | `'apoB measures atherogenic particle count.'` |
| `council_reviewer`         | openrouter-reviewer (gemini-2.5-flash) | `stop` | `'apoB measures atherogenic particle count.'` |
| `council_decider`          | openrouter-decider (gpt-5-mini)        | `stop` | `'apoB measures atherogenic particle count.'` |
| `embedding`                | gemini-embeddings (gemini-embedding-2) | n/a    | 3072-dim, L2-normalized |

**Role split (post-review):** local Qwen handles Stage 2 high-volume free work
and Stage 5 legal review; cloud Qwen 3.7 Max (Alibaba ModelStudio, Singapore
workspace `ws-9rbr73q7bd7owx21`) holds the Alibaba-family vote in the Stage 3
three-family council. Eliminates the bottleneck of running 27B-Q4 inference
on contested-claim adjudication while keeping local for the bulk Stage 2
loop. Key sourced from `~/.secrets` as `DASHSCOPE_API_KEY`.

### 11.5 Deferred — manual user action required

- **Rebind Mac MLX-LM to tailnet IP** (Codex H2). On the Mac:
  `mlx_lm.server --host 100.119.217.94 --port 8080 ...`. Currently bound to
  `0.0.0.0:8080`. Tailscale ACL gates peers but not per-service.

### 11.6 Pre-Hermes blockers — next session

Both reviewers flagged these as load-bearing before the spike can actually
run. They are infrastructure, not LLM access, and will be tackled in the
next work block:

1. **`state.json` contract** for stage handoffs. The stateless-pipeline /
   file-system-handoff discipline (per §10) only works if the schema is
   pinned. Needs: stage id, input refs (cached source paths), output refs
   (ExtractedClaim JSON paths), cost ledger, quarantine reasons, run id.
2. **`ExtractedClaim` JSON schema** for Stage 2. Constrained-decoding target
   for the four Stage 2 roles. Must encode: verbatim quote, source URL,
   marker tag, population qualifier, units, paradigm label, source-cache
   hash, extractor model id, timestamp.
3. **Cached source transcript fixture** for the first spike test. One real
   source (e.g., an `apoB` guideline excerpt or a Peter Attia transcript
   segment we already have license for) saved under
   `/home/zoltan/Projects/metabolicum-agentic-research/fixtures/sources/`.
4. **Deterministic smoke test** that runs the full Stage 2 pipeline against
   the fixture and asserts identical output across two runs with `temperature=0`
   and the pinned seed (Hermes spike Criterion #4).

Optional (Kimi D): wire `bge-m3-local` (second llama-server on port 8081)
before the spike if Gemini free-tier embedding quota becomes a concern. Not
load-bearing at pilot volume.
