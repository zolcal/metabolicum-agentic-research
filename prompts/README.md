# Agent Prompts — Agentic Research Pipeline

This directory contains role-locked system prompts for the `metabolicum-agentic-research` pipeline. Each prompt is injected into the Hermes task runner as a single-step task with strict inputs and outputs.

## Design Principles

1. **No autonomy** — Agents do not decide what to do next. The pipeline decides which agent runs which task.
2. **No memory** — Each task is stateless. State lives in `state.json` files and Supabase, not in agent context.
3. **No web search** — Agents read cached source artifacts only. The pipeline fetches sources once.
4. **Schema enforcement** — All outputs are JSON with strict schemas. Invalid output = retry or quarantine.
5. **Hidden derivation** — Agents see SM row data and envelope facts only. Source families, licenses, paths, and hashes are excluded.

## Prompt Files

| # | File | Role | Stage | Input | Output |
|---|------|------|-------|-------|--------|
| 01 | [`01-content-extractor.md`](01-content-extractor.md) | Content Extractor | Stage 2 | Source transcript | Array of verbatim claims |
| 02 | [`02-marker-tagger.md`](02-marker-tagger.md) | Marker Tagger | Stage 2 | Verbatim claim + glossary | Marker slug list + match metadata |
| 03 | [`03-demographic-structurer.md`](03-demographic-structurer.md) | Demographic Structurer | Stage 2 | Verbatim claim + tags | `MarkerRecommendation` |
| 04a | [`04a-council-extractor.md`](04a-council-extractor.md) | Council Extractor | Stage 3 | `MarkerRecommendation` + cached source artifact | Independent claim re-extraction |
| 04b | [`04b-council-reviewer.md`](04b-council-reviewer.md) | Council Reviewer | Stage 3 | Claim + extractor output + source URL + anchors/envelopes | Quote/anchor/envelope verification facts |
| 04c | [`04c-council-decider.md`](04c-council-decider.md) | Council Decider | Stage 3 | Claim + extractor/reviewer outputs + registry | Approval/quarantine decision |
| 05 | [`05-legal-reviewer.md`](05-legal-reviewer.md) | Legal Reviewer | Stage 5 | Approved claim + source metadata | Legal gate decision |

## Stage Flow

```
Stage 1: Discovery (not in this directory; no role-locked Stage 1 prompt is currently checked in)
  ↓ fetched source artifact
Stage 2: Extraction
  01 Extractor → 02 Tagger → 03 Structurer
  ↓ MarkerRecommendation
Stage 3: Validation Council
  04a Council Extractor → 04b Council Reviewer → 04c Council Decider
  ↓ approved claim
Stage 4: Provenance resolution
  ↓ resolved/ambiguous/unresolvable provenance
Stage 5: Legal Review
  05 Legal Reviewer
  ↓ approved legal gate
Stage 6: Assembly → .sql artifact per marker × paradigm
```

The Stage 3 council is split into role-specific prompts. `04a-council-extractor.md` independently re-extracts from the cached source artifact, `04b-council-reviewer.md` verifies the source and compares anchors/envelopes, and `04c-council-decider.md` makes the final approval/quarantine decision. The runner preserves the three-family council by assigning those roles to distinct model families and quarantining any material disagreement between the Stage 2 claim, extractor output, reviewer facts, and decider judgment.

## Hermes-Specific Notes

- Use these prompts as **system messages** in Hermes' task definitions.
- Set `temperature: 0` for extractors, taggers, and structurers.
- Set `temperature: 0.2` for council roles and legal reviewers (slight variation helps cross-validation).
- Disable Hermes' persistent memory and skill formation for these roles. Use `state.json` handoff files instead.
- Hermes' Kanban is useful for running multiple Stage-1 discovery agents in parallel, but Stage 2 and 3 should be sequential per source.

## Provider-Agnostic Notes

These prompts use OpenAI-compatible function-calling / JSON mode. They work with:
- Gemini (via OpenAI compatibility layer)
- Local Qwen through llama-server or another OpenAI-compatible local endpoint
- Local models (llama.cpp, vLLM, Ollama) with JSON mode
- Claude (via Anthropic API, Bedrock, or OpenRouter)
- Grok only if a future sanctioned X-native endpoint is added to the LLM registry

Every prompt includes `<injected by pipeline>` placeholders for model identity, timestamps, and UUIDs. The pipeline must inject these before sending the prompt.

## Schema Validation

The pipeline (not the agent) is responsible for:
- JSON Schema validation of agent output
- Verbatim quote substring matching against cached source
- Duplicate stratum detection
- Forbidden key detection

Agents are told about schema constraints so they can self-correct on retry, but the pipeline is the ultimate validator.
