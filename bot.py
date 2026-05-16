import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone

_RATE_LIMIT_SECONDS = 1.5
_last_message_time: dict[int, float] = {}

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
    ADV_PLACEMENT_MAN_CHAT_ID,
    AP_MAN_CHAT_ID,
    FS_MAN_CHAT_ID,
    GENERAL_MAN_CHAT_ID,
    PERSON_Z_CHAT_ID,
    SAT_BOOKING_URL,
    WEBSITE_URL_ADV_PLACEMENT,
    IMKON_MAN_CHAT_ID,
    LINK_EXPIRY_HOURS,
    MS_MAN_CHAT_ID,
    PERSON_X_CHAT_ID,
    REQUIRED_CHANNEL_IDS,
    REQUIRED_CHANNEL_INVITES,
    REQUIRED_GROUP_IDS,
    REQUIRED_GROUP_INVITES,
    RI_MAN_CHAT_ID,
    SAT_MAN_CHAT_ID,
    ADV_ENGLISH_REVIEWER_CHAT_ID,
    AE_GROUP_CHAT_ID,
    RS_GROUP_CHAT_ID,
    PODCAST_CHANNEL_IDS,
    PODCAST_CHANNEL_HANDLES,
    PODCAST_YOUTUBE_URL,
    SPECIAL_EVENT_CHANNEL_IDS,
    SPECIAL_EVENT_CHANNEL_HANDLES,
    VALERA_CHAT_ID,
    TELEGRAM_BOT_TOKEN,
    WEBSITE_URL_ADMISSIONS,
    WEBSITE_URL_FULL_SUPPORT,
    WEBSITE_URL_MASTERS,
    WEBSITE_URL_IMKON,
    WEBSITE_URL_RESEARCH_INSTITUTE,
)

logger = logging.getLogger(__name__)

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

# Accumulates Research Seminar registration answers per chat_id.
_rs_state: dict[int, dict] = {}

# Chat IDs with bypass mode active — skips "coming soon" gates to expose real flows.
_bypass_users: set[int] = set()

