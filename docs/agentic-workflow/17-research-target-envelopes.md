# Research target envelopes

Research target envelopes are internal-use range references for steering and evaluating research, never for proving it. For basic research the envelope is the public SM anchor rows carried in each marker's brief (section 19); optionally it also includes private internal target facts where such non-publishable goals exist. Envelopes define what the agentic research workflow is trying to discover, confirm, contradict, or refine from open-source evidence. They are not evidence, not citations, not scores, not production data, and not user-facing medical claims.

The reason for the envelope layer is practical. Some target ranges are known before the agentic workflow begins because of internal research, internal judgment, or non-publishable sources. The agentic workflow should be allowed to use those values as research goals, but it must not launder their origins into the claim database. The public evidence still has to be discovered from legitimate open-source material and pass extraction, council, provenance, legal review, and manual handoff.

## Operational envelope for basic research

For basic research, the operational envelope is the canonical SM range file that each marker's brief references via a council-only `sm_reference` (section 19); the brief itself carries no SM numbers. These are public population reference intervals from the frozen SM wave, not a private seed, and they exist for one purpose: to judge the alignment of already-extracted MO claims. They are a soft reference, not a rigid gate — a claim that falls outside them is flagged for review, never auto-rejected — and it was always intended this way.

The richer private envelope-fact model defined in the rest of this section is an optional layer, used only for markers where internal, non-publishable target ranges exist. Whether the envelope is the SM file behind a brief's `sm_reference` or a private fact, the same firewall applies: it is never in the brief, and only the validation council resolves it (sections 2 and 19). It never becomes an input range, evidence, a citation, a score, or production data.

## Boundary rules

Every envelope has two forms:

- private derivation artifact: source-bearing human-audit file that explains where the envelope came from and why its bounds were chosen
- sanitized envelope fact: source-free row or file record containing only the operational range goal, context qualifiers, readiness state, and use-policy flags

The private derivation artifact is never passed to discovery agents, extraction agents, council agents, scoring, legal review, assembly, export artifacts, or `metasync`. The sanitized envelope fact may be used to focus search terms, decide when discovery has probably converged, and flag contradictions that need more work.

Required use-policy flags:

```yaml
use_policy:
  publishable: false
  evidence_weight: 0
  disclose_origin_to_agents: false
  export_to_metasync: false
```

These flags are not advisory. If any flag would need to be true for a workflow step, that step is outside this contract.

## Atomic fact model

Research target envelopes are represented as atomic sanitized facts, not copied source tables and not necessarily one row per marker. This mirrors the range-fact model used for stratified marker ranges: every valid contextual row becomes its own fact, while display choices and private derivation stay separate.

One marker may have a broad fallback envelope and many more specific envelope facts. For example, a marker may need separate facts by age, sex, weight, BMI, ethnicity, altitude, pregnancy status, specimen, method, assay, or population cohort. A generic adult envelope is useful as a search seed, but it must not erase more granular open-source ranges discovered later.

The generation rule is: source granularity wins. If open-source research finds a credible table, image, PDF, guideline, or practitioner page with more detailed context than the private seed, the workflow preserves that context as candidate range facts and evaluates them against the nearest compatible envelope facts. It does not collapse them into a broad all-population target.

## Envelope fact fields

```yaml
research_target_envelope_fact:
  id: rtef_<marker>_<paradigm>_<context>_<version>_<order>
  marker: string
  paradigm: SM | RC | MO
  envelope_version: string
  range_order: integer
  units: string
  specimen: null | string
  method: null | string
  variant: null | string
  direction: below | above | between | at
  target:
    value: null | number
    low: null | number
    high: null | number
  tolerance:
    low: null | number
    high: null | number
  context:
    sex_for_lab_reference: null | female | male | string
    gender: null | string
    age_min: null | number
    age_max: null | number
    weight_min: null | number
    weight_max: null | number
    bmi_min: null | number
    bmi_max: null | number
    ethnicity: null | string
    altitude_meters: null | number
    cohort: null | string
    pregnancy_status: null | string
    stratum: null | string
    population_scope: null | string
    population: {}
  display_role: null | primary | supporting | fallback | not_for_display
  primary_goal: boolean
  readiness_state: ready | draft | insufficient
  generation_method: string
  context_note: null | string
  derivation_hash: null | string
  use_policy:
    publishable: false
    evidence_weight: 0
    disclose_origin_to_agents: false
    export_to_metasync: false
  created_at: datetime
  updated_at: datetime
```

