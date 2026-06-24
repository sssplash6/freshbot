import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone

_RATE_LIMIT_SECONDS = 1.5
_last_message_time: dict[int, float] = {}

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
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

# Chat IDs with bypass mode active — skips "coming soon" gates to expose real flows.
_bypass_users: set[int] = set()

# Top-level nav buttons that escape any active capture state (question/followup input).
_NAV_BUTTONS: frozenset[str] = frozenset({
    # Main menu
    msg.BTN_PROGRAMS, msg.BTN_GENERAL_INQUIRY, msg.BTN_PODCAST,
    msg.BTN_HOME, msg.BTN_START, msg.BTN_IVYMAXXING,
    msg.BTN_ADV_ENGLISH, msg.BTN_SAT_ENROLL, msg.BTN_TRIAL_AP,
    # Program sub-menu
    msg.BTN_SAT, msg.BTN_ADMISSIONS, msg.BTN_FULL_SUPPORT, msg.BTN_MASTERS,
    msg.BTN_ADV_PLACEMENT, msg.BTN_IMKON, msg.BTN_RESEARCH_INSTITUTE,
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
            [msg.BTN_IVYMAXXING, msg.BTN_ADV_ENGLISH],
            [msg.BTN_SAT_ENROLL, msg.BTN_PROGRAMS],
            [msg.BTN_GENERAL_INQUIRY],
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
            [msg.BTN_SAT],
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

    # Admin routing for PERSON_X.
    # If mid-video-setup, route to the video admin handler. Otherwise, if PERSON_X
    # is an expert replying to a question, fall through to the expert handler;
    # any other admin message is ignored.
    if chat_id == PERSON_X_CHAT_ID:
        if _video_admin_state.get("step") is not None:
            await _video_admin_message_handler(update, context)
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
    elif text == msg.BTN_IVYMAXXING:
        await _handle_ivymaxxing(update, chat_id)
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
    file_id = await db.get_program_video(program)

    if file_id:
        await update.message.reply_text(msg.PROGRAM_CHOSEN.format(description=description))
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
    await update.message.reply_text(msg.FAQ_TYPE_QUESTION, reply_markup=_back_keyboard())


async def _handle_adv_english(update: Update, chat_id: int) -> None:
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(msg.BTN_AE_APPLY_NOW, callback_data="ae_apply_now")]
    ])
    await update.message.reply_text(msg.AE_INTRO, reply_markup=keyboard, parse_mode="HTML")


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
            f"    {program}: {count}" for program, count in s["questions_by_program"]
        )
        by_program = f"  By program:\n{lines}\n"
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
        # Cap broadcast concurrency so it can never starve the connection pool
        # or Telegram send budget that live user replies depend on.
        sem = asyncio.Semaphore(15)

        async def _send_one(cid: int) -> None:
            nonlocal sent, failed, first_error
            async with sem:
                try:
                    # Refresh the persistent reply keyboard for every user...
                    await context.bot.send_message(
                        chat_id=cid,
                        text=msg.BROADCAST_KEYBOARD_MENU_NOTE,
                        reply_markup=_main_keyboard(),
                    )
                    # ...then the event promo with its inline join button.
                    await context.bot.send_message(
                        chat_id=cid,
                        text=msg.BROADCAST_KEYBOARD_MESSAGE,
                        parse_mode="HTML",
                        reply_markup=InlineKeyboardMarkup(
                            [[InlineKeyboardButton(msg.BTN_IVYMAXXING, callback_data="ivy_join")]]
                        ),
                    )
                    sent += 1
                except Exception as e:
                    if first_error is None:
                        first_error = f"{type(e).__name__}: {e}"
                    logger.warning("Broadcast failed for chat_id=%d: %s: %s", cid, type(e).__name__, e)
                    failed += 1
                await asyncio.sleep(0.05)

        await asyncio.gather(*(_send_one(cid) for cid in chat_ids))
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
        for p in msg.PROGRAM_DESCRIPTIONS.keys()
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
    if not video:
        await update.message.reply_text(msg.SETVIDEO_NOT_VIDEO)
        return
    program = _video_admin_state["program"]
    await db.upsert_program_video(program, video.file_id)
    _video_admin_state["step"] = None
    _video_admin_state["program"] = None
    await update.message.reply_text(msg.SETVIDEO_SAVED.format(program=program))


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
# Ivymaxxing with Sega Arakelyan — webinar gate (must be in both groups)
# ---------------------------------------------------------------------------

