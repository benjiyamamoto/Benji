"""
Benji CLI — `benji` command entry point.

Usage:
  benji run          # start the server (scheduler + iMessage monitor)
  benji status       # print health summary
  benji tasks        # list registered tasks
  benji fix <task>   # invoke Claude Code to fix a failing task
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

console = Console()


def main() -> None:
    args = sys.argv[1:]
    cmd  = args[0] if args else "run"

    if cmd == "run":
        asyncio.run(_run())
    elif cmd == "status":
        _status()
    elif cmd == "tasks":
        _tasks()
    elif cmd == "fix" and len(args) > 1:
        asyncio.run(_fix(args[1]))
    else:
        _help()


async def _run() -> None:
    from benji.main import main as benji_main
    await benji_main()


def _status() -> None:
    from benji.config import LOGS_DIR
    summary = LOGS_DIR / "health_summary.md"
    if summary.exists():
        console.print(summary.read_text())
    else:
        console.print("[yellow]No health summary yet. Run `benji run` first.[/yellow]")


def _tasks() -> None:
    from benji.config import TASKS_DIR
    table = Table(title="Benji Scheduled Tasks")
    table.add_column("File", style="cyan")
    table.add_column("Schedule", style="green")
    table.add_column("Last Status")

    from benji.scheduler import _parse_schedule
    from benji.run_log import read_last_run

    for f in sorted(TASKS_DIR.glob("*.py")):
        if f.name.startswith("_"):
            continue
        schedule = _parse_schedule(f.read_text())
        sched_str = str(schedule) if schedule else "[red]no schedule[/red]"
        last = read_last_run(f.stem)
        status = last.status.value if last else "never run"
        table.add_row(f.name, sched_str, status)

    console.print(table)


async def _fix(task_name: str) -> None:
    from benji.claude import ask_claude_to_fix_task
    console.print(f"[yellow]Asking Claude Code to fix task: {task_name}[/yellow]")
    result = await ask_claude_to_fix_task(task_name)
    console.print(result)


def _help() -> None:
    console.print("""
[bold]benji[/bold] — local AI orchestrator

Commands:
  [cyan]benji run[/cyan]          Start Benji (scheduler + iMessage monitor)
  [cyan]benji status[/cyan]       Show latest health summary
  [cyan]benji tasks[/cyan]        List all scheduled tasks
  [cyan]benji fix <task>[/cyan]   Ask Claude Code to fix a failing task
""")
