# HANDOVER-SESSION-11

## Date
2026-05-29

## Summary
Stabilized Hermes on the OpenAI Codex login path, upgraded the vendored Hermes agent to v0.15.2, documented skill-triage guidance for Claude, and clarified gateway/dashboard operation.

## Completed
- Fixed the immediate Hermes config issue by moving the live gateway runtime back to `openai-codex` / `gpt-5.5` via ChatGPT/Codex login instead of OpenRouter API spend.
- Investigated the earlier `TypeError: 'NoneType' object is not iterable` failure and confirmed it matched the upstream Codex null-output stream bug.
- Temporarily backported a local fix, then verified upstream Hermes already addressed it in newer releases.
- Upgraded the Hermes vendor submodule from `v2026.5.16` / Hermes `0.14.0` to `v2026.5.29.2` / Hermes `0.15.2`.
- Installed the upgraded release's missing test dependency into the existing Hermes `.venv`: `pytest-timeout==2.4.0` via `uv pip install --python ...`.
- Restarted the Hermes gateway after the upgrade; current gateway PID at handover time: `552261`.
- Verified a tiny live Codex request through `openai-codex` returned exactly `OK`.
- Appended skill-triage findings for Claude to `docs/agentic-workflow/SYNC-2026-05-29-brief-driven-realignment.md`.
- Explained operational commands for messaging gateway and browser dashboard.

## Key Decisions
- Use OpenAI Codex login (`openai-codex`, `gpt-5.5`) as the default Hermes provider for this project; avoid OpenRouter GPT-5.5 spend except by explicit decision.
- Keep `fallback_providers: []` in the live gateway config to avoid silent OpenRouter spending.
- Treat generic Hermes skills as operator aids unless a worker task manifest explicitly allows them. Pipeline workers remain governed by `hermes/SOUL.md`: stateless, fixed tools, no runtime skill/tool discovery.
- Do not install more generic skills now. Prefer small project-specific skills later: PubMed/NCBI, biomedical source discovery, Hermes brief guardrails, practitioner registry maintenance, and source-quality triage.
- `hermes-hudui` is not needed now. Use Hermes' built-in dashboard first; HUDUI may be useful later for operator visibility but is not aligned with strict stateless worker contracts.

## Verification
- `./run-hermes --version` reported `Hermes Agent v0.15.2 (2026.5.29.2)`.
- `./run-hermes dump` reported `version: 0.15.2`, `provider: openai-codex`, `model: gpt-5.5`.
- Focused upstream Hermes tests passed with normal pytest config after installing `pytest-timeout`:
  - `83 passed in 19.51s`
  - Command: `.venv/bin/python -m pytest tests/run_agent/test_run_agent_codex_responses.py tests/run_agent/test_codex_no_tools_nonetype.py tests/run_agent/test_jsondecodeerror_retryable.py -q`
- Compile check passed:
  - `.venv/bin/python -m py_compile run_agent.py agent/codex_runtime.py agent/transports/codex.py agent/auxiliary_client.py`
- Live smoke test passed:
  - `./run-hermes -z 'Reply with exactly: OK' --provider openai-codex -m gpt-5.5 --ignore-rules`
  - Output: `OK`
- Gateway status after restart: active systemd user service, PID `552261`.

## Files Changed
- `vendor/hermes-agent-v2026.5.16` — parent repo submodule pointer updated to commit `77a1650c7` (`v2026.5.29.2`, Hermes `0.15.2`).
- `docs/agentic-workflow/SYNC-2026-05-29-brief-driven-realignment.md` — appended skill-triage section for Claude.
- `HANDOVER-SESSION-11.md` — this handover.
- Runtime/local state changed but not tracked:
  - `hermes/gateway-home/config.yaml` now uses `openai-codex`, `gpt-5.5`, `fallback_providers: []`.
  - Hermes `.venv` now has `pytest-timeout==2.4.0`.

## Commits Made
- `79d538a chore: upgrade Hermes agent vendor to v0.15.2`

## Current Operational Commands
- Messaging gateway status:
  ```bash
  cd /home/zoltan/Projects/metabolicum-agentic-research
  ./run-hermes gateway status
  ```
- Restart messaging gateway:
  ```bash
  ./run-hermes gateway restart
  ```
- Start browser dashboard with embedded TUI:
  ```bash
  ./run-hermes dashboard --tui --no-open
  ```
  Open `http://127.0.0.1:9119`.
- Dashboard status/stop:
  ```bash
  ./run-hermes dashboard --status
  ./run-hermes dashboard --stop
  ```
- Do not use `--insecure` unless intentionally exposing the dashboard beyond localhost.

## In Progress
- No code task is actively in progress.
- This handover and the sync-file skill triage note are ready to commit together.

## Existing Dirty/Untracked Context To Preserve
The parent repo had unrelated dirty/untracked files before the latest handover work. Do not revert them casually. At minimum, earlier status included changes such as:
- `docs/TABLE-EXTRACTION-TOOLS.md`
- deleted `fixtures/expected/wave-0/apob.expected.yaml`
- `input/marker_glossary.json`
- multiple untracked handovers, fixture updates, research asset reports, YouTube inventory outputs, and helper scripts.

## Next Steps
1. If continuing skills work, design project-specific skills rather than installing broad generic skills:
   - `/pubmed` or `/ncbi-eutils`
   - `/biomedical-source-discovery`
   - `/metabolicum-hermes-briefs`
   - `/metabolicum-practitioner-registry`
   - `/source-quality-triage`
2. Keep using `./run-hermes` from the project root. Do not call a system `hermes` binary directly.
