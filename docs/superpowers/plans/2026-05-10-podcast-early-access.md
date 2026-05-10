# Podcast Early Access Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a gated "Early Access: Freshman Podcast" section to the bot's main menu, restructure the menu to a cleaner 2-per-line layout, and remove the unused "Special Offer - Advanced English" button.

**Architecture:** Three files touched in sequence — `config.py` adds optional env vars, `messages.py` adds strings and removes the old button label, `bot.py` removes the dead handler, updates the keyboard, and wires the new podcast flow (initial handler + inline callback).

**Tech Stack:** Python, python-telegram-bot, aiosqlite, APScheduler, Render (deployment).

---

## File Map

| File | Change |
|---|---|
| `config.py` | Add 3 optional podcast env vars |
| `messages.py` | Add 5 podcast strings, remove `BTN_SPECIAL_OFFER_AE` |
| `bot.py` | Remove special offer, update keyboard, add podcast handler + callback + routing |

---

### Task 1: Add podcast env vars to `config.py`

**Files:**
- Modify: `telegram_bot/config.py`

- [ ] **Step 1: Add the three optional podcast variables at the end of `config.py`**

Append after the existing `_optional_str_list` calls (after line 68):

```python
PODCAST_CHANNEL_IDS: list[int] = _optional_int_list("PODCAST_CHANNEL_IDS")
PODCAST_CHANNEL_HANDLES: list[str] = _optional_str_list("PODCAST_CHANNEL_HANDLES")
PODCAST_YOUTUBE_URL: str = os.getenv("PODCAST_YOUTUBE_URL", "")
```

- [ ] **Step 2: Verify the bot still starts (imports load without error)**

```bash
cd /Users/workingmyassof/freshbot/telegram_bot
python -c "from config import PODCAST_CHANNEL_IDS, PODCAST_CHANNEL_HANDLES, PODCAST_YOUTUBE_URL; print('OK')"
```

Expected output: `OK`

- [ ] **Step 3: Commit**

```bash
git add telegram_bot/config.py
git commit -m "feat: add podcast channel env vars to config"
```

---

### Task 2: Add podcast strings and remove Special Offer button from `messages.py`

**Files:**
- Modify: `telegram_bot/messages.py`

- [ ] **Step 1: Add podcast button label and strings**

After the `BTN_START` line (line 521 currently) add:

```python
BTN_PODCAST = "🎙 Early Access: Freshman Podcast"

PODCAST_COMING_SOON = "🔒 Early Access to Freshman Podcast is coming soon. Stay tuned!"

PODCAST_MUST_JOIN = (
    "To access the Freshman Podcast, please subscribe to the following channels first:\n"
    "{channel_list}\n\n"
    "Once you've subscribed, tap the button below."
)

PODCAST_ACCESS_GRANTED = (
    "🎙 Welcome to Freshman Podcast — Early Access!\n\n"
    "Here is your link:\n{youtube_url}"
)

BTN_PODCAST_CHECK = "✅ I've subscribed — check again"
```

- [ ] **Step 2: Remove `BTN_SPECIAL_OFFER_AE`**

Delete this line from `messages.py`:

```python
BTN_SPECIAL_OFFER_AE = "Special Offer - Advanced English"
```

- [ ] **Step 3: Verify messages module loads cleanly**

```bash
python -c "import messages; print(messages.BTN_PODCAST)"
```

Expected output: `🎙 Early Access: Freshman Podcast`

- [ ] **Step 4: Commit**

```bash
git add telegram_bot/messages.py
git commit -m "feat: add podcast strings, remove special offer button label"
```

---

### Task 3: Update main menu keyboard and remove Special Offer from `bot.py`

**Files:**
- Modify: `telegram_bot/bot.py`

- [ ] **Step 1: Remove `BTN_SPECIAL_OFFER_AE` from the config import block**

In `bot.py` around line 47, remove `BTN_SPECIAL_OFFER_AE` from the `import messages as msg` usage. It's referenced as `msg.BTN_SPECIAL_OFFER_AE` — search for all occurrences:

```bash
grep -n "SPECIAL_OFFER_AE" telegram_bot/bot.py
```

There will be two: the `elif` routing branch and the handler function.

- [ ] **Step 2: Replace `_main_keyboard()` with the new layout**

Find the current `_main_keyboard` function (around line 101) and replace its body:

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

- [ ] **Step 3: Remove the Special Offer routing branch from `handle_message`**

Find and delete this `elif` block (around line 265):

```python
elif text == msg.BTN_SPECIAL_OFFER_AE:
    await _handle_special_offer_ae(update, chat_id)
```

- [ ] **Step 4: Remove the `_handle_special_offer_ae` function entirely**

Find and delete the entire function (around line 1246):

```python
async def _handle_special_offer_ae(update: Update, chat_id: int) -> None:
    await update.message.reply_text("Coming soon!", reply_markup=_main_keyboard())
```

- [ ] **Step 5: Verify no remaining references to special offer**

```bash
grep -n "special_offer\|SPECIAL_OFFER" telegram_bot/bot.py
```

Expected output: nothing.

- [ ] **Step 6: Commit**

