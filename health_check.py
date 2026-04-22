"""
Benji built-in task: health_check

Runs on a fixed interval (configured in config.py).
Reads the last-run log for every task in ~/.benji/logs/
and writes a human-readable summary to ~/.benji/logs/health_summary.md.

If any task failed, it sends you an iMessage (via Benji's send_imessage helper)
and optionally invokes Claude Code to investigate.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from benji.config import LOGS_DIR, TASKS_DIR
from benji.logger import log
from benji.run_log import read_last_run, TaskStatus


HEALTH_SUMMARY = LOGS_DIR / "health_summary.md"


async def run() -> None:
    log.info("[health_check] starting")

    task_files = list(TASKS_DIR.glob("*.py"))
    results: list[dict] = []
    failures: list[str] = []

    for task_file in sorted(task_files):
        if task_file.name.startswith("_"):
            continue
        last = read_last_run(task_file.stem)
        if last is None:
            results.append({"task": task_file.stem, "status": "never_run", "detail": ""})
        else:
            results.append({
                "task":   task_file.stem,
                "status": last.status.value,
                "ran_at": last.ran_at.isoformat(),
                "detail": last.detail,
            })
            if last.status == TaskStatus.FAILURE:
                failures.append(task_file.stem)

    _write_summary(results, failures)

    if failures:
        msg = f"⚠️ Benji health check: {len(failures)} task(s) failed: {', '.join(failures)}. Check ~/.benji/logs/health_summary.md"
        log.warning(f"[health_check] {msg}")
        await _notify(msg, failures)
    else:
        log.info(f"[health_check] all {len(results)} tasks healthy ✓")


def _write_summary(results: list[dict], failures: list[str]) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"# Benji Health Summary",
        f"_Generated: {now}_",
        "",
        f"## Status: {'🔴 FAILURES DETECTED' if failures else '🟢 All systems go'}",
        "",
        "| Task | Status | Last Run | Detail |",
        "|------|--------|----------|--------|",
    ]
    for r in results:
        icon = {"ok": "✅", "failure": "❌", "never_run": "⬜"}.get(r["status"], "❓")
        ran  = r.get("ran_at", "—")
        lines.append(f"| {r['task']} | {icon} {r['status']} | {ran} | {r.get('detail','')[:80]} |")

    if failures:
        lines += [
            "",
            "## Failed Tasks",
            "",
            "The following tasks need attention:",
            "",
        ]
        for f in failures:
            log_file = LOGS_DIR / f"{f}_last_run.json"
            lines.append(f"### {f}")
            if log_file.exists():
                lines.append(f"```\n{log_file.read_text()}\n```")
            lines.append("")

    HEALTH_SUMMARY.write_text("\n".join(lines))
    log.info(f"[health_check] summary written to {HEALTH_SUMMARY}")


async def _notify(message: str, failed_tasks: list[str]) -> None:
    """
    Send an iMessage to yourself and optionally invoke Claude Code.
    Import here to avoid circular imports at startup.
    """
    try:
        from benji.imessage import send_imessage
        await send_imessage(message)
    except Exception as exc:
        log.error(f"[health_check] could not send iMessage: {exc}")

    # Future: invoke Claude Code automatically
    # from benji.claude import ask_claude_to_fix
    # for task in failed_tasks:
    #     await ask_claude_to_fix(task)
