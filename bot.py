import asyncio
import csv
import html
import io
import json
import logging
import random
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

_RATE_LIMIT_SECONDS = 1.5
_last_message_time: dict[int, float] = {}

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.error import TelegramError
from telegram.ext import (
    AIORateLimiter,
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telegram.request import HTTPXRequest

import database as db
import messages as msg
from config import (
    ADV_PLACEMENT_MAN_CHAT_ID,
    AP_MAN_CHAT_ID,
    FS_MAN_CHAT_ID,
    GENERAL_MAN_CHAT_ID,
    PERSON_Z_CHAT_ID,
    SAT_BOOKING_URL,
    WEBSITE_URL_ADV_PLACEMENT,
    IMKON_MAN_CHAT_ID,
    MS_MAN_CHAT_ID,
    PERSON_X_CHAT_ID,
    RI_MAN_CHAT_ID,
    SAT_MAN_CHAT_ID,
    ADV_ENGLISH_REVIEWER_CHAT_ID,
    AE_GROUP_CHAT_ID,
    PODCAST_CHANNEL_IDS,
    PODCAST_CHANNEL_HANDLES,
    PODCAST_YOUTUBE_URL,
    VALERA_CHAT_ID,
    TELEGRAM_BOT_TOKEN,
    WEBSITE_URL_ADMISSIONS,
    WEBSITE_URL_FULL_SUPPORT,
    WEBSITE_URL_MASTERS,
    WEBSITE_URL_IMKON,
    WEBSITE_URL_RESEARCH_INSTITUTE,
)

logger = logging.getLogger(__name__)

_MEMBER_STATUSES = {"member", "administrator", "creator"}

# Map each program to its experts and booking URL
_PROGRAM_EXPERT: dict[str, list[int]] = {
    msg.BTN_SAT: SAT_MAN_CHAT_ID,
    msg.BTN_ADMISSIONS: AP_MAN_CHAT_ID,
    msg.BTN_FULL_SUPPORT: FS_MAN_CHAT_ID,
    msg.BTN_MASTERS: MS_MAN_CHAT_ID,
    msg.BTN_ADV_PLACEMENT: ADV_PLACEMENT_MAN_CHAT_ID,
    msg.BTN_IMKON: IMKON_MAN_CHAT_ID,
    msg.BTN_RESEARCH_INSTITUTE: RI_MAN_CHAT_ID,
    msg.BTN_ADV_ENGLISH_PROGRAM: [ADV_ENGLISH_REVIEWER_CHAT_ID],
    "General Inquiry": GENERAL_MAN_CHAT_ID,
}

# Maps flow names (for menu-level flows) to their program key in _PROGRAM_EXPERT
_FLOW_PROGRAM: dict[str, str] = {
    "general_inquiry": "General Inquiry",
}

_AE_REVIEWER_IDS: frozenset[int] = frozenset(
    x for x in (ADV_ENGLISH_REVIEWER_CHAT_ID, VALERA_CHAT_ID) if x is not None
)

_PROGRAM_WEBSITE_URL: dict[str, str] = {
    msg.BTN_SAT: SAT_BOOKING_URL,
    msg.BTN_ADV_PLACEMENT: WEBSITE_URL_ADV_PLACEMENT,
    msg.BTN_ADMISSIONS: WEBSITE_URL_ADMISSIONS,
    msg.BTN_FULL_SUPPORT: WEBSITE_URL_FULL_SUPPORT,
    msg.BTN_MASTERS: WEBSITE_URL_MASTERS,
    msg.BTN_IMKON: WEBSITE_URL_IMKON,
    msg.BTN_RESEARCH_INSTITUTE: WEBSITE_URL_RESEARCH_INSTITUTE,
}

_PROGRAM_WEBSITE_INTRO: dict[str, str] = {
    msg.BTN_SAT: msg.SAT_BOOKING_INTRO,
    msg.BTN_ADV_PLACEMENT: msg.AP_CLASSES_REGISTER_INTRO,
}

_EXPERT_CHAT_IDS: frozenset[int] = frozenset(
    id for ids in _PROGRAM_EXPERT.values() for id in ids
)

# Tracks experts who have sent /clarify and are waiting to type their clarification text.
# Maps expert_chat_id → {"user_chat_id": int, "thread_id": int | None}
_expert_clarification_state: dict[int, dict] = {}

# Accumulates Advanced English application answers per chat_id across steps.
_ae_state: dict[int, dict] = {}


# Accumulates SAT enrollment answers per chat_id.
_sat_enroll_state: dict[int, dict] = {}

# Accumulates Economics Olympiad Prep registration answers per chat_id
# ({"full_name": str, "courses": set[str]}).
_econ_state: dict[int, dict] = {}

# Olympiad Prep course options — callback key → display label.
_ECON_COURSES: dict[str, str] = {
    "macro": msg.BTN_ECON_MACRO,
    "micro": msg.BTN_ECON_MICRO,
    "calcbc": msg.BTN_ECON_CALC_BC,
    "phys1": msg.BTN_ECON_PHYSICS,
}

# Who gets notified of a new Olympiad Prep registration (deduped).
_ECON_NOTIFY_IDS: frozenset[int] = frozenset(
    {PERSON_X_CHAT_ID, *ADV_PLACEMENT_MAN_CHAT_ID}
)

# Chat IDs with bypass mode active — skips "coming soon" gates to expose real flows.
_bypass_users: set[int] = set()

# Top-level nav buttons that escape any active capture state (question/followup input).
_NAV_BUTTONS: frozenset[str] = frozenset({
    # Main menu
    msg.BTN_PROGRAMS, msg.BTN_GENERAL_INQUIRY, msg.BTN_PODCAST,
    msg.BTN_HOME, msg.BTN_START,
    msg.BTN_ADV_ENGLISH, msg.BTN_SAT_ENROLL, msg.BTN_TRIAL_AP,
    msg.BTN_GET_GUIDEBOOK, msg.BTN_GETTING_IN, msg.BTN_MERCH, msg.BTN_SAT_CONSULT,
    msg.BTN_VALERA_GIVEAWAY,
    # Program sub-menu
    msg.BTN_SAT, msg.BTN_ADMISSIONS, msg.BTN_FULL_SUPPORT, msg.BTN_MASTERS,
    msg.BTN_ADV_PLACEMENT, msg.BTN_IMKON, msg.BTN_RESEARCH_INSTITUTE,
    msg.BTN_ADV_ENGLISH_PROGRAM,
    # Action / FAQ / resolved keyboards
    msg.BTN_ASK_QUESTION, msg.BTN_REGISTER,
    msg.BTN_FAQ_YES, msg.BTN_FAQ_NO,
    msg.BTN_YES_RESOLVED, msg.BTN_NO_RESOLVED,
})


# ---------------------------------------------------------------------------
# Keyboards
# ---------------------------------------------------------------------------

def _main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [msg.BTN_VALERA_GIVEAWAY, msg.BTN_SAT_CONSULT],
            [msg.BTN_MERCH, msg.BTN_GET_GUIDEBOOK],
            [msg.BTN_ADV_ENGLISH, msg.BTN_SAT_ENROLL],
            [msg.BTN_PROGRAMS, msg.BTN_GENERAL_INQUIRY],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def _program_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [msg.BTN_FULL_SUPPORT, msg.BTN_ADMISSIONS],
            [msg.BTN_IMKON, msg.BTN_MASTERS],
            [msg.BTN_RESEARCH_INSTITUTE, msg.BTN_ADV_PLACEMENT],
            [msg.BTN_SAT, msg.BTN_ADV_ENGLISH_PROGRAM],
            [msg.BTN_HOME],
        ],
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


def _back_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[msg.BTN_BACK]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def _econ_courses_keyboard(selected: set[str]) -> InlineKeyboardMarkup:
    """Multi-select course picker. Selected courses show a checkmark; a final
    Done row submits the registration."""
    rows = [
        [InlineKeyboardButton(
            f"{'✅ ' if key in selected else ''}{label}",
            callback_data=f"econ_course:{key}",
        )]
        for key, label in _ECON_COURSES.items()
    ]
    rows.append([InlineKeyboardButton(msg.BTN_ECON_DONE, callback_data="econ_done")])
    return InlineKeyboardMarkup(rows)


def _sat_format_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[msg.BTN_SAT_ONLINE, msg.BTN_SAT_OFFLINE], [msg.BTN_BACK]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def _ae_format_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(msg.BTN_AE_ONLINE, callback_data="ae_format:online"),
        InlineKeyboardButton(msg.BTN_AE_OFFLINE, callback_data="ae_format:offline"),
    ]])


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
    # Edited messages (and other non-message updates) arrive with update.message=None.
    if update.message is None:
        return
    text = update.message.text
    chat_id = update.effective_chat.id

    # Per-user rate limit — silently drop messages that arrive too fast
    now = time.monotonic()
    if now - _last_message_time.get(chat_id, 0) < _RATE_LIMIT_SECONDS:
        return
    _last_message_time[chat_id] = now

    # Q-admins who aren't experts: if they swipe-reply to a question re-issued
    # via the /unanswered "Answer" button, route it like an expert reply. Only
    # intercepts when the replied-to message matches a tracked question, so
    # all other admin/user behavior is untouched.
    if (
        chat_id in _Q_ADMIN_IDS
        and chat_id not in _EXPERT_CHAT_IDS
        and text
        and update.message.reply_to_message is not None
    ):
        question = await db.get_question_by_expert_message_any_status(
            chat_id, update.message.reply_to_message.message_id
        )
        if question:
            await _handle_expert_message(update, chat_id, text)
            return

    # Admin routing for PERSON_X.
    # If mid-video-setup, route to the video admin handler. Otherwise, if PERSON_X
    # is an expert replying to a question, fall through to the expert handler;
    # any other admin message is ignored.
    if chat_id == PERSON_X_CHAT_ID:
        if _video_admin_state.get("step") is not None:
            await _video_admin_message_handler(update, context)
            return
        if _merch_qr_state["waiting"] and update.message.photo:
            await db.set_setting("merch_payme_qr_file_id", update.message.photo[-1].file_id)
            _merch_qr_state["waiting"] = False
            await update.message.reply_text(msg.MERCH_QR_SAVED)
            return
        is_reply = update.message.reply_to_message is not None
        if not (chat_id in _EXPERT_CHAT_IDS and is_reply and text):
            return
        # Fall through to expert handler below

    # Expert reply routing — intercept before normal button handling
    if chat_id in _EXPERT_CHAT_IDS:
        if text is not None:
            await _handle_expert_message(update, chat_id, text)
        return

    # Allow video/photo/document through for AE media steps
    if text is None:
        # Shared contact — the merch delivery step offers a request_contact button.
        contact = update.message.contact
        if contact is not None:
            user_c = await db.get_user(chat_id)
            if user_c and user_c.get("flow") == "merch" and user_c.get("status") == "merch_step_phone":
                if await _merch_state_valid(context.bot, chat_id):
                    await _handle_merch_phone(update, chat_id, contact.phone_number or "")
                return
        video = update.message.video
        video_note = update.message.video_note
        photo = update.message.photo
        document = update.message.document
        if video or video_note or photo or document:
            user_v = await db.get_user(chat_id)
            if user_v and user_v.get("flow") == "adv_english":
                status_v = user_v.get("status")
                if status_v == "ae_step_video" and (video or video_note):
                    fid = (video or video_note).file_id
                    await _handle_ae_video(update, chat_id, fid, video_note is not None)
                    return
                if status_v == "ae_step_ielts" and (photo or document):
                    if photo:
                        fid, ftype = photo[-1].file_id, "photo"
                    else:
                        fid, ftype = document.file_id, "document"
                    await _handle_ae_ielts_file(update, chat_id, fid, ftype)
                    return
            if user_v and user_v.get("flow") == "ae_payment" and user_v.get("status") == "ae_payment_step_screenshot":
                if photo or document:
                    if photo:
                        fid, ftype = photo[-1].file_id, "photo"
                    else:
                        fid, ftype = document.file_id, "document"
                    await _handle_ae_payment_screenshot(update, chat_id, fid, ftype, context)
                    return
            if user_v and user_v.get("flow") == "tap" and user_v.get("status") == "tap_step_screenshot":
                if photo or document:
                    if photo:
                        fid, ftype = photo[-1].file_id, "photo"
                    else:
                        fid, ftype = document.file_id, "document"
                    await _handle_tap_screenshot(update, chat_id, fid, ftype, context)
                    return
        return

    # Back always takes priority over free-text capture states
    if text == msg.BTN_BACK:
        await _handle_back(update, chat_id)
        return

    # Capture free-text input from user.
    # Nav buttons always escape capture state — reset and fall through to routing.
    user = await db.get_user(chat_id)
    if user and user.get("status") == "awaiting_question_text":
        if text in _NAV_BUTTONS:
            await db.set_flow(chat_id, None)
            await db.set_status(chat_id, None)
        else:
            await _handle_question_text(update, chat_id, text, context)
            return
    if user and user.get("status") == "awaiting_followup_text":
        if text in _NAV_BUTTONS:
            await db.set_flow(chat_id, None)
            await db.set_status(chat_id, None)
        else:
            await _handle_followup_text(update, chat_id, text, context)
            return

    if user and user.get("flow") == "ae_payment" and user.get("status") == "ae_payment_step_screenshot":
        if text in _NAV_BUTTONS:
            await db.set_flow(chat_id, None)
            await db.set_status(chat_id, None)
        else:
            await update.message.reply_text(msg.AE_PAYMENT_SCREENSHOT_REQUIRED)
            return

    if user and user.get("flow") == "tap" and user.get("status") == "tap_step_screenshot":
        if text in _NAV_BUTTONS:
            await db.set_flow(chat_id, None)
            await db.set_status(chat_id, None)
        else:
            await update.message.reply_text(msg.TAP_SCREENSHOT_REQUIRED)
            return

    if user and user.get("flow") == "sat_enroll":
        if text in _NAV_BUTTONS:
            _sat_enroll_state.pop(chat_id, None)
            await db.set_flow(chat_id, None)
            await db.set_status(chat_id, None)
        else:
            await _handle_sat_enroll_step(update, chat_id, text, context)
            return

    if user and user.get("flow") == "econ":
        if text in _NAV_BUTTONS:
            _econ_state.pop(chat_id, None)
            await db.set_flow(chat_id, None)
            await db.set_status(chat_id, None)
        else:
            await _handle_econ_step(update, chat_id, text, context)
            return

    if user and user.get("flow") == "merch":
        if text in _NAV_BUTTONS:
            _merch_state.pop(chat_id, None)
            await db.set_flow(chat_id, None)
            await db.set_status(chat_id, None)
        else:
            await _handle_merch_step(update, chat_id, text, context)
            return

    if user and user.get("flow") == "adv_english" and user.get("status") in (
        "ae_step_format", "ae_step_full_name", "ae_step_video", "ae_step_ielts", "ae_step_sat",
        "ae_step_why", "ae_step_perspective", "ae_step_resources",
    ):
        if text in _NAV_BUTTONS:
            _ae_state.pop(chat_id, None)
            await db.set_flow(chat_id, None)
            await db.set_status(chat_id, None)
        elif user.get("status") == "ae_step_format":
            await update.message.reply_text(msg.AE_ASK_FORMAT, reply_markup=_ae_format_keyboard())
            return
        elif user.get("status") == "ae_step_video":
            await update.message.reply_text(msg.AE_VIDEO_REQUIRED, reply_markup=_back_keyboard())
            return
        elif user.get("status") == "ae_step_ielts":
            await update.message.reply_text(msg.AE_IELTS_REQUIRED, reply_markup=_back_keyboard())
            return
        else:
            await _handle_ae_step(update, chat_id, text, context)
            return

    if text == msg.BTN_PROGRAMS:
        await _handle_programs(update, chat_id)
    elif text == msg.BTN_ADV_ENGLISH:
        await _handle_adv_english(update, chat_id)
    elif text == msg.BTN_TRIAL_AP:
        await _handle_trial_ap(update, chat_id, context)
    elif text == msg.BTN_SAT_ENROLL:
        await _handle_sat_enroll(update, chat_id, context)
    elif text == msg.BTN_GENERAL_INQUIRY:
        await _handle_general_inquiry(update, chat_id)
    elif text == msg.BTN_PODCAST:
        await _handle_podcast(update, chat_id)
    elif text == msg.BTN_GET_GUIDEBOOK:
        await _handle_guidebook(update, chat_id)
    elif text == msg.BTN_GETTING_IN:
        await _handle_getting_in(update, chat_id)
    elif text == msg.BTN_MERCH:
        await _merch_begin(context.bot, chat_id)
    elif text == msg.BTN_SAT_CONSULT:
        await _satc_begin(context.bot, chat_id)
    elif text == msg.BTN_VALERA_GIVEAWAY:
        await _vg_begin(context.bot, chat_id)
    elif text == msg.BTN_SAT:
        await _handle_program(update, chat_id, msg.BTN_SAT)
    elif text == msg.BTN_ADMISSIONS:
        await _handle_program(update, chat_id, msg.BTN_ADMISSIONS)
    elif text == msg.BTN_FULL_SUPPORT:
        await _handle_program(update, chat_id, msg.BTN_FULL_SUPPORT)
    elif text == msg.BTN_MASTERS:
        await _handle_program(update, chat_id, msg.BTN_MASTERS)
    elif text == msg.BTN_ADV_PLACEMENT:
        await _handle_program(update, chat_id, msg.BTN_ADV_PLACEMENT)
    elif text == msg.BTN_IMKON:
        await _handle_program(update, chat_id, msg.BTN_IMKON)
    elif text == msg.BTN_RESEARCH_INSTITUTE:
        await _handle_program(update, chat_id, msg.BTN_RESEARCH_INSTITUTE)
    elif text == msg.BTN_ADV_ENGLISH_PROGRAM:
        await _handle_program(update, chat_id, msg.BTN_ADV_ENGLISH_PROGRAM)
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
    elif text == msg.BTN_BACK:
        await _handle_back(update, chat_id)
    elif text == msg.BTN_HOME:
        user = await db.get_user(chat_id)
        first_name = user["first_name"] if user else "there"
        await db.set_program(chat_id, None)
        await db.set_flow(chat_id, None)
        await db.set_status(chat_id, None)
        await update.message.reply_text(
            msg.WELCOME.format(first_name=first_name),
            reply_markup=_main_keyboard(),
        )
    elif text == msg.BTN_START:
        await start(update, context)
    else:
        # Unrecognized text — likely an old cached button. Push a fresh keyboard.
        user = await db.get_user(chat_id)
        first_name = user["first_name"] if user else "there"
        await update.message.reply_text(
            msg.WELCOME.format(first_name=first_name),
            reply_markup=_main_keyboard(),
        )


