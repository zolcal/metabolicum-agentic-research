# Evidence rating system

This document defines the complete evidence rating vocabulary for the agentic research pipeline. The pipeline is intended to operate as its own project, database, repository, and filesystem implementation, so scoring is defined here as a standalone contract.

## Canonical scale

Every evidence-bearing artifact stores a specific `evidence_sub_grade`. The parent `evidence_grade` is derived from the first letter of the sub-grade.

Strongest to weakest:

```
A1 > A2 > A3 >
B1 > B2 > B3 >
C1 > C2 > C3 > C4 >
D1 > D2 > D3 >
P1 > P2 >
E1 > E2 > E3
```

The numeric suffix means strength within its parent tier: `1` is strongest, higher numbers are weaker. Parent tiers represent evidence families.

| Parent | Meaning |
| --- | --- |
| A | High-confidence interventional or synthesized clinical evidence |
| B | Strong clinical evidence |
| C | Moderate clinical or observational evidence |
| D | Emerging human evidence |
| P | Preclinical evidence |
| E | Guideline, expert opinion, theoretical, or unmapped evidence |

## Sub-grade definitions

| Sub-grade | Meaning |
| --- | --- |
| A1 | Meta-analysis of randomized controlled trials with large aggregate sample and low heterogeneity |
| A2 | Multiple randomized controlled trials with consistent results |
| A3 | Large prospective cohort with RCT confirmation |
| B1 | Single pre-registered randomized controlled trial with adequate sample size |
| B2 | Large prospective cohort study |
| B3 | Mendelian randomization study |
| C1 | Small randomized controlled trial |
| C2 | Prospective cohort study with moderate sample size |
| C3 | Case-control study |
| C4 | Large cross-sectional study |
| D1 | Pilot human study |
| D2 | Case series or case report |
| D3 | Human mechanistic or physiological evidence |
| P1 | Animal study |
| P2 | In vitro, cell-line, organoid, or non-human mechanistic model |
| E1 | Major guideline or consensus statement |
| E2 | Named expert or practitioner opinion |
| E3 | Theoretical framework, narrative hypothesis, or unmapped fallback |

## D3 versus P grades

`D3` is reserved for mechanistic or physiological evidence measured in humans. Examples include controlled human physiology studies, human tissue studies, human challenge studies, clamp studies, tracer studies, or other direct human measurements that explain a biological mechanism without necessarily proving clinical outcomes.

`P1` and `P2` are not human evidence. They can support biological plausibility and mechanism discovery, but they do not satisfy production-grade human mechanistic evidence by themselves.

## Scoring implications

The scoring lookup uses the canonical order above. `P1` and `P2` rank after `D3` and before `E1`.

Default scalar mapping for composite scoring is linear across the ordered sub-grades, strongest to weakest. `A1` maps to `1.00`; `E3` maps to `0.10`; intermediate grades are evenly spaced unless `scoring_config.yaml` overrides them. The document-set defaults are:

| Sub-grade | Scalar |
| --- | ---: |
| A1 | 1.00 |
| A2 | 0.95 |
| A3 | 0.89 |
| B1 | 0.84 |
| B2 | 0.79 |
| B3 | 0.74 |
| C1 | 0.68 |
| C2 | 0.63 |
| C3 | 0.58 |
| C4 | 0.52 |
| D1 | 0.47 |
| D2 | 0.42 |
| D3 | 0.36 |
| P1 | 0.31 |
| P2 | 0.26 |
| E1 | 0.21 |
| E2 | 0.15 |
| E3 | 0.10 |

Preclinical evidence can raise plausibility, but it cannot by itself clear a production publication threshold that requires human evidence. For MO ranges, `D3` can satisfy the Layer 2 mechanistic/physiological evidence requirement when the cited source is genuinely human. `P1` and `P2` can support the mechanism narrative but leave the human-mechanistic layer incomplete unless paired with a qualifying human source.