`range_order` defines display precedence when multiple envelope facts for the same marker overlap. Lower numbers are more specific. Example: `1` = sex- and age-specific fact, `2` = sex-specific fact, `3` = general adult fact. The council uses `range_order` to select the most specific comparable envelope fact before falling back to broader facts.

`target` is the expected research goal. `tolerance` is the wider guard band used for discovery and contradiction handling. For one-sided markers, the unused side remains `null`. For example, a lower-is-better marker may have `target.high` and `tolerance.high` while `target.low` remains `null`.

`readiness_state` controls whether the fact can guide a run. `ready` means the fact is usable for agentic discovery. `draft` means it can be reviewed by humans but should not steer agents. `insufficient` means the marker or context exists but the input data does not support an envelope fact yet.

`display_role` does not make the fact public. It only helps reviewers distinguish primary goals from fallback or supporting facts while keeping display policy separate from range storage.

## What envelopes may do

Envelopes may:

- focus discovery queries toward numeric claims relevant to a marker and context, without exposing the target numbers to the discovery agent
- help the council classify discovered claims as aligned, wider, narrower, contradictory, or not comparable
- identify markers and strata that need more source discovery
- show when open-source evidence is converging around the internal goal
- show when the internal goal likely needs correction
- seed broad discovery when no stratified input exists

Envelopes may not:

- approve a claim
- auto-reject a claim that falls outside the envelope — out-of-envelope claims are flagged for review, not dropped
- enter discovery or extraction prompts — they are revealed only to the council
- replace a source URL, quote, PMID, DOI, or citation
- increase an evidence grade
- contribute to the composite score
- be exported to `metasync`
- be published or shown to users
- be used to infer a claim that no source actually stated
- force open-source findings into the same granularity as the private seed

## Convergence statuses

The council assigns an `alignment_status` for each comparable `(biomarker_claim, envelope_fact)` pair — this is the same `alignment_status` annotation referenced in sections 2 and 19:

| `alignment_status` | Meaning |
| --- | --- |
| `aligned` | The open-source claim falls inside the target or tolerance envelope fact. |
| `narrower_than_envelope` | The claim is more restrictive than the envelope fact. |
| `wider_than_envelope` | The claim is broader or less restrictive than the envelope fact. |
| `contradictory` | The claim points in a materially different direction or outside tolerance. |
| `not_comparable` | Units, population, direction, specimen, method, or context do not match closely enough. |

These statuses are research workflow signals only. They do not change legal approval or evidence scoring.

An envelope fact with zero `claim_envelope_evaluations` rows is treated as having no open-source support yet. This is an envelope-level derived status computed from the link table — `COUNT(*) = 0` per envelope — not a claim-envelope relationship, and therefore not part of `alignment_status`.

## File placement

For basic research the operational envelope is the canonical SM range file the brief references via `sm_reference` (section 19); only the council dereferences it, resolving it into `council/sm_alignment_reference.json`. It is never embedded in the brief. Private derivation artifacts belong outside run folders and outside export paths. The canonical sanitized envelope facts live in the `research_target_envelopes` table defined in section four. At run start, the runner may generate `research_target_envelopes.sanitized.json` from ready table rows as a transient run artifact. The sanitized file contains envelope facts only. It must contain no source names, source URLs, proprietary notes, non-public provenance, or references to external project history.

The `research_target_envelopes` table is an operational store and comparison contract, not a publication surface. Claim-to-envelope comparisons are persisted in `claim_envelope_evaluations`.

## Generation principle

Envelope generation should prefer broad, defensible bounds when multiple good internal data points exist, but broad does not mean context-blind. The default rule is inclusive rather than aggressive: preserve the range of plausible good data, then use the tolerance band to absorb uncertainty and population variation.

When the private input is less granular than later open-source research, the open-source context becomes part of the research record as separate candidate facts. The private envelope remains a goal and comparison tool, not a constraint on what the research workflow is allowed to discover.

The generation algorithm and actual marker values are intentionally separate from this documentation section. The contract here defines how envelopes may be used safely; the data-generation pass creates the marker-specific envelope facts under this boundary.
