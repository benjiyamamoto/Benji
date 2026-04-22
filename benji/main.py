"""
Benji — a local AI orchestrator.
Gemma4 (via Ollama) handles the interface and routing.
Claude Code handles the heavy lifting when needed.
"""

import asyncio

from benji.scheduler import start_scheduler
from benji.imessage import start_imessage_monitor
from benji.logger import log


async def main() -> None:
    log.info("Benji is waking up...")

    scheduler = await start_scheduler()
    await start_imessage_monitor()
    log.info("Benji is ready.")

    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit, asyncio.CancelledError):
        log.info("Benji is going to sleep. Goodbye!")
        scheduler.shutdown()
