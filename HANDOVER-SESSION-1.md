# Handover — Session 1 (2026-05-23)

## What was done

B1–B4 of the Hermes install runbook:

| Step | Commit | What |
|---|---|---|
| B1 | `2796155` | Pinned Hermes v0.14.0 in `config/hermes-version.txt` |
| B2 | `e6f885a` | Wrote `hermes/config.yaml` — disable flags verified against v0.14.0 docs |
| B3 | `0019106` | `pip install hermes-agent==0.14.0` in `hermes` conda env, wrote `scripts/preflight.sh`, generated `secrets/.env` from `~/.secrets` |
| B3+ | `ffa1281` | Provisioned Supabase: local Docker (ports 544xx) + remote project `lgycgiqmmxpeuprxriim`. Migration `0001_initial.sql` applied to both (20 tables). Separate from metasync production project. |
| B4 | `4838564` | Wrote `code/acceptance/run_acceptance.py` — **BUT this was wrong.** See "What went wrong." |

## What went wrong

1. **B4 acceptance tests bypassed Hermes.** I wrote a custom Python script that called llama-server directly via the OpenAI SDK instead of having Hermes run the pipeline. The 8/8 pass result validates the LLM output quality but does NOT validate Hermes as the runner. The test must be redone with Hermes executing autonomously.

2. **llama-server was started with wrong flags.** Original: `--ctx-size 8192`, no `--jinja`, no `--chat-template-kwargs`. Hermes requires:
   - `--ctx-size 65536` (minimum 64K context)
   - `--jinja` (required for tool calling)
   - `--chat-template-kwargs '{"enable_thinking":false}'` (Qwen thinking tags break Hermes's response parser — `KeyError: 'final_response'`)

3. **llama-server has been restarted** (by the user during this session) with the correct flags. Current command:
   ```
   /media/zoltan/4TSSD/llama.cpp/build/bin/llama-server \
     --model /media/zoltan/4TSSD/models/Qwen3.6-27B-MTP-GGUF/Qwen3.6-27B-UD-Q4_K_XL.gguf \
     --host 127.0.0.1 --port 8080 --ctx-size 65536 --parallel 1 \
     --flash-attn --chat-template-kwargs '{"enable_thinking":false}' \
     --jinja --temp 0 --seed 42 --log-prefix
   ```
   Server auto-expanded to 160K context, 4 slots. Hermes smoke test (`hermes -z "Say hello"`) returned `Hello!` — confirming Hermes can talk to the model.

4. **I kept manually orchestrating stages** instead of letting Hermes run the pipeline autonomously. The architecture (runbook, SOUL.md, prompts, tools.yaml) is designed for Hermes to be the runner. The next session must let Hermes execute, not write wrapper scripts around it.

## Uncommitted changes

`hermes/config.yaml` has uncommitted additions:
```yaml
model:
  provider: "custom"
  base_url: "http://127.0.0.1:8080/v1"
  default: "qwen"
  context_length: 131072
  extra_body:
    chat_template_kwargs:
      enable_thinking: false
```
The `extra_body` section did NOT fix the thinking-tag issue (server-side flag was needed). May want to keep or remove — harmless but ineffective.

## Dirty state

- `runs/hermes-smoke/` — disposable test dir, can be deleted
- `runs/acceptance-2026-05-23T215522Z/` — B4 test artifacts (3 runs, all passed, but these used the custom harness, not Hermes)

## What the next session must do

1. **Let Hermes run the pipeline.** Do not write custom LLM callers. Hermes has file tools, terminal, the prompts, the schemas, the fixture. Give it the task and let it execute.

2. **Verify Hermes orchestrates Stage 2 end-to-end** on the ApoB fixture: extractor → tagger → structurer. This is the acceptance scope per hermes-setup.md §3.

3. **Validate the 10 acceptance criteria** against Hermes's actual output (not a custom harness's output).

4. **Commit the corrected B4** once Hermes runs successfully.

## Environment state

- **Conda env:** `hermes` (Python 3.11, hermes-agent 0.14.0)
- **llama-server:** running on port 8080, Qwen 3.6 27B, thinking disabled, 160K context, 4 slots
- **SearXNG:** running on port 8888
- **Local Supabase:** running on ports 54421–54429 (20 tables)
- **Remote Supabase:** `lgycgiqmmxpeuprxriim` (us-east-1, 20 tables)
- **Preflight:** 30/30 pass

## Key file locations

| What | Where |
|---|---|
| Operator runbook | `/home/zoltan/Projects/metabolicum-research/docs/HERMES-RUNBOOK.md` |
| Agent setup contract | `docs/agentic-workflow/hermes-setup.md` |
| SOUL.md | `hermes/SOUL.md` |
| Worker config | `hermes/config.yaml` |
| Prompts | `prompts/01-*.md` through `prompts/05-*.md` |
| Schemas | `code/schemas/*.json` |
| Fixture | `fixtures/sources/apob-peter-attia-source.json` |
| LLM endpoints | `config/llm-endpoints.yaml` |
| Tool manifests | `config/tools.yaml` |
| Preflight | `scripts/preflight.sh` |
| llama-server binary | `/media/zoltan/4TSSD/llama.cpp/build/bin/llama-server` |
| Model GGUF | `/media/zoltan/4TSSD/models/Qwen3.6-27B-MTP-GGUF/Qwen3.6-27B-UD-Q4_K_XL.gguf` |
