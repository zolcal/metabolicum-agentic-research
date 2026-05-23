# Hermes Agent Setup — Configuration and Acceptance Contract

> **Status:** Hermes selected as the pipeline runner (decision 2026-05-22). The earlier "spike vs custom runner" framing is retired.
> **Purpose:** Configuration contract and acceptance tests for the Hermes install in `metabolicum-agentic-research`.
> **Constraint:** Hermes runs as a **stateless task executor**, not an autonomous self-evolving agent.

---

## 1. Statelessness Requirement

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

## 2. Hermes Restriction Model

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

Setup blockers, installation sequence, and host provisioning live in the operator runbook outside this agent tree. This file keeps only the runtime contract Hermes workers must satisfy.

### 2.1 Runtime Topology — Gateway vs Worker

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
| Role | Execute exactly one stage of exactly one source × marker job per the prompts (Stage 2 extractor, Stage 2 tagger, Stage 2 structurer, Stage 3 council, Stage 5 legal, etc.). |
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

## 3. Acceptance Tests

These checks must hold after the Hermes install and before the pipeline runs real markers. They are pass/fail; any failure surfaces a configuration problem to be fixed before proceeding.

### Operational metadata

| Field | Value |
|---|---|
| **Hermes version pinned** | `[TODO: tag or commit hash]` (recorded in `config/hermes-version.txt` before install) |
| **Acceptance code location** | `metabolicum-agentic-research/code/acceptance/` plus `code/canonicalizer.py` |
| **Model class for determinism test** | Local llama.cpp + Qwen 3.6 MTP on AI machine only (see §1.1). Cloud models cannot guarantee bit-exact reproducibility and are out of scope for Acceptance Test #4. |
| **External-provider boundary** | Acceptance tests use local inference only. Any cloud call is out of scope unless explicitly approved. |
| **MCP support** | Out of scope. Our tools are fixed (read file, write file, Supabase query, submit output). |

### Test Task

Run the full Stage 2 chain on **one cached source transcript** (e.g., a practitioner blog post or podcast transcript from the `sources` table): content extractor → marker tagger → demographic structurer.

**Input:**
- `fixtures/sources/<id>.json` expanded to `source.transcript.json` for the run (immutable; validates against `code/schemas/source_fixture.schema.json`)
- `marker_glossary.json`
- `practitioner_aliases.json`
- Schema-locked prompts from `prompts/01-content-extractor.md`, `prompts/02-marker-tagger.md`, and `prompts/03-demographic-structurer.md`

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
| 4 | **Determinism (canonicalized)** | Across 3 isolated runs (local llama.cpp + Qwen 3.6 MTP on the AI machine, temp 0, seed pinned), outputs are **semantically equivalent** under: sort JSON keys, normalize array order where order is not semantically meaningful, ignore whitespace. Byte-identical preferred but not required. If MTP breaks byte-equivalence, disable MTP for this criterion and re-enable for production. | Run × 3 with disposable `HERMES_HOME` each time; pipe through `code/canonicalizer.py`; diff. Test artifact records model name, version, GGUF SHA-256, llama.cpp commit/tag, runtime, seed, and whether MTP was enabled. |
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
