"""Generate the local-setup guide PDF for whoever receives the zipped project.

Run once: python generate_setup_guide.py
Output:    00_START_HERE.pdf  (sorts to the top of the folder so they see it first)
"""
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


# ── Style sheet ───────────────────────────────────────────────────────────
styles = getSampleStyleSheet()

H1 = ParagraphStyle(
    "H1", parent=styles["Heading1"], fontSize=24, spaceAfter=14,
    textColor=colors.HexColor("#0d3b66"), spaceBefore=8, leading=28,
)
H2 = ParagraphStyle(
    "H2", parent=styles["Heading2"], fontSize=16, spaceAfter=10,
    textColor=colors.HexColor("#0d3b66"), spaceBefore=18, leading=20,
)
H3 = ParagraphStyle(
    "H3", parent=styles["Heading3"], fontSize=13, spaceAfter=6,
    textColor=colors.HexColor("#1d5089"), spaceBefore=12, leading=16,
)
BODY = ParagraphStyle(
    "Body", parent=styles["BodyText"], fontSize=11, leading=15.5,
    spaceAfter=8, alignment=TA_JUSTIFY,
)
NOTE = ParagraphStyle(
    "Note", parent=BODY, leftIndent=14, rightIndent=14,
    backColor=colors.HexColor("#fff8dc"),
    borderColor=colors.HexColor("#e6c200"),
    borderWidth=1, borderPadding=8, spaceAfter=12, spaceBefore=8,
)
WARN = ParagraphStyle(
    "Warn", parent=BODY, leftIndent=14, rightIndent=14,
    backColor=colors.HexColor("#ffe4e1"),
    borderColor=colors.HexColor("#c0392b"),
    borderWidth=1, borderPadding=8, spaceAfter=12, spaceBefore=8,
)
TIP = ParagraphStyle(
    "Tip", parent=BODY, leftIndent=14, rightIndent=14,
    backColor=colors.HexColor("#e8f5e9"),
    borderColor=colors.HexColor("#2e7d32"),
    borderWidth=1, borderPadding=8, spaceAfter=12, spaceBefore=8,
)
CODE = ParagraphStyle(
    "Code", parent=BODY, fontName="Courier", fontSize=9.5, leading=13,
    backColor=colors.HexColor("#f4f6f8"),
    borderColor=colors.HexColor("#cfd8dc"),
    borderWidth=0.5, borderPadding=8,
    leftIndent=6, rightIndent=6, spaceAfter=10, spaceBefore=4,
)
COVER_TITLE = ParagraphStyle(
    "CoverTitle", parent=H1, fontSize=34, alignment=TA_CENTER,
    spaceAfter=18, leading=40,
)
COVER_SUB = ParagraphStyle(
    "CoverSub", parent=BODY, fontSize=14, alignment=TA_CENTER,
    textColor=colors.HexColor("#555"), spaceAfter=4,
)


def p(text, style=BODY):
    return Paragraph(text, style)


def code(text):
    return Paragraph(
        text.replace(" ", "&nbsp;").replace("\n", "<br/>"),
        CODE,
    )


def bullet(items):
    return [Paragraph(f"&bull;&nbsp;&nbsp;{i}", BODY) for i in items]


def info_table(headers, rows, col_widths):
    data = [[p(f"<b>{h}</b>") for h in headers]]
    for r in rows:
        data.append([p(c) for c in r])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d3b66")),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("ALIGN",      (0, 0), (-1, -1), "LEFT"),
        ("VALIGN",     (0, 0), (-1, -1), "TOP"),
        ("GRID",       (0, 0), (-1, -1), 0.4, colors.HexColor("#cfd8dc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f4f6f8")]),
        ("FONTSIZE",   (0, 0), (-1, -1), 10),
        ("LEFTPADDING",  (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
    ]))
    return t


