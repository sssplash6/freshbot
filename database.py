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
            CREATE TABLE IF NOT EXISTS program_videos (
                program    TEXT PRIMARY KEY,
                file_id    TEXT NOT NULL,
                video_type TEXT NOT NULL DEFAULT 'video',
                created_at TEXT NOT NULL
            )
        """)
        # Add video_type column to existing deployments that predate round-video support
        try:
            await db.execute(
                "ALTER TABLE program_videos ADD COLUMN video_type TEXT NOT NULL DEFAULT 'video'"
            )
            await db.commit()
        except Exception:
            pass
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
            CREATE TABLE IF NOT EXISTS tap_entries (
                id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id              INTEGER NOT NULL UNIQUE,
                username             TEXT,
                first_name           TEXT NOT NULL,
                screenshot_file_id   TEXT NOT NULL,
                screenshot_file_type TEXT NOT NULL DEFAULT 'photo',
                status               TEXT NOT NULL DEFAULT 'pending',
                reviewer_message_id  INTEGER,
                invite_link          TEXT,
                created_at           TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sat_enrollments (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id      INTEGER NOT NULL UNIQUE,
                username     TEXT,
                first_name   TEXT NOT NULL,
                full_name    TEXT NOT NULL,
                sat_history  TEXT NOT NULL,
                test_date    TEXT NOT NULL,
                enrolled_at  TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS econ_enrollments (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id      INTEGER NOT NULL UNIQUE,
                username     TEXT,
                first_name   TEXT NOT NULL,
                full_name    TEXT NOT NULL,
                courses      TEXT NOT NULL,
                enrolled_at  TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS masters_webinar_registrations (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id         INTEGER NOT NULL UNIQUE,
                username        TEXT,
                first_name      TEXT NOT NULL,
                full_name       TEXT NOT NULL,
                place_of_study  TEXT NOT NULL,
                registered_at   TEXT NOT NULL
            )
        """)
        for _col in [
            "ALTER TABLE users ADD COLUMN guidebook_sent_at TEXT",
            "ALTER TABLE adv_english_applications ADD COLUMN video_file_id TEXT",
            "ALTER TABLE adv_english_applications ADD COLUMN video_type TEXT",
            "ALTER TABLE adv_english_applications ADD COLUMN sat_score TEXT",
            "ALTER TABLE adv_english_applications ADD COLUMN ielts_file_type TEXT",
            "ALTER TABLE adv_english_applications ADD COLUMN payment_screenshot_file_id TEXT",
            "ALTER TABLE adv_english_applications ADD COLUMN payment_screenshot_file_type TEXT",
            "ALTER TABLE adv_english_applications ADD COLUMN format_type TEXT",
            # Attendance tracking for the offline seminar: `attending` holds the
            # registrant's answer to the "will you attend?" poll ('yes'/'no'),
            # `attended` is the on-the-day check-in toggled by /masters_attendance.
            "ALTER TABLE masters_webinar_registrations ADD COLUMN attending TEXT",
            "ALTER TABLE masters_webinar_registrations ADD COLUMN attending_at TEXT",
            "ALTER TABLE masters_webinar_registrations ADD COLUMN attended INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE masters_webinar_registrations ADD COLUMN attended_at TEXT",
        ]:
            try:
                await db.execute(_col)
                await db.commit()
            except Exception:
                pass
        # Retired features — drop their tables permanently (data already exported).
        for _tbl in [
            "eg_events", "eg_issued_links", "eg_join_approvals",
            "special_event_posts", "special_event_participants",
            "sat_giveaway_posts", "sat_giveaway_entries",
            "hku_registrations",
            "apw_events", "apw_issued_links", "apw_interests",
            "rs_posts", "rs_registrations",
            "tap_posts",
        ]:
            await db.execute(f"DROP TABLE IF EXISTS {_tbl}")
        # The seminar registration table is reused per event. Clear out the
        # finished 24 July 2026 Master's Seminar so /masters_list shows only
        # Free Admissions Seminar (2 Aug 2026) signups. Scoped by timestamp
        # rather than a bare DELETE so a restart never wipes live registrations.
        await db.execute(
            "DELETE FROM masters_webinar_registrations WHERE registered_at < ?",
            ("2026-07-29",),
        )
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


