# Orchestration and file-system pattern

The user's existing pattern places each agent in its own input folder for configuration and its own output folder for results, with the pipeline culminating in one SQL file per marker per paradigm. This section evaluates alternatives and recommends keeping and formalizing that pattern with one small adjustment.

Among the alternatives, database-driven state — using Supabase as the single source of truth — has the advantage of being transactional and unified. The disadvantage is that every run mutates the database, replay becomes hard, and debugging happens via SQL rather than file inspection. With the separate research project, this becomes more attractive because research mutations do not affect production, but file-system intermediates remain inspectable in ways database rows are not. Event-driven orchestration — Temporal, Inngest, BullMQ — has serious momentum in 2026. OpenAI's VP of Application Infrastructure said at Replay 2026 that "Temporal's durable orchestration framework is critical to handling our massive scale, complex agentic workflows" (The New Stack, retrieved 2026-05-13). And per the Inngest blog (retrieved 2026-05-13), "In late 2025, durable execution crossed the chasm into the early majority." All of this is real, but the contract does not require that machinery. Flat-file orchestration is simpler, the on-disk artifacts are inspectable by humans and reviewer models, and `git diff` between runs is a debugging superpower. Git-based orchestration, with each agent committing and the next agent reviewing pull requests, has audit trail appeal but is slow and Git was not designed for this kind of high-velocity workflow.

`[JUDGMENT]` The recommended pattern is a hybrid: file-system per-run, the `metabolicum-agentic-research` Supabase project as canonical research store, and Git for reviewed export artifacts only.

Duplicate ingestion is prevented by source identity, not by trusting the runner. The canonical source key is the normalized URL plus platform and, where relevant, episode or post identifier. Before ingestion, the runner checks the `sources.url` uniqueness constraint and acquires a source-level lock in the research project or local run state. If two runs discover the same source, one run owns extraction and the other references the existing source row.

The proposed directory layout reflects the two-tier ingestion. A run is scoped to a wave and triggered by that wave's brief set (section 19): the orchestrator reads each marker's brief, routes the pointer fields to discovery, and withholds the stripped SM rows, releasing them only to the Stage 3 council (the visibility gate; sections 2, 17, 19). Each run lives under a timestamped folder. Within each run, the `discovery` folder holds the Stage 1 outputs from each active discovery agent (basic research: YouTube, podcasts, Reddit, web) plus a `ranked_sources.json` summary and `state.json` for handoff. The `sources` folder holds one subdirectory per ingested source, each containing the source metadata, the transcript, the extracted claims as JSON Lines, and a `state.json`. The `council` folder holds accepted and rejected claims and its own `state.json`. The `provenance` folder holds resolved and unresolvable entries. The `legal` folder holds approved, quarantined, and rejected entries. The `assembly` folder holds one subdirectory per marker, each containing the `artifact.sql`. A `run.log` at the root captures the full execution trace.

Static inputs live outside `/runs/`:

```
/input/
  /sm-ranges/
    /wave-0/
      apob.yaml                 # untouched SM reference anchor
    /wave-1/
      ...
  /hermes-briefs/
    /wave-0/
      apob.yaml                 # generated Hermes trigger: pointer fields + stripped SM rows
      apob.index.json           # diagnostics sidecar (scores/match terms); not a Hermes input
    /wave-1/
      ...
  /youtube-video-inventory/
    /videos/
      <video_id>.json           # metadata-only inventory (title, description, no transcript)
  /marker_glossary.json
  /practitioner_registry.json
```

Per-run artifacts:

```
/runs/
  /<run_timestamp>/                              # one run per wave
    research_target_envelopes.sanitized.json     # council-only; withheld from discovery + extraction
    /discovery/                                  # basic research: youtube, podcasts, reddit, web
      youtube.json
      podcasts.json
      reddit.json
      web.json
      ranked_sources.json
      state.json
    /sources/
      /<source_id>/
        source.json
        transcript.txt
        extracted_claims.jsonl
        state.json
    /council/
      accepted_claims.jsonl
      rejected_claims.jsonl
      claim_envelope_evaluations.jsonl
      state.json
    /provenance/
      resolved.jsonl
      unresolvable.jsonl
    /legal/
      approved.jsonl
      quarantined.jsonl
      rejected.jsonl
    /assembly/
      /<marker>/
        artifact.sql
    /run.log
```

