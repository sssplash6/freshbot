import os
from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _require_int_list(name: str) -> list[int]:
    return [int(x.strip()) for x in _require(name).split(",") if x.strip()]


TELEGRAM_BOT_TOKEN: str = _require("TELEGRAM_BOT_TOKEN")

PERSON_X_CHAT_ID: int = int(_require("PERSON_X_CHAT_ID"))
PERSON_Y_CHAT_ID: int = int(_require("PERSON_Y_CHAT_ID"))

# Expert chat IDs for each program's question routing (comma-separated for multiple)
SAT_MAN_CHAT_ID: list[int] = _require_int_list("SAT_MAN_CHAT_ID")
AP_MAN_CHAT_ID: list[int] = _require_int_list("AP_MAN_CHAT_ID")
FS_MAN_CHAT_ID: list[int] = _require_int_list("FS_MAN_CHAT_ID")

GOOGLE_SERVICE_ACCOUNT_FILE: str = _require("GOOGLE_SERVICE_ACCOUNT_FILE")
GOOGLE_CALENDAR_ID: str = _require("GOOGLE_CALENDAR_ID")
GOOGLE_BOOKING_URL_SAT: str = _require("GOOGLE_BOOKING_URL_SAT")
GOOGLE_BOOKING_URL_AP: str = _require("GOOGLE_BOOKING_URL_AP")
GOOGLE_BOOKING_URL_FS: str = _require("GOOGLE_BOOKING_URL_FS")
GOOGLE_WEBHOOK_TOKEN: str = _require("GOOGLE_WEBHOOK_TOKEN")

WEBHOOK_HOST: str = _require("WEBHOOK_HOST")
WEBHOOK_PORT: int = int(os.getenv("WEBHOOK_PORT", "8000"))


def _require_str_list(name: str) -> list[str]:
    return [x.strip() for x in _require(name).split(",") if x.strip()]


# Event gate
REQUIRED_GROUP_IDS: list[int] = _require_int_list("REQUIRED_GROUP_IDS")
REQUIRED_GROUP_INVITES: list[str] = _require_str_list("REQUIRED_GROUP_INVITES")
REQUIRED_CHANNEL_IDS: list[int] = _require_int_list("REQUIRED_CHANNEL_IDS")
REQUIRED_CHANNEL_INVITES: list[str] = _require_str_list("REQUIRED_CHANNEL_INVITES")
EVENT_GROUP_ID: int = int(_require("EVENT_GROUP_ID"))
LINK_EXPIRY_HOURS: int = int(os.getenv("LINK_EXPIRY_HOURS", "24"))
