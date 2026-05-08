from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_LEFT, TA_CENTER

OUTPUT = "Expert_Bot_Guide.pdf"

doc = SimpleDocTemplate(
    OUTPUT,
    pagesize=A4,
    leftMargin=2.5 * cm,
    rightMargin=2.5 * cm,
    topMargin=2.5 * cm,
    bottomMargin=2.5 * cm,
)

styles = getSampleStyleSheet()

title_style = ParagraphStyle(
    "Title",
    parent=styles["Normal"],
    fontSize=22,
    fontName="Helvetica-Bold",
    textColor=colors.HexColor("#1a1a2e"),
    spaceAfter=6,
    alignment=TA_CENTER,
)
subtitle_style = ParagraphStyle(
    "Subtitle",
    parent=styles["Normal"],
    fontSize=12,
    fontName="Helvetica",
    textColor=colors.HexColor("#555555"),
    spaceAfter=20,
    alignment=TA_CENTER,
)
section_style = ParagraphStyle(
    "Section",
    parent=styles["Normal"],
    fontSize=13,
    fontName="Helvetica-Bold",
    textColor=colors.HexColor("#1a1a2e"),
    spaceBefore=18,
    spaceAfter=6,
)
body_style = ParagraphStyle(
    "Body",
    parent=styles["Normal"],
    fontSize=10.5,
    fontName="Helvetica",
    textColor=colors.HexColor("#333333"),
    leading=16,
    spaceAfter=6,
)
bullet_style = ParagraphStyle(
    "Bullet",
    parent=body_style,
    leftIndent=16,
    bulletIndent=4,
    spaceAfter=4,
)
note_style = ParagraphStyle(
    "Note",
    parent=body_style,
    fontSize=10,
    textColor=colors.HexColor("#555555"),
    leftIndent=12,
    fontName="Helvetica-Oblique",
)
code_style = ParagraphStyle(
    "Code",
    parent=styles["Normal"],
    fontSize=10.5,
    fontName="Courier-Bold",
    textColor=colors.HexColor("#d63031"),
    backColor=colors.HexColor("#f5f5f5"),
    leftIndent=12,
    spaceAfter=4,
    leading=16,
)

def section(text):
    return Paragraph(text, section_style)

def body(text):
    return Paragraph(text, body_style)

def bullet(text):
    return Paragraph(f"• {text}", bullet_style)

def note(text):
    return Paragraph(f"ℹ {text}", note_style)

def code(text):
    return Paragraph(text, code_style)

def sp(n=1):
    return Spacer(1, n * 0.3 * cm)

def hr():
    return HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#dddddd"), spaceAfter=4)

story = []

# ── Title ──────────────────────────────────────────────────────────────────
story.append(sp(2))
story.append(Paragraph("Freshman Bot", title_style))
story.append(Paragraph("Expert User Guide", subtitle_style))
story.append(hr())
story.append(sp())

# ── Overview ───────────────────────────────────────────────────────────────
story.append(section("Overview"))
story.append(body(
    "The Freshman Bot receives questions from students and routes them directly to you "
    "in Telegram. Your job is simple: read the question, reply to it, and the student "
    "instantly receives your answer. No app switching, no dashboards — everything happens "
    "inside Telegram."
))

story.append(sp())
story.append(note("Important: You must start a chat with the bot before you can receive any questions. Open the bot and tap Start."))

# ── Getting Started ────────────────────────────────────────────────────────
story.append(section("Getting Started"))
story.append(body("Before the bot can send you questions, complete these two steps:"))
story.append(bullet("Open the Freshman Bot in Telegram."))
story.append(bullet("Tap <b>Start</b> (or send /start). This allows the bot to message you."))
story.append(bullet("Ask your admin to run <b>/pingexperts</b> to confirm you are reachable."))

# ── How Questions Arrive ───────────────────────────────────────────────────
story.append(section("How Questions Arrive"))
story.append(body(
    "When a student submits a question, you receive a message from the bot that looks like this:"
))
story.append(sp(0.5))

sample_data = [
    ["❓ New question from Ali (@ali123) (Program: SAT):\n\n"
     "When does the next SAT prep course start?\n\n"
     "Reply to this message to send your answer to the student."]
]
t = Table(sample_data, colWidths=[14 * cm])
t.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0f4ff")),
    ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#1a1a2e")),
    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
    ("FONTSIZE", (0, 0), (-1, -1), 10),
    ("LEADING", (0, 0), (-1, -1), 15),
    ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#b0bec5")),
    ("ROWPADDING", (0, 0), (-1, -1), 10),
]))
story.append(t)
story.append(sp())

