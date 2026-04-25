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
from config import (
    AP_MAN_CHAT_ID,
    FS_MAN_CHAT_ID,
    GOOGLE_BOOKING_URL_AP,
    GOOGLE_BOOKING_URL_FS,
    GOOGLE_BOOKING_URL_SAT,
    PERSON_X_CHAT_ID,
    SAT_MAN_CHAT_ID,
    TELEGRAM_BOT_TOKEN,
)

logger = logging.getLogger(__name__)

# Map each program to its expert and booking URL
_PROGRAM_EXPERT: dict[str, int] = {
    msg.BTN_SAT: SAT_MAN_CHAT_ID,
    msg.BTN_ADMISSIONS: AP_MAN_CHAT_ID,
    msg.BTN_FULL_SUPPORT: FS_MAN_CHAT_ID,
}

_PROGRAM_BOOKING_URL: dict[str, str] = {
    msg.BTN_SAT: GOOGLE_BOOKING_URL_SAT,
    msg.BTN_ADMISSIONS: GOOGLE_BOOKING_URL_AP,
    msg.BTN_FULL_SUPPORT: GOOGLE_BOOKING_URL_FS,
}

_EXPERT_CHAT_IDS: frozenset[int] = frozenset(
    {SAT_MAN_CHAT_ID, AP_MAN_CHAT_ID, FS_MAN_CHAT_ID}
)


def _get_booking_url(program: str | None) -> str:
    return _PROGRAM_BOOKING_URL.get(program or "", GOOGLE_BOOKING_URL_SAT)


# ---------------------------------------------------------------------------
# Keyboards
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


def _faq_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[msg.BTN_FAQ_YES], [msg.BTN_FAQ_NO], [msg.BTN_BACK]],
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
# Message dispatcher
# ---------------------------------------------------------------------------

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    chat_id = update.effective_chat.id

    # Expert reply routing — intercept before normal button handling
    if chat_id in _EXPERT_CHAT_IDS:
        await _handle_expert_message(update, chat_id, text)
        return

    # Capture free-text question from user
    user = await db.get_user(chat_id)
    if user and user.get("status") == "awaiting_question_text":
        await _handle_question_text(update, chat_id, text, context)
        return

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
    elif text == msg.BTN_FAQ_YES:
        await _handle_faq_yes(update, chat_id)
    elif text == msg.BTN_FAQ_NO:
        await _handle_faq_no(update, chat_id)
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
    description = msg.PROGRAM_DESCRIPTIONS.get(program, "")
    await update.message.reply_text(
        msg.PROGRAM_CHOSEN.format(description=description),
        reply_markup=_action_keyboard(),
    )


# ---------------------------------------------------------------------------
# Ask a Question — shows FAQ then routes to expert if needed
# ---------------------------------------------------------------------------

async def _handle_ask_question(
    update: Update, chat_id: int, context: ContextTypes.DEFAULT_TYPE
) -> None:
    user = await db.get_user(chat_id)

    if user and user.get("flow") == "question":
        return

    await db.set_flow(chat_id, "question")
    await db.set_status(chat_id, "faq_shown")

    await update.message.reply_text(
        msg.FAQ_MESSAGE,
        reply_markup=_faq_keyboard(),
    )


# ---------------------------------------------------------------------------
# FAQ: user says it was answered
# ---------------------------------------------------------------------------

async def _handle_faq_yes(update: Update, chat_id: int) -> None:
    user = await db.get_user(chat_id)

    if user and user.get("status") == "resolved":
        return

    await db.set_flow(chat_id, None)
    await db.set_status(chat_id, "resolved")
    await update.message.reply_text(
        msg.RESOLVED_YES_REPLY,
        reply_markup=_start_keyboard(),
    )


# ---------------------------------------------------------------------------
# FAQ: user still has a question — prompt them to type it
# ---------------------------------------------------------------------------

async def _handle_faq_no(update: Update, chat_id: int) -> None:
    await db.set_status(chat_id, "awaiting_question_text")
    await update.message.reply_text(
        msg.FAQ_TYPE_QUESTION,
        reply_markup=_back_keyboard(),
    )


# ---------------------------------------------------------------------------
# Capture free-text question, forward to appropriate expert
# ---------------------------------------------------------------------------

