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
        "This program is for students who want more than just SAT prep. You'll be in an environment with admissions-focused mentors and driven peers, gaining early exposure to the college admissions world while improving your SAT."
    ),
    "Admissions Program": (
        "🎓 Build Your Competitive Admissions Plan\n\n"
        "The Admissions Program 2026 offers the most impactful educational experience in Freshman's history.\n\n"
        "Over the next months, you will write 25,000+ words essays and read hundreds of pages of undergraduate literature, thus experiencing education at the Ivy League and other competitive universities.\n\n"
        "Our past graduates launched startups, wrote world-class undergraduate research, received summer school scholarships, started passion projects, and many more."
    ),
    "Full Support Program": (
        "🏆 Harvard, Yale, Princeton, Columbia, and Duke Full-Ride Scholarships — Full Support makes dreams possible!\n\n"
        "Full Support is our most comprehensive and personalized admissions program.\n\n"
        "Every year, we select 12–15 ambitious students applying to selective American universities.\n\n"
        "In the past three years, over 80% of our students were accepted to top U.S. and global universities."
    ),
    "AP Classes": (
        "AP Classes by Freshman Academy are preparatory courses for AP exams led by well-qualified mentors, available in both individual and group formats.\n\n"
        "We cover theory, practice questions, and authentic mock exams to fully prepare you and maximize your score."
    ),
    "Imkon": (
        "Imkon Scholars is a free, high-impact admissions preparation program designed to help talented, underserved students gain access to top global universities.\n\n"
        "Spearheaded by Freshman Academy, scholars are provided mentorship, writing support, and research guidance. The program aims to bridge the gap between talent and opportunity."
    ),
    "Research Institute": (
        "The Freshman Research Institute advances the research skills of high school, undergraduate, and graduate students.\n\n"
        "Our program supports students at any stage of their research — whether in ideating, evaluation of sources, writing, and editing.\n\n"
        "This is a unique opportunity to turn your research ideas into potential publications, elevating your profile for academic and career advancement."
    ),
    "Advanced English": (
        "Advanced English is designed to help you get your level of English to an entirely new level. "
        "As a part of the class, you will learn to critically assess texts and effectively communicate your thoughts in your written works. "
        "This class is also perfect for those who want to get a taste of and prepare for quality international education.\n\n"
        "Note that Advanced English will most certainly be the most challenging English class you have ever had."
    ),
    "Master's Support": (
        "Master's Support is Freshman's comprehensive admissions program for students pursuing graduate education at top global universities.\n\n"
        "What's included:\n\n"
        "📄 Research Proposal — We assess your proposal and strengthen your thesis to meet your target program's requirements.\n\n"
        "🗓 Application Timeline & Strategy — We map out a strategic admissions calendar tailored to your availability and deadlines.\n\n"
        "🔍 Overall Profile Assessment — We review your full application for consistency and alignment with your target programs.\n\n"
        "✍️ Statement of Purpose — We guide you through the entire writing process, from initial notes to final draft.\n\n"
        "📝 Additional Essays — Close guidance and detailed feedback on every supplemental essay.\n\n"
        "🎯 Program Selection — We match you to programs that fit your interests, career path, and profile."
    ),
}

CHOOSE_PROGRAM = "Choose your program:"

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

