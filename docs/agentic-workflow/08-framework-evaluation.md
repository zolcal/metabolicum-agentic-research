# Agent framework evaluation

This section evaluates the major agent frameworks available in May 2026 against our specific needs: production stability, observability, multi-agent coordination, structured output guarantees, model-agnosticism across providers including non-US model families, and compatibility with our file-system stage pattern.

| Framework | License / lang | Strength | Weakness | Verdict |
| --- | --- | --- | --- | --- |
| Hermes Agent (Nous Research) | MIT / Python | Persistent memory, skill formation, native MCP, OpenAI-compatible endpoints, durable multi-agent Kanban with heartbeat and hallucination recovery | Requires explicit disable configuration to enforce stateless execution | **Selected runner** (decision 2026-05-22). Configuration contract in `hermes-setup.md`. |
| LangGraph | MIT / Python | Production durability, deterministic state machines, native LangSmith tracing, natural fit for file-system stages; v0.4 added state persistence + human-in-the-loop checkpoints | Verbose | Available as fallback if Hermes ever needs replacement |
| CrewAI | MIT / Python | Fast prototyping, clean role abstraction; Flows event-driven mode added 2025–2026 | Weak logging, lagging observability | Not the primary candidate for this workflow |
| AutoGen / Microsoft Agent Framework | MIT / Python | Established multi-agent patterns | Microsoft shifted focus to MAF; AutoGen feature development slowed | Don't start new projects on AutoGen |
| Pydantic-AI | MIT / Python | Schema-first design, native Pydantic validation, Logfire observability, model-agnostic across major providers, MCP/A2A support | Adopting it makes Pydantic a runtime commitment | Evaluate as a structured-output layer, not the assumed inner-agent layer |
| Mastra | Apache 2.0 / TypeScript | Production deployments at Replit, PayPal, Sanity, Brex | TypeScript; our pipeline is Python | Skip for the research pipeline |
| DSPy | MIT / Python | Declarative prompt optimization given evals | Not an orchestrator | Re-evaluate later for extractor prompt tuning |
| Letta (formerly MemGPT) | Apache 2.0 / Python | Best memory architecture in the field (MemFS git-tracked memory) | Our pipeline is stateless per run; persistent memory belongs in Supabase | Skip |

**Hermes Agent is the selected runner** (decision 2026-05-22). It runs as a stateless task executor against the LLM access layer in `REVIEW-2026-05-21-llm-access.md`: local Qwen via llama-server for extraction roles, cloud council endpoints through the endpoint registry, and fixed tool manifests. The configuration contract and acceptance tests live in `hermes-setup.md` (§3 restriction table, §4 acceptance criteria, §5 Kanban readiness). LangGraph, Pydantic-AI, and CrewAI remain available as fallback options if a future Hermes setback ever forces a runner change, but they are not the assumed path.
