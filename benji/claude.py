"""
Benji Claude Code integration.

Invokes the `claude` CLI as a subprocess in non-interactive (-p) mode.
This stays within Anthropic's terms of service — we're calling Claude Code
(Anthropic's own product), not routing subscription tokens through a
third-party API.

Claude Code must be installed and authenticated separately:
  npm install -g @anthropic-ai/claude-code
  claude login   (one-time browser auth on your main machine)
  claude setup-token  (then set CLAUDE_CODE_OAUTH_TOKEN on the Mac mini)
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from benji.config import CLAUDE_CODE_CMD, CLAUDE_CODE_TIMEOUT, BENJI_HOME
from benji.logger import log


async def ask_claude(prompt: str, cwd: Path | None = None) -> str:
    """
    Run `claude -p <prompt>` and return stdout as a string.

    cwd: working directory for Claude Code (defaults to ~/.benji).
         For project-specific tasks, pass the project directory so Claude
         has the right file context.
    """
    work_dir = cwd or BENJI_HOME
    log.info(f"[claude] invoking Claude Code (cwd={work_dir})")
    log.debug(f"[claude] prompt: {prompt[:200]}")

    try:
        proc = await asyncio.create_subprocess_exec(
            CLAUDE_CODE_CMD, "-p", prompt,
            cwd=str(work_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(),
            timeout=CLAUDE_CODE_TIMEOUT,
        )
    except asyncio.TimeoutError:
        proc.kill()
        log.error(f"[claude] timed out after {CLAUDE_CODE_TIMEOUT}s")
        return f"⚠️ Claude Code timed out after {CLAUDE_CODE_TIMEOUT} seconds."

    out = stdout.decode().strip()
    err = stderr.decode().strip()

    if proc.returncode != 0:
        log.error(f"[claude] exit {proc.returncode}: {err[:200]}")
        return f"⚠️ Claude Code exited with error:\n{err}"

    log.info(f"[claude] done ({len(out)} chars)")
    return out


async def ask_claude_to_fix_task(task_name: str) -> str:
    """
    Convenience wrapper: read the failed task's source + last run log,
    build a repair prompt, and hand it to Claude Code.
    """
    from benji.config import TASKS_DIR, LOGS_DIR

    task_file = TASKS_DIR / f"{task_name}.py"
    log_file  = LOGS_DIR  / f"{task_name}_last_run.json"

    if not task_file.exists():
        return f"⚠️ Task file not found: {task_file}"

    source   = task_file.read_text()
    last_log = log_file.read_text() if log_file.exists() else "(no log)"

    prompt = f"""The Benji scheduled task `{task_name}` failed.

## Task source ({task_file})
```python
{source}
```

## Last run log
```json
{last_log}
```

Please:
1. Diagnose the failure.
2. Fix the task file in-place at {task_file}.
3. Confirm what you changed and why.
"""
    return await ask_claude(prompt, cwd=TASKS_DIR)
