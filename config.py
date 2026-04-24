import os
from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


TELEGRAM_BOT_TOKEN: str = _require("TELEGRAM_BOT_TOKEN")

PERSON_X_CHAT_ID: int = int(_require("PERSON_X_CHAT_ID"))
PERSON_Y_CHAT_ID: int = int(_require("PERSON_Y_CHAT_ID"))

GOOGLE_SERVICE_ACCOUNT_FILE: str = _require("GOOGLE_SERVICE_ACCOUNT_FILE")
GOOGLE_CALENDAR_ID: str = _require("GOOGLE_CALENDAR_ID")
GOOGLE_BOOKING_URL: str = _require("GOOGLE_BOOKING_URL")
GOOGLE_WEBHOOK_TOKEN: str = _require("GOOGLE_WEBHOOK_TOKEN")

WEBHOOK_HOST: str = _require("WEBHOOK_HOST")
WEBHOOK_PORT: int = int(os.getenv("WEBHOOK_PORT", "8000"))