# Top-level nav buttons that escape any active capture state (question/followup input).
_NAV_BUTTONS: frozenset[str] = frozenset({
    # Main menu
    msg.BTN_PROGRAMS, msg.BTN_GENERAL_INQUIRY, msg.BTN_PODCAST,
    msg.BTN_SPECIAL_EVENTS, msg.BTN_GET_LINK, msg.BTN_HOME, msg.BTN_START,
    msg.BTN_ADV_ENGLISH, msg.BTN_SAT_GIVEAWAY, msg.BTN_RS,
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
            [msg.BTN_PROGRAMS, msg.BTN_GENERAL_INQUIRY],
            [msg.BTN_SPECIAL_EVENTS, msg.BTN_GET_LINK],
            [msg.BTN_ADV_ENGLISH, msg.BTN_RS],
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

    # Per-user rate limit — silently drop messages that arrive too fast
    now = time.monotonic()
    if now - _last_message_time.get(chat_id, 0) < _RATE_LIMIT_SECONDS:
        return
    _last_message_time[chat_id] = now

    # Event gate admin routing.
    # If mid-event-setup OR not a reply to a known question, route to admin handler.
    # If PERSON_X is also an expert and is replying (reply_to_message is set),
    # let the expert handler run so student questions get answered.
    if chat_id == PERSON_X_CHAT_ID:
        if _sevent_admin_state.get("step") is not None:
            await _sevent_message_handler(update, context)
            return
        if _video_admin_state.get("step") is not None:
            await _video_admin_message_handler(update, context)
            return
        in_setup = _eg_admin_state.get("step") is not None
        is_reply = update.message.reply_to_message is not None
        if in_setup or not (chat_id in _EXPERT_CHAT_IDS and is_reply and text):
            await _eg_admin_message_handler(update, context)
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
            if user_v and user_v.get("flow") == "sat_giveaway" and user_v.get("status") == "sat_step_screenshot":
                if photo or document:
                    if photo:
                        fid, ftype = photo[-1].file_id, "photo"
                    else:
                        fid, ftype = document.file_id, "document"
                    await _handle_sat_screenshot(update, chat_id, fid, ftype, context)
                    return
        contact = update.message.contact
        if contact:
            user_v = await db.get_user(chat_id)
            if user_v and user_v.get("flow") == "rs" and user_v.get("status") == "rs_step_phone":
                if contact.user_id != update.effective_user.id:
                    await update.message.reply_text(msg.RS_PHONE_REQUIRED, reply_markup=_rs_phone_keyboard())
                    return
                await _handle_rs_phone(update, chat_id, contact.phone_number, context)
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

    if user and user.get("flow") == "rs":
        if text in _NAV_BUTTONS:
            await db.set_flow(chat_id, None)
            await db.set_status(chat_id, None)
        elif user.get("status") == "rs_step_name":
            await _handle_rs_name(update, chat_id, text, context)
            return
        else:
            await update.message.reply_text(msg.RS_PHONE_REQUIRED, reply_markup=_rs_phone_keyboard())
            return

    if user and user.get("flow") == "ae_payment" and user.get("status") == "ae_payment_step_screenshot":
        if text in _NAV_BUTTONS:
            await db.set_flow(chat_id, None)
            await db.set_status(chat_id, None)
        else:
            await update.message.reply_text(msg.AE_PAYMENT_SCREENSHOT_REQUIRED)
            return

    if user and user.get("flow") == "sat_giveaway" and user.get("status") == "sat_step_screenshot":
        if text in _NAV_BUTTONS:
            await db.set_flow(chat_id, None)
            await db.set_status(chat_id, None)
        else:
            await update.message.reply_text(msg.SAT_GIVEAWAY_SCREENSHOT_REQUIRED)
            return

    if user and user.get("flow") == "adv_english" and user.get("status") in (
        "ae_step_full_name", "ae_step_video", "ae_step_ielts", "ae_step_sat",
        "ae_step_why", "ae_step_perspective", "ae_step_resources",
    ):
        if text in _NAV_BUTTONS:
            _ae_state.pop(chat_id, None)
            await db.set_flow(chat_id, None)
            await db.set_status(chat_id, None)
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
    elif text == msg.BTN_SPECIAL_EVENTS:
        await _handle_special_events(update, chat_id, context)
    elif text == msg.BTN_ADV_ENGLISH:
        await _handle_adv_english(update, chat_id)
    elif text == msg.BTN_SAT_GIVEAWAY:
        await _handle_sat_giveaway(update, chat_id, context)
    elif text == msg.BTN_RS:
        await _handle_rs(update, chat_id, context)
    elif text == msg.BTN_GENERAL_INQUIRY:
        await _handle_general_inquiry(update, chat_id)
    elif text == msg.BTN_PODCAST:
        await _handle_podcast(update, chat_id)
    elif text == msg.BTN_GET_LINK:
        await _eg_student_get_link(update, chat_id, context)
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
        await query.message.reply_text(msg.AE_ALREADY_APPLIED, reply_markup=_main_keyboard())
        return

    _ae_state[chat_id] = {}
    await db.set_flow(chat_id, "adv_english")
    await db.set_status(chat_id, "ae_step_full_name")
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
            terms_file_id = await db.get_setting("ae_terms_file_id")
            if terms_file_id:
                await context.bot.send_document(
                    chat_id=applicant_chat_id,
                    document=terms_file_id,
                    caption=msg.AE_TERMS_CAPTION,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(
                            msg.BTN_AE_ACCEPT_TERMS,
                            callback_data=f"ae_terms_accept:{applicant_chat_id}",
                        )
                    ]]),
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

    if flow == "rs":
        _rs_state.pop(chat_id, None)
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
        await bot.copy_message(
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
        chat_id=event["event_group_id"],
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

    await update.effective_message.reply_text(
        msg.EG_INVITE_SENT.format(expiry_hours=LINK_EXPIRY_HOURS, link=invite.invite_link),
        reply_markup=_main_keyboard(),
    )


async def _eg_student_get_link(
    update: Update, chat_id: int, context: ContextTypes.DEFAULT_TYPE
) -> None:
    event = await db.eg_get_active_event()
    if not event:
        await update.message.reply_text(msg.EG_NO_ACTIVE_EVENT, reply_markup=_main_keyboard())
        return

    # Deliver the event post immediately on button tap
    await _eg_deliver_event_post(chat_id, event, context.bot)

    group_results, channel_results = await _eg_check_membership(context.bot, chat_id)
    missing = _eg_build_missing_links(group_results, channel_results)

    if missing:
        await _eg_send_missing_message(update, missing)
        return

    existing_link = await db.eg_get_issued_link(event["id"], chat_id)
    if existing_link:
        await update.effective_message.reply_text(
            msg.EG_ALREADY_ISSUED.format(link=existing_link["invite_link"]),
            reply_markup=_main_keyboard(),
        )
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
    event = await db.eg_get_active_event()
    if not event or request.chat.id != event["event_group_id"]:
        return

    await context.bot.approve_chat_join_request(event["event_group_id"], request.from_user.id)
    await db.eg_log_join_approval(event["id"], request.from_user.id)
    logger.info("Approved join request from user %s", request.from_user.id)


# ---------------------------------------------------------------------------
# Event gate — admin flow (PERSON_X only)
# ---------------------------------------------------------------------------

# In-memory state for the two-step /event setup (only one admin, no DB needed)
_eg_admin_state: dict = {"step": None, "event_group_id": None}

# In-memory state for /setvideo admin flow
_video_admin_state: dict = {"step": None, "program": None}

# In-memory state for /sevent admin flow
_sevent_admin_state: dict = {"step": None}

# Tracks last rolled participant ID for /reroll exclusion
_roll_state: dict = {"last_id": None}


async def _eg_admin_event_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if update.effective_user.id != PERSON_X_CHAT_ID:
        return
    _eg_admin_state["step"] = "awaiting_group_id"
    _eg_admin_state["event_group_id"] = None
    await update.message.reply_text(
        "Send me the event group ID (the negative integer, e.g. -1001234567890)."
    )


async def _eg_admin_message_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    msg_obj = update.message
    step = _eg_admin_state.get("step")

    if step == "awaiting_group_id":
        raw = (msg_obj.text or "").strip()
        try:
            group_id = int(raw)
        except ValueError:
            await msg_obj.reply_text("That doesn't look like a valid group ID. Send a negative integer.")
            return
        _eg_admin_state["event_group_id"] = group_id
        _eg_admin_state["step"] = "awaiting_post"
        await msg_obj.reply_text("Got it! Now send the event post — any message (text, photo, or forwarded post).")
        return

    if step == "awaiting_post":
        post_chat_id = msg_obj.chat_id
        post_message_id = msg_obj.message_id
        post_text = msg_obj.text or msg_obj.caption

        await db.eg_save_event(
            _eg_admin_state["event_group_id"],
            post_chat_id,
            post_message_id,
            post_text,
        )
        _eg_admin_state["step"] = None
        _eg_admin_state["event_group_id"] = None
        await msg_obj.reply_text(msg.EG_EVENT_ACTIVATED)

        # Broadcast event post to all known bot users
        event = await db.eg_get_active_event()
        if event:
            chat_ids = await db.get_all_chat_ids()
            sent = 0
            failed = 0
            for cid in chat_ids:
                try:
                    await _eg_deliver_event_post(cid, event, context.bot)
                    sent += 1
                except Exception as e:
                    logger.warning("Broadcast failed for chat_id=%d: %s", cid, e)
                    failed += 1
            await msg_obj.reply_text(
                f"📢 Broadcast: {sent} sent, {failed} failed "
                f"({len(chat_ids)} total users in DB)."
            )
        return

    # No active setup — hint to use /event
    await msg_obj.reply_text("Use /event to set up a new event.")


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
    _eg_admin_state["step"] = None
    _eg_admin_state["event_group_id"] = None
    await db.eg_deactivate_event()
    await update.message.reply_text(msg.EG_ADMIN_EVENT_CLEARED)


async def _eg_admin_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != PERSON_X_CHAT_ID:
        return
    await update.message.reply_text(msg.EG_ADMIN_HELP)


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
    event_str = "Yes" if s["active_event"] else "No"

    await update.message.reply_text(
        msg.ADMIN_STATS.format(
            total_users=s["total_users"],
            active_users_7d=s["active_users_7d"],
            users_in_flow=s["users_in_flow"],
            total_questions=s["total_questions"],
            pending_questions=s["pending_questions"],
            answered_questions=s["answered_questions"],
            questions_by_program=by_program,
            active_event=event_str,
            total_links=s["total_links"],
            total_approvals=s["total_approvals"],
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
    sent = failed = 0
    first_error: str | None = None
    for cid in chat_ids:
        try:
            await context.bot.send_message(
                chat_id=cid,
                text=msg.BROADCAST_KEYBOARD_MESSAGE,
                reply_markup=_main_keyboard(),
                parse_mode="HTML",
            )
            sent += 1
        except Exception as e:
            if first_error is None:
                first_error = f"{type(e).__name__}: {e}"
            logger.warning("Broadcast failed for chat_id=%d: %s: %s", cid, type(e).__name__, e)
            failed += 1
        await asyncio.sleep(0.05)
    result = msg.BROADCAST_KEYBOARD_DONE.format(sent=sent, failed=failed, total=len(chat_ids))
    if first_error:
        result += f"\n\nFirst error: {first_error}"
    await update.message.reply_text(result)


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


# ---------------------------------------------------------------------------
# /sevent — admin flow (PERSON_X only)
# ---------------------------------------------------------------------------

async def _sevent_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != PERSON_X_CHAT_ID:
        return
    _sevent_admin_state["step"] = "awaiting_post"
    await update.message.reply_text(msg.SEVENT_SEND_POST)


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


async def _sevent_participants_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != PERSON_X_CHAT_ID:
        return
    participants = await db.se_get_all_participants()
    count = len(participants)
    if count == 0:
        await update.message.reply_text("No participants yet.")
        return
    lines = [f"{i + 1}. {p['first_name']}" + (f" (@{p['username']})" if p.get("username") else "") for i, p in enumerate(participants)]
    header = f"Special event participants: {count}\n\n"
    chunks, current = [], header
    for line in lines:
        if len(current) + len(line) + 1 > 4096:
            await update.message.reply_text(current)
            current = ""
        current += line + "\n"
    if current:
        await update.message.reply_text(current)


async def _sevent_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if _sevent_admin_state.get("step") != "awaiting_post":
        return
    msg_obj = update.message
    await db.se_save_post(msg_obj.chat_id, msg_obj.message_id)
    _sevent_admin_state["step"] = None
    await msg_obj.reply_text(msg.SEVENT_SAVED)


# ---------------------------------------------------------------------------
# Special Events — student flow
# ---------------------------------------------------------------------------

async def _handle_special_events(
    update: Update, chat_id: int, context: ContextTypes.DEFAULT_TYPE
) -> None:
    post = await db.se_get_active_post()
    if not post:
        await update.message.reply_text(msg.SE_NO_ACTIVE_EVENT, reply_markup=_main_keyboard())
        return
    await context.bot.copy_message(
        chat_id=chat_id,
        from_chat_id=post["post_chat_id"],
        message_id=post["post_message_id"],
    )
    await update.message.reply_text(
        msg.SE_JOIN_PROMPT,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton(msg.BTN_CLICK_TO_JOIN, callback_data="se_join")]]
        ),
    )


