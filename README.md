# Telegram Education Bot

A customer-facing Telegram bot for an education company. Users choose a program, then either get support contact info (with a 10-hour follow-up) or book a meeting via Google Calendar (with automated reminders).

---

## Prerequisites

- Python 3.11+
- A Google Cloud project with the Calendar API enabled
- A service account with a downloaded JSON key file
- A public HTTPS URL for the Google Calendar webhook endpoint
  - For local development: [ngrok](https://ngrok.com/) (`ngrok http 8000`)
  - For production: any server with a domain and TLS

---

## Installation

```bash
# 1. Enter the project folder
cd telegram_bot

# 2. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Configuration

Copy `.env.example` to `.env` and fill in every value:

```bash
cp .env.example .env
```

| Variable | Where to get it |
|---|---|
| `TELEGRAM_BOT_TOKEN` | [@BotFather](https://t.me/BotFather) → `/newbot` |
| `PERSON_X_CHAT_ID` | Send a message to [@userinfobot](https://t.me/userinfobot) from that person's account |
| `PERSON_Y_CHAT_ID` | Same as above |
| `GOOGLE_SERVICE_ACCOUNT_FILE` | Path to your downloaded service account JSON key (e.g. `credentials.json`) |
| `GOOGLE_CALENDAR_ID` | The calendar to watch — use `primary` for your main calendar, or paste the calendar's email address from Google Calendar settings |
| `GOOGLE_BOOKING_URL` | Your Google Calendar Appointment Scheduling link (the shareable booking page URL) |
| `GOOGLE_WEBHOOK_TOKEN` | Any random secret string you invent — Google will echo it back so you can verify requests |
| `WEBHOOK_HOST` | Your public URL, e.g. `https://yourdomain.com` or your ngrok URL |
| `WEBHOOK_PORT` | Port uvicorn listens on (default: `8000`) |

---

## Google Cloud Setup

### 1. Create a service account

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → **IAM & Admin → Service Accounts**
2. Click **Create Service Account**, give it a name, click **Done**
3. Click the service account → **Keys** → **Add Key → Create new key → JSON**
4. Download the JSON file and place it in the project folder
5. Set `GOOGLE_SERVICE_ACCOUNT_FILE` to its filename (e.g. `credentials.json`)

### 2. Enable the Google Calendar API

In Google Cloud Console → **APIs & Services → Library** → search **Google Calendar API** → **Enable**.

### 3. Share your calendar with the service account

1. Open [Google Calendar](https://calendar.google.com/)
2. Find the calendar you want to use → **⋮ → Settings and sharing**
3. Under **Share with specific people**, add the service account email (looks like `name@project.iam.gserviceaccount.com`)
4. Grant it **See all event details** permission

### 4. Add a custom question to your booking page

In Google Calendar → your appointment schedule → **Edit** → **Booking questions** → **Add question**:

- **Question:** `What is your Telegram username? (e.g. @username)`
- **Required:** Yes (recommended)

This is how the bot matches a Google Calendar booking to a Telegram user.

### 5. The webhook is registered automatically

On startup, `main.py` calls `setup_calendar_watch()` which registers a push notification channel with Google Calendar. Google will POST to `https://<WEBHOOK_HOST>/webhook/google-calendar` when bookings are created. No manual webhook setup required.

> **Note:** Google Calendar push notification channels expire after up to 7 days. The bot re-registers on every restart. For long-running deployments, restart the bot at least weekly or add a periodic renewal task.

---

## Running the Bot

```bash
python main.py
```

This starts both the Telegram polling bot and the uvicorn webhook server in a single process. No separate processes needed.

Press `Ctrl+C` to stop. The bot shuts down gracefully.

---

## Editing Contact Info

Open `messages.py` and update this line:

```python
CONTACT_INFO = "[CONTACT INFO — TO BE FILLED IN LATER]"
```

No other file needs to change.

---

## Project Structure

```
telegram_bot/
├── main.py              # Entry point — starts bot + FastAPI together
├── bot.py               # All Telegram handlers and conversation logic
├── scheduler.py         # APScheduler setup, job restore on restart, job functions
├── database.py          # All DB operations (aiosqlite), schema creation
├── google_calendar.py   # Google Calendar webhook endpoint + matching logic
├── config.py            # Loads .env, exposes typed config constants
├── messages.py          # All user-facing strings (edit here, not in bot.py)
├── requirements.txt
├── .env.example
└── README.md
```

The SQLite database (`bot.db`) is created automatically in the working directory on first run.

---

## Restart Safety

Pending scheduled jobs (follow-ups and meeting reminders) are stored in the `scheduled_jobs` table. On every startup, `main.py` restores all unsent future jobs into APScheduler automatically — no reminders are lost if the process restarts.

---

## Conversation Flows

```
/start
  └── Choose program (SAT / Admissions / Full Support)
        └── Ask a Question
              ├── Contact info sent
              └── 10h later: "Was your issue resolved?"
                    ├── Yes → resolved
                    └── No  → escalate to PERSON_X

        └── Register / Book a Meeting
              ├── Google Calendar booking link sent
              ├── "Have you completed your booking?"
              │     ├── Not yet → resend link
              │     └── Yes     → awaiting_match
              └── Google Calendar webhook fires
                    ├── Match by Telegram username (from intake question)
                    ├── 60m before meeting → remind user + PERSON_Y
                    └── 10m before meeting → remind user + PERSON_Y
```
# freshbot
# freshbot
