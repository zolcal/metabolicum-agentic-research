# Hermes Agent Setup — Configuration and Acceptance Contract

> **Status:** Hermes selected as the pipeline runner (decision 2026-05-22). The earlier "spike vs custom runner" framing is retired.
> **Purpose:** Configuration contract and acceptance tests for the Hermes install in `metabolicum-agentic-research`.
> **Constraint:** Hermes runs as a **stateless task executor**, not an autonomous self-evolving agent.

---

## 1. Recap: Where We Are

### Completed
- **SM anchor input infrastructure:** Waves 1 (108 frozen YAMLs), 2A (109 canonical candidates), 3 (674 unreviewed DB). Zero derivation leakage. No cross-wave overlap.
- **Marker identity registry:** 1,110 markers, 4 superseded aliases resolved, 53 duplicate display-name groups adjudicated, 104 wave-1 approved.
- **PMID backfill:** 272/986 files populated (844 PMIDs).
- **Agent prompts:** 5 role prompts drafted (content extractor, marker tagger, demographic structurer, council decider, legal reviewer).
- **Envelope framework validated:** §17 boundary rules are sufficient. No per-marker curation needed. Early hand-curated envelope-facts draft was superseded by §17 and removed; the active SM input set now lives at `metabolicum-agentic-research/input/sm-ranges/` (pilots + wave-1 + wave-2 + wave-2b + wave-3) and remains canonical.

### Open Blockers
1. Create `metabolicum-agentic-research` repo (clean history, isolated from `metasync`).
2. Deploy Supabase schema (§04 tables with hard constraints).
3. Install Hermes Agent and configure for stateless execution.
4. Configure local inference stack (see §1.1).

### 1.1 Local Inference Stack

**Primary local inference target.** AI machine (RTX 3090 Ti 24GB + RTX 5060 Ti 16GB) running `llama.cpp llama-server` over a local-network OpenAI-compatible API. Replaces the prior Ollama-based plan; llama.cpp has native MTP speculative-decoding support and lower per-call overhead.

**Initial model.** `unsloth/Qwen3.6-27B-MTP-GGUF:UD-Q4_K_XL` (or equivalent 4-bit Qwen3.6 MTP GGUF). Q8 quants exceed 24GB VRAM before KV cache and must not be used on the 3090 Ti. Project-specific benchmarks (decode throughput, MTP acceptance rate) required before committing; third-party numbers are indicative only.

**Initial mode.** Single request slot (`-np 1`), text-only, MTP enabled (`--spec-type draft-mtp`), temperature 0, seed pinned. Deterministic byte-equivalence across 3 isolated runs is the gate; if MTP breaks determinism, disable MTP for the determinism acceptance test specifically and re-enable for production.

**Known MTP constraints (load-bearing for batch scale).** Current llama.cpp MTP does **not** support `-np > 1` (multiple concurrent request slots) or `--mmproj` (vision). MTP is therefore single-slot text-only. Pilot + Stage 2/3 production are sequential by design and unaffected. Wave-3 batch (674 markers, parallel ingestion) requires one of: spawn N parallel `llama-server` processes (one MTP session each, multiplexed at the orchestration layer), disable MTP for batch and accept the throughput hit in exchange for `-np > 4` slots, or migrate batch workloads to vLLM/SGLang. This decision is deferred to the Wave-3 readiness pass.

**Secondary GPU (RTX 5060 Ti 16GB).** Runs separate processes: embedding model (e.g., BGE-M3 or e5-multilingual-large), reranker, Whisper transcription, or a small classifier. Each as its own `llama-server` or service. Mixed-architecture multi-GPU serving is avoided because CUDA compute capabilities differ (3090 Ti is Ampere 8.6; 5060 Ti is Blackwell 12.0) and vLLM/PyTorch prebuilt wheels do not consistently support both — be ready to build llama.cpp from source if prebuilt binaries lack Blackwell kernels or PTX.

**MacBook Pro (36GB unified memory).** Dev / fallback node only, not production. Use MLX-LM server with Qwen3.6-9B or 14B for typical use; 27B 4-bit is feasible but tight on long-context tasks. MLX is the right Apple Silicon path — third-party benchmarks indicate it outperforms llama.cpp on Metal for sub-14B models, but project-specific verification required before committing.