async def _se_get_missing_handles(bot, student_chat_id: int) -> list[str]:
    missing: list[str] = []
    for channel_id, handle in zip(SPECIAL_EVENT_CHANNEL_IDS, SPECIAL_EVENT_CHANNEL_HANDLES):
        try:
            member = await bot.get_chat_member(channel_id, student_chat_id)
            if member.status not in _EG_MEMBER_STATUSES:
                missing.append(handle)
        except TelegramError:
            logger.warning("Cannot check SE membership in %s. Failing open.", channel_id)
    return missing


async def _podcast_get_missing(bot, chat_id: int) -> list[str]:
    if not PODCAST_CHANNEL_IDS:
        return []
    missing = []
    for channel_id, handle in zip(PODCAST_CHANNEL_IDS, PODCAST_CHANNEL_HANDLES):
        try:
            member = await bot.get_chat_member(channel_id, chat_id)
            if member.status not in _EG_MEMBER_STATUSES:
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


async def _se_edit(query, *args, **kwargs) -> None:
    try:
        await query.edit_message_text(*args, **kwargs)
    except TelegramError as e:
        if "not modified" not in str(e).lower():
            raise


async def _se_check_membership_and_respond(
    query, student_chat_id: int, first_name: str, username: str | None, context
) -> None:
    existing = await db.se_get_participant(student_chat_id)
    if existing:
        # Re-verify they're still subscribed — remove and re-gate if they left
        if SPECIAL_EVENT_CHANNEL_IDS:
            missing_handles = await _se_get_missing_handles(context.bot, student_chat_id)
            if missing_handles:
                await db.se_remove_participant(student_chat_id)
                channel_list = "\n".join(f"• {h}" for h in missing_handles)
                await _se_edit(
                    query,
                    msg.SE_MUST_JOIN.format(channel_list=channel_list),
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton(msg.BTN_SE_CHECK, callback_data="se_check")]]
                    ),
                )
                return
        await _se_edit(query, msg.SE_ALREADY_PARTICIPATING)
        return

    missing_handles = await _se_get_missing_handles(context.bot, student_chat_id) if SPECIAL_EVENT_CHANNEL_IDS else []

    if missing_handles:
        channel_list = "\n".join(f"• {h}" for h in missing_handles)
        await _se_edit(
            query,
            msg.SE_MUST_JOIN.format(channel_list=channel_list),
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(msg.BTN_SE_CHECK, callback_data="se_check")]]
            ),
        )
        return

    await db.se_add_participant(student_chat_id, first_name, username)
    await _se_edit(query, msg.SE_NOW_PARTICIPATING)