Private source-bearing envelope derivation material does not live under `/runs/` and is not copied into agent input folders. The canonical envelope facts live in the `research_target_envelopes` table in the standalone research database. At run start, the runner queries ready rows and generates the transient `research_target_envelopes.sanitized.json` artifact for that run. The generated file contains only atomic envelope facts: marker, paradigm, unit, specimen, method, direction, population qualifiers, target bounds, tolerance bounds, readiness state, and use-policy flags. The sanitized file is not a source table and must not include source names, source URLs, proprietary notes, non-public provenance, or external project history. Because it carries target and tolerance bounds, the sanitized file is council-scoped: the orchestrator places it at the run root and injects it only into the Stage 3 council prompt, never into discovery or extraction (the visibility gate; sections 2, 17, 19). For basic research the council's alignment reference is the brief's stripped SM rows, supplied the same council-only way.

The rules are append-only writes, per-stage replayability, `state.json` as canonical handoff, no private envelope derivation material in run folders, and terminal `.sql` artifacts living in their own Git repo separate from the architecture documents, one per marker-paradigm pair.

The `state.json` handoff is intentionally small and stage-neutral. Each stage writes a JSON object with this shape:

```json
{
  "schema_version": "1",
  "run_id": "2026-05-21T190000Z",
  "stage": "stage_2_extraction",
  "status": "pending|running|completed|failed|quarantined",
  "input_files": ["relative/path/from/run/root.json"],
  "output_files": ["relative/path/from/run/root.jsonl"],
  "started_at": "2026-05-21T19:00:00Z",
  "completed_at": null,
  "model_endpoints": ["qwen-local"],
  "tool_manifest": "stage_2_extraction",
  "metrics": {
    "sources_processed": 0,
    "claims_emitted": 0,
    "provider_calls": 0
  },
  "error": null
}
```

`state.json` may record file paths, counts, endpoint IDs, timing, and terminal error summaries. It must not contain API keys, cookies, hidden envelope derivation notes, or full private source-bearing artifacts.

Run folders are retained while they are needed for audit and replay, but they are not an infinite storage promise. The default policy is to keep full run artifacts for active development and any run that produced exported claims; failed or exploratory runs may be compacted into state summaries, logs, and database rows after review. Deletion must never remove the canonical research database rows or the reviewed export artifacts.

The runner may maintain runtime state for provider limits, quotas, or usage tracking. The contract does not mandate specific quota fields, usage limits, or fallback thresholds — these are orchestration-runtime policies. The runner must record `extraction_model` per source so that quality and provider behavior are auditable after the fact. A dry-run mode may be provided by the orchestration agent to estimate resource use before committing to external provider calls.

Provider retry behavior is centralized. Transient network errors and provider rate limits use bounded exponential backoff with jitter and a maximum retry count. Permanent errors, authentication failures, paywall failures, and terms-of-service blocks do not retry indefinitely; they create quarantine or source-skip records with reason codes. Every provider call records provider, model or endpoint, request class, retry count, and terminal status.

Council agreement is a runner responsibility, not a fourth free-form agent. The runner executes the role-specific Stage 3 prompts as a linear three-family council: `04a-council-extractor.md`, then `04b-council-reviewer.md`, then `04c-council-decider.md`. The decider may approve only when the Stage 2 claim, independent extractor output, and reviewer verification facts materially agree on the quote, marker, paradigm, and financial-conflict posture. Any material disagreement is quarantined with `rejection_codes: ["council_disagreement"]`. Numeric fields, evidence sub-grade, and envelope-alignment differences are preserved for review rather than silently averaged.

Secrets belong to the standalone `metabolicum-agentic-research` project boundary. They are not stored in run folders, exported artifacts, architecture docs, or `metasync`. The implementation may use environment variables, a secrets manager, or Supabase-managed secrets, but the contract is that production `metasync` credentials are never available to the agentic pipeline and that logs redact keys, tokens, cookies, and signed URLs.

The runtime framework decision is intentionally deferred. Whatever runner is selected must write checkpoints to the `metabolicum-agentic-research` project or to local run state under that project's filesystem boundary. The file-system layout is for inspectable outputs and handoff artifacts; runtime-specific state must not live in `metasync` or the legacy `metabolicum-research` workspace.

The reason not to go pure event-driven is straightforward. Temporal and Inngest shine on large, concurrent, long-running workflow systems. This contract prioritizes inspectable artifacts, replayability, and source-level audit before orchestration sophistication. If future scale changes the operating model, the runner can revisit event-driven orchestration without changing the source-first data contracts.