**Fallback paths.** If deterministic byte-equivalence fails with MTP enabled, disable MTP for the determinism test. If single-slot throughput becomes a Wave-3 bottleneck, evaluate vLLM or SGLang as the batch engine. If Blackwell driver/CUDA compat blocks the 5060 Ti workloads, run them on CPU or migrate to a separate machine.

---

## 2. Statelessness requirement

Hermes Agent's default behavior is **self-evolution**:
- Auto-generates skills from completed tasks.
- Persists memory across sessions (MEMORY.md + FTS5).
- Builds user profiles and long-term state.

Our pipeline requires **stateless determinism**:
- One source → one run → one output artifact.
- No cross-run memory (state lives in Supabase, not agent memory).
- No skill formation (prompts are schema-locked, not learned).
- Reproducibility: same input + same model → same output.

The remainder of this document defines the configuration that satisfies these requirements and the acceptance tests that verify it.

---

## 3. Hermes Restriction Model

The following Hermes features must be disabled or overridden in the install configuration:

| Hermes Feature | Default Behavior | Required Restriction | Enforcement Method |
|---|---|---|---|
| **Skill Formation** | Auto-creates `~/.hermes/skills/` after tasks | Disable entirely | Verify exact disable switch against pinned Hermes version (see §3.1); disposable `HERMES_HOME` per worker run (see Acceptance Test #5). Workers only — gateway runtime does not run task work and therefore does not produce skills. |
| **Persistent Memory** | `MEMORY.md`, `USER.md`, `memories/users/<id>/USER.md`, `state.db` FTS5 message history; auto-write triggered by "remember that…" patterns | Disable on workers; gateway keeps `state.db` for Telegram session routing only, never memory writes | Config block (Hermes-version-specific; verify against pinned-version docs in §3.1 B2): `memory.memory_enabled: false`, `memory.user_profile_enabled: false`, `memory.auto_write: false`, `agent.disabled_toolsets: [memory]`. Workers also use disposable `HERMES_HOME` per run. Gateway sets the same config but persists `state.db` for the lifetime of the daemon (see §3.2). |
| **Identity / Persona Files** | `~/.hermes/SOUL.md` (system-prompt slot #1, auto-generated starter if missing, never overwritten once exists), `~/.hermes/config.yaml` (personalities + display) | Pin both files in the project repo; load fresh from the pinned copies into each disposable `HERMES_HOME` at run start; SHA-256 unchanged across runs | Project-controlled `SOUL.md` checked in at `metabolicum-agentic-research/hermes/SOUL.md` defining the stateless task-executor persona (refuses persona drift, refuses skill formation, refuses to invent quotes). Symlinked or copied into `HERMES_HOME/SOUL.md` at run start. Acceptance Test #7 must assert `sha256(HERMES_HOME/SOUL.md) == sha256(repo/SOUL.md)` and same for `config.yaml`. |
| **Cross-Stage Visibility** | Agent can see previous conversation history | Isolate per-task context | Fresh `state.json` handoff per stage; no Hermes-internal history |
| **Self-Improvement Loop** | Agent patches its own prompts | Disable; schema-locked prompts only | Immutable prompt files loaded at runtime; no runtime prompt mutation. `SOUL.md` falls under this category (covered explicitly by the Identity / Persona Files row). |
| **Multi-Turn Autonomy** | Agent decides when task is "done" | Hard turn limits + deterministic exit | Max N turns; forced tool call to `submit_output` |
| **Tool Discovery** | Agent discovers tools dynamically | Fixed tool list per stage | Explicit tool manifest; no MCP server browsing (MCP support out of scope — see §5) |

### 3.1 Setup blockers (must clear before Hermes install)

| # | Blocker | Why |
|---|---|---|
| B1 | **Pin Hermes version** (release tag or commit hash) recorded in `config/hermes-version.txt` | Hermes is fast-evolving; configuration validated against one version may not hold against the next. SHA pinning of `SOUL.md` and `config.yaml` is only meaningful for the pinned version. |
| B2 | **Verify the exact disable mechanism** for skill formation and persistent memory against the pinned version's official docs. Record the verified config block in `hermes/config.yaml` and a notes file. Cover every file named in the §3 table — `MEMORY.md`, `USER.md`, `memories/users/<id>/USER.md`, `state.db`, `skills/`, `SOUL.md`, `config.yaml`. Also locate and document the **Kanban backing store** (likely a table in `state.db` or a sibling SQLite under `~/.hermes/`); confirm it is separable from the memory schema (i.e., workers can keep Kanban writes enabled while memory writes stay disabled) and record the file path plus the table or schema name. | Earlier draft invented env-var names that don't exist in current Hermes. Don't install with unverified switches. The Kanban is the operational value that justifies Hermes for batch resilience (see §5); if the Kanban is welded to the memory features we're disabling, the configuration approach has to be revisited before install. |
| B3 | **Decide local vs cloud model class** for the determinism acceptance test. ✅ Resolved: local llama.cpp + Qwen 3.6 MTP on the AI machine. Cloud models cannot guarantee bit-exact reproducibility and are out of scope for Acceptance Test #4. | Without this decision, the determinism criterion has indeterminate semantics. |

### 3.2 Runtime topology — gateway vs worker

There are two distinct Hermes runtimes in this pipeline, and the §3 restrictions apply differently to each. The split exists because the user-facing **Telegram interface** requires a long-running daemon, while the **research execution** must remain stateless and deterministic per task.

```
┌──────────────────┐         ┌──────────────────┐         ┌──────────────────┐
│  Telegram        │  enq    │   Kanban         │  pop    │  Worker          │
│  Gateway         │ ──────▶ │   (durable)      │ ──────▶ │  (one task,      │
│  (long-running)  │         │                  │         │   disposable     │
│                  │ ◀────── │                  │ ◀────── │   HERMES_HOME)   │
└──────────────────┘  status └──────────────────┘  result └──────────────────┘
```

**Gateway runtime** — one process per project, runs for the lifetime of the deployment.

| Property | Value |
|---|---|
| Started by | `hermes gateway setup` once, then `hermes gateway run` (or equivalent for the pinned version). Verify exact CLI per B2. |
| Process lifetime | Long-running. Survives across many Telegram messages. |
| `HERMES_HOME` | Persistent, project-pinned (e.g., `metabolicum-agentic-research/hermes/gateway-home/`). NOT disposable. |
| `state.db` | Used for Telegram session routing only. Sessions hold message history per Telegram thread so the gateway can resolve replies; no memory-feature writes (`memory.memory_enabled: false`, `memory.auto_write: false`). |
| `SOUL.md`, `config.yaml` | Pinned from the repo, same SHA-256 enforcement as workers. |
| `MEMORY.md`, `USER.md`, `memories/users/`, `skills/` | Must not exist or must be empty. Asserted at gateway start and via Acceptance Test #7. |
| Role | Control plane: receive Telegram message → authorize sender → enqueue task on Kanban → return run id → surface status / result back to Telegram thread. **Never executes research work itself.** |
| LLM calls | Only the small "router" calls needed to interpret an incoming Telegram message and decide which task to enqueue. No Stage-2/3 model calls. |

**Worker runtime** — one process per task, dies when the task finishes.

| Property | Value |
|---|---|
| Started by | Kanban worker pool (`hermes kanban work` or equivalent) spawning a subprocess per pulled task. |
| Process lifetime | One task, then exit. |
| `HERMES_HOME` | **Disposable**, recreated per task at e.g. `metabolicum-agentic-research/runs/<run_id>/hermes-home/`. Deleted (or retained as an audit artifact) at task end. Acceptance Tests #4, #5, #7 apply unchanged. |
| `SOUL.md`, `config.yaml` | Pinned from the repo, copied into the disposable `HERMES_HOME` at task start. SHA-256 asserted. |
| All other Hermes restriction rows (Skill Formation, Persistent Memory, Cross-Stage Visibility, Self-Improvement, Multi-Turn Autonomy, Tool Discovery) | Apply in full as defined in §3. |
| Role | Execute exactly one stage of exactly one source × marker job per the agent-prompts (Stage 2 extractor, Stage 2 tagger, Stage 2 structurer, Stage 3 council, Stage 5 legal, etc.). |
| Kanban | Workers pull tasks from the same Kanban the gateway writes to. The Kanban's heartbeat / reclaim / zombie-detection / hallucination-recovery features (§5) apply at this layer. |

**Telegram setup notes**:

- Gateway is configured via `hermes gateway setup` and a selected Telegram adapter (verify exact CLI flags against the pinned version per B2).
- A Telegram bot token plus an allowlist of authorized chat ids must live under the project secrets boundary (per §10 secrets policy), never in `~/.hermes/` or the gateway's `HERMES_HOME`.
- Authorization is per-user: every incoming message must resolve to an allowlisted Telegram user id before any task is enqueued. The gateway does not enqueue from unauthorized senders.
- The gateway exposes a fixed verb set on Telegram: `/queue <marker>`, `/status <run_id>`, `/cancel <run_id>`, `/last`, `/help`. Free-form prompts are interpreted by the gateway's lightweight router only, and any ambiguity returns a clarification instead of speculative enqueue.

**Scope ordering.** The first acceptance pass (§4) exercises **only the worker runtime** on a single cached source. The gateway + Telegram interface and the durable-Kanban resilience test land afterward as named follow-ups in §5. Until then, tasks are enqueued via direct CLI / API calls to the Kanban.

### What We Keep
- **Model-agnostic routing:** local llama.cpp `llama-server` over OpenAI-compatible endpoint (see §1.1). Hermes supports any OpenAI-compatible backend; llama.cpp is the chosen one.
- **Structured output:** Native JSON mode or forced schema (to be validated against §04 contract).
- **Tool calling:** Read file, write file, query Supabase, submit output. Fixed, enumerated.
- **Observability:** Logging every tool call and response for replay.

---

## 4. Acceptance tests

These checks must hold after the Hermes install and before the pipeline runs real markers. They are pass/fail; any failure surfaces a configuration problem to be fixed before proceeding.

### Operational metadata

| Field | Value |
|---|---|
| **Hermes version pinned** | `[TODO: tag or commit hash]` (recorded in `config/hermes-version.txt` before install) |
| **Acceptance code location** | `metabolicum-agentic-research/code/` |
| **Model class for determinism test** | Local llama.cpp + Qwen 3.6 MTP on AI machine only (see §1.1). Cloud models cannot guarantee bit-exact reproducibility and are out of scope for Acceptance Test #4. |
| **External-provider boundary** | Acceptance tests use local inference only. Any cloud call is out of scope unless explicitly approved. |
| **MCP support** | Out of scope. Our tools are fixed (read file, write file, Supabase query, submit output). |

### Test Task

Run the full Stage 2 chain on **one cached source transcript** (e.g., a practitioner blog post or podcast transcript from the `sources` table): content extractor → marker tagger → demographic structurer.

**Input:**
- `source.transcript.json` (immutable)
- `marker_glossary.json`
- `practitioner_aliases.json`
- Schema-locked prompts from `agent-prompts/01-content-extractor.md`, `02-marker-tagger.md`, and `03-demographic-structurer.md`

**Expected Output:**
- JSON array of `MarkerRecommendation` objects conforming to section four.
- Every recommendation has `applies_to_markers`, `verbatim_quote`, numeric value or range when present, `units`, `direction`, `population`, `speaker_or_author`, `cited_paper`, `paradigm`, `extraction_model`, and `extractor_confidence`.
- No inferred qualifiers. No invented markers. If the source is silent about a demographic qualifier, the corresponding `PopulationQualifier` field is `null` and `applies_to` is `unspecified`.

### Criteria

| # | Criterion | Threshold | Test method |
|---|---|---|---|
| 1 | **Schema compliance** | 100% of output validates against the section-four `MarkerRecommendation`, `PopulationQualifier`, and `CitedPaper` contracts | Pydantic or JSON Schema validation; reject if any row fails |
| 2 | **Verbatim fidelity** | Every numeric claim has a verbatim quote ≥1 sentence | Quote must appear as substring of fetched source after whitespace normalization |
| 3 | **No hallucination** | Zero invented markers; zero inferred demographic qualifiers | Diff claim markers against `marker_glossary`; `PopulationQualifier` fields must be `null` if source is silent and `applies_to` must be `unspecified` unless the source states a population |
| 4 | **Determinism (canonicalized)** | Across 3 isolated runs (local llama.cpp + Qwen 3.6 MTP on the AI machine, temp 0, seed pinned), outputs are **semantically equivalent** under: sort JSON keys, normalize array order where order is not semantically meaningful, ignore whitespace. Byte-identical preferred but not required. If MTP breaks byte-equivalence, disable MTP for this criterion and re-enable for production. | Run × 3 with disposable `HERMES_HOME` each time; pipe through canonicalizer; diff. Test artifact records model name, version, GGUF SHA-256, llama.cpp commit/tag, runtime, seed, and whether MTP was enabled. |
| 5 | **State isolation across runs** | No state read or reused across isolated runs; all run artifacts confined to the run directory | Set `HERMES_HOME=<run_dir>/hermes-home/`; delete/recreate between each of the 3 runs; verify run N+1 cannot read or be influenced by run N's `memories/`, `state.db`, `skills/`, sync cache, or any other persisted surface |
| 6 | **Observability** | Full tool-call log replayable from a single artifact | Structured log: timestamp, tool name, inputs, outputs, model identity, turn index. Replay must reproduce final output under the determinism rules in #4 |
| 7 | **Restriction enforcement (per §3 row)** | Every row in §3 restriction table independently verified as enforced | For each row: a specific test that proves the restricted behavior cannot occur. Skill formation: assert `HERMES_HOME/skills/` is empty post-run. Memory: assert `memories/` and `state.db` empty. Self-improvement: assert prompt file SHA-256 unchanged across runs. Multi-turn autonomy: assert run terminates at exactly the configured max-turn or earlier via `submit_output`. Tool discovery: assert no tool was called that wasn't in the manifest. |
| 8 | **Multi-agent handoff isolation** | Stage 2's three agents (extractor → tagger → structurer) run as separate isolated Hermes tasks with file-system handoff, without enabling cross-task memory | Three sequential tasks; each receives only the previous task's `state.json` output; assert no Hermes-internal context carries over (Criterion #5 applies between them) |
| 9 | **Mid-run error handling** | If a tool call fails mid-task, Hermes terminates with a recordable error state (quarantine signal); does not retry indefinitely, hang, or partial-output | Inject a deliberate tool failure (e.g., Supabase query 500). Run must exit within bounded time with a clear failure record. |
| 10 | **Schema-violation rejection** | A prompt designed to elicit a non-schema-compliant response must be detected and rejected by the runtime, not passed downstream | Feed a forced bad-output prompt. Hermes must either prevent emission or surface a validation failure; under no circumstance should garbage reach the `submit_output` channel as success |

Financial conflict validation is not part of the Stage 2 acceptance pass because it requires a seeded section-sixteen practitioner registry and the Stage 3 council-decider prompt. A Stage 3 add-on test is run separately once the registry is loaded.

### Failure handling

A failure on any criterion is a configuration defect to fix, not a reason to swap runners. Typical fixes: tighten the §3 disable config, fix the prompt/schema binding, fix the runner harness, adjust the deterministic-seed plumbing. The pipeline does not run real markers until all ten criteria pass.

---

## 5. Durable Kanban — Wave-3 readiness

The acceptance pass in §4 exercises one cached source through one Stage 2 chain. It **does not exercise** the durable multi-agent Kanban. Heartbeat, zombie detection, hallucination recovery, and batch resumability only matter at multi-task scale.

**A batch-resilience test is required before Wave-3 (674 markers) can run on Hermes.** Scope:

- Run 50 ingestion tasks in parallel, then SIGKILL 10 of them mid-run.
- Verify the Kanban marks them as zombies, retries them cleanly, and produces complete output for all 50.
- Verify no banned memory features (skill formation, MEMORY.md, cross-task context) re-enable themselves under the Kanban's retry semantics.
- Inject schema-violation outputs on 5 random tasks; verify the hallucination-recovery loop catches and re-prompts, not silently passes through.

If this test fails, Wave-3 is held back until the Kanban configuration is corrected. The Kanban readiness test is independent of the Stage 2 acceptance pass.

---

## 6. Sequence

1. Setup blockers B1–B2 cleared (B3 already resolved): pinned Hermes version recorded, disable mechanisms verified against pinned-version docs, Kanban store path documented.
2. Create the `metabolicum-agentic-research` git repository, deploy the §04 Supabase schema, lay down the project secrets boundary.
3. Pin `hermes/SOUL.md` and `hermes/config.yaml` in the repo with the verified disable block.
4. Install Hermes at the pinned version.
5. Run the §4 acceptance tests against one cached source fixture.
6. Fix any failures, re-run until all ten criteria pass.
7. Run the five-marker pilot.
8. Run the §5 Kanban readiness test.
9. Run the Wave-3 batch.