async def _se_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    await _se_check_membership_and_respond(
        query, user.id, user.first_name, user.username, context
    )


async def _se_check_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    await _se_check_membership_and_respond(
        query, user.id, user.first_name, user.username, context
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
    if not application or application["status"] not in ("terms_accepted",):
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


# ---------------------------------------------------------------------------
# Research Seminar — student flow, admin commands
# ---------------------------------------------------------------------------

RS_SLOT_LIMIT = 31

def _rs_phone_keyboard() -> ReplyKeyboardMarkup:
    from telegram import KeyboardButton
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(msg.BTN_RS_SHARE_PHONE, request_contact=True)],
            [msg.BTN_BACK],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


async def _handle_rs(
    update: Update, chat_id: int, context: ContextTypes.DEFAULT_TYPE
) -> None:
    post = await db.rs_get_active_post()
    if not post:
        await update.message.reply_text(msg.RS_NO_POST)
        return

    existing = await db.rs_get_registration(chat_id)
    if existing:
        await update.message.reply_text(msg.RS_ALREADY_REGISTERED)
        return

    count = await db.rs_count_registrations()
    if count >= RS_SLOT_LIMIT:
        await update.message.reply_text(msg.RS_SLOTS_FULL)
        return

    await context.bot.copy_message(
        chat_id=chat_id,
        from_chat_id=post["post_chat_id"],
        message_id=post["post_message_id"],
    )
    await update.message.reply_text(msg.RS_ASK_FULL_NAME, reply_markup=_back_keyboard())
    await db.set_flow(chat_id, "rs")
    await db.set_status(chat_id, "rs_step_name")


