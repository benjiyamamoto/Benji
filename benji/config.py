"""
Benji configuration — all paths and settings in one place.
Everything lives under ~/.benji/ so the project root stays clean
and multiple users can share the same codebase with their own state.
"""

from pathlib import Path

# ── Directories ────────────────────────────────────────────────────────────────

BENJI_HOME = Path.home() / ".benji"

TASKS_DIR      = BENJI_HOME / "tasks"       # scheduled Python scripts
LOGS_DIR       = BENJI_HOME / "logs"        # per-task run logs + benji.log
PROJECTS_DIR   = BENJI_HOME / "projects"    # per-project context & history
CONFIG_FILE    = BENJI_HOME / "config.md"   # human-readable global config

# Create all directories on first import
for _dir in (TASKS_DIR, LOGS_DIR, PROJECTS_DIR):
    _dir.mkdir(parents=True, exist_ok=True)


# ── Ollama ─────────────────────────────────────────────────────────────────────

OLLAMA_HOST  = "http://localhost:11434"
OLLAMA_MODEL = "gemma4:e4b"  # ~8B param variant, fits comfortably in 16 GB RAM


# ── iMessage ───────────────────────────────────────────────────────────────────

IMESSAGE_DB = Path.home() / "Library" / "Messages" / "chat.db"
IMESSAGE_POLL_SECONDS = 15          # how often to check for new messages
IMESSAGE_TRIGGER_HANDLE = None      # set to your phone number / AppleID
                                    # to filter to only YOUR messages,
                                    # e.g. "+15145550123"
                                    # None = watch all incoming messages


# ── Claude Code ────────────────────────────────────────────────────────────────

CLAUDE_CODE_CMD = "claude"          # must be on PATH after `npm install -g`
CLAUDE_CODE_TIMEOUT = 300           # seconds before we give up on a task


# ── Health check ───────────────────────────────────────────────────────────────

HEALTH_CHECK_INTERVAL_MINUTES = 30
