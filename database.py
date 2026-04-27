import aiosqlite
from datetime import datetime, timezone

DB_PATH = "bot.db"


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                chat_id             INTEGER PRIMARY KEY,
                first_name          TEXT,
                username            TEXT,
                program             TEXT,
                flow                TEXT,
                status              TEXT,
                meeting_time        TEXT,
                event_id            TEXT,
                created_at          TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_jobs (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id   INTEGER,
                job_type  TEXT,
                run_at    TEXT,
                sent      INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                user_chat_id      INTEGER,
                program           TEXT,
                question_text     TEXT,
                expert_chat_id    INTEGER,
                expert_message_id INTEGER,
                status            TEXT DEFAULT 'pending',
                created_at        TEXT
            )
        """)
        await db.commit()


# ---------------------------------------------------------------------------
# User operations
# ---------------------------------------------------------------------------

async def upsert_user(chat_id: int, first_name: str, username: str | None) -> None:
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (chat_id, first_name, username, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                first_name = excluded.first_name,
                username   = excluded.username
        """, (chat_id, first_name, username, now))
        await db.commit()


async def set_program(chat_id: int, program: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET program = ? WHERE chat_id = ?",
            (program, chat_id),
        )
        await db.commit()


async def set_flow(chat_id: int, flow: str | None) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET flow = ? WHERE chat_id = ?",
            (flow, chat_id),
        )
        await db.commit()


async def set_status(chat_id: int, status: str | None) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET status = ? WHERE chat_id = ?",
            (status, chat_id),
        )
        await db.commit()


async def set_meeting_info(
    chat_id: int, meeting_time: str, event_id: str
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """UPDATE users
               SET meeting_time = ?, event_id = ?, status = 'matched'
               WHERE chat_id = ?""",
            (meeting_time, event_id, chat_id),
        )
        await db.commit()


async def get_user(chat_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE chat_id = ?", (chat_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_user_by_event_id(event_id: str) -> dict | None:
    """Return a user that already has this Google Calendar event_id stored (already matched)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE event_id = ?", (event_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_user_by_username(username: str) -> dict | None:
    """Match by normalized username (no @, lowercase) with status = 'awaiting_match'."""
    normalized = username.lstrip("@").lower().strip()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT * FROM users
               WHERE LOWER(username) = ? AND status = 'awaiting_match'""",
            (normalized,),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def reset_user(chat_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """UPDATE users
               SET program = NULL, flow = NULL, status = NULL,
                   meeting_time = NULL, event_id = NULL
               WHERE chat_id = ?""",
            (chat_id,),
        )
        await db.commit()


# ---------------------------------------------------------------------------
# Scheduled job operations
# ---------------------------------------------------------------------------

async def save_job(chat_id: int, job_type: str, run_at: datetime) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO scheduled_jobs (chat_id, job_type, run_at) VALUES (?, ?, ?)",
            (chat_id, job_type, run_at.isoformat()),
        )
        await db.commit()
        return cursor.lastrowid


async def mark_job_sent(job_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE scheduled_jobs SET sent = 1 WHERE id = ?",
            (job_id,),
        )
        await db.commit()


async def get_pending_jobs() -> list[dict]:
    """Return all unsent jobs scheduled to run in the future."""
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM scheduled_jobs WHERE sent = 0 AND run_at > ?",
            (now,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Question operations
# ---------------------------------------------------------------------------

async def save_question(user_chat_id: int, program: str, question_text: str) -> int:
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO questions (user_chat_id, program, question_text, created_at)
               VALUES (?, ?, ?, ?)""",
            (user_chat_id, program, question_text, now),
        )
        await db.commit()
        return cursor.lastrowid


async def set_question_expert_message(
    question_id: int, expert_chat_id: int, expert_message_id: int
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """UPDATE questions SET expert_chat_id = ?, expert_message_id = ?
               WHERE id = ?""",
            (expert_chat_id, expert_message_id, question_id),
        )
        await db.commit()


async def get_question_by_expert_message(
    expert_chat_id: int, expert_message_id: int
) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT * FROM questions
               WHERE expert_chat_id = ? AND expert_message_id = ? AND status = 'pending'""",
            (expert_chat_id, expert_message_id),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_question_by_expert_message_any_status(
    expert_chat_id: int, expert_message_id: int
) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT * FROM questions
               WHERE expert_chat_id = ? AND expert_message_id = ?""",
            (expert_chat_id, expert_message_id),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def mark_question_answered(question_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE questions SET status = 'answered' WHERE id = ?",
            (question_id,),
        )
        await db.commit()


async def mark_sibling_questions_answered(user_chat_id: int, question_text: str) -> None:
    """Mark all other pending records for the same question (sent to multiple experts) as answered."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """UPDATE questions SET status = 'answered'
               WHERE user_chat_id = ? AND question_text = ? AND status = 'pending'""",
            (user_chat_id, question_text),
        )
        await db.commit()
