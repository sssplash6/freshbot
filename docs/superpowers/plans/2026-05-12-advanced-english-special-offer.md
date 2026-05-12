# Special Offer – Advanced English Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "Special Offer – Advanced English" button to the main menu that walks users through a 5-step application form, compiles a `.txt` file, sends it to a reviewer with Accept/Reject buttons, and notifies the applicant of the decision.

**Architecture:** In-memory dict `_ae_state` accumulates answers per chat_id across the 5 steps; `flow`/`status` in DB tracks which step the user is on. On completion a `.txt` file is built in-memory via `io.BytesIO` and sent via `send_document`. Reviewer's Accept/Reject are inline `CallbackQueryHandler`s that DM the applicant. Applications are stored in a new `adv_english_applications` table to block re-submission.

**Tech Stack:** Python 3.11, python-telegram-bot 20.x, aiosqlite, stdlib `io`

---

## File Map

| File | Action | What changes |
|------|--------|-------------|
| `config.py` | Modify | Add `ADV_ENGLISH_REVIEWER_CHAT_ID` |
| `messages.py` | Modify | Rename giveaway button, add `BTN_ADV_ENGLISH`, all AE prompts/notifications |
| `database.py` | Modify | Add `adv_english_applications` table + 5 DB functions |
| `bot.py` | Modify | New keyboard layout, in-memory state, entry handler, step capture, file send, callbacks, handler registration |

---

### Task 1: Config — add reviewer env var

**Files:**
- Modify: `config.py`

- [ ] **Step 1: Add the new required env var**

In `config.py`, after the `PERSON_Z_CHAT_ID` line, add:

```python
ADV_ENGLISH_REVIEWER_CHAT_ID: int = int(_require("ADV_ENGLISH_REVIEWER_CHAT_ID"))
```

- [ ] **Step 2: Add to .env (local dev)**

In your `.env` file, add:
```
ADV_ENGLISH_REVIEWER_CHAT_ID=<your_chat_id>
```

- [ ] **Step 3: Commit**

```bash
git add config.py
git commit -m "feat: add ADV_ENGLISH_REVIEWER_CHAT_ID config"
```

---

### Task 2: Messages — all new strings

**Files:**
- Modify: `messages.py`

- [ ] **Step 1: Update BTN_SPECIAL_EVENTS label**

Find:
```python
BTN_SPECIAL_EVENTS = "Consultation Giveaway with Valera"
```
Replace with:
```python
BTN_SPECIAL_EVENTS = "Consultation Giveaway w/ Valera"
```

- [ ] **Step 2: Add BTN_ADV_ENGLISH and all AE strings**

After `BTN_PODCAST_CHECK`, add:

```python
BTN_ADV_ENGLISH = "Special Offer – Advanced English"

AE_ALREADY_APPLIED = (
    "You've already applied. We'll be in touch!"
)

AE_PROMPT_FULL_NAME = "Please enter your full name:"

AE_PROMPT_IELTS = "What is your IELTS score?"

AE_PROMPT_WHY = (
    "Why do you want to join Advanced English? (50–100 words)"
)

AE_PROMPT_PERSPECTIVE = (
    "What is a topic, book, or idea you have encountered recently that completely changed "
    "your perspective on a subject? (100–150 words)"
)

AE_PROMPT_RESOURCES = (
    "List a selection of texts, resources and outlets that have contributed to your "
    "intellectual development outside of academic courses, including but not limited to "
    "books, journals, websites, podcasts, essays, plays, videos, and other content that "
    "you enjoy. (100 words)"
)

AE_SUBMITTED = (
    "Thank you! Your application has been submitted. We'll notify you of the decision."
)

AE_ACCEPTED = "Congratulations! You've been accepted to Advanced English. \U0001f389"

AE_REJECTED = "Thank you for applying. Unfortunately, you have not been accepted at this time."

AE_REVIEWER_CAPTION = (
    "\U0001f4cb New Advanced English application from {first_name}{username_part}"
)

BTN_AE_ACCEPT = "✅ Accept"
BTN_AE_REJECT = "❌ Reject"

AE_REVIEWER_ACCEPTED = "✅ Accepted. Applicant has been notified."
AE_REVIEWER_REJECTED = "❌ Rejected. Applicant has been notified."
AE_REVIEWER_ALREADY_DECIDED = "ℹ️ Decision already recorded for this application."
```

- [ ] **Step 3: Commit**

```bash
git add messages.py
git commit -m "feat: add Advanced English messages and rename giveaway button"
```

