# HANDOVER-SESSION-2 - Hermes operator launch fixed

Date: 2026-05-23

## What was fixed

- Built official Hermes TUI from `/home/zoltan/Projects/metabolicum-agentic-research/vendor/hermes-agent-v2026.5.16/ui-tui` and linked it to the conda package path expected by Hermes:
  `/home/zoltan/miniconda3/envs/hermes/lib/python3.11/site-packages/ui-tui`.
- Created project-scoped Hermes home:
  `/home/zoltan/Projects/metabolicum-agentic-research/hermes/gateway-home`.
- Active project Hermes home contains copied `SOUL.md`, copied `config.yaml`, and `.env` symlink to:
  `/home/zoltan/Projects/metabolicum-agentic-research/secrets/.env`.
- Synced bundled Hermes skills from the checked-out official source into project Hermes home, fixing missing `kanban-worker`.
- Created operator launchers:
  `/home/zoltan/.local/bin/hermes-metabolicum`
  `/home/zoltan/.local/bin/hermes-metabolicum-kanban`
- Created desktop entries:
  `/home/zoltan/.local/share/applications/hermes-metabolicum.desktop`
  `/home/zoltan/.local/share/applications/hermes-metabolicum-kanban.desktop`
- Updated `/media/zoltan/4TSSD/ops/llama-server/launch-qwen-mtp.sh` to use 64k context and disable Qwen thinking server-side:
  `--ctx-size 65536`, `--chat-template-kwargs {enable_thinking:false}`, `--reasoning off`, `--reasoning-budget 0`.
- Updated active and repo Hermes config context to `65536`:
  `/home/zoltan/Projects/metabolicum-agentic-research/hermes/config.yaml`
  `/home/zoltan/Projects/metabolicum-agentic-research/hermes/gateway-home/config.yaml`

## Current running state

- Qwen llama-server is running in a visible GNOME Terminal titled `Qwen llama-server 64k no-thinking`.
- Active Qwen PID at handover: `3799695`.
- Endpoint verified: `http://127.0.0.1:8080/v1/models` reports `n_ctx: 65536`.
- Hermes TUI was opened with `/home/zoltan/.local/bin/hermes-metabolicum`.
- Hermes Kanban monitor was opened with `/home/zoltan/.local/bin/hermes-metabolicum-kanban`.

## Active Kanban task

Project board: `metabolicum-agentic-research` under project `HERMES_HOME`.

Active task:
- `t_7820683a` - `stage_2_extraction: apob <- apob-peter-attia-source`
- assignee: `default`
- status at handover: `running`
- latest run: run 6, started 2026-05-23 21:04
- log: `/home/zoltan/Projects/metabolicum-agentic-research/hermes/gateway-home/kanban/boards/metabolicum-agentic-research/logs/t_7820683a.log`

Previous failed/reclaimed attempts were caused by missing bundled skill, Qwen backend down, 8k context, and then 16k context. The current run is the first one using the fixed 64k no-thinking backend and is doing actual project shell work.

## Operator commands

Open Hermes TUI:
```bash
/home/zoltan/.local/bin/hermes-metabolicum
```

Watch Kanban:
```bash
/home/zoltan/.local/bin/hermes-metabolicum-kanban
```

Check task:
```bash
HERMES_HOME=/home/zoltan/Projects/metabolicum-agentic-research/hermes/gateway-home \
HERMES_KANBAN_BOARD=metabolicum-agentic-research \
/home/zoltan/miniconda3/envs/hermes/bin/hermes kanban --board metabolicum-agentic-research show t_7820683a
```

Tail task log:
```bash
tail -f /home/zoltan/Projects/metabolicum-agentic-research/hermes/gateway-home/kanban/boards/metabolicum-agentic-research/logs/t_7820683a.log
```
