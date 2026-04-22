# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

**Benji** is a local AI orchestrator daemon for macOS. It runs two models in a coordinated workflow:
- **Gemma4 (via Ollama)** — handles iMessage routing and routine tasks locally (fast, free, private)
- **Claude Code (`claude -p`)** — invoked via subprocess for heavy lifting (coding, debugging, repair)

The process runs continuously on a Mac mini, polling iMessage and running scheduled tasks.

## Commands

**Install dependencies:**
```bash
uv sync
```

**Run Benji:**
```bash
uv run benji run
```

**CLI:**
```bash
uv run benji status        # Show latest health summary
uv run benji tasks         # List scheduled tasks and their last-run status
uv run benji fix <task>    # Ask Claude Code to diagnose a failing task
```

**Type check:**
```bash
mypy benji/
```

## Architecture

Benji runs two concurrent async loops:

1. **Scheduler** (`benji/scheduler.py`) — APScheduler auto-discovers task files from `~/.benji/tasks/*.py`, parsing a `# benji:schedule` header comment to register each task. Built-in `health_check` runs every 30 minutes.

2. **iMessage Monitor** (`benji/imessage.py`) — polls `~/Library/Messages/chat.db` every 15 seconds. New messages are routed through Gemma4: if Gemma4 returns `HANDLE:`, it replies directly; if it returns `ESCALATE:`, it calls Claude Code (`benji/claude.py`) and sends the result.

### Key files

| File | Role |
|------|------|
| `benji/config.py` | Central config (paths, model names, DB location) |
| `benji/scheduler.py` | APScheduler wrapper; parses schedule headers, registers tasks |
| `benji/imessage.py` | Polls `chat.db`, routes to Gemma4 or Claude Code |
| `benji/ollama.py` | Async wrapper around Ollama client |
| `benji/claude.py` | Invokes `claude -p` as subprocess; includes task repair logic |
| `benji/run_log.py` | Writes per-task JSON status to `~/.benji/logs/<task>_last_run.json` |
| `benji/tasks/health_check.py` | Built-in task; reads run logs, sends iMessage alert on failure |
| `benji/tasks/example_task.py` | Template for user-defined tasks |

### Runtime state (all in `~/.benji/`)

- `tasks/*.py` — user-defined scheduled tasks (auto-discovered)
- `logs/<task>_last_run.json` — last run status per task (JSON)
- `logs/health_summary.md` — human-readable summary written by health_check
- `logs/benji.log` — unified application log
- `imessage_watermark.txt` — tracks last-processed message ID (prevents reprocessing)
- `config.md` — optional user config (human-readable)

### Task file format

User tasks live in `~/.benji/tasks/` and must:
1. Declare a schedule header (parsed by the scheduler):
   ```python
   # benji:schedule interval minutes=15
   # benji:schedule cron hour=8 minute=0
   ```
2. Expose an `async def run() -> None` function
3. Call `write_run_log(task_name, "OK"|"FAILURE", detail)` before returning

### Design constraints

- **Fully async** — all I/O uses `asyncio`; do not introduce blocking calls
- **Stateless** — the process can crash and restart freely; all state is in `~/.benji/`
- **macOS-only** — uses `osascript` for sending iMessage, direct SQLite access to `chat.db`
- **Strict mypy** — all code must pass `mypy --strict`