async def _handle_rs_name(
    update: Update, chat_id: int, full_name: str, context: ContextTypes.DEFAULT_TYPE
) -> None:
    _rs_state[chat_id] = {"full_name": full_name}
    await db.set_status(chat_id, "rs_step_phone")
    await update.message.reply_text(msg.RS_ASK_PHONE, reply_markup=_rs_phone_keyboard())


async def _handle_rs_phone(
    update: Update, chat_id: int, phone: str, context: ContextTypes.DEFAULT_TYPE
) -> None:
    state = _rs_state.pop(chat_id, {})
    full_name = state.get("full_name", "").strip()

    if not full_name:
        await db.set_status(chat_id, "rs_step_name")
        await update.message.reply_text(msg.RS_ASK_FULL_NAME, reply_markup=_back_keyboard())
        return

    count = await db.rs_count_registrations()
    if count >= RS_SLOT_LIMIT:
        await db.set_flow(chat_id, None)
        await db.set_status(chat_id, None)
        await update.message.reply_text(msg.RS_SLOTS_FULL, reply_markup=_main_keyboard())
        return

    user = await db.get_user(chat_id)
    first_name = user["first_name"] if user else ""
    username = user["username"] if user else None

    await db.rs_save_registration(chat_id, username, first_name, full_name, phone)
    await db.set_flow(chat_id, None)
    await db.set_status(chat_id, None)

    try:
        invite = await context.bot.create_chat_invite_link(
            chat_id=RS_GROUP_CHAT_ID,
            member_limit=1,
        )
        await update.message.reply_text(
            msg.RS_REGISTERED.format(link=invite.invite_link),
            reply_markup=_main_keyboard(),
        )
    except Exception:
        logger.exception("Failed to create RS invite for chat_id=%d", chat_id)
        await update.message.reply_text(
            msg.RS_REGISTERED.format(link="(error generating link — please contact support)"),
            reply_markup=_main_keyboard(),
        )


async def _rs_post_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if update.effective_user.id != PERSON_X_CHAT_ID:
        return
    reply = update.message.reply_to_message
    if not reply:
        await update.message.reply_text(msg.RS_POST_USAGE)
        return
    await db.rs_save_post(reply.chat.id, reply.message_id)
    await update.message.reply_text(msg.RS_POST_SET + "\n\nPrevious registrations have been cleared.")


async def _rs_export_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if update.effective_user.id != PERSON_X_CHAT_ID:
        return
    registrations = await db.rs_get_all_registrations()
    if not registrations:
        await update.message.reply_text(msg.RS_EXPORT_EMPTY)
        return
    lines = ["Research Seminar Registrations\n"]
    for i, r in enumerate(registrations, 1):
        upart = f" (@{r['username']})" if r.get("username") else ""
        lines.append(f"{i}. {r['full_name']}{upart} — {r['phone']}")
    content = "\n".join(lines).encode("utf-8")
    import io
    await update.message.reply_document(
        document=io.BytesIO(content),
        filename="rs_registrations.txt",
    )


# ---------------------------------------------------------------------------
# SAT Program Giveaway — student flow, admin commands, reviewer callbacks
# ---------------------------------------------------------------------------

async def _handle_sat_giveaway(
    update: Update, chat_id: int, context: ContextTypes.DEFAULT_TYPE
) -> None:
    post = await db.sat_get_active_post()
    if not post:
        await update.message.reply_text(msg.SAT_GIVEAWAY_NO_POST)
        return

    entry = await db.sat_get_entry(chat_id)
    if entry and entry["status"] in ("pending", "approved"):
        await update.message.reply_text(msg.SAT_GIVEAWAY_ALREADY_SUBMITTED)
        return

    await context.bot.copy_message(
        chat_id=chat_id,
        from_chat_id=post["post_chat_id"],
        message_id=post["post_message_id"],
    )
    await update.message.reply_text(msg.SAT_GIVEAWAY_PROMPT, reply_markup=_back_keyboard())
    await db.set_flow(chat_id, "sat_giveaway")
    await db.set_status(chat_id, "sat_step_screenshot")


