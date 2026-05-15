import os

import aiosqlite
from datetime import datetime, timezone

DB_PATH = os.environ.get("DB_PATH", "/tmp/bot.db")


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
        await db.execute("""
            CREATE TABLE IF NOT EXISTS eg_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status TEXT NOT NULL,
                event_group_id INTEGER,
                post_chat_id INTEGER,
                post_message_id INTEGER,
                post_text TEXT,
                created_at TEXT NOT NULL
            )
        """)
        # Add event_group_id column to existing deployments that predate this field
        try:
            await db.execute("ALTER TABLE eg_events ADD COLUMN event_group_id INTEGER")
            await db.commit()
        except Exception:
            pass
        # Add answer_text column to existing deployments that predate this field
        try:
            await db.execute("ALTER TABLE questions ADD COLUMN answer_text TEXT")
            await db.commit()
        except Exception:
            pass
        # Add thread_id for conversation chain tracking
        try:
            await db.execute("ALTER TABLE questions ADD COLUMN thread_id INTEGER")
            await db.commit()
        except Exception:
            pass
        await db.execute("""
            CREATE TABLE IF NOT EXISTS eg_issued_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL,
                student_chat_id INTEGER NOT NULL,
                invite_link TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (event_id) REFERENCES eg_events(id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS eg_join_approvals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL,
                student_chat_id INTEGER NOT NULL,
                approved_at TEXT NOT NULL,
                FOREIGN KEY (event_id) REFERENCES eg_events(id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS program_videos (
                program    TEXT PRIMARY KEY,
                file_id    TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS special_event_posts (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                post_chat_id    INTEGER NOT NULL,
                post_message_id INTEGER NOT NULL,
                is_active       INTEGER NOT NULL DEFAULT 1,
                created_at      TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS special_event_participants (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                student_chat_id INTEGER NOT NULL UNIQUE,
                first_name      TEXT NOT NULL,
                username        TEXT,
                participated_at TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS adv_english_applications (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id             INTEGER NOT NULL UNIQUE,
                username            TEXT,
                full_name           TEXT NOT NULL,
                video_file_id       TEXT,
                video_type          TEXT,
                ielts               TEXT NOT NULL,
                sat_score           TEXT,
                why_adv_english     TEXT NOT NULL,
                perspective_answer  TEXT NOT NULL,
                resources_answer    TEXT NOT NULL,
                status              TEXT NOT NULL DEFAULT 'pending',
                reviewer_message_id INTEGER,
                created_at          TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bot_settings (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sat_giveaway_posts (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                post_chat_id    INTEGER NOT NULL,
                post_message_id INTEGER NOT NULL,
                is_active       INTEGER NOT NULL DEFAULT 1,
                created_at      TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sat_giveaway_entries (
                id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id              INTEGER NOT NULL UNIQUE,
                username             TEXT,
                first_name           TEXT NOT NULL,
                screenshot_file_id   TEXT NOT NULL,
                screenshot_file_type TEXT NOT NULL DEFAULT 'photo',
                status               TEXT NOT NULL DEFAULT 'pending',
                reviewer_message_id  INTEGER,
                created_at           TEXT NOT NULL
            )
        """)
        for _col in [
            "ALTER TABLE adv_english_applications ADD COLUMN video_file_id TEXT",
            "ALTER TABLE adv_english_applications ADD COLUMN video_type TEXT",
            "ALTER TABLE adv_english_applications ADD COLUMN sat_score TEXT",
            "ALTER TABLE adv_english_applications ADD COLUMN ielts_file_type TEXT",
        ]:
            try:
                await db.execute(_col)
                await db.commit()
            except Exception:
                pass
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

