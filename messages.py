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
    "Research Institute": (
        "Lorem ipsum dolor sit amet, consectetur adipisicing elit. "
        "Temporibus nemo iusto at autem similique reiciendis itaque esse quasi reprehenderit iure."
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

def _build_faq_message(items: list[tuple[str, str]]) -> str:
    lines = "\n\n".join(
        f"<b>{i + 1}. {q}</b>\n{a}" for i, (q, a) in enumerate(items)
    )
    return "<b>Frequently Asked Questions</b>\n\n" + lines + "\n\n───\nDid this answer your question?"


SAT_FAQ_ITEMS = [
    (
        "When does the program start and end?",
        "The program runs on a rolling basis, so you can join anytime. The first 2 months focus on core concepts and strategy. After that, Padawan students take a mock test—those who pass move up to the Jedi group, where the focus shifts heavily to advanced practice and score maximization. There, students will be perfecting their test-taking skills for the two following months.",
    ),
    (
        "Who is this program for?",
        "This program is for students who want more than just SAT prep. You'll be in an environment with admissions-focused mentors and driven peers, gaining early exposure to the college admissions world while improving your SAT.",
    ),
    (
        "Are the classes held online or offline?",
        "All classes are conducted in person at the Freshman's Office in the <a href=\"https://maps.app.goo.gl/YZRGrhNwbjwyfB3U7\">NestOne building</a>.",
    ),
    (
        "Who are the mentors?",
        "Mentors are Freshman alumni with more than 1.5+ years of teaching experience and with hundreds of successful students, helping them achieve high SAT results.",
    ),
    (
        "What is the program structure?",
        "Both groups last for two months. There are 12 classes a month, each 1.5 hours long.",
    ),
    (
        "How do you decide which group I fit into?",
        "Our placement is based on a short interview. We consider your academic background, past SAT experience, and mindset to place you in either Padawan or Jedi groups.",
    ),
    (
        "What subjects do you cover?",
        "In the Padawan group, we focus on covering the theory of Math and EBRW. In the Jedi group, we additionally run Critical Reading sessions where you explore advanced texts and essays to strengthen critical thinking and reading comprehension.",
    ),
    (
        "How much time do I need to commit weekly?",
        "It varies from case to case, but you should expect to dedicate at least 20 hours per week outside of class, depending on your starting point, goals, and efficiency.",
    ),
    (
        "How much does the program cost?",
        "Freshman SAT Program is on a promotional price right now, so it costs $120 instead of $240.",
    ),
]

FS_FAQ_ITEMS = [
    (
        "Why is Full Support so expensive/cheap?",
        "Interestingly, we receive both questions equally often.\n\n"
        "The reason behind Full Support's low prices, relative to companies with similar track record to ours, lies in our passionate team. We work at a discounted rate to assist the students from the post-Soviet space in their admissions aspirations.\n\n"
        "However, we still need to fairly compensate our highly skilled consultants. Running Full Support demands a large amount of resources, which are used to fund our team and also ensure that we overdeliver on our promises, supporting you beyond the application deadlines.",
    ),
    (
        "How do you select students?",
        "Although aspects like test scores are crucial, we typically look beyond academics into your life story.\n\n"
        "Ideally, we seek academically stellar students with a solid extracurricular list and a track record of discipline, relentlessness, high integrity, and a commitment to excellence in whatever they do.\n\n"
        "However, every student we admitted had areas that required improvement. Many lacked extracurricular activities when they joined, but showcased immense potential to develop their various involvements.\n\n"
        "Even if you are unsure, you can still apply. Our team will be happy to evaluate your application and offer you other options—Private Consultations or Admissions Programs—to support your educational endeavors.",
    ),
    (
        "How long does the program last?",
        "As the \"Full Support\" name suggests, our program lasts until the admissions process is fully finalized.\n\n"
        "Our work typically extends until March of the following year, when you have your interviews.",
    ),
    (
        "What is the deadline for the program?",
        "Our priority deadline is April 1, during which we typically admit 4–7 students.\n\n"
        "After the deadline passes, we will accept applications on a rolling basis until August.",
    ),
    (
        "How hard is it to be accepted to Full Support?",
        "In the last admissions cycle, we received over 200 applications, out of which we selected 15 students. We plan to admit 15 in 2026 as well.",
    ),
    (
        "My family can afford Full Support. Can I still apply for Co-op assistance?",
        "Co-op Assistance is strictly for families who truly cannot afford Full Support.\n\n"
        "During the application, we will require proof of income and bank statements to verify the applicant's financial status.\n\n"
        "As our resources are limited, we trust applicants who can afford the program will have the integrity to enable low-income families a potentially life-changing opportunity.",
    ),
]

RI_FAQ_ITEMS = [
    (
        "I have no research experience, should I still apply?",
        "Yes, absolutely. This program is designed to support those with little to no research experience. We tailor the program and individual consultations directly to your academic needs.",
    ),
    (
        "Will our meetings be offline or online?",
        "For students based in Tashkent, we offer offline or hybrid formats for our lectures and consultations.",
    ),
    (
        "Will I be expelled if I miss a lesson or homework submission?",
        "Missing a class or assignment without appropriate justification would result in expulsion without a refund.\n\n"
        "Our programs have historically attracted some of Central Asia's most academically talented and ambitious students. This rule aims to ensure that the participants get the most out of the Program, transforming their applications before university deadlines.",
    ),
    (
        "I'm unsure if research is what I need to focus on",
        "Even if you are unsure, we encourage you to reach out to us and we will be open to discuss your academic and career interests to see how we can tailor our program for your needs.",
    ),
]

IMKON_FAQ_ITEMS = [
    (
        "What exactly is Imkon, how is Pre-Imkon different from Imkon?",
        "Pre-Imkon and Imkon Scholars are Freshman-backed free tier admissions guidance. "
        "Pre-Imkon is an admissions program-like course — 8 weeks of structured learning about general admissions, with homework and supplemental sessions, but no individualized consultations or research paper writing. "
        "Imkon Scholars are typically selected students from Pre-Imkon who show a lot of potential and are offered individualized help throughout the entire year up until ED deadlines.",
    ),
    (
        "How many students are accepted to Pre-Imkon and Imkon?",
        "We accept 50 students to Pre-Imkon every year, and 15 students to Imkon Scholars. "
        "Typically 10 Imkon Scholars are chosen from Pre-Imkon, and another 5 are chosen through external applications or active promising students from the Freshman community who are financially eligible.",
    ),
    (
        "What are the eligibility requirements to enroll in Imkon?",
        "We look at a myriad of things: general grades, foundation of admissions knowledge, and depth of writing. "
        "For Pre-Imkon alumni, we also consider rate of growth and how active they were during the program.\n\n"
        "We also have financial criteria. Although it varies slightly by region (with a slightly higher threshold for Tashkent), we are generally aiming to support students whose families earn less than $10,000 in annual income, or less than $3,000 per dependent.",
    ),
    (
        "What is Imkon Scholars?",
        "Imkon Scholars is an admissions support program akin to Full Support. We help students from acceptance (around late May/early June) until ED deadlines.",
    ),
    (
        "What does Imkon provide?",
        "We provide structured guidance, individualized help, and general aid throughout the application process. "
        "We do not cover costs for the CSS Profile, standardized exams (SAT, AP, etc.), or any other forms of direct financial aid.",
    ),
    (
        "Who provides the funding for Imkon?",
        "Our investors have created a fund and donated to the cause, which is what makes Pre-Imkon and Imkon Scholars possible.",
    ),
]

PARTNERSHIPS_FAQ_ITEMS = [
    (
        "What types of partnerships do you offer?",
        "We collaborate with schools, tutoring centers, and educational organizations. "
        "Reach out to discuss what kind of partnership fits your needs.",
    ),
    (
        "How do I start a partnership with Freshman Academy?",
        "Fill out a brief inquiry and our partnerships team will get back to you within 2 business days.",
    ),
    (
        "Are there revenue-sharing or referral programs?",
        "Yes — we have referral and co-branded program options. Our team can walk you through the details.",
    ),
    (
        "What is the typical timeline to get a partnership started?",
        "Most partnerships are set up within 1–2 weeks after initial alignment.",
    ),
    (
        "Who do I contact for partnership questions?",
        "Use this chat — our partnerships team monitors it directly.",
    ),
]

SAT_FAQ_MESSAGE = _build_faq_message(SAT_FAQ_ITEMS)
FS_FAQ_MESSAGE = _build_faq_message(FS_FAQ_ITEMS)
RI_FAQ_MESSAGE = _build_faq_message(RI_FAQ_ITEMS)
IMKON_FAQ_MESSAGE = _build_faq_message(IMKON_FAQ_ITEMS)
PARTNERSHIPS_FAQ_MESSAGE = _build_faq_message(PARTNERSHIPS_FAQ_ITEMS)

# Lookup: program button label → FAQ message. Programs absent from this dict show no FAQ.
PROGRAM_FAQ_MESSAGE: dict[str, str] = {
    "SAT Program": SAT_FAQ_MESSAGE,
    "Full Support Program": FS_FAQ_MESSAGE,
    "Research Institute": RI_FAQ_MESSAGE,
    "Imkon": IMKON_FAQ_MESSAGE,
}

GENERAL_INQUIRY_INTRO = (
    "You can browse our FAQs below, or ask our team directly if you still have a question."
)

GENERAL_INQUIRY_MENU = "Choose a topic:"

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
BTN_RESEARCH_INSTITUTE = "Research Institute"

BTN_GENERAL_INQUIRY = "💬 General Inquiry"
BTN_GENERAL = "General"
BTN_PARTNERSHIPS = "🤝 Partnerships"
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

EG_ALREADY_ISSUED = (
    "You already have a link for this event:\n"
    "{link}\n\n"
    "Do not share it \u2014 it will only work once."
)

QUESTION_TOO_LONG = (
    "Your message is too long (max 1000 characters). Please shorten it and try again."
)

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
    "/broadcastkeyboard \u2014 push updated menu to all users\n"
    "/help \u2014 show this message"
)

BROADCAST_KEYBOARD_MESSAGE = "We\u2019ve updated our menu! Here\u2019s what\u2019s available now \U0001f447"
BROADCAST_KEYBOARD_DONE = "Keyboard broadcast: {sent} sent, {failed} failed ({total} total users)."

ADMIN_STATS = (
    "\U0001f4ca Bot Stats\n"
    "\n"
    "\U0001f465 Users\n"
    "  Total: {total_users}\n"
    "  Joined last 7 days: {active_users_7d}\n"
    "  Currently in a flow: {users_in_flow}\n"
    "\n"
    "❓ Questions\n"
    "  Total: {total_questions}\n"
    "  Pending: {pending_questions}\n"
    "  Answered: {answered_questions}\n"
    "{questions_by_program}"
    "\n"
    "\U0001f4c5 Event Gate\n"
    "  Active event: {active_event}\n"
    "  Links issued (all time): {total_links}\n"
    "  Join approvals (all time): {total_approvals}\n"
    "\n"
    "⏰ Scheduled jobs pending: {pending_jobs}\n"
    "\n"
    "\U0001f3a5 Intro videos set: {videos_set}"
)

