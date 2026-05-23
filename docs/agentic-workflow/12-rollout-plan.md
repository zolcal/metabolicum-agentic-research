# Delivery goals and constraints

This document sets outcome goals and redesign triggers. It does not prescribe the implementation framework's sequencing or runner mechanics.

The first release target is five pilot markers:

- TG/HDL ratio
- HbA1c
- ApoB
- Lp(a)
- fasting insulin / HOMA-IR

These markers were chosen because they stress different parts of the system. TG/HDL and fasting insulin are MO-heavy and practitioner-language-heavy. HbA1c is SM-heavy but has meaningful MO divergence. ApoB and Lp(a) test lipidology, causal-evidence interpretation, and cross-marker tagging.

The implementation is successful when:

- the standalone `metabolicum-agentic-research` project exists with separate Git, Supabase, local runtime filesystem, and secrets boundary
- the core contracts exist for `sources`, `claims`, `source_claim_marker`, `biomarker_claims`, `sm_anchors`, `research_target_envelopes`, `claim_envelope_evaluations`, `provenance`, `legal_reviews`, `quarantine`, marker glossary, and optional citation edges
- section-fifteen evidence lookup, marker normalization, practitioner aliases, COI severity, and semantic discovery metadata are enforced
- research target envelope facts exist for pilot markers as sanitized internal goals, with private derivation material excluded from agent inputs and export artifacts
- source-first ingestion processes each source once and can tag multiple markers from one source
- approved claims have verbatim quotes, source URLs, retrieval timestamps, evidence sub-grades, provenance status, legal status, and conflict metadata
- rejected or uncertain claims are preserved in quarantine with reason codes
- the internal review surface can sort by composite score, filter by paradigm, show high-divergence claims, and expose financial-conflict detail
- controlled export/import artifacts are produced for `metasync`, with manual approval before production import

Several failure modes should trigger redesign rather than delay:

- discovery produces too few high-quality claims for a pilot marker
- open-source claims do not converge on the research target envelope after adequate discovery
- open-source claims repeatedly contradict the envelope, indicating either a bad envelope or a real disagreement that needs human review
- verbatim quote rejection is frequent enough to indicate extractor hallucination
- cross-marker tagging is so low that the source-first design is not paying off
- council disagreement is high enough to suggest source quality, prompt design, or model diversity problems
- quarantine volume is high but reason codes are too vague to guide fixes

The implementation must report enough metrics to make those triggers concrete. Minimum operational metrics are:

- source discovery count by platform, marker, and source tier
- approved, rejected, and quarantined claim counts by marker and reason code
- verbatim quote rejection rate
- council disagreement rate
- evidence-chain completion rate
- legal quarantine rate
- cross-marker tagging rate
- duplicate source hit rate
- provider retry and failure counts

`[JUDGMENT]` Pilot defaults: investigate if verbatim quote rejection exceeds 20%, council disagreement exceeds 40%, evidence-chain completion falls below 80%, or legal quarantine exceeds 15%. These are redesign triggers, not hidden scoring penalties. Provider routing, resource-use thresholds, and fallback policies are orchestration-runtime decisions and may be adjusted without changing this contract.

What the first implementation does not do is also worth being explicit about. It does not add Pinecone, Qdrant, Weaviate, Mem0, or Temporal. It does not add Facebook, Instagram, or LinkedIn beyond manual seeds. It does not activate the PM paradigm. It does not build user-facing UI beyond the internal dashboard. It does not introduce multi-tenant pipelines.

Hermes Agent is the selected runner (decision 2026-05-22); the runtime framework decision is settled. The configuration contract and acceptance tests live in `hermes-setup.md`. The data and artifact contracts in §04 and §18 remain the gating discipline regardless of runner.

## Deferred decisions

The following decisions are intentionally left to the implementation framework or later calibration:

- semantic embedding model choice and thresholds, while preserving prior `multilingual-e5-large` and 0.76-threshold research as calibration evidence
- local GPU model tier and exact fallback models, while requiring every extraction to record `extraction_model`
- full multilingual discovery beyond pilot-language support
- existing corpus calibration, pending corpus availability inside `metabolicum-agentic-research`
- network-derived authority scoring, while optionally collecting citation edges for future evaluation
