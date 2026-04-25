# All user-facing strings live here.
# Use .format(**kwargs) when sending — never hardcode these elsewhere.

# ---------------------------------------------------------------------------
# Contact info placeholder — edit this when ready
# ---------------------------------------------------------------------------
CONTACT_INFO = "[CONTACT INFO — TO BE FILLED IN LATER]"

# ---------------------------------------------------------------------------
# /start
# ---------------------------------------------------------------------------
WELCOME = "Hi {first_name}! Welcome. Please choose your program:"

# ---------------------------------------------------------------------------
# Program chosen
# ---------------------------------------------------------------------------
PROGRAM_CHOSEN = "Great choice! What would you like to do?"

# ---------------------------------------------------------------------------
# Ask a Question flow
# ---------------------------------------------------------------------------
CONTACT_MESSAGE = "You can reach us at: {contact_info}"

FOLLOWUP_QUESTION = (
    "Hi {first_name}, was your issue resolved?"
)

RESOLVED_YES_REPLY = (
    "Great! Glad your issue was resolved. Feel free to reach out anytime."
)

RESOLVED_NO_USER_REPLY = (
    "We've alerted our team. Someone will reach out shortly!"
)

ESCALATION_TO_PERSON_X = (
    "\U0001f6a8 URGENT: User @{username} ({first_name}) has an unresolved issue.\n"
    "Chat ID: {chat_id}. Please respond immediately."
)

# Used when user has no @username
ESCALATION_TO_PERSON_X_NO_USERNAME = (
    "\U0001f6a8 URGENT: User {first_name} (ID: {chat_id}) has an unresolved issue.\n"
    "Please respond immediately."
)

# ---------------------------------------------------------------------------
# Register / Book a Meeting flow
# ---------------------------------------------------------------------------
BOOKING_INTRO = "Please use the link below to book your session:"

BOOKING_CONFIRM_PROMPT = "Have you completed your booking?"

BOOKING_NOT_YET_REPLY = "No problem! Here's the link again: {booking_url}"

BOOKING_CONFIRMED_REPLY = (
    "Perfect! We'll send you a reminder before your meeting."
)

# ---------------------------------------------------------------------------
# Reminders (sent to user)
# ---------------------------------------------------------------------------
REMINDER_TO_USER = (
    "\u23f0 Reminder: Your meeting is in {minutes} minutes!\n"
    "See you soon, {first_name}."
)

# ---------------------------------------------------------------------------
# Reminders (sent to PERSON_Y)
# ---------------------------------------------------------------------------
REMINDER_TO_PERSON_Y = (
    "\U0001f4c5 Meeting in {minutes} minutes with @{username} ({first_name}).\n"
    "Chat ID: {chat_id}."
)

REMINDER_TO_PERSON_Y_NO_USERNAME = (
    "\U0001f4c5 Meeting in {minutes} minutes with {first_name} (ID: {chat_id})."
)

# ---------------------------------------------------------------------------
# /cancel
# ---------------------------------------------------------------------------
CANCEL_REPLY = "Session reset. Type /start to begin."

# ---------------------------------------------------------------------------
# Button labels
# ---------------------------------------------------------------------------
BTN_SAT = "SAT Program"
BTN_ADMISSIONS = "Admissions Program"
BTN_FULL_SUPPORT = "Full Support Program"

BTN_ASK_QUESTION = "Ask a Question"
BTN_REGISTER = "Book an Interview"

BTN_YES_RESOLVED = "Yes \u2705"
BTN_NO_RESOLVED = "No \u274c"

BTN_YES_BOOKED = "Yes, I booked \u2705"
BTN_NO_BOOKED = "Not yet \u274c"

BTN_BACK = "\u2b05\ufe0f Back"
BTN_START = "/start"
