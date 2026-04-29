"""Generate a detailed Render.com deployment guide as a PDF.

Run once: python generate_render_guide.py
Output:    RENDER_DEPLOYMENT_GUIDE.pdf
"""
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
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
    "Body", parent=styles["BodyText"], fontSize=10.5, leading=15,
    spaceAfter=8, alignment=TA_JUSTIFY,
)
NOTE = ParagraphStyle(
    "Note", parent=BODY, leftIndent=14, rightIndent=14, backColor=colors.HexColor("#fff8dc"),
    borderColor=colors.HexColor("#e6c200"), borderWidth=1, borderPadding=8,
    spaceAfter=12, spaceBefore=8,
)
WARN = ParagraphStyle(
    "Warn", parent=BODY, leftIndent=14, rightIndent=14, backColor=colors.HexColor("#ffe4e1"),
    borderColor=colors.HexColor("#c0392b"), borderWidth=1, borderPadding=8,
    spaceAfter=12, spaceBefore=8,
)
CODE = ParagraphStyle(
    "Code", parent=BODY, fontName="Courier", fontSize=9, leading=12,
    backColor=colors.HexColor("#f4f6f8"), borderColor=colors.HexColor("#cfd8dc"),
    borderWidth=0.5, borderPadding=8, leftIndent=6, rightIndent=6,
    spaceAfter=10, spaceBefore=4,
)
COVER_TITLE = ParagraphStyle(
    "CoverTitle", parent=H1, fontSize=32, alignment=TA_CENTER, spaceAfter=18,
    leading=38,
)
COVER_SUB = ParagraphStyle(
    "CoverSub", parent=BODY, fontSize=14, alignment=TA_CENTER,
    textColor=colors.HexColor("#555"), spaceAfter=4,
)


# ── Helpers ───────────────────────────────────────────────────────────────
def p(text, style=BODY):
    return Paragraph(text, style)


def code(text):
    return Paragraph(text.replace(" ", "&nbsp;").replace("\n", "<br/>"), CODE)


def bullet(items):
    return [Paragraph(f"&bull;&nbsp;&nbsp;{i}", BODY) for i in items]


def env_table(rows):
    """rows = [(name, default, required, description), ...]"""
    data = [[p("<b>Variable</b>"), p("<b>Required?</b>"), p("<b>Default</b>"), p("<b>What it does</b>")]]
    for name, default, required, desc in rows:
        data.append([
            Paragraph(f"<font name='Courier' size='9'>{name}</font>", BODY),
            p(required),
            Paragraph(f"<font name='Courier' size='9'>{default}</font>", BODY),
            p(desc),
        ])
    t = Table(data, colWidths=[44 * mm, 22 * mm, 30 * mm, 70 * mm], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d3b66")),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("ALIGN",      (0, 0), (-1, -1), "LEFT"),
        ("VALIGN",     (0, 0), (-1, -1), "TOP"),
        ("GRID",       (0, 0), (-1, -1), 0.4, colors.HexColor("#cfd8dc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f4f6f8")]),
        ("FONTSIZE",   (0, 0), (-1, -1), 9.5),
        ("LEFTPADDING",  (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
    ]))
    return t


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
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f6f8")]),
        ("FONTSIZE",   (0, 0), (-1, -1), 9.5),
        ("LEFTPADDING",  (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
    ]))
    return t