async def cancel_pending_jobs(chat_id: int, job_type: str) -> list[int]:
    """Mark this user's unsent jobs of a type as sent. Returns the cancelled job ids."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id FROM scheduled_jobs WHERE chat_id = ? AND job_type = ? AND sent = 0",
            (chat_id, job_type),
        ) as cursor:
            job_ids = [row[0] for row in await cursor.fetchall()]
        if job_ids:
            await db.execute(
                f"UPDATE scheduled_jobs SET sent = 1 WHERE id IN ({','.join('?' * len(job_ids))})",
                job_ids,
            )
            await db.commit()
        return job_ids


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


async def get_question_by_id(question_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT q.*, u.first_name, u.username
               FROM questions q
               LEFT JOIN users u ON q.user_chat_id = u.chat_id
               WHERE q.id = ?""",
            (question_id,),
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


async def mark_question_skipped(question_id: int) -> None:
    """Dismiss a question without answering it (duplicate / spam)."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE questions SET status = 'skipped' WHERE id = ? AND status = 'pending'",
            (question_id,),
        )
        await db.commit()


async def mark_sibling_questions_skipped(user_chat_id: int, question_text: str) -> None:
    """Skip all other pending copies of the same question (sent to multiple experts)."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """UPDATE questions SET status = 'skipped'
               WHERE user_chat_id = ? AND question_text = ? AND status = 'pending'""",
            (user_chat_id, question_text),
        )
        await db.commit()


async def restore_skipped_question(question_id: int) -> bool:
    """Put a skipped question back in the pending queue. False if it wasn't skipped."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "UPDATE questions SET status = 'pending' WHERE id = ? AND status = 'skipped'",
            (question_id,),
        )
        await db.commit()
        return cursor.rowcount > 0


async def count_pending_questions(user_chat_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM questions WHERE user_chat_id = ? AND status = 'pending'",
            (user_chat_id,),
        ) as cursor:
            return (await cursor.fetchone())[0]


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


async def upsert_program_video(program: str, file_id: str, video_type: str = "video") -> None:
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO program_videos (program, file_id, video_type, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(program) DO UPDATE SET
                file_id    = excluded.file_id,
                video_type = excluded.video_type,
                created_at = excluded.created_at
        """, (program, file_id, video_type, now))
        await db.commit()


async def delete_program_video(program: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM program_videos WHERE program = ?", (program,)
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_programs_with_videos() -> list[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT program FROM program_videos") as cursor:
            return [row[0] for row in await cursor.fetchall()]


async def get_program_video(program: str) -> tuple[str, str] | None:
    """Returns (file_id, video_type) or None. video_type is 'video' or 'video_note'."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT file_id, video_type FROM program_videos WHERE program = ?", (program,)
        ) as cursor:
            row = await cursor.fetchone()
            return (row[0], row[1]) if row else None


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
            "SELECT program, "
            "COUNT(*), "
            "SUM(CASE WHEN status = 'answered' THEN 1 ELSE 0 END), "
            "SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) "
            "FROM questions GROUP BY program ORDER BY COUNT(*) DESC"
        )

        pending_jobs      = await scalar("SELECT COUNT(*) FROM scheduled_jobs WHERE sent = 0")

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


# ---------------------------------------------------------------------------
# Advanced English application operations
# ---------------------------------------------------------------------------