async def _handle_sat_screenshot(
    update: Update,
    chat_id: int,
    file_id: str,
    file_type: str,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    user = await db.get_user(chat_id)
    first_name = user["first_name"] if user else "Unknown"
    username = user["username"] if user else None

    await db.sat_save_entry(chat_id, username, first_name, file_id, file_type)
    await db.set_flow(chat_id, None)
    await db.set_status(chat_id, None)
    await update.message.reply_text(msg.SAT_GIVEAWAY_SUBMITTED, reply_markup=_main_keyboard())

    username_part = f" (@{username})" if username else ""
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(msg.BTN_SAT_APPROVE, callback_data=f"sat_approve:{chat_id}"),
        InlineKeyboardButton(msg.BTN_SAT_REJECT, callback_data=f"sat_reject:{chat_id}"),
    ]])

    for reviewer_id in SAT_MAN_CHAT_ID:
        if file_type == "photo":
            sent = await context.bot.send_photo(
                chat_id=reviewer_id,
                photo=file_id,
                caption=msg.SAT_REVIEWER_ENTRY.format(
                    first_name=first_name, username_part=username_part
                ),
                reply_markup=keyboard,
            )
        else:
            sent = await context.bot.send_document(
                chat_id=reviewer_id,
                document=file_id,
                caption=msg.SAT_REVIEWER_ENTRY.format(
                    first_name=first_name, username_part=username_part
                ),
                reply_markup=keyboard,
            )
        await db.sat_set_entry_reviewer_message(chat_id, sent.message_id)


async def _sat_decision_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE, decision: str
) -> None:
    query = update.callback_query
    await query.answer()

    applicant_chat_id = int(query.data.split(":")[1])
    entry = await db.sat_get_entry(applicant_chat_id)

    if not entry or entry["status"] != "pending":
        await query.answer(msg.SAT_REVIEWER_ALREADY_DECIDED, show_alert=True)
        return

    await db.sat_set_entry_status(applicant_chat_id, decision)

    student_msg = msg.SAT_GIVEAWAY_APPROVED if decision == "approved" else msg.SAT_GIVEAWAY_REJECTED
    reviewer_confirmation = msg.SAT_REVIEWER_ACCEPTED if decision == "approved" else msg.SAT_REVIEWER_REJECTED

    try:
        await context.bot.send_message(chat_id=applicant_chat_id, text=student_msg)
    except Exception:
        logger.exception("Failed to notify SAT giveaway participant chat_id=%d", applicant_chat_id)

    caption = query.message.caption or ""
    await query.edit_message_caption(
        caption=f"{caption}\n\n{reviewer_confirmation}",
        reply_markup=None,
    )


async def _sat_approve_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _sat_decision_callback(update, context, "approved")


async def _sat_reject_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _sat_decision_callback(update, context, "rejected")


async def _sat_webinar_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != PERSON_X_CHAT_ID:
        return
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("📺 Join the webinar", url="https://t.me/freshmanblog"),
    ]])
    chat_ids = await db.get_all_chat_ids()
    sent = failed = 0
    first_error: str | None = None
    for cid in chat_ids:
        try:
            await context.bot.send_message(
                chat_id=cid,
                text=msg.SAT_WEBINAR_REMINDER,
                reply_markup=keyboard,
                parse_mode="HTML",
            )
            sent += 1
        except Exception as e:
            if first_error is None:
                first_error = f"{type(e).__name__}: {e}"
            logger.warning("Webinar remind failed for chat_id=%d: %s", cid, e)
            failed += 1
        await asyncio.sleep(0.05)
    result = msg.SAT_WEBINAR_DONE.format(sent=sent, failed=failed, total=len(chat_ids))
    if first_error:
        result += f"\n\nFirst error: {first_error}"
    await update.message.reply_text(result)


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
    sent = failed = 0
    for cid in chat_ids:
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
    )


async def _sat_post_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != PERSON_X_CHAT_ID:
        return
    reply = update.message.reply_to_message
    if not reply:
        await update.message.reply_text(msg.SAT_POST_USAGE)
        return
    await db.sat_save_post(reply.chat.id, reply.message_id)
    await update.message.reply_text(msg.SAT_POST_SET)


async def _sat_remind_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != PERSON_X_CHAT_ID:
        return
    users = await db.sat_get_users_awaiting_screenshot()
    sent = failed = 0
    for u in users:
        try:
            await context.bot.send_message(
                chat_id=u["chat_id"],
                text=msg.SAT_REMIND_SCREENSHOT,
                parse_mode="HTML",
            )
            sent += 1
        except Exception:
            logger.warning("Failed to remind SAT user chat_id=%d", u["chat_id"])
            failed += 1
    await update.message.reply_text(
        msg.SAT_REMIND_DONE.format(sent=sent, failed=failed, total=len(users))
    )


