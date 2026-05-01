# All user-facing strings live here.
# Use .format(**kwargs) when sending — never hardcode these elsewhere.

# ---------------------------------------------------------------------------
# /start
# ---------------------------------------------------------------------------
WELCOME = "Hi {first_name}! Welcome to Freshman Academy. What would you like to do?"

# ---------------------------------------------------------------------------
# Program chosen
# ---------------------------------------------------------------------------

# Edit each description below when ready — keep the dict keys matching the button labels exactly
PROGRAM_DESCRIPTIONS = {
    "SAT Program": (
        "Lorem ipsum dolor sit amet, consectetur adipisicing elit. "
        "Temporibus nemo iusto at autem similique reiciendis itaque esse quasi reprehenderit iure."
    ),
    "Admissions Program": (
        "Lorem ipsum dolor sit, amet consectetur adipisicing elit. "
        "Deleniti maxime esse eligendi cum iure repellat eos ducimus fugiat est expedita."
    ),
    "Full Support Program": (
        "Lorem ipsum dolor sit amet consectetur adipisicing elit. "
        "Ipsa doloribus numquam maiores commodi quibusdam molestiae placeat ipsum eveniet dignissimos totam!"
    ),
    "Advanced Placement": (
        "Lorem, ipsum dolor sit amet consectetur adipisicing elit. "
        "Ullam tempore cumque soluta nemo nobis ipsa, perspiciatis officia doloremque earum ab."
    ),
    "Imkon": (
        "Lorem ipsum dolor sit amet, consectetur adipisicing elit. "
        "Voluptate, necessitatibus ex! Quia magni cupiditate mollitia ab impedit ad cum doloribus?"
    ),
}

_program_list = "\n\n".join(
    f"{name}\n{desc}" for name, desc in PROGRAM_DESCRIPTIONS.items()
)
CHOOSE_PROGRAM = _program_list + "\n\nChoose your program:"

PROGRAMS_COMING_SOON = "🚧 This section is coming soon. Stay tuned!"

PROGRAM_CHOSEN = "Great choice!\n\n{description}\n\nWhat would you like to do?"
PROGRAM_BACK = "{description}\n\nWhat would you like to do?"

# ---------------------------------------------------------------------------
# FAQ — edit questions and answers below as needed
# ---------------------------------------------------------------------------
FAQ_ITEMS = [
    (
        "What programs do you offer?",
        "We offer three programs: SAT Prep, Admissions Program (AP), and Full Support (FS).",
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
        "Tap 'Reserve a spot' in the menu to schedule a session via our calendar.",
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

GENERAL_INQUIRY_INTRO = (
    "You can browse our FAQs below, or ask our team directly if you still have a question."
)

FAQ_TYPE_QUESTION = (
    "Please type your question below and our team will get back to you shortly:"
)

FOLLOWUP_TYPE_QUESTION = (
    "Please type your follow-up question and we'll get back to you shortly:"
)

FOLLOWUP_FORWARDED = (
    "✅ Your follow-up has been forwarded! You will receive a reply here shortly."
)

FOLLOWUP_NO_PREVIOUS = (
    "You don't have any previous answered questions to follow up on."
)

EXPERT_FOLLOWUP = (
    "🔄 Follow-up from {first_name}{username_part} (Program: {program}):\n\n"
    "{followup}\n\n"
    "─── Previous conversation ───\n"
    "❓ {original_question}\n"
    "💬 {expert_answer}\n\n"
    "Reply to this message to send your answer to the student."
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
WEBSITE_LINK_INTRO = "Here is the relevant section of our website:"

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
BTN_PROGRAMS = "📚 Programs"
BTN_GET_LINK = "🔗 Get Event Link"

BTN_SAT = "SAT Program"
BTN_ADMISSIONS = "Admissions Program"
BTN_FULL_SUPPORT = "Full Support Program"
BTN_ADV_PLACEMENT = "Advanced Placement"
BTN_IMKON = "Imkon"

BTN_GENERAL_INQUIRY = "💬 General Inquiry"
BTN_ASK_QUESTION = "Ask a question"
BTN_REGISTER = "Reserve a spot"

BTN_FAQ_YES = "Yes, it's answered \u2705"
BTN_FAQ_NO = "No, I have another question \u274c"

BTN_YES_RESOLVED = "Yes \u2705"
BTN_NO_RESOLVED = "No \u274c"

BTN_YES_BOOKED = "Yes, I booked \u2705"
BTN_NO_BOOKED = "Not yet \u274c"

BTN_BACK = "\u2b05\ufe0f Back"
BTN_HOME = "\U0001f3e0 Home"
BTN_START = "Fresh Start"

# ---------------------------------------------------------------------------
# Event gate \u2014 student flow
# ---------------------------------------------------------------------------
EG_NOT_MEMBER = (
    "To access this event, you need to join the following first:\n"
    "{links}\n\n"
    "Once you've joined, tap the button below."
)

EG_CHECK_AGAIN_BUTTON = "I've joined \u2014 check again \u2705"

EG_NO_ACTIVE_EVENT = "There is no active event at the moment. Check back soon!"

EG_INVITE_SENT = (
    "Here is your personal link to join the event group "
    "(valid for {expiry_hours} hours, one use only):\n"
    "{link}\n\n"
    "Do not share this link \u2014 it will only work once."
)

EG_MISSING_CHAT = "\u2022 {name} \u2192 {invite}"

# ---------------------------------------------------------------------------
# Event gate \u2014 admin flow (PERSON_X only)
# ---------------------------------------------------------------------------
EG_EVENT_ACTIVATED = (
    "\u2705 Event activated! Students who tap 'Get Event Link' will receive the event "
    "post and a unique invite link. The previous event (if any) has been deactivated."
)

EG_ADMIN_STATUS_TEMPLATE = (
    "\ud83d\udccc Current event:\n"
    "Status: {status}\n"
    "Post set: {post_set}\n"
    "Last updated: {last_updated}\n"
    "Links issued: {links_issued}\n"
    "Join approvals: {join_approvals}"
)

EG_ADMIN_EVENT_CLEARED = "Event cleared. Students will see 'no active event'."

SETVIDEO_CHOOSE_PROGRAM = "Which program do you want to set the intro video for?"
SETVIDEO_SEND_VIDEO = "Got it! Now send the video for *{program}*."
SETVIDEO_SAVED = "✅ Intro video saved for {program}."
SETVIDEO_NOT_VIDEO = "That doesn't look like a video file. Please send a video."

EG_ADMIN_HELP = (
    "Event gate admin commands:\n"
    "/event \u2014 set up a new event (will ask for group ID then post)\n"
    "/status \u2014 show current event status and stats\n"
    "/clearevent \u2014 deactivate current event\n"
    "/help \u2014 show this message"
)

