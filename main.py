import asyncio
import logging

import uvicorn

import database as db
from bot import build_app
from google_calendar import get_fastapi_app, setup_calendar_watch
from config import WEBHOOK_PORT
from scheduler import init_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    # 1. Initialize database (creates tables if needed)
    await db.init_db()
    logger.info("Database initialized.")

    # 2. Build the Telegram application
    bot_app = build_app()
    tg_bot = bot_app.bot

    # 3. Initialize scheduler and restore pending jobs from DB
    await init_scheduler(tg_bot)

    # 4. Register Google Calendar push notification watch
    await setup_calendar_watch()

    # 5. Build FastAPI app (needs bot reference for scheduling reminders)
    fastapi_app = get_fastapi_app(tg_bot)

    # 6. Configure uvicorn
    uvi_config = uvicorn.Config(
        app=fastapi_app,
        host="0.0.0.0",
        port=WEBHOOK_PORT,
        log_level="info",
    )
    uvi_server = uvicorn.Server(uvi_config)

    # 7. Run bot polling + uvicorn in a single process
    #
    # python-telegram-bot v20+ pattern for running alongside other async services:
    #   - `async with bot_app` handles initialize() / shutdown()
    #   - `bot_app.updater.start_polling()` starts polling in the background (non-blocking)
    #   - `uvi_server.serve()` blocks until the server exits
    #   - We then cleanly stop the updater and bot
    #
    async with bot_app:
        await bot_app.start()
        await bot_app.updater.start_polling(drop_pending_updates=True)
        logger.info("Telegram bot polling started.")

        logger.info("Starting uvicorn on port %d ...", WEBHOOK_PORT)
        await uvi_server.serve()  # blocks until process is interrupted

        # Graceful shutdown
        logger.info("Shutting down...")
        await bot_app.updater.stop()
        await bot_app.stop()


if __name__ == "__main__":
    asyncio.run(main())
