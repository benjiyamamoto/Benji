# benji:schedule interval minutes=60
"""
Example Benji task: daily_summary

This task is a template showing how to write your own scheduled tasks.
Copy this file to ~/.benji/tasks/, adjust the schedule header and run() body,
and Benji will pick it up automatically on next start.

The first line MUST be the schedule header:
  # benji:schedule interval minutes=60
  # benji:schedule cron hour=8 minute=0

Your run() function can be async or sync.
Always call write_run_log() at the end so the health checker knows it ran.
"""

from benji.run_log import write_run_log, TaskStatus
from benji.logger import log


async def run() -> None:
    task_name = "example_task"
    log.info(f"[{task_name}] running")

    try:
        # ── Your task logic goes here ──────────────────────────────────────────
        log.info(f"[{task_name}] hello from the example task! Replace me.")
        # ──────────────────────────────────────────────────────────────────────

        write_run_log(task_name, TaskStatus.OK, "completed successfully")

    except Exception as exc:
        log.error(f"[{task_name}] failed: {exc}")
        write_run_log(task_name, TaskStatus.FAILURE, str(exc))
        raise