# ── Page footer ───────────────────────────────────────────────────────────
def add_page_number(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#777"))
    canvas.drawString(
        20 * mm, 12 * mm,
        "AI Threat Detection SOC — Render Deployment Guide",
    )
    canvas.drawRightString(
        A4[0] - 20 * mm, 12 * mm,
        f"Page {doc.page}",
    )
    canvas.restoreState()


# ── Document content ──────────────────────────────────────────────────────
story = []

# Cover
story += [
    Spacer(1, 2.2 * inch),
    p("AI THREAT DETECTION SOC", COVER_TITLE),
    p("Render.com Deployment Guide", COVER_SUB),
    Spacer(1, 0.4 * inch),
    p("Step-by-step instructions to deploy the backend (Flask) and frontend (Vite/React) to Render's free tier — including every environment variable, build command, and gotcha.", COVER_SUB),
    Spacer(1, 0.6 * inch),
    p("If you can copy-paste, you can deploy this.", ParagraphStyle("tag", parent=BODY, alignment=TA_CENTER, fontSize=11, textColor=colors.HexColor("#0d3b66"))),
    PageBreak(),
]

# ── 1. What is Render ─────────────────────────────────────────────────────
story += [
    p("1. What is Render?", H1),
    p(
        "Render is a cloud hosting platform — like Heroku or Vercel — that lets you "
        "deploy web apps, APIs, databases, and static sites directly from a GitHub repo. "
        "It auto-builds on every push, gives you HTTPS for free, and has a generous "
        "free tier that's enough for demos and portfolio projects.",
    ),
    p(
        "For this project we'll use <b>two</b> services on Render:",
    ),
    *bullet([
        "<b>Web Service</b> — runs the Python Flask backend (the ML brain)",
        "<b>Static Site</b> — serves the React frontend (the dashboard)",
    ]),
    p("Both are free. They communicate over HTTPS using URLs Render generates for you.", BODY),
]

# ── 2. Architecture ───────────────────────────────────────────────────────
story += [
    p("2. How the deployment looks", H2),
    code(
        "Browser  ─►  Render Static Site (frontend)\n"
        "                 |\n"
        "                 |  HTTPS calls to /predict, /aria-chat, ...\n"
        "                 ▼\n"
        "         Render Web Service (Flask backend)\n"
        "                 |\n"
        "                 ├─► Gemini API   (incident reports + ARIA)\n"
        "                 ├─► IPStack API  (geolocation)\n"
        "                 └─► SQLite       (UBA logs, on-disk)"
    ),
    p(
        "The frontend is a static React build (HTML/CSS/JS). The backend is the only "
        "thing that needs Python and ML libraries. Each side has its own URL.",
    ),
]

# ── 3. Prerequisites ──────────────────────────────────────────────────────
story += [
    p("3. Prerequisites — make these accounts first", H2),
    *bullet([
        "<b>GitHub account</b> — render pulls code from a Git repo. Sign up at github.com if you don't have one.",
        "<b>Render account</b> — sign up at render.com. You can sign in with GitHub for one-click setup.",
        "<b>Gemini API key</b> — for AI incident reports + ARIA chatbot. Get one free at aistudio.google.com (sign in, click 'Get API Key').",
        "<b>IPStack API key</b> (optional) — for the geographic threat map. Free tier (100 calls/month) at ipstack.com.",
        "<b>The project on your machine</b> with all changes from this session (CHANGES.md, STRUCTURE.md, the backend/ package).",
    ]),
    p(
        "Without Gemini, AI report generation falls back to plain text templates. Without IPStack, the world map shows no markers but everything else still works.",
        NOTE,
    ),
]

# ── 4. Step 1: Push to GitHub ─────────────────────────────────────────────
story += [
    p("4. Step 1: Push the code to GitHub", H2),
    p("Skip this section if your code is already on GitHub.", BODY),
    p("Open a terminal in the project root and run:", BODY),
    code(
        "git init\n"
        "git add .\n"
        "git commit -m \"Initial commit\"\n"
        "git branch -M main"
    ),
    p(
        "Now go to <b>github.com/new</b>, create an empty repository (don't initialize "
        "with README), copy the 2 commands GitHub shows you to push an existing repo. "
        "They look like this:",
    ),
    code(
        "git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git\n"
        "git push -u origin main"
    ),
    p(
        "Important: the project's <b>.gitignore</b> already excludes <font name='Courier'>.env</font>, "
        "<font name='Courier'>*.pkl</font>, <font name='Courier'>KDDTrain+.txt</font>, and "
        "<font name='Courier'>node_modules/</font>. That's deliberate — these get regenerated on Render. "
        "If you accidentally committed them earlier, delete them from Git history.",
        WARN,
    ),
]

# ── 5. Step 2: Tiny code prep ─────────────────────────────────────────────
story += [
    p("5. Step 2: Two small tweaks the project needs for cloud", H2),
    p(
        "These are <b>not yet applied</b> to your repo. Make these two edits before you deploy "
        "(they're 5-line changes; the deploy will fail without them):",
    ),

    p("5.1 — Tell the frontend where the backend lives", H3),
    p(
        "On localhost the frontend hits <font name='Courier'>http://localhost:5000</font>. "
        "On Render, the backend has a different URL. In <font name='Courier'>frontend/src/api/threatApi.ts</font> "
        "(and the other api files), replace the hardcoded base URL with one read from <font name='Courier'>import.meta.env.VITE_API_URL</font>.",
    ),
    code(
        "// Before\n"
        "const API_BASE = 'http://localhost:5000';\n\n"
        "// After\n"
        "const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:5000';"
    ),

    p("5.2 — Add a production WSGI server", H3),
    p(
        "Flask's built-in dev server (<font name='Courier'>app.run()</font>) is not suitable for "
        "production. Add <b>gunicorn</b> to <font name='Courier'>requirements.txt</font>:",
    ),
    code("gunicorn==23.0.0"),
    p("Render's start command will use it instead of <font name='Courier'>python backend_final.py</font>.", BODY),
]

# ── 6. Step 3: Deploy backend ─────────────────────────────────────────────
story += [
    p("6. Step 3: Deploy the backend (Web Service)", H2),
    *bullet([
        "Log into <b>render.com</b>, click <b>+ New &raquo; Web Service</b>.",
        "Connect your GitHub repo. Pick the repo for this project.",
        "Render auto-detects it's Python. Fill in the form:",
    ]),
    info_table(
        ["Field", "Value"],
        [
            ("Name", "ai-soc-backend (or anything)"),
            ("Region", "Closest to you / your users"),
            ("Branch", "main"),
            ("Root Directory", "&nbsp;(leave blank)"),
            ("Runtime", "Python 3"),
            ("Build Command", "<font name='Courier' size='9'>pip install -r requirements.txt &amp;&amp; python download_dataset.py &amp;&amp; python train_model.py</font>"),
            ("Start Command", "<font name='Courier' size='9'>gunicorn --bind 0.0.0.0:$PORT --timeout 180 backend_final:app</font>"),
            ("Plan", "Free"),
        ],
        col_widths=[42 * mm, 122 * mm],
    ),
    p(
        "<b>What that build command does:</b><br/>"
        "1. Installs Python deps from <font name='Courier'>requirements.txt</font><br/>"
        "2. Downloads the NSL-KDD dataset (19 MB)<br/>"
        "3. Runs <font name='Courier'>train_model.py</font> to generate the 3 .pkl files<br/>"
        "First boot then trains the rest of the models in <font name='Courier'>backend_final.py</font> and saves them to <font name='Courier'>models_cache.pkl</font>. "
        "Subsequent boots are fast — about 1 second.",
    ),
    p(
        "<b>--timeout 180</b> matters: training all models takes ~14&nbsp;s. The default gunicorn timeout (30&nbsp;s) would kill the worker mid-training. 180 gives plenty of headroom.",
        NOTE,
    ),
    p("6.1 — Set environment variables (backend)", H3),
    p("Scroll down to <b>Environment</b> while creating the service (or add later under <b>Environment</b> tab) and add:", BODY),
]

backend_env = [
    ("GEMINI_API_KEY",      "—",                       "Yes (for AI)",   "From aistudio.google.com. Without this, ARIA + reports fall back to templates."),
    ("IPSTACK_API_KEY",     "—",                       "Optional",        "From ipstack.com. Without this, the world map shows no markers."),
    ("ALLOWED_ORIGINS",     "(see below)",             "Yes",             "Frontend URL after you deploy step 4. Example: https://ai-soc-frontend.onrender.com"),
    ("GEMINI_MODEL",        "gemini-2.5-flash",        "No",              "Override only if you want a different Gemini model."),
    ("LOG_LEVEL",           "INFO",                    "No",              "DEBUG / INFO / WARNING / ERROR."),
    ("PYTHON_VERSION",      "3.11.9",                  "Recommended",     "Pin Python version. Render defaults to 3.x — pin to avoid surprise upgrades."),
    ("RETRAIN_MODELS",      "(unset)",                 "No",              "Set to 1 to force retrain on every boot. Leave unset for fast restarts."),
]
story += [env_table(backend_env)]

story += [
    p(
        "<b>About <font name='Courier'>ALLOWED_ORIGINS</font>:</b> you don't know the frontend URL yet — "
        "you'll create it in step 4. For now, set it to <font name='Courier'>*</font> "
        "temporarily, deploy the backend, deploy the frontend, then come back and change it to "
        "the real frontend URL.",
        NOTE,
    ),
    p(
        "Click <b>Create Web Service</b>. Render starts building. Watch the logs — first build takes "
        "5-10 minutes (installing scipy, scikit-learn, shap is heavy). Subsequent deploys are faster.",
    ),
    p(
        "When you see <font name='Courier'>Listening on 0.0.0.0:10000</font> (or similar), the backend is "
        "live. Render gives you a URL like <font name='Courier'>https://ai-soc-backend.onrender.com</font>. "
        "<b>Copy this URL</b> — you'll need it for the frontend.",
    ),
    p("Test it:", BODY),
    code("curl https://ai-soc-backend.onrender.com/health"),
    p("Should return JSON with <font name='Courier'>\"ready\": true</font>.", BODY),
]

# ── 7. Step 4: Deploy frontend ────────────────────────────────────────────
story += [
    p("7. Step 4: Deploy the frontend (Static Site)", H2),
    *bullet([
        "Click <b>+ New &raquo; Static Site</b>.",
        "Pick the same GitHub repo.",
        "Fill in:",
    ]),
    info_table(
        ["Field", "Value"],
        [
            ("Name", "ai-soc-frontend"),
            ("Branch", "main"),
            ("Root Directory", "frontend"),
            ("Build Command", "<font name='Courier' size='9'>pnpm install &amp;&amp; pnpm build</font>"),
            ("Publish Directory", "dist"),
        ],
        col_widths=[42 * mm, 122 * mm],
    ),
    p("7.1 — Set environment variables (frontend)", H3),
]

frontend_env = [
    ("VITE_API_URL", "—", "Yes",
     "The backend URL from step 6. Example: https://ai-soc-backend.onrender.com (no trailing slash)."),
    ("NODE_VERSION", "20.18.0", "Recommended",
     "Pin Node version. Render defaults change occasionally."),
]
story += [env_table(frontend_env)]

story += [
    p(
        "<b>Important:</b> Vite bakes <font name='Courier'>VITE_*</font> variables into the build "
        "at build time, not runtime. If you change <font name='Courier'>VITE_API_URL</font> later, "
        "trigger a manual <b>Clear build cache &amp; deploy</b> from Render's dashboard — otherwise the "
        "old URL stays compiled into the JS bundle.",
        WARN,
    ),
    p(
        "Click <b>Create Static Site</b>. Build takes 2-4 minutes. When done, Render gives a URL like "
        "<font name='Courier'>https://ai-soc-frontend.onrender.com</font>.",
    ),
]

# ── 8. Step 5: Wire them together ─────────────────────────────────────────
story += [
    p("8. Step 5: Connect the two services", H2),
    p("Now the frontend exists, go back and update the backend's <font name='Courier'>ALLOWED_ORIGINS</font>:", BODY),
    *bullet([
        "Open the backend service on Render",
        "<b>Environment</b> tab",
        "Edit <font name='Courier'>ALLOWED_ORIGINS</font>",
        "Set it to your frontend URL — example: <font name='Courier'>https://ai-soc-frontend.onrender.com</font>",
        "Save changes — Render auto-redeploys",
    ]),
    p(
        "Open the frontend URL in a browser. The dashboard should load. Click <b>Predict</b> "
        "with a default sample input. If you see live results — congrats, you're deployed.",
    ),
]

# ── 9. Full env var reference ─────────────────────────────────────────────
story += [
    p("9. Complete environment variable reference", H2),
    p("Backend service (Render &raquo; Environment):", H3),
    env_table(backend_env + [
        ("HOST",          "0.0.0.0",                "Auto-set", "Bind address. Render's gunicorn command sets this — don't override."),
        ("PORT",          "(Render sets)",          "Auto-set", "Render injects this. The gunicorn command reads $PORT."),
        ("FLASK_DEBUG",   "(unset)",                "No",       "Don't enable debug mode in production."),
        ("DATABASE_URL",  "sqlite:///uba_logs.db",  "Optional", "Switch UBA storage to Postgres (e.g. Render's free Postgres)."),
    ]),
    Spacer(1, 0.2 * inch),
    p("Frontend static site:", H3),
    env_table(frontend_env),
]

# ── 10. Free tier limits ──────────────────────────────────────────────────
story += [
    p("10. Render free tier — what to expect", H2),
    info_table(
        ["Limit", "Free tier value", "Impact on this app"],
        [
            ("RAM", "512 MB", "Tight — training uses ~400 MB. Should fit but watch logs."),
            ("CPU", "0.1 (shared)", "First boot training is slow (~30-60 s instead of 14 s)."),
            ("Bandwidth", "100 GB / month", "Plenty for demo traffic."),
            ("Sleep after inactivity", "15 min", "<b>Backend goes to sleep.</b> First request after sleep takes ~30 s to wake."),
            ("Build minutes", "Unlimited", "OK."),
            ("HTTPS", "Free, auto-renewed", "OK."),
            ("Custom domain", "Supported", "OK (add a CNAME)."),
        ],
        col_widths=[42 * mm, 38 * mm, 84 * mm],
    ),
    p(
        "<b>The sleep behavior is the biggest gotcha.</b> If your demo audience hits the dashboard "
        "and the backend was idle for 15+ minutes, the first <font name='Courier'>/predict</font> call "
        "will hang for 20-30 seconds while Render wakes the container. Subsequent calls are normal speed. "
        "For a live demo, hit the URL once 1 minute before showing it.",
        WARN,
    ),
]

# ── 11. Common errors ─────────────────────────────────────────────────────
story += [
    p("11. Common deployment errors and fixes", H2),
    info_table(
        ["Symptom", "Cause", "Fix"],
        [
            ("Build fails: 'Could not find a version that satisfies the requirement xyz'",
             "Python version mismatch.",
             "Set <font name='Courier'>PYTHON_VERSION=3.11.9</font> env var. Some packages don't have wheels for Python 3.13 yet."),
            ("Build hangs at 'Collecting scipy/scikit-learn'",
             "Slow free-tier CPU compiling wheels.",
             "Wait. First build is 5-10 min. Re-deploys hit pip cache and are faster."),
            ("'Worker timed out' in logs, 502 from frontend",
             "Gunicorn killed the worker mid-training.",
             "Make sure start command has <font name='Courier'>--timeout 180</font>."),
            ("Frontend loads but Predict returns network error",
             "CORS blocking, or wrong VITE_API_URL.",
             "Check ALLOWED_ORIGINS matches frontend URL exactly. Re-deploy frontend after VITE_API_URL change."),
            ("'No module named backend' on start",
             "gunicorn run from wrong directory.",
             "Make sure Root Directory is empty (project root), not 'backend'."),
            ("OOM (memory) crash during training",
             "Free tier 512 MB exceeded.",
             "Drop <font name='Courier'>n_estimators</font> in trainer.py from 50 to 25, or upgrade to paid tier."),
            ("Models retrain on every restart",
             "Render's filesystem is ephemeral — models_cache.pkl is lost on redeploy.",
             "Expected. Cache persists across <i>restarts</i> but not <i>redeploys</i>. Acceptable: ~14 s extra on each git push."),
            ("UBA data disappears",
             "SQLite file is on ephemeral disk.",
             "Add a Render Disk (paid) or migrate to Render Postgres via DATABASE_URL."),
        ],
        col_widths=[55 * mm, 45 * mm, 64 * mm],
    ),
]

# ── 12. Checklist ─────────────────────────────────────────────────────────
story += [
    p("12. Final post-deploy checklist", H2),
    *bullet([
        "Frontend URL loads the dashboard",
        "Top-right status badges: <b>AI REPORT: READY</b> (Gemini configured) and optionally <b>GEO MAPPING: READY</b> (IPStack configured)",
        "Click <b>Predict</b> with default values — get a LOW threat with ~90% confidence",
        "Open <font name='Courier'>backend-url/health</font> — returns <font name='Courier'>{\"ready\": true}</font>",
        "Try the <b>BATCH ANALYSIS</b> tab — upload <font name='Courier'>sample_batch.csv</font> from the repo root",
        "Try <b>UBA MONITORING</b> tab — click 'Simulate' for a brute-force scenario",
        "Try the ARIA chatbot (bottom-right) — ask 'What is DoS?'",
        "Open browser dev tools — confirm requests go to <font name='Courier'>https://...onrender.com</font>, not localhost",
    ]),
]

# ── 13. Optional: render.yaml ─────────────────────────────────────────────
story += [
    p("13. Optional: one-click deploy via render.yaml", H2),
    p(
        "Instead of clicking through the UI, you can put the entire deployment config in a "
        "<font name='Courier'>render.yaml</font> file at the repo root. Then on Render: "
        "<b>+ New &raquo; Blueprint &raquo; pick repo</b>. Render reads the YAML and creates both services in one click.",
    ),
    code(
        "services:\n"
        "  - type: web\n"
        "    name: ai-soc-backend\n"
        "    runtime: python\n"
        "    buildCommand: pip install -r requirements.txt &amp;&amp; python download_dataset.py &amp;&amp; python train_model.py\n"
        "    startCommand: gunicorn --bind 0.0.0.0:$PORT --timeout 180 backend_final:app\n"
        "    plan: free\n"
        "    envVars:\n"
        "      - key: PYTHON_VERSION\n"
        "        value: 3.11.9\n"
        "      - key: GEMINI_API_KEY\n"
        "        sync: false           # prompts you to set in dashboard\n"
        "      - key: IPSTACK_API_KEY\n"
        "        sync: false\n"
        "      - key: ALLOWED_ORIGINS\n"
        "        value: https://ai-soc-frontend.onrender.com\n\n"
        "  - type: web\n"
        "    name: ai-soc-frontend\n"
        "    runtime: static\n"
        "    rootDir: frontend\n"
        "    buildCommand: pnpm install &amp;&amp; pnpm build\n"
        "    staticPublishPath: dist\n"
        "    envVars:\n"
        "      - key: VITE_API_URL\n"
        "        value: https://ai-soc-backend.onrender.com"
    ),
    p("Save this as <font name='Courier'>render.yaml</font>, push, then go to Render and click Blueprint.", BODY),
]

# ── 14. Glossary ──────────────────────────────────────────────────────────
story += [
    p("14. Terms you'll see in the docs", H2),
    info_table(
        ["Term", "Means"],
        [
            ("Web Service", "A long-running HTTP server (your Flask backend)"),
            ("Static Site", "Pre-built HTML/JS/CSS files served from CDN (your React frontend)"),
            ("Blueprint", "A render.yaml file that defines multiple services at once"),
            ("Build Command", "Shell command that installs dependencies and prepares artifacts"),
            ("Start Command", "Shell command that launches the long-running process"),
            ("Environment Group", "A named set of env vars you can attach to multiple services"),
            ("Health Check Path", "URL Render hits to verify your service is alive (use /health)"),
            ("Auto-Deploy", "Re-deploys on every git push to the connected branch"),
        ],
        col_widths=[40 * mm, 124 * mm],
    ),
]

# ── 15. Wrap up ───────────────────────────────────────────────────────────
story += [
    p("15. After deployment", H2),
    *bullet([
        "<b>Update README.md</b> in your repo with the live URLs so people can try it",
        "<b>Add a Render badge</b>: <font name='Courier'>[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)</font>",
        "<b>Set up Render's auto-deploy</b> — every git push to main triggers a redeploy (on by default)",
        "<b>Check logs regularly</b> for the first day — free tier RAM is tight, OOM crashes happen",
        "<b>Set a UptimeRobot ping</b> on /health every 10 minutes if you want to keep the backend warm (anti-sleep workaround)",
    ]),
    Spacer(1, 0.4 * inch),
    p(
        "<i>That's it. You should now have a fully cloud-hosted SOC dashboard running on free infrastructure, accessible from anywhere.</i>",
        ParagraphStyle("end", parent=BODY, alignment=TA_CENTER, textColor=colors.HexColor("#0d3b66"), fontSize=11),
    ),
]


# ── Build PDF ─────────────────────────────────────────────────────────────
def build():
    doc = SimpleDocTemplate(
        "RENDER_DEPLOYMENT_GUIDE.pdf",
        pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=20 * mm, bottomMargin=20 * mm,
        title="Render Deployment Guide — AI Threat Detection SOC",
        author="AI Threat Detection SOC",
    )
    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    print("Wrote RENDER_DEPLOYMENT_GUIDE.pdf")


if __name__ == "__main__":
    build()
