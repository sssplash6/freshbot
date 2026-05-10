# Podcast Early Access — Design Spec
_Date: 2026-05-10_

## Overview

Add an "Early Access: Freshman Podcast" section to the bot. The feature is gated behind a public "coming soon" block that can be bypassed via the existing `/santix` mechanism. Bypassed users must pass a Telegram channel subscription check before receiving the YouTube link. Additionally, remove the unused "Special Offer - Advanced English" button and restructure the main menu to a 2-per-line layout.

---

## Main Menu Layout

```
[📚 Programs]  [💬 General Inquiry]
[🎙 Early Access: Freshman Podcast]
[Consultation Giveaway with Valera]
[🔗 Get Event Link]
```

- "Special Offer - Advanced English" button is removed entirely (button label, handler, and routing).

---

## Podcast Feature Flow

1. User taps `🎙 Early Access: Freshman Podcast`.
2. **Public block:** If `chat_id` is NOT in `_bypass_users` → reply with coming soon message, show main keyboard. Stop.
3. **Subscription check:** Check user's membership in each channel in `PODCAST_CHANNEL_IDS`.
   - Fails open on Telegram API error (treats as subscribed) to avoid locking out users on transient errors.
4. **Missing channels:** If any channels are unsubscribed → show list of `PODCAST_CHANNEL_HANDLES` with an inline "✅ I've subscribed — check again" button (callback `podcast_check`).
5. **Access granted:** If all subscribed → send `PODCAST_YOUTUBE_URL` in a message.

The "check again" callback re-runs steps 3–5 on the same inline message (edit in place). Bypass check is also enforced in the callback in case the user somehow holds a stale inline button.

---

## Environment Variables

All three are optional. If `PODCAST_CHANNEL_IDS` is empty, the subscription check is skipped and the link is delivered immediately.

| Variable | Type | Description |
|---|---|---|
| `PODCAST_CHANNEL_IDS` | comma-separated integers | Telegram channel IDs to check subscription against |
| `PODCAST_CHANNEL_HANDLES` | comma-separated strings | Human-readable handles/links shown when user is not subscribed |
| `PODCAST_YOUTUBE_URL` | string | YouTube link delivered after passing the check |

---

## Code Changes

### `config.py`
- Add `PODCAST_CHANNEL_IDS: list[int]` via `_optional_int_list`
- Add `PODCAST_CHANNEL_HANDLES: list[str]` via `_optional_str_list`
- Add `PODCAST_YOUTUBE_URL: str` via `os.getenv` with empty string default

### `messages.py`
- Add `BTN_PODCAST = "🎙 Early Access: Freshman Podcast"`
- Add `PODCAST_COMING_SOON` — coming soon string
- Add `PODCAST_MUST_JOIN` — channel list prompt (uses `{channel_list}` placeholder)
- Add `PODCAST_ACCESS_GRANTED` — success message with `{youtube_url}` placeholder
- Add `BTN_PODCAST_CHECK = "✅ I've subscribed — check again"`
- Remove `BTN_SPECIAL_OFFER_AE`

### `bot.py`
- Import `PODCAST_CHANNEL_IDS`, `PODCAST_CHANNEL_HANDLES`, `PODCAST_YOUTUBE_URL` from config
- Remove `BTN_SPECIAL_OFFER_AE` import usage and `_handle_special_offer_ae` function
- Update `_main_keyboard()` to new 4-row 2-per-line layout
- Add `_podcast_get_missing(bot, chat_id) -> list[str]` — membership check helper
- Add `_handle_podcast(update, chat_id)` — initial button handler (bypass + check + respond)
- Add `_podcast_check_callback(update, context)` — inline "check again" callback
- Add routing in `handle_message` for `BTN_PODCAST`
- Remove routing for `BTN_SPECIAL_OFFER_AE`
- Register `_podcast_check_callback` with pattern `^podcast_check$` in `build_app()`
- Remove `CommandHandler` / routing for special offer if any

---

## Error Handling

- Telegram API errors during membership check → fail open (treat as subscribed), log warning.
- `PODCAST_YOUTUBE_URL` empty string → still delivered as-is (admin responsibility to set it).
- "message not modified" error on callback edit → silently swallow (same as existing `_se_edit` pattern).