# ---------------------------------------------------------------------------
# Main menu → Programs
# ---------------------------------------------------------------------------

async def _handle_programs(update: Update, chat_id: int) -> None:
    await update.message.reply_text(msg.CHOOSE_PROGRAM, reply_markup=_program_keyboard())


# ---------------------------------------------------------------------------
# Program selection
# ---------------------------------------------------------------------------

async def _handle_program(update: Update, chat_id: int, program: str) -> None:
    await db.set_program(chat_id, program)
    description = msg.PROGRAM_DESCRIPTIONS.get(program, "")
    video = await db.get_program_video(program)

    if video:
        file_id, video_type = video
        await update.message.reply_text(msg.PROGRAM_CHOSEN.format(description=description))
        if video_type == "video_note":
            await update.message.reply_video_note(file_id, reply_markup=_action_keyboard())
        else:
            await update.message.reply_video(file_id, reply_markup=_action_keyboard())
    else:
        await update.message.reply_text(
            msg.PROGRAM_CHOSEN.format(description=description),
            reply_markup=_action_keyboard(),
        )


# ---------------------------------------------------------------------------
# General Inquiry — main-menu FAQ/question flow (no program context)
# ---------------------------------------------------------------------------

async def _handle_general_inquiry(update: Update, chat_id: int) -> None:
    await db.set_flow(chat_id, "general_inquiry")
    await db.set_status(chat_id, "awaiting_question_text")
    video = await db.get_program_video("General Inquiry")
    if video:
        file_id, video_type = video
        if video_type == "video_note":
            await update.message.reply_video_note(file_id)
        else:
            await update.message.reply_video(file_id)
    await update.message.reply_text(msg.FAQ_TYPE_QUESTION, reply_markup=_back_keyboard())


async def _handle_adv_english(update: Update, chat_id: int) -> None:
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(msg.BTN_AE_APPLY_NOW, callback_data="ae_apply_now")]
    ])
    await update.message.reply_text(msg.AE_INTRO, reply_markup=keyboard, parse_mode="HTML")