AP_FAQ_ITEMS = [
    (
        "Will I be expelled if I miss a lesson or homework submission?",
        "Missing a class or assignment without appropriate justification would result in expulsion without a refund.\n\n"
        "The Admissions Program has historically attracted some of Central Asia's most academically talented and ambitious students.\n\n"
        "Thus, this rule aims to ensure that the participants get the most out of the Program, transforming their applications before university deadlines.",
    ),
    (
        "Why is the Admissions Program so cheap or expensive?",
        "Interestingly, we receive both questions equally often.\n\n"
        "The reason behind the Admissions Program's low prices, relative to companies with similar track record to ours, lies in our passionate team. We work at a discounted rate to assist students from the post-Soviet space in their admissions aspirations.\n\n"
        "However, we still need to fairly compensate our highly skilled consultants. Running the Admissions Program demands a large amount of resources, which are used to fund our team and also ensure that we overdeliver on our promises, supporting you beyond the application deadlines.",
    ),
    (
        "How do you select students?",
        "Although aspects like test scores are considered, we typically look beyond academics into your life story.\n\n"
        "Ideally, we seek academically promising students with some extracurricular experiences and a track record of discipline, relentlessness, high integrity, and a commitment to excellence in whatever they do.\n\n"
        "Even if you are unsure, you can still apply. Our team will be happy to evaluate your application and offer you other options — Private Consultations or Full Support — to support your educational endeavors.",
    ),
    (
        "How hard is it to be accepted to the Admissions Program?",
        "In the last admissions cycle, we received over 320 applications, out of which we selected 60+ students.\n\n"
        "However, with this year's improved curriculum and increased personalization, we plan to admit only 17 ambitious students per cohort.",
    ),
    (
        "I have high SAT and IELTS scores. Will I be admitted to the program?",
        "US universities usually value your academics (test scores, GPA, etc.) at only 30% of your entire application.\n\n"
        "Similarly, we seek students who demonstrate immense capability beyond academia, evaluated through a holistic consideration of your entire profile including your academics, extracurriculars, and other contexts.",
    ),
    (
        "My family can afford the program. Can I still apply for Co-op Assistance?",
        "Co-op Assistance is strictly for families who truly cannot afford the Admissions Program.\n\n"
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

ADV_PLACEMENT_FAQ_ITEMS = [
    (
        "What AP subjects do you offer?",
        "Currently, we offer AP Microeconomics, AP Macroeconomics, AP Calculus AB, and AP Calculus BC. "
        "We plan to expand our subject list soon — please stay tuned for updates.",
    ),
    (
        "Who is this program designed for?",
        "The program is designed for high school students and gap-year students who want to master college-level material and prepare for the official AP exams.",
    ),
    (
        "How do I enroll in a course?",
        'To begin the process, please fill out our official <a href="https://forms.gle/FWYA8UDZwkVLWUkV8">enrollment form</a>.',
    ),
    (
        "Are there specific prerequisites or grade requirements?",
        "Requirements vary by subject. To ensure you are placed in the right level, we offer a free consultation with a mentor once you apply.",
    ),
    (
        "Do you offer a trial class?",
        "Yes, trial classes are available for students who wish to experience our teaching style before committing.",
    ),
    (
        "Can I join multiple courses at once?",
        "Yes. Our team will help you build a non-overlapping schedule and can provide specialized course packages.",
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

MS_FAQ_ITEMS = [
    (
        "What is the cost of Master's Support?",
        "The pricing will depend on the selected Master's programs and the estimated level of support.",
    ),
    (
        "How do you select students?",
        "Although aspects like test scores are crucial, we typically look beyond academics into your life story and professional experience.\n\n"
        "Ideally, we seek academically stellar students with strong professional achievements and a track record of discipline, relentlessness, high integrity, and a commitment to excellence in whatever they do.\n\n"
        "However, we still encourage you to apply regardless of your achievements. Our team will be happy to evaluate your application and offer you other options — Private Consultations or Short Programs — to support your educational endeavors.",
    ),
    (
        "Can you prepare students for GRE or GMAT?",
        "Yes! We can prepare you for GRE and/or GMAT at an additional cost.",
    ),
    (
        "How long does the program last?",
        "As the \"Master's Support\" name suggests, our program lasts until the admissions process is fully finalized.\n\n"
        "Our work typically extends until March of the following year, when you have your interviews.",
    ),
    (
        "What is the deadline for application?",
        "There is no priority deadline — we accept students on a rolling basis.",
    ),
    (
        "Does Freshman offer financial assistance?",
        "Due to the high operational costs of the program, Freshman will not be offering financial assistance for Master's applicants.\n\n"
        "However, if you would like us to review your essay at an affordable price, consider Freshman's Consultations.",
    ),
]

AE_PROGRAM_FAQ_ITEMS = [
    (
        "Who is this program best suited for?",
        "If you are tired of simply learning English and want to transition to discussing solid concepts in English instead, then the program is best suited for you. "
        "It is also meant for those who want to train academic rigor and the capacity to handle a workload level beyond traditional curricula. "
        "Another type of people are those who use it as a stepping stone to first train and then transition into harder programs at Freshman. "
        "Lastly, any ages and occupations are welcome, meaning our cohorts are diverse in both criteria.",
    ),
    (
        "Is Advanced English good for improving my English?",
        "Yes, but not in a traditional way. There won't be memorizing of grammar rules, yet the foundational skills you will build throughout the program (reading, writing, critical thinking) will help you with a range of English-related activities—be it taking the SAT or writing your own research paper.",
    ),
    (
        "Can you give a brief explanation of the course's structure and design?",
        "Students read and analyze fundamental texts on all topics, including but not limited to undergraduate education, technology, philosophy, history, and social sciences. "
        "We will engage in seminar-style discussions, write critical reflections that force us to articulate complicated arguments with clarity and precision, learn basic research concepts so you know how to back up your claims with evidence, and navigate an undergraduate-level workload to build the stamina required for higher education.",
    ),
    (
        "Are there eligibility criteria for AE? Can I apply even if I don't have IELTS?",
        "The only requirement to take Advanced English is English proficiency. An IELTS score of 7.0+ is ideal. "
        "However, if there is some other way to demonstrate your proficiency, that also works: e.g., an SAT English section score, experience studying abroad, or a quick interview with one of our mentors.",
    ),
    (
        "Do you select students for the program, or is it first-come, first-served?",
        "Most of the students applying on time will be admitted unless the groups for the cohorts are full or you lack English proficiency.",
    ),
    (
        "Is the July cohort going to be any different from June?",
        "Every new cohort will have a brand-new curriculum and, this time around, it will be even better-structured and engaging. "
        "Additionally, we are adding weekly homework reviews with the TAs to get feedback on your writing!",
    ),
    (
        "Is there an online program this time?",
        "Yes, but please note that the online curriculum will match the June offline curriculum. "
        "We are also expecting a larger cohort for the July offline program, which offers you the opportunity to visit us at Nest One and join our future in-person events.",
    ),
    (
        "What's included?",
        "✅ 8 Seminars\n"
        "✅ Q&A sessions\n"
        "✅ Weekly Homework\n"
        "✅ New Curriculum\n"
        "✅ Presentation Review\n"
        "✅ Freshman Alumni Network Membership\n"
        "✅ Access to the Nest One Co-working Space",
    ),
]

SAT_FAQ_MESSAGE = _build_faq_message(SAT_FAQ_ITEMS)
FS_FAQ_MESSAGE = _build_faq_message(FS_FAQ_ITEMS)
AP_FAQ_MESSAGE = _build_faq_message(AP_FAQ_ITEMS)
ADV_PLACEMENT_FAQ_MESSAGE = _build_faq_message(ADV_PLACEMENT_FAQ_ITEMS)
MS_FAQ_MESSAGE = _build_faq_message(MS_FAQ_ITEMS)
RI_FAQ_MESSAGE = _build_faq_message(RI_FAQ_ITEMS)
IMKON_FAQ_MESSAGE = _build_faq_message(IMKON_FAQ_ITEMS)
PARTNERSHIPS_FAQ_MESSAGE = _build_faq_message(PARTNERSHIPS_FAQ_ITEMS)
AE_PROGRAM_FAQ_MESSAGE = _build_faq_message(AE_PROGRAM_FAQ_ITEMS)

# Lookup: program button label → FAQ message. Programs absent from this dict show no FAQ.
PROGRAM_FAQ_MESSAGE: dict[str, str] = {
    "SAT Program": SAT_FAQ_MESSAGE,
    "Admissions Program": AP_FAQ_MESSAGE,
    "Full Support Program": FS_FAQ_MESSAGE,
    "Master's Support": MS_FAQ_MESSAGE,
    "AP Classes": ADV_PLACEMENT_FAQ_MESSAGE,
    "Research Institute": RI_FAQ_MESSAGE,
    "Imkon": IMKON_FAQ_MESSAGE,
    "Advanced English": AE_PROGRAM_FAQ_MESSAGE,
}

FAQ_TYPE_QUESTION = (
    "Please type your question below and our team will get back to you shortly.\n\n"
    "💡 Already received an answer and want to continue the conversation? Use /followup."
)

FOLLOWUP_CHAIN_CONTEXT = (
    "─── Previous conversation ───\n"
    "❓ {original_question}\n\n"
    "💬 {expert_answer}"
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

EXPERT_QUESTION_REISSUED = (
    "❓ Question #{question_id} from {first_name}{username_part} "
    "(Program: {program}, asked {date}):\n\n"
    "{question}\n\n"
    "Reply to this message to send your answer to the student."
)

Q_ANSWER_RESENT = "Question sent below — reply to that message to answer."

Q_ANSWER_GONE = "This question no longer exists in the database."

# Skip — dismiss a duplicate or spam question without replying to the student
BTN_Q_SKIP = "⏭ Skip"

Q_SKIP_NOTE = "\n\n⏭ Skipped — no answer was sent to the student."

Q_SKIP_DONE = "Skipped. The student was not notified."

Q_SKIP_RESTORED = "Restored to unanswered."

Q_SKIP_NOT_SKIPPED = "This question is not skipped — nothing to restore."

ANSWER_FROM_EXPERT = "💬 Our team answered your question:\n\n❓ {question}\n\n{answer}"

EXPERT_REPLY_SENT = "✅ Your answer has been sent to the student."

EXPERT_ALREADY_ANSWERED = "ℹ️ This question has already been answered by another person."

EXPERT_ALREADY_SKIPPED = (
    "ℹ️ This question was skipped. Use /skipped to restore it if you want to answer after all."
)

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
    "🚨 URGENT: User @{username} ({first_name}) has an unresolved issue.\n"
    "Chat ID: {chat_id}\n\n"
    "❓ Their question:\n{question}\n\n"
    "Please respond immediately."
)

ESCALATION_TO_PERSON_X_NO_USERNAME = (
    "🚨 URGENT: User {first_name} (ID: {chat_id}) has an unresolved issue.\n\n"
    "❓ Their question:\n{question}\n\n"
    "Please respond immediately."
)

ESCALATION_TO_EXPERT = (
    "⚠️ {first_name}{username_part} has not received an answer yet.\n\n"
    "❓ Their question:\n{question}\n\n"
    "Please reply as soon as possible."
)

# ---------------------------------------------------------------------------
# Register / Book a Meeting flow
# ---------------------------------------------------------------------------
WEBSITE_LINK_INTRO = "Here is the relevant section of our website:"
SAT_BOOKING_INTRO = "Use the link below to book your SAT consultation:"
AP_CLASSES_REGISTER_INTRO = "Please fill out the form below to enroll in AP Classes:"

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
BTN_CLICK_TO_JOIN = "Click to join! 🎉"

BTN_SAT = "SAT Program"
BTN_ADMISSIONS = "Admissions Program"
BTN_FULL_SUPPORT = "Full Support Program"
BTN_MASTERS = "Master's Support"
BTN_ADV_PLACEMENT = "AP Classes"
BTN_IMKON = "Imkon"
BTN_RESEARCH_INSTITUTE = "Research Institute"
BTN_ADV_ENGLISH_PROGRAM = "Advanced English"

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
BTN_PODCAST = "\U0001f399 Early Access: Freshman Podcast"

PODCAST_COMING_SOON = "\U0001f512 Early Access to Freshman Podcast is coming soon. Stay tuned!"

PODCAST_MUST_JOIN = (
    "To access the Freshman Podcast, please subscribe to the following channels first:\n"
    "{channel_list}\n\n"
    "Once you've subscribed, tap the button below."
)

PODCAST_ACCESS_GRANTED = (
    "\U0001f399 Welcome to Freshman Podcast \u2014 Early Access!\n\n"
    "Here is your link:\n{youtube_url}"
)

BTN_PODCAST_CHECK = "\u2705 I've subscribed \u2014 check again"

BTN_ADMISSIONS_APPLY = "\U0001f4dd Learn More & Apply"
ADMISSIONS_APPLY_URL = "https://freshman.academy/admissions"

# ---------------------------------------------------------------------------
# College Admissions Guidebook (SAT Freshman) \u2014 subscribe to both channels,
# then get the PDF. The intro is admin-editable via /set_guidebook_intro, so
# GUIDEBOOK_INTRO_DEFAULT is only the fallback until one is saved.
# ---------------------------------------------------------------------------

BTN_GET_GUIDEBOOK = "\U0001f4d8 College Admissions Guidebook"

GUIDEBOOK_INTRO_DEFAULT = (
    "\U0001f4da <b>Your Complete College Admissions Guidebook is Here</b>\n\n"
    "Applying to college can feel overwhelming \u2014 essays, deadlines, "
    "requirements, strategy. We put together a full step-by-step guidebook.\n\n"
    "Information you\u2019ll find inside:\n\n"
    "1. Where to start your admissions journey\n"
    "2. What steps to take, and in what order\n"
    "3. Timeline breakdown\n\n"
    "To get your free copy:\n"
    "Subscribe to @freshmanblog &amp; @satfreshman \U0001f393"
)

BTN_GUIDEBOOK_GET = "\U0001f4e5 Get the guidebook"

GUIDEBOOK_MUST_JOIN = (
    "To get the <b>College Admissions Guidebook</b>, please subscribe to both "
    "channels first:\n"
    "{channel_list}\n\n"
    "Once you\u2019ve subscribed, tap the button below."
)

BTN_GUIDEBOOK_CHECK = "\u2705 I\u2019ve subscribed \u2014 check again"

GUIDEBOOK_ACCESS_GRANTED = (
    "\U0001f4d8 You\u2019re all set \u2014 here\u2019s your <b>College Admissions "
    "Guidebook</b>. Enjoy!"
)

GUIDEBOOK_UNAVAILABLE = (
    "\U0001f512 The College Admissions Guidebook isn\u2019t available right now. "
    "Please check back soon!"
)

GUIDEBOOK_COMING_SOON = (
    "\U0001f6a7 The College Admissions Guidebook is coming soon. Stay tuned!"
)

GUIDEBOOK_INTRO_SET_USAGE = (
    "Send the intro text with the command, or reply to the message you want to "
    "use:\n\n"
    "<code>/set_guidebook_intro Your intro text here</code>\n\n"
    "Formatting from the replied-to message (bold, italic, links) is kept. "
    "Send <code>/set_guidebook_intro reset</code> to go back to the default."
)
GUIDEBOOK_INTRO_SET_SUCCESS = (
    "\u2705 Guidebook intro saved. Here\u2019s how it will look:"
)
GUIDEBOOK_INTRO_RESET = "\u2705 Guidebook intro reset to the default."

GUIDEBOOK_SET_USAGE = (
    "Reply to the guidebook PDF with /set_guidebook to save it. Without one the "
    "bot sends assets/guidebook/college_admissions.pdf."
)
GUIDEBOOK_SET_SUCCESS = "\u2705 College Admissions Guidebook file saved successfully."

# ---------------------------------------------------------------------------
# Top 10 Mistakes handbook (Freshman Global) — subscribe to both channels,
# then get the PDF. The intro is admin-editable via /set_handbook_intro, so
# HANDBOOK_INTRO_DEFAULT is only the fallback until one is saved.
# ---------------------------------------------------------------------------

BTN_HANDBOOK = "\U0001f4d5 Top 10 Mistakes Handbook"

HANDBOOK_INTRO_DEFAULT = (
    "\U0001f4d5 <b>Top 10 Mistakes Freshman Global Applicants Make</b>\n\n"
    "We put together the ten mistakes we see most often in applications \u2014 "
    "and exactly how to avoid each one.\n\n"
    "Tap below to get your free copy."
)

BTN_HANDBOOK_GET = "\U0001f4e5 Get the handbook"

HANDBOOK_MUST_JOIN = (
    "To get the <b>Top 10 Mistakes Handbook</b>, please subscribe to both "
    "channels first:\n"
    "{channel_list}\n\n"
    "Once you\u2019ve subscribed, tap the button below."
)

BTN_HANDBOOK_CHECK = "\u2705 I\u2019ve subscribed \u2014 check again"

HANDBOOK_ACCESS_GRANTED = (
    "\U0001f4d5 You\u2019re all set \u2014 here\u2019s your <b>Top 10 Mistakes "
    "Handbook</b>. Enjoy!"
)

HANDBOOK_UNAVAILABLE = (
    "\U0001f512 The Top 10 Mistakes Handbook isn\u2019t available right now. "
    "Please check back soon!"
)

HANDBOOK_COMING_SOON = (
    "\U0001f6a7 The Top 10 Mistakes Handbook is coming soon. Stay tuned!"
)

HANDBOOK_INTRO_SET_USAGE = (
    "Send the intro text with the command, or reply to the message you want to "
    "use:\n\n"
    "<code>/set_handbook_intro Your intro text here</code>\n\n"
    "Formatting from the replied-to message (bold, italic, links) is kept. "
    "Send <code>/set_handbook_intro reset</code> to go back to the default."
)
HANDBOOK_INTRO_SET_SUCCESS = (
    "\u2705 Handbook intro saved. Here\u2019s how it will look:"
)
HANDBOOK_INTRO_RESET = "\u2705 Handbook intro reset to the default."

HANDBOOK_SET_USAGE = (
    "Reply to the handbook PDF with /set_handbook to save it. Without one the "
    "bot sends assets/handbook/top10_mistakes.pdf."
)
HANDBOOK_SET_SUCCESS = "\u2705 Top 10 Mistakes Handbook file saved successfully."

BTN_GETTING_IN = "\u2728 Getting In: Manzilbek Karlibaev"

GETTING_IN_INTRO = (
    "\U0001f44b Welcome to the <b>Freshman Getting In Series, Episode XIII</b>!\n\n"
    "We're excited to have you with us for our upcoming conversation with "
    "<b>Manzilbek Karlibaev</b>, a graduate of the Presidential School in Nukus "
    "who was admitted to <b>KAIST</b> (Korea Advanced Institute of Science and "
    "Technology) with a full-ride scholarship worth over $29,000 to study "
    "Artificial Intelligence and Machine Learning.\n\n"
    "\U0001f4cd Before joining the event group, please take a moment to review "
    "our <b>Community Guidelines</b>:\n\n"
    "(1) The group is exclusively for communication related to the Getting In "
    "Series. Please keep discussions relevant to the event.\n\n"
    "(2) Promotional content, advertisements, external opportunities, and "
    "personal projects may only be shared with prior approval from the "
    "Freshman team. If you'd like to share something, please contact "
    "@ValeriyaNizhnikova, the host of the event.\n\n"
    "(3) Please be respectful, supportive, and engaged. We create these events "
    "not only to help you learn from exceptional speakers, but also to connect "
    "you with ambitious, like-minded people.\n\n"
    "\U0001f4f2 <b>The Zoom link will be shared in the event group 10 minutes "
    "before the session.</b>\n\n"
    "We're looking forward to your questions and hope you'll actively "
    "participate in the discussion!\n\n"
    "\u27a1\ufe0f <b>Join the event group here:</b>"
)

BTN_GETTING_IN_JOIN = "\U0001f517 Join the group chat"

GETTING_IN_COMING_SOON = (
    "🚧 Getting In with Manzilbek Karlibaev is coming soon. Stay tuned!"
)

BTN_ADV_ENGLISH = "Special Offer \u2013 Advanced English"


AE_INTRO = (
    "\U0001f4a5<b>Special Offer: Advanced English</b>\n\n"
    "<b>What is included?</b>\n\n"
    "✅ 8 Offline Seminars\n"
    "✅ Q&amp;A sessions\n"
    "✅ Weekly Homework\n"
    "✅ New Curriculum\n"
    "✅ Presentation Review\n"
    "✅ Freshman Alumni Network Membership\n"
    "✅ Access to the Nest One Co-working Space\n\n"
    "\U0001f4cd <b>Where:</b> <a href=\"https://yandex.uz/maps/-/CPftJ6OW\">Freshman Office</a>\n"
    "\U0001f4c5 <b>When:</b> Sundays and Wednesdays from 1:00 PM to 2:30 PM\n\n"
    "\U0001f525 <b>Early Offer: $149</b> — apply by <b>June 24</b>!\n"
    "After June 24: $169"
)

BTN_AE_APPLY_NOW = "Apply Now"

AE_ASK_FORMAT = "Will you be joining Online or Offline?"
BTN_AE_ONLINE = "\U0001f5a5️ Online"
BTN_AE_OFFLINE = "\U0001f3eb Offline"

AE_ALREADY_APPLIED = "You've already applied. We'll be in touch!"

AE_STATUS_PENDING = "⏳ Your application is under review. We’ll notify you of the decision soon."
AE_STATUS_PAYMENT_PENDING = "⏳ Your payment screenshot is under review. We’ll notify you shortly."
AE_STATUS_PAYMENT_CONFIRMED = "✅ Your payment was confirmed. You should have received your group invite link in a previous message."

AE_STUCK_REMINDER = (
    "Hello, this is Gulrukh, an Advanced English Leader at Freshman! "
    "I’m also a rising junior at University of Pennsylvania, majoring in Political Science and History.\n\n"
    "I noticed that you may be stuck on one of the steps in the application for the Advanced English program.\n\n"
    "I wanted to reassure you that all of the information you submit through the application bot will be viewed "
    "only by me. There is also just one day left to apply, in case you’ve been putting it off!\n\n"
    "If you have any questions about the program — whether you’re unsure what it involves, "
    "whether it’s the right fit for you, or anything else — please feel free to reach out to me "
    "on Telegram (@gulyashskartoshkoy).\n\n"
    "Best regards,\nGulrukh Sodikova"
)
AE_STUCK_DONE = "AE stuck reminder sent: {sent} delivered, {failed} failed ({total} total)."

AE_PAYMENT_DEADLINE = (
    "⏰ <b>Reminder: the deadline to complete your Advanced English payment is May 25.</b>\n\n"
    "If you encounter any problems with the payment, please message @gulyashskartoshkoy."
)
AE_PAYMENT_DEADLINE_DONE = "Payment deadline reminder sent: {sent} delivered, {failed} failed ({total} total)."

AE_REMIND_CLOSING = (
    "⏰ <b>Tonight is your last chance to apply for Advanced English!</b>\n\n"
    "Applications close at midnight — now is the time.\n"
    "Don’t miss your spot! Takes just a few minutes \U0001f447"
)
AE_REMIND_DONE = "AE reminder sent: {sent} delivered, {failed} failed ({total} total)."
AE_REMIND_USAGE = "Usage: /ae_remind 3 (or 2 or 1)"

AE_PROMPT_FULL_NAME = "Please enter your full name:"

AE_PROMPT_VIDEO = (
    "Please record a 1-minute video message in this chat introducing yourself \u2014 "
    "who you are, where you\u2019re from, and what draws you to language and learning.\n\n"
    "\U0001f512 <b>Confidentiality notice:</b> Your video will only be seen by our admissions team "
    "and will not be shared with anyone outside of Freshman. It is used solely to evaluate your application."
)

AE_VIDEO_REQUIRED = (
    "Please send a video message in this chat to continue. "
    "Record a short introduction (about 1 minute) and send it here."
)

AE_PROMPT_IELTS = (
    "Please send a screenshot or file of your IELTS certificate."
)

AE_IELTS_REQUIRED = (
    "Please send a photo or file of your IELTS certificate to continue."
)

AE_PROMPT_SAT = (
    "What is your SAT Evidence-Based Reading & Writing (EBRW) score? "
    "If you don't have an SAT score, write N/A."
)

AE_PROMPT_WHY = "Why do you want to join Advanced English? (50\u2013100 words)"

AE_PROMPT_PERSPECTIVE = (
    "What is a topic, book, or idea you have encountered recently that completely changed "
    "your perspective on a subject? (75\u2013100 words)"
)

AE_PROMPT_RESOURCES = (
    "List texts, resources, and outlets that have shaped your intellectual development \u2014 "
    "books, journals, podcasts, essays, videos, or other content you value. (up to 100 words)"
)

AE_WORD_COUNT_TOO_SHORT = (
    "Your answer is too short ({count} words — minimum {min}). Please expand and try again."
)
AE_WORD_COUNT_TOO_LONG = (
    "Your answer is too long ({count} words — maximum {max}). Please shorten and try again."
)
AE_WORD_COUNT_EXACT = (
    "Your answer must be exactly {exact} words (yours: {count}). Please adjust and try again."
)

AE_SUBMITTED = (
    "Thank you! Your application has been submitted. We\u2019ll notify you of the decision."
)

AE_ACCEPTED = (
    "\U0001f389Congratulations on your acceptance! \n\n"
    "To secure your place, please complete your payment. Immediately afterward, you will receive a link "
    "to join our group and access all important updates, such as homework instructions and information.\n\n"
    "Best regards,\n"
    "Gulrukh Sodikova\n"
    "Advanced English Leader"
)

AE_PAYMENT_HELP = (
    "If you encounter any problems, dm @gulyashskartoshkoy"
)

AE_TERMS_CAPTION = (
    "\U0001f4dc Please read and sign the terms and conditions below to complete your enrollment."
)

AE_SET_TERMS_SUCCESS = "\u2705 Terms & Conditions PDF saved successfully."
AE_SET_TERMS_USAGE = "Reply to a PDF document with /ae_set_terms to save it."

BTN_AE_ACCEPT_TERMS = "\u2705 I have read and accept the terms"

AE_PAYMENT_NOT_SET = "\U0001f4b3 Please make the payment and tap the button below once done."
BTN_AE_PAYMENT_MADE = "\U0001f4b3 I\u2019ve made the payment \u2014 share screenshot"

AE_PAYMENT_SCREENSHOT_PROMPT = (
    "Please send a screenshot confirming your payment."
)
AE_PAYMENT_SCREENSHOT_REQUIRED = "Please send a photo or document screenshot of your payment to continue."

AE_PAYMENT_SUBMITTED = "\u23f3 Your payment screenshot is under review. We\u2019ll notify you shortly!"

AE_PAYMENT_CONFIRMED = (
    "\u2705 <b>Payment confirmed!</b>\n\n"
    "Welcome to Advanced English! Here is your one-time invite link to join the group:\n{link}"
)
AE_PAYMENT_REJECTED = (
    "\u274c Your payment screenshot wasn\u2019t approved.\n\n"
    "Please double-check and send a new screenshot confirming your payment."
)

AE_PAYMENT_REVIEWER_ENTRY = (
    "\U0001f4b8 Payment screenshot from {first_name}{username_part}"
)
BTN_AE_CONFIRM_PAYMENT = "\u2705 Confirm Payment"
BTN_AE_REJECT_PAYMENT = "\u274c Reject"
AE_PAYMENT_REVIEWER_CONFIRMED = "\u2705 Payment confirmed. Invite link sent to applicant."
AE_PAYMENT_REVIEWER_REJECTED = "\u274c Payment rejected. Applicant notified."
AE_PAYMENT_ALREADY_DECIDED = "\u2139\ufe0f Decision already recorded for this payment."

AE_SET_PAYMENT_SUCCESS = "\u2705 Payment post saved."
AE_SET_PAYMENT_USAGE = "Reply to any message with /ae_set_payment to save it as the payment post."

AE_REJECTED = "Thank you for applying. Unfortunately, you have not been accepted at this time."

AE_REVIEWER_CAPTION = "\U0001f4cb New Advanced English application from {first_name}{username_part}"

BTN_AE_ACCEPT = "\u2705 Accept"
BTN_AE_REJECT = "\u274c Reject"

AE_REVIEWER_ACCEPTED = "\u2705 Accepted. Applicant has been notified."
AE_REVIEWER_REJECTED = "\u274c Rejected. Applicant has been notified."
AE_REVIEWER_ALREADY_DECIDED = "\u2139\ufe0f Decision already recorded for this application."


# ---------------------------------------------------------------------------
# SAT Program Enrollment
# ---------------------------------------------------------------------------

BTN_SAT_ENROLL = "Enroll at SAT Program"
BTN_SAT_ONLINE = "\U0001f5a5\ufe0f Online"
BTN_SAT_OFFLINE = "\U0001f3eb Offline"

SAT_ENROLL_INFO = (
    "\U0001f393 <b>Online SAT Program by Freshman Academy</b>\n\n"
    "In our SAT program, you\u2019ll learn alongside admissions-focused mentors "
    "and driven peers, gaining early exposure to the college admissions world while improving your SAT.\n\n"
    "\U0001f4b8 <b>Price:</b> <s>$240</s> $90/month (EID offer)\n\n"
    "To enroll, fill in the short form below and our team will reach out to you shortly."
)

SAT_ENROLL_ASK_FORMAT = "Will you be joining Online or Offline?"
SAT_ENROLL_ASK_NAME = "What\u2019s your name?"
SAT_ENROLL_ASK_HISTORY = (
    "Have you taken the SAT before?\n\n"
    "If yes, what was your score? If not, just type \u201cNo\u201d."
)
SAT_ENROLL_ASK_DATE = "When would you like to take the test? (e.g. \u201cJune 2025\u201d or a specific date)"
SAT_ENROLL_SUBMITTED = "\u2705 Thank you! Freshman Team will reach out to you soon!"
SAT_ENROLL_EXPERT_ENTRY = (
    "\U0001f4cb New SAT Program enrollment\n"
    "From: <a href=\"tg://user?id={chat_id}\">{first_name}</a>{username_part}\n\n"
    "<b>Format:</b> {format_type}\n"
    "<b>Name:</b> {full_name}\n"
    "<b>SAT History:</b> {sat_history}\n"
    "<b>Desired Test Date:</b> {test_date}"
)

# ---------------------------------------------------------------------------
# Economics Olympiad Prep — broadcast + registration flow
# ---------------------------------------------------------------------------
ECON_OLYMPIAD_INTRO = (
    "\U0001f3c6 <b>Free International Economics Olympiad Prep</b>\n\n"
    "Now, you can get a chance to prepare for the <b>International Economics Olympiad</b> "
    "in our <b>Olympiad Prep Program</b> at <b>completely no cost</b> by registering for our "
    "AP Micro and/or Macroeconomics courses.\n\n"
    "Don’t miss the chance to make your Honors section shine even brighter. "
    "To register, tap the button below \U0001f447"
)
BTN_ECON_JOIN = "\U0001f3c6 Join now!"

ECON_ASK_NAME = "What’s your full name?"
ECON_ASK_COURSES = (
    "Which course(s) would you like to register for?\n\n"
    "Tap to select — you can choose more than one — then tap ✅ Done."
)
BTN_ECON_MACRO = "AP Macroeconomics"
BTN_ECON_MICRO = "AP Microeconomics"
BTN_ECON_CALC_BC = "AP Calculus BC"
BTN_ECON_PHYSICS = "AP Physics I"
BTN_ECON_DONE = "✅ Done"
ECON_NO_COURSES = "Please select at least one course before tapping ✅ Done."
ECON_SUBMITTED = "✅ Thank you! Freshman Team will reach out to you soon!"
ECON_EXPERT_ENTRY = (
    "\U0001f3c6 New Olympiad Prep registration\n"
    "From: <a href=\"tg://user?id={chat_id}\">{first_name}</a>{username_part}\n\n"
    "<b>Name:</b> {full_name}\n"
    "<b>Courses:</b> {courses}"
)

# ---------------------------------------------------------------------------
# Merch shop — catalog + order flow
# ---------------------------------------------------------------------------

BTN_MERCH = "🛍 Freshman Academy Merch"

MERCH_COMING_SOON = (
    "🚧 Freshman Academy merch is coming soon. Stay tuned!"
)

# (key, label, price in UZS). The key doubles as the merch_buy: callback suffix
# and the catalog photo filename (assets/merch/<key>.jpg — the pen has no photo
# yet, so it appears in the price list and item picker but not the album).
MERCH_ITEMS = [
    ("notebook", "Notebook", 90000),
    ("pen", "Pen", 25000),
    ("pencil", "Pencil", 20000),
    ("tshirt", "T-shirt", 120000),
    ("cap", "Cap", 120000),
    ("mug", "Mug", 120000),
    ("bag", "Bag", 120000),
]

# /broadcastkeyboard announcement — the inline button opens the catalog.
MERCH_ANNOUNCE = (
    "🛍 <b>Freshman Academy merch is out</b>\n\n"
    "Notebooks, pens, pencils, t-shirts, caps, mugs and tote bags — "
    "20,000 to 120,000 UZS. Pick up from the office or get it delivered.\n\n"
    "Tap below to browse and order."
)
BTN_MERCH_BROWSE = "🛍 Browse the merch"

MERCH_CATALOG_CAPTION = (
    "🛍 <b>Freshman Academy Merch</b>\n\n"
    "Rep the Freshman! Here's what's available:\n\n"
    "{items}"
)
MERCH_CATALOG_ITEM_LINE = "• <b>{label}</b> — {price} UZS"
MERCH_CHOOSE_ITEM = (
    "Tap an item to add it to your cart — add as many as you like, "
    "then check out. 👇"
)
MERCH_QTY_PROMPT = "<b>{label}</b> — {price} UZS each.\n\nHow many would you like?"
BTN_MERCH_QTY_BACK = "⬅️ Back"
BTN_MERCH_REMOVE = "🗑 Remove from cart"
BTN_MERCH_CHECKOUT = "🛒 Checkout"
MERCH_CART_EMPTY = "Your cart is empty — tap an item first."
MERCH_CART_LINE = "• {label} ×{qty} — {line_total} UZS"
MERCH_CART_SUMMARY = "\n\n🛒 <b>Your cart</b>\n{lines}\n<b>Total:</b> {total} UZS"
MERCH_ASK_NAME = "What's your full name?"
MERCH_ASK_DELIVERY = "How would you like to receive your order?"
BTN_MERCH_PICKUP = "🏢 Pick up from the office"
BTN_MERCH_DELIVERY = "🚚 Delivery"
BTN_MERCH_SHARE_PHONE = "📱 Share my phone number"
MERCH_ASK_PHONE = (
    "What's a working phone number for the delivery?\n\n"
    "Tap the button below to share it, or type it in."
)
MERCH_PHONE_INVALID = (
    "Hmm, that doesn't look like a phone number — please send a working phone number."
)
MERCH_ASK_ADDRESS = "What address should we deliver your order to?"
# Shared purchase summary — shown to the buyer at the payment step and
# forwarded to PERSON_X.
MERCH_ORDER_SUMMARY = (
    "{lines}\n"
    "<b>Total:</b> {total} UZS\n\n"
    "<b>Name:</b> {full_name}\n"
    "<b>Delivery:</b> {delivery}{delivery_details}"
)
MERCH_PAYMENT_QR = (
    "✅ Your order is in!\n\n"
    "{summary}\n\n"
    "💳 Final step — pay the total via Payme by scanning the QR code above.\n\n"
    "Once the payment is through, our team will confirm your order. Thank you! 💙"
)
MERCH_PAYMENT_PENDING = (
    "✅ Your order is in!\n\n"
    "{summary}\n\n"
    "💳 Final step — payment via Payme. Our team will contact you shortly. "
    "Thank you! 💙"
)
MERCH_ORDER_FORWARD = (
    "🛍 New merch order\n"
    "From: <a href=\"tg://user?id={chat_id}\">{first_name}</a>{username_part}\n\n"
    "{summary}"
)
MERCH_ORDER_DELIVERY_DETAILS = (
    "\n<b>Phone:</b> {phone}\n"
    "<b>Address:</b> {address}"
)
MERCH_LIST_EMPTY = "No merch orders yet."
MERCH_QR_PROMPT = (
    "Send me the Payme QR code as a photo — it will be shown at every merch "
    "order's payment step."
)
MERCH_QR_SAVED = "✅ Payme QR saved. Merch orders will now end with this QR code."

# ---------------------------------------------------------------------------
# SAT Freshman — free SAT strategy consultations (subscription giveaway)
# ---------------------------------------------------------------------------

BTN_SAT_CONSULT = "📚 SAT Freshman - Free Consultations"

SATC_COMING_SOON = (
    "🚧 Free SAT strategy consultations are coming soon. Stay tuned!"
)

SATC_INTRO = (
    "📚 <b>SAT Freshman — Free SAT Strategy Consultations</b>\n\n"
    "The SAT Freshman is giving away free SAT strategy consultations to "
    "everyone who just wants to start studying for SAT or taking it soon!\n\n"
    "During the consultation, we will help you identify your weak areas and "
    "build a preparation strategy.\n\n"
    "To claim your free consultation, follow the steps below!"
)

# /broadcastkeyboard giveaway announcement — the menu flow keeps SATC_INTRO.
SATC_ANNOUNCEMENT = (
    "🎁 <b>New Giveaway: Free SAT Strategy Consultations!</b>\n\n"
    "The SAT Freshman is giving away free SAT strategy consultations to "
    "everyone who just wants to start studying for SAT or taking it soon!\n\n"
    "During the consultation, we will help you identify your weak areas and "
    "build a preparation strategy.\n\n"
    "<b>How to claim your consultation:</b>\n"
    "1️⃣ Subscribe to @satfreshman and @freshmanblog\n"
    "2️⃣ Tap the button below\n"
    "3️⃣ Book a time slot"
)

# The inline button under the announcement runs the subscription gate.
BTN_SATC_OPEN = "📅 Claim your free consultation"

SATC_MUST_JOIN = (
    "To claim your free SAT consultation, please subscribe to both channels "
    "first:\n"
    "{channel_list}\n\n"
    "Once you've subscribed, tap the button below."
)

BTN_SATC_CHECK = "✅ I've subscribed — check again"

SATC_ACCESS_GRANTED = (
    "✅ You're all set — book your free SAT strategy consultation below!"
)

BTN_SATC_BOOK = "🗓 Book your consultation"

SATC_LIST_EMPTY = "No one has claimed an SAT consultation yet."

# Shown to anyone tapping a leftover button under the retired Freshman Global
# free-consultations announcement.
CONSULT_ENDED = (
    "This giveaway has ended. Check the menu for what's running now!"
)

# Shown to anyone tapping a leftover button under the retired Research Program
# Fair x Research Competition announcement.
RF_ENDED = (
    "This event has ended. Check the menu for what’s running now!"
)

# ---------------------------------------------------------------------------
# Consultation Giveaway with Valera — lottery (subscribe → join → /roll)
# ---------------------------------------------------------------------------

BTN_VALERA_GIVEAWAY = "💥 Consultation Giveaway with Valera"

VG_COMING_SOON = (
    "🚧 The Consultation Giveaway with Valera is coming soon. Stay tuned!"
)

VG_INTRO = (
    "💥 <b>Consultation Giveaway with Valera</b>\n\n"
    "Valera, Founder of Freshman Academy, has consulted students admitted to "
    "Harvard, Princeton, Yale, Cornell, Columbia, UPenn, Stanford, "
    "UC Berkeley, Brown, and many more.\n\n"
    "Win <b>3 consultations with Valera</b>, worth <b>$360</b>, by following "
    "the instructions and pressing the button below.\n\n"
    "<b>How to enter:</b>\n"
    "1️⃣ Subscribe to @valeranotes and @freshmanblog\n"
    "2️⃣ Tap the button below to join the draw\n\n"
    "🗓 We will send the results through the bot by September 1."
)

VG_JOIN_PROMPT = "Tap below to join the giveaway:"
BTN_VG_JOIN = "🎉 Join the giveaway"

VG_MUST_JOIN = (
    "To join the giveaway, please subscribe to both channels first:\n"
    "{channel_list}\n\n"
    "Once you've subscribed, tap the button below."
)
BTN_VG_CHECK = "✅ I've subscribed — check again"

VG_ALREADY_PARTICIPATING = (
    "You're already in the draw! We'll announce the winner through the bot. 🎉"
)
VG_NOW_PARTICIPATING = (
    "🎉 You are now participating!\n\n"
    "We will announce the winner through the bot. Good luck!"
)

# /roll and /reroll — winner draw (Person X only)
ROLL_NO_PARTICIPANTS = "No participants yet."
ROLL_ONLY_ONE = "Only one participant — can't pick someone different."
ROLL_USE_FIRST = "Use /roll first."
ROLL_RESULT = '🎲 Result: <a href="tg://user?id={chat_id}">{first_name}</a>{username_part}'
REROLL_RESULT = '🎲 Re-rolled: <a href="tg://user?id={chat_id}">{first_name}</a>{username_part}'

BTN_CONFIRM_WINNER = "✅ Confirm Winner"
BTN_REROLL_INLINE = "🎲 Reroll"

ROLL_CONFIRMING = "⏳ Winner confirmed — notifying {count} participants…"
ROLL_WINNER_NOTIFY = (
    "Congratulations! 🎉\n\n"
    "You have won the Consultation Giveaway with Valera: three consultations "
    "with Valera, Founder of Freshman Academy, worth $360.\n\n"
    "Valera will contact you personally with the next steps."
)
ROLL_LOSER_NOTIFY = (
    "Thank you for participating in the Consultation Giveaway with Valera!\n\n"
    "Unfortunately, you were not selected this time. "
    "Stay tuned, we will be launching more opportunities soon."
)
ROLL_CONFIRMED = "✅ Winner confirmed. Notifications sent: {sent} delivered, {failed} failed."

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
SETVIDEO_SEND_VIDEO = "Got it! Now send the video for *{program}* — a normal video or a round video message both work."
SETVIDEO_SAVED = "✅ Intro video saved for {program}."
SETVIDEO_NOT_VIDEO = "That doesn't look like a video. Please send a normal video or a round video message."

DELETEVIDEO_CHOOSE_PROGRAM = "Which program's intro video do you want to delete?"
DELETEVIDEO_DELETED = "🗑 Intro video deleted for {program}."
DELETEVIDEO_NOT_SET = "No intro video is set for {program}."
DELETEVIDEO_NONE_SET = "No intro videos are set right now."

EG_ADMIN_HELP = (
    "Event gate admin commands:\n"
    "/event \u2014 set up a new event (will ask for group ID then post)\n"
    "/status \u2014 show current event status and stats\n"
    "/clearevent \u2014 deactivate current event\n"
    "/broadcastkeyboard \u2014 push updated menu to all users\n"
    "/help \u2014 show this message"
)

BTN_AE_LEARN_MORE = "📖 Learn More"
BROADCAST_KEYBOARD_MENU_NOTE = "Your menu has been updated \U0001f447"
BROADCAST_KEYBOARD_DONE = "Keyboard broadcast: {sent} sent, {failed} failed ({total} total users)."

# /broadcastkeyboard announces both row-1 lead magnets in one message: the two
# admin-set intros joined by this divider, with a button under each.
BROADCAST_LEAD_MAGNETS_SEPARATOR = "\n\n\u2014\u2014\u2014\n\n"

BROADCAST_TOO_LONG = (
    "\u26a0\ufe0f The two intros come to {length} characters together \u2014 Telegram caps a "
    "message at {limit}. Shorten one with /set_handbook_intro or "
    "/set_guidebook_intro and try again."
)


# ---------------------------------------------------------------------------
# Admin stats
# ---------------------------------------------------------------------------
ADMIN_STATS = (
    "\U0001f4ca Bot Stats\n"
    "\n"
    "\U0001f465 Users\n"
    "  Total: {total_users}\n"
    "  Joined last 7 days: {active_users_7d}\n"
    "  Currently in a flow: {users_in_flow}\n"
    "\n"
    "❓ Questions\n"
    "  \U0001f4e5 Total: {total_questions}\n"
    "  ✅ Answered: {answered_questions}\n"
    "  ⏳ Pending: {pending_questions}\n"
    "{questions_by_program}"
    "\n"
    "⏰ Scheduled jobs pending: {pending_jobs}\n"
    "\n"
    "\U0001f3a5 Intro videos set: {videos_set}\n"
    "\n"
    "\U0001f4da Advanced English Applications\n"
    "  Total: {ae_total}\n"
    "  Pending: {ae_pending}\n"
    "  Accepted: {ae_accepted}\n"
    "  Rejected: {ae_rejected}"
)


# ---------------------------------------------------------------------------
# Trial AP Lesson
# ---------------------------------------------------------------------------

BTN_TRIAL_AP = "Attend Trial AP Lesson"

TAP_COMING_SOON = "🚧 Trial AP Lessons are coming soon. Stay tuned!"

TAP_INTRO = (
    "\U0001f393 <b>Attend a Trial AP Lesson</b>\n\n"
    "To get access to the trial lesson group, here's what to do:\n\n"
    "1⃣ Repost this post to your story or feed:\n"
    "https://t.me/freshmanblog/2209\n\n"
    "2⃣ Tap the button below and send a screenshot of your repost as proof.\n\n"
    "Once our team confirms it, you'll get a one-time invite link to the group."
)

BTN_TAP_JOIN = "Join"
BTN_TAP_SCREENSHOT = "\U0001f4f8 Send screenshot of repost"

TAP_ALREADY_SUBMITTED = (
    "You've already submitted a screenshot. We'll notify you once it's reviewed!"
)

TAP_ALREADY_CONFIRMED = (
    "You're already confirmed! Here's your invite link to the group:\n{link}"
)

TAP_SCREENSHOT_PROMPT = (
    "Send a screenshot of your repost here and we'll review it shortly."
)

TAP_SCREENSHOT_REQUIRED = "Please send a photo or document screenshot to continue."

TAP_SUBMITTED = "⏳ Your screenshot is under review. We'll notify you of the result!"

TAP_CONFIRMED = (
    "✅ Your repost was confirmed! Here's your one-time invite link to the trial lesson group:\n{link}"
)

TAP_REJECTED = (
    "❌ Your screenshot wasn't approved. Make sure it clearly shows your repost, then try again."
)

TAP_REVIEWER_ENTRY = "\U0001f4f8 New Trial AP Lesson repost from {first_name}{username_part}"

TAP_REVIEWER_ACCEPTED = "✅ Confirmed. Invite link sent to the participant."
TAP_REVIEWER_REJECTED = "❌ Rejected. Participant notified."
TAP_REVIEWER_ALREADY_DECIDED = "ℹ️ Decision already recorded for this entry."
TAP_REVIEWER_LINK_FAILED = "⚠️ Confirmed, but creating the invite link failed. Check bot admin rights on the group."

BTN_TAP_APPROVE = "✅ Confirm"
BTN_TAP_REJECT = "❌ Reject"


# ---------------------------------------------------------------------------
# Fireside Chat on Nuclear Justice & Policy (Freshman Research Institute,
# online, 5 September 2026, 5 PM UZT) — tap register, get the Meet link.
# Replaces the Sep 3 Culture & Psyche chat; same fc_ handlers and callback
# data, so stale broadcast buttons now register for this event instead.
# ---------------------------------------------------------------------------

BTN_FIRESIDE_CHAT = "\U0001f4ad Fireside Chat on Nuclear Justice & Policy"

FC_COMING_SOON = (
    "🚧 The Fireside Chat on Nuclear Justice & Policy is coming soon. Stay tuned!"
)

# Sent as the poster's caption, so it must stay under Telegram's 1024-character
# caption limit.
FC_INTRO = (
    "💭 <b>Fireside Chat on Nuclear Justice &amp; Policy</b>\n\n"
    "☢️ What role can Central Asians play in the global nuclear order?\n\n"
    "⚛️ Join the Freshman Research Institute for a discussion with "
    "<b>Yerdaulet Rakhmatulla</b>, who has a wealth of experience in nuclear "
    "activism and policy making from the United Nations to the International "
    "Campaign to Abolish Nuclear Weapons (ICAN).\n\n"
    "🗓 5 September\n"
    "🕔 5 PM UZT\n"
    "💻 Online\n\n"
    "Tap the button below to register — we'll send you the link right away."
)

BTN_FC_REGISTER = "✅ Register for free"

FC_REGISTERED = (
    "🎉 <b>You're registered!</b>\n\n"
    "Join the Fireside Chat on <b>5 September at 5 PM UZT</b> using the button "
    "below. Save the link — it's the same one on the day of the event."
)

BTN_FC_JOIN = "🔗 Join the Fireside Chat"

# Shown on the inline button when someone taps register a second time.
FC_ALREADY_REGISTERED = "You're already registered — the link is in the chat above."

FC_LIST_EMPTY = "No one has registered for the Fireside Chat yet."