async def ae_save_application(
    chat_id: int,
    username: str | None,
    format_type: str,
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
                (chat_id, username, format_type, full_name, video_file_id, video_type, ielts, ielts_file_type,
                 sat_score, why_adv_english, perspective_answer, resources_answer, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (chat_id, username, format_type, full_name, video_file_id, video_type, ielts, ielts_file_type,
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


async def ae_set_status_by_chat_id(chat_id: int, status: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE adv_english_applications SET status = ? WHERE chat_id = ?",
            (status, chat_id),
        )
        await db.commit()


async def ae_set_payment_screenshot(
    chat_id: int, file_id: str, file_type: str
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE adv_english_applications"
            " SET payment_screenshot_file_id = ?, payment_screenshot_file_type = ?, status = 'payment_pending'"
            " WHERE chat_id = ?",
            (file_id, file_type, chat_id),
        )
        await db.commit()


async def ae_get_applications_by_status(statuses: list[str]) -> list[dict]:
    placeholders = ",".join("?" * len(statuses))
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            f"SELECT * FROM adv_english_applications WHERE status IN ({placeholders})",
            statuses,
        ) as cursor:
            return [dict(row) for row in await cursor.fetchall()]


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
# Extracurriculars Guidebook
# ---------------------------------------------------------------------------

async def mark_guidebook_sent(chat_id: int) -> None:
    """Record that this user received the guidebook (keeps the first delivery time)."""
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET guidebook_sent_at = COALESCE(guidebook_sent_at, ?)"
            " WHERE chat_id = ?",
            (now, chat_id),
        )
        await db.commit()


async def count_guidebook_recipients() -> int:
    """Number of unique users who have received the guidebook at least once."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE guidebook_sent_at IS NOT NULL"
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


# ---------------------------------------------------------------------------
# Trial AP Lesson
# ---------------------------------------------------------------------------

async def tap_save_entry(
    chat_id: int,
    username: str | None,
    first_name: str,
    screenshot_file_id: str,
    screenshot_file_type: str,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO tap_entries
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


async def tap_get_entry(chat_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM tap_entries WHERE chat_id = ?", (chat_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def tap_set_entry_reviewer_message(chat_id: int, message_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE tap_entries SET reviewer_message_id = ? WHERE chat_id = ?",
            (message_id, chat_id),
        )
        await db.commit()


async def tap_set_entry_status(chat_id: int, status: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE tap_entries SET status = ? WHERE chat_id = ?",
            (status, chat_id),
        )
        await db.commit()


async def tap_set_entry_link(chat_id: int, invite_link: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE tap_entries SET invite_link = ? WHERE chat_id = ?",
            (invite_link, chat_id),
        )
        await db.commit()


# ---------------------------------------------------------------------------
# SAT Program Enrollment operations
# ---------------------------------------------------------------------------

async def sat_enroll_save(
    chat_id: int,
    username: str | None,
    first_name: str,
    full_name: str,
    sat_history: str,
    test_date: str,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO sat_enrollments
               (chat_id, username, first_name, full_name, sat_history, test_date, enrolled_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(chat_id) DO UPDATE SET
                   username = excluded.username,
                   first_name = excluded.first_name,
                   full_name = excluded.full_name,
                   sat_history = excluded.sat_history,
                   test_date = excluded.test_date,
                   enrolled_at = excluded.enrolled_at""",
            (chat_id, username, first_name, full_name, sat_history, test_date, now),
        )
        await db.commit()


async def econ_enroll_save(
    chat_id: int,
    username: str | None,
    first_name: str,
    full_name: str,
    courses: str,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO econ_enrollments
               (chat_id, username, first_name, full_name, courses, enrolled_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(chat_id) DO UPDATE SET
                   username = excluded.username,
                   first_name = excluded.first_name,
                   full_name = excluded.full_name,
                   courses = excluded.courses,
                   enrolled_at = excluded.enrolled_at""",
            (chat_id, username, first_name, full_name, courses, now),
        )
        await db.commit()


async def econ_enroll_get_all() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM econ_enrollments ORDER BY enrolled_at"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def get_ae_stuck_users() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE flow = 'adv_english'"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def sat_enroll_get_all() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM sat_enrollments ORDER BY enrolled_at"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def masters_webinar_save(
    chat_id: int,
    username: str | None,
    first_name: str,
    full_name: str,
    place_of_study: str,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO masters_webinar_registrations
               (chat_id, username, first_name, full_name, place_of_study, registered_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(chat_id) DO UPDATE SET
                   username = excluded.username,
                   first_name = excluded.first_name,
                   full_name = excluded.full_name,
                   place_of_study = excluded.place_of_study,
                   registered_at = excluded.registered_at""",
            (chat_id, username, first_name, full_name, place_of_study, now),
        )
        await db.commit()


async def masters_webinar_get_all() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM masters_webinar_registrations ORDER BY registered_at"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def masters_webinar_get(chat_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM masters_webinar_registrations WHERE chat_id = ?", (chat_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def masters_webinar_set_attending(chat_id: int, answer: str) -> bool:
    """Record the registrant's 'will you attend?' poll answer ('yes'/'no').

    Returns False if the chat_id isn't a registrant, so the caller can tell a
    stale button tap apart from a real answer.
    """
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """UPDATE masters_webinar_registrations
               SET attending = ?, attending_at = ?
               WHERE chat_id = ?""",
            (answer, now, chat_id),
        )
        await db.commit()
        return cursor.rowcount > 0


async def masters_webinar_toggle_attended(chat_id: int) -> bool | None:
    """Flip the on-the-day check-in flag. Returns the new state, or None if the
    chat_id isn't a registrant."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT attended FROM masters_webinar_registrations WHERE chat_id = ?",
            (chat_id,),
        ) as cursor:
            row = await cursor.fetchone()
        if row is None:
            return None
        new_state = 0 if row[0] else 1
        await db.execute(
            """UPDATE masters_webinar_registrations
               SET attended = ?, attended_at = ?
               WHERE chat_id = ?""",
            (new_state, datetime.now(timezone.utc).isoformat() if new_state else None, chat_id),
        )
        await db.commit()
        return bool(new_state)
