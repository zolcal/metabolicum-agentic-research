# Hermes MO runtime: no-quarantine, iterate-discovery, SM-as-sanity

**Date:** 2026-05-30
**Status:** Design approved verbally (numbers locked); spec for review before implementation.
**Scope:** the MO (metabolic-optimization) live runtime loop in `metabolicum-agentic-research`. Does NOT touch the SM or RC paradigms, the SM-anchor firewall, or the brief-generation phase (frozen 2026-05-30).

## Problem

The current Stage 3-6 chain has three claim dispositions: `{approve, quarantine, reject}`. **Quarantine assumes a human review queue that does not exist** — quarantined claims are dead data. Worse, a quarantined marker just ends empty with no attempt to do better.

Evidence (`runs/wave0-live-20260529/fasting-insulin.json`): fasting-insulin produced 0 range_facts. All 4 "claims" were quarantined and, on inspection, were **off-marker garbage** — three were LDL / TG-HDL claims mis-tagged to fasting-insulin with paraphrased (non-verbatim) quotes; one was a TG/HDL claim the council disagreed on. So quarantine was *correctly* rejecting bad claims, but there was no mechanism to then **go find real fasting-insulin sources**.

## Goals

1. **Eliminate quarantine.** Every claim reaches a terminal verdict: `{approved, rejected}`. Rejected claims are written to an **audit log** (reason + quote + source) — a record, not a pending queue.
2. **Iterate discovery.** Per marker, if too few claims are approved, the search agent finds **new** sources and tries again, up to a bounded limit.
3. **Use SM ranges as a sanity bound, never a conformance target.** SM filters implausible values; it does not punish legitimate MO divergence.

## Terminal reject reasons (all logged, none quarantined)

| code | meaning | triggers discovery widening? |
|------|---------|------------------------------|
| `quote_not_verbatim` | reviewer re-fetched the source and could not substring-match the quote | yes |
| `marker_mismatch` | claim content is about a different marker than the brief (e.g. LDL claim tagged to fasting-insulin) | yes |
| `sm_sanity_fail` | value implausible vs SM (see rule below) | yes |
| `council_disagreement` | the 3 council families do not materially agree | yes |

A claim is **approved** iff: (1) its quote verbatim-verifies in the fresh-fetched source, AND (2) it is about the brief's marker, AND (3) it passes the SM sanity check, AND (4) the council materially agrees. Otherwise **rejected** (logged).

## SM sanity rule (the only SM gate)

Given the marker's SM envelope `[sm_low, sm_high]` (council-only, from `input/sm-ranges/`) and a claim value/bounds `V`:

- **Wrong sign** — `V <= 0` for a physically-positive marker → reject.
- **Order of magnitude off** — any bound `> 10 * sm_high` or `< sm_low / 10` → reject. (Catches "ApoB 8000" and unit-confusion errors: mg/dL↔g/L, nmol/L↔mg/dL.)
- **Otherwise pass.** A merely *aggressive* MO value (e.g. ApoB < 60 vs SM < 90, fasting insulin < 5 vs SM < 25) is well within 10× → **approved**, and gets an alignment label (`narrower | wider | contradictory`) — NOT a reject.
- **No SM range for the marker** → sign + absurdity checks only (no 10× band available).

SM retains its other two existing jobs unchanged: it is the SM paradigm's own published output, and the council's alignment annotation. SM stays at `evidence_weight=0`.

## The per-marker loop

```
STOP_COUNT = 2          # approved MO claims needed to stop searching
MAX_ROUNDS = 3          # widening rounds
MAX_NEW_SOURCES = 12    # new sources fetched per marker (whichever cap hits first)

approved = []
seen_sources = {}
round = 0
while len(approved) < STOP_COUNT and round < MAX_ROUNDS and len(seen_sources) < MAX_NEW_SOURCES:
    sources = (brief.recommended_sources if round == 0
               else widen(brief.recommended_search_queries, broaden=round))  # new, unseen sources
    for s in sources (capped at MAX_NEW_SOURCES total):
        claims = extract(s)                      # Stage 2, live (llama-server)
        for c in claims:
            verdict = council_judge(c)           # approve | reject(reason)  — NO quarantine
            (approved if verdict.approved else rejection_log).append(c)
    round += 1

# terminal
if approved: assemble -> range_facts -> persist(agentic Supabase) -> export(output/)
else:        marker terminal = "no_mo_support_found"   # clean, NOT quarantine
```

- `widen()` reuses the spec's existing discovery rule (§02: recommended sources first, then `recommended_search_queries`, then broader web/youtube/podcast search), deduping against `seen_sources`.
- Cost ceiling per marker ≈ `MAX_NEW_SOURCES` × (~$0.03 extraction + council ~$0.045/claim) → low single dollars worst case.

## Components

- **`code/pipeline/iterate.py` (new):** owns the loop above — the marker-level controller. Calls existing `code/discovery/*` (Stage 1, live) and `code/pipeline/stages.py` (Stage 2, live), then `council_llm` / `legal` / `assembly`.
- **`council_llm.py` / `legal.py` (modify):** disposition becomes binary `{approve, reject(reason)}`; remove the "pending manual review" / quarantine branch. Add `marker_mismatch` and `sm_sanity_fail` checks (SM sanity in the council, where the SM reference is already dereferenced).
- **`persist.py` + `code/db.py` (modify):** replace the `quarantine` write with a `rejection_log` write (terminal rejects: `claim_id, marker, reason_code, verbatim_quote, source_id, run_id`). Update `_WRITES` FK order. This is also the **first real `--write`** to the agentic Supabase.
- **`orchestrate.run_marker_live` (modify):** delegate to `iterate.py` instead of consuming a pre-made claims file.
- **Export:** the deterministic §18 `range_facts` projection → `output/` (reviewed artifact / import.sql). Manual gate before any metasync import is unchanged.

## Non-goals
- Not loosening the verbatim-quote requirement (the anti-fabrication core stays).
- Not building prescreen / parallelism (separate scaling work).
- Not writing to production metasync (only the agentic Supabase).

## Risks
- A marker may legitimately terminate at 0 ("no MO support found"). Valid; surfaced in the run report.
- Live quote-verification remains the dominant reject cause; that's intended (it's the fabrication guard).
- First-ever DB write — verify FK order + enum conformance on the first run; inspect rows before scaling.

## Acceptance / demo
- **fasting-insulin** runs end-to-end live through the new loop → either ≥1 verifiable range_fact **persisted to the agentic Supabase + exported to `output/`**, or a clean `no_mo_support_found` terminal with a populated `rejection_log`. **Zero quarantine rows anywhere.**
- **hba1c** (recommended plumbing-proof — it already yields 5 real claims) runs end-to-end → ≥1 range_fact persisted + exported, proving the DB-write + export path on a marker with genuine claims, independent of fasting-insulin's discovery outcome.
