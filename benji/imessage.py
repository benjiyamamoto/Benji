"""
Benji iMessage monitor.

Polls ~/Library/Messages/chat.db every N seconds for new incoming messages.
When a new message arrives:
  1. Gemma4 (via Ollama) decides if it can handle it.
  2. If yes  → Gemma4 replies directly.
  3. If no   → Claude Code is invoked for the heavy lifting.

To send iMessages, Benji uses `osascript` — no extra dependencies needed,
works on any macOS with Messages.app signed in to your Apple ID.

IMPORTANT: grant Terminal (or your Python runtime) Full Disk Access in
System Settings → Privacy & Security → Full Disk Access
so it can read chat.db.
"""

from __future__ import annotations

import asyncio
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from benji.config import (
    IMESSAGE_DB,
    IMESSAGE_POLL_SECONDS,
    IMESSAGE_TRIGGER_HANDLE,
    BENJI_HOME,
)
from benji.logger import log
from benji.ollama import ask_ollama
from benji.claude import ask_claude

# ── Watermark — last message rowid we've seen ──────────────────────────────────
_WATERMARK_FILE = BENJI_HOME / "imessage_watermark.txt"


def _load_watermark() -> int:
    if _WATERMARK_FILE.exists():
        return int(_WATERMARK_FILE.read_text().strip())
    return 0


def _save_watermark(rowid: int) -> None:
    _WATERMARK_FILE.write_text(str(rowid))


# ── chat.db query ──────────────────────────────────────────────────────────────

def _fetch_new_messages(since_rowid: int) -> list[dict]:
    """
    Returns messages newer than since_rowid.
    Filters by IMESSAGE_TRIGGER_HANDLE if set.
    """
    if not IMESSAGE_DB.exists():
        log.warning(f"[imessage] chat.db not found at {IMESSAGE_DB}")
        return []

    # chat.db is locked by Messages.app — open read-only with WAL mode
    uri = f"file:{IMESSAGE_DB}?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True)
    except sqlite3.OperationalError as exc:
        log.error(f"[imessage] cannot open chat.db: {exc} "
                  "(grant Full Disk Access to Terminal in System Settings)")
        return []

    try:
        cur = conn.cursor()
        query = """
            SELECT
                m.ROWID,
                m.text,
                m.is_from_me,
                m.date,
                h.id AS handle
            FROM message m
            LEFT JOIN handle h ON m.handle_id = h.ROWID
            WHERE m.ROWID > ?
              AND m.is_from_me = 0
              AND m.text IS NOT NULL
              AND m.text != ''
        """
        params: list = [since_rowid]

        if IMESSAGE_TRIGGER_HANDLE:
            query += " AND h.id = ?"
            params.append(IMESSAGE_TRIGGER_HANDLE)

        query += " ORDER BY m.ROWID ASC"
        rows = cur.execute(query, params).fetchall()
        return [
            {
                "rowid":  r[0],
                "text":   r[1],
                "handle": r[4] or "unknown",
            }
            for r in rows
        ]
    finally:
        conn.close()


# ── iMessage sender (via osascript) ───────────────────────────────────────────

async def send_imessage(text: str, handle: str | None = None) -> None:
    """
    Send an iMessage to `handle` (or IMESSAGE_TRIGGER_HANDLE if None).
    Uses AppleScript so no extra dependencies needed.
    """
    target = handle or IMESSAGE_TRIGGER_HANDLE
    if not target:
        log.warning("[imessage] no target handle configured, cannot send message")
        return

    # Escape double quotes in the message text for AppleScript
    safe_text = text.replace('"', '\\"')
    script = (
        f'tell application "Messages"\n'
        f'  set targetBuddy to "{target}"\n'
        f'  set targetService to 1st account whose service type = iMessage\n'
        f'  set textBuddy to participant targetBuddy of targetService\n'
        f'  send "{safe_text}" to textBuddy\n'
        f'end tell'
    )
    proc = await asyncio.create_subprocess_exec(
        "osascript", "-e", script,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        log.error(f"[imessage] osascript failed: {stderr.decode()}")
    else:
        log.info(f"[imessage] sent message to {target}")


# ── Routing logic ──────────────────────────────────────────────────────────────

_ROUTING_PROMPT = """You are Benji, a local AI assistant running on a Mac mini.
You received the following iMessage from your owner:

"{message}"

Decide: can you handle this yourself with a short, helpful reply?
Or does this require Claude Code (for coding tasks, debugging, writing scripts,
or anything that needs file system access)?

Reply with EXACTLY one of:
  HANDLE: <your reply to send back>
  ESCALATE: <one-sentence reason why Claude Code is needed>
"""


async def _route_message(text: str, handle: str) -> None:
    log.info(f"[imessage] new message from {handle}: {text[:80]}")

    prompt  = _ROUTING_PROMPT.format(message=text)
    response = await ask_ollama(prompt)

    if response.startswith("HANDLE:"):
        reply = response[len("HANDLE:"):].strip()
        log.info(f"[imessage] Gemma4 handling directly: {reply[:80]}")
        await send_imessage(reply, handle)

    elif response.startswith("ESCALATE:"):
        reason = response[len("ESCALATE:"):].strip()
        log.info(f"[imessage] escalating to Claude Code: {reason}")
        await send_imessage(f"⏳ On it — handing this to Claude Code: {reason}", handle)
        result = await ask_claude(text)
        await send_imessage(result, handle)

    else:
        # Fallback: treat as HANDLE
        log.warning(f"[imessage] unexpected routing response, treating as reply: {response[:80]}")
        await send_imessage(response, handle)


# ── Poll loop ──────────────────────────────────────────────────────────────────

async def _poll_loop() -> None:
    watermark = _load_watermark()
    log.info(f"[imessage] monitor started (polling every {IMESSAGE_POLL_SECONDS}s, watermark={watermark})")

    while True:
        try:
            messages = _fetch_new_messages(watermark)
            for msg in messages:
                watermark = max(watermark, msg["rowid"])
                await _route_message(msg["text"], msg["handle"])
            if messages:
                _save_watermark(watermark)
        except Exception as exc:
            log.error(f"[imessage] poll error: {exc}")

        await asyncio.sleep(IMESSAGE_POLL_SECONDS)


async def start_imessage_monitor() -> asyncio.Task:  # type: ignore[type-arg]
    """Launch the poll loop as a background asyncio task."""
    return asyncio.create_task(_poll_loop())