async def _ae_program_faq_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Inline 'Learn More' button (e.g. from /broadcastkeyboard) — show the AE FAQ
    and drop the user into the same question flow a program selection would."""
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id

    await db.set_program(chat_id, msg.BTN_ADV_ENGLISH_PROGRAM)
    await db.set_flow(chat_id, "question")
    await db.set_status(chat_id, "faq_shown")
    await query.message.reply_text(
        msg.PROGRAM_FAQ_MESSAGE[msg.BTN_ADV_ENGLISH_PROGRAM],
        reply_markup=_faq_keyboard(),
        parse_mode="HTML",
    )


async def _ae_apply_now_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id

    existing = await db.ae_get_application(chat_id)
    if existing:
        status = existing["status"]
        if status == "rejected":
            await query.message.reply_text(msg.AE_REJECTED, reply_markup=_main_keyboard())
        elif status == "payment_confirmed":
            await query.message.reply_text(msg.AE_STATUS_PAYMENT_CONFIRMED, reply_markup=_main_keyboard())
        elif status == "payment_pending":
            await query.message.reply_text(msg.AE_STATUS_PAYMENT_PENDING, reply_markup=_main_keyboard())
        elif status in ("terms_accepted", "payment_rejected"):
            payment_keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton(msg.BTN_AE_PAYMENT_MADE, callback_data=f"ae_payment_made:{chat_id}"),
            ]])
            post_chat_id = await db.get_setting("ae_payment_post_chat_id")
            post_message_id = await db.get_setting("ae_payment_post_message_id")
            if post_chat_id and post_message_id:
                await context.bot.copy_message(
                    chat_id=chat_id,
                    from_chat_id=int(post_chat_id),
                    message_id=int(post_message_id),
                    reply_markup=payment_keyboard,
                )
            else:
                await query.message.reply_text(msg.AE_PAYMENT_NOT_SET, reply_markup=payment_keyboard)
            await context.bot.send_message(chat_id=chat_id, text=msg.AE_PAYMENT_HELP)
        else:
            await query.message.reply_text(msg.AE_STATUS_PENDING, reply_markup=_main_keyboard())
        return

    _ae_state[chat_id] = {}
    await db.set_flow(chat_id, "adv_english")
    await db.set_status(chat_id, "ae_step_format")
    await query.message.reply_text(msg.AE_ASK_FORMAT, reply_markup=_ae_format_keyboard())


async def _ae_format_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id

    user = await db.get_user(chat_id)
    if not (user and user.get("flow") == "adv_english" and user.get("status") == "ae_step_format"):
        return

    choice = query.data.split(":")[1]
    format_type = msg.BTN_AE_ONLINE if choice == "online" else msg.BTN_AE_OFFLINE
    _ae_state.setdefault(chat_id, {})["format_type"] = format_type
    await db.set_status(chat_id, "ae_step_full_name")
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass
    await query.message.reply_text(msg.AE_PROMPT_FULL_NAME, reply_markup=_back_keyboard())


_AE_STEPS = [
    ("ae_step_full_name",   "full_name",          "ae_step_video",       msg.AE_PROMPT_VIDEO),
    ("ae_step_sat",         "sat_score",          "ae_step_why",         msg.AE_PROMPT_WHY),
    ("ae_step_why",         "why_adv_english",    "ae_step_perspective", msg.AE_PROMPT_PERSPECTIVE),
    ("ae_step_perspective", "perspective_answer", "ae_step_resources",   msg.AE_PROMPT_RESOURCES),
]

# (min_words, max_words) per essay step — ±5 word tolerance applied to all limits.
_AE_WORD_LIMITS: dict[str, tuple[int, int]] = {
    "ae_step_why": (45, 105),
    "ae_step_perspective": (70, 105),
    "ae_step_resources": (0, 100),
}


def _ae_check_word_count(status: str, text: str) -> str | None:
    limits = _AE_WORD_LIMITS.get(status)
    if not limits:
        return None
    min_w, max_w = limits
    count = len(text.split())
    if min_w == max_w and count != min_w:
        return msg.AE_WORD_COUNT_EXACT.format(exact=min_w, count=count)
    if count < min_w:
        return msg.AE_WORD_COUNT_TOO_SHORT.format(count=count, min=min_w)
    if count > max_w:
        return msg.AE_WORD_COUNT_TOO_LONG.format(count=count, max=max_w)
    return None


async def _handle_ae_step(
    update: Update, chat_id: int, text: str, context: ContextTypes.DEFAULT_TYPE
) -> None:
    user = await db.get_user(chat_id)
    status = user.get("status") if user else None

    for current_status, field, next_status, next_prompt in _AE_STEPS:
        if status == current_status:
            error = _ae_check_word_count(current_status, text)
            if error:
                await update.message.reply_text(error, reply_markup=_back_keyboard())
                return
            _ae_state.setdefault(chat_id, {})[field] = text
            await db.set_status(chat_id, next_status)
            await update.message.reply_text(next_prompt, reply_markup=_back_keyboard(), parse_mode="HTML")
            return

    if status == "ae_step_resources":
        error = _ae_check_word_count("ae_step_resources", text)
        if error:
            await update.message.reply_text(error, reply_markup=_back_keyboard())
            return
        _ae_state.setdefault(chat_id, {})["resources_answer"] = text
        await _ae_finish(update, chat_id, context)


async def _handle_ae_video(
    update: Update, chat_id: int, file_id: str, is_note: bool
) -> None:
    _ae_state.setdefault(chat_id, {})["video_file_id"] = file_id
    _ae_state[chat_id]["video_type"] = "video_note" if is_note else "video"
    await db.set_status(chat_id, "ae_step_ielts")
    await update.message.reply_text(msg.AE_PROMPT_IELTS, reply_markup=_back_keyboard())


async def _handle_ae_ielts_file(
    update: Update, chat_id: int, file_id: str, file_type: str
) -> None:
    _ae_state.setdefault(chat_id, {})["ielts"] = file_id
    _ae_state[chat_id]["ielts_file_type"] = file_type
    await db.set_status(chat_id, "ae_step_sat")
    await update.message.reply_text(msg.AE_PROMPT_SAT, reply_markup=_back_keyboard())


async def _ae_finish(
    update: Update, chat_id: int, context: ContextTypes.DEFAULT_TYPE
) -> None:
    answers = _ae_state.pop(chat_id, {})
    user = await db.get_user(chat_id)
    username = user.get("username") if user else None
    first_name = user["first_name"] if user else "Unknown"

    format_type     = answers.get("format_type", "")
    full_name       = answers.get("full_name", "")
    video_file_id   = answers.get("video_file_id", "")
    video_type      = answers.get("video_type", "video")
    ielts           = answers.get("ielts", "")
    ielts_file_type = answers.get("ielts_file_type", "photo")
    sat_score       = answers.get("sat_score", "")
    why_adv_english = answers.get("why_adv_english", "")
    perspective     = answers.get("perspective_answer", "")
    resources       = answers.get("resources_answer", "")

    await db.ae_save_application(
        chat_id=chat_id,
        username=username,
        format_type=format_type,
        full_name=full_name,
        video_file_id=video_file_id,
        video_type=video_type,
        ielts=ielts,
        ielts_file_type=ielts_file_type,
        sat_score=sat_score,
        why_adv_english=why_adv_english,
        perspective_answer=perspective,
        resources_answer=resources,
    )

    await db.set_flow(chat_id, None)
    await db.set_status(chat_id, None)
    await update.message.reply_text(msg.AE_SUBMITTED, reply_markup=_main_keyboard())

    username_part = f" (@{username})" if username else ""
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("\U0001f4cb View Applications", callback_data="ae_list"),
    ]])
    await context.bot.send_message(
        chat_id=ADV_ENGLISH_REVIEWER_CHAT_ID,
        text=f"\U0001f4e9 New AE application from {first_name}{username_part}",
        reply_markup=keyboard,
    )


async def _ae_list_handler(
    context: ContextTypes.DEFAULT_TYPE, target_chat_id: int
) -> None:
    applications = await db.ae_get_all_applications()
    if not applications:
        await context.bot.send_message(chat_id=target_chat_id, text="No AE applications yet.")
        return
    buttons = [
        [InlineKeyboardButton(
            f"{app['full_name']} — {app['status']}",
            callback_data=f"ae_view:{app['id']}",
        )]
        for app in applications
    ]
    await context.bot.send_message(
        chat_id=target_chat_id,
        text=f"\U0001f4cb Advanced English Applications ({len(applications)}):",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def _ae_list_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    await update.callback_query.answer()
    await _ae_list_handler(context, update.callback_query.message.chat.id)


async def _ae_list_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if update.effective_chat.id not in _AE_REVIEWER_IDS:
        return
    await _ae_list_handler(context, update.effective_chat.id)


async def _ae_view_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()
    application_id = int(query.data.split(":")[1])
    application = await db.ae_get_application_by_id(application_id)
    if not application:
        await query.message.reply_text("Application not found.")
        return

    app = dict(application)
    username_part = f" (@{app['username']})" if app.get("username") else ""
    text = (
        f"<b>Advanced English Application</b>\n"
        f"{'─' * 28}\n"
        f"<b>Name:</b> {app['full_name']}{username_part}\n"
        f"<b>Format:</b> {app.get('format_type') or 'N/A'}\n"
        f"<b>Status:</b> {app['status']}\n"
        f"<b>SAT:</b> {app.get('sat_score') or 'N/A'}\n\n"
        f"<b>Q: Why do you want to join Advanced English?</b>\n{app['why_adv_english']}\n\n"
        f"<b>Q: What is a topic, book, or idea you have encountered recently that completely changed your perspective on a subject?</b>\n{app['perspective_answer']}\n\n"
        f"<b>Q: List texts, resources, and outlets that have shaped your intellectual development — books, journals, podcasts, essays, videos, or other content you value.</b>\n{app['resources_answer']}"
    )
    reviewer_chat_id = query.message.chat.id
    await context.bot.send_message(
        chat_id=reviewer_chat_id, text=text, parse_mode="HTML"
    )

    ielts_fid = app.get("ielts")
    ielts_ftype = app.get("ielts_file_type", "photo")
    if ielts_fid:
        try:
            if ielts_ftype == "document":
                await context.bot.send_document(
                    chat_id=reviewer_chat_id, document=ielts_fid, caption="IELTS certificate"
                )
            else:
                await context.bot.send_photo(
                    chat_id=reviewer_chat_id, photo=ielts_fid, caption="IELTS certificate"
                )
        except Exception:
            await context.bot.send_message(
                chat_id=reviewer_chat_id, text="⚠️ Could not load IELTS certificate."
            )

    video_file_id = app.get("video_file_id")
    video_type = app.get("video_type", "video")
    if video_file_id:
        try:
            if video_type == "video_note":
                await context.bot.send_video_note(
                    chat_id=reviewer_chat_id, video_note=video_file_id
                )
            else:
                await context.bot.send_video(
                    chat_id=reviewer_chat_id, video=video_file_id,
                    caption="Video introduction",
                )
        except Exception:
            await context.bot.send_message(
                chat_id=reviewer_chat_id, text="⚠️ Could not load video."
            )

    if app["status"] == "pending":
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(msg.BTN_AE_ACCEPT, callback_data=f"ae_accept:{application_id}"),
            InlineKeyboardButton(msg.BTN_AE_REJECT, callback_data=f"ae_reject:{application_id}"),
        ]])
        await context.bot.send_message(
            chat_id=reviewer_chat_id,
            text=f"Decision for <b>{app['full_name']}</b>:",
            parse_mode="HTML",
            reply_markup=keyboard,
        )


async def _ae_decision_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE, decision: str
) -> None:
    query = update.callback_query
    await query.answer()

    application_id = int(query.data.split(":")[1])
    application = await db.ae_get_application_by_id(application_id)

    if not application:
        await query.edit_message_reply_markup(reply_markup=None)
        return

    if application["status"] != "pending":
        await query.answer(msg.AE_REVIEWER_ALREADY_DECIDED, show_alert=True)
        return

    await db.ae_set_status(application_id, decision)

    applicant_chat_id = application["chat_id"]
    applicant_msg = msg.AE_ACCEPTED if decision == "accepted" else msg.AE_REJECTED
    reviewer_confirmation = msg.AE_REVIEWER_ACCEPTED if decision == "accepted" else msg.AE_REVIEWER_REJECTED

    try:
        await context.bot.send_message(chat_id=applicant_chat_id, text=applicant_msg)
        if decision == "accepted":
            await db.ae_set_status_by_chat_id(applicant_chat_id, "terms_accepted")
            payment_keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton(msg.BTN_AE_PAYMENT_MADE, callback_data=f"ae_payment_made:{applicant_chat_id}"),
            ]])
            post_chat_id = await db.get_setting("ae_payment_post_chat_id")
            post_message_id = await db.get_setting("ae_payment_post_message_id")
            if post_chat_id and post_message_id:
                await context.bot.copy_message(
                    chat_id=applicant_chat_id,
                    from_chat_id=int(post_chat_id),
                    message_id=int(post_message_id),
                    reply_markup=payment_keyboard,
                )
            else:
                await context.bot.send_message(
                    chat_id=applicant_chat_id,
                    text=msg.AE_PAYMENT_NOT_SET,
                    reply_markup=payment_keyboard,
                )
            await context.bot.send_message(
                chat_id=applicant_chat_id,
                text=msg.AE_PAYMENT_HELP,
            )
    except Exception:
        logger.exception("Failed to notify applicant chat_id=%d", applicant_chat_id)

    await query.edit_message_text(
        text=f"{query.message.text}\n\n{reviewer_confirmation}",
        reply_markup=None,
    )


async def _ae_accept_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _ae_decision_callback(update, context, "accepted")


async def _ae_reject_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _ae_decision_callback(update, context, "rejected")


async def _ae_set_terms_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if update.effective_chat.id not in _AE_REVIEWER_IDS:
        return
    reply = update.message.reply_to_message
    if not reply or not reply.document:
        await update.message.reply_text(msg.AE_SET_TERMS_USAGE)
        return
    await db.set_setting("ae_terms_file_id", reply.document.file_id)
    await update.message.reply_text(msg.AE_SET_TERMS_SUCCESS)


async def _set_guidebook_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if update.effective_chat.id != PERSON_X_CHAT_ID and update.effective_chat.id not in _AE_REVIEWER_IDS:
        return
    reply = update.message.reply_to_message
    if not reply or not reply.document:
        await update.message.reply_text(msg.GUIDEBOOK_SET_USAGE)
        return
    await db.set_setting("guidebook_file_id", reply.document.file_id)
    await update.message.reply_text(msg.GUIDEBOOK_SET_SUCCESS)


async def _guidebook_count_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if update.effective_chat.id != PERSON_X_CHAT_ID and update.effective_chat.id not in _AE_REVIEWER_IDS:
        return
    count = await db.count_guidebook_recipients()
    await update.message.reply_text(
        f"📖 Guidebook delivered to {count} unique user(s)."
    )


async def _clear_adv_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.id != PERSON_X_CHAT_ID:
        return
    count = await db.ae_clear_all_applications()
    await update.message.reply_text(f"✅ Cleared {count} Advanced English application(s).")


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

    program = user.get("program") if user else None
    faq_message = msg.PROGRAM_FAQ_MESSAGE.get(program or "", msg.SAT_FAQ_MESSAGE)

    await update.message.reply_text(
        faq_message,
        reply_markup=_faq_keyboard(),
        parse_mode="HTML",
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

def _q_skip_keyboard(question_id: int) -> InlineKeyboardMarkup:
    """Skip button attached to a question sent to an expert — dismisses a duplicate
    or spam question without sending the student anything."""
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(msg.BTN_Q_SKIP, callback_data=f"qs:{question_id}")]]
    )


async def _handle_question_text(
    update: Update, chat_id: int, text: str | None, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not text:
        await update.message.reply_text(msg.FAQ_TYPE_QUESTION, reply_markup=_back_keyboard())
        return
    if len(text) > 1000:
        await update.message.reply_text(msg.QUESTION_TOO_LONG, reply_markup=_back_keyboard())
        return
    user = await db.get_user(chat_id)
    flow = user.get("flow") if user else None
    program = _FLOW_PROGRAM.get(flow or "") or (user.get("program") if user else None)
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
        # Saved before sending so the Skip button can carry the question id, and so
        # a failed send still leaves the question visible in /unanswered.
        question_id = await db.save_question(chat_id, program or "", text)
        try:
            sent = await context.bot.send_message(
                chat_id=expert_chat_id,
                text=expert_text,
                reply_markup=_q_skip_keyboard(question_id),
            )
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

    _expert_clarification_state[expert_chat_id] = {
        "user_chat_id": question["user_chat_id"],
        "thread_id": question.get("thread_id"),
        "question_id": question["id"],
    }
    await update.message.reply_text(msg.EXPERT_CLARIFY_READY)


# ---------------------------------------------------------------------------
# Conversation chain formatter
# ---------------------------------------------------------------------------

def _format_chain(questions: list[dict], new_answer: str | None = None) -> str:
    parts = []
    for i, q in enumerate(questions):
        is_last = i == len(questions) - 1
        parts.append(f"❓ {q['question_text']}")
        answer = new_answer if (is_last and new_answer is not None) else q.get("answer_text")
        if answer:
            parts.append(f"💬 {answer}")
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Expert sends a message — route reply back to the student
# ---------------------------------------------------------------------------

async def _handle_expert_message(
    update: Update, expert_chat_id: int, text: str
) -> None:
    # If expert previously sent /clarify, this message is the clarification text.
    if expert_chat_id in _expert_clarification_state and update.message.reply_to_message is None:
        state = _expert_clarification_state.pop(expert_chat_id)
        user_chat_id = state["user_chat_id"]
        thread_id = state.get("thread_id")
        question_id = state.get("question_id")
        try:
            if question_id:
                await db.append_clarification(question_id, text)
            if thread_id:
                thread = await db.get_thread(thread_id)
                student_text = _format_chain(thread)
            else:
                student_text = msg.CLARIFICATION_FROM_EXPERT.format(answer=text)
            await update.get_bot().send_message(chat_id=user_chat_id, text=student_text)
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

    question = await db.get_question_by_expert_message_any_status(
        expert_chat_id, reply_to.message_id
    )

    if not question:
        await update.message.reply_text(msg.EXPERT_REPLY_NOT_FOUND)
        return

    if question["status"] == "skipped":
        await update.message.reply_text(msg.EXPERT_ALREADY_SKIPPED)
        return

    if question["status"] != "pending":
        await update.message.reply_text(msg.EXPERT_ALREADY_ANSWERED)
        return

    user_chat_id = question["user_chat_id"]
    question_id = question["id"]
    question_text = question["question_text"]
    thread_id = question.get("thread_id")

    try:
        await db.mark_question_answered(question_id, text)
        await db.mark_sibling_questions_answered(user_chat_id, question_text)
        if thread_id:
            thread = await db.get_thread(thread_id)
            student_text = _format_chain(thread, new_answer=text)
        else:
            student_text = msg.ANSWER_FROM_EXPERT.format(question=question_text, answer=text)
        await update.get_bot().send_message(chat_id=user_chat_id, text=student_text)
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

    # Advanced English has no booking URL — route to its standalone application flow.
    if program == msg.BTN_ADV_ENGLISH_PROGRAM:
        await _handle_adv_english(update, chat_id)
        return

    intro = _PROGRAM_WEBSITE_INTRO.get(program, msg.WEBSITE_LINK_INTRO)
    await update.message.reply_text(intro, reply_markup=ReplyKeyboardRemove())
    await update.message.reply_text(
        _PROGRAM_WEBSITE_URL.get(program, ""),
        reply_markup=_action_keyboard(),
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
    program = user.get("program") if user else None
    last_q = await db.get_last_question(chat_id)
    question_text = last_q["question_text"] if last_q else "—"
    username_part = f" (@{raw_username})" if raw_username else ""

    if raw_username:
        admin_text = msg.ESCALATION_TO_PERSON_X.format(
            username=raw_username,
            first_name=first_name,
            chat_id=chat_id,
            question=question_text,
        )
    else:
        admin_text = msg.ESCALATION_TO_PERSON_X_NO_USERNAME.format(
            first_name=first_name,
            chat_id=chat_id,
            question=question_text,
        )

    expert_text = msg.ESCALATION_TO_EXPERT.format(
        first_name=first_name,
        username_part=username_part,
        question=question_text,
    )

    bot = update.get_bot()
    await bot.send_message(chat_id=PERSON_X_CHAT_ID, text=admin_text)
    await bot.send_message(chat_id=PERSON_Z_CHAT_ID, text=admin_text)
    thread_id = last_q.get("thread_id") or (last_q["id"] if last_q else None)
    for expert_id in (_PROGRAM_EXPERT.get(program or "") or []):
        try:
            sent = await bot.send_message(chat_id=expert_id, text=expert_text)
            if thread_id:
                question_id = await db.save_question(
                    chat_id, program or "", question_text, thread_id=thread_id
                )
                await db.set_question_expert_message(question_id, expert_id, sent.message_id)
        except Exception:
            logger.exception("Failed to send escalation to expert %d", expert_id)
    await update.message.reply_text(
        msg.RESOLVED_NO_USER_REPLY,
        reply_markup=_start_keyboard(),
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

    if flow == "sat_enroll":
        _sat_enroll_state.pop(chat_id, None)
        await db.set_flow(chat_id, None)
        await db.set_status(chat_id, None)
        await update.message.reply_text(
            msg.WELCOME.format(first_name=first_name),
            reply_markup=_main_keyboard(),
        )
        return
    if flow == "econ":
        _econ_state.pop(chat_id, None)
        await db.set_flow(chat_id, None)
        await db.set_status(chat_id, None)
        await update.message.reply_text(
            msg.WELCOME.format(first_name=first_name),
            reply_markup=_main_keyboard(),
        )
        return
    if flow == "merch":
        _merch_state.pop(chat_id, None)
        await db.set_flow(chat_id, None)
        await db.set_status(chat_id, None)
        await update.message.reply_text(
            msg.WELCOME.format(first_name=first_name),
            reply_markup=_main_keyboard(),
        )
        return
    if flow == "adv_english":
        _ae_state.pop(chat_id, None)
        await db.set_flow(chat_id, None)
        await db.set_status(chat_id, None)
        await update.message.reply_text(
            msg.WELCOME.format(first_name=first_name),
            reply_markup=_main_keyboard(),
        )
        return
    elif flow == "general_inquiry":
        await db.set_flow(chat_id, None)
        await db.set_status(chat_id, None)
        await update.message.reply_text(
            msg.WELCOME.format(first_name=first_name),
            reply_markup=_main_keyboard(),
        )
    elif flow in ("question",) or (
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
# /followup — user sends a follow-up after receiving an answer
# ---------------------------------------------------------------------------

async def followup_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    last_q = await db.get_last_answered_question(chat_id)
    if not last_q:
        await update.message.reply_text(msg.FOLLOWUP_NO_PREVIOUS)
        return
    await db.set_status(chat_id, "awaiting_followup_text")
    thread_id = last_q.get("thread_id") or last_q["id"]
    thread = await db.get_thread(thread_id)
    chain = _format_chain(thread)
    await update.message.reply_text(f"─── Conversation so far ───\n\n{chain}")
    await update.message.reply_text(msg.FOLLOWUP_TYPE_QUESTION, reply_markup=_back_keyboard())


async def _handle_followup_text(
    update: Update, chat_id: int, text: str | None, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not text:
        await update.message.reply_text(msg.FOLLOWUP_TYPE_QUESTION, reply_markup=_back_keyboard())
        return
    if len(text) > 1000:
        await update.message.reply_text(msg.QUESTION_TOO_LONG, reply_markup=_back_keyboard())
        return

    last_q = await db.get_last_answered_question(chat_id)
    if not last_q:
        await update.message.reply_text(msg.FOLLOWUP_NO_PREVIOUS, reply_markup=_start_keyboard())
        await db.set_status(chat_id, None)
        return

    user = await db.get_user(chat_id)
    first_name = user["first_name"] if user else "Unknown"
    raw_username = user.get("username") if user else None
    username_part = f" (@{raw_username})" if raw_username else ""
    program = last_q.get("program") or "General Inquiry"
    thread_id = last_q.get("thread_id") or last_q["id"]

    expert_chat_ids = _PROGRAM_EXPERT.get(program, GENERAL_MAN_CHAT_ID)

    thread = await db.get_thread(thread_id)
    chain = _format_chain(thread)
    expert_text = (
        f"🔄 Follow-up from {first_name}{username_part} (Program: {program}):\n\n"
        f"{chain}\n\n"
        f"❓ {text}\n\n"
        f"Reply to this message to send your answer to the student."
    )

    for expert_chat_id in expert_chat_ids:
        try:
            sent = await context.bot.send_message(chat_id=expert_chat_id, text=expert_text)
            question_id = await db.save_question(chat_id, program, text, thread_id=thread_id)
            await db.set_question_expert_message(question_id, expert_chat_id, sent.message_id)
        except Exception:
            logger.exception(
                "Failed to forward follow-up from chat_id=%d to expert %d", chat_id, expert_chat_id
            )

    await db.set_flow(chat_id, None)
    await db.set_status(chat_id, "question_pending")
    await update.message.reply_text(msg.FOLLOWUP_FORWARDED, reply_markup=_start_keyboard())


# ---------------------------------------------------------------------------
# Event gate — admin flow (PERSON_X only)
# ---------------------------------------------------------------------------

# In-memory state for the two-step /event setup (only one admin, no DB needed)

# In-memory state for /setvideo admin flow
_video_admin_state: dict = {"step": None, "program": None}


# Tracks last rolled participant ID for /reroll exclusion


async def _export_db_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != PERSON_X_CHAT_ID:
        return
    with open(db.DB_PATH, "rb") as f:
        await update.message.reply_document(document=f, filename="bot.db")


async def _stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id not in {PERSON_X_CHAT_ID, VALERA_CHAT_ID}:
        return
    s = await db.get_stats()

    if s["questions_by_program"]:
        lines = "\n".join(
            f"    {program} — {total} total\n"
            f"      ✅ {answered or 0} answered  •  ⏳ {pending or 0} pending"
            for program, total, answered, pending in s["questions_by_program"]
        )
        by_program = f"\n  \U0001f4cb By program:\n{lines}\n"
    else:
        by_program = ""

    videos = ", ".join(s["videos_set"]) if s["videos_set"] else "none"

    await update.message.reply_text(
        msg.ADMIN_STATS.format(
            total_users=s["total_users"],
            active_users_7d=s["active_users_7d"],
            users_in_flow=s["users_in_flow"],
            total_questions=s["total_questions"],
            pending_questions=s["pending_questions"],
            answered_questions=s["answered_questions"],
            questions_by_program=by_program,
            pending_jobs=s["pending_jobs"],
            videos_set=videos,
            ae_total=s["ae_total"],
            ae_pending=s["ae_pending"],
            ae_accepted=s["ae_accepted"],
            ae_rejected=s["ae_rejected"],
        )
    )


async def _broadcast_keyboard_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if update.effective_user.id != PERSON_X_CHAT_ID:
        return
    chat_ids = await db.get_all_chat_ids()
    await update.message.reply_text(f"📢 Broadcasting to {len(chat_ids)} users — I'll report back when done.")

    async def _run() -> None:
        sent = failed = 0
        first_error: str | None = None
        # Send in fixed-size batches with a pause in between so the broadcast
        # stays under Telegram's ~30 msg/s flood limit and never starves the
        # connection pool or send budget that live user replies depend on.
        batch_size = 20
        batch_pause = 1.5

        async def _send_one(cid: int) -> None:
            nonlocal sent, failed, first_error
            try:
                # SAT consultations giveaway announcement — the button runs
                # the subscription gate and hands over the booking link.
                await context.bot.send_message(
                    chat_id=cid,
                    text=msg.SATC_ANNOUNCEMENT,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(msg.BTN_SATC_OPEN, callback_data="satc_open")],
                    ]),
                )
                sent += 1
            except Exception as e:
                if first_error is None:
                    first_error = f"{type(e).__name__}: {e}"
                logger.warning("Broadcast failed for chat_id=%d: %s: %s", cid, type(e).__name__, e)
                failed += 1

        for start in range(0, len(chat_ids), batch_size):
            await asyncio.gather(*(_send_one(cid) for cid in chat_ids[start:start + batch_size]))
            await asyncio.sleep(batch_pause)
        result = msg.BROADCAST_KEYBOARD_DONE.format(sent=sent, failed=failed, total=len(chat_ids))
        if first_error:
            result += f"\n\nFirst error: {first_error}"
        await update.message.reply_text(result)

    asyncio.create_task(_run())


# ---------------------------------------------------------------------------
# /setvideo — admin flow (PERSON_X only)
# ---------------------------------------------------------------------------

async def _video_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != PERSON_X_CHAT_ID:
        return
    _video_admin_state["step"] = "awaiting_program"
    _video_admin_state["program"] = None
    keyboard = [
        [InlineKeyboardButton(p, callback_data=f"setvideo_{p}")]
        for p in (*msg.PROGRAM_DESCRIPTIONS.keys(), "General Inquiry")
    ]
    await update.message.reply_text(
        msg.SETVIDEO_CHOOSE_PROGRAM,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def _video_admin_program_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()
    if update.effective_user.id != PERSON_X_CHAT_ID:
        return
    program = query.data[len("setvideo_"):]
    _video_admin_state["step"] = "awaiting_video"
    _video_admin_state["program"] = program
    await query.edit_message_text(msg.SETVIDEO_SEND_VIDEO.format(program=program))


async def _video_admin_message_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if _video_admin_state.get("step") != "awaiting_video":
        return
    video = update.message.video
    video_note = update.message.video_note
    if not (video or video_note):
        await update.message.reply_text(msg.SETVIDEO_NOT_VIDEO)
        return
    file_id = (video or video_note).file_id
    video_type = "video_note" if video_note else "video"
    program = _video_admin_state["program"]
    await db.upsert_program_video(program, file_id, video_type)
    _video_admin_state["step"] = None
    _video_admin_state["program"] = None
    await update.message.reply_text(msg.SETVIDEO_SAVED.format(program=program))


async def _delete_video_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != PERSON_X_CHAT_ID:
        return
    programs = await db.get_programs_with_videos()
    if not programs:
        await update.message.reply_text(msg.DELETEVIDEO_NONE_SET)
        return
    keyboard = [
        [InlineKeyboardButton(p, callback_data=f"deletevideo_{p}")]
        for p in programs
    ]
    await update.message.reply_text(
        msg.DELETEVIDEO_CHOOSE_PROGRAM,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def _delete_video_program_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()
    if update.effective_user.id != PERSON_X_CHAT_ID:
        return
    program = query.data[len("deletevideo_"):]
    deleted = await db.delete_program_video(program)
    if deleted:
        await query.edit_message_text(msg.DELETEVIDEO_DELETED.format(program=program))
    else:
        await query.edit_message_text(msg.DELETEVIDEO_NOT_SET.format(program=program))


async def _ping_experts_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != PERSON_X_CHAT_ID:
        return
    ok, fail = [], []
    seen = set()
    for program, expert_ids in _PROGRAM_EXPERT.items():
        for eid in expert_ids:
            if eid in seen:
                continue
            seen.add(eid)
            try:
                await context.bot.send_message(chat_id=eid, text="✅ Ping from bot — you are reachable.")
                ok.append(f"✅ {eid} ({program})")
            except Exception as e:
                fail.append(f"❌ {eid} ({program}): {e}")
    lines = ["*Ping results:*", ""] + ok + ([""] + fail if fail else [])
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def _podcast_get_missing(bot, chat_id: int) -> list[str]:
    if not PODCAST_CHANNEL_IDS:
        return []
    missing = []
    for channel_id, handle in zip(PODCAST_CHANNEL_IDS, PODCAST_CHANNEL_HANDLES):
        try:
            member = await bot.get_chat_member(channel_id, chat_id)
            if member.status not in _MEMBER_STATUSES:
                missing.append(handle)
        except TelegramError:
            logger.warning("Cannot check podcast membership in %s. Failing open.", channel_id)
    return missing


async def _handle_podcast(update: Update, chat_id: int) -> None:
    missing = await _podcast_get_missing(update.get_bot(), chat_id)
    if missing:
        channel_list = "\n".join(f"• {h}" for h in missing)
        await update.message.reply_text(
            msg.PODCAST_MUST_JOIN.format(channel_list=channel_list),
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(msg.BTN_PODCAST_CHECK, callback_data="podcast_check")]]
            ),
        )
        return
    await update.message.reply_text(
        msg.PODCAST_ACCESS_GRANTED.format(youtube_url=PODCAST_YOUTUBE_URL),
        reply_markup=_main_keyboard(),
    )


async def _podcast_check_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_user.id
    missing = await _podcast_get_missing(context.bot, chat_id)
    if missing:
        channel_list = "\n".join(f"• {h}" for h in missing)
        try:
            await query.edit_message_text(
                msg.PODCAST_MUST_JOIN.format(channel_list=channel_list),
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton(msg.BTN_PODCAST_CHECK, callback_data="podcast_check")]]
                ),
            )
        except TelegramError as e:
            if "not modified" not in str(e).lower():
                raise
        return
    try:
        await query.edit_message_text(
            msg.PODCAST_ACCESS_GRANTED.format(youtube_url=PODCAST_YOUTUBE_URL),
        )
    except TelegramError as e:
        if "not modified" not in str(e).lower():
            raise


# ---------------------------------------------------------------------------
# Extracurriculars Guidebook — subscribe to both channels, then get the file
# ---------------------------------------------------------------------------

GUIDEBOOK_REQUIRED_IDS = [-1001188644050, -1001481432083]
GUIDEBOOK_REQUIRED_HANDLES = ["@valeranotes", "@freshmanblog"]


async def _guidebook_is_member(bot, channel_id: int, chat_id: int) -> bool:
    """True if chat_id is a member of channel_id. Fails open on API error."""
    try:
        member = await bot.get_chat_member(channel_id, chat_id)
        return member.status in _MEMBER_STATUSES
    except TelegramError:
        logger.warning("Cannot check guidebook membership in %s. Failing open.", channel_id)
        return True


async def _guidebook_get_missing(bot, chat_id: int) -> list[str]:
    # Check both channels concurrently so the user isn't waiting on two
    # sequential round-trips (each already queued behind the rate limiter).
    results = await asyncio.gather(
        *(_guidebook_is_member(bot, cid, chat_id) for cid in GUIDEBOOK_REQUIRED_IDS)
    )
    return [h for h, ok in zip(GUIDEBOOK_REQUIRED_HANDLES, results) if not ok]


async def _guidebook_deliver(bot, chat_id: int) -> None:
    """Send the guidebook file once requirements are met."""
    file_id = await db.get_setting("guidebook_file_id")
    if not file_id:
        logger.warning("guidebook_file_id is not set; cannot deliver guidebook.")
        await bot.send_message(chat_id=chat_id, text=msg.GUIDEBOOK_UNAVAILABLE)
        return
    await bot.send_document(
        chat_id=chat_id,
        document=file_id,
        caption=msg.GUIDEBOOK_ACCESS_GRANTED,
        parse_mode="HTML",
    )
    await db.mark_guidebook_sent(chat_id)
    logger.info("Guidebook delivered to chat_id=%d", chat_id)


async def _guidebook_send_flow(bot, chat_id: int) -> None:
    missing = await _guidebook_get_missing(bot, chat_id)
    if missing:
        channel_list = "\n".join(f"• {h}" for h in missing)
        await bot.send_message(
            chat_id=chat_id,
            text=msg.GUIDEBOOK_MUST_JOIN.format(channel_list=channel_list),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(msg.BTN_GUIDEBOOK_CHECK, callback_data="guidebook_check")]]
            ),
        )
        return
    await _guidebook_deliver(bot, chat_id)


async def _handle_guidebook(update: Update, chat_id: int) -> None:
    await _guidebook_send_flow(update.get_bot(), chat_id)


async def _safe_answer(query) -> None:
    """Ack a callback query, ignoring 'query is too old' errors.

    Under a broadcast burst the AIORateLimiter can delay answer_callback_query
    past Telegram's expiry window; if that ack fails we must still run the flow,
    so this never propagates.
    """
    try:
        await query.answer()
    except TelegramError:
        pass


async def _guidebook_get_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Inline "Get Extracurriculars Guidebook" button from /broadcastkeyboard —
    # runs the same gate flow.
    query = update.callback_query
    await _safe_answer(query)
    await _guidebook_send_flow(context.bot, update.effective_user.id)


async def _guidebook_check_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await _safe_answer(query)
    chat_id = update.effective_user.id
    missing = await _guidebook_get_missing(context.bot, chat_id)
    if missing:
        channel_list = "\n".join(f"• {h}" for h in missing)
        try:
            await query.edit_message_text(
                msg.GUIDEBOOK_MUST_JOIN.format(channel_list=channel_list),
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton(msg.BTN_GUIDEBOOK_CHECK, callback_data="guidebook_check")]]
                ),
            )
        except TelegramError as e:
            if "not modified" not in str(e).lower():
                raise
        return
    await _guidebook_deliver(context.bot, chat_id)


# ---------------------------------------------------------------------------
# Getting In with Abrorbek Samijonov — group chat invite
# ---------------------------------------------------------------------------

GETTING_IN_GROUP_URL = "https://t.me/+KegB4Myh01NmOWIy"

# Coming-soon gate. True = series is live for everyone. False = only /santix
# bypass users see it (everyone else gets GETTING_IN_COMING_SOON).
GETTING_IN_LIVE = True


async def _handle_getting_in(update: Update, chat_id: int) -> None:
    if not GETTING_IN_LIVE and chat_id not in _bypass_users:
        await update.message.reply_text(msg.GETTING_IN_COMING_SOON)
        return
    await update.get_bot().send_message(
        chat_id=chat_id,
        text=msg.GETTING_IN_INTRO,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton(msg.BTN_GETTING_IN_JOIN, url=GETTING_IN_GROUP_URL)]]
        ),
    )


# ---------------------------------------------------------------------------
# AE payment flow — terms acceptance, payment QR, screenshot review, invite link
# ---------------------------------------------------------------------------

async def _ae_terms_accept_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()
    applicant_chat_id = int(query.data.split(":")[1])

    application = await db.ae_get_application(applicant_chat_id)
    if not application or application["status"] not in ("accepted",):
        return

    await db.ae_set_status_by_chat_id(applicant_chat_id, "terms_accepted")
    await query.edit_message_reply_markup(reply_markup=None)

    payment_keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(msg.BTN_AE_PAYMENT_MADE, callback_data=f"ae_payment_made:{applicant_chat_id}"),
    ]])
    post_chat_id = await db.get_setting("ae_payment_post_chat_id")
    post_message_id = await db.get_setting("ae_payment_post_message_id")
    if post_chat_id and post_message_id:
        await context.bot.copy_message(
            chat_id=applicant_chat_id,
            from_chat_id=int(post_chat_id),
            message_id=int(post_message_id),
            reply_markup=payment_keyboard,
        )
    else:
        await context.bot.send_message(
            chat_id=applicant_chat_id,
            text=msg.AE_PAYMENT_NOT_SET,
            reply_markup=payment_keyboard,
        )


async def _ae_payment_made_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()
    applicant_chat_id = int(query.data.split(":")[1])

    application = await db.ae_get_application(applicant_chat_id)
    if not application or application["status"] not in ("terms_accepted", "payment_rejected"):
        return

    await query.edit_message_reply_markup(reply_markup=None)
    await db.set_flow(applicant_chat_id, "ae_payment")
    await db.set_status(applicant_chat_id, "ae_payment_step_screenshot")
    await context.bot.send_message(
        chat_id=applicant_chat_id,
        text=msg.AE_PAYMENT_SCREENSHOT_PROMPT,
        reply_markup=_back_keyboard(),
    )


async def _handle_ae_payment_screenshot(
    update: Update,
    chat_id: int,
    file_id: str,
    file_type: str,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    await db.ae_set_payment_screenshot(chat_id, file_id, file_type)
    await db.set_flow(chat_id, None)
    await db.set_status(chat_id, None)
    await update.message.reply_text(msg.AE_PAYMENT_SUBMITTED, reply_markup=_main_keyboard())

    user = await db.get_user(chat_id)
    first_name = user["first_name"] if user else "Unknown"
    username = user["username"] if user else None
    username_part = f" (@{username})" if username else ""

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(msg.BTN_AE_CONFIRM_PAYMENT, callback_data=f"ae_payment_confirm:{chat_id}"),
        InlineKeyboardButton(msg.BTN_AE_REJECT_PAYMENT, callback_data=f"ae_payment_reject:{chat_id}"),
    ]])

    for reviewer_id in _AE_REVIEWER_IDS:
        if file_type == "photo":
            await context.bot.send_photo(
                chat_id=reviewer_id,
                photo=file_id,
                caption=msg.AE_PAYMENT_REVIEWER_ENTRY.format(
                    first_name=first_name, username_part=username_part
                ),
                reply_markup=keyboard,
            )
        else:
            await context.bot.send_document(
                chat_id=reviewer_id,
                document=file_id,
                caption=msg.AE_PAYMENT_REVIEWER_ENTRY.format(
                    first_name=first_name, username_part=username_part
                ),
                reply_markup=keyboard,
            )


async def _ae_payment_decision_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE, decision: str
) -> None:
    query = update.callback_query

    applicant_chat_id = int(query.data.split(":")[1])
    application = await db.ae_get_application(applicant_chat_id)

    if not application or application["status"] != "payment_pending":
        await query.answer(msg.AE_PAYMENT_ALREADY_DECIDED, show_alert=True)
        return

    await query.answer()

    caption = query.message.caption or ""

    if decision == "confirmed":
        await db.ae_set_status_by_chat_id(applicant_chat_id, "payment_confirmed")
        try:
            invite = await context.bot.create_chat_invite_link(
                chat_id=AE_GROUP_CHAT_ID,
                member_limit=1,
            )
            await context.bot.send_message(
                chat_id=applicant_chat_id,
                text=msg.AE_PAYMENT_CONFIRMED.format(link=invite.invite_link),
                parse_mode="HTML",
            )
        except Exception:
            logger.exception("Failed to create invite or notify AE applicant chat_id=%d", applicant_chat_id)
        await query.edit_message_caption(
            caption=f"{caption}\n\n{msg.AE_PAYMENT_REVIEWER_CONFIRMED}",
            reply_markup=None,
        )
    else:
        await db.ae_set_status_by_chat_id(applicant_chat_id, "payment_rejected")
        await db.set_flow(applicant_chat_id, "ae_payment")
        await db.set_status(applicant_chat_id, "ae_payment_step_screenshot")
        try:
            await context.bot.send_message(
                chat_id=applicant_chat_id,
                text=msg.AE_PAYMENT_REJECTED,
                reply_markup=_back_keyboard(),
            )
        except Exception:
            logger.exception("Failed to notify AE applicant chat_id=%d", applicant_chat_id)
        await query.edit_message_caption(
            caption=f"{caption}\n\n{msg.AE_PAYMENT_REVIEWER_REJECTED}",
            reply_markup=None,
        )


async def _ae_payment_confirm_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    await _ae_payment_decision_callback(update, context, "confirmed")


async def _ae_payment_reject_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    await _ae_payment_decision_callback(update, context, "rejected")


async def _ae_set_payment_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if update.effective_user.id != PERSON_X_CHAT_ID:
        return
    reply = update.message.reply_to_message
    if not reply:
        await update.message.reply_text(msg.AE_SET_PAYMENT_USAGE)
        return
    await db.set_setting("ae_payment_post_chat_id", str(reply.chat.id))
    await db.set_setting("ae_payment_post_message_id", str(reply.message_id))
    await update.message.reply_text(msg.AE_SET_PAYMENT_SUCCESS)


# Tables backing the features being retired — exported by /export_all, dropped by /retire_features.


# ---------------------------------------------------------------------------
# SAT Program Enrollment — student flow
# ---------------------------------------------------------------------------

async def _handle_sat_enroll(
    update: Update, chat_id: int, context: ContextTypes.DEFAULT_TYPE
) -> None:
    await update.message.reply_text(
        msg.SAT_ENROLL_INFO,
        parse_mode="HTML",
    )
    _sat_enroll_state[chat_id] = {}
    await db.set_flow(chat_id, "sat_enroll")
    await db.set_status(chat_id, "sat_enroll_step_format")
    await update.message.reply_text(msg.SAT_ENROLL_ASK_FORMAT, reply_markup=_sat_format_keyboard())


async def _sat_enroll_inline_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    # Inline "Enroll at SAT Program" button (e.g. from /broadcastkeyboard) —
    # starts the same SAT enrollment flow.
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id

    await context.bot.send_message(
        chat_id=chat_id,
        text=msg.SAT_ENROLL_INFO,
        parse_mode="HTML",
    )
    _sat_enroll_state[chat_id] = {}
    await db.set_flow(chat_id, "sat_enroll")
    await db.set_status(chat_id, "sat_enroll_step_format")
    await context.bot.send_message(
        chat_id=chat_id,
        text=msg.SAT_ENROLL_ASK_FORMAT,
        reply_markup=_sat_format_keyboard(),
    )


async def _handle_sat_enroll_step(
    update: Update, chat_id: int, text: str, context: ContextTypes.DEFAULT_TYPE
) -> None:
    user = await db.get_user(chat_id)
    status = user.get("status") if user else None

    if status == "sat_enroll_step_format":
        if text not in (msg.BTN_SAT_ONLINE, msg.BTN_SAT_OFFLINE):
            await update.message.reply_text(msg.SAT_ENROLL_ASK_FORMAT, reply_markup=_sat_format_keyboard())
            return
        _sat_enroll_state.setdefault(chat_id, {})["format_type"] = text.strip()
        await db.set_status(chat_id, "sat_enroll_step_name")
        await update.message.reply_text(msg.SAT_ENROLL_ASK_NAME, reply_markup=_back_keyboard())

    elif status == "sat_enroll_step_name":
        if not text.strip():
            await update.message.reply_text(msg.SAT_ENROLL_ASK_NAME, reply_markup=_back_keyboard())
            return
        _sat_enroll_state.setdefault(chat_id, {})["full_name"] = text.strip()
        await db.set_status(chat_id, "sat_enroll_step_history")
        await update.message.reply_text(msg.SAT_ENROLL_ASK_HISTORY, reply_markup=_back_keyboard())

    elif status == "sat_enroll_step_history":
        _sat_enroll_state.setdefault(chat_id, {})["sat_history"] = text.strip()
        await db.set_status(chat_id, "sat_enroll_step_date")
        await update.message.reply_text(msg.SAT_ENROLL_ASK_DATE, reply_markup=_back_keyboard())

    elif status == "sat_enroll_step_date":
        state = _sat_enroll_state.pop(chat_id, {})
        format_type = state.get("format_type", "")
        full_name = state.get("full_name", "")
        sat_history = state.get("sat_history", "")
        test_date = text.strip()

        u = await db.get_user(chat_id)
        first_name = u["first_name"] if u else "Unknown"
        username = u["username"] if u else None

        await db.sat_enroll_save(chat_id, username, first_name, full_name, sat_history, test_date)
        await db.set_flow(chat_id, None)
        await db.set_status(chat_id, None)
        await update.message.reply_text(msg.SAT_ENROLL_SUBMITTED, reply_markup=_main_keyboard())

        username_part = f" (@{username})" if username else ""
        expert_text = msg.SAT_ENROLL_EXPERT_ENTRY.format(
            first_name=first_name,
            username_part=username_part,
            chat_id=chat_id,
            format_type=format_type,
            full_name=full_name,
            sat_history=sat_history,
            test_date=test_date,
        )
        for expert_id in SAT_MAN_CHAT_ID:
            try:
                await context.bot.send_message(
                    chat_id=expert_id,
                    text=expert_text,
                    parse_mode="HTML",
                )
            except Exception:
                logger.exception("Failed to notify SAT expert %d for enrollment", expert_id)


# ---------------------------------------------------------------------------
# Economics Olympiad Prep — registration flow
# ---------------------------------------------------------------------------

async def _econ_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Inline "Join now!" button (from /broadcastkeyboard) — starts registration.
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_user.id

    _econ_state[chat_id] = {"courses": set()}
    await db.set_flow(chat_id, "econ")
    await db.set_status(chat_id, "econ_step_name")
    await context.bot.send_message(
        chat_id=chat_id,
        text=msg.ECON_ASK_NAME,
        reply_markup=_back_keyboard(),
    )


async def _handle_econ_step(
    update: Update, chat_id: int, text: str, context: ContextTypes.DEFAULT_TYPE
) -> None:
    user = await db.get_user(chat_id)
    status = user.get("status") if user else None

    if status == "econ_step_name":
        if not text.strip():
            await update.message.reply_text(msg.ECON_ASK_NAME, reply_markup=_back_keyboard())
            return
        _econ_state.setdefault(chat_id, {"courses": set()})["full_name"] = text.strip()
        await db.set_status(chat_id, "econ_step_courses")
        await update.message.reply_text(
            msg.ECON_ASK_COURSES,
            reply_markup=_econ_courses_keyboard(_econ_state[chat_id]["courses"]),
        )

    elif status == "econ_step_courses":
        # User is expected to tap inline buttons here — re-prompt on stray text.
        await update.message.reply_text(
            msg.ECON_ASK_COURSES,
            reply_markup=_econ_courses_keyboard(
                _econ_state.get(chat_id, {}).get("courses", set())
            ),
        )


async def _econ_course_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_user.id

    state = _econ_state.setdefault(chat_id, {"courses": set()})
    selected: set[str] = state.setdefault("courses", set())
    key = query.data[len("econ_course:"):]
    if key not in _ECON_COURSES:
        return
    if key in selected:
        selected.discard(key)
    else:
        selected.add(key)
    try:
        await query.edit_message_reply_markup(reply_markup=_econ_courses_keyboard(selected))
    except Exception:
        # Benign if the markup is unchanged or the message is too old.
        pass


async def _econ_done_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_user.id

    state = _econ_state.get(chat_id, {})
    selected: set[str] = state.get("courses", set())
    if not selected:
        await context.bot.send_message(chat_id=chat_id, text=msg.ECON_NO_COURSES)
        return

    _econ_state.pop(chat_id, None)
    full_name = state.get("full_name", "")
    # Preserve the fixed course order for a stable, readable record.
    course_labels = [label for key, label in _ECON_COURSES.items() if key in selected]
    courses = ", ".join(course_labels)

    u = await db.get_user(chat_id)
    first_name = u["first_name"] if u else "Unknown"
    username = u["username"] if u else None

    await db.econ_enroll_save(chat_id, username, first_name, full_name, courses)
    await db.set_flow(chat_id, None)
    await db.set_status(chat_id, None)

    # Freeze the picker so it can't be re-tapped, then confirm.
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass
    await context.bot.send_message(
        chat_id=chat_id,
        text=msg.ECON_SUBMITTED,
        reply_markup=_main_keyboard(),
    )

    username_part = f" (@{username})" if username else ""
    notify_text = msg.ECON_EXPERT_ENTRY.format(
        first_name=first_name,
        username_part=username_part,
        chat_id=chat_id,
        full_name=full_name,
        courses=courses,
    )
    for notify_id in _ECON_NOTIFY_IDS:
        try:
            await context.bot.send_message(
                chat_id=notify_id,
                text=notify_text,
                parse_mode="HTML",
            )
        except Exception:
            logger.exception("Failed to notify %d of Olympiad Prep registration", notify_id)


async def _econ_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id not in _ECON_NOTIFY_IDS:
        return
    rows = await db.econ_enroll_get_all()
    if not rows:
        await update.message.reply_text("No Olympiad Prep registrations yet.")
        return
    lines = [f"\U0001f3c6 <b>Olympiad Prep registrations ({len(rows)})</b>", ""]
    for r in rows:
        username_part = f" (@{r['username']})" if r.get("username") else ""
        lines.append(
            f"• <a href=\"tg://user?id={r['chat_id']}\">{r['full_name']}</a>"
            f"{username_part} — {r['courses']}"
        )
    await update.message.reply_text(
        "\n".join(lines), parse_mode="HTML", disable_web_page_preview=True
    )


# ---------------------------------------------------------------------------
# Merch shop — catalog album + order flow (name → delivery → payment QR)
# ---------------------------------------------------------------------------

_MERCH_PHOTO_DIR = Path(__file__).resolve().parent / "assets" / "merch"

# Coming-soon gate. True = shop is live for everyone. False = only /santix
# bypass users see it (everyone else gets MERCH_COMING_SOON). Gated in
# _merch_begin, so both the menu button and the merch_open broadcast button
# are covered.
MERCH_LIVE = True

# Accumulates merch order answers per chat_id
# ({"item": str, "full_name": str, "delivery": str, "phone": str, "address": str}).
_merch_state: dict[int, dict] = {}

# True while PERSON_X is expected to send the Payme QR photo (/set_merch_qr).
_merch_qr_state: dict[str, bool] = {"waiting": False}


def _merch_item(key: str) -> tuple[str, int]:
    for k, label, price in msg.MERCH_ITEMS:
        if k == key:
            return label, price
    return key or "Unknown item", 0


def _merch_items_keyboard(cart: dict[str, int]) -> InlineKeyboardMarkup:
    """Item picker. Items already in the cart show a checkmark and their count;
    tapping any item (re-)asks for its quantity. Checkout starts the order form."""
    rows = [
        [InlineKeyboardButton(
            f"✅ {label} ×{cart[key]}" if key in cart else label,
            callback_data=f"merch_buy:{key}",
        )]
        for key, label, _ in msg.MERCH_ITEMS
    ]
    rows.append([InlineKeyboardButton(msg.BTN_MERCH_CHECKOUT, callback_data="merch_checkout")])
    return InlineKeyboardMarkup(rows)


def _merch_qty_keyboard(key: str, in_cart: bool) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(str(n), callback_data=f"merch_qty:{key}:{n}") for n in range(1, 6)],
        [InlineKeyboardButton(str(n), callback_data=f"merch_qty:{key}:{n}") for n in range(6, 11)],
    ]
    last_row = [InlineKeyboardButton(msg.BTN_MERCH_QTY_BACK, callback_data="merch_qty_back")]
    if in_cart:
        last_row.append(InlineKeyboardButton(msg.BTN_MERCH_REMOVE, callback_data=f"merch_qty:{key}:0"))
    rows.append(last_row)
    return InlineKeyboardMarkup(rows)


def _merch_cart(chat_id: int) -> dict[str, int]:
    return _merch_state.setdefault(chat_id, {}).setdefault("cart", {})


def _merch_cart_lines(cart: dict[str, int]) -> tuple[str, int]:
    """Renders the cart as MERCH_CART_LINE rows (in catalog order) and returns
    them with the total."""
    lines: list[str] = []
    total = 0
    for key, label, price in msg.MERCH_ITEMS:
        qty = cart.get(key)
        if not qty:
            continue
        line_total = price * qty
        total += line_total
        lines.append(msg.MERCH_CART_LINE.format(label=label, qty=qty, line_total=f"{line_total:,}"))
    return "\n".join(lines), total


def _merch_picker_text(cart: dict[str, int]) -> str:
    text = msg.MERCH_CHOOSE_ITEM
    if cart:
        lines, total = _merch_cart_lines(cart)
        text += msg.MERCH_CART_SUMMARY.format(lines=lines, total=f"{total:,}")
    return text


def _merch_delivery_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[msg.BTN_MERCH_PICKUP], [msg.BTN_MERCH_DELIVERY], [msg.BTN_BACK]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def _merch_phone_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton(msg.BTN_MERCH_SHARE_PHONE, request_contact=True)], [msg.BTN_BACK]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


async def _merch_begin(bot, chat_id: int) -> None:
    """Send the catalog (photo album captioned with the price list) and the
    item picker that starts an order."""
    if not MERCH_LIVE and chat_id not in _bypass_users:
        await bot.send_message(chat_id=chat_id, text=msg.MERCH_COMING_SOON)
        return
    caption = msg.MERCH_CATALOG_CAPTION.format(
        items="\n".join(
            msg.MERCH_CATALOG_ITEM_LINE.format(label=label, price=f"{price:,}")
            for _, label, price in msg.MERCH_ITEMS
        )
    )
    await _merch_send_catalog_photos(bot, chat_id, caption)
    cart = _merch_cart(chat_id)
    await bot.send_message(
        chat_id=chat_id,
        text=_merch_picker_text(cart),
        parse_mode="HTML",
        reply_markup=_merch_items_keyboard(cart),
    )


async def _merch_send_catalog_photos(bot, chat_id: int, caption: str) -> None:
    """Send the product photos as one album. Uploaded file_ids are cached in
    bot_settings so later catalog views don't re-upload ~1MB of photos; a stale
    cache (e.g. after a token change) is cleared and the send falls back to a
    text-only catalog."""
    cached = None
    try:
        cached = await db.get_setting("merch_catalog_file_ids")
        if cached:
            photos = json.loads(cached)
        else:
            # Items without a photo file (currently the pen) stay in the price
            # list and item picker — they just don't appear in the album.
            photos = [
                (_MERCH_PHOTO_DIR / f"{key}.jpg").read_bytes()
                for key, _, _ in msg.MERCH_ITEMS
                if (_MERCH_PHOTO_DIR / f"{key}.jpg").exists()
            ]
        if not photos:
            raise RuntimeError("no merch catalog photos available")
        media = [
            InputMediaPhoto(p, caption=caption if i == 0 else None, parse_mode="HTML")
            for i, p in enumerate(photos)
        ]
        sent = await bot.send_media_group(chat_id=chat_id, media=media)
        if not cached:
            await db.set_setting(
                "merch_catalog_file_ids",
                json.dumps([m.photo[-1].file_id for m in sent]),
            )
    except Exception:
        logger.exception("Merch catalog album failed for chat_id=%d; sending text catalog", chat_id)
        if cached:
            await db.set_setting("merch_catalog_file_ids", "")
        await bot.send_message(chat_id=chat_id, text=caption, parse_mode="HTML")


async def _merch_open_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Inline "Browse the merch" button under the /broadcastkeyboard
    # announcement — sends the same catalog as the menu button.
    query = update.callback_query
    await query.answer()
    await _merch_begin(context.bot, update.effective_chat.id)


async def _merch_buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Item button in the picker — morph the picker into a quantity prompt.
    # Also gated so pickers sent before the coming-soon gate stay inert.
    query = update.callback_query
    if not MERCH_LIVE and update.effective_chat.id not in _bypass_users:
        await query.answer(msg.MERCH_COMING_SOON, show_alert=True)
        return
    await query.answer()
    key = query.data.split(":", 1)[1]
    if not any(k == key for k, _, _ in msg.MERCH_ITEMS):
        return
    chat_id = update.effective_chat.id
    label, price = _merch_item(key)
    try:
        await query.edit_message_text(
            msg.MERCH_QTY_PROMPT.format(label=label, price=f"{price:,}"),
            parse_mode="HTML",
            reply_markup=_merch_qty_keyboard(key, key in _merch_cart(chat_id)),
        )
    except TelegramError:
        pass


async def _merch_show_picker(query, chat_id: int) -> None:
    """Morph the callback's message back into the item picker + cart summary."""
    cart = _merch_cart(chat_id)
    try:
        await query.edit_message_text(
            _merch_picker_text(cart),
            parse_mode="HTML",
            reply_markup=_merch_items_keyboard(cart),
        )
    except TelegramError:
        pass


