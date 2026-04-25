import logging
from datetime import datetime, timedelta, timezone

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import database as db
import messages as msg
from config import GOOGLE_BOOKING_URL, PERSON_X_CHAT_ID, TELEGRAM_BOT_TOKEN

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Keyboards (appear in the typing area)
# ---------------------------------------------------------------------------

def _program_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[msg.BTN_SAT], [msg.BTN_ADMISSIONS], [msg.BTN_FULL_SUPPORT]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def _action_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[msg.BTN_ASK_QUESTION], [msg.BTN_REGISTER], [msg.BTN_BACK]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def _resolved_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[msg.BTN_YES_RESOLVED, msg.BTN_NO_RESOLVED]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def _booked_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[msg.BTN_YES_BOOKED], [msg.BTN_NO_BOOKED], [msg.BTN_BACK]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def _back_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[msg.BTN_BACK]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def _start_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[msg.BTN_START]],
        resize_keyboard=True,
        is_persistent=True,
    )


# ---------------------------------------------------------------------------
# /start
# ---------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat_id = update.effective_chat.id
    first_name = user.first_name or "there"
    username = user.username

    await db.upsert_user(chat_id, first_name, username)

    await update.message.reply_text(
        msg.WELCOME.format(first_name=first_name),
        reply_markup=_program_keyboard(),
    )


# ---------------------------------------------------------------------------
# /cancel
# ---------------------------------------------------------------------------

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    await db.reset_user(chat_id)
    await update.message.reply_text(
        msg.CANCEL_REPLY,
        reply_markup=_start_keyboard(),
    )


# ---------------------------------------------------------------------------
# Message dispatcher — routes button taps by text
# ---------------------------------------------------------------------------

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    chat_id = update.effective_chat.id

    if text == msg.BTN_SAT:
        await _handle_program(update, chat_id, msg.BTN_SAT)
    elif text == msg.BTN_ADMISSIONS:
        await _handle_program(update, chat_id, msg.BTN_ADMISSIONS)
    elif text == msg.BTN_FULL_SUPPORT:
        await _handle_program(update, chat_id, msg.BTN_FULL_SUPPORT)
    elif text == msg.BTN_ASK_QUESTION:
        await _handle_ask_question(update, chat_id, context)
    elif text == msg.BTN_REGISTER:
        await _handle_register(update, chat_id)
    elif text == msg.BTN_YES_RESOLVED:
        await _handle_resolved_yes(update, chat_id)
    elif text == msg.BTN_NO_RESOLVED:
        await _handle_resolved_no(update, chat_id)
    elif text == msg.BTN_YES_BOOKED:
        await _handle_booked_yes(update, chat_id)
    elif text == msg.BTN_NO_BOOKED:
        await _handle_booked_no(update, chat_id)
    elif text == msg.BTN_BACK:
        await _handle_back(update, chat_id)
    elif text == msg.BTN_START:
        await start(update, context)


# ---------------------------------------------------------------------------
# Program selection
# ---------------------------------------------------------------------------

async def _handle_program(update: Update, chat_id: int, program: str) -> None:
    await db.set_program(chat_id, program)
    await update.message.reply_text(
        msg.PROGRAM_CHOSEN,
        reply_markup=_action_keyboard(),
    )


# ---------------------------------------------------------------------------
# Ask a Question
# ---------------------------------------------------------------------------

async def _handle_ask_question(
    update: Update, chat_id: int, context: ContextTypes.DEFAULT_TYPE
) -> None:
    user = await db.get_user(chat_id)

    # Guard: already in question flow
    if user and user.get("flow") == "question":
        return

    await db.set_flow(chat_id, "question")
    await db.set_status(chat_id, "contact_sent")

    await update.message.reply_text(
        msg.CONTACT_MESSAGE.format(contact_info=msg.CONTACT_INFO),
        reply_markup=_back_keyboard(),
    )

    # Schedule 10-hour follow-up
    from scheduler import schedule_followup
    run_at = datetime.now(timezone.utc) + timedelta(hours=10)
    await schedule_followup(
        bot=context.bot,
        chat_id=chat_id,
        first_name=user["first_name"] if user else "there",
        run_at=run_at,
    )