---

### Task 3: Database — applications table and helpers

**Files:**
- Modify: `database.py`

- [ ] **Step 1: Add table creation in `init_db()`**

Inside `init_db()`, before the final `await db.commit()`, add:

```python
        await db.execute("""
            CREATE TABLE IF NOT EXISTS adv_english_applications (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id             INTEGER NOT NULL UNIQUE,
                username            TEXT,
                full_name           TEXT NOT NULL,
                ielts               TEXT NOT NULL,
                why_adv_english     TEXT NOT NULL,
                perspective_answer  TEXT NOT NULL,
                resources_answer    TEXT NOT NULL,
                status              TEXT NOT NULL DEFAULT 'pending',
                reviewer_message_id INTEGER,
                created_at          TEXT NOT NULL
            )
        """)
```

- [ ] **Step 2: Add `ae_save_application()`**

After the special event DB functions, add:

```python
async def ae_save_application(
    chat_id: int,
    username: str | None,
    full_name: str,
    ielts: str,
    why_adv_english: str,
    perspective_answer: str,
    resources_answer: str,
) -> int:
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO adv_english_applications
                (chat_id, username, full_name, ielts, why_adv_english,
                 perspective_answer, resources_answer, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (chat_id, username, full_name, ielts, why_adv_english,
               perspective_answer, resources_answer, now))
        await db.commit()
        return cursor.lastrowid
```

- [ ] **Step 3: Add `ae_get_application()`**

```python
async def ae_get_application(chat_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM adv_english_applications WHERE chat_id = ?", (chat_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None
```

- [ ] **Step 4: Add `ae_get_application_by_id()`, `ae_set_reviewer_message()`, and `ae_set_status()`**

```python
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
```

- [ ] **Step 5: Commit**

```bash
git add database.py
git commit -m "feat: add adv_english_applications table and DB helpers"
```

---

### Task 4: Bot — keyboard layout and nav buttons

**Files:**
- Modify: `bot.py`

- [ ] **Step 1: Import ADV_ENGLISH_REVIEWER_CHAT_ID from config**

In the `from config import (...)` block in `bot.py`, add:
```python
    ADV_ENGLISH_REVIEWER_CHAT_ID,
```

- [ ] **Step 2: Add BTN_ADV_ENGLISH to `_NAV_BUTTONS`**

Find:
```python
_NAV_BUTTONS: frozenset[str] = frozenset({
    msg.BTN_PROGRAMS, msg.BTN_GENERAL_INQUIRY, msg.BTN_PODCAST,
    msg.BTN_SPECIAL_EVENTS, msg.BTN_GET_LINK, msg.BTN_HOME, msg.BTN_START,
})
```
Replace with:
```python
_NAV_BUTTONS: frozenset[str] = frozenset({
    msg.BTN_PROGRAMS, msg.BTN_GENERAL_INQUIRY, msg.BTN_PODCAST,
    msg.BTN_SPECIAL_EVENTS, msg.BTN_GET_LINK, msg.BTN_HOME, msg.BTN_START,
    msg.BTN_ADV_ENGLISH,
})
```

- [ ] **Step 3: Update `_main_keyboard()`**

Find:
```python
def _main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [msg.BTN_PROGRAMS, msg.BTN_GENERAL_INQUIRY],
            [msg.BTN_PODCAST],
            [msg.BTN_SPECIAL_EVENTS],
            [msg.BTN_GET_LINK],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )
```
Replace with:
```python
def _main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [msg.BTN_PROGRAMS, msg.BTN_GENERAL_INQUIRY],
            [msg.BTN_ADV_ENGLISH],
            [msg.BTN_SPECIAL_EVENTS, msg.BTN_PODCAST],
            [msg.BTN_GET_LINK],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )
```

- [ ] **Step 4: Commit**

```bash
git add bot.py
git commit -m "feat: update main keyboard layout for Advanced English"
```

---

### Task 5: Bot — in-memory state, entry handler, and routing

**Files:**
- Modify: `bot.py`

- [ ] **Step 1: Add `import io` at the top of bot.py**

Near the other stdlib imports at the top of `bot.py`, add:
```python
import io
```

- [ ] **Step 2: Add in-memory state dict**

Near the other in-memory state dicts (next to `_expert_clarification_state`), add:

```python
# Accumulates Advanced English application answers per chat_id across steps.
_ae_state: dict[int, dict] = {}
```