async def _merch_qty_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Quantity choice for an item — 0 removes it from the cart.
    query = update.callback_query
    await query.answer()
    _, key, qty_str = query.data.split(":")
    if not any(k == key for k, _, _ in msg.MERCH_ITEMS):
        return
    chat_id = update.effective_chat.id
    cart = _merch_cart(chat_id)
    qty = int(qty_str)
    if qty <= 0:
        cart.pop(key, None)
    else:
        cart[key] = min(qty, 10)
    await _merch_show_picker(query, chat_id)


async def _merch_qty_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await _merch_show_picker(query, update.effective_chat.id)


async def _merch_checkout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Checkout — freeze the picker and start the order form for the whole cart.
    query = update.callback_query
    chat_id = update.effective_chat.id
    if not MERCH_LIVE and chat_id not in _bypass_users:
        await query.answer(msg.MERCH_COMING_SOON, show_alert=True)
        return
    cart = _merch_cart(chat_id)
    if not cart:
        await query.answer(msg.MERCH_CART_EMPTY, show_alert=True)
        return
    await query.answer()
    try:
        await query.edit_message_text(
            _merch_picker_text(cart), parse_mode="HTML", reply_markup=None
        )
    except TelegramError:
        pass
    await db.set_flow(chat_id, "merch")
    await db.set_status(chat_id, "merch_step_name")
    await context.bot.send_message(
        chat_id=chat_id, text=msg.MERCH_ASK_NAME, reply_markup=_back_keyboard()
    )


