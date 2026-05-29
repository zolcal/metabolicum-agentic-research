# Sync note — brief-driven realignment (2026-05-29)

**Audience:** any agent (Codex, Claude, or human) working on the Hermes trigger / orchestrator.
**Status:** coordination note, not a spec. The authoritative contracts are the numbered `docs/agentic-workflow/` files. This note exists because concurrent sessions shared the working tree and the trigger work predated the doc realignment.

## What happened

The `docs/agentic-workflow/` spec set was realigned to the **brief-driven** architecture in commit `9a6feeb` (on `origin/main`). Files changed: **§00, §02, §03, §05, §10, §17, §18, §19** (§19 newly tracked) and the README. The **§04 SQL DDL is unchanged** and remains the schema authority.

If your trigger/orchestrator predates this, reconcile against it — **especially SM-ranges handling.**

## ① The big one for the trigger — SM-ranges visibility firewall

The SM rows ride *inside* the brief, but they are an **alignment reference, never an input/evidence range**. The orchestrator must gate visibility **by stage**:

- **Discovery + extraction run BLIND to the SM numbers.** They receive only marker identity, units, risk direction, and the brief's `recommended_search_queries`. Extraction must be byte-grounded in fetched sources.
- **SM rows are revealed ONLY at the Stage-3 council**, to assign `alignment_status` ∈ `aligned` / `narrower_than_envelope` / `wider_than_envelope` / `contradictory` / `not_comparable` (canonical **long forms** from the §04 DDL). `evidence_weight = 0`. Soft — `paradigm_divergence_flag: extreme` surfaces outliers, never auto-rejects.
- Rationale: a number the extractor never sees can't be anchored on or fabricated toward (anti-hallucination; ties to the project's zero-fabrication rule).

➡️ **Implication: do NOT pass the brief's SM rows into the discovery or extraction prompts.** Parse the brief, route the *pointer fields* to discovery, and hold the SM block for the council step only. Enforce this in the orchestrator, not by prompt instruction.

## ② Other deltas

- **Trigger unit is the WAVE** (a batch of markers under `input/hermes-briefs/<wave>/`), not a single marker. Stage 2 is per-source (one fetch serves every marker in the wave); assembly is per-marker.
- **Brief = search-seed only** (stripped SM rows + 6 pointer lists) and must stay **clean**: no scores / `_meta`. Ranking diagnostics (video scores, match terms) belong in a sidecar `input/hermes-briefs/<wave>/<marker>.index.json`.
  - ⚠️ The *current* brief files still carry a `_meta` block — they need regeneration. **Do not build the trigger to depend on `_meta`.**
- **Discovery scope (basic research):** YouTube + podcasts + public web/practitioner surfaces + PMID/DOI/Crossref + search-query fallback. **X/Twitter, Telegram, LinkedIn are deferred to a maintenance phase** — do not wire them for basic research. Meta is out.
- **§10 run layout:** `research_target_envelopes.sanitized.json` moved **out of `/discovery/` to the run root**, council-only (same firewall). `state.json` includes `"schema_version": "1"`. The `council/` folder gains `claim_envelope_evaluations.jsonl`.
- **§18 export surface is `range_facts`** (a deterministic projection of `biomarker_claims`), not the legacy `paradigm_ranges`.

## Read in this order

1. **§19** `19-hermes-input-pointer-framework.md` — the trigger contract (most relevant to you)
2. **§02** `02-architecture-overview.md` — architecture + the visibility-gate diagram
3. **§17** `17-research-target-envelopes.md` — envelope / firewall
4. **§10** `10-orchestration-and-filesystem.md` — orchestration + run layout
5. **§05** `05-validation-council.md` — how the council consumes SM rows

All on `origin/main` @ `9a6feeb`.

## Action

Align the trigger solution to the above — in particular, **never inject SM numbers into discovery or extraction.** If anything here conflicts with what you've already built, note the specific spot in this file (or a reply) so we can reconcile rather than diverge again.
