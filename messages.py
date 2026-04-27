# All user-facing strings live here.
# Use .format(**kwargs) when sending — never hardcode these elsewhere.

# ---------------------------------------------------------------------------
# /start
# ---------------------------------------------------------------------------
WELCOME = "Hi {first_name}! Welcome to Freshman Academy . Please choose the program of interest:"

# ---------------------------------------------------------------------------
# Program chosen
# ---------------------------------------------------------------------------

# Edit each description below when ready — keep the dict keys matching the button labels exactly
PROGRAM_DESCRIPTIONS = {
    "SAT Program": (
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
        "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua."
    ),
    "Admissions Program": (
        "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris "
        "nisi ut aliquip ex ea commodo consequat."
    ),
    "Full Support Program": (
        "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum "
        "dolore eu fugiat nulla pariatur."
    ),
}

PROGRAM_CHOSEN = "Great choice!\n\n{description}\n\nWhat would you like to do?"
PROGRAM_BACK = "{description}\n\nWhat would you like to do?"

# ---------------------------------------------------------------------------
# FAQ — edit questions and answers below as needed
# ---------------------------------------------------------------------------
FAQ_ITEMS = [
    (
        "What programs do you offer?",
        "We offer three programs: SAT Prep, University Admissions (AP), and Full Support (FS).",
    ),
    (
        "How long does the program last?",
        "Duration varies by package. Book a consultation to get personalized information.",
    ),
    (
        "How much does it cost?",
        "Pricing depends on the program and package you choose. Book a free consultation for details.",
    ),
    (
        "How do I book a session?",
        "Tap 'Book an interview' in the menu to schedule a session via our calendar.",
    ),
    (
        "Can I switch programs?",
        "Yes! Reach out to our team and we will help you transition.",
    ),
]

_faq_lines = "\n\n".join(
    f"{i + 1}. {q}\n{a}" for i, (q, a) in enumerate(FAQ_ITEMS)
)
FAQ_MESSAGE = (
    "Here are some frequently asked questions:\n\n"
    + _faq_lines
    + "\n\n───\nDid this answer your question?"
)

FAQ_TYPE_QUESTION = (
    "Please type your question below and our team will get back to you shortly:"
)

QUESTION_FORWARDED = (
    "✅ Your question has been forwarded to our team! You will receive an answer here shortly."
)

EXPERT_QUESTION = (
    "❓ New question from {first_name}{username_part} (Program: {program}):\n\n"
    "{question}\n\n"
    "Reply to this message to send your answer to the student."
)

ANSWER_FROM_EXPERT = "\U0001f4ac Our team answered your question:\n\n{answer}"

EXPERT_REPLY_SENT = "✅ Your answer has been sent to the student."

EXPERT_ALREADY_ANSWERED = "ℹ️ This question has already been answered by another person."

EXPERT_REPLY_NOT_FOUND = (
    "Could not find the question you are replying to. It may have already been answered."
)

EXPERT_USE_REPLY = (
    "To answer a student’s question, please use Telegram’s reply feature "
    "on the question message."
)

EXPERT_CLARIFY_USE_REPLY = (
    "To send a clarification, reply to the original question message first, then send /clarify."
)

EXPERT_CLARIFY_READY = (
    "Got it! Send your clarification message now (just type it — no need to reply)."
)

EXPERT_CLARIFY_SENT = "✅ Clarification sent to the student."

CLARIFICATION_FROM_EXPERT = "📝 Clarification from our team:\n\n{answer}"

# ---------------------------------------------------------------------------
# Ask a Question flow
# ---------------------------------------------------------------------------
FOLLOWUP_QUESTION = (
    "Hi {first_name}, did you receive an answer to your question?"
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
    "Program: {program}\n"
    "See you soon, {first_name}."
)

# ---------------------------------------------------------------------------
# Reminders (sent to PERSON_Y)
# ---------------------------------------------------------------------------
REMINDER_TO_PERSON_Y = (
    "\U0001f4c5 Meeting in {minutes} minutes with @{username} ({first_name}).\n"
    "Program: {program}\n"
    "Chat ID: {chat_id}."
)

REMINDER_TO_PERSON_Y_NO_USERNAME = (
    "\U0001f4c5 Meeting in {minutes} minutes with {first_name} (ID: {chat_id}).\n"
    "Program: {program}"
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

BTN_ASK_QUESTION = "Ask a question"
BTN_REGISTER = "Book an interview"

BTN_FAQ_YES = "Yes, it's answered \u2705"
BTN_FAQ_NO = "No, I have another question \u274c"

BTN_YES_RESOLVED = "Yes \u2705"
BTN_NO_RESOLVED = "No \u274c"

BTN_YES_BOOKED = "Yes, I booked \u2705"
BTN_NO_BOOKED = "Not yet \u274c"

BTN_BACK = "\u2b05\ufe0f Back"
BTN_START = "Fresh Start"