async def _merch_state_valid(bot, chat_id: int) -> bool:
    """The in-memory order state dies on restart while flow/status persist in
    the DB — when they disagree, restart the order cleanly from the catalog."""
    if _merch_state.get(chat_id, {}).get("cart"):
        return True
    _merch_state.pop(chat_id, None)
    await db.set_flow(chat_id, None)
    await db.set_status(chat_id, None)
    await _merch_begin(bot, chat_id)
    return False


async def _handle_merch_step(
    update: Update, chat_id: int, text: str, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not await _merch_state_valid(context.bot, chat_id):
        return
    user = await db.get_user(chat_id)
    status = user.get("status") if user else None

    if status == "merch_step_name":
        if not text.strip():
            await update.message.reply_text(msg.MERCH_ASK_NAME, reply_markup=_back_keyboard())
            return
        _merch_state.setdefault(chat_id, {})["full_name"] = text.strip()
        await db.set_status(chat_id, "merch_step_delivery")
        await update.message.reply_text(
            msg.MERCH_ASK_DELIVERY, reply_markup=_merch_delivery_keyboard()
        )

    elif status == "merch_step_delivery":
        if text == msg.BTN_MERCH_PICKUP:
            _merch_state.setdefault(chat_id, {})["delivery"] = "pickup"
            await _merch_finalize(context.bot, chat_id)
        elif text == msg.BTN_MERCH_DELIVERY:
            _merch_state.setdefault(chat_id, {})["delivery"] = "delivery"
            await db.set_status(chat_id, "merch_step_phone")
            await update.message.reply_text(
                msg.MERCH_ASK_PHONE, reply_markup=_merch_phone_keyboard()
            )
        else:
            await update.message.reply_text(
                msg.MERCH_ASK_DELIVERY, reply_markup=_merch_delivery_keyboard()
            )

    elif status == "merch_step_phone":
        await _handle_merch_phone(update, chat_id, text)

    elif status == "merch_step_address":
        if not text.strip():
            await update.message.reply_text(msg.MERCH_ASK_ADDRESS, reply_markup=_back_keyboard())
            return
        _merch_state.setdefault(chat_id, {})["address"] = text.strip()
        await _merch_finalize(context.bot, chat_id)


async def _handle_merch_phone(update: Update, chat_id: int, phone: str) -> None:
    # Accepts a typed number or a shared contact's phone_number.
    if sum(c.isdigit() for c in phone) < 7:
        await update.message.reply_text(
            msg.MERCH_PHONE_INVALID, reply_markup=_merch_phone_keyboard()
        )
        return
    _merch_state.setdefault(chat_id, {})["phone"] = phone.strip()
    await db.set_status(chat_id, "merch_step_address")
    await update.message.reply_text(msg.MERCH_ASK_ADDRESS, reply_markup=_back_keyboard())


async def _merch_finalize(bot, chat_id: int) -> None:
    """Close the order: save it, show the payment step (Payme QR), and forward
    the entry to PERSON_X."""
    state = _merch_state.pop(chat_id, {})
    await db.set_flow(chat_id, None)
    await db.set_status(chat_id, None)

    cart = state.get("cart", {})
    lines, total = _merch_cart_lines(cart)
    item_summary = ", ".join(
        f"{label} ×{cart[key]}" for key, label, _ in msg.MERCH_ITEMS if cart.get(key)
    )
    user = await db.get_user(chat_id)
    first_name = user["first_name"] if user else "Unknown"
    username = user["username"] if user else None
    full_name = state.get("full_name", "")
    delivery = state.get("delivery", "pickup")
    phone = state.get("phone")
    address = state.get("address")

    # One row per checkout: `item` is the cart summary, `price` the total.
    await db.merch_order_save(
        chat_id, username, first_name, full_name, item_summary, total, delivery, phone, address
    )

    delivery_details = ""
    if delivery == "delivery":
        delivery_details = msg.MERCH_ORDER_DELIVERY_DETAILS.format(
            phone=html.escape(phone or "—"), address=html.escape(address or "—")
        )
    summary = msg.MERCH_ORDER_SUMMARY.format(
        lines=lines,
        total=f"{total:,}",
        full_name=html.escape(full_name),
        delivery=msg.BTN_MERCH_PICKUP if delivery == "pickup" else msg.BTN_MERCH_DELIVERY,
        delivery_details=delivery_details,
    )

    # Payment — the closing step. The QR is set via /set_merch_qr; until then
    # the order still lands with PERSON_X and the user is told details follow.
    qr_file_id = await db.get_setting("merch_payme_qr_file_id")
    if qr_file_id:
        await bot.send_photo(
            chat_id=chat_id,
            photo=qr_file_id,
            caption=msg.MERCH_PAYMENT_QR.format(summary=summary),
            parse_mode="HTML",
            reply_markup=_main_keyboard(),
        )
    else:
        await bot.send_message(
            chat_id=chat_id,
            text=msg.MERCH_PAYMENT_PENDING.format(summary=summary),
            parse_mode="HTML",
            reply_markup=_main_keyboard(),
        )

    username_part = f" (@{username})" if username else ""
    order_text = msg.MERCH_ORDER_FORWARD.format(
        chat_id=chat_id,
        first_name=html.escape(first_name),
        username_part=username_part,
        summary=summary,
    )
    try:
        await bot.send_message(chat_id=PERSON_X_CHAT_ID, text=order_text, parse_mode="HTML")
    except Exception:
        logger.exception("Failed to forward merch order to PERSON_X for chat_id=%d", chat_id)


async def _set_merch_qr_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != PERSON_X_CHAT_ID:
        return
    _merch_qr_state["waiting"] = True
    await update.message.reply_text(msg.MERCH_QR_PROMPT)


async def _merch_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != PERSON_X_CHAT_ID:
        return
    rows = await db.merch_orders_get_all()
    if not rows:
        await update.message.reply_text(msg.MERCH_LIST_EMPTY)
        return
    lines = [f"🛍 <b>Merch orders ({len(rows)})</b>", ""]
    for r in rows:
        username_part = f" (@{r['username']})" if r.get("username") else ""
        if r["delivery"] == "delivery":
            where = f"🚚 {html.escape(r['phone'] or '—')}, {html.escape(r['address'] or '—')}"
        else:
            where = "🏢 pickup"
        lines.append(
            f"• <a href=\"tg://user?id={r['chat_id']}\">{html.escape(r['full_name'])}</a>"
            f"{username_part} — {r['item']} ({r['price']:,} UZS) — {where}"
        )
    # Telegram caps a message at 4096 chars — send the list in chunks of whole
    # lines so a long order list never overflows a single message.
    chunk: list[str] = []
    length = 0
    for line in lines:
        if chunk and length + len(line) + 1 > 3900:
            await update.message.reply_text(
                "\n".join(chunk), parse_mode="HTML", disable_web_page_preview=True
            )
            chunk, length = [], 0
        chunk.append(line)
        length += len(line) + 1
    if chunk:
        await update.message.reply_text(
            "\n".join(chunk), parse_mode="HTML", disable_web_page_preview=True
        )


# ---------------------------------------------------------------------------
# SAT Freshman consultations — subscribe to both channels, then book a slot
# ---------------------------------------------------------------------------

# Coming-soon gate. True = giveaway is live for everyone. False = only /santix
# bypass users see it (everyone else gets SATC_COMING_SOON). Gated in
# _satc_begin and both inline callbacks, so the menu button, the satc_open
# broadcast button, and old check-again buttons are all covered.
SATC_LIVE = True

# The bot must be an admin in both channels for the membership check to work.
# @satfreshman goes in by handle — get_chat_member takes either, so swap in its
# numeric ID if the channel ever goes private.
SATC_REQUIRED_IDS = ["@satfreshman", -1001481432083]
SATC_REQUIRED_HANDLES = ["@satfreshman", "@freshmanblog"]

SATC_BOOKING_URL = "https://calendar.app.google/5UA6X1zCVnBnypQM7"


def _satc_links_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(msg.BTN_SATC_BOOK, url=SATC_BOOKING_URL)]]
    )