- [ ] **Step 3: Add the entry handler `_handle_adv_english()`**

After `_handle_general_inquiry()`, add:

```python
async def _handle_adv_english(update: Update, chat_id: int) -> None:
    existing = await db.ae_get_application(chat_id)
    if existing:
        await update.message.reply_text(msg.AE_ALREADY_APPLIED, reply_markup=_main_keyboard())
        return

    _ae_state[chat_id] = {}
    await db.set_flow(chat_id, "adv_english")
    await db.set_status(chat_id, "ae_step_full_name")
    await update.message.reply_text(msg.AE_PROMPT_FULL_NAME, reply_markup=_back_keyboard())
```

- [ ] **Step 4: Add capture state check in `handle_message()`**

In `handle_message()`, after the `"awaiting_followup_text"` capture block, add:

```python
    if user and user.get("flow") == "adv_english" and user.get("status") in (
        "ae_step_full_name", "ae_step_ielts", "ae_step_why",
        "ae_step_perspective", "ae_step_resources",
    ):
        if text in _NAV_BUTTONS:
            _ae_state.pop(chat_id, None)
            await db.set_flow(chat_id, None)
            await db.set_status(chat_id, None)
        else:
            await _handle_ae_step(update, chat_id, text, context)
            return
```

- [ ] **Step 5: Wire entry handler in `handle_message()` routing**

In `handle_message()`, after the `BTN_SPECIAL_EVENTS` branch, add:

```python
    elif text == msg.BTN_ADV_ENGLISH:
        await _handle_adv_english(update, chat_id)
```

- [ ] **Step 6: Commit**

```bash
git add bot.py
git commit -m "feat: add Advanced English entry handler and state routing"
```

---

### Task 6: Bot — step handler and file compilation

**Files:**
- Modify: `bot.py`

- [ ] **Step 1: Add `_AE_STEPS` tuple and `_handle_ae_step()`**

After `_handle_adv_english()`, add:

```python
_AE_STEPS = [
    ("ae_step_full_name",   "full_name",          "ae_step_ielts",       msg.AE_PROMPT_IELTS),
    ("ae_step_ielts",       "ielts",              "ae_step_why",         msg.AE_PROMPT_WHY),
    ("ae_step_why",         "why_adv_english",    "ae_step_perspective", msg.AE_PROMPT_PERSPECTIVE),
    ("ae_step_perspective", "perspective_answer", "ae_step_resources",   msg.AE_PROMPT_RESOURCES),
]


async def _handle_ae_step(
    update: Update, chat_id: int, text: str, context: ContextTypes.DEFAULT_TYPE
) -> None:
    user = await db.get_user(chat_id)
    status = user.get("status") if user else None

    for current_status, field, next_status, next_prompt in _AE_STEPS:
        if status == current_status:
            _ae_state.setdefault(chat_id, {})[field] = text
            await db.set_status(chat_id, next_status)
            await update.message.reply_text(next_prompt, reply_markup=_back_keyboard())
            return

    if status == "ae_step_resources":
        _ae_state.setdefault(chat_id, {})["resources_answer"] = text
        await _ae_finish(update, chat_id, context)
```

- [ ] **Step 2: Add `_ae_finish()`**

```python
async def _ae_finish(
    update: Update, chat_id: int, context: ContextTypes.DEFAULT_TYPE
) -> None:
    answers = _ae_state.pop(chat_id, {})
    user = await db.get_user(chat_id)
    username = user.get("username") if user else None
    first_name = user["first_name"] if user else "Unknown"

    full_name       = answers.get("full_name", "")
    ielts           = answers.get("ielts", "")
    why_adv_english = answers.get("why_adv_english", "")
    perspective     = answers.get("perspective_answer", "")
    resources       = answers.get("resources_answer", "")

    application_id = await db.ae_save_application(
        chat_id=chat_id,
        username=username,
        full_name=full_name,
        ielts=ielts,
        why_adv_english=why_adv_english,
        perspective_answer=perspective,
        resources_answer=resources,
    )

    await db.set_flow(chat_id, None)
    await db.set_status(chat_id, None)

    await update.message.reply_text(msg.AE_SUBMITTED, reply_markup=_main_keyboard())

    username_part = f" (@{username})" if username else ""
    file_content = (
        f"ADVANCED ENGLISH APPLICATION\n"
        f"{'=' * 40}\n"
        f"Name:     {full_name}\n"
        f"Username: @{username or 'N/A'}\n"
        f"IELTS:    {ielts}\n\n"
        f"Why Advanced English?\n"
        f"{'-' * 30}\n"
        f"{why_adv_english}\n\n"
        f"A topic, book, or idea that changed your perspective:\n"
        f"{'-' * 30}\n"
        f"{perspective}\n\n"
        f"Texts, resources and outlets:\n"
        f"{'-' * 30}\n"
        f"{resources}\n"
    ).encode("utf-8")

    file_obj = io.BytesIO(file_content)
    file_obj.name = f"ae_application_{chat_id}.txt"

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(msg.BTN_AE_ACCEPT, callback_data=f"ae_accept:{application_id}"),
            InlineKeyboardButton(msg.BTN_AE_REJECT, callback_data=f"ae_reject:{application_id}"),
        ]
    ])

    caption = msg.AE_REVIEWER_CAPTION.format(
        first_name=first_name,
        username_part=username_part,
    )

    sent = await context.bot.send_document(
        chat_id=ADV_ENGLISH_REVIEWER_CHAT_ID,
        document=file_obj,
        filename=f"ae_application_{chat_id}.txt",
        caption=caption,
        reply_markup=keyboard,
    )
    await db.ae_set_reviewer_message(application_id, sent.message_id)
```