async def save_question(
    user_chat_id: int, program: str, question_text: str, thread_id: int | None = None
) -> int:
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO questions (user_chat_id, program, question_text, created_at, thread_id)
               VALUES (?, ?, ?, ?, ?)""",
            (user_chat_id, program, question_text, now, thread_id),
        )
        await db.commit()
        question_id = cursor.lastrowid
        if thread_id is None:
            await db.execute("UPDATE questions SET thread_id = ? WHERE id = ?", (question_id, question_id))
            await db.commit()
        return question_id


async def get_thread(thread_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM questions WHERE thread_id = ? ORDER BY created_at ASC",
            (thread_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


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


async def append_clarification(question_id: int, clarification: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT answer_text FROM questions WHERE id = ?", (question_id,)
        ) as cursor:
            row = await cursor.fetchone()
        existing = (row[0] or "") if row else ""
        updated = f"{existing}\n\n📝 Clarification:\n{clarification}".strip()
        await db.execute(
            "UPDATE questions SET answer_text = ? WHERE id = ?",
            (updated, question_id),
        )
        await db.commit()


async def mark_question_answered(question_id: int, answer_text: str | None = None) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE questions SET status = 'answered', answer_text = ? WHERE id = ?",
            (answer_text, question_id),
        )
        await db.commit()


async def get_last_question(user_chat_id: int) -> dict | None:
    """Return the most recent question from this user regardless of status."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM questions WHERE user_chat_id = ? ORDER BY id DESC LIMIT 1",
            (user_chat_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_last_answered_question(user_chat_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT * FROM questions
               WHERE user_chat_id = ? AND status = 'answered'
               ORDER BY id DESC LIMIT 1""",
            (user_chat_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_questions_filtered(
    status: str,
    program: str | None = None,
    days: int | None = None,
    offset: int = 0,
    limit: int = 5,
) -> tuple[list[dict], int]:
    conditions = ["q.status = ?"]
    params: list = [status]

    if program:
        conditions.append("q.program = ?")
        params.append(program)
    if days:
        conditions.append("q.created_at >= datetime('now', ?)")
        params.append(f"-{days} days")

    where = " AND ".join(conditions)

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            f"SELECT COUNT(*) FROM questions q WHERE {where}", params
        ) as cur:
            total = (await cur.fetchone())[0]

        async with db.execute(
            f"""SELECT q.*, u.first_name, u.username
                FROM questions q
                LEFT JOIN users u ON q.user_chat_id = u.chat_id
                WHERE {where}
                ORDER BY q.created_at DESC
                LIMIT ? OFFSET ?""",
            params + [limit, offset],
        ) as cur:
            rows = await cur.fetchall()

    return [dict(r) for r in rows], total


async def mark_sibling_questions_answered(user_chat_id: int, question_text: str) -> None:
    """Mark all other pending records for the same question (sent to multiple experts) as answered."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """UPDATE questions SET status = 'answered'
               WHERE user_chat_id = ? AND question_text = ? AND status = 'pending'""",
            (user_chat_id, question_text),
        )
        await db.commit()


# ---------------------------------------------------------------------------
# Event gate operations
# ---------------------------------------------------------------------------

async def eg_save_event(
    event_group_id: int,
    post_chat_id: int | None,
    post_message_id: int | None,
    post_text: str | None,
) -> int:
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE eg_events SET status = 'inactive' WHERE status = 'active'")
        cursor = await db.execute(
            "INSERT INTO eg_events "
            "(status, event_group_id, post_chat_id, post_message_id, post_text, created_at) "
            "VALUES ('active', ?, ?, ?, ?, ?)",
            (event_group_id, post_chat_id, post_message_id, post_text, now),
        )
        event_id = cursor.lastrowid
        await db.commit()
    return event_id


async def eg_get_active_event() -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM eg_events WHERE status = 'active' ORDER BY id DESC LIMIT 1"
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def eg_deactivate_event() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE eg_events SET status = 'inactive' WHERE status = 'active'")
        await db.commit()


async def eg_store_issued_link(
    event_id: int,
    student_chat_id: int,
    invite_link: str,
    expires_at: str,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO eg_issued_links "
            "(event_id, student_chat_id, invite_link, expires_at, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (event_id, student_chat_id, invite_link, expires_at, now),
        )
        await db.commit()


async def eg_log_join_approval(event_id: int, student_chat_id: int) -> None:
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO eg_join_approvals (event_id, student_chat_id, approved_at) "
            "VALUES (?, ?, ?)",
            (event_id, student_chat_id, now),
        )
        await db.commit()


async def eg_get_issued_link(event_id: int, student_chat_id: int) -> dict | None:
    """Return the most recent non-expired link for this user+event, or None."""
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT * FROM eg_issued_links
               WHERE event_id = ? AND student_chat_id = ? AND expires_at > ?
               ORDER BY id DESC LIMIT 1""",
            (event_id, student_chat_id, now),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def eg_count_issued_links(event_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM eg_issued_links WHERE event_id = ?", (event_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0]


async def eg_count_join_approvals(event_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM eg_join_approvals WHERE event_id = ?", (event_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0]


async def upsert_program_video(program: str, file_id: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO program_videos (program, file_id, created_at)
            VALUES (?, ?, ?)
            ON CONFLICT(program) DO UPDATE SET
                file_id    = excluded.file_id,
                created_at = excluded.created_at
        """, (program, file_id, now))
        await db.commit()


async def get_program_video(program: str) -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT file_id FROM program_videos WHERE program = ?", (program,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def get_stats() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        async def scalar(query, params=()):
            async with db.execute(query, params) as cur:
                row = await cur.fetchone()
                return row[0] if row else 0

        async def rows(query, params=()):
            async with db.execute(query, params) as cur:
                return await cur.fetchall()

        total_users       = await scalar("SELECT COUNT(*) FROM users")
        active_users_7d   = await scalar(
            "SELECT COUNT(*) FROM users WHERE created_at >= datetime('now', '-7 days')"
        )
        users_in_flow     = await scalar(
            "SELECT COUNT(*) FROM users WHERE flow IS NOT NULL"
        )

        total_questions   = await scalar("SELECT COUNT(*) FROM questions")
        pending_questions = await scalar("SELECT COUNT(*) FROM questions WHERE status = 'pending'")
        answered_questions = await scalar("SELECT COUNT(*) FROM questions WHERE status = 'answered'")

        questions_by_program = await rows(
            "SELECT program, COUNT(*) FROM questions GROUP BY program ORDER BY COUNT(*) DESC"
        )

        pending_jobs      = await scalar("SELECT COUNT(*) FROM scheduled_jobs WHERE sent = 0")

        active_event      = await scalar("SELECT COUNT(*) FROM eg_events WHERE status = 'active'")
        total_links       = await scalar("SELECT COUNT(*) FROM eg_issued_links")
        total_approvals   = await scalar("SELECT COUNT(*) FROM eg_join_approvals")

        videos_set        = await rows("SELECT program FROM program_videos")

        ae_total     = await scalar("SELECT COUNT(*) FROM adv_english_applications")
        ae_pending   = await scalar("SELECT COUNT(*) FROM adv_english_applications WHERE status = 'pending'")
        ae_accepted  = await scalar("SELECT COUNT(*) FROM adv_english_applications WHERE status = 'accepted'")
        ae_rejected  = await scalar("SELECT COUNT(*) FROM adv_english_applications WHERE status = 'rejected'")

    return {
        "total_users": total_users,
        "active_users_7d": active_users_7d,
        "users_in_flow": users_in_flow,
        "total_questions": total_questions,
        "pending_questions": pending_questions,
        "answered_questions": answered_questions,
        "questions_by_program": questions_by_program,
        "pending_jobs": pending_jobs,
        "active_event": active_event,
        "total_links": total_links,
        "total_approvals": total_approvals,
        "videos_set": [r[0] for r in videos_set],
        "ae_total": ae_total,
        "ae_pending": ae_pending,
        "ae_accepted": ae_accepted,
        "ae_rejected": ae_rejected,
    }


async def get_all_chat_ids() -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT chat_id FROM users") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]


# ---------------------------------------------------------------------------
# Special event operations
# ---------------------------------------------------------------------------

async def se_get_active_post() -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM special_event_posts WHERE is_active = 1 ORDER BY id DESC LIMIT 1"
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def se_save_post(post_chat_id: int, post_message_id: int) -> None:
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE special_event_posts SET is_active = 0 WHERE is_active = 1")
        await db.execute(
            "INSERT INTO special_event_posts (post_chat_id, post_message_id, is_active, created_at) "
            "VALUES (?, ?, 1, ?)",
            (post_chat_id, post_message_id, now),
        )
        await db.commit()


async def se_get_all_participants() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM special_event_participants ORDER BY participated_at"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def se_get_participant(student_chat_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM special_event_participants WHERE student_chat_id = ?",
            (student_chat_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def se_remove_participant(student_chat_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM special_event_participants WHERE student_chat_id = ?",
            (student_chat_id,),
        )
        await db.commit()


async def se_add_participant(
    student_chat_id: int, first_name: str, username: str | None
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT OR IGNORE INTO special_event_participants
               (student_chat_id, first_name, username, participated_at)
               VALUES (?, ?, ?, ?)""",
            (student_chat_id, first_name, username, now),
        )
        await db.commit()


# ---------------------------------------------------------------------------
# Advanced English application operations
# ---------------------------------------------------------------------------

async def ae_save_application(
    chat_id: int,
    username: str | None,
    full_name: str,
    video_file_id: str,
    video_type: str,
    ielts: str,
    ielts_file_type: str,
    sat_score: str,
    why_adv_english: str,
    perspective_answer: str,
    resources_answer: str,
) -> int:
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO adv_english_applications
                (chat_id, username, full_name, video_file_id, video_type, ielts, ielts_file_type,
                 sat_score, why_adv_english, perspective_answer, resources_answer, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (chat_id, username, full_name, video_file_id, video_type, ielts, ielts_file_type,
               sat_score, why_adv_english, perspective_answer, resources_answer, now))
        await db.commit()
        return cursor.lastrowid


async def ae_get_all_applications() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM adv_english_applications ORDER BY created_at DESC"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def ae_get_application(chat_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM adv_english_applications WHERE chat_id = ?", (chat_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def ae_get_application_by_id(application_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM adv_english_applications WHERE id = ?", (application_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def ae_set_reviewer_message(application_id: int, message_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE adv_english_applications SET reviewer_message_id = ? WHERE id = ?",
            (message_id, application_id),
        )
        await db.commit()


async def ae_set_status(application_id: int, status: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE adv_english_applications SET status = ? WHERE id = ?",
            (status, application_id),
        )
        await db.commit()


async def ae_clear_all_applications() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("DELETE FROM adv_english_applications")
        await db.commit()
        return cursor.rowcount


async def get_setting(key: str) -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT value FROM bot_settings WHERE key = ?", (key,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def set_setting(key: str, value: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO bot_settings (key, value) VALUES (?, ?)"
            " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        await db.commit()


# ---------------------------------------------------------------------------
# SAT Giveaway operations
# ---------------------------------------------------------------------------

async def sat_save_post(post_chat_id: int, post_message_id: int) -> None:
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE sat_giveaway_posts SET is_active = 0 WHERE is_active = 1")
        await db.execute(
            "INSERT INTO sat_giveaway_posts (post_chat_id, post_message_id, is_active, created_at)"
            " VALUES (?, ?, 1, ?)",
            (post_chat_id, post_message_id, now),
        )
        await db.commit()


async def sat_get_active_post() -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM sat_giveaway_posts WHERE is_active = 1 ORDER BY id DESC LIMIT 1"
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def sat_save_entry(
    chat_id: int,
    username: str | None,
    first_name: str,
    screenshot_file_id: str,
    screenshot_file_type: str,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO sat_giveaway_entries
               (chat_id, username, first_name, screenshot_file_id, screenshot_file_type, status, created_at)
               VALUES (?, ?, ?, ?, ?, 'pending', ?)
               ON CONFLICT(chat_id) DO UPDATE SET
                   username = excluded.username,
                   first_name = excluded.first_name,
                   screenshot_file_id = excluded.screenshot_file_id,
                   screenshot_file_type = excluded.screenshot_file_type,
                   status = 'pending',
                   reviewer_message_id = NULL,
                   created_at = excluded.created_at""",
            (chat_id, username, first_name, screenshot_file_id, screenshot_file_type, now),
        )
        await db.commit()


async def sat_get_entry(chat_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM sat_giveaway_entries WHERE chat_id = ?", (chat_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def sat_set_entry_reviewer_message(chat_id: int, message_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE sat_giveaway_entries SET reviewer_message_id = ? WHERE chat_id = ?",
            (message_id, chat_id),
        )
        await db.commit()


async def sat_set_entry_status(chat_id: int, status: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE sat_giveaway_entries SET status = ? WHERE chat_id = ?",
            (status, chat_id),
        )
        await db.commit()


async def sat_get_users_awaiting_screenshot() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE flow = 'sat_giveaway' AND status = 'sat_step_screenshot'"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def sat_get_all_approved() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM sat_giveaway_entries WHERE status = 'approved' ORDER BY created_at"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
