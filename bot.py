import logging
from datetime import datetime, timedelta, timezone

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

import database as db
import messages as msg
from config import GOOGLE_BOOKING_URL, PERSON_X_CHAT_ID, TELEGRAM_BOT_TOKEN

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _program_label(callback_data: str) -> str:
    return {
        "prog_sat": msg.BTN_SAT,
        "prog_admissions": msg.BTN_ADMISSIONS,
        "prog_full": msg.BTN_FULL_SUPPORT,
    }.get(callback_data, callback_data)


def _username_display(user: dict) -> str:
    """Return @username or 'first_name (ID: chat_id)' fallback."""
    if user.get("username"):
        return f"@{user['username']}"
    return f"{user['first_name']} (ID: {user['chat_id']})"


def _program_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(msg.BTN_SAT, callback_data="prog_sat"),
            InlineKeyboardButton(msg.BTN_ADMISSIONS, callback_data="prog_admissions"),
            InlineKeyboardButton(msg.BTN_FULL_SUPPORT, callback_data="prog_full"),
        ]
    ])


def _action_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(msg.BTN_ASK_QUESTION, callback_data="act_question"),
            InlineKeyboardButton(msg.BTN_REGISTER, callback_data="act_register"),
        ]
    ])


def _resolved_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(msg.BTN_YES_RESOLVED, callback_data="resolved_yes"),
            InlineKeyboardButton(msg.BTN_NO_RESOLVED, callback_data="resolved_no"),
        ]
    ])


def _booked_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(msg.BTN_YES_BOOKED, callback_data="booked_yes"),
            InlineKeyboardButton(msg.BTN_NO_BOOKED, callback_data="booked_no"),
        ]
    ])


# ---------------------------------------------------------------------------
# /start
# ---------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat_id = update.effective_chat.id
    first_name = user.first_name or "there"
    username = user.username  # may be None

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
    await update.message.reply_text(msg.CANCEL_REPLY)


# ---------------------------------------------------------------------------
# Callback query dispatcher
# ---------------------------------------------------------------------------

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    data = query.data
    chat_id = update.effective_chat.id

    if data in ("prog_sat", "prog_admissions", "prog_full"):
        await _handle_program(query, chat_id, data)
    elif data == "act_question":
        await _handle_ask_question(query, chat_id, context)
    elif data == "act_register":
        await _handle_register(query, chat_id)
    elif data == "resolved_yes":
        await _handle_resolved_yes(query, chat_id)
    elif data == "resolved_no":
        await _handle_resolved_no(query, chat_id)
    elif data == "booked_yes":
        await _handle_booked_yes(query, chat_id)
    elif data == "booked_no":
        await _handle_booked_no(query, chat_id)
    else:
        logger.warning("Unknown callback data: %s", data)


# ---------------------------------------------------------------------------
# Program selection
# ---------------------------------------------------------------------------

async def _handle_program(query, chat_id: int, data: str) -> None:
    program = _program_label(data)
    await db.set_program(chat_id, program)
    await query.edit_message_text(
        f"Program selected: {program}\n\n{msg.PROGRAM_CHOSEN}",
        reply_markup=_action_keyboard(),
    )


# ---------------------------------------------------------------------------
# Ask a Question
# ---------------------------------------------------------------------------

async def _handle_ask_question(query, chat_id: int, context) -> None:
    user = await db.get_user(chat_id)

    # Guard: already in question flow
    if user and user.get("flow") == "question":
        return

    await db.set_flow(chat_id, "question")
    await db.set_status(chat_id, "contact_sent")

    await query.edit_message_text(
        msg.CONTACT_MESSAGE.format(contact_info=msg.CONTACT_INFO)
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

async def _handle_register(query, chat_id: int) -> None:
    user = await db.get_user(chat_id)

    # Guard: already sent booking link
    if user and user.get("status") == "awaiting_match":
        return

    await db.set_flow(chat_id, "booking")
    await db.set_status(chat_id, "link_sent")

    await query.edit_message_text(msg.BOOKING_INTRO)
    await query.message.reply_text(
        GOOGLE_BOOKING_URL,
        reply_markup=_booked_keyboard(),
    )
    await query.message.reply_text(msg.BOOKING_CONFIRM_PROMPT)


# ---------------------------------------------------------------------------
# Resolved: Yes
# ---------------------------------------------------------------------------

async def _handle_resolved_yes(query, chat_id: int) -> None:
    user = await db.get_user(chat_id)

    # Guard: already answered
    if user and user.get("status") == "resolved":
        return

    await db.set_status(chat_id, "resolved")
    await query.edit_message_text(msg.RESOLVED_YES_REPLY)


# ---------------------------------------------------------------------------
# Resolved: No
# ---------------------------------------------------------------------------

async def _handle_resolved_no(query, chat_id: int) -> None:
    user = await db.get_user(chat_id)

    # Guard: already escalated
    if user and user.get("status") == "escalated":
        return

    await db.set_status(chat_id, "escalated")

    first_name = user["first_name"] if user else "Unknown"
    raw_username = user.get("username") if user else None

    # Message to PERSON_X
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

    await query.get_bot().send_message(chat_id=PERSON_X_CHAT_ID, text=escalation_text)
    await query.edit_message_text(msg.RESOLVED_NO_USER_REPLY)


# ---------------------------------------------------------------------------
# Booked: Yes
# ---------------------------------------------------------------------------

async def _handle_booked_yes(query, chat_id: int) -> None:
    user = await db.get_user(chat_id)

    # Guard: already confirmed
    if user and user.get("status") in ("awaiting_match", "matched"):
        return

    await db.set_status(chat_id, "awaiting_match")
    await query.edit_message_text(msg.BOOKING_CONFIRMED_REPLY)


# ---------------------------------------------------------------------------
# Booked: No
# ---------------------------------------------------------------------------

async def _handle_booked_no(query, chat_id: int) -> None:
    await query.edit_message_text(
        msg.BOOKING_NOT_YET_REPLY.format(booking_url=GOOGLE_BOOKING_URL),
        reply_markup=_booked_keyboard(),
    )
    await query.message.reply_text(msg.BOOKING_CONFIRM_PROMPT)


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
    app.add_handler(CallbackQueryHandler(handle_callback))

    return app