- [ ] **Step 3: Commit**

```bash
git add bot.py
git commit -m "feat: add Advanced English step handler and file compilation"
```

---

### Task 7: Bot — Accept/Reject callbacks and applicant notification

**Files:**
- Modify: `bot.py`

- [ ] **Step 1: Add `_ae_decision_callback()`, `_ae_accept_callback()`, `_ae_reject_callback()`**

After `_ae_finish()`, add:

```python
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
    except Exception:
        logger.exception("Failed to notify applicant chat_id=%d", applicant_chat_id)

    await query.edit_message_caption(
        caption=f"{query.message.caption}\n\n{reviewer_confirmation}",
        reply_markup=None,
    )


async def _ae_accept_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _ae_decision_callback(update, context, "accepted")


async def _ae_reject_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _ae_decision_callback(update, context, "rejected")
```

- [ ] **Step 2: Register callbacks in `build_app()`**

In `build_app()`, alongside the other `CallbackQueryHandler` registrations, add:

```python
    app.add_handler(CallbackQueryHandler(_ae_accept_callback, pattern="^ae_accept:"))
    app.add_handler(CallbackQueryHandler(_ae_reject_callback, pattern="^ae_reject:"))
```

- [ ] **Step 3: Commit**

```bash
git add bot.py
git commit -m "feat: add Advanced English accept/reject callbacks"
```

---

### Task 8: Bot — Back button handling for adv_english flow

**Files:**
- Modify: `bot.py`

- [ ] **Step 1: Update `_handle_back()` to handle `adv_english` flow**

In `_handle_back()`, find:
```python
    if flow == "general_inquiry":
```
Add a new branch **before** it:

```python
    if flow == "adv_english":
        _ae_state.pop(chat_id, None)
        await db.set_flow(chat_id, None)
        await db.set_status(chat_id, None)
        await update.message.reply_text(
            msg.WELCOME.format(first_name=first_name),
            reply_markup=_main_keyboard(),
        )
        return
```

- [ ] **Step 2: Commit**

```bash
git add bot.py
git commit -m "feat: handle back button in Advanced English flow"
```

---

### Task 9: Manual testing checklist

No automated test framework exists in this codebase. Test against a live bot instance.

- [ ] `/start` shows the new 4-row keyboard: Advanced English on row 2, Giveaway and Podcast sharing row 3.
- [ ] **Happy path** — tap the button, fill in all 5 answers; "Thank you" message appears; `.txt` file arrives at reviewer chat with Accept/Reject buttons.
- [ ] **Accept flow** — reviewer taps Accept; applicant gets accepted message; reviewer sees "✅ Accepted. Applicant has been notified."; buttons disappear.
- [ ] **Reject flow** — reviewer taps Reject; applicant gets rejected message; reviewer sees "❌ Rejected."; buttons disappear.
- [ ] **Already applied** — start the flow again; "You've already applied" appears.
- [ ] **Back button** — tap Advanced English, type a name, tap Back; returns to main menu; re-tapping Advanced English starts fresh.
- [ ] **Nav button escape** — tap Advanced English, type a name, tap Programs; Programs keyboard appears; AE flow is cleared.
- [ ] **Double-decision guard** — after Accept, attempt Reject via the same message; "Decision already recorded" alert appears.
