import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot, ReplyKeyboardMarkup

import database as db
import messages as msg
from config import PERSON_Y_CHAT_ID

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


# ---------------------------------------------------------------------------
# Scheduler lifecycle
# ---------------------------------------------------------------------------

def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone="UTC")
    return _scheduler


async def init_scheduler(bot: Bot) -> None:
    scheduler = get_scheduler()
    scheduler.start()
    await restore_jobs(bot)
    logger.info("Scheduler started and jobs restored.")


async def restore_jobs(bot: Bot) -> None:
    pending = await db.get_pending_jobs()
    for job in pending:
        run_at = datetime.fromisoformat(job["run_at"])
        _register_job(bot, job, run_at)
    logger.info("Restored %d pending job(s) from DB.", len(pending))


def _register_job(bot: Bot, job: dict, run_at: datetime) -> None:
    job_id = job["id"]
    chat_id = job["chat_id"]
    job_type = job["job_type"]
    scheduler = get_scheduler()

    if job_type == "followup_10h":
        scheduler.add_job(
            send_followup,
            trigger="date",
            run_date=run_at,
            kwargs={"bot": bot, "chat_id": chat_id, "job_id": job_id},
            id=f"followup_{job_id}",
            replace_existing=True,
        )
    elif job_type in ("reminder_60m", "reminder_10m"):
        minutes = 60 if job_type == "reminder_60m" else 3
        scheduler.add_job(
            send_meeting_reminder,
            trigger="date",
            run_date=run_at,
            kwargs={"bot": bot, "chat_id": chat_id, "job_id": job_id, "minutes": minutes},
            id=f"reminder_{job_id}",
            replace_existing=True,
        )
    else:
        logger.warning("Unknown job_type '%s' for job id=%d — skipping.", job_type, job_id)


# ---------------------------------------------------------------------------
# Schedule new jobs
# ---------------------------------------------------------------------------

async def schedule_followup(
    bot: Bot, chat_id: int, first_name: str, run_at: datetime
) -> None:
    job_id = await db.save_job(chat_id, "followup_10h", run_at)
    scheduler = get_scheduler()
    scheduler.add_job(
        send_followup,
        trigger="date",
        run_date=run_at,
        kwargs={"bot": bot, "chat_id": chat_id, "job_id": job_id},
        id=f"followup_{job_id}",
        replace_existing=True,
    )
    logger.info("Scheduled followup_10h job %d for chat_id=%d at %s", job_id, chat_id, run_at)


async def schedule_meeting_reminders(bot: Bot, chat_id: int, meeting_time: datetime) -> None:
    from datetime import timedelta

    for minutes, job_type in ((60, "reminder_60m"), (3, "reminder_10m")):
        run_at = meeting_time - timedelta(minutes=minutes)
        if run_at <= datetime.now(timezone.utc):
            logger.info(
                "Skipping %s for chat_id=%d — run_at is in the past.", job_type, chat_id
            )
            continue
        job_id = await db.save_job(chat_id, job_type, run_at)
        scheduler = get_scheduler()
        scheduler.add_job(
            send_meeting_reminder,
            trigger="date",
            run_date=run_at,
            kwargs={"bot": bot, "chat_id": chat_id, "job_id": job_id, "minutes": minutes},
            id=f"reminder_{job_id}",
            replace_existing=True,
        )
        logger.info(
            "Scheduled %s job %d for chat_id=%d at %s", job_type, job_id, chat_id, run_at
        )


# ---------------------------------------------------------------------------
# Job functions
# ---------------------------------------------------------------------------

async def send_followup(bot: Bot, chat_id: int, job_id: int) -> None:
    user = await db.get_user(chat_id)
    if not user:
        logger.warning("send_followup: no user found for chat_id=%d", chat_id)
        await db.mark_job_sent(job_id)
        return

    # Guard: already resolved, escalated, or answered — don't re-send
    if user.get("status") in ("resolved", "escalated", "answered"):
        await db.mark_job_sent(job_id)
        return

    first_name = user.get("first_name") or "there"
    keyboard = ReplyKeyboardMarkup(
        [[msg.BTN_YES_RESOLVED, msg.BTN_NO_RESOLVED]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    try:
        await bot.send_message(
            chat_id=chat_id,
            text=msg.FOLLOWUP_QUESTION.format(first_name=first_name),
            reply_markup=keyboard,
        )
    except Exception:
        logger.exception("Failed to send follow-up to chat_id=%d", chat_id)
    finally:
        await db.mark_job_sent(job_id)


async def send_meeting_reminder(
    bot: Bot, chat_id: int, job_id: int, minutes: int
) -> None:
    user = await db.get_user(chat_id)
    if not user:
        logger.warning("send_meeting_reminder: no user found for chat_id=%d", chat_id)
        await db.mark_job_sent(job_id)
        return

    first_name = user.get("first_name") or "there"
    raw_username = user.get("username")
    program = user.get("program") or "N/A"

    # Message to user
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=msg.REMINDER_TO_USER.format(
                minutes=minutes,
                first_name=first_name,
                program=program,
            ),
        )
    except Exception:
        logger.exception("Failed to send meeting reminder to chat_id=%d", chat_id)

    # Message to PERSON_Y
    try:
        if raw_username:
            text = msg.REMINDER_TO_PERSON_Y.format(
                minutes=minutes,
                username=raw_username,
                first_name=first_name,
                chat_id=chat_id,
                program=program,
            )
        else:
            text = msg.REMINDER_TO_PERSON_Y_NO_USERNAME.format(
                minutes=minutes,
                first_name=first_name,
                chat_id=chat_id,
                program=program,
            )
        await bot.send_message(chat_id=PERSON_Y_CHAT_ID, text=text)
    except Exception:
        logger.exception("Failed to send meeting reminder to PERSON_Y for chat_id=%d", chat_id)
    finally:
        await db.mark_job_sent(job_id)
