import logging
import time
from datetime import datetime, timedelta, timezone

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    ChatJoinRequestHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import database as db
import messages as msg
from config import (
    AP_MAN_CHAT_ID,
    EVENT_GROUP_ID,
    FS_MAN_CHAT_ID,
    GOOGLE_BOOKING_URL_AP,
    GOOGLE_BOOKING_URL_FS,
    GOOGLE_BOOKING_URL_SAT,
    LINK_EXPIRY_HOURS,
    PERSON_X_CHAT_ID,
    REQUIRED_CHANNEL_IDS,
    REQUIRED_CHANNEL_INVITES,
    REQUIRED_GROUP_IDS,
    REQUIRED_GROUP_INVITES,
    SAT_MAN_CHAT_ID,
    TELEGRAM_BOT_TOKEN,
)

logger = logging.getLogger(__name__)

# Map each program to its experts and booking URL
_PROGRAM_EXPERT: dict[str, list[int]] = {
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
    id for ids in _PROGRAM_EXPERT.values() for id in ids
)

# Tracks experts who have sent /clarify and are waiting to type their clarification text.
# Maps expert_chat_id → user_chat_id to route the follow-up message.
_expert_clarification_state: dict[int, int] = {}


def _get_booking_url(program: str | None) -> str:
    return _PROGRAM_BOOKING_URL.get(program or "", GOOGLE_BOOKING_URL_SAT)


# ---------------------------------------------------------------------------
# Keyboards
# ---------------------------------------------------------------------------

