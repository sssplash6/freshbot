import asyncio
import logging

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

    async with bot_app:
        await bot_app.start()
        await bot_app.updater.start_polling(drop_pending_updates=True)
        logger.info("Telegram bot polling started.")
        await bot_app.updater.idle()
        await bot_app.stop()


if __name__ == "__main__":
    asyncio.run(main())
