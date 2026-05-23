# metabolicum-agentic-research

**Scope rule:** this tree is Hermes-only. It holds the agentic research project's source code, inputs, outputs, runs, secrets, and pinned Hermes configuration. **Nothing else.**

The authoritative specification lives in the sibling `metabolicum-research/docs/agentic-workflow/` doc set until a later migration. This repo must satisfy those contracts (§04 schema, §10 file-system layout, §17 envelope firewall, §18 export projection) regardless of where the spec is hosted.

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
| `docs/` | Project-specific docs. Includes `docs/policies/` — vendored policy docs the Hermes agent needs at runtime (e.g. `RANGE-STATUS-COLOR-POLICY.md`). The agentic-workflow spec set still lives in legacy `metabolicum-research/docs/agentic-workflow/` until a later migration. |
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
- The agentic-workflow specification doc set (lives in legacy `metabolicum-research/docs/agentic-workflow/`)

## LLM backend

This project's agents talk to `http://127.0.0.1:8080` (OpenAI-compatible). That endpoint is served by llama-server, configured at `/media/zoltan/4TSSD/ops/llama-server/`. See `ops/llama-server/README.md` for operator details.

## Setup status

- [x] Endpoint registry + adapter (`config/llm-endpoints.yaml`, `code/llm_client.py`) smoke-tested 2026-05-21.
- [x] Per-stage tool manifests (`config/tools.yaml`).
- [x] SM range inputs migrated from legacy (986 YAMLs across pilots + 4 waves).
- [x] Marker identity registry migrated.
- [x] Agent prompts (5 role files) copied from legacy.
- [x] §04 schema captured as `supabase/migrations/0001_initial.sql`.
- [x] JSON Schemas for `state.json` and `MarkerRecommendation` drafted.
- [x] `hermes/SOUL.md` persona drafted (config flag wording pending B2).
- [x] `marker_glossary.json` seeded for 5 pilot markers.
- [ ] **B1**: pin Hermes version in `config/hermes-version.txt`.
- [ ] **B2**: verify disable mechanisms against the pinned version's docs; fill in `hermes/config.yaml`.
- [ ] Supabase project provisioning (hosted, separate from `metasync`).
- [ ] One fixture source dropped into `fixtures/sources/`.
- [ ] Install Hermes at pinned version.
- [ ] Run the §4 acceptance tests from `metabolicum-research/docs/agentic-workflow/hermes-setup.md`.