```bash
git add telegram_bot/bot.py
git commit -m "feat: update main menu to 2-per-line, remove special offer button"
```

---

### Task 4: Add podcast handler, callback, and routing to `bot.py`

**Files:**
- Modify: `telegram_bot/bot.py`

- [ ] **Step 1: Add podcast config vars to the import block**

Find the `from config import (` block at the top of `bot.py` and add three entries:

```python
    PODCAST_CHANNEL_IDS,
    PODCAST_CHANNEL_HANDLES,
    PODCAST_YOUTUBE_URL,
```

- [ ] **Step 2: Add `_podcast_get_missing` helper**

Add this function after the `_se_get_missing_handles` function (search for it — around line 1274):

```python
async def _podcast_get_missing(bot, chat_id: int) -> list[str]:
    if not PODCAST_CHANNEL_IDS:
        return []
    missing = []
    for channel_id, handle in zip(PODCAST_CHANNEL_IDS, PODCAST_CHANNEL_HANDLES):
        try:
            member = await bot.get_chat_member(channel_id, chat_id)
            if member.status not in _EG_MEMBER_STATUSES:
                missing.append(handle)
        except TelegramError:
            logger.warning("Cannot check podcast membership in %s. Failing open.", channel_id)
    return missing
```

- [ ] **Step 3: Add `_handle_podcast` handler**

Add this function directly after `_podcast_get_missing`:

```python
async def _handle_podcast(update: Update, chat_id: int) -> None:
    if chat_id not in _bypass_users:
        await update.message.reply_text(msg.PODCAST_COMING_SOON, reply_markup=_main_keyboard())
        return
    missing = await _podcast_get_missing(update.get_bot(), chat_id)
    if missing:
        channel_list = "\n".join(f"• {h}" for h in missing)
        await update.message.reply_text(
            msg.PODCAST_MUST_JOIN.format(channel_list=channel_list),
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(msg.BTN_PODCAST_CHECK, callback_data="podcast_check")]]
            ),
        )
        return
    await update.message.reply_text(
        msg.PODCAST_ACCESS_GRANTED.format(youtube_url=PODCAST_YOUTUBE_URL),
        reply_markup=_main_keyboard(),
    )
```

- [ ] **Step 4: Add `_podcast_check_callback` callback**

Add this function directly after `_handle_podcast`:

```python
async def _podcast_check_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_user.id
    if chat_id not in _bypass_users:
        try:
            await query.edit_message_text(msg.PODCAST_COMING_SOON)
        except TelegramError as e:
            if "not modified" not in str(e).lower():
                raise
        return
    missing = await _podcast_get_missing(context.bot, chat_id)
    if missing:
        channel_list = "\n".join(f"• {h}" for h in missing)
        try:
            await query.edit_message_text(
                msg.PODCAST_MUST_JOIN.format(channel_list=channel_list),
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton(msg.BTN_PODCAST_CHECK, callback_data="podcast_check")]]
                ),
            )
        except TelegramError as e:
            if "not modified" not in str(e).lower():
                raise
        return
    try:
        await query.edit_message_text(
            msg.PODCAST_ACCESS_GRANTED.format(youtube_url=PODCAST_YOUTUBE_URL),
        )
    except TelegramError as e:
        if "not modified" not in str(e).lower():
            raise
```

- [ ] **Step 5: Add routing in `handle_message`**

In the `handle_message` function, add an `elif` branch for the podcast button. Place it alongside the other main-menu button handlers (after the `BTN_GENERAL_INQUIRY` branch, around line 267):

```python
elif text == msg.BTN_PODCAST:
    await _handle_podcast(update, chat_id)
```

- [ ] **Step 6: Register the callback handler in `build_app`**

In `build_app()`, after the existing `CallbackQueryHandler` registrations, add:

```python
app.add_handler(CallbackQueryHandler(_podcast_check_callback, pattern="^podcast_check$"))
```

- [ ] **Step 7: Verify the module imports and parses without errors**

```bash
python -c "from bot import build_app; print('OK')"
```

Expected output: `OK`

- [ ] **Step 8: Manual smoke test**

1. Start the bot locally: `python main.py`
2. Send `/start` — confirm 4-row menu appears with Programs+General Inquiry on row 1
3. Tap "🎙 Early Access: Freshman Podcast" — confirm "coming soon" message
4. Send `/santix` to enable bypass
5. Tap "🎙 Early Access: Freshman Podcast" again — if `PODCAST_CHANNEL_IDS` is empty, confirm link message appears; if set, confirm channel list appears with "check again" button

- [ ] **Step 9: Commit**

```bash
git add telegram_bot/bot.py
git commit -m "feat: add podcast early access flow with bypass and channel gate"
```

---

## Env Vars to Set on Render

After deploying, add these to the Render service environment:

| Key | Example value | Required |
|---|---|---|
| `PODCAST_CHANNEL_IDS` | `-1001234567890,-1009876543210` | No (skips channel check if absent) |
| `PODCAST_CHANNEL_HANDLES` | `@freshmanacademy,@freshmanpodcast` | No (paired with IDs) |
| `PODCAST_YOUTUBE_URL` | `https://youtube.com/...` | No (empty string delivered if absent) |