def add_page_number(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#777"))
    canvas.drawString(20 * mm, 12 * mm,
        "AI Threat Detection SOC — Setup Guide")
    canvas.drawRightString(A4[0] - 20 * mm, 12 * mm, f"Page {doc.page}")
    canvas.restoreState()


# ── Story ────────────────────────────────────────────────────────────────
story = []

# Cover
story += [
    Spacer(1, 1.6 * inch),
    p("AI THREAT DETECTION SOC", COVER_TITLE),
    p("Local Setup &amp; Run Guide", COVER_SUB),
    Spacer(1, 0.3 * inch),
    p("Read this first. It walks you through installing Python, Node.js, "
      "and pnpm, restoring the project, getting API keys, training the ML "
      "models, and running the full dashboard locally — start to finish, "
      "no shortcuts skipped.",
      COVER_SUB),
    Spacer(1, 0.5 * inch),
    p("Estimated time: <b>20-30 minutes</b> for first-time setup.",
      ParagraphStyle("tag", parent=BODY, alignment=TA_CENTER,
                     fontSize=12, textColor=colors.HexColor("#0d3b66"))),
    PageBreak(),
]

# ── 1. What is this project ──────────────────────────────────────────────
story += [
    p("1. What is this project?", H1),
    p(
        "<b>AI Threat Detection SOC</b> is a full-stack Security Operations "
        "Center dashboard. It uses machine learning to analyze network traffic "
        "in real time, classify threats (DoS, Probe, R2L, U2R), explain "
        "<i>why</i> each alert was triggered using SHAP, detect zero-day "
        "anomalies via Isolation Forest, and generate executive incident "
        "reports using Google Gemini.",
    ),
    p("Two parts, both run on your machine:"),
    *bullet([
        "<b>Backend</b> — a Python Flask API. Loads ML models, serves "
        "predictions and explanations. Runs on <b>localhost:5000</b>.",
        "<b>Frontend</b> — a React dashboard built with Vite. Talks to the "
        "backend over HTTP. Runs on <b>localhost:5173</b> (or 5174).",
    ]),
    p(
        "You'll open both in two separate terminal windows, then point "
        "your browser at localhost:5173.",
        TIP,
    ),
]

# ── 2. What you need to install ──────────────────────────────────────────
story += [
    p("2. Software you need to install", H2),
    p("Three things — install in this order:"),
    info_table(
        ["What", "Version", "Where to download", "Why"],
        [
            ("Python", "3.10 or newer (3.11 best)",
             "python.org/downloads",
             "Backend language. Tick &quot;Add Python to PATH&quot; in the installer."),
            ("Node.js", "20.0 or newer (LTS)",
             "nodejs.org",
             "Required for the frontend build tools."),
            ("pnpm", "10 or newer",
             "After Node, run: <font name='Courier' size='9'>npm install -g pnpm</font>",
             "Faster &amp; lighter than npm. The frontend uses it."),
        ],
        col_widths=[28 * mm, 32 * mm, 50 * mm, 56 * mm],
    ),
    p(
        "<b>Verify installation</b> by opening a fresh terminal (PowerShell or "
        "Command Prompt on Windows, Terminal on Mac/Linux) and running:",
    ),
    code(
        "python --version    # should print 3.10+\n"
        "node --version      # should print v20+\n"
        "pnpm --version      # should print 10+"
    ),
    p(
        "If any command says <i>not recognized</i> or <i>command not found</i>, "
        "the install didn't add it to your PATH. Reinstall with the &quot;Add to PATH&quot; "
        "option enabled, or restart your terminal and try again.",
        WARN,
    ),
]

# ── 3. Get API keys ──────────────────────────────────────────────────────
story += [
    p("3. Get the two API keys", H2),
    p(
        "The dashboard uses two external services. Both have free tiers — "
        "no credit card required. Get the keys before you start so you "
        "don't have to come back later.",
    ),
    p("3.1 — Google Gemini API key (REQUIRED for AI reports + ARIA chatbot)", H3),
    *bullet([
        "Go to <b>aistudio.google.com</b>",
        "Sign in with any Google account",
        "Click <b>&quot;Get API Key&quot;</b> in the left menu",
        "Click <b>&quot;Create API key&quot;</b>",
        "Copy the key — looks like <font name='Courier'>AIzaSy...</font>",
    ]),
    p(
        "Without this key, AI report generation falls back to plain text "
        "templates and ARIA gives canned responses. Everything else still works.",
        NOTE,
    ),
    p("3.2 — IPStack API key (OPTIONAL, for the world map)", H3),
    *bullet([
        "Go to <b>ipstack.com</b>",
        "Click <b>&quot;Sign up free&quot;</b>",
        "Verify email, log in",
        "Copy the API key from the dashboard",
    ]),
    p(
        "Without this key, the world map shows no attack location markers. "
        "All other features still work.",
        NOTE,
    ),
]

# ── 4. Restore the project ───────────────────────────────────────────────
story += [
    p("4. Unzip the project", H2),
    *bullet([
        "Right-click the zip file &raquo; Extract All",
        "Pick a folder you'll remember (e.g. <font name='Courier'>D:\\projects\\ai-threat-detection-soc</font>)",
        "Open that folder in your terminal:",
    ]),
    code('cd "D:\\projects\\ai-threat-detection-soc"'),
    p(
        "If you're on Mac/Linux, the path will look like "
        "<font name='Courier'>~/projects/ai-threat-detection-soc</font> instead.",
    ),
]

# ── 5. Backend setup ─────────────────────────────────────────────────────
story += [
    p("5. Set up the Python backend", H2),
    p("5.1 — Create a virtual environment (isolated Python install)", H3),
    code(
        "# Windows PowerShell\n"
        "python -m venv .venv\n"
        ".\\.venv\\Scripts\\Activate.ps1\n\n"
        "# Mac/Linux\n"
        "python3 -m venv .venv\n"
        "source .venv/bin/activate"
    ),
    p(
        "Your prompt should now show <font name='Courier'>(.venv)</font> at "
        "the start. That means the venv is active.",
    ),
    p(
        "On Windows, if PowerShell blocks the activation script, run this once:<br/>"
        "<font name='Courier'>Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned</font>",
        WARN,
    ),
    p("5.2 — Install Python dependencies", H3),
    code("pip install -r requirements.txt"),
    p(
        "This downloads and installs Flask, scikit-learn, pandas, shap, "
        "google-genai, sqlalchemy, and ~20 other packages. <b>First install "
        "takes 2-5 minutes</b> (some packages are large). Re-runs are fast "
        "because pip caches them.",
    ),
    p("5.3 — Download the dataset", H3),
    code("python download_dataset.py"),
    p(
        "This pulls down the <b>NSL-KDD</b> dataset (19 MB) — a standard "
        "academic benchmark for network intrusion detection. Saved as "
        "<font name='Courier'>KDDTrain+.txt</font>. Run once.",
    ),
    p("5.4 — Train the threat-level model", H3),
    code("python train_model.py"),
    p(
        "Generates 3 small files: <font name='Courier'>threat_model.pkl</font>, "
        "<font name='Courier'>scaler.pkl</font>, "
        "<font name='Courier'>label_encoder.pkl</font>. "
        "Takes about 5 seconds. Run once.",
    ),
    p("5.5 — Create your <font name='Courier'>.env</font> file", H3),
    p(
        "In the project root, create a file literally named "
        "<font name='Courier'>.env</font> (with the leading dot, no extension) "
        "and paste:",
    ),
    code(
        "GEMINI_API_KEY=paste-your-gemini-key-here\n"
        "IPSTACK_API_KEY=paste-your-ipstack-key-here\n"
        "LOG_LEVEL=INFO"
    ),
    p(
        "Save the file. The backend reads this at startup. <b>Don't commit "
        "this file to git</b> — the included <font name='Courier'>.gitignore</font> "
        "already excludes it.",
        WARN,
    ),
    p(
        "On Windows, File Explorer might hide files starting with a dot. "
        "Use VS Code or Notepad++ to create the file, or in PowerShell: "
        "<font name='Courier'>New-Item .env -Type File</font>",
        TIP,
    ),
]

# ── 6. Frontend setup ────────────────────────────────────────────────────
story += [
    p("6. Set up the React frontend", H2),
    p("Open a <b>second terminal window</b> (keep the first for the backend). "
      "In the new terminal:"),
    code(
        'cd "D:\\projects\\ai-threat-detection-soc\\frontend"\n'
        "pnpm install"
    ),
    p(
        "This installs ~330 React/Vite/UI packages into "
        "<font name='Courier'>frontend/node_modules</font>. "
        "<b>First install takes 1-3 minutes</b>. Re-runs are instant from cache.",
    ),
]

# ── 7. Run the app ───────────────────────────────────────────────────────
story += [
    p("7. Run the application", H2),
    p("You need <b>two terminals running at the same time</b>.", BODY),

    p("Terminal 1 — Backend", H3),
    code(
        "cd \"D:\\projects\\ai-threat-detection-soc\"\n"
        ".\\.venv\\Scripts\\Activate.ps1     # Windows\n"
        "# OR: source .venv/bin/activate    # Mac/Linux\n\n"
        "python backend_final.py"
    ),
    p(
        "<b>First boot takes ~14 seconds</b> while it trains the 5-class "
        "attack classifier, isolation forest, SHAP explainer, and computes "
        "the heatmap. After that, the trained state is cached to "
        "<font name='Courier'>models_cache.pkl</font> and subsequent boots "
        "take about 1 second.",
    ),
    p(
        "When you see <font name='Courier'>Running on http://127.0.0.1:5000</font>, "
        "the backend is ready. <b>Leave this terminal alone.</b>",
        TIP,
    ),

    p("Terminal 2 — Frontend", H3),
    code(
        "cd \"D:\\projects\\ai-threat-detection-soc\\frontend\"\n"
        "pnpm dev"
    ),
    p(
        "Vite starts up in 2-3 seconds. Look for "
        "<font name='Courier'>Local: http://localhost:5173</font>. "
        "Open that URL in your browser.",
    ),

    p("Or — use the included shortcut scripts (Windows only)", H3),
    p("Double-click these from File Explorer instead of typing commands:"),
    *bullet([
        "<font name='Courier'>start_backend.bat</font> — opens a window, runs the backend",
        "<font name='Courier'>start_frontend.bat</font> — opens a window, runs the frontend",
    ]),
]

# ── 8. What you should see ───────────────────────────────────────────────
story += [
    p("8. What you should see in the browser", H2),
    p("Open <font name='Courier'>http://localhost:5173</font> (or 5174 if "
      "5173 was busy). You should see:"),
    *bullet([
        "A dark-themed dashboard titled <b>AI THREAT RISK PREDICTION SYSTEM</b>",
        "Top right: a green pulsing <b>SYSTEM ACTIVE</b> indicator",
        "Two status badges: <b>AI REPORT: READY</b> (Gemini works) and "
        "<b>GEO MAPPING: READY</b> (IPStack works)",
        "Three tabs: <b>SINGLE ANALYSIS</b>, <b>BATCH ANALYSIS</b>, <b>UBA MONITORING</b>",
        "A radar sweep, terminal log, and threat-level gauge in the middle",
        "Bottom right: an ARIA chatbot icon",
    ]),
    p("Try clicking <b>PREDICT</b> with the default values. You should "
      "instantly see a <b>LOW</b> threat result with a confidence score around 90%.",
      TIP),
]

# ── 9. Common problems ───────────────────────────────────────────────────
story += [
    p("9. Common problems and fixes", H2),
    info_table(
        ["Problem", "Fix"],
        [
            ("<b>'python' is not recognized</b>",
             "Python isn't on your PATH. Reinstall Python with "
             "&quot;Add to PATH&quot; ticked, or use <font name='Courier'>py</font> "
             "instead of <font name='Courier'>python</font> on Windows."),
            ("<b>Activate.ps1 cannot be loaded — execution policy</b>",
             "Run once in PowerShell: <font name='Courier'>Set-ExecutionPolicy "
             "-Scope CurrentUser -ExecutionPolicy RemoteSigned</font>"),
            ("<b>pip install hangs on scipy/scikit-learn</b>",
             "Slow internet or building from source. Wait 5 minutes. "
             "If it still fails, install Microsoft C++ Build Tools (Windows)."),
            ("<b>Backend says: FileNotFoundError: 'KDDTrain+.txt'</b>",
             "You skipped step 5.3. Run "
             "<font name='Courier'>python download_dataset.py</font>"),
            ("<b>Backend says: 'threat_model.pkl' not found</b>",
             "You skipped step 5.4. Run "
             "<font name='Courier'>python train_model.py</font>"),
            ("<b>Frontend: Failed to resolve import 'framer-motion'</b>",
             "Reinstall: <font name='Courier'>cd frontend &amp;&amp; pnpm install</font>"),
            ("<b>Frontend opens but Predict shows 'Network Error'</b>",
             "Backend not running. Check terminal 1 — must say "
             "&quot;Running on http://127.0.0.1:5000&quot;."),
            ("<b>Port 5000 already in use</b>",
             "Something else is using port 5000. Kill it, or run with "
             "<font name='Courier'>$env:PORT=5001; python backend_final.py</font>"),
            ("<b>Port 5173 already in use</b>",
             "Vite auto-picks 5174. Just use that URL instead. "
             "If both are busy, check terminal 2 for the actual URL."),
            ("<b>AI REPORT badge says NOT READY</b>",
             "Your <font name='Courier'>.env</font> file is missing or "
             "<font name='Courier'>GEMINI_API_KEY</font> is wrong. "
             "Recheck step 5.5 then restart the backend."),
            ("<b>Backend uses a lot of CPU during first boot</b>",
             "Normal. RandomForest training. Capped to 2 cores. "
             "Resolves in ~14 seconds. Subsequent boots use cache."),
        ],
        col_widths=[55 * mm, 109 * mm],
    ),
]

# ── 10. Where to learn more ──────────────────────────────────────────────
story += [
    p("10. Other docs in this project", H2),
    info_table(
        ["File", "What's in it"],
        [
            ("<b>STRUCTURE.md</b>",
             "Full reference: every backend module, every endpoint, "
             "every frontend component. Read this if you want to modify the code."),
            ("<b>CHANGES.md</b>",
             "What was improved over the original codebase: 22 fixes including "
             "model cache, structured logging, Gemini SDK migration, modular refactor."),
            ("<b>RENDER_DEPLOYMENT_GUIDE.pdf</b>",
             "Step-by-step guide to deploy this project for free on Render.com "
             "so it's accessible from anywhere on the internet."),
            ("<b>README.md</b>",
             "Original project overview — features and tech stack."),
            ("<b>SETUP_COMPLETE.md</b>",
             "Original quick-reference setup notes (legacy)."),
        ],
        col_widths=[55 * mm, 109 * mm],
    ),
]

# ── 11. Folder map ───────────────────────────────────────────────────────
story += [
    p("11. Quick folder map", H2),
    code(
        "ai-threat-detection-soc/\n"
        "├── 00_START_HERE.pdf            ← THIS FILE\n"
        "├── README.md                    ← Project overview\n"
        "├── STRUCTURE.md                 ← Full code reference\n"
        "├── CHANGES.md                   ← Improvement log\n"
        "├── RENDER_DEPLOYMENT_GUIDE.pdf  ← Deploy to the cloud\n"
        "│\n"
        "├── backend_final.py             ← Backend entry point (run this)\n"
        "├── train_model.py               ← Trains threat model\n"
        "├── download_dataset.py          ← Fetches NSL-KDD\n"
        "├── requirements.txt             ← Python dependencies\n"
        "├── start_backend.bat/.ps1       ← Windows shortcut\n"
        "├── start_frontend.bat/.ps1      ← Windows shortcut\n"
        "│\n"
        "├── backend/                     ← Modular Flask backend (14 modules)\n"
        "├── frontend/                    ← React + Vite dashboard\n"
        "│\n"
        "└── (created at runtime)\n"
        "    ├── .venv/                   ← your Python venv\n"
        "    ├── .env                     ← your API keys\n"
        "    ├── KDDTrain+.txt            ← dataset (download_dataset.py)\n"
        "    ├── threat_model.pkl         ← (train_model.py)\n"
        "    ├── scaler.pkl               ← (train_model.py)\n"
        "    ├── label_encoder.pkl        ← (train_model.py)\n"
        "    ├── models_cache.pkl         ← (auto, after first backend boot)\n"
        "    └── frontend/node_modules/   ← (pnpm install)"
    ),
]

# ── 12. The TL;DR cheat sheet ────────────────────────────────────────────
story += [
    p("12. TL;DR cheat sheet — copy-paste these to install everything", H2),
    p("<b>Windows PowerShell:</b>", BODY),
    code(
        "# (Once) install Python, Node, pnpm — see Section 2\n\n"
        "cd \"D:\\projects\\ai-threat-detection-soc\"\n\n"
        "# Backend setup\n"
        "python -m venv .venv\n"
        ".\\.venv\\Scripts\\Activate.ps1\n"
        "pip install -r requirements.txt\n"
        "python download_dataset.py\n"
        "python train_model.py\n\n"
        "# Create .env file with your API keys (see Section 5.5)\n\n"
        "# Frontend setup (in a new terminal)\n"
        "cd frontend\n"
        "pnpm install\n"
        "cd ..\n\n"
        "# Run\n"
        "# Terminal 1:  python backend_final.py\n"
        "# Terminal 2:  cd frontend; pnpm dev\n"
        "# Browser:     http://localhost:5173"
    ),
    p("<b>Mac / Linux:</b>", BODY),
    code(
        "cd ~/projects/ai-threat-detection-soc\n\n"
        "python3 -m venv .venv\n"
        "source .venv/bin/activate\n"
        "pip install -r requirements.txt\n"
        "python download_dataset.py\n"
        "python train_model.py\n\n"
        "# Create .env (see Section 5.5)\n\n"
        "cd frontend && pnpm install && cd ..\n\n"
        "# Run\n"
        "# Terminal 1:  python backend_final.py\n"
        "# Terminal 2:  cd frontend && pnpm dev"
    ),
    Spacer(1, 0.3 * inch),
    p(
        "<i>Welcome aboard. If anything in this guide is unclear, "
        "section 9 covers the most common stumbling blocks.</i>",
        ParagraphStyle("end", parent=BODY, alignment=TA_CENTER,
                       textColor=colors.HexColor("#0d3b66"), fontSize=11),
    ),
]


# ── Build PDF ────────────────────────────────────────────────────────────
def build():
    doc = SimpleDocTemplate(
        "00_START_HERE.pdf",
        pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=20 * mm, bottomMargin=20 * mm,
        title="Setup Guide — AI Threat Detection SOC",
        author="AI Threat Detection SOC",
    )
    doc.build(story, onFirstPage=add_page_number,
              onLaterPages=add_page_number)
    print("Wrote 00_START_HERE.pdf")


if __name__ == "__main__":
    build()
