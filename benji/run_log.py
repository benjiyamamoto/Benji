"""
Benji run_log — every scheduled task calls write_run_log() when it finishes.
The health checker reads these logs to build its summary.

Log files live at ~/.benji/logs/<task_name>_last_run.json
(only the LAST run is kept — we don't need a full history per task,
the health checker only cares about the most recent result)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from benji.config import LOGS_DIR


class TaskStatus(str, Enum):
    OK      = "ok"
    FAILURE = "failure"


@dataclass
class RunLog:
    task:   str
    status: TaskStatus
    ran_at: datetime
    detail: str = ""


def write_run_log(task: str, status: TaskStatus, detail: str = "") -> None:
    """Call this at the end of every task's run() function."""
    entry = {
        "task":   task,
        "status": status.value,
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "detail": detail,
    }
    log_file = LOGS_DIR / f"{task}_last_run.json"
    log_file.write_text(json.dumps(entry, indent=2))


def read_last_run(task: str) -> RunLog | None:
    """Returns the last RunLog for a task, or None if it has never run."""
    log_file = LOGS_DIR / f"{task}_last_run.json"
    if not log_file.exists():
        return None
    data = json.loads(log_file.read_text())
    return RunLog(
        task=data["task"],
        status=TaskStatus(data["status"]),
        ran_at=datetime.fromisoformat(data["ran_at"]),
        detail=data.get("detail", ""),
    )