def _main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[msg.BTN_PROGRAMS], [msg.BTN_GET_LINK]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


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

    if chat_id == PERSON_X_CHAT_ID:
        return

    first_name = user.first_name or "there"
    username = user.username

    await db.upsert_user(chat_id, first_name, username)

    await update.message.reply_text(
        msg.WELCOME.format(first_name=first_name),
        reply_markup=_main_keyboard(),
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

    # Event gate admin routing
    if chat_id == PERSON_X_CHAT_ID:
        await _eg_admin_message_handler(update, context)
        return

    # Expert reply routing — intercept before normal button handling
    if chat_id in _EXPERT_CHAT_IDS:
        await _handle_expert_message(update, chat_id, text)
        return

    # Capture free-text question from user
    user = await db.get_user(chat_id)
    if user and user.get("status") == "awaiting_question_text":
        await _handle_question_text(update, chat_id, text, context)
        return

    if text == msg.BTN_PROGRAMS:
        await _handle_programs(update, chat_id)
    elif text == msg.BTN_GET_LINK:
        await _eg_student_get_link(update, chat_id, context)
    elif text == msg.BTN_SAT:
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
# Main menu → Programs
# ---------------------------------------------------------------------------

async def _handle_programs(update: Update, chat_id: int) -> None:
    await update.message.reply_text(
        msg.CHOOSE_PROGRAM,
        reply_markup=_program_keyboard(),
    )


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

    expert_chat_ids = _PROGRAM_EXPERT.get(program or "")
    if not expert_chat_ids:
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

    for expert_chat_id in expert_chat_ids:
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
# /clarify — expert flags intent to send a follow-up to an already-answered question
# ---------------------------------------------------------------------------

async def clarify_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    expert_chat_id = update.effective_chat.id

    if expert_chat_id not in _EXPERT_CHAT_IDS:
        return

    reply_to = update.message.reply_to_message
    if reply_to is None:
        await update.message.reply_text(msg.EXPERT_CLARIFY_USE_REPLY)
        return

    question = await db.get_question_by_expert_message_any_status(
        expert_chat_id, reply_to.message_id
    )

    if not question:
        await update.message.reply_text(msg.EXPERT_REPLY_NOT_FOUND)
        return

    _expert_clarification_state[expert_chat_id] = question["user_chat_id"]
    await update.message.reply_text(msg.EXPERT_CLARIFY_READY)


# ---------------------------------------------------------------------------
# Expert sends a message — route reply back to the student
# ---------------------------------------------------------------------------

async def _handle_expert_message(
    update: Update, expert_chat_id: int, text: str
) -> None:
    # If expert previously sent /clarify, this message is the clarification text.
    if expert_chat_id in _expert_clarification_state and update.message.reply_to_message is None:
        user_chat_id = _expert_clarification_state.pop(expert_chat_id)
        try:
            await update.get_bot().send_message(
                chat_id=user_chat_id,
                text=msg.CLARIFICATION_FROM_EXPERT.format(answer=text),
            )
            await update.message.reply_text(msg.EXPERT_CLARIFY_SENT)
        except Exception:
            logger.exception(
                "Failed to send clarification to user chat_id=%d", user_chat_id
            )
        return

    # Expert started a new reply while in clarification mode — discard stale state.
    _expert_clarification_state.pop(expert_chat_id, None)

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
    question_text = question["question_text"]

    try:
        await update.get_bot().send_message(
            chat_id=user_chat_id,
            text=msg.ANSWER_FROM_EXPERT.format(answer=text),
        )
        await db.mark_question_answered(question_id)
        await db.mark_sibling_questions_answered(user_chat_id, question_text)
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
    first_name = user["first_name"] if user else "there"

    if flow in ("booking", "question") or (
        user and user.get("status") in ("faq_shown", "awaiting_question_text")
    ):
        # Deep flow → back to action keyboard
        await db.set_flow(chat_id, None)
        await db.set_status(chat_id, None)
        await update.message.reply_text(
            msg.PROGRAM_BACK.format(description=description),
            reply_markup=_action_keyboard(),
        )
    elif program:
        # Action keyboard → back to program list
        await db.set_program(chat_id, None)
        await db.set_flow(chat_id, None)
        await db.set_status(chat_id, None)
        await update.message.reply_text(
            msg.CHOOSE_PROGRAM,
            reply_markup=_program_keyboard(),
        )
    else:
        # Program list → back to main menu
        await update.message.reply_text(
            msg.WELCOME.format(first_name=first_name),
            reply_markup=_main_keyboard(),
        )


# ---------------------------------------------------------------------------
# Event gate — student flow
# ---------------------------------------------------------------------------

_EG_MEMBER_STATUSES = {"member", "administrator", "creator"}


async def _eg_check_membership(bot, user_id: int) -> tuple[list[bool], list[bool]]:
    """Returns (group_results, channel_results). Fails open on API error."""
    group_results: list[bool] = []
    for gid in REQUIRED_GROUP_IDS:
        try:
            member = await bot.get_chat_member(gid, user_id)
            group_results.append(member.status in _EG_MEMBER_STATUSES)
        except TelegramError:
            logger.warning("Cannot check membership in %s. Failing open.", gid)
            group_results.append(True)

    channel_results: list[bool] = []
    for cid in REQUIRED_CHANNEL_IDS:
        try:
            member = await bot.get_chat_member(cid, user_id)
            channel_results.append(member.status in _EG_MEMBER_STATUSES)
        except TelegramError:
            logger.warning("Cannot check membership in %s. Failing open.", cid)
            channel_results.append(True)

    return group_results, channel_results


def _eg_build_missing_links(group_results: list[bool], channel_results: list[bool]) -> list[str]:
    missing = []
    for i, ok in enumerate(group_results):
        if not ok:
            invite = REQUIRED_GROUP_INVITES[i] if i < len(REQUIRED_GROUP_INVITES) else "?"
            missing.append(msg.EG_MISSING_CHAT.format(name=f"Required Group {i + 1}", invite=invite))
    for i, ok in enumerate(channel_results):
        if not ok:
            invite = REQUIRED_CHANNEL_INVITES[i] if i < len(REQUIRED_CHANNEL_INVITES) else "?"
            missing.append(msg.EG_MISSING_CHAT.format(name=f"Required Channel {i + 1}", invite=invite))
    return missing


async def _eg_send_missing_message(update: Update, missing: list[str]) -> None:
    keyboard = [[InlineKeyboardButton(msg.EG_CHECK_AGAIN_BUTTON, callback_data="check_membership")]]
    await update.effective_message.reply_text(
        msg.EG_NOT_MEMBER.format(links="\n".join(missing)),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def _eg_deliver_event_post(chat_id: int, event: dict, bot) -> None:
    if event.get("post_message_id") and event.get("post_chat_id"):
        await bot.forward_message(
            chat_id=chat_id,
            from_chat_id=event["post_chat_id"],
            message_id=event["post_message_id"],
        )
    elif event.get("post_text"):
        await bot.send_message(chat_id=chat_id, text=event["post_text"])


async def _eg_send_invite(
    update: Update, context: ContextTypes.DEFAULT_TYPE, student_id: int, event: dict
) -> None:
    expire_date = datetime.utcnow() + timedelta(hours=LINK_EXPIRY_HOURS)
    link_name = f"student_{student_id}_{int(time.time())}"

    invite = await context.bot.create_chat_invite_link(
        chat_id=EVENT_GROUP_ID,
        member_limit=1,
        expire_date=expire_date,
        name=link_name,
    )

    await db.eg_store_issued_link(
        event_id=event["id"],
        student_chat_id=student_id,
        invite_link=invite.invite_link,
        expires_at=expire_date.isoformat(),
    )

    await _eg_deliver_event_post(update.effective_chat.id, event, context.bot)
    await update.effective_message.reply_text(
        msg.EG_INVITE_SENT.format(expiry_hours=LINK_EXPIRY_HOURS, link=invite.invite_link)
    )


async def _eg_student_get_link(
    update: Update, chat_id: int, context: ContextTypes.DEFAULT_TYPE
) -> None:
    group_results, channel_results = await _eg_check_membership(context.bot, chat_id)
    missing = _eg_build_missing_links(group_results, channel_results)

    if missing:
        await _eg_send_missing_message(update, missing)
        return

    event = await db.eg_get_active_event()
    if not event:
        await update.message.reply_text(msg.EG_NO_ACTIVE_EVENT)
        return

    await _eg_send_invite(update, context, chat_id, event)


async def _eg_check_membership_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()
    user = update.effective_user

    group_results, channel_results = await _eg_check_membership(context.bot, user.id)
    missing = _eg_build_missing_links(group_results, channel_results)

    if missing:
        await _eg_send_missing_message(update, missing)
        return

    event = await db.eg_get_active_event()
    if not event:
        await query.edit_message_text(msg.EG_NO_ACTIVE_EVENT)
        return

    await _eg_send_invite(update, context, user.id, event)


async def _eg_join_request_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    request = update.chat_join_request
    if request.chat.id != EVENT_GROUP_ID:
        return

    await context.bot.approve_chat_join_request(EVENT_GROUP_ID, request.from_user.id)

    event = await db.eg_get_active_event()
    if event:
        await db.eg_log_join_approval(event["id"], request.from_user.id)

    logger.info("Approved join request from user %s", request.from_user.id)


# ---------------------------------------------------------------------------
# Event gate — admin flow (PERSON_X only)
# ---------------------------------------------------------------------------

async def _eg_admin_message_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    msg_obj = update.message
    if msg_obj.forward_from_chat:
        post_chat_id = msg_obj.forward_from_chat.id
        post_message_id = msg_obj.forward_from_message_id
        post_text = None
    elif msg_obj.forward_from:
        post_chat_id = msg_obj.forward_from.id
        post_message_id = msg_obj.forward_from_message_id
        post_text = None
    else:
        post_chat_id = msg_obj.chat_id
        post_message_id = msg_obj.message_id
        post_text = msg_obj.text or msg_obj.caption

    await db.eg_save_event(post_chat_id, post_message_id, post_text)
    await msg_obj.reply_text(msg.EG_EVENT_ACTIVATED)


async def _eg_admin_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != PERSON_X_CHAT_ID:
        return

    event = await db.eg_get_active_event()
    if event:
        links = await db.eg_count_issued_links(event["id"])
        approvals = await db.eg_count_join_approvals(event["id"])
        text = msg.EG_ADMIN_STATUS_TEMPLATE.format(
            status="Active",
            post_set="Yes",
            last_updated=event["created_at"],
            links_issued=links,
            join_approvals=approvals,
        )
    else:
        text = msg.EG_ADMIN_STATUS_TEMPLATE.format(
            status="No active event",
            post_set="No",
            last_updated="—",
            links_issued=0,
            join_approvals=0,
        )
    await update.message.reply_text(text)


async def _eg_admin_clearevent(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != PERSON_X_CHAT_ID:
        return
    await db.eg_deactivate_event()
    await update.message.reply_text(msg.EG_ADMIN_EVENT_CLEARED)


async def _eg_admin_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != PERSON_X_CHAT_ID:
        return
    await update.message.reply_text(msg.EG_ADMIN_HELP)


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
    app.add_handler(CommandHandler("clarify", clarify_command))
    app.add_handler(CommandHandler("status", _eg_admin_status))
    app.add_handler(CommandHandler("clearevent", _eg_admin_clearevent))
    app.add_handler(CommandHandler("help", _eg_admin_help))
    app.add_handler(CallbackQueryHandler(_eg_check_membership_callback, pattern="^check_membership$"))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    app.add_handler(ChatJoinRequestHandler(_eg_join_request_handler))

    return app