async def _satc_is_member(bot, channel_id: int | str, chat_id: int) -> bool:
    """True if chat_id is a member of channel_id. Fails open on API error."""
    try:
        member = await bot.get_chat_member(channel_id, chat_id)
        return member.status in _MEMBER_STATUSES
    except TelegramError:
        logger.warning("Cannot check SAT consult membership in %s. Failing open.", channel_id)
        return True


async def _satc_get_missing(bot, chat_id: int) -> list[str]:
    results = await asyncio.gather(
        *(_satc_is_member(bot, cid, chat_id) for cid in SATC_REQUIRED_IDS)
    )
    return [h for h, ok in zip(SATC_REQUIRED_HANDLES, results) if not ok]


async def _satc_record_claim(user, chat_id: int) -> None:
    """Log who passed the gate and got the booking link (first claim keeps its
    timestamp). Falls back to the users table when no Telegram user object is
    at hand (the menu-button path)."""
    if user is not None:
        first_name, username = user.first_name, user.username
    else:
        row = await db.get_user(chat_id)
        first_name = (row or {}).get("first_name")
        username = (row or {}).get("username")
    await db.satc_add_claim(chat_id, first_name, username)


async def _satc_send_gate(bot, chat_id: int, user=None) -> None:
    missing = await _satc_get_missing(bot, chat_id)
    if missing:
        channel_list = "\n".join(f"• {h}" for h in missing)
        await bot.send_message(
            chat_id=chat_id,
            text=msg.SATC_MUST_JOIN.format(channel_list=channel_list),
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(msg.BTN_SATC_CHECK, callback_data="satc_check")]]
            ),
        )
        return
    await _satc_record_claim(user, chat_id)
    await bot.send_message(
        chat_id=chat_id,
        text=msg.SATC_ACCESS_GRANTED,
        reply_markup=_satc_links_keyboard(),
    )


async def _satc_begin(bot, chat_id: int) -> None:
    """Send the giveaway promo, then either the must-join gate or the link."""
    if not SATC_LIVE and chat_id not in _bypass_users:
        await bot.send_message(chat_id=chat_id, text=msg.SATC_COMING_SOON)
        return
    await bot.send_message(
        chat_id=chat_id,
        text=msg.SATC_INTRO,
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
    await _satc_send_gate(bot, chat_id)


async def _satc_open_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Inline button under the /broadcastkeyboard announcement — the promo is
    # already on screen, so go straight to the subscription gate.
    query = update.callback_query
    if not SATC_LIVE and update.effective_user.id not in _bypass_users:
        await query.answer(msg.SATC_COMING_SOON, show_alert=True)
        return
    await _safe_answer(query)
    await _satc_send_gate(context.bot, update.effective_user.id, update.effective_user)


async def _satc_check_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not SATC_LIVE and update.effective_user.id not in _bypass_users:
        await query.answer(msg.SATC_COMING_SOON, show_alert=True)
        return
    await _safe_answer(query)
    chat_id = update.effective_user.id
    missing = await _satc_get_missing(context.bot, chat_id)
    if missing:
        channel_list = "\n".join(f"• {h}" for h in missing)
        try:
            await query.edit_message_text(
                msg.SATC_MUST_JOIN.format(channel_list=channel_list),
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton(msg.BTN_SATC_CHECK, callback_data="satc_check")]]
                ),
            )
        except TelegramError as e:
            if "not modified" not in str(e).lower():
                raise
        return
    await _satc_record_claim(update.effective_user, chat_id)
    try:
        await query.edit_message_text(
            msg.SATC_ACCESS_GRANTED,
            reply_markup=_satc_links_keyboard(),
        )
    except TelegramError as e:
        if "not modified" not in str(e).lower():
            raise


async def _satc_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != PERSON_X_CHAT_ID:
        return
    claims = await db.satc_get_all_claims()
    if not claims:
        await update.message.reply_text(msg.SATC_LIST_EMPTY)
        return
    lines = [
        f"{i + 1}. {c['first_name'] or '—'}" + (f" (@{c['username']})" if c.get("username") else "")
        for i, c in enumerate(claims)
    ]
    current = f"SAT consultation claims: {len(claims)}\n\n"
    for line in lines:
        if len(current) + len(line) + 1 > 4096:
            await update.message.reply_text(current)
            current = ""
        current += line + "\n"
    if current:
        await update.message.reply_text(current)


async def _consult_retired_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # The retired Freshman Global consultations announcement was broadcast, so
    # its inline buttons are still out there. Answer instead of spinning.
    await update.callback_query.answer(msg.CONSULT_ENDED, show_alert=True)


# ---------------------------------------------------------------------------
# Consultation Giveaway with Valera — subscribe to both channels to enter the
# draw; Person X picks the winner with /roll + /reroll
# ---------------------------------------------------------------------------

# Coming-soon gate. True = giveaway is live for everyone. False = only /santix
# bypass users see it (everyone else gets VG_COMING_SOON). Gated in _vg_begin
# and both inline callbacks, so the menu button and old check-again buttons
# are all covered.
VG_LIVE = True

# The bot must be an admin in both channels for the membership check to work.
VG_REQUIRED_IDS = [-1001188644050, -1001481432083]
VG_REQUIRED_HANDLES = ["@valeranotes", "@freshmanblog"]

# Tracks the last rolled participant so /reroll can exclude them.
_roll_state: dict = {"last_id": None}


async def _vg_is_member(bot, channel_id: int | str, chat_id: int) -> bool:
    """True if chat_id is a member of channel_id. Fails open on API error."""
    try:
        member = await bot.get_chat_member(channel_id, chat_id)
        return member.status in _MEMBER_STATUSES
    except TelegramError:
        logger.warning("Cannot check giveaway membership in %s. Failing open.", channel_id)
        return True


async def _vg_get_missing(bot, chat_id: int) -> list[str]:
    results = await asyncio.gather(
        *(_vg_is_member(bot, cid, chat_id) for cid in VG_REQUIRED_IDS)
    )
    return [h for h, ok in zip(VG_REQUIRED_HANDLES, results) if not ok]


async def _vg_begin(bot, chat_id: int) -> None:
    """Send the giveaway promo, then the join prompt with the entry button."""
    if not VG_LIVE and chat_id not in _bypass_users:
        await bot.send_message(chat_id=chat_id, text=msg.VG_COMING_SOON)
        return
    await bot.send_message(
        chat_id=chat_id,
        text=msg.VG_INTRO,
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
    # The join button lives on its own message so the gate/confirmation edits
    # don't wipe the promo off the screen.
    await bot.send_message(
        chat_id=chat_id,
        text=msg.VG_JOIN_PROMPT,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton(msg.BTN_VG_JOIN, callback_data="vg_join")]]
        ),
    )


async def _vg_edit(query, *args, **kwargs) -> None:
    try:
        await query.edit_message_text(*args, **kwargs)
    except TelegramError as e:
        if "not modified" not in str(e).lower():
            raise


async def _vg_process_entry(user, context, send) -> None:
    """Verify the subscriptions, then enter the user into the draw (or re-gate
    them if they unsubscribed). `send` is an async callable(text, reply_markup)
    — an edit for taps on the join prompt, a fresh message for taps on the
    broadcast announcement (so the promo stays on screen)."""
    missing = await _vg_get_missing(context.bot, user.id)
    if missing:
        # Left a channel after joining? Drop them from the draw until they're
        # subscribed again.
        await db.vg_remove_participant(user.id)
        channel_list = "\n".join(f"• {h}" for h in missing)
        await send(
            msg.VG_MUST_JOIN.format(channel_list=channel_list),
            InlineKeyboardMarkup(
                [[InlineKeyboardButton(msg.BTN_VG_CHECK, callback_data="vg_check")]]
            ),
        )
        return

    if await db.vg_get_participant(user.id):
        await send(msg.VG_ALREADY_PARTICIPATING, None)
        return
    await db.vg_add_participant(user.id, user.first_name, user.username)
    await send(msg.VG_NOW_PARTICIPATING, None)


async def _vg_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Shared by vg_join and vg_check — the button lives on the join prompt
    message, so the outcome replaces it in place."""
    query = update.callback_query
    user = update.effective_user
    if not VG_LIVE and user.id not in _bypass_users:
        await query.answer(msg.VG_COMING_SOON, show_alert=True)
        return
    await _safe_answer(query)

    async def send(text, reply_markup):
        await _vg_edit(query, text, reply_markup=reply_markup)

    await _vg_process_entry(user, context, send)


async def _vg_open_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Inline button under the /broadcastkeyboard announcement — reply with a
    fresh message instead of editing the promo away."""
    query = update.callback_query
    user = update.effective_user
    if not VG_LIVE and user.id not in _bypass_users:
        await query.answer(msg.VG_COMING_SOON, show_alert=True)
        return
    await _safe_answer(query)

    async def send(text, reply_markup):
        await context.bot.send_message(
            chat_id=user.id, text=text, reply_markup=reply_markup
        )

    await _vg_process_entry(user, context, send)


async def _vg_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != PERSON_X_CHAT_ID:
        return
    participants = await db.vg_get_all_participants()
    if not participants:
        await update.message.reply_text(msg.ROLL_NO_PARTICIPANTS)
        return
    lines = [
        f"{i + 1}. {p['first_name']}" + (f" (@{p['username']})" if p.get("username") else "")
        for i, p in enumerate(participants)
    ]
    current = f"Giveaway participants: {len(participants)}\n\n"
    for line in lines:
        if len(current) + len(line) + 1 > 4096:
            await update.message.reply_text(current)
            current = ""
        current += line + "\n"
    if current:
        await update.message.reply_text(current)


def _roll_format(participant: dict, header: str) -> str:
    username_part = f" (@{participant['username']})" if participant.get("username") else ""
    return header.format(
        chat_id=participant["chat_id"],
        first_name=participant["first_name"],
        username_part=username_part,
    )


def _roll_keyboard(winner_chat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(msg.BTN_CONFIRM_WINNER, callback_data=f"vg_confirm:{winner_chat_id}"),
        InlineKeyboardButton(msg.BTN_REROLL_INLINE, callback_data="vg_reroll"),
    ]])


async def _roll_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != PERSON_X_CHAT_ID:
        return
    participants = await db.vg_get_all_participants()
    if not participants:
        await update.message.reply_text(msg.ROLL_NO_PARTICIPANTS)
        return
    winner = random.choice(participants)
    _roll_state["last_id"] = winner["chat_id"]
    await update.message.reply_text(
        _roll_format(winner, msg.ROLL_RESULT),
        parse_mode="HTML",
        reply_markup=_roll_keyboard(winner["chat_id"]),
    )


