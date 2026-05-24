# Hermes Usage Guide — metabolicum-agentic-research

> **Purpose:** This document tells you how to run the Metabolicum research pipeline through Hermes, and how to prevent Cloud Code / Codex / VS Code agents from hijacking the work.

---

## The Golden Rule

**All processing goes through `./run-hermes`. Never use VS Code's "Agent" panel, never use Codex inline, never use Cloud Code for research tasks.**

If you see an AI assistant inside VS Code trying to "help" with the pipeline, **ignore it**. The only agent runtime authorized for this project is Hermes.

---

## Quick Start

### 1. Open Hermes CLI (interactive TUI)

```bash
cd /home/zoltan/Projects/metabolicum-agentic-research
./run-hermes
```

This drops you into the Hermes terminal interface where you can:
- Chat with the agent
- Run `/tools` to see available tools
- Run `/skills` to see skills
- Use slash commands for control

### 2. Initialize the pipeline

```bash
./scripts/init-pipeline.sh
```

This runs preflight checks, verifies Hermes is configured, and shows the Kanban board status.

### 3. Enqueue a task

```bash
./scripts/enqueue-source.sh apob-peter-attia-source apob
```

This creates a task on the Kanban board for processing.

### 4. Start a worker

```bash
./scripts/run-worker.sh --once
```

This claims the next ready task and processes it.

### 5. Run acceptance tests

```bash
./scripts/run-acceptance.sh --runs 3
```

This runs the Stage 2 acceptance test harness against the cached fixture.

---

## How to Prevent Cloud Code / Codex Takeover

### The Problem
VS Code extensions like Cloud Code and GitHub Copilot / Codex detect that you're working on a codebase and offer to "help" by reading files, suggesting edits, or even running commands. In this project, **that is wrong** — the agent runtime is Hermes, not VS Code.

### Solutions

1. **Use a terminal outside VS Code**
   - Open a standalone terminal (GNOME Terminal, Kitty, Alacritty, etc.)
   - `cd` to the project root
   - Run `./run-hermes` or the pipeline scripts
   - Do NOT use VS Code's integrated terminal for Hermes work if Cloud Code is active

2. **Disable Cloud Code in VS Code**
   - Open VS Code Command Palette (`Ctrl+Shift+P`)
   - Type "Extensions: Disable Extension"
   - Find "Cloud Code" and disable it
   - Reload VS Code

3. **Disable GitHub Copilot / Codex inline suggestions**
   - VS Code Settings → search "copilot"
   - Uncheck "GitHub Copilot: Enable"
   - Or disable the extension entirely

4. **Use the `run-hermes` wrapper exclusively**
   - The wrapper at `./run-hermes` hardcodes the venv path and HERMES_HOME
   - Even if VS Code has its own Python environment, it cannot hijack this wrapper
   - The wrapper ignores PATH and goes straight to the project venv

5. **Close VS Code entirely when running the pipeline**
   - The simplest solution: use a text editor that is NOT an agent
   - `nano`, `vim`, `emacs`, `gedit`, or `zed --no-agent` for file editing
   - Keep VS Code closed while Hermes is running

---

## Architecture Reminder

```
┌──────────────────┐         ┌──────────────────┐         ┌──────────────────┐
│  Telegram        │  enq    │   Kanban         │  pop    │  Worker          │
│  Gateway         │ ──────▶ │   (durable)      │ ──────▶ │  (one task,      │
│  (long-running)  │         │                  │         │   disposable     │
│                  │ ◀────── │                  │ ◀────── │   HERMES_HOME)   │
└──────────────────┘  status └──────────────────┘  result └──────────────────┘
```

- **Gateway**: One process, runs for days/weeks. Handles Telegram messages only.
- **Kanban**: SQLite-backed task queue at `hermes/gateway-home/kanban/`.
- **Worker**: One process per task. Stateless. Reads prompts from `prompts/`. Writes output to `runs/<id>/`.

The workers are the only things that do actual research work. The gateway is just a control plane.

---

## Command Reference

### Hermes CLI (interactive)

```bash
./run-hermes                    # Start TUI
./run-hermes --version          # Show version
./run-hermes doctor             # Diagnose issues
./run-hermes model              # Configure LLM providers
```

### Kanban (task queue)

```bash
./run-hermes kanban boards list
./run-hermes kanban boards switch metabolicum-agentic-research
./run-hermes kanban list
./run-hermes kanban create --title "task name" --description "details"
./run-hermes kanban claim --profile worker-1
./run-hermes kanban complete <task-id>
```

### Gateway (Telegram bot)

```bash
./run-hermes gateway setup      # One-time setup
./run-hermes gateway start      # Start the gateway daemon
```

### Pipeline scripts

```bash
./scripts/init-pipeline.sh                          # Verify setup
./scripts/enqueue-source.sh <source> <marker>       # Add task to queue
./scripts/run-worker.sh --once                      # Process one task
./scripts/run-stage.sh <stage> <run> <source> <m>   # Run single stage
./scripts/run-acceptance.sh --runs 3                # Run acceptance tests
```

---

## Troubleshooting

### "Hermes venv not found"

```bash
cd vendor/hermes-agent-v2026.5.16
./setup-hermes.sh
cd ../..
```

### "Cloud Code is still active"

1. Check VS Code bottom status bar for "Cloud Code" or "Copilot" icons
2. Click them and sign out / disable
3. Or uninstall the extensions entirely
4. Reload VS Code

### "Codex keeps suggesting changes"

- Codex is GitHub Copilot's chat interface
- Disable the GitHub Copilot Chat extension in VS Code
- Or use a different editor for this project

### "I want to edit files without an AI agent interfering"

```bash
# Use a plain text editor
nano file.txt
vim file.txt

# Or Zed without agent features
zed --no-agent file.txt
```

---

## Verification: Is Hermes Actually Running?

After starting a worker or the gateway, check:

```bash
# Is the Hermes process running?
ps aux | grep hermes_cli

# Is the Kanban database active?
ls -la hermes/gateway-home/kanban/boards/metabolicum-agentic-research/

# Are run artifacts being created?
ls -la runs/

# Is the local LLM responding?
curl -s http://127.0.0.1:8080/v1/models | python3 -m json.tool
```

---

## File Locations

| File | Purpose |
|---|---|
| `./run-hermes` | Project-local Hermes launcher (always use this) |
| `hermes/config.yaml` | Pinned worker restriction config |
| `hermes/SOUL.md` | Stateless task-executor persona |
| `hermes/gateway-home/` | Gateway runtime state (SQLite, sessions) |
| `prompts/*.md` | Role-locked stage prompts |
| `fixtures/sources/*.json` | Cached source transcripts |
| `runs/<id>/` | Per-run output artifacts |
| `code/llm_client.py` | LLM endpoint adapter |
| `code/acceptance/run_acceptance.py` | Acceptance test harness |

---

*Last updated: 2026-05-23. If Hermes version changes, update `config/hermes-version.txt` and re-run `./scripts/init-pipeline.sh`.*