# ── Answering a Question ───────────────────────────────────────────────────
story.append(section("Answering a Question"))
story.append(body(
    "To answer a question, you <b>must use Telegram's reply feature</b> on the question message:"
))
story.append(bullet("Long-press (mobile) or right-click (desktop) the question message."))
story.append(bullet("Tap <b>Reply</b>."))
story.append(bullet("Type your answer and send."))
story.append(sp(0.5))
story.append(body("The student receives your answer immediately. You will see:"))
story.append(code("✅ Your answer has been sent to the student."))
story.append(sp(0.5))
story.append(note(
    "Do NOT send a new message without replying — the bot won't know which student to forward it to."
))

# ── Sending a Clarification ────────────────────────────────────────────────
story.append(section("Sending a Clarification"))
story.append(body(
    "If a question has already been answered but you want to add more information:"
))
story.append(bullet("Reply to the original question message."))
story.append(bullet("Send the command:"))
story.append(code("/clarify"))
story.append(bullet("Type your clarification and send it (no need to reply this time)."))
story.append(sp(0.5))
story.append(body("The student receives the clarification along with the full conversation history."))

# ── Commands Reference ─────────────────────────────────────────────────────
story.append(section("Commands Reference"))

cmd_data = [
    ["Command", "What it does"],
    ["/clarify", "Add a follow-up to a question you already answered.\nReply to the question first, then send /clarify."],
]
cmd_table = Table(cmd_data, colWidths=[4 * cm, 10 * cm])
cmd_table.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 10),
    ("LEADING", (0, 0), (-1, -1), 15),
    ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f9f9f9")),
    ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#333333")),
    ("FONTNAME", (0, 1), (0, -1), "Courier-Bold"),
    ("FONTNAME", (1, 1), (1, -1), "Helvetica"),
    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
    ("ROWPADDING", (0, 0), (-1, -1), 8),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
]))
story.append(cmd_table)

# ── Common Errors ──────────────────────────────────────────────────────────
story.append(section("Common Situations"))

err_data = [
    ["Situation", "What to do"],
    [
        "You type a message without replying",
        "Bot tells you to use the reply feature. Long-press the question and tap Reply."
    ],
    [
        "Question was already answered",
        "Bot says it's already answered. Use /clarify (with a reply) to add more info."
    ],
    [
        "You don't receive any questions",
        "You may not have started the bot. Open it and tap Start, then ask admin to run /pingexperts."
    ],
]
err_table = Table(err_data, colWidths=[5.5 * cm, 8.5 * cm])
err_table.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 10),
    ("LEADING", (0, 0), (-1, -1), 15),
    ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f9f9f9")),
    ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#333333")),
    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
    ("ROWPADDING", (0, 0), (-1, -1), 8),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
]))
story.append(err_table)

# ── Expert Account Limitations ────────────────────────────────────────────
story.append(section("Expert Account Limitations"))
story.append(body(
    "Your Telegram account is registered as an expert account. "
    "This means the bot is configured to route student questions to you — "
    "it is <b>not a student account</b>. The following features are <b>not available</b> "
    "to you when using the bot from your expert account:"
))
story.append(bullet("Browsing programs (SAT, Admissions, Full Support, etc.)"))
story.append(bullet("Getting booking or registration links"))
story.append(bullet("Submitting questions as a student"))
story.append(bullet("Any other student-facing menu or flow"))
story.append(sp(0.5))
story.append(note(
    "If you need to use the bot as a student, do so from a separate personal Telegram account "
    "that is not registered as an expert."
))

# ── Quick Checklist ────────────────────────────────────────────────────────
story.append(section("Quick Checklist"))
story.append(bullet("I have opened the bot and tapped <b>Start</b>."))
story.append(bullet("Admin has confirmed I am reachable via <b>/pingexperts</b>."))
story.append(bullet("I know to <b>reply</b> to the question message to send my answer."))
story.append(bullet("I know to use <b>/clarify</b> (with a reply) for follow-up information."))

story.append(sp(3))
story.append(hr())
story.append(Paragraph("Freshman Education · Bot Support Guide", ParagraphStyle(
    "Footer",
    parent=styles["Normal"],
    fontSize=8,
    textColor=colors.HexColor("#aaaaaa"),
    alignment=TA_CENTER,
)))

doc.build(story)
print(f"Created: {OUTPUT}")
