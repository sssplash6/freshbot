import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from functools import partial

from fastapi import FastAPI, Header, HTTPException, Request
from google.oauth2 import service_account
from googleapiclient.discovery import build
from telegram import Bot

import database as db
from config import (
    GOOGLE_CALENDAR_ID,
    GOOGLE_SERVICE_ACCOUNT_FILE,
    GOOGLE_WEBHOOK_TOKEN,
    WEBHOOK_HOST,
)
from scheduler import schedule_meeting_reminders

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

# Track already-processed event IDs to avoid double-scheduling on repeated notifications
_processed_event_ids: set[str] = set()


# ---------------------------------------------------------------------------
# Google Calendar API helpers (sync wrapped for async use)
# ---------------------------------------------------------------------------

def _build_service():
    # Prefer JSON env var (used on Render/Railway), fall back to local file
    raw_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if raw_json:
        info = json.loads(raw_json)
        credentials = service_account.Credentials.from_service_account_info(
            info, scopes=SCOPES
        )
    else:
        credentials = service_account.Credentials.from_service_account_file(
            GOOGLE_SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
    return build("calendar", "v3", credentials=credentials, cache_discovery=False)


async def _run_sync(func, *args, **kwargs):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(func, *args, **kwargs))


# ---------------------------------------------------------------------------
# Watch registration
# ---------------------------------------------------------------------------

async def setup_calendar_watch() -> None:
    """
    Register a Google Calendar push notification channel on startup.
    Google will POST to /webhook/google-calendar when events change.
    Watches expire (max ~7 days); re-registering on restart keeps them fresh.
    """
    channel_id = str(uuid.uuid4())
    address = f"{WEBHOOK_HOST}/webhook/google-calendar"

    def _watch():
        service = _build_service()
        return service.events().watch(
            calendarId=GOOGLE_CALENDAR_ID,
            body={
                "id": channel_id,
                "type": "web_hook",
                "address": address,
                "token": GOOGLE_WEBHOOK_TOKEN,
            },
        ).execute()

    try:
        result = await _run_sync(_watch)
        expiry_ms = result.get("expiration", 0)
        expiry = datetime.fromtimestamp(int(expiry_ms) / 1000, tz=timezone.utc)
        logger.info(
            "Google Calendar watch registered. Channel: %s, expires: %s", channel_id, expiry
        )
    except Exception:
        logger.exception(
            "Failed to register Google Calendar watch — webhook notifications will not work."
        )


# ---------------------------------------------------------------------------
# Username extraction
# ---------------------------------------------------------------------------

def _extract_telegram_username(description: str) -> str | None:
    """
    Parse the event description for the Telegram username intake answer.

    Google Calendar Appointment Scheduling puts intake form answers in the
    event description. The format is typically:

        What is your Telegram username? (e.g. @username): @johndoe

    We look for any line containing "telegram" and take the value after the
    first colon on that line.
    """
    if not description:
        return None
    for line in description.splitlines():
        if "telegram" in line.lower() and ":" in line:
            answer = line.split(":", 1)[1].strip()
            if answer:
                return answer
    return None


# ---------------------------------------------------------------------------
# Booking handler
# ---------------------------------------------------------------------------

async def _handle_new_booking(bot: Bot, event: dict) -> None:
    event_id = event.get("id", "")
    if not event_id:
        return

    # Skip if already handled in this process lifetime
    if event_id in _processed_event_ids:
        return

    # Skip if already matched in DB (survives restarts)
    existing = await db.get_user_by_event_id(event_id)
    if existing:
        _processed_event_ids.add(event_id)
        return

    description = event.get("description", "")
    raw_username = _extract_telegram_username(description)

    if not raw_username:
        logger.warning("Booking event %s has no Telegram username in description.", event_id)
        _processed_event_ids.add(event_id)
        return

    normalized = raw_username.lstrip("@").lower().strip()
    user = await db.get_user_by_username(normalized)

    if not user:
        logger.warning(
            "No awaiting_match user found for username '%s' (event %s).", normalized, event_id
        )
        _processed_event_ids.add(event_id)
        return

    chat_id = user["chat_id"]

    start_time_raw = event.get("start", {}).get("dateTime", "")
    if not start_time_raw:
        logger.warning("Event %s has no start dateTime — cannot schedule reminders.", event_id)
        _processed_event_ids.add(event_id)
        return

    try:
        meeting_time = datetime.fromisoformat(start_time_raw)
        if meeting_time.tzinfo is None:
            meeting_time = meeting_time.replace(tzinfo=timezone.utc)
    except ValueError:
        logger.warning(
            "Unparseable start time '%s' for event %s.", start_time_raw, event_id
        )
        _processed_event_ids.add(event_id)
        return

    await db.set_meeting_info(chat_id, meeting_time.isoformat(), event_id)
    logger.info(
        "Matched booking event %s → chat_id=%d, meeting at %s.", event_id, chat_id, meeting_time
    )

    await schedule_meeting_reminders(bot, chat_id, meeting_time)
    _processed_event_ids.add(event_id)


# ---------------------------------------------------------------------------
# FastAPI app factory
# ---------------------------------------------------------------------------

def get_fastapi_app(bot: Bot) -> FastAPI:
    app = FastAPI()

    @app.post("/webhook/google-calendar")
    async def google_calendar_webhook(
        request: Request,
        x_goog_channel_token: str = Header(default=""),
        x_goog_resource_state: str = Header(default=""),
    ):
        # Verify our token
        if x_goog_channel_token != GOOGLE_WEBHOOK_TOKEN:
            logger.warning("Invalid Google Calendar webhook token — rejected.")
            raise HTTPException(status_code=403, detail="Invalid token")

        # Initial sync handshake — Google sends this immediately after watch registration
        if x_goog_resource_state == "sync":
            logger.info("Google Calendar sync handshake received.")
            return {"status": "ok"}

        if x_goog_resource_state != "exists":
            return {"status": "ignored"}

        # Fetch events updated in the last 5 minutes to catch newly created bookings
        now = datetime.now(timezone.utc)
        updated_min = (now - timedelta(minutes=5)).isoformat()

        def _list_events():
            service = _build_service()
            return service.events().list(
                calendarId=GOOGLE_CALENDAR_ID,
                updatedMin=updated_min,
                singleEvents=True,
                orderBy="updated",
            ).execute()

        try:
            result = await _run_sync(_list_events)
        except Exception:
            logger.exception("Failed to list Google Calendar events.")
            raise HTTPException(status_code=500, detail="Calendar API error")

        events = result.get("items", [])
        for event in events:
            if event.get("status") == "confirmed":
                await _handle_new_booking(bot, event)

        return {"status": "ok"}

    return app
