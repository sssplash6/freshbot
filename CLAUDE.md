# Freshbot — Telegram bot

Telegram bot for Freshman Academy. python-telegram-bot (PTB) v21, async, **polling mode**.

## Run / entry
- `python main.py` — entrypoint. Calls `db.init_db()`, `build_app()` (bot.py), `init_scheduler()`, then `updater.start_polling(drop_pending_updates=True)`.
- No webhook. Single long-running process.

## Module map
| File | Role |
|------|------|
| `main.py` | Entrypoint + polling loop + signal handling. |
| `bot.py` | **Everything**: all handlers (~126 async fns, 3200+ lines) + `build_app()` handler registration at the bottom. |
| `database.py` | aiosqlite. One async function per query, no ORM. |
| `messages.py` | All user-facing strings + `BTN_*` button-label constants. |
| `config.py` | Env vars loaded via `_require()` — admin/reviewer chat IDs, URLs. Missing var = hard fail at import. |
| `scheduler.py` | APScheduler; fires pending jobs saved in DB. |

## How routing works
- **Text + contacts** → `handle_message` (bot.py). Dispatches by matching the message text against `msg.BTN_*` constants and the user's current `flow`/`status` (stored in DB per user). This is the main menu / reply-keyboard logic.
- **Commands** (`/...`) → individual `CommandHandler`s, mostly **admin-only**, gated by `update.effective_user.id == PERSON_X_CHAT_ID` (some use other reviewer IDs).
- **Inline buttons** → `CallbackQueryHandler`s keyed by `callback_data` **pattern prefix** (e.g. `^tap_join$`, `^ae_view:`).

## Feature domains (function/callback prefixes)
- `ae_` — Advanced English applications (terms → payment → review flow)
- `sat_enroll` — SAT Program enrollment (full name → SAT history → test date)
- `tap_` — Trial AP Lesson (join → pre-set post → repost screenshot → reviewer confirm → group invite)
- Getting In Series — no prefix. One menu button + `GETTING_IN_INTRO`, joined by a direct URL button (`GETTING_IN_GROUP_URL` in bot.py). Per episode, swap the speaker in the button label / intro / coming-soon text, swap the group URL, and repoint `/broadcastkeyboard` at the promo.
- `q`/`qp:`/`qd:`/`qa:`/`qs:`/`qr:` — ask-a-question → expert Q&A threads. Experts answer by swipe-reply; `qs:` skips a duplicate/spam question (silent, cancels the 10h follow-up), `qr:` restores it. Viewers: `/answered`, `/unanswered`, `/skipped`.

Retired (removed in Phase 2, tables dropped on startup): `eg_` event giveaway, `se_` special events/rolls, `sat_` giveaway, `hku_` HKU event, `apw_` AP webinar, `rs_` research seminar.

Retired (code removed, table **kept**): `mw_`/`mwa:` Free Admissions Seminar (offline, Bocconi). All handlers, organiser commands, and `MW_*` strings are gone, but `masters_webinar_registrations` and its `database.py` helpers stay so past registration/attendance data survives — recover it via `/export_db`.

## Conventions
- Per-user state machine in DB: `flow` + `status` columns drive `handle_message` branching. Clear both (`set_flow(None)`, `set_status(None)`) when a flow completes.
- Long fan-out sends (broadcasts) run in a background `asyncio.create_task`, capped with an `asyncio.Semaphore` so they don't starve live replies. `build_app()` sets a large `connection_pool_size` + `AIORateLimiter` for the same reason.
- Admin commands silently `return` for non-admins (no error reply).

## Deploy
- User controls deploy timing — **do not push or deploy without explicit instruction.**
- DB is sqlite on the server; `/export_db` dumps it.
