"""
Benji scheduler — APScheduler wrapper.

Scheduled tasks live as plain .py files in ~/.benji/tasks/.
Each file must expose a run() coroutine (or plain function).
Benji discovers them at startup and registers them automatically.

Each task file declares its own schedule via a top-level docstring
block like this:

    # benji:schedule interval minutes=15

Supported trigger formats:
    # benji:schedule interval minutes=15
    # benji:schedule interval hours=1
    # benji:schedule cron hour=8 minute=0          (daily at 08:00)
    # benji:schedule cron day_of_week=mon hour=9   (Mondays at 09:00)
"""

import importlib.util
import re
import sys
from pathlib import Path
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from benji.config import TASKS_DIR, HEALTH_CHECK_INTERVAL_MINUTES
from benji.logger import log


# ── Schedule header parser ─────────────────────────────────────────────────────

_SCHEDULE_RE = re.compile(r"#\s*benji:schedule\s+(\w+)\s*(.*)")
_KV_RE       = re.compile(r"(\w+)=(\S+)")


def _parse_schedule(source: str) -> dict[str, Any] | None:
    """Return {'trigger': 'interval'|'cron', **kwargs} or None."""
    for line in source.splitlines()[:20]:          # only scan the top of file
        m = _SCHEDULE_RE.match(line.strip())
        if m:
            trigger = m.group(1)
            kwargs  = {k: _coerce(v) for k, v in _KV_RE.findall(m.group(2))}
            return {"trigger": trigger, **kwargs}
    return None


def _coerce(value: str) -> int | str:
    try:
        return int(value)
    except ValueError:
        return value


# ── Dynamic task loader ────────────────────────────────────────────────────────

def _load_task(path: Path) -> Any:
    """Dynamically import a task file and return the module."""
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[path.stem] = module
    spec.loader.exec_module(module)          # type: ignore[union-attr]
    return module


# ── Scheduler bootstrap ────────────────────────────────────────────────────────

async def start_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()

    # ── Built-in: health check ─────────────────────────────────────────────────
    from benji.tasks.health_check import run as health_run
    scheduler.add_job(
        health_run,
        trigger=IntervalTrigger(minutes=HEALTH_CHECK_INTERVAL_MINUTES),
        id="health_check",
        name="Health Check",
        replace_existing=True,
    )
    log.info(f"  ✓ registered built-in task: health_check "
             f"(every {HEALTH_CHECK_INTERVAL_MINUTES} min)")

    # ── User tasks from ~/.benji/tasks/*.py ────────────────────────────────────
    for task_file in sorted(TASKS_DIR.glob("*.py")):
        if task_file.name.startswith("_"):
            continue
        try:
            source   = task_file.read_text()
            schedule = _parse_schedule(source)
            if schedule is None:
                log.warning(f"  ⚠ {task_file.name}: no '# benji:schedule' header, skipping")
                continue

            module  = _load_task(task_file)
            trigger_type = schedule.pop("trigger")
            trigger = (
                IntervalTrigger(**schedule)
                if trigger_type == "interval"
                else CronTrigger(**schedule)
            )

            if not hasattr(module, "run"):
                log.warning(f"  ⚠ {task_file.name}: no run() function, skipping")
                continue

            scheduler.add_job(
                module.run,
                trigger=trigger,
                id=task_file.stem,
                name=task_file.stem,
                replace_existing=True,
            )
            log.info(f"  ✓ registered task: {task_file.stem} ({trigger_type} {schedule})")

        except Exception as exc:
            log.error(f"  ✗ failed to load {task_file.name}: {exc}")

    scheduler.start()
    log.info("Scheduler started.")
    return scheduler
