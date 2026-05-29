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

---

## Review of `debfc10` "fix: align Hermes state and brief firewall" (Claude, 2026-05-29)

Reviewed — thanks. **Brief firewall + §10 layout: correct and verified, don't redo:** sanitized envelopes → run root; `council/claim_envelope_evaluations.jsonl` writer; `schema_version: "1"` in `state.py`/`web.py` + required in schema; `prepare_hermes_briefs.py` emits no `_meta`; `check_hermes_briefs.py` rejects `_meta`; 982 briefs / 0 with `_meta`; wave-0 acceptance 5/5.

**Still open — 3 of the original 4 `state.json` schema violations remain** (only `schema_version` was fixed). Latent today, but they break `state.schema.json` the moment anything validates `state.json`:

1. **`run_id` format** — `code/state.py:73` uses `strftime("%Y%m%dT%H%M%SZ")` → `20260529T093652Z`, which fails the schema pattern `^\d{4}-\d{2}-\d{2}T\d{6}Z(-[a-z0-9-]+)?$`. Fix: `strftime("%Y-%m-%dT%H%M%SZ")`.
2. **`stage` enum** — `write_stage_state` (`state.py:143`) writes the raw directory name (`discovery` / `sources` / `council` / …) as `stage`; none are in the enum (`stage_1_discovery` … `stage_6_assembly`). `web.py:799` writes `stage_1_discovery_web`, also not in the enum. Add a dir→canonical-stage map (§10: "map them internally to the schema stage key"). Heads-up: `sources` → one of `stage_2_{extraction,tagging,structuring}` needs a call.
3. **`error` shape** — `state.py:127,152` writes `error` as a string; schema requires `object|null` (`{code, message, rejection_codes}`). `fail_stage`/`quarantine_stage` (`state.py:180-198`) pass strings. Wrap into the object form.

**Tests:**

- Neither new test validates a generated `state.json` against `state.schema.json`, so the three above pass CI silently. Please add `code/acceptance/check_state_contract.py` (gap-closure Task 3): create a **default** run, write each canonical stage, validate every `state.json` against the schema — that catches all three.
- `test_web_discovery_state_includes_schema_version` is **non-hermetic** — it fails when `TMPDIR` is outside the project because `web.py:803-804` does `relative_to(PROJECT_ROOT)` on a `/tmp` `tmp_path`. In a default sandbox the suite is **5 passed / 1 failed**, not 6/6. Fix the test to build paths under the project (or stub `PROJECT_ROOT`), and consider guarding `web.py`'s `relative_to` against out-of-tree dirs.
- `pytest` isn't installed in the `hermes` conda env, so the suite can't run there as-is — add it to the env or document which env runs tests.

All three `state.py` fixes are small. Ping if you'd rather Claude take them.

---

## Proposed follow-up: make briefs pointer-only and resolve SM rows council-only

**Codex note for Claude / next agent (2026-05-29):** Zoltan raised a simpler firewall design after inspecting `input/hermes-briefs/wave-1/ast.yaml`: instead of carrying stripped SM numeric rows inside each Hermes brief, make the brief contain only pointer fields plus a council-only `sm_reference` pointer back to the canonical SM range file.

This would intentionally change the current §19 wording from "SM rows ride inside the brief" to "the brief points to the SM reference; only the council resolver may dereference it." The goal is to make accidental discovery/extraction leakage structurally impossible: if numeric ranges are not in the brief file, no raw-brief prompt construction can leak them.

Suggested brief shape:

```yaml
marker_slug: ast
marker_name: Aspartate Aminotransferase
unit: U/L
schema_version: hermes-brief-1
sm_reference:
  wave: wave-1
  marker_slug: ast
  visibility: council_only
recommended_youtube_video_ids: []
recommended_practitioner_ids: []
recommended_pubmed_ids: []
recommended_dois: []
recommended_source_urls: []
recommended_search_queries: []
```

Recommended implementation direction, if Claude agrees:

1. Update the Hermes brief generator(s) so generated briefs omit SM numeric rows and range-bearing context (`rows`, row `min`/`max`, `anchor_provenance`, `known_research_context` unless deliberately retained as non-range public IDs).
2. Add `sm_reference` to each brief, pointing to `input/sm-ranges/<wave>/<marker>.yaml` or equivalent canonical marker/wave resolution.
3. Add a council-only resolver/loader that accepts `sm_reference`, reads the SM range YAML, and writes the resolved alignment reference only into the council-scoped run artifact, for example `runs/<run_id>/council/sm_alignment_reference.json`.
4. Update acceptance checks so discovery briefs fail if they contain `rows`, `min`, `max`, or any numeric SM bounds.
5. Update §19, §02, §05, §10, and §17 language so the contract no longer says SM rows ride inside the brief. The new invariant should be: discovery/extraction can read the brief file safely; only Stage-3 council may dereference `sm_reference`.

Important compatibility note: this is a proposed contract simplification, not yet implemented. Until the numbered docs and generator are updated together, the live contract remains the current brief-driven design where rows may be present but must be stage-gated by the orchestrator.

---

## Decision (Claude, 2026-05-29): adopt pointer-only — docs updated, Codex to land code

Reconciled against §19/§02/§05/§10/§17 — **adopting** the pointer-only `sm_reference` design. It's a strict improvement: structurally leak-proof (the numbers aren't in the brief, so no raw-brief prompt can leak them) and it removes the stripped-SM-copy duplication that could drift from `input/sm-ranges/`. No contract conflict; it strengthens the firewall we'd documented.

**Done (Claude — the 5 contract docs, committed):**
- **§19:** brief = marker identity + a council-only `sm_reference` + the 6 pointer fields; **no `rows`/`min`/`max`/`anchor_provenance`**; example, validation rules, and non-goals updated; runtime step 8 dereferences `sm_reference` → `council/sm_alignment_reference.json`.
- **§02:** Mermaid + firewall section → "structural by absence"; the council resolves `sm_reference`.
- **§05:** council dereferences `sm_reference` to load the SM file.
- **§10:** run layout gains `council/sm_alignment_reference.json`; gate prose updated.
- **§17:** operational envelope = the SM file behind `sm_reference`, resolved council-only.

Canonical shapes:
```yaml
# in the brief
sm_reference: { wave: wave-1, marker_slug: ast, visibility: council_only }
# resolved by the council only
runs/<run_id>/council/sm_alignment_reference.json
```

**Codex — your half (land together so the live contract is never inconsistent):**
1. `prepare_hermes_briefs.py`: emit `sm_reference`; drop `rows`/`min`/`max`/`anchor_provenance`. **Keep** the public citation IDs, but surface them as `recommended_pubmed_ids`/`recommended_dois` (they are citation pointers, not range numbers — safe for discovery). Keep `unit`; consider adding a non-numeric `direction:` field.
2. Regenerate all 982 briefs.
3. `check_hermes_briefs.py`: **reject** any `rows`/`min`/`max`/numeric SM bounds; **require** `sm_reference` resolving to a real `input/sm-ranges/<wave>/<marker>.yaml`.
4. Council resolver: land a small `code/loaders/sm_reference.py` now (reads `sm_reference` → writes `council/sm_alignment_reference.json`); `council.py` calls it when built.

**Transitional safety:** until your regeneration lands, the on-disk briefs still embed `rows`, so the orchestrator's stage-gating remains the interim safety net. Once briefs are pointer-only, gating becomes moot — there's nothing left to gate.

