# Scoring methodology

Scoring is a core property of the research output, not an afterthought. Default practitioner/source weights are defined in section sixteen. A runtime `scoring_config.yaml` may override these values, but the document-set default is authoritative until changed here.

Evidence grading is defined inside this document set, not delegated to another repository. Section fifteen is authoritative for the sub-grade vocabulary, ordering, and default scalar mapping. Every evidence-bearing record carries an `evidence_sub_grade`, including the `P1` and `P2` preclinical branch, and derives `evidence_grade` from the first letter. The digit is an ordinal strength marker within its parent tier: `1` is strongest, higher numbers are weaker.

Each BiomarkerClaim carries four scores, each in the range zero to one. Signal strength is from Stage 1: source tier weight multiplied by surface priority weight, engagement score, and recency decay. Evidence grade is from Stage 2 and Provenance, using the default scalar table in section fifteen unless `scoring_config.yaml` overrides it. Council consensus is from Stage 3: 1.0 if extractor, reviewer, and decider all agreed; lower if they disagreed. Anthropological specificity rewards qualified claims: a claim qualified for "adult women aged 40 to 55 with insulin resistance" scores higher than a generic claim.

Default source tier weights are:

| Tier | Weight |
| --- | ---: |
| A | 1.00 |
| B | 0.75 |
| C | 0.50 |
| D | 0.25 |

Default signal components are defined as follows. `source_tier_weight` comes from the table above. `surface_priority_weight` comes from section sixteen. `engagement_score` is a platform-normalized value between zero and one: use the percentile rank of the item among comparable items on the same platform and source surface, with missing engagement set to `0.50` rather than zero. `recency_decay` is a bounded freshness multiplier: `1.00` for sources published or updated within the current review window, decaying toward `0.50` for older but still relevant sources. Evergreen guidelines, books, and foundational papers can be pinned at `0.75` or higher when the registry marks them as foundational.

This gives the default signal formula:

```
signal = source_tier_weight × surface_priority_weight × engagement_score × recency_decay
```

Exact per-platform engagement inputs are implementation details, but the normalized score must be stored with the candidate so reviewers can explain why a source ranked highly.

`[JUDGMENT]` The composite combines these via a weighted geometric mean, so that a zero in any dimension kills the composite:

```
composite = (signal^w1 × evidence^w2 × consensus^w3 × specificity^w4)^(1/(w1+w2+w3+w4))
```

The composite weights `w1` through `w4` come from `scoring_config.yaml`. The default is all weights equal to one, which gives an unweighted geometric mean. We tune after the pilot.

Default council consensus is `1.00` when extractor, reviewer, and decider agree on marker, quote validity, paradigm, and evidence sub-grade. Minor disagreement resolved by the decider scores `0.75`. Major disagreement with an approved claim scores `0.50` and should surface for review. Claims that cannot clear the council are quarantined, not scored.

Default anthropological specificity is `0.40` for unspecified population, `0.60` for one meaningful qualifier, `0.80` for two or more coherent qualifiers, and `1.00` when marker, population, sex or age band, comorbidity context, units, and target direction are all explicit in the source.

Uncertainty is expressed through confidence intervals on every score. Variance across extractor, reviewer, and decider gives the consensus CI. A discrete quantum from the section-fifteen evidence-grade calibration gives the evidence-grade CI. Bootstrap over signal sources gives the signal CI. The composite CI is computed by Monte Carlo with 10,000 samples.

The financial-conflict flag is a separate boolean property of the claim, not a numeric component of the composite. The reason is that financial conflicts are informational, not disqualifying — a practitioner who sells ApoB testing is not less correct about ApoB simply by virtue of having that commercial interest. The flag surfaces in the dashboard and in downstream consumer surfaces so that users and reviewers can apply their own discount factor. This design surfaces known conflicts rather than pretending to judge what the pipeline cannot know.

Research target envelopes do not contribute to the composite score. They have `evidence_weight = 0` by contract and are never treated as source, signal, evidence, consensus, or specificity. Envelope alignment is stored separately in `claim_envelope_evaluations`, with an optional primary status on `biomarker_claims` for filtering. It is used to decide whether discovery has converged, contradicted the internal goal, or needs more open-source work. This keeps the scoring model clean: public claims are scored from public evidence, while private goals guide iteration without laundering hidden information into the score.

The UI consequences are useful. The dashboard can sort by composite, filter by minimum composite, and surface high-divergence claims where consensus is low but signal is high. These are the most interesting cases for manual review — practitioners are saying something loudly, but our models cannot agree on what they meant.
