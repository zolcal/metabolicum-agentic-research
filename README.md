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
| `docs/agentic-workflow/` | Authoritative specification: 18 numbered section files + `hermes-setup.md` + `README.md` + the dated `REVIEW-2026-05-21-llm-access.md`. Migrated from legacy `metabolicum-research/` on 2026-05-23. `docs/agentic-workflow/internal/` holds non-agent-visible audit history (SM-range generation reports, frozen-anchor review). The operational guidance for each stage is in the corresponding section file (§02 architecture, §05 council, §06 provenance, §07 legal, §10 orchestration + state.json, §18 export shape, `hermes-setup.md` for acceptance tests). |
| `docs/policies/` | Vendored policy docs the Hermes agent reads at runtime (e.g. `RANGE-STATUS-COLOR-POLICY.md`). Upstream sources cited inline in each file. |
| `fixtures/` | Fixture sources for the Hermes acceptance pass. `fixtures/sources/<id>.json` holds one cached transcript per fixture and must validate against `code/schemas/source_fixture.schema.json`. |
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

## What's in this project

Everything Hermes needs at runtime — spec contracts, schemas, prompts, policies, inputs. Hermes never reaches outside this tree.

**Contracts the agent enforces** (all readable from project boundary):

- [docs/agentic-workflow/04-research-agents-spec.md](file:///home/zoltan/Projects/metabolicum-agentic-research/docs/agentic-workflow/04-research-agents-spec.md) — full §04 SQL schema + `MarkerRecommendation`
- [docs/agentic-workflow/05-validation-council.md](file:///home/zoltan/Projects/metabolicum-agentic-research/docs/agentic-workflow/05-validation-council.md) — council process
- [docs/agentic-workflow/06-provenance-and-chain-of-evidence.md](file:///home/zoltan/Projects/metabolicum-agentic-research/docs/agentic-workflow/06-provenance-and-chain-of-evidence.md) — PMID/DOI resolution
- [docs/agentic-workflow/07-legal-and-ip-agent.md](file:///home/zoltan/Projects/metabolicum-agentic-research/docs/agentic-workflow/07-legal-and-ip-agent.md) — quote-length, license, ToS rules
- [docs/agentic-workflow/10-orchestration-and-filesystem.md](file:///home/zoltan/Projects/metabolicum-agentic-research/docs/agentic-workflow/10-orchestration-and-filesystem.md) — file-system + `state.json`
- [docs/agentic-workflow/15-evidence-rating-system.md](file:///home/zoltan/Projects/metabolicum-agentic-research/docs/agentic-workflow/15-evidence-rating-system.md) — A1–E3 + P1/P2
- [docs/agentic-workflow/16-practitioner-directory-system.md](file:///home/zoltan/Projects/metabolicum-agentic-research/docs/agentic-workflow/16-practitioner-directory-system.md) — registry + COI
- [docs/agentic-workflow/17-research-target-envelopes.md](file:///home/zoltan/Projects/metabolicum-agentic-research/docs/agentic-workflow/17-research-target-envelopes.md) — envelope firewall
- [docs/agentic-workflow/18-research-output-ingestion-contract.md](file:///home/zoltan/Projects/metabolicum-agentic-research/docs/agentic-workflow/18-research-output-ingestion-contract.md) — §18 export shape
- [docs/policies/RANGE-STATUS-COLOR-POLICY.md](file:///home/zoltan/Projects/metabolicum-agentic-research/docs/policies/RANGE-STATUS-COLOR-POLICY.md) — status alias + canonical palette + State A/B/C

**Operational entry point for the runtime:**

- [docs/agentic-workflow/hermes-setup.md](file:///home/zoltan/Projects/metabolicum-agentic-research/docs/agentic-workflow/hermes-setup.md) — Hermes restriction model, runtime topology (gateway vs worker), acceptance tests

## Operator concerns (not in this tree)

Setup gate, install blockers, and the broader operator runbook live in [the planning workspace runbook](file:///home/zoltan/Projects/metabolicum-research/docs/HERMES-RUNBOOK.md). Hermes never needs to read those — by the time Hermes is running, they're already resolved.

Pipeline deliverables aren't a checklist — they're approved `biomarker_claims` rows in Supabase and golden §18 exports at [fixtures/expected/wave-0/](file:///home/zoltan/Projects/metabolicum-agentic-research/fixtures/expected/wave-0/). The definition of "done" per marker is the eight criteria in [docs/agentic-workflow/hermes-setup.md](file:///home/zoltan/Projects/metabolicum-agentic-research/docs/agentic-workflow/hermes-setup.md) (and the operator runbook).
