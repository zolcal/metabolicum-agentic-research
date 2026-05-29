# Metabolicum MO pipeline rebuild — index

Author: Zoltan. Status: standalone specification for implementation-framework design.

This document set is the standalone specification for the Metabolicum agentic research pipeline. Every load-bearing technical, legal, and capability claim belongs inside these files. This is not the implementation. It is the contract that constrains the implementation.

## Project boundaries

There are three different projects in scope, and this document set must keep them separate.

| Project | Role | Boundary |
| --- | --- | --- |
| `metasync` | Production Metabolicum application | Hosts the user-facing web app, production Supabase, user accounts, payments, dashboards, calculators, evaluators, and any PHI-adjacent user data. The agentic research pipeline must not run inside this repository or use production database credentials. |
| `metabolicum-research` | Legacy research workspace | Holds the historical `research/`, `output/`, and `inventory/` trees that pre-date the agentic pipeline. Referenced as a data source for legacy SM/RC content where useful, but not the home of these planning documents (migrated into `metabolicum-agentic-research/docs/agentic-workflow/` on 2026-05-23). Not the target implementation repository or target database. |
| `metabolicum-agentic-research` | Standalone agentic research project | Home of this document set and the rebuilt pipeline. Has its own Git repository, Supabase project, local filesystem/runtime folders, secrets, run artifacts, and implementation code. Its contracts are defined by this document set. |

The future `metabolicum-agentic-research` project may emit reviewed SQL or structured export artifacts for controlled import into `metasync`, but it is not part of the production app and must remain credential-isolated from it.

## Reading order

The intended reading order moves from philosophy to architecture to specifications to operational concerns. Read `00-executive-summary.md` first for the one-page version, then `01-philosophy-and-principles.md` for the smart-and-frugal-but-visionary ethos, then `02-architecture-overview.md` for the pipeline diagram and data flow. From there, sections three through seven cover the agents themselves and their cross-cutting responsibilities — social discovery (basic research uses YouTube, podcasts, and public web; X/Twitter, Telegram, and LinkedIn are deferred to the content-discovery maintenance phase), content extraction, council validation, provenance, and legal vetting. Sections eight through eleven address infrastructure choices: framework, memory and vector architecture, orchestration, and scoring methodology. Sections twelve and thirteen cover delivery goals, constraints, repository policy, and production handoff. Section fourteen lists open questions that the user must resolve before implementation can begin. Section fifteen defines the self-contained evidence rating system used by scoring and provenance. Section sixteen defines the practitioner and source directory system used by discovery, scoring, and conflict flagging. Section seventeen defines research target envelopes: for basic research these are the brief's stripped SM rows used as a soft alignment reference, with an optional private envelope-fact layer for non-publishable internal goals; both steer and evaluate research convergence without becoming evidence, citations, or production data, and both are withheld from discovery and extraction and revealed only to the council. Section eighteen defines the SQL-compatible research output ingestion contract for ranges, source artifacts, learn-page narrative, references, and citation links. Section nineteen defines the Hermes input pointer framework: the per-wave research brief is the pipeline trigger — SM range YAMLs stripped to reference rows and enhanced with compact pointers (videos, practitioners, PMIDs, DOIs, URLs, queries) to guide research, with ranking diagnostics kept in a sidecar rather than the brief. Section twenty defines semantic practitioner matching: how e5 embeddings bridge thesaurus gaps when matching practitioners to markers. Section twenty-one defines the table-to-claims conversion rule: tables are detected by the extractor but must be structurally converted into population-qualified claims before they enter the research database.

## Self-contained contracts

The practitioner and source registry is defined locally in `16-practitioner-directory-system.md`. The evidence rating system is defined locally in `15-evidence-rating-system.md`. The research target envelope-fact contract is defined locally in `17-research-target-envelopes.md`. The research output ingestion contract is defined locally in `18-research-output-ingestion-contract.md`. Runtime data contracts are defined in `04-research-agents-spec.md`, `06-provenance-and-chain-of-evidence.md`, `07-legal-and-ip-agent.md`, `10-orchestration-and-filesystem.md`, and `11-scoring-methodology.md`. Implementation must not depend on outside repositories, archived notes, or unlisted files as authority.

## Conventions

Sentence-case headings throughout. Em dashes with spaces on both sides. The tag `[JUDGMENT]` marks a reasoning-grounded recommendation. The tag `[EXTRAPOLATION]` marks a projection beyond what sources directly support. The tag `[TODO]` marks an item that requires user input before implementation.
