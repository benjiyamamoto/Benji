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
    log.info("🐾 Benji is waking up...")

    # Start the APScheduler with all registered tasks
    scheduler = await start_scheduler()

    # Start the iMessage monitor
    await start_imessage_monitor()

    log.info("🐾 Benji is ready.")

    try:
        # Keep the event loop alive
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        log.info("🐾 Benji is going to sleep. Goodbye!")
        scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
