# metabolicum-agentic-research

**Scope rule:** this tree is Hermes-only. It holds the agentic research project's source code, inputs, outputs, runs, secrets, and pinned Hermes configuration. **Nothing else.**

The authoritative specification is `docs/agentic-workflow/` in this repo (migrated from the legacy `metabolicum-research/` workspace on 2026-05-23). This repo must satisfy its own contracts (§04 schema, §10 file-system layout, §17 envelope firewall, §18 export projection).

## Host-level infrastructure (outside this tree)

```
/media/zoltan/4TSSD/
├── metabolicum-agentic-research/   ← this project (Hermes-only)
├── ops/
│   ├── host-setup/scripts/         ← one-time host migration scripts
│   └── llama-server/               ← LLM backend service (llama.cpp + Qwen 3.6 MTP)
│       ├── launch-qwen-mtp.sh
│       ├── README.md
│       └── logs/llama-server.log
├── llama.cpp/                      ← llama.cpp source + build (shared tool)
├── models/                         ← GGUF model files (shared)
├── hf-cache/                       ← HuggingFace cache (HF_HOME)
├── conda-envs/                     ← conda envs for shared tooling
└── docker/                         ← Docker data-root
```

## Project layout

| Dir | Purpose |
|---|---|
| `code/` | Hermes runtime code (`llm_client.py`, schemas, harness). |
| `code/schemas/` | JSON Schemas: `state.schema.json` (stage handoff), `extracted_claim.schema.json` (Stage 2 constrained-decoding). |
| `config/` | Endpoint registry (`llm-endpoints.yaml`), per-stage tool manifests (`tools.yaml`), pinned Hermes version (`hermes-version.txt`, once B1 is cleared). |
| `docs/HERMES-RUNBOOK.md` | **Operational entry point for the Hermes runtime.** Post-install, this is what Hermes reads first: pre-conditions checklist, per-stage runbook, council orchestration, storage targets, definition-of-done per marker, failure modes. Everything else (specs, policies, prompts, schemas) is referenced from here. |
| `docs/agentic-workflow/` | Authoritative specification: 18 numbered section files + `hermes-setup.md` + `README.md` + the dated `REVIEW-2026-05-21-llm-access.md`. Migrated from legacy `metabolicum-research/` on 2026-05-23. `docs/agentic-workflow/internal/` holds non-agent-visible audit history (SM-range generation reports, frozen-anchor review). |
| `docs/policies/` | Vendored policy docs the Hermes agent reads at runtime (e.g. `RANGE-STATUS-COLOR-POLICY.md`). Upstream sources cited inline in each file. |
| `fixtures/` | Fixture sources for the Hermes acceptance pass. `fixtures/sources/<id>.json` holds one cached transcript per fixture. |
| `hermes/` | Pinned Hermes persona + config (`SOUL.md`, `config.yaml`). Copied into each disposable `HERMES_HOME` at run start; SHA-256 must match across runs (acceptance test #7). The gateway's persistent `HERMES_HOME` lives at `hermes/gateway-home/` once the Telegram interface lands; it is gitignored. |
| `input/` | Agent-visible inputs. |
| `input/sm-ranges/` | SM range YAMLs: 5 pilot samples + waves 1 (108), 2 (109), 2b (90), 3 (674). Source for `sm_anchors` seeding and SM bulk ingestion. |
| `input/registry/` | Marker identity registry (`marker-identity-registry.v1.yaml`, 1,110 markers). |
| `input/marker_glossary.json` | Stage 2 marker tagger glossary (5 pilot markers + aliases). |
| `output/` | Approved per-marker SQL artifacts and other terminal exports. |
| `prompts/` | Role-locked agent prompts (extractor, tagger, structurer, council decider, legal reviewer). |
| `runs/` | Per-run artifacts (`/runs/<timestamp>/discovery/...` per spec §10). Each run's disposable worker `HERMES_HOME` lives at `runs/<timestamp>/hermes-home/`; subtrees are gitignored. |
| `supabase/migrations/` | SQL migrations targeting the `metabolicum-agentic-research` Supabase project. `0001_initial.sql` deploys the full §04 schema. |
| `secrets/` | `.env` (gitignored). `.env.example` lists variable names only. |
| `scripts/` | Hermes-specific scripts (install, preflight, acceptance harness). |

## What does NOT belong here

- Host-machine migration scripts (fstab edits, Docker data-root moves, HF cache moves) → `../ops/host-setup/scripts/`
- LLM backend service files (llama-server launch, logs, tuning notes) → `../ops/llama-server/`
- General tooling shared across projects (llama.cpp source, GGUF models, HF cache, conda envs) → other top-level dirs under `/media/zoltan/4TSSD/`
- General tooling and unrelated docs from the legacy `metabolicum-research/` workspace

## LLM backend

This project's agents talk to `http://127.0.0.1:8080` (OpenAI-compatible). That endpoint is served by llama-server, configured at `/media/zoltan/4TSSD/ops/llama-server/`. See `ops/llama-server/README.md` for operator details.

## Install-time gate

One-pass setup checklist. Each item is detailed as a pre-condition in `docs/HERMES-RUNBOOK.md` §2 and asserted by `scripts/preflight.sh`. When everything below is green, Hermes is ready to enqueue tasks. After install, this checklist is not revisited — subsequent progress is pipeline output, not setup work.

**Scaffolding (done):**

- [x] Project bootstrapped + git initialized
- [x] LLM endpoint registry + adapter (`config/llm-endpoints.yaml`, `code/llm_client.py`) — smoke-tested 2026-05-21
- [x] Per-stage tool manifests (`config/tools.yaml`)
- [x] §04 schema captured as `supabase/migrations/0001_initial.sql`
- [x] JSON Schemas for `state.json` and `MarkerRecommendation` (`code/schemas/`)
- [x] 5 role-locked prompts (`prompts/`)
- [x] `hermes/SOUL.md` persona drafted
- [x] Spec set internalized at `docs/agentic-workflow/` (single source of truth)
- [x] Color policy vendored at `docs/policies/RANGE-STATUS-COLOR-POLICY.md`
- [x] Inputs in place: SM YAMLs, registry, marker glossary, wave-0 acceptance set
- [x] `docs/HERMES-RUNBOOK.md` — operational entry point for the runtime

**Remaining install items:**

- [ ] **B1** — pin Hermes version in `config/hermes-version.txt`
- [ ] **B2** — verify disable mechanisms against pinned-version docs; fill `hermes/config.yaml`
- [ ] Provision hosted Supabase project; apply `0001_initial.sql`; verify CHECK constraints (paradigm_affinity, canonical_color)
- [ ] Drop ≥1 cached source transcript per pilot marker into `fixtures/sources/`
- [ ] Install Hermes at pinned version
- [ ] `scripts/preflight.sh` passes (asserts every pre-condition in RUNBOOK §2)
- [ ] §4 acceptance tests in `docs/agentic-workflow/hermes-setup.md` — all 10 pass against a fixture source

## After install: pipeline deliverables

Once the install-time gate is green, Hermes starts producing output. Deliverables aren't a checklist — they're the pipeline doing its job. Progress shows up as approved `biomarker_claims` rows in Supabase and golden §18 exports at `fixtures/expected/wave-0/<slug>.expected.yaml`. The definition of "done" per marker is in `docs/HERMES-RUNBOOK.md` §4 Stage 6.
