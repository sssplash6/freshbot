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
PERSON_Z_CHAT_ID: int = int(_require("PERSON_Z_CHAT_ID"))
VALERA_CHAT_ID: int | None = int(v) if (v := os.getenv("VALERA_CHAT_ID", "").strip()) else None
ADV_ENGLISH_REVIEWER_CHAT_ID: int = int(_require("ADV_ENGLISH_REVIEWER_CHAT_ID"))
AE_GROUP_CHAT_ID: int = int(_require("AE_GROUP_CHAT_ID"))
RS_GROUP_CHAT_ID: int = int(_require("RS_GROUP_CHAT_ID"))

# Expert chat IDs for each program's question routing (comma-separated for multiple)
SAT_MAN_CHAT_ID: list[int] = _require_int_list("SAT_MAN_CHAT_ID")
AP_MAN_CHAT_ID: list[int] = _require_int_list("AP_MAN_CHAT_ID")
FS_MAN_CHAT_ID: list[int] = _require_int_list("FS_MAN_CHAT_ID")
ADV_PLACEMENT_MAN_CHAT_ID: list[int] = _require_int_list("ADV_PLACEMENT_MAN_CHAT_ID")
MS_MAN_CHAT_ID: list[int] = _require_int_list("MS_MAN_CHAT_ID")
IMKON_MAN_CHAT_ID: list[int] = _require_int_list("IMKON_MAN_CHAT_ID")
GENERAL_MAN_CHAT_ID: list[int] = _require_int_list("GENERAL_MAN_CHAT_ID")
RI_MAN_CHAT_ID: list[int] = _require_int_list("RI_MAN_CHAT_ID")

SAT_BOOKING_URL: str = _require("SAT_BOOKING_URL")

WEBSITE_URL_ADV_PLACEMENT: str = _require("WEBSITE_URL_ADV_PLACEMENT")
WEBSITE_URL_ADMISSIONS: str = _require("WEBSITE_URL_ADMISSIONS")
WEBSITE_URL_FULL_SUPPORT: str = _require("WEBSITE_URL_FULL_SUPPORT")
WEBSITE_URL_MASTERS: str = _require("WEBSITE_URL_MASTERS")
WEBSITE_URL_IMKON: str = _require("WEBSITE_URL_IMKON")
WEBSITE_URL_RESEARCH_INSTITUTE: str = _require("WEBSITE_URL_RESEARCH_INSTITUTE")

WEBHOOK_HOST: str = _require("WEBHOOK_HOST")
WEBHOOK_PORT: int = int(os.getenv("WEBHOOK_PORT", "8000"))


def _require_str_list(name: str) -> list[str]:
    return [x.strip() for x in _require(name).split(",") if x.strip()]


def _optional_int_list(name: str) -> list[int]:
    value = os.getenv(name, "").strip()
    return [int(x.strip()) for x in value.split(",") if x.strip()]


def _optional_str_list(name: str) -> list[str]:
    value = os.getenv(name, "").strip()
    return [x.strip() for x in value.split(",") if x.strip()]


# Event gate
REQUIRED_GROUP_IDS: list[int] = _require_int_list("REQUIRED_GROUP_IDS")
REQUIRED_GROUP_INVITES: list[str] = _require_str_list("REQUIRED_GROUP_INVITES")
REQUIRED_CHANNEL_IDS: list[int] = _require_int_list("REQUIRED_CHANNEL_IDS")
REQUIRED_CHANNEL_INVITES: list[str] = _require_str_list("REQUIRED_CHANNEL_INVITES")
LINK_EXPIRY_HOURS: int = int(os.getenv("LINK_EXPIRY_HOURS", "24"))

SPECIAL_EVENT_CHANNEL_IDS: list[int] = _optional_int_list("SPECIAL_EVENT_CHANNEL_IDS")
SPECIAL_EVENT_CHANNEL_HANDLES: list[str] = _optional_str_list("SPECIAL_EVENT_CHANNEL_HANDLES")

PODCAST_CHANNEL_IDS: list[int] = _optional_int_list("PODCAST_CHANNEL_IDS")
PODCAST_CHANNEL_HANDLES: list[str] = _optional_str_list("PODCAST_CHANNEL_HANDLES")
PODCAST_YOUTUBE_URL: str = os.getenv("PODCAST_YOUTUBE_URL", "")

HKU_GROUP_CHAT_ID: int | None = int(v) if (v := os.getenv("HKU_GROUP_CHAT_ID", "").strip()) else None
FRESHMANBLOG_CHANNEL_ID: int | None = int(v) if (v := os.getenv("FRESHMANBLOG_CHANNEL_ID", "").strip()) else None