async def _sat_reroll_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != PERSON_X_CHAT_ID:
        return
    approved = await db.sat_get_all_approved()
    if len(approved) < 2:
        await update.message.reply_text(
            msg.SAT_REROLL_NOT_ENOUGH if approved else msg.SAT_REROLL_NO_ENTRIES
        )
        return
    winners = _random.sample(approved, 2)

    def _fmt(p: dict) -> str:
        upart = f" (@{p['username']})" if p.get("username") else ""
        return f'<a href="tg://user?id={p["chat_id"]}">{p["first_name"]}</a>{upart}'

    await update.message.reply_text(
        msg.SAT_REROLL_RESULT.format(winner1=_fmt(winners[0]), winner2=_fmt(winners[1])),
        parse_mode="HTML",
    )


# ---------------------------------------------------------------------------
# /roll and /reroll — pick a random special event participant (PERSON_X only)
# ---------------------------------------------------------------------------

import random as _random


def _roll_format(participant: dict, header: str) -> str:
    username_part = f" (@{participant['username']})" if participant.get("username") else ""
    return header.format(
        chat_id=participant["student_chat_id"],
        first_name=participant["first_name"],
        username_part=username_part,
    )


def _roll_keyboard(winner_chat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(msg.BTN_CONFIRM_WINNER, callback_data=f"se_confirm:{winner_chat_id}"),
        InlineKeyboardButton(msg.BTN_REROLL_INLINE, callback_data="se_reroll"),
    ]])


async def _roll_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != PERSON_X_CHAT_ID:
        return
    participants = await db.se_get_all_participants()
    if not participants:
        await update.message.reply_text(msg.ROLL_NO_PARTICIPANTS)
        return
    winner = _random.choice(participants)
    _roll_state["last_id"] = winner["student_chat_id"]
    await update.message.reply_text(
        _roll_format(winner, msg.ROLL_RESULT),
        parse_mode="HTML",
        reply_markup=_roll_keyboard(winner["student_chat_id"]),
    )


async def _reroll_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != PERSON_X_CHAT_ID:
        return
    if _roll_state["last_id"] is None:
        await update.message.reply_text(msg.ROLL_USE_FIRST)
        return
    participants = await db.se_get_all_participants()
    pool = [p for p in participants if p["student_chat_id"] != _roll_state["last_id"]]
    if not pool:
        await update.message.reply_text(msg.ROLL_ONLY_ONE)
        return
    winner = _random.choice(pool)
    _roll_state["last_id"] = winner["student_chat_id"]
    await update.message.reply_text(
        _roll_format(winner, msg.REROLL_RESULT),
        parse_mode="HTML",
        reply_markup=_roll_keyboard(winner["student_chat_id"]),
    )


async def _roll_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if update.effective_user.id != PERSON_X_CHAT_ID:
        return
    winner_chat_id = int(query.data.split(":")[1])
    participants = await db.se_get_all_participants()
    sent = failed = 0
    for p in participants:
        cid = p["student_chat_id"]
        text = msg.ROLL_WINNER_NOTIFY if cid == winner_chat_id else msg.ROLL_LOSER_NOTIFY
        try:
            await context.bot.send_message(chat_id=cid, text=text)
            sent += 1
        except Exception:
            logger.warning("Failed to notify participant chat_id=%d", cid)
            failed += 1
    _roll_state["last_id"] = None
    await query.edit_message_text(
        msg.ROLL_CONFIRMED.format(sent=sent, failed=failed),
    )


async def _se_reroll_inline_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if update.effective_user.id != PERSON_X_CHAT_ID:
        return
    if _roll_state["last_id"] is None:
        await query.edit_message_text(msg.ROLL_USE_FIRST)
        return
    participants = await db.se_get_all_participants()
    pool = [p for p in participants if p["student_chat_id"] != _roll_state["last_id"]]
    if not pool:
        await query.edit_message_text(msg.ROLL_ONLY_ONE)
        return
    winner = _random.choice(pool)
    _roll_state["last_id"] = winner["student_chat_id"]
    await query.edit_message_text(
        _roll_format(winner, msg.REROLL_RESULT),
        parse_mode="HTML",
        reply_markup=_roll_keyboard(winner["student_chat_id"]),
    )


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

