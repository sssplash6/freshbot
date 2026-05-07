import asyncio
import logging
import signal

import database as db
from bot import build_app
from scheduler import init_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    await db.init_db()
    logger.info("Database initialized.")

    bot_app = build_app()
    await init_scheduler(bot_app.bot)

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)

    async with bot_app:
        await bot_app.start()
        await bot_app.updater.start_polling(drop_pending_updates=True)
        logger.info("Telegram bot polling started.")
        await stop_event.wait()
        await bot_app.updater.stop()
        await bot_app.stop()


if __name__ == "__main__":
    asyncio.run(main())
