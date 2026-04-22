# 🐾 Benji

Benji is nicer to you than lobsters

A local AI orchestrator for your Mac mini.

**Gemma4 (via Ollama)** handles everyday tasks and iMessage routing.  
**Claude Code** handles the heavy lifting — coding, debugging, scripting — only when actually needed.

Named after [Yoshua Bengio](https://yoshuabengio.org/), Montreal AI pioneer and McGill alumnus. Runs on a Mac mini named Benji Yamamoto.

---

## Architecture

```
APScheduler
    ├── health_check       (built-in, every 30 min)
    ├── your_task_a.py     (written by Claude, auto-discovered)
    └── your_task_b.py     (written by Claude, auto-discovered)

iMessage (chat.db polling)
    └── Gemma4 (Ollama)    can I handle this myself?
            ├── YES → reply directly
            └── NO  → Claude Code → reply with result

health_check
    └── anything failed?
            ├── NO  → log "all good"
            └── YES → iMessage you + optionally invoke Claude Code to fix it
```

Everything is **stateless** — state lives in `~/.benji/` as `.md` and `.json` files.  
If Benji crashes, just restart it. Nothing is lost.

---

## Setup

### 1. Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Clone and install Benji

```bash
git clone https://github.com/yourname/benji.git
cd benji
uv sync
```

### 3. Install and start Ollama

```bash
brew install ollama
ollama pull gemma4:e4b    # ~8B param, fits in 16 GB RAM
ollama serve              # runs on localhost:11434
```

### 4. Install Claude Code

```bash
npm install -g @anthropic-ai/claude-code
```

Then authenticate. On your **main machine** (where you can open a browser):

```bash
claude login
```

On your **Mac mini** (headless), generate a long-lived token instead:

```bash
claude setup-token
# copy the printed token, then:
export CLAUDE_CODE_OAUTH_TOKEN=<your token>
# add to ~/.zshrc or ~/.bashrc to persist it
```

### 5. Configure Benji

Edit `~/.benji/config.md` (created on first run) or edit `benji/config.py` directly:

```python
OLLAMA_MODEL = "gemma4:e4b"          # default; swap tag if you have more RAM
IMESSAGE_TRIGGER_HANDLE = "+15145550123"  # your phone number
```

### 6. Grant Full Disk Access

For iMessage monitoring, give Terminal (or your Python binary) Full Disk Access:

**System Settings → Privacy & Security → Full Disk Access → + → Terminal**

### 7. Run Benji

```bash
uv run benji run
# or
uv run python main.py
```

---

## Adding Scheduled Tasks

Ask Claude Code to write a task for you:

```
claude -p "Write a Benji scheduled task that checks my external IP every hour
and logs it to ~/.benji/logs/ip_history.md. Follow the pattern in
benji/tasks/example_task.py"
```

Claude Code will write the file. Drop it in `~/.benji/tasks/` and restart Benji.  
It will be auto-discovered and scheduled.

---

## Commands

```bash
benji run           # start Benji
benji status        # show latest health summary
benji tasks         # list all scheduled tasks and their last status
benji fix <task>    # ask Claude Code to diagnose and fix a failing task
```

---

## File Structure

```
~/.benji/
  config.md                    # human-readable config (future)
  imessage_watermark.txt        # last seen iMessage rowid
  tasks/
    your_task.py               # your scheduled tasks live here
  logs/
    benji.log                  # main log
    health_summary.md          # latest health check report
    <task>_last_run.json       # per-task last run status
  projects/
    <project>/
      context.md               # current task context
      history.md               # conversation log
      instructions.md          # project-specific Claude instructions
```

---

## Philosophy

- **Gemma4 for everything routine** — fast, local, free, private
- **Claude Code only when needed** — expensive tokens used wisely
- **Stateless server** — crash and restart freely, state is always safe
- **Plain text state** — `.md` files are human-readable, git-friendly, debuggable
- **Self-healing** — failed tasks trigger Claude Code automatically
- **iMessage as the interface** — talk to Benji the same way it talks to you

---

## License

MIT