_Q_ADMIN_IDS: frozenset[int] = frozenset({PERSON_X_CHAT_ID, PERSON_Z_CHAT_ID})

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
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .build()
    )

    _private = filters.ChatType.PRIVATE
    app.add_handler(CommandHandler("start", start, filters=_private))
    app.add_handler(CommandHandler("cancel", cancel, filters=_private))
    app.add_handler(CommandHandler("clarify", clarify_command, filters=_private))
    app.add_handler(CommandHandler("event", _eg_admin_event_command, filters=_private))
    app.add_handler(CommandHandler("status", _eg_admin_status, filters=_private))
    app.add_handler(CommandHandler("clearevent", _eg_admin_clearevent, filters=_private))
    app.add_handler(CommandHandler("help", _eg_admin_help, filters=_private))
    app.add_handler(CommandHandler("broadcastkeyboard", _broadcast_keyboard_command, filters=_private))
    app.add_handler(CommandHandler("stats", _stats_command, filters=_private))
    app.add_handler(CommandHandler("export_db", _export_db_command, filters=_private))
    app.add_handler(CommandHandler("setvideo", _video_admin_command, filters=_private))
    app.add_handler(CommandHandler("sevent", _sevent_command, filters=_private))
    app.add_handler(CommandHandler("sparticipants", _sevent_participants_command, filters=_private))
    app.add_handler(CommandHandler("pingexperts", _ping_experts_command, filters=_private))
    app.add_handler(CommandHandler("roll", _roll_command, filters=_private))
    app.add_handler(CommandHandler("reroll", _reroll_command, filters=_private))
    app.add_handler(CommandHandler("followup", followup_command, filters=_private))
    app.add_handler(CommandHandler("santix", _santix_command, filters=_private))
    app.add_handler(CommandHandler("answered", _q_answered_command, filters=_private))
    app.add_handler(CommandHandler("clear_adv", _clear_adv_command, filters=_private))
    app.add_handler(CommandHandler("unanswered", _q_unanswered_command, filters=_private))
    app.add_handler(CommandHandler("ae_list", _ae_list_command, filters=_private))
    app.add_handler(CommandHandler("ae_set_terms", _ae_set_terms_command, filters=_private))
    app.add_handler(CommandHandler("ae_set_payment", _ae_set_payment_command, filters=_private))
    app.add_handler(CommandHandler("ae_remind", _ae_remind_command, filters=_private))
    app.add_handler(CallbackQueryHandler(_ae_terms_accept_callback, pattern="^ae_terms_accept:"))
    app.add_handler(CallbackQueryHandler(_ae_payment_made_callback, pattern="^ae_payment_made:"))
    app.add_handler(CallbackQueryHandler(_ae_payment_confirm_callback, pattern="^ae_payment_confirm:"))
    app.add_handler(CallbackQueryHandler(_ae_payment_reject_callback, pattern="^ae_payment_reject:"))
    app.add_handler(CommandHandler("sat_webinar", _sat_webinar_command, filters=_private))
    app.add_handler(CommandHandler("sat_post", _sat_post_command, filters=_private))
    app.add_handler(CommandHandler("sat_remind", _sat_remind_command, filters=_private))
    app.add_handler(CommandHandler("sat_reroll", _sat_reroll_command, filters=_private))
    app.add_handler(CommandHandler("rs_post", _rs_post_command, filters=_private))
    app.add_handler(CommandHandler("rs_export", _rs_export_command, filters=_private))
    app.add_handler(CallbackQueryHandler(_sat_approve_callback, pattern="^sat_approve:"))
    app.add_handler(CallbackQueryHandler(_sat_reject_callback, pattern="^sat_reject:"))
    app.add_handler(CallbackQueryHandler(_eg_check_membership_callback, pattern="^check_membership$"))
    app.add_handler(CallbackQueryHandler(_se_join_callback, pattern="^se_join$"))
    app.add_handler(CallbackQueryHandler(_se_check_callback, pattern="^se_check$"))
    app.add_handler(CallbackQueryHandler(_roll_confirm_callback, pattern="^se_confirm:"))
    app.add_handler(CallbackQueryHandler(_se_reroll_inline_callback, pattern="^se_reroll$"))
    app.add_handler(CallbackQueryHandler(_video_admin_program_callback, pattern="^setvideo_"))
    app.add_handler(CallbackQueryHandler(_q_program_callback, pattern="^qp:"))
    app.add_handler(CallbackQueryHandler(_q_date_callback, pattern="^qd:"))
    app.add_handler(CallbackQueryHandler(_podcast_check_callback, pattern="^podcast_check$"))
    app.add_handler(CallbackQueryHandler(_ae_apply_now_callback, pattern="^ae_apply_now$"))
    app.add_handler(CallbackQueryHandler(_ae_list_callback, pattern="^ae_list$"))
    app.add_handler(CallbackQueryHandler(_ae_view_callback, pattern="^ae_view:"))
    app.add_handler(CallbackQueryHandler(_ae_accept_callback, pattern="^ae_accept:"))
    app.add_handler(CallbackQueryHandler(_ae_reject_callback, pattern="^ae_reject:"))
    app.add_handler(MessageHandler(_private & filters.CONTACT, handle_message))
    app.add_handler(MessageHandler(_private & ~filters.COMMAND, handle_message))
    app.add_handler(ChatJoinRequestHandler(_eg_join_request_handler))

    return app