async def _reroll_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != PERSON_X_CHAT_ID:
        return
    if _roll_state["last_id"] is None:
        await update.message.reply_text(msg.ROLL_USE_FIRST)
        return
    participants = await db.vg_get_all_participants()
    pool = [p for p in participants if p["chat_id"] != _roll_state["last_id"]]
    if not pool:
        await update.message.reply_text(msg.ROLL_ONLY_ONE)
        return
    winner = random.choice(pool)
    _roll_state["last_id"] = winner["chat_id"]
    await update.message.reply_text(
        _roll_format(winner, msg.REROLL_RESULT),
        parse_mode="HTML",
        reply_markup=_roll_keyboard(winner["chat_id"]),
    )


async def _vg_reroll_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await _safe_answer(query)
    if update.effective_user.id != PERSON_X_CHAT_ID:
        return
    if _roll_state["last_id"] is None:
        await _vg_edit(query, msg.ROLL_USE_FIRST)
        return
    participants = await db.vg_get_all_participants()
    pool = [p for p in participants if p["chat_id"] != _roll_state["last_id"]]
    if not pool:
        await _vg_edit(query, msg.ROLL_ONLY_ONE)
        return
    winner = random.choice(pool)
    _roll_state["last_id"] = winner["chat_id"]
    await _vg_edit(
        query,
        _roll_format(winner, msg.REROLL_RESULT),
        parse_mode="HTML",
        reply_markup=_roll_keyboard(winner["chat_id"]),
    )


async def _vg_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Notify every participant of the outcome — winner text for the winner,
    better-luck text for everyone else. Runs in the background so a big
    participant list doesn't stall the handler."""
    query = update.callback_query
    await _safe_answer(query)
    if update.effective_user.id != PERSON_X_CHAT_ID:
        return
    winner_chat_id = int(query.data.split(":")[1])
    participants = await db.vg_get_all_participants()
    _roll_state["last_id"] = None
    await _vg_edit(query, msg.ROLL_CONFIRMING.format(count=len(participants)))

    async def _run() -> None:
        sent = failed = 0
        # Same batching as /broadcastkeyboard — stay under Telegram's flood
        # limit and keep the connection pool free for live replies.
        batch_size = 20
        batch_pause = 1.5

        async def _send_one(p: dict) -> None:
            nonlocal sent, failed
            text = (
                msg.ROLL_WINNER_NOTIFY
                if p["chat_id"] == winner_chat_id
                else msg.ROLL_LOSER_NOTIFY
            )
            try:
                await context.bot.send_message(chat_id=p["chat_id"], text=text)
                sent += 1
            except Exception as e:
                logger.warning(
                    "Failed to notify giveaway participant chat_id=%d: %s", p["chat_id"], e
                )
                failed += 1

        for start in range(0, len(participants), batch_size):
            await asyncio.gather(*(_send_one(p) for p in participants[start:start + batch_size]))
            await asyncio.sleep(batch_pause)
        await context.bot.send_message(
            chat_id=PERSON_X_CHAT_ID,
            text=msg.ROLL_CONFIRMED.format(sent=sent, failed=failed),
        )

    asyncio.create_task(_run())


# ---------------------------------------------------------------------------
# SAT enrollments — admin list view
# ---------------------------------------------------------------------------

_SAT_LIST_IDS: frozenset[int] = frozenset(
    x for x in (PERSON_X_CHAT_ID, VALERA_CHAT_ID) if x is not None
)


# ---------------------------------------------------------------------------
# Trial AP Lesson — student flow + review
# ---------------------------------------------------------------------------

TAP_GROUP_CHAT_ID = -1003830859397


def _tap_intro_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(msg.BTN_TAP_SCREENSHOT, callback_data="tap_screenshot")]]
    )


async def _handle_trial_ap(
    update: Update, chat_id: int, context: ContextTypes.DEFAULT_TYPE
) -> None:
    entry = await db.tap_get_entry(chat_id)
    if entry and entry["status"] == "confirmed" and entry.get("invite_link"):
        await update.message.reply_text(
            msg.TAP_ALREADY_CONFIRMED.format(link=entry["invite_link"]),
            reply_markup=_main_keyboard(),
        )
        return
    await update.message.reply_text(
        msg.TAP_INTRO, parse_mode="HTML", reply_markup=_tap_intro_markup()
    )


async def _tap_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Inline "Join" button (e.g. from /broadcastkeyboard) — same streamlined intro.
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_user.id

    entry = await db.tap_get_entry(chat_id)
    if entry and entry["status"] == "confirmed" and entry.get("invite_link"):
        await context.bot.send_message(
            chat_id=chat_id,
            text=msg.TAP_ALREADY_CONFIRMED.format(link=entry["invite_link"]),
            reply_markup=_main_keyboard(),
        )
        return

    await context.bot.send_message(
        chat_id=chat_id,
        text=msg.TAP_INTRO,
        parse_mode="HTML",
        reply_markup=_tap_intro_markup(),
    )


async def _tap_screenshot_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_user.id

    entry = await db.tap_get_entry(chat_id)
    if entry and entry["status"] == "confirmed" and entry.get("invite_link"):
        await context.bot.send_message(
            chat_id=chat_id,
            text=msg.TAP_ALREADY_CONFIRMED.format(link=entry["invite_link"]),
            reply_markup=_main_keyboard(),
        )
        return

    await context.bot.send_message(
        chat_id=chat_id,
        text=msg.TAP_SCREENSHOT_PROMPT,
        reply_markup=_back_keyboard(),
    )
    await db.set_flow(chat_id, "tap")
    await db.set_status(chat_id, "tap_step_screenshot")


async def _handle_tap_screenshot(
    update: Update,
    chat_id: int,
    file_id: str,
    file_type: str,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    user = await db.get_user(chat_id)
    first_name = user["first_name"] if user else "Unknown"
    username = user["username"] if user else None

    await db.tap_save_entry(chat_id, username, first_name, file_id, file_type)
    await db.set_flow(chat_id, None)
    await db.set_status(chat_id, None)
    await update.message.reply_text(msg.TAP_SUBMITTED, reply_markup=_main_keyboard())

    username_part = f" (@{username})" if username else ""
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(msg.BTN_TAP_APPROVE, callback_data=f"tap_approve:{chat_id}"),
        InlineKeyboardButton(msg.BTN_TAP_REJECT, callback_data=f"tap_reject:{chat_id}"),
    ]])
    caption = msg.TAP_REVIEWER_ENTRY.format(first_name=first_name, username_part=username_part)

    reviewers = ADV_PLACEMENT_MAN_CHAT_ID or [PERSON_X_CHAT_ID]
    if not ADV_PLACEMENT_MAN_CHAT_ID:
        logger.warning(
            "ADV_PLACEMENT_MAN_CHAT_ID is empty — routing Trial AP screenshot to PERSON_X fallback."
        )
    for reviewer_id in reviewers:
        try:
            if file_type == "photo":
                sent = await context.bot.send_photo(
                    chat_id=reviewer_id, photo=file_id, caption=caption, reply_markup=keyboard,
                )
            else:
                sent = await context.bot.send_document(
                    chat_id=reviewer_id, document=file_id, caption=caption, reply_markup=keyboard,
                )
            await db.tap_set_entry_reviewer_message(chat_id, sent.message_id)
        except Exception:
            logger.exception("Failed to send Trial AP entry to reviewer chat_id=%d", reviewer_id)


async def _tap_decision_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE, decision: str
) -> None:
    query = update.callback_query
    await query.answer()

    applicant_chat_id = int(query.data.split(":")[1])
    entry = await db.tap_get_entry(applicant_chat_id)

    if not entry or entry["status"] != "pending":
        await query.answer(msg.TAP_REVIEWER_ALREADY_DECIDED, show_alert=True)
        return

    caption = query.message.caption or ""

    if decision == "rejected":
        await db.tap_set_entry_status(applicant_chat_id, "rejected")
        try:
            await context.bot.send_message(chat_id=applicant_chat_id, text=msg.TAP_REJECTED)
        except Exception:
            logger.exception("Failed to notify Trial AP participant chat_id=%d", applicant_chat_id)
        await query.edit_message_caption(
            caption=f"{caption}\n\n{msg.TAP_REVIEWER_REJECTED}", reply_markup=None,
        )
        return

    # Confirmed → issue a one-time invite link to the group.
    try:
        invite = await context.bot.create_chat_invite_link(
            chat_id=TAP_GROUP_CHAT_ID,
            member_limit=1,
        )
    except Exception:
        logger.exception("Failed to create Trial AP invite for chat_id=%d", applicant_chat_id)
        await query.edit_message_caption(
            caption=f"{caption}\n\n{msg.TAP_REVIEWER_LINK_FAILED}", reply_markup=query.message.reply_markup,
        )
        return

    await db.tap_set_entry_status(applicant_chat_id, "confirmed")
    await db.tap_set_entry_link(applicant_chat_id, invite.invite_link)
    try:
        await context.bot.send_message(
            chat_id=applicant_chat_id,
            text=msg.TAP_CONFIRMED.format(link=invite.invite_link),
        )
    except Exception:
        logger.exception("Failed to notify Trial AP participant chat_id=%d", applicant_chat_id)
    await query.edit_message_caption(
        caption=f"{caption}\n\n{msg.TAP_REVIEWER_ACCEPTED}", reply_markup=None,
    )


async def _tap_approve_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _tap_decision_callback(update, context, "confirmed")


async def _tap_reject_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _tap_decision_callback(update, context, "rejected")



async def _ae_remind_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != PERSON_X_CHAT_ID:
        return
    args = context.args
    if not args or args[0] not in ("1", "2", "3"):
        await update.message.reply_text(msg.AE_REMIND_USAGE)
        return
    days = int(args[0])
    text = msg.AE_REMIND_CLOSING.format(days=days, s="" if days == 1 else "s")
    chat_ids = await db.get_all_chat_ids()
    stuck = {u["chat_id"] for u in await db.get_ae_stuck_users()}
    sent = failed = skipped = 0
    for cid in chat_ids:
        if cid in stuck:
            skipped += 1
            continue
        try:
            await context.bot.send_message(
                chat_id=cid,
                text=text,
                reply_markup=_main_keyboard(),
                parse_mode="HTML",
            )
            sent += 1
        except Exception:
            logger.warning("AE remind failed for chat_id=%d", cid)
            failed += 1
        await asyncio.sleep(0.05)
    await update.message.reply_text(
        msg.AE_REMIND_DONE.format(sent=sent, failed=failed, total=len(chat_ids))
        + f" ({skipped} skipped — mid-application)"
    )


async def _ae_payment_remind_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != PERSON_X_CHAT_ID:
        return
    users = await db.ae_get_applications_by_status(["terms_accepted", "payment_rejected"])
    sent = failed = 0
    for u in users:
        try:
            await context.bot.send_message(
                chat_id=u["chat_id"],
                text=msg.AE_PAYMENT_DEADLINE,
                parse_mode="HTML",
            )
            sent += 1
        except Exception:
            logger.warning("AE payment remind failed for chat_id=%d", u["chat_id"])
            failed += 1
        await asyncio.sleep(0.05)
    await update.message.reply_text(
        msg.AE_PAYMENT_DEADLINE_DONE.format(sent=sent, failed=failed, total=len(users))
    )


async def _ae_stuck_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != PERSON_X_CHAT_ID:
        return
    users = await db.get_ae_stuck_users()
    sent = failed = 0
    for u in users:
        try:
            await context.bot.send_message(chat_id=u["chat_id"], text=msg.AE_STUCK_REMINDER)
            sent += 1
        except Exception:
            logger.warning("AE stuck remind failed for chat_id=%d", u["chat_id"])
            failed += 1
        await asyncio.sleep(0.05)
    await update.message.reply_text(
        msg.AE_STUCK_DONE.format(sent=sent, failed=failed, total=len(users))
    )


import random as _random


# ---------------------------------------------------------------------------
# /santix — toggle bypass mode to skip "coming soon" gates for testing
# ---------------------------------------------------------------------------

async def _santix_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if chat_id in _bypass_users:
        _bypass_users.discard(chat_id)
        await update.message.reply_text("🔒 Bypass mode off.")
    else:
        _bypass_users.add(chat_id)
        await update.message.reply_text("🔓 Bypass mode on — coming soon sections are now accessible.")


# ---------------------------------------------------------------------------
# App builder
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# /answered, /unanswered and /skipped — admin question viewer
# ---------------------------------------------------------------------------

_Q_ADMIN_IDS: frozenset[int] = frozenset(
    x for x in (PERSON_X_CHAT_ID, PERSON_Z_CHAT_ID, VALERA_CHAT_ID) if x is not None
)

_Q_PAGE_SIZE = 5

# Short codes used in callback_data to stay under Telegram's 64-byte limit
_Q_PROG_CODES: dict[str, str | None] = {
    "ALL": None,
    "SAT": "SAT Program",
    "ADM": "Admissions Program",
    "FS":  "Full Support Program",
    "MS":  "Master's Support",
    "AP":  "AP Classes",
    "RI":  "Research Institute",
    "IK":  "Imkon",
    "AE":  "Advanced English",
    "GI":  "General Inquiry",
}

_Q_PROG_LABELS: dict[str, str] = {
    "ALL": "All Programs",
    "SAT": "SAT",
    "ADM": "Admissions",
    "FS":  "Full Support",
    "MS":  "Master's",
    "AP":  "AP",
    "RI":  "Research Inst.",
    "IK":  "Imkon",
    "AE":  "Adv. English",
    "GI":  "General Inquiry",
}

# Reverse map: expert chat_id → set of program strings they receive questions for.
_EXPERT_PROGRAMS: dict[int, set[str]] = {}
for _prog, _ids in _PROGRAM_EXPERT.items():
    for _eid in _ids:
        _EXPERT_PROGRAMS.setdefault(_eid, set()).add(_prog)


def _q_allowed_prog_codes(user_id: int) -> set[str] | None:
    """Program codes a user may view in /answered & /unanswered.

    Returns None for full-access admins (all programs, incl. "ALL"), or the set
    of codes a department expert is scoped to. Empty set = no access.
    """
    if user_id in _Q_ADMIN_IDS:
        return None
    programs = _EXPERT_PROGRAMS.get(user_id, set())
    return {code for code, prog in _Q_PROG_CODES.items() if prog and prog in programs}


def _q_can_view(user_id: int) -> bool:
    return user_id in _Q_ADMIN_IDS or bool(_EXPERT_PROGRAMS.get(user_id))


def _q_prog_allowed(user_id: int, prog_code: str) -> bool:
    """Whether a user may query a given program code ("ALL" is admin-only)."""
    allowed = _q_allowed_prog_codes(user_id)
    if allowed is None:
        return True
    return prog_code in allowed


def _q_question_allowed(user_id: int, program: str | None) -> bool:
    """Whether a user may act on a single question belonging to `program`."""
    if user_id in _Q_ADMIN_IDS:
        return True
    return bool(program) and program in _EXPERT_PROGRAMS.get(user_id, set())

_Q_DATE_OPTIONS = [
    ("0",  None, "All time"),
    ("1",  1,    "Today"),
    ("7",  7,    "Last 7 days"),
    ("30", 30,   "Last 30 days"),
]


def _q_program_keyboard(status: str, allowed: set[str] | None = None) -> InlineKeyboardMarkup:
    rows = []
    if allowed is None:
        rows.append([InlineKeyboardButton("All Programs", callback_data=f"qp:{status}:ALL")])
        codes = [code for code in _Q_PROG_CODES if code != "ALL"]
    else:
        codes = [code for code in _Q_PROG_CODES if code != "ALL" and code in allowed]
    prog_btns = [
        InlineKeyboardButton(_Q_PROG_LABELS[code], callback_data=f"qp:{status}:{code}")
        for code in codes
    ]
    for i in range(0, len(prog_btns), 2):
        rows.append(prog_btns[i : i + 2])
    return InlineKeyboardMarkup(rows)


def _q_date_keyboard(status: str, prog_code: str) -> InlineKeyboardMarkup:
    rows = []
    for i in range(0, len(_Q_DATE_OPTIONS), 2):
        row = [
            InlineKeyboardButton(label, callback_data=f"qd:{status}:{prog_code}:{key}:0")
            for key, _, label in _Q_DATE_OPTIONS[i : i + 2]
        ]
        rows.append(row)
    return InlineKeyboardMarkup(rows)


_Q_STATUS_LABELS: dict[str, str] = {
    "answered": "✅ Answered",
    "pending": "⏳ Unanswered",
    "skipped": "⏭ Skipped",
}


def _q_format_entry(q: dict, status: str) -> str:
    date = (q.get("created_at") or "")[:10]
    program = q.get("program") or "—"
    first_name = q.get("first_name") or "Unknown"
    username = q.get("username")
    user_str = f"{first_name} (@{username})" if username else first_name
    question = (q.get("question_text") or "").strip()

    lines = [f"#{q['id']} · {program} · {date}", f"👤 {user_str}", f"❓ {question}"]
    if status == "answered" and q.get("answer_text"):
        lines.append(f"💬 {q['answer_text'].strip()}")
    return "\n".join(lines)