# ---------------------------------------------------------------------------
# Register / Book a Meeting
# ---------------------------------------------------------------------------

async def _handle_register(update: Update, chat_id: int) -> None:
    user = await db.get_user(chat_id)

    # Guard: already sent booking link
    if user and user.get("status") == "awaiting_match":
        return

    await db.set_flow(chat_id, "booking")
    await db.set_status(chat_id, "link_sent")

    await update.message.reply_text(
        msg.BOOKING_INTRO,
        reply_markup=ReplyKeyboardRemove(),
    )
    await update.message.reply_text(GOOGLE_BOOKING_URL)
    await update.message.reply_text(
        msg.BOOKING_CONFIRM_PROMPT,
        reply_markup=_booked_keyboard(),
    )


# ---------------------------------------------------------------------------
# Resolved: Yes
# ---------------------------------------------------------------------------

async def _handle_resolved_yes(update: Update, chat_id: int) -> None:
    user = await db.get_user(chat_id)

    # Guard: already answered
    if user and user.get("status") == "resolved":
        return

    await db.set_status(chat_id, "resolved")
    await update.message.reply_text(
        msg.RESOLVED_YES_REPLY,
        reply_markup=_start_keyboard(),
    )


# ---------------------------------------------------------------------------
# Resolved: No
# ---------------------------------------------------------------------------

async def _handle_resolved_no(update: Update, chat_id: int) -> None:
    user = await db.get_user(chat_id)

    # Guard: already escalated
    if user and user.get("status") == "escalated":
        return

    await db.set_status(chat_id, "escalated")

    first_name = user["first_name"] if user else "Unknown"
    raw_username = user.get("username") if user else None

    if raw_username:
        escalation_text = msg.ESCALATION_TO_PERSON_X.format(
            username=raw_username,
            first_name=first_name,
            chat_id=chat_id,
        )
    else:
        escalation_text = msg.ESCALATION_TO_PERSON_X_NO_USERNAME.format(
            first_name=first_name,
            chat_id=chat_id,
        )

    await update.get_bot().send_message(chat_id=PERSON_X_CHAT_ID, text=escalation_text)
    await update.message.reply_text(
        msg.RESOLVED_NO_USER_REPLY,
        reply_markup=_start_keyboard(),
    )


# ---------------------------------------------------------------------------
# Booked: Yes
# ---------------------------------------------------------------------------

async def _handle_booked_yes(update: Update, chat_id: int) -> None:
    user = await db.get_user(chat_id)

    # Guard: already confirmed
    if user and user.get("status") in ("awaiting_match", "matched"):
        return

    await db.set_status(chat_id, "awaiting_match")
    await update.message.reply_text(
        msg.BOOKING_CONFIRMED_REPLY,
        reply_markup=_start_keyboard(),
    )


# ---------------------------------------------------------------------------
# Booked: No
# ---------------------------------------------------------------------------

async def _handle_booked_no(update: Update, chat_id: int) -> None:
    await update.message.reply_text(
        msg.BOOKING_NOT_YET_REPLY.format(booking_url=GOOGLE_BOOKING_URL),
    )
    await update.message.reply_text(
        msg.BOOKING_CONFIRM_PROMPT,
        reply_markup=_booked_keyboard(),
    )


# ---------------------------------------------------------------------------
# Back
# ---------------------------------------------------------------------------

async def _handle_back(update: Update, chat_id: int) -> None:
    user = await db.get_user(chat_id)
    flow = user.get("flow") if user else None

    if flow in ("booking", "question"):
        # Back from booking confirmation or question flow → return to action selection
        await db.set_flow(chat_id, None)
        await db.set_status(chat_id, None)
        await update.message.reply_text(
            msg.PROGRAM_CHOSEN,
            reply_markup=_action_keyboard(),
        )
    else:
        # Back from action selection → return to program selection
        await db.reset_user(chat_id)
        first_name = user["first_name"] if user else "there"
        await update.message.reply_text(
            msg.WELCOME.format(first_name=first_name),
            reply_markup=_program_keyboard(),
        )


# ---------------------------------------------------------------------------
# App builder
# ---------------------------------------------------------------------------

def build_app() -> Application:
    app = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    return app
