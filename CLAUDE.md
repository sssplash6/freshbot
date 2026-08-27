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
- Getting In Series — no prefix. Currently **Episode XIII, Manzilbek Karlibaev** (KAIST, full ride, AI/ML): menu button restored on row 1 sharing with the Research Fair; `GETTING_IN_INTRO` doubles as the broadcast copy, sent with a single inline `BTN_GETTING_IN_JOIN` URL button pointing at `GETTING_IN_GROUP_URL` (bot.py). Gated by `GETTING_IN_LIVE`. Per episode, swap the speaker in the button label / intro / coming-soon text, swap the group URL, and repoint `/broadcastkeyboard` at the promo. When the button loses its menu slot the handler and `_NAV_BUTTONS` entry stay so stale persistent keyboards keep working.
- `q`/`qp:`/`qd:`/`qa:`/`qs:`/`qr:` — ask-a-question → expert Q&A threads. Experts answer by swipe-reply; `qs:` skips a duplicate/spam question (silent, cancels the 10h follow-up), `qr:` restores it. Viewers: `/answered`, `/unanswered`, `/skipped`.
- `merch_`/`merch_buy:`/`merch_qty:` — Merch shop. Catalog album (photos in `assets/merch/<key>.jpg`, keyed by `msg.MERCH_ITEMS`; uploaded file_ids cached in `bot_settings`) → cart picker (tap an item → inline 1–10 quantity prompt; the picker message morphs between picker and qty prompt and shows the cart + total; re-tap to change qty or remove) → `merch_checkout` → full name → pickup or delivery (delivery adds phone via `request_contact` or text, then address) → final payment step shows the Payme QR (`/set_merch_qr`, stored in `bot_settings`; text fallback until set). One `merch_orders` row per checkout (`item` = cart summary, `price` = total), forwarded to Person X with the username; `/merch_list` shows orders. Gated by `MERCH_LIVE` (bot.py) — while `False`, all entry points and old inline pickers answer `MERCH_COMING_SOON` (`/santix` bypasses, same as Getting In). Menu button shares row 3 with the guidebook.
- `rf_` — Freshman Research Program Fair x Research Competition (Aug 28 2026). Plain registration event, no membership gate: menu button (shares row 1 with the Getting In Series) or the `rf_register` inline button → `RF_INTRO`/`RF_ANNOUNCEMENT` event copy (both are `RF_DETAILS`) → `RF_REGISTER_PROMPT` with the register button on its own message → two-step capture (`flow="research_fair"`, `rf_step_name` → `rf_step_email`, accumulated in `_rf_state`). Email is checked by `_rf_valid_email` (loose: one `@`, no whitespace, dotted alphabetic TLD); if `_rf_state` is empty at the email step (bot restarted mid-flow) the user is bounced back to the name step instead of saving a blank row. Saved to `research_fair_registrations` (upsert on `chat_id`) and forwarded to Person X; `/rf_list` lists registrations, `/rf_group` pushes the event group chat link (`RF_GROUP_URL` in bot.py) to every registrant in batched background sends, `db.research_fair_get` short-circuits anyone already registered. Gated by `RF_LIVE` (bot.py) — while `False`, entry points answer `RF_COMING_SOON` (`/santix` bypasses). `RF_ANNOUNCEMENT` + the `rf_register` callback stay ready for a re-broadcast; `/broadcastkeyboard` is currently pointed at the Getting In episode promo.
- `satc_` — SAT Freshman free SAT strategy consultations (subscription giveaway, no flow/status). Replaces the retired Freshman Global `consult_` giveaway. Menu button (shares row 1 with the Valera giveaway) or `satc_open` inline button → `SATC_INTRO` promo → membership gate on @satfreshman + @freshmanblog (`SATC_REQUIRED_IDS` in bot.py — @satfreshman goes in by handle, freshmanblog by numeric ID; the bot must be an **admin** in both channels or the check fails open, guidebook-style) → pass → `SATC_ACCESS_GRANTED` with one booking button (`SATC_BOOKING_URL`). Each pass is logged in `sat_consult_claims` (first claim keeps its timestamp; the menu path pulls name/username from the `users` table); `/satc_list` lists claimants. Actual bookings live in the Google Calendar booking page, not the bot. Gated by `SATC_LIVE` (bot.py) — while `False`, all entry points answer `SATC_COMING_SOON` (`/santix` bypasses, same as merch). `SATC_ANNOUNCEMENT` + the `satc_open` callback stay ready for a re-broadcast; `/broadcastkeyboard` is currently pointed at the Getting In episode promo.
- `vg_` — Consultation Giveaway with Valera (lottery: win 3 consultations, $360). Revival of the retired `se_` special-event rolls, now on its own `valera_giveaway_participants` table. Menu button (shares row 1 with the SAT consultations giveaway) → `VG_INTRO` promo + separate `VG_JOIN_PROMPT` message with a `vg_join` button (separate so gate edits don't wipe the promo) → membership gate on @valeranotes + @freshmanblog (`VG_REQUIRED_IDS` in bot.py, numeric IDs; bot must be **admin** in both, fails open) → participant row saved; re-tapping re-verifies and drops anyone who unsubscribed. Winner draw (Person X only): `/roll` picks a random participant, `/reroll` or the inline `vg_reroll` button excludes the last pick (`_roll_state`), `vg_confirm:` notifies every participant (winner/loser text, batched background send) and reports delivered/failed counts. `/vg_list` lists participants. Gated by `VG_LIVE` (bot.py) — while `False`, entry points answer `VG_COMING_SOON` (`/santix` bypasses). `VG_INTRO` + the `vg_open` callback (same entry logic as `vg_join` but replies with fresh messages so the announcement isn't edited away) stay ready for a re-broadcast; `/broadcastkeyboard` is currently pointed at the Getting In episode promo.

Retired (removed in Phase 2, tables dropped on startup): `eg_` event giveaway, `se_` special events/rolls, `sat_` giveaway, `hku_` HKU event, `apw_` AP webinar, `rs_` research seminar.

Retired (code removed, table **kept**): `mw_`/`mwa:` Free Admissions Seminar (offline, Bocconi), `art_` Art Seminar by Baxshillo Djumaev (offline), `fireside_` Fireside Chat (Freshman Research Institute, Aug 18 2026), and `consult_` Freshman Global free strategy & EC consultations (Hasan / Imron / Umid, retired Aug 22 2026 when the SAT consultations giveaway took its menu slot — the only leftover is `_consult_retired_callback`, which answers `CONSULT_ENDED` on stale `consult_open`/`consult_check` buttons from the broadcast announcement). All handlers, commands, and `MW_*`/`ART_*`/`FIRESIDE_*`/`CONSULT_*` strings are gone, but `masters_webinar_registrations` / `art_seminar_registrations` / `fireside_registrations` / `consult_claims` and their `database.py` helpers stay so past registration/attendance/claim data survives — recover it via `/export_db`.

## Conventions
- Per-user state machine in DB: `flow` + `status` columns drive `handle_message` branching. Clear both (`set_flow(None)`, `set_status(None)`) when a flow completes.
- Long fan-out sends (broadcasts) run in a background `asyncio.create_task`, capped with an `asyncio.Semaphore` so they don't starve live replies. `build_app()` sets a large `connection_pool_size` + `AIORateLimiter` for the same reason.
- Admin commands silently `return` for non-admins (no error reply).

## Deploy
- User controls deploy timing — **do not push or deploy without explicit instruction.**
- DB is sqlite on the server; `/export_db` dumps it.