async def _handle_question_text(
    update: Update, chat_id: int, text: str, context: ContextTypes.DEFAULT_TYPE
) -> None:
    user = await db.get_user(chat_id)
    program = user.get("program") if user else None
    first_name = user["first_name"] if user else "Unknown"
    raw_username = user.get("username") if user else None

    expert_chat_id = _PROGRAM_EXPERT.get(program or "")
    if not expert_chat_id:
        logger.warning("No expert found for program '%s' (chat_id=%d)", program, chat_id)
        await update.message.reply_text(
            msg.QUESTION_FORWARDED,
            reply_markup=_start_keyboard(),
        )
        await db.set_flow(chat_id, None)
        await db.set_status(chat_id, "question_pending")
        return

    username_part = f" (@{raw_username})" if raw_username else ""
    expert_text = msg.EXPERT_QUESTION.format(
        first_name=first_name,
        username_part=username_part,
        program=program or "N/A",
        question=text,
    )

    try:
        sent = await context.bot.send_message(chat_id=expert_chat_id, text=expert_text)
        question_id = await db.save_question(chat_id, program or "", text)
        await db.set_question_expert_message(question_id, expert_chat_id, sent.message_id)
    except Exception:
        logger.exception(
            "Failed to forward question from chat_id=%d to expert %d", chat_id, expert_chat_id
        )

    await db.set_flow(chat_id, None)
    await db.set_status(chat_id, "question_pending")

    await update.message.reply_text(
        msg.QUESTION_FORWARDED,
        reply_markup=_start_keyboard(),
    )

    # Schedule 10-hour follow-up to check if the student got an answer
    from scheduler import schedule_followup
    run_at = datetime.now(timezone.utc) + timedelta(hours=10)
    await schedule_followup(
        bot=context.bot,
        chat_id=chat_id,
        first_name=first_name,
        run_at=run_at,
    )


# ---------------------------------------------------------------------------
# Expert sends a message — route reply back to the student
# ---------------------------------------------------------------------------

async def _handle_expert_message(
    update: Update, expert_chat_id: int, text: str
) -> None:
    reply_to = update.message.reply_to_message

    if reply_to is None:
        await update.message.reply_text(msg.EXPERT_USE_REPLY)
        return

    question = await db.get_question_by_expert_message(
        expert_chat_id, reply_to.message_id
    )

    if not question:
        await update.message.reply_text(msg.EXPERT_REPLY_NOT_FOUND)
        return

    user_chat_id = question["user_chat_id"]
    question_id = question["id"]

    try:
        await update.get_bot().send_message(
            chat_id=user_chat_id,
            text=msg.ANSWER_FROM_EXPERT.format(answer=text),
        )
        await db.mark_question_answered(question_id)
        await db.set_status(user_chat_id, "answered")
        await update.message.reply_text(msg.EXPERT_REPLY_SENT)
    except Exception:
        logger.exception(
            "Failed to send expert answer to user chat_id=%d", user_chat_id
        )


# ---------------------------------------------------------------------------
# Register / Book a Meeting
# ---------------------------------------------------------------------------

async def _handle_register(update: Update, chat_id: int) -> None:
    user = await db.get_user(chat_id)

    if user and user.get("status") == "awaiting_match":
        return

    program = user.get("program") if user else None
    booking_url = _get_booking_url(program)

    await db.set_flow(chat_id, "booking")
    await db.set_status(chat_id, "link_sent")

    await update.message.reply_text(
        msg.BOOKING_INTRO,
        reply_markup=ReplyKeyboardRemove(),
    )
    await update.message.reply_text(booking_url)
    await update.message.reply_text(
        msg.BOOKING_CONFIRM_PROMPT,
        reply_markup=_booked_keyboard(),
    )


# ---------------------------------------------------------------------------
# Resolved: Yes
# ---------------------------------------------------------------------------

async def _handle_resolved_yes(update: Update, chat_id: int) -> None:
    user = await db.get_user(chat_id)

    if user and user.get("status") == "resolved":
        return

    await db.set_status(chat_id, "resolved")
    await update.message.reply_text(
        msg.RESOLVED_YES_REPLY,
        reply_markup=_start_keyboard(),
    )


# ---------------------------------------------------------------------------
# Resolved: No — escalate to PERSON_X as fallback
# ---------------------------------------------------------------------------

async def _handle_resolved_no(update: Update, chat_id: int) -> None:
    user = await db.get_user(chat_id)

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
    user = await db.get_user(chat_id)
    program = user.get("program") if user else None
    booking_url = _get_booking_url(program)

    await update.message.reply_text(
        msg.BOOKING_NOT_YET_REPLY.format(booking_url=booking_url),
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
    program = user.get("program") if user else None
    description = msg.PROGRAM_DESCRIPTIONS.get(program or "", "")

    if flow in ("booking", "question") or (
        user and user.get("status") in ("faq_shown", "awaiting_question_text")
    ):
        await db.set_flow(chat_id, None)
        await db.set_status(chat_id, None)
        await update.message.reply_text(
            msg.PROGRAM_CHOSEN.format(description=description),
            reply_markup=_action_keyboard(),
        )
    else:
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