async def _q_edit(query, text: str, markup: InlineKeyboardMarkup | None = None) -> None:
    """edit_message_text that tolerates an unchanged re-render (Telegram 400)."""
    try:
        await query.edit_message_text(text, reply_markup=markup)
    except TelegramError as exc:
        if "not modified" not in str(exc).lower():
            raise


async def _q_show_results(
    query,
    status: str,
    prog_code: str,
    days_key: str,
    offset: int,
) -> None:
    program = _Q_PROG_CODES.get(prog_code)
    days_val = next((d for k, d, _ in _Q_DATE_OPTIONS if k == days_key), None)
    days_label = next((l for k, _, l in _Q_DATE_OPTIONS if k == days_key), "All time")
    prog_label = _Q_PROG_LABELS.get(prog_code, prog_code)
    status_label = _Q_STATUS_LABELS.get(status, status)

    questions, total = await db.get_questions_filtered(
        status=status, program=program, days=days_val,
        offset=offset, limit=_Q_PAGE_SIZE,
    )

    if not questions and offset > 0:
        # This page emptied out (e.g. everything on it was skipped) — step back to
        # the last page that still has entries instead of showing a dead end.
        last_page = ((total - 1) // _Q_PAGE_SIZE) * _Q_PAGE_SIZE if total else 0
        if last_page < offset:
            await _q_show_results(query, status, prog_code, days_key, last_page)
            return

    end = min(offset + _Q_PAGE_SIZE, total)
    header = f"{status_label} | {prog_label} | {days_label}\nShowing {offset + 1}–{end} of {total}\n\n"

    if not questions:
        await _q_edit(query, header.strip() + "\n\nNo questions found.")
        return

    body = "\n──────────\n".join(_q_format_entry(q, status) for q in questions)
    text = header + body
    if len(text) > 4000:
        text = text[:4000] + "\n…"

    # Filter context is appended to the action callbacks so the list can re-render
    # itself in place after a question is skipped or restored.
    ctx = f"{status}:{prog_code}:{days_key}:{offset}"

    rows = []
    if status == "pending":
        for q in questions:
            rows.append([
                InlineKeyboardButton(f"✍️ Answer #{q['id']}", callback_data=f"qa:{q['id']}"),
                InlineKeyboardButton(f"⏭ Skip #{q['id']}", callback_data=f"qs:{q['id']}:{ctx}"),
            ])
    elif status == "skipped":
        restore_row = []
        for q in questions:
            restore_row.append(
                InlineKeyboardButton(f"↩️ Restore #{q['id']}", callback_data=f"qr:{q['id']}:{ctx}")
            )
            if len(restore_row) == 2:
                rows.append(restore_row)
                restore_row = []
        if restore_row:
            rows.append(restore_row)

    nav = []
    if offset > 0:
        nav.append(InlineKeyboardButton(
            "← Prev", callback_data=f"qd:{status}:{prog_code}:{days_key}:{offset - _Q_PAGE_SIZE}"
        ))
    if end < total:
        nav.append(InlineKeyboardButton(
            "Next →", callback_data=f"qd:{status}:{prog_code}:{days_key}:{offset + _Q_PAGE_SIZE}"
        ))
    if nav:
        rows.append(nav)
    markup = InlineKeyboardMarkup(rows) if rows else None
    await _q_edit(query, text, markup)


async def _q_launch(update: Update, status: str, noun: str) -> None:
    user_id = update.effective_user.id
    if not _q_can_view(user_id):
        return
    allowed = _q_allowed_prog_codes(user_id)

    # Department expert scoped to exactly one program → skip the program picker.
    if allowed is not None and len(allowed) == 1:
        prog_code = next(iter(allowed))
        prog_label = _Q_PROG_LABELS.get(prog_code, prog_code)
        await update.message.reply_text(
            f"Filter {noun} questions — {prog_label}\nChoose a date range:",
            reply_markup=_q_date_keyboard(status, prog_code),
        )
        return

    await update.message.reply_text(
        f"Filter {noun} questions — choose a program:",
        reply_markup=_q_program_keyboard(status, allowed),
    )


async def _q_answered_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _q_launch(update, "answered", "answered")


async def _q_unanswered_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _q_launch(update, "pending", "unanswered")


async def _q_skipped_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _q_launch(update, "skipped", "skipped")


async def _q_program_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    _, status, prog_code = query.data.split(":", 2)
    if not _q_prog_allowed(update.effective_user.id, prog_code):
        return
    prog_label = _Q_PROG_LABELS.get(prog_code, prog_code)
    await query.edit_message_text(
        f"Program: {prog_label}\nNow choose a date range:",
        reply_markup=_q_date_keyboard(status, prog_code),
    )


async def _q_date_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    _, status, prog_code, days_key, offset_str = query.data.split(":", 4)
    if not _q_prog_allowed(update.effective_user.id, prog_code):
        return
    await _q_show_results(query, status, prog_code, days_key, int(offset_str))


async def _q_answer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Re-send a pending question as a fresh tracked message so it can be
    answered with a normal swipe-reply, even if the original expert message
    is old or was never registered in the DB."""
    query = update.callback_query
    if not _q_can_view(update.effective_user.id):
        await query.answer()
        return

    question_id = int(query.data.split(":", 1)[1])
    question = await db.get_question_by_id(question_id)

    if not question:
        await query.answer(msg.Q_ANSWER_GONE, show_alert=True)
        return
    if not _q_question_allowed(update.effective_user.id, question.get("program")):
        await query.answer()
        return
    if question["status"] != "pending":
        await query.answer(msg.EXPERT_ALREADY_ANSWERED, show_alert=True)
        return

    username = question.get("username")
    expert_text = msg.EXPERT_QUESTION_REISSUED.format(
        question_id=question_id,
        first_name=question.get("first_name") or "Unknown",
        username_part=f" (@{username})" if username else "",
        program=question.get("program") or "N/A",
        date=(question.get("created_at") or "")[:10] or "unknown",
        question=question.get("question_text") or "",
    )

    chat_id = update.effective_chat.id
    sent = await context.bot.send_message(
        chat_id=chat_id, text=expert_text, reply_markup=_q_skip_keyboard(question_id)
    )
    await db.set_question_expert_message(question_id, chat_id, sent.message_id)
    await query.answer(msg.Q_ANSWER_RESENT)


async def _q_load_for_action(query, question_id: int) -> dict | None:
    """Fetch a question for a skip/restore tap, answering the query if not permitted."""
    user_id = query.from_user.id
    if not _q_can_view(user_id):
        await query.answer()
        return None

    question = await db.get_question_by_id(question_id)
    if not question:
        await query.answer(msg.Q_ANSWER_GONE, show_alert=True)
        return None
    if not _q_question_allowed(user_id, question.get("program")):
        await query.answer()
        return None
    return question


async def _q_skip_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Dismiss a question without answering it — for duplicates and spam. The
    student is never notified, and their pending follow-up ping is cancelled."""
    query = update.callback_query
    parts = query.data.split(":")
    question_id = int(parts[1])

    question = await _q_load_for_action(query, question_id)
    if question is None:
        return
    if question["status"] == "answered":
        await query.answer(msg.EXPERT_ALREADY_ANSWERED, show_alert=True)
        return

    if question["status"] == "pending":
        user_chat_id = question["user_chat_id"]
        await db.mark_question_skipped(question_id)
        await db.mark_sibling_questions_skipped(user_chat_id, question["question_text"])
        # Only silence the follow-up if nothing else of theirs is still waiting.
        if await db.count_pending_questions(user_chat_id) == 0:
            from scheduler import cancel_followups
            await cancel_followups(user_chat_id)

    await query.answer(msg.Q_SKIP_DONE)

    if len(parts) > 2:
        # Tapped in an /unanswered list — refresh it so the skipped entry drops off.
        _, _, status, prog_code, days_key, offset_str = parts
        await _q_show_results(query, status, prog_code, days_key, int(offset_str))
        return

    # Tapped on the forwarded question itself — mark it up and drop the button.
    try:
        await query.edit_message_text((query.message.text or "") + msg.Q_SKIP_NOTE)
    except Exception:
        logger.exception("Failed to annotate skipped question message #%d", question_id)


async def _q_restore_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Put a skipped question back into the unanswered queue."""
    query = update.callback_query
    parts = query.data.split(":")
    question_id = int(parts[1])

    question = await _q_load_for_action(query, question_id)
    if question is None:
        return

    restored = await db.restore_skipped_question(question_id)
    await query.answer(msg.Q_SKIP_RESTORED if restored else msg.Q_SKIP_NOT_SKIPPED)

    if len(parts) > 2:
        _, _, status, prog_code, days_key, offset_str = parts
        await _q_show_results(query, status, prog_code, days_key, int(offset_str))


def build_app() -> Application:
    app = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .concurrent_updates(True)
        .rate_limiter(AIORateLimiter())
        .request(
            HTTPXRequest(
                connection_pool_size=256,
                pool_timeout=20,
                connect_timeout=30,
                read_timeout=30,
                write_timeout=30,
            )
        )
        .get_updates_request(HTTPXRequest(connection_pool_size=16))
        .build()
    )

    _private = filters.ChatType.PRIVATE
    app.add_handler(CommandHandler("start", start, filters=_private))
    app.add_handler(CommandHandler("cancel", cancel, filters=_private))
    app.add_handler(CommandHandler("clarify", clarify_command, filters=_private))
    app.add_handler(CommandHandler("broadcastkeyboard", _broadcast_keyboard_command, filters=_private))
    app.add_handler(CommandHandler("stats", _stats_command, filters=_private))
    app.add_handler(CommandHandler("export_db", _export_db_command, filters=_private))
    app.add_handler(CommandHandler("setvideo", _video_admin_command, filters=_private))
    app.add_handler(CommandHandler("deletevideo", _delete_video_command, filters=_private))
    app.add_handler(CommandHandler("pingexperts", _ping_experts_command, filters=_private))
    app.add_handler(CommandHandler("followup", followup_command, filters=_private))
    app.add_handler(CommandHandler("santix", _santix_command, filters=_private))
    app.add_handler(CommandHandler("answered", _q_answered_command, filters=_private))
    app.add_handler(CommandHandler("clear_adv", _clear_adv_command, filters=_private))
    app.add_handler(CommandHandler("unanswered", _q_unanswered_command, filters=_private))
    app.add_handler(CommandHandler("skipped", _q_skipped_command, filters=_private))
    app.add_handler(CommandHandler("ae_list", _ae_list_command, filters=_private))
    app.add_handler(CommandHandler("econ_list", _econ_list_command, filters=_private))
    app.add_handler(CommandHandler("merch_list", _merch_list_command, filters=_private))
    app.add_handler(CommandHandler("set_merch_qr", _set_merch_qr_command, filters=_private))
    app.add_handler(CommandHandler("roll", _roll_command, filters=_private))
    app.add_handler(CommandHandler("reroll", _reroll_command, filters=_private))
    app.add_handler(CommandHandler("vg_list", _vg_list_command, filters=_private))
    app.add_handler(CommandHandler("satc_list", _satc_list_command, filters=_private))
    app.add_handler(CommandHandler("ae_set_terms", _ae_set_terms_command, filters=_private))
    app.add_handler(CommandHandler("set_guidebook", _set_guidebook_command, filters=_private))
    app.add_handler(CommandHandler("guidebook_count", _guidebook_count_command, filters=_private))
    app.add_handler(CommandHandler("ae_set_payment", _ae_set_payment_command, filters=_private))
    app.add_handler(CommandHandler("ae_remind", _ae_remind_command, filters=_private))
    app.add_handler(CommandHandler("ae_stuck", _ae_stuck_command, filters=_private))
    app.add_handler(CommandHandler("ae_payment_remind", _ae_payment_remind_command, filters=_private))
    app.add_handler(CallbackQueryHandler(_ae_terms_accept_callback, pattern="^ae_terms_accept:"))
    app.add_handler(CallbackQueryHandler(_ae_payment_made_callback, pattern="^ae_payment_made:"))
    app.add_handler(CallbackQueryHandler(_ae_payment_confirm_callback, pattern="^ae_payment_confirm:"))
    app.add_handler(CallbackQueryHandler(_ae_payment_reject_callback, pattern="^ae_payment_reject:"))
    app.add_handler(CallbackQueryHandler(_tap_join_callback, pattern="^tap_join$"))
    app.add_handler(CallbackQueryHandler(_tap_screenshot_callback, pattern="^tap_screenshot$"))
    app.add_handler(CallbackQueryHandler(_tap_approve_callback, pattern="^tap_approve:"))
    app.add_handler(CallbackQueryHandler(_tap_reject_callback, pattern="^tap_reject:"))
    app.add_handler(CallbackQueryHandler(_video_admin_program_callback, pattern="^setvideo_"))
    app.add_handler(CallbackQueryHandler(_delete_video_program_callback, pattern="^deletevideo_"))
    app.add_handler(CallbackQueryHandler(_q_program_callback, pattern="^qp:"))
    app.add_handler(CallbackQueryHandler(_q_date_callback, pattern="^qd:"))
    app.add_handler(CallbackQueryHandler(_q_answer_callback, pattern="^qa:"))
    app.add_handler(CallbackQueryHandler(_q_skip_callback, pattern="^qs:"))
    app.add_handler(CallbackQueryHandler(_q_restore_callback, pattern="^qr:"))
    app.add_handler(CallbackQueryHandler(_podcast_check_callback, pattern="^podcast_check$"))
    app.add_handler(CallbackQueryHandler(_guidebook_get_callback, pattern="^guidebook_get$"))
    app.add_handler(CallbackQueryHandler(_guidebook_check_callback, pattern="^guidebook_check$"))
    app.add_handler(CallbackQueryHandler(_sat_enroll_inline_callback, pattern="^sat_enroll_inline$"))
    app.add_handler(CallbackQueryHandler(_econ_join_callback, pattern="^econ_join$"))
    app.add_handler(CallbackQueryHandler(_merch_open_callback, pattern="^merch_open$"))
    app.add_handler(CallbackQueryHandler(_merch_buy_callback, pattern="^merch_buy:"))
    app.add_handler(CallbackQueryHandler(_merch_qty_callback, pattern="^merch_qty:"))
    app.add_handler(CallbackQueryHandler(_merch_qty_back_callback, pattern="^merch_qty_back$"))
    app.add_handler(CallbackQueryHandler(_merch_checkout_callback, pattern="^merch_checkout$"))
    app.add_handler(CallbackQueryHandler(_satc_open_callback, pattern="^satc_open$"))
    app.add_handler(CallbackQueryHandler(_satc_check_callback, pattern="^satc_check$"))
    app.add_handler(CallbackQueryHandler(_consult_retired_callback, pattern="^consult_(open|check)$"))
    app.add_handler(CallbackQueryHandler(_vg_join_callback, pattern="^vg_join$"))
    app.add_handler(CallbackQueryHandler(_vg_join_callback, pattern="^vg_check$"))
    app.add_handler(CallbackQueryHandler(_vg_open_callback, pattern="^vg_open$"))
    app.add_handler(CallbackQueryHandler(_vg_confirm_callback, pattern="^vg_confirm:"))
    app.add_handler(CallbackQueryHandler(_vg_reroll_callback, pattern="^vg_reroll$"))
    app.add_handler(CallbackQueryHandler(_econ_course_callback, pattern="^econ_course:"))
    app.add_handler(CallbackQueryHandler(_econ_done_callback, pattern="^econ_done$"))
    app.add_handler(CallbackQueryHandler(_ae_program_faq_callback, pattern="^ae_program_faq$"))
    app.add_handler(CallbackQueryHandler(_ae_apply_now_callback, pattern="^ae_apply_now$"))
    app.add_handler(CallbackQueryHandler(_ae_format_callback, pattern="^ae_format:"))
    app.add_handler(CallbackQueryHandler(_ae_list_callback, pattern="^ae_list$"))
    app.add_handler(CallbackQueryHandler(_ae_view_callback, pattern="^ae_view:"))
    app.add_handler(CallbackQueryHandler(_ae_accept_callback, pattern="^ae_accept:"))
    app.add_handler(CallbackQueryHandler(_ae_reject_callback, pattern="^ae_reject:"))
    app.add_handler(MessageHandler(_private & filters.CONTACT, handle_message))
    app.add_handler(MessageHandler(_private & ~filters.COMMAND, handle_message))
    app.add_error_handler(_on_error)
    return app


async def _on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Catch-all so handler exceptions are logged as a single line, not a
    multi-frame traceback. Stale-callback 'query is too old' errors are benign."""
    logger.warning("Handler error: %s: %s", type(context.error).__name__, context.error)