IVY_REQUIRED_GROUP_IDS = [-1003765677875, -1001481432083]
IVY_REQUIRED_GROUP_HANDLES = ["@freshmanclassof2031", "@freshmanblog"]
# `&` is escaped to `&amp;` because the URL is embedded in a Telegram HTML link.
IVY_CALENDAR_URL = (
    "https://calendar.google.com/calendar/event?action=TEMPLATE"
    "&amp;tmeid=M29ha3Fyc2FkY2hrcDBwaGVnNjdvMDlpMm4gc2VnYUBmcmVzaG1hbi5hY2FkZW15"
    "&amp;tmsrc=sega%40freshman.academy"
)


async def _ivy_get_missing(bot, chat_id: int) -> list[str]:
    missing = []
    for group_id, handle in zip(IVY_REQUIRED_GROUP_IDS, IVY_REQUIRED_GROUP_HANDLES):
        try:
            member = await bot.get_chat_member(group_id, chat_id)
            if member.status not in _MEMBER_STATUSES:
                missing.append(handle)
        except TelegramError:
            logger.warning("Cannot check Ivymaxxing membership in %s. Failing open.", group_id)
    return missing


def _ivy_granted_text() -> str:
    calendar_line = (
        msg.IVY_CALENDAR_LINE.format(calendar_url=IVY_CALENDAR_URL) if IVY_CALENDAR_URL else ""
    )
    return msg.IVY_ACCESS_GRANTED.format(calendar_line=calendar_line)


async def _ivy_send_flow(bot, chat_id: int) -> None:
    missing = await _ivy_get_missing(bot, chat_id)
    if missing:
        channel_list = "\n".join(f"• {h}" for h in missing)
        await bot.send_message(
            chat_id=chat_id,
            text=msg.IVY_MUST_JOIN.format(channel_list=channel_list),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(msg.BTN_IVY_CHECK, callback_data="ivy_check")]]
            ),
        )
        return
    await bot.send_message(
        chat_id=chat_id,
        text=_ivy_granted_text(),
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=_main_keyboard(),
    )


async def _handle_ivymaxxing(update: Update, chat_id: int) -> None:
    await _ivy_send_flow(update.get_bot(), chat_id)


async def _ivy_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Inline "join" button from /broadcastkeyboard — runs the same gate flow.
    query = update.callback_query
    await query.answer()
    await _ivy_send_flow(context.bot, update.effective_user.id)


async def _ivy_check_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_user.id
    missing = await _ivy_get_missing(context.bot, chat_id)
    if missing:
        channel_list = "\n".join(f"• {h}" for h in missing)
        try:
            await query.edit_message_text(
                msg.IVY_MUST_JOIN.format(channel_list=channel_list),
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton(msg.BTN_IVY_CHECK, callback_data="ivy_check")]]
                ),
            )
        except TelegramError as e:
            if "not modified" not in str(e).lower():
                raise
        return
    try:
        await query.edit_message_text(
            _ivy_granted_text(), parse_mode="HTML", disable_web_page_preview=True
        )
    except TelegramError as e:
        if "not modified" not in str(e).lower():
            raise


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
# /answered and /unanswered — admin question viewer
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
    "GI":  "General Inquiry",
}

_Q_DATE_OPTIONS = [
    ("0",  None, "All time"),
    ("1",  1,    "Today"),
    ("7",  7,    "Last 7 days"),
    ("30", 30,   "Last 30 days"),
]


def _q_program_keyboard(status: str) -> InlineKeyboardMarkup:
    all_btn = [InlineKeyboardButton("All Programs", callback_data=f"qp:{status}:ALL")]
    prog_btns = [
        InlineKeyboardButton(_Q_PROG_LABELS[code], callback_data=f"qp:{status}:{code}")
        for code in _Q_PROG_CODES
        if code != "ALL"
    ]
    rows = [all_btn]
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
    status_label = "✅ Answered" if status == "answered" else "⏳ Unanswered"

    questions, total = await db.get_questions_filtered(
        status=status, program=program, days=days_val,
        offset=offset, limit=_Q_PAGE_SIZE,
    )

    end = min(offset + _Q_PAGE_SIZE, total)
    header = f"{status_label} | {prog_label} | {days_label}\nShowing {offset + 1}–{end} of {total}\n\n"

    if not questions:
        await query.edit_message_text(header.strip() + "\n\nNo questions found.")
        return

    body = "\n──────────\n".join(_q_format_entry(q, status) for q in questions)
    text = header + body
    if len(text) > 4000:
        text = text[:4000] + "\n…"

    nav = []
    if offset > 0:
        nav.append(InlineKeyboardButton(
            "← Prev", callback_data=f"qd:{status}:{prog_code}:{days_key}:{offset - _Q_PAGE_SIZE}"
        ))
    if end < total:
        nav.append(InlineKeyboardButton(
            "Next →", callback_data=f"qd:{status}:{prog_code}:{days_key}:{offset + _Q_PAGE_SIZE}"
        ))
    markup = InlineKeyboardMarkup([nav]) if nav else None
    await query.edit_message_text(text, reply_markup=markup)


async def _q_answered_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id not in _Q_ADMIN_IDS:
        return
    await update.message.reply_text(
        "Filter answered questions — choose a program:",
        reply_markup=_q_program_keyboard("answered"),
    )


async def _q_unanswered_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id not in _Q_ADMIN_IDS:
        return
    await update.message.reply_text(
        "Filter unanswered questions — choose a program:",
        reply_markup=_q_program_keyboard("pending"),
    )


async def _q_program_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if update.effective_user.id not in _Q_ADMIN_IDS:
        return
    _, status, prog_code = query.data.split(":", 2)
    prog_label = _Q_PROG_LABELS.get(prog_code, prog_code)
    await query.edit_message_text(
        f"Program: {prog_label}\nNow choose a date range:",
        reply_markup=_q_date_keyboard(status, prog_code),
    )


async def _q_date_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if update.effective_user.id not in _Q_ADMIN_IDS:
        return
    _, status, prog_code, days_key, offset_str = query.data.split(":", 4)
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
    app.add_handler(CommandHandler("pingexperts", _ping_experts_command, filters=_private))
    app.add_handler(CommandHandler("followup", followup_command, filters=_private))
    app.add_handler(CommandHandler("santix", _santix_command, filters=_private))
    app.add_handler(CommandHandler("answered", _q_answered_command, filters=_private))
    app.add_handler(CommandHandler("clear_adv", _clear_adv_command, filters=_private))
    app.add_handler(CommandHandler("unanswered", _q_unanswered_command, filters=_private))
    app.add_handler(CommandHandler("ae_list", _ae_list_command, filters=_private))
    app.add_handler(CommandHandler("ae_set_terms", _ae_set_terms_command, filters=_private))
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
    app.add_handler(CallbackQueryHandler(_q_program_callback, pattern="^qp:"))
    app.add_handler(CallbackQueryHandler(_q_date_callback, pattern="^qd:"))
    app.add_handler(CallbackQueryHandler(_podcast_check_callback, pattern="^podcast_check$"))
    app.add_handler(CallbackQueryHandler(_ivy_check_callback, pattern="^ivy_check$"))
    app.add_handler(CallbackQueryHandler(_ivy_join_callback, pattern="^ivy_join$"))
    app.add_handler(CallbackQueryHandler(_ae_apply_now_callback, pattern="^ae_apply_now$"))
    app.add_handler(CallbackQueryHandler(_ae_format_callback, pattern="^ae_format:"))
    app.add_handler(CallbackQueryHandler(_ae_list_callback, pattern="^ae_list$"))
    app.add_handler(CallbackQueryHandler(_ae_view_callback, pattern="^ae_view:"))
    app.add_handler(CallbackQueryHandler(_ae_accept_callback, pattern="^ae_accept:"))
    app.add_handler(CallbackQueryHandler(_ae_reject_callback, pattern="^ae_reject:"))
    app.add_handler(MessageHandler(_private & filters.CONTACT, handle_message))
    app.add_handler(MessageHandler(_private & ~filters.COMMAND, handle_message))
    return app
