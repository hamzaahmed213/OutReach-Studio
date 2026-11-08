import base64
import io
import os
import re
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import pandas as pd
import streamlit as st
from pypdf import PdfReader

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from database import (
    init_db,
    save_cv,
    load_cv,
    save_recruiters,
    load_recruiters,
    get_email_counts,
    save_draft,
    load_drafts,
    update_draft_status,
    log_email,
    get_sent_today,
    get_outreach_tracker,
    has_sent_email,
)


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Internship Outreach Bot",
    page_icon="📧",
    layout="wide",
)

init_db()


# --------------------------------------------------
# VISUAL DESIGN SYSTEM
# --------------------------------------------------

st.markdown(
    """
    <style>
    :root {
        color-scheme: dark;
        --bg: #0b1020;
        --panel: #111a2d;
        --panel-raised: #151f35;
        --panel-soft: #0f1729;
        --border: #26334b;
        --border-soft: #202c42;
        --text: #e7edf8;
        --muted: #91a0b8;
        --muted-2: #71819b;
        --accent: #7895f5;
        --accent-strong: #5878e8;
        --success: #4fc39a;
        --warning: #e7b96b;
        --danger: #ee858c;
    }

    html, body, [class*="css"] {
        font-family: Inter, ui-sans-serif, system-ui, -apple-system,
                     BlinkMacSystemFont, "Segoe UI", sans-serif;
        color: var(--text);
    }
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
        background: var(--bg);
        color: var(--text);
    }
    [data-testid="stHeader"] {
        background: rgba(11, 16, 32, .94);
        border-bottom: 1px solid var(--border-soft);
    }
    [data-testid="stMainBlockContainer"] {
        max-width: 1480px;
        padding-top: 1.8rem;
        padding-bottom: 3rem;
    }
    [data-testid="stVerticalBlock"] { gap: .85rem; }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: #0d1526;
        border-right: 1px solid var(--border);
    }
    [data-testid="stSidebar"] > div:first-child {
        background: transparent;
        padding: 1.35rem 1rem;
    }
    [data-testid="stSidebar"] * { color: var(--text); }
    [data-testid="stSidebar"] [data-testid="stRadio"] > label {
        color: var(--muted-2) !important;
        font-size: .7rem;
        font-weight: 750;
        letter-spacing: .13em;
        text-transform: uppercase;
        margin-bottom: .55rem;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] {
        gap: .28rem;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label {
        padding: .62rem .75rem;
        border: 1px solid transparent;
        border-radius: 9px;
        margin: 0;
        transition: background .12s ease, border-color .12s ease;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label:hover {
        background: #17233a;
        border-color: var(--border);
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) {
        background: #1a2947;
        border-color: #344b79;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label p {
        color: #cbd5e6;
        font-size: .88rem;
        font-weight: 550;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) p {
        color: #ffffff;
        font-weight: 700;
    }
    [data-testid="stSidebar"] hr { border-color: var(--border); }

    /* Brand and page identity */
    .brand-lockup {
        display: flex; align-items: center; gap: 11px;
        padding: .3rem .2rem 1rem;
    }
    .brand-mark {
        width: 39px; height: 39px; display: grid; place-items: center;
        border-radius: 11px; color: #fff; font-size: 18px; font-weight: 800;
        background: #526fce;
        border: 1px solid #7895f5;
        box-shadow: 0 5px 18px rgba(69, 96, 180, .18);
    }
    .brand-name {
        color: #f4f7fd; font-size: 1rem; font-weight: 760;
        letter-spacing: -.035em;
    }
    .brand-sub { color: var(--muted); font-size: .69rem; margin-top: 3px; }
    .sidebar-status {
        color: #b5c1d4; font-size: .74rem;
        padding: .62rem .7rem; margin: .35rem 0;
        background: #121d31; border: 1px solid var(--border-soft);
        border-radius: 9px;
    }
    .workspace-kicker {
        color: #91a8f7; font-size: .68rem; font-weight: 750;
        text-transform: uppercase; letter-spacing: .15em;
        margin-bottom: .45rem;
    }
    .hero-panel {
        background: #121e34;
        border: 1px solid #2a3a58;
        border-radius: 15px;
        padding: 1.55rem 1.7rem;
        color: var(--text);
        margin: .3rem 0 1.25rem;
    }
    .hero-panel h2 {
        color: #f2f5fc !important; margin: 0 0 .4rem 0;
        font-size: 1.48rem !important; letter-spacing: -.04em;
    }
    .hero-panel p {
        color: #aab8ce !important; margin: 0;
        max-width: 740px; font-size: .9rem; line-height: 1.65;
    }
    .hero-pill {
        display: inline-block; margin-top: .9rem;
        padding: .3rem .62rem; border-radius: 6px;
        color: #cbd7ff; background: #1c2b49;
        border: 1px solid #344a76; font-size: .7rem; font-weight: 650;
    }

    /* Typography */
    h1, h2, h3, h4 {
        color: #edf2fb !important;
        letter-spacing: -.035em;
        font-weight: 720 !important;
    }
    h1 { font-size: 1.9rem !important; }
    h2 { font-size: 1.35rem !important; }
    h3 { font-size: 1.05rem !important; }
    p, li, label, [data-testid="stMarkdownContainer"] {
        color: #c1ccdc;
    }
    [data-testid="stCaptionContainer"] p, .stCaption {
        color: var(--muted) !important;
    }

    /* Metrics and surfaces */
    [data-testid="stMetric"] {
        background: var(--panel);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 1rem 1.1rem;
        box-shadow: none;
    }
    [data-testid="stMetricLabel"] p {
        color: var(--muted) !important;
        font-size: .77rem !important;
        font-weight: 620 !important;
    }
    [data-testid="stMetricValue"] {
        color: #f0f4fc !important;
        font-size: 1.8rem !important;
        font-weight: 760 !important;
        letter-spacing: -.04em;
    }
    [data-testid="stMetricDelta"] { color: var(--muted) !important; }
    [data-testid="stExpander"], [data-testid="stPopover"] {
        background: var(--panel);
        border: 1px solid var(--border);
        border-radius: 11px;
    }
    [data-testid="stAlert"] {
        background: #141f34;
        border: 1px solid var(--border);
        border-radius: 10px;
        color: var(--text);
    }

    /* Inputs */
    .stTextInput input, .stTextArea textarea,
    .stNumberInput input, .stDateInput input,
    .stSelectbox div[data-baseweb="select"] > div,
    .stMultiSelect div[data-baseweb="select"] > div {
        background: #0f192b !important;
        border: 1px solid #2b3a53 !important;
        border-radius: 8px !important;
        color: #e6edf8 !important;
    }
    .stTextInput input::placeholder, .stTextArea textarea::placeholder {
        color: #73839d !important;
    }
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 1px rgba(120,149,245,.2) !important;
    }
    [data-baseweb="select"] * { color: #e6edf8 !important; }
    [data-baseweb="popover"], [data-baseweb="menu"] {
        background: #142037 !important;
        border: 1px solid var(--border) !important;
    }
    [role="option"]:hover { background: #223352 !important; }
    [data-testid="stFileUploader"] section {
        background: #101a2d;
        border: 1px dashed #405171;
        border-radius: 11px;
        padding: .9rem;
    }
    [data-testid="stFileUploader"] small,
    [data-testid="stFileUploader"] span { color: var(--muted) !important; }

    /* Buttons */
    .stButton > button, .stDownloadButton > button {
        min-height: 2.55rem;
        padding: .48rem .95rem;
        border-radius: 8px;
        border: 1px solid #34445f;
        background: #17243a;
        color: #dce5f5;
        font-weight: 650;
        transition: background .12s ease, border-color .12s ease;
    }
    .stButton > button:hover, .stDownloadButton > button:hover {
        border-color: #647fc8;
        background: #1d2c48;
        color: #ffffff;
    }
    .stButton > button[kind="primary"] {
        background: #526fce;
        border-color: #526fce;
        color: #fff;
    }
    .stButton > button[kind="primary"]:hover {
        background: #617fdf;
        border-color: #617fdf;
    }

    /* Tables */
    [data-testid="stDataFrame"], [data-testid="stDataEditor"] {
        background: #101a2b;
        border: 1px solid var(--border);
        border-radius: 10px;
        overflow: hidden;
    }
    [data-testid="stDataFrame"] *, [data-testid="stDataEditor"] * {
        color: #d8e1ef;
    }
    hr {
        border-color: var(--border) !important;
        margin: 1.25rem 0 !important;
    }
    [data-testid="stProgressBar"] > div {
        background: #202e46;
        border-radius: 20px;
    }
    [data-testid="stProgressBar"] > div > div {
        background: var(--accent-strong);
        border-radius: 20px;
    }
    code {
        color: #b8c8ff !important;
        background: #17243a !important;
    }
    @media (max-width: 800px) {
        [data-testid="stMainBlockContainer"] { padding: 1rem 1rem 2rem; }
        h1 { font-size: 1.55rem !important; }
        .hero-panel { padding: 1.2rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
TOKEN_FILE = "token.json"
CREDENTIALS_FILE = "credentials.json"
CV_PATH = os.path.join("uploads", "my_cv.pdf")
CV_ATTACHMENT_NAME = "Hamza_Ahmed_CV.pdf"
DAILY_SEND_LIMIT = 20


def describe_send_error(error):
    """Return a readable error, including Gmail API response details."""
    if isinstance(error, HttpError):
        try:
            details = error.content.decode("utf-8", errors="replace")
        except Exception:
            details = str(error)
        return f"Gmail API error (HTTP {error.status_code}): {details}"
    return f"{type(error).__name__}: {error}"


# --------------------------------------------------
# GMAIL AUTHENTICATION AND SENDING
# --------------------------------------------------

def connect_gmail():
    """Authenticate with Gmail and return an authorized Gmail API service."""
    if not os.path.exists(CREDENTIALS_FILE):
        raise FileNotFoundError(
            "credentials.json was not found. Put your Google OAuth "
            "Desktop App credentials.json in the project folder."
        )

    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(
            CREDENTIALS_FILE,
            SCOPES,
        )
        creds = flow.run_local_server(port=0)

    with open(TOKEN_FILE, "w", encoding="utf-8") as token_file:
        token_file.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def send_gmail_email(service, recipient, subject, body):
    """Send one email through Gmail and attach the uploaded CV."""
    if not os.path.exists(CV_PATH):
        raise FileNotFoundError(
            "CV attachment not found. Upload your CV before sending."
        )

    recipient = str(recipient).strip()
    if not recipient or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", recipient):
        raise ValueError(f"Invalid recipient email address: {recipient}")

    message = MIMEMultipart()
    message["to"] = recipient
    message["subject"] = str(subject)

    message.attach(MIMEText(str(body), "plain", "utf-8"))

    with open(CV_PATH, "rb") as cv_file:
        attachment = MIMEApplication(cv_file.read(), _subtype="pdf")
        attachment.add_header(
            "Content-Disposition",
            "attachment",
            filename=CV_ATTACHMENT_NAME,
        )
        message.attach(attachment)

    raw_message = base64.urlsafe_b64encode(
        message.as_bytes()
    ).decode("utf-8")

    result = (
        service.users()
        .messages()
        .send(userId="me", body={"raw": raw_message})
        .execute()
    )
    return result


# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------

if "cv_text" not in st.session_state:
    st.session_state.cv_text = load_cv() or ""

if "recruiters" not in st.session_state:
    loaded_recruiters = load_recruiters()
    st.session_state.recruiters = (
        loaded_recruiters
        if isinstance(loaded_recruiters, pd.DataFrame)
        else pd.DataFrame()
    )

if "gmail_connected" not in st.session_state:
    st.session_state.gmail_connected = False


# --------------------------------------------------
# JOB MATCHING
# --------------------------------------------------

def calculate_match(cv_text, job_title, job_description):
    cv_text = str(cv_text).lower()
    job_title = str(job_title).lower()
    job_description = str(job_description).lower()

    skills = [
        "python", "java", "javascript", "html", "css", "react",
        "fastapi", "django", "flask", "sql", "mysql", "mongodb",
        "machine learning", "deep learning", "pandas", "numpy",
        "scikit-learn", "git", "api", "data structures",
        "problem solving",
    ]

    matched_skills = []
    required_skills = []

    for skill in skills:
        # Use word boundaries for single-word skills and escaped text for phrases.
        pattern = r"\b" + re.escape(skill) + r"\b"
        if re.search(pattern, job_description) or re.search(pattern, job_title):
            required_skills.append(skill)
            if re.search(pattern, cv_text):
                matched_skills.append(skill)

    if not required_skills:
        return 0, [], "Low"

    score = round(len(matched_skills) / len(required_skills) * 100)

    if score >= 70:
        priority = "High"
    elif score >= 40:
        priority = "Medium"
    else:
        priority = "Low"

    return score, matched_skills, priority


# --------------------------------------------------
# EMAIL GENERATION
# --------------------------------------------------

def clean_value(value, fallback=""):
    if pd.isna(value):
        return fallback
    value = str(value).strip()
    return fallback if value.lower() == "nan" else value


GITHUB_PROFILE = "https://github.com/hamzaahmed213"

ROLE_TEMPLATES = {
    "Auto-detect": "Auto-detect",
    "Software Engineer / SDE": "Software Engineer / SDE",
    "Python Developer": "Python Developer",
    "Frontend / Web Developer": "Frontend / Web Developer",
    "Backend Developer": "Backend Developer",
    "AI / Machine Learning Intern": "AI / Machine Learning Intern",
    "Data Analyst / Data Science Intern": "Data Analyst / Data Science Intern",
    "General Internship": "General Internship",
}


def detect_role_template(role, description):
    text = f"{role} {description}".lower()

    if re.search(r"\bai\b", text) or any(word in text for word in ["machine learning", "artificial intelligence", "deep learning", "nlp", "computer vision", "ml intern"]):
        return "AI / Machine Learning Intern"
    if any(word in text for word in ["data analyst", "data science", "business analyst", "analytics", "bi analyst"]):
        return "Data Analyst / Data Science Intern"
    if any(word in text for word in ["frontend", "front-end", "front end", "react", "web developer", "ui developer"]):
        return "Frontend / Web Developer"
    if any(word in text for word in ["backend", "back-end", "back end", "api developer", "fastapi", "django"]):
        return "Backend Developer"
    if "python" in text:
        return "Python Developer"
    if any(word in text for word in ["software engineer", "software developer", "sde", "full stack", "full-stack"]):
        return "Software Engineer / SDE"
    return "General Internship"


def generate_email(recruiter, cv_text, template_type="Auto-detect"):
    name = clean_value(recruiter.get("recruiter_name", ""))
    company = clean_value(recruiter.get("company", ""))
    role = clean_value(recruiter.get("job_title", ""), "Internship")
    description = clean_value(recruiter.get("job_description", ""))

    if template_type == "Auto-detect":
        selected_template = detect_role_template(role, description)
    else:
        selected_template = template_type

    if name:
        greeting = f"Dear {name},"
    elif company:
        greeting = f"Hello {company} Hiring Team,"
    else:
        greeting = "Hello Hiring Team,"

    cv_text_lower = str(cv_text).lower()
    role_and_description = f"{role} {description}".lower()
    skills = [
        "Python", "Java", "JavaScript", "HTML", "CSS", "React",
        "FastAPI", "Django", "SQL", "Machine Learning", "Pandas",
        "NumPy", "Git", "API", "scikit-learn", "Flask",
    ]
    matched = [
        skill for skill in skills
        if skill.lower() in cv_text_lower and skill.lower() in role_and_description
    ]
    skill_text = ", ".join(matched[:5]) if matched else "Python, JavaScript, web development, and problem-solving"

    openings = {
        "Software Engineer / SDE": (
            f"I am writing to express my interest in the {role} opportunity at {company or 'your organization'}. "
            f"I am building my software development foundation through programming practice and projects, with exposure to {skill_text}. "
            "I am keen to contribute to practical engineering work, learn from the team, and strengthen my problem-solving skills."
        ),
        "Python Developer": (
            f"I would like to apply for the {role} opportunity at {company or 'your organization'}. "
            f"I have been developing my Python skills through hands-on practice and projects, alongside exposure to {skill_text}. "
            "I am interested in writing clean, useful code and contributing to real development tasks while learning from your team."
        ),
        "Frontend / Web Developer": (
            f"I am interested in the {role} opportunity at {company or 'your organization'}. "
            f"My web development experience includes working with {skill_text}, and I enjoy building clear, responsive user interfaces. "
            "I would value the opportunity to contribute to your web projects and grow through practical team experience."
        ),
        "Backend Developer": (
            f"I am reaching out to apply for the {role} opportunity at {company or 'your organization'}. "
            f"I am developing my backend and programming skills, with exposure to {skill_text}. "
            "I am particularly interested in APIs, application logic, and building reliable services, and would welcome the chance to contribute."
        ),
        "AI / Machine Learning Intern": (
            f"I am writing to express my interest in the {role} opportunity at {company or 'your organization'}. "
            f"I have an academic and project-based interest in AI and machine learning, with exposure to {skill_text}. "
            "I am eager to learn from real-world workflows and contribute to data-driven or machine-learning projects under your team's guidance."
        ),
        "Data Analyst / Data Science Intern": (
            f"I would like to be considered for the {role} opportunity at {company or 'your organization'}. "
            f"I am building my data and programming skills through hands-on learning, with exposure to {skill_text}. "
            "I am interested in working with data, identifying useful insights, and supporting practical analytical projects."
        ),
        "General Internship": (
            f"I am reaching out to express my interest in the {role} opportunity at {company or 'your organization'}. "
            f"I am an IT student building my technical skills through programming practice and projects, with exposure to {skill_text}. "
            "I would appreciate the opportunity to contribute, learn from your team, and be considered for this opening."
        ),
    }

    subject = f"Application for {role}"
    body = f"""{greeting}

{openings[selected_template]}

You can find my projects and code on GitHub:
{GITHUB_PROFILE}

I have attached my resume for your consideration. I would be grateful for the opportunity to discuss how I could contribute to your team.

Thank you for your time.

Best regards,
Hamza Ahmed"""

    return subject, body.strip()


# --------------------------------------------------
# NAVIGATION
# --------------------------------------------------

st.markdown(
    """
    <div class="workspace-kicker">PERSONAL WORKSPACE</div>
    """,
    unsafe_allow_html=True,
)

st.sidebar.markdown(
    """
    <div class="brand-lockup">
        <div class="brand-mark">O</div>
        <div>
            <div class="brand-name">Outreach Studio</div>
            <div class="brand-sub">Internship application workspace</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

page = st.sidebar.radio(
    "WORKSPACE",
    [
        "Dashboard",
        "Upload CV",
        "Recruiter Database",
        "Job Matching",
        "Email Generator",
        "Draft Manager",
        "Outreach Tracker",
        "Settings",
    ],
)

st.sidebar.divider()
cv_ready = os.path.exists(CV_PATH)
recruiter_total = len(st.session_state.recruiters)
token_saved = os.path.exists(TOKEN_FILE)
st.sidebar.markdown(
    f"""
    <div class="sidebar-status">{"●" if cv_ready else "○"} &nbsp; CV {"ready" if cv_ready else "not uploaded"}</div>
    <div class="sidebar-status">{"●" if recruiter_total else "○"} &nbsp; {recruiter_total} recruiters imported</div>
    <div class="sidebar-status">{"●" if token_saved else "○"} &nbsp; Gmail setup {"saved" if token_saved else "not connected"}</div>
    """,
    unsafe_allow_html=True,
)
st.sidebar.caption("Review every draft before sending.")


# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------

if page == "Dashboard":
    st.markdown(
        """
        <div class="hero-panel">
            <h2>Your outreach, organised.</h2>
            <p>Manage recruiter contacts, match opportunities to your CV, prepare role-specific emails, and send only the drafts you approve.</p>
            <span class="hero-pill">✦ &nbsp; Internship search workspace</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    sent_count, pending_count = get_email_counts()
    sent_today = get_sent_today()

    col1, col2, col3 = st.columns(3)
    col1.metric("Recruiters imported", len(st.session_state.recruiters))
    col2.metric("Emails sent", sent_count)
    col3.metric("Awaiting approval", pending_count)

    st.divider()
    left, right = st.columns([1.45, 1])
    with left:
        st.subheader("Daily sending activity")
        st.caption("Your app-level sending safeguard")
        st.metric("Successful sends today", f"{sent_today} / {DAILY_SEND_LIMIT}")
        st.progress(min(sent_today / DAILY_SEND_LIMIT, 1.0))
        st.caption(f"{max(DAILY_SEND_LIMIT - sent_today, 0)} sends remaining under the app's daily limit.")
    with right:
        st.subheader("Quick workflow")
        st.markdown(
            """
            1. **Upload CV** — save your latest resume.
            2. **Recruiter Database** — import your Excel contacts.
            3. **Job Matching** — review role fit and priority.
            4. **Email Generator** — create and edit a draft.
            5. **Draft Manager** — approve and send.
            """
        )


# --------------------------------------------------
# UPLOAD CV
# --------------------------------------------------

elif page == "Upload CV":
    st.header("CV Intelligence")

    cv_upload = st.file_uploader(
        "Upload your resume (PDF)",
        type=["pdf"],
        key="cv_uploader",
    )

    if cv_upload is not None:
        try:
            reader = PdfReader(io.BytesIO(cv_upload.getvalue()))
            extracted_text = "\n".join(
                pdf_page.extract_text() or ""
                for pdf_page in reader.pages
            ).strip()

            if not extracted_text:
                st.warning(
                    "No readable text was found in this PDF. "
                    "Try a text-based PDF rather than a scanned image."
                )
            else:
                os.makedirs("uploads", exist_ok=True)

                with open(CV_PATH, "wb") as cv_file:
                    cv_file.write(cv_upload.getbuffer())

                with open(
                    os.path.join("uploads", "cv_text.txt"),
                    "w",
                    encoding="utf-8",
                ) as text_file:
                    text_file.write(extracted_text)

                st.session_state.cv_text = extracted_text
                save_cv(extracted_text)

                st.success(
                    f"CV processed and saved. It will be attached to every "
                    f"email sent by this app as {CV_ATTACHMENT_NAME}."
                )
                st.text_area(
                    "Extracted CV information",
                    extracted_text,
                    height=300,
                )

        except Exception as error:
            st.error(f"CV reading error: {error}")

    elif st.session_state.cv_text:
        st.success("Your CV text is already loaded.")

        if os.path.exists(CV_PATH):
            st.success(f"Attachment file ready: {CV_ATTACHMENT_NAME}")
        else:
            st.warning(
                "Your CV text is saved, but the PDF attachment is missing. "
                "Upload the PDF again before sending emails."
            )

        st.text_area(
            "Current CV information",
            st.session_state.cv_text,
            height=300,
        )


# --------------------------------------------------
# RECRUITER DATABASE
# --------------------------------------------------

elif page == "Recruiter Database":
    st.header("Recruiter Intelligence")

    excel_upload = st.file_uploader(
        "Upload recruiter Excel sheet",
        type=["xlsx", "xls"],
        key="recruiter_excel_uploader",
    )

    if excel_upload is not None:
        try:
            df = pd.read_excel(excel_upload)
            df.columns = (
                df.columns.astype(str)
                .str.strip()
                .str.lower()
                .str.replace(" ", "_", regex=False)
            )

            aliases = {
                "recruiter_name": ["name", "hr_name", "contact_person"],
                "email": ["email_address", "recruiter_email", "contact_email"],
                "company": ["company_name", "organization"],
                "job_title": ["role", "position", "job_role", "title"],
                "job_description": [
                    "description", "job_details", "requirements"
                ],
                "job_link": ["link", "application_link", "url"],
            }

            for standard, alternatives in aliases.items():
                if standard not in df.columns:
                    for alternative in alternatives:
                        if alternative in df.columns:
                            df.rename(
                                columns={alternative: standard},
                                inplace=True,
                            )
                            break

            if "email" not in df.columns:
                st.error("Email column not found in the uploaded Excel file.")
            else:
                df["email"] = (
                    df["email"]
                    .fillna("")
                    .astype(str)
                    .str.strip()
                    .str.lower()
                )

                valid_email = df["email"].str.fullmatch(
                    r"[^@\s]+@[^@\s]+\.[^@\s]+"
                )
                df = df[valid_email].copy()
                total_valid = len(df)

                df.drop_duplicates(
                    subset=["email"],
                    keep="first",
                    inplace=True,
                )
                duplicates_removed = total_valid - len(df)

                for column in [
                    "recruiter_name",
                    "company",
                    "job_title",
                    "job_description",
                    "job_link",
                ]:
                    if column not in df.columns:
                        df[column] = ""

                df = df[
                    [
                        "recruiter_name",
                        "email",
                        "company",
                        "job_title",
                        "job_description",
                        "job_link",
                    ]
                ]

                st.session_state.recruiters = df
                save_recruiters(df)

                col1, col2 = st.columns(2)
                col1.metric("Valid unique recruiters", len(df))
                col2.metric("Duplicates removed", duplicates_removed)

                st.dataframe(df, use_container_width=True)

                st.download_button(
                    "Download cleaned CSV",
                    data=df.to_csv(index=False).encode("utf-8"),
                    file_name="cleaned_recruiters.csv",
                    mime="text/csv",
                )

        except Exception as error:
            st.error(f"Excel import failed: {error}")

    if not st.session_state.recruiters.empty:
        st.subheader("Currently Loaded Recruiters")
        st.dataframe(
            st.session_state.recruiters,
            use_container_width=True,
        )

        recruiter_export = st.session_state.recruiters
        export_col1, export_col2 = st.columns(2)
        with export_col1:
            st.download_button(
                "Download Recruiter Database (CSV)",
                data=recruiter_export.to_csv(index=False).encode("utf-8"),
                file_name="recruiter_database.csv",
                mime="text/csv",
                key="download_recruiter_database_csv",
            )
        with export_col2:
            recruiter_excel = io.BytesIO()
            with pd.ExcelWriter(recruiter_excel, engine="openpyxl") as writer:
                recruiter_export.to_excel(writer, index=False, sheet_name="Recruiters")
            st.download_button(
                "Download Recruiter Database (Excel)",
                data=recruiter_excel.getvalue(),
                file_name="recruiter_database.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_recruiter_database_xlsx",
            )


# --------------------------------------------------
# JOB MATCHING
# --------------------------------------------------

elif page == "Job Matching":
    st.header("Job Matching Engine")

    cv_text = st.session_state.cv_text
    recruiters = st.session_state.recruiters

    if not cv_text:
        st.warning("Please upload your CV first.")
    elif recruiters.empty:
        st.warning("Please import your recruiter Excel sheet first.")
    else:
        results = []

        for _, recruiter in recruiters.iterrows():
            score, matched, priority = calculate_match(
                cv_text,
                recruiter.get("job_title", ""),
                recruiter.get("job_description", ""),
            )

            results.append(
                {
                    "Recruiter": clean_value(
                        recruiter.get("recruiter_name", ""),
                        "Hiring Team",
                    ),
                    "Company": clean_value(
                        recruiter.get("company", ""),
                        "Unknown",
                    ),
                    "Job Role": clean_value(
                        recruiter.get("job_title", ""),
                        "Unknown",
                    ),
                    "Email": recruiter.get("email", ""),
                    "Match Score": score,
                    "Priority": priority,
                    "Matched Skills": ", ".join(matched),
                }
            )

        result_df = pd.DataFrame(results).sort_values(
            by="Match Score",
            ascending=False,
        )

        high = int((result_df["Priority"] == "High").sum())
        medium = int((result_df["Priority"] == "Medium").sum())
        low = int((result_df["Priority"] == "Low").sum())

        col1, col2, col3 = st.columns(3)
        col1.metric("High Priority", high)
        col2.metric("Medium Priority", medium)
        col3.metric("Low Priority", low)

        st.subheader("Matching Results")
        st.dataframe(result_df, use_container_width=True)

        match_col1, match_col2 = st.columns(2)
        with match_col1:
            st.download_button(
                "Download Matching Results (CSV)",
                data=result_df.to_csv(index=False).encode("utf-8"),
                file_name="job_matching_results.csv",
                mime="text/csv",
                key="download_matching_results_csv",
            )
        with match_col2:
            matching_excel = io.BytesIO()
            with pd.ExcelWriter(matching_excel, engine="openpyxl") as writer:
                result_df.to_excel(writer, index=False, sheet_name="Job Matches")
            st.download_button(
                "Download Matching Results (Excel)",
                data=matching_excel.getvalue(),
                file_name="job_matching_results.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_matching_results_xlsx",
            )


# --------------------------------------------------
# EMAIL GENERATOR
# --------------------------------------------------

elif page == "Email Generator":
    st.header("Personalized Email Generator")

    cv_text = st.session_state.cv_text
    recruiters = st.session_state.recruiters

    if not cv_text:
        st.warning("Upload your CV first.")
    elif recruiters.empty:
        st.warning("Import your recruiter Excel sheet first.")
    else:
        st.write("Select a recruiter to generate a personalized email.")

        recruiter_options = recruiters.index.tolist()
        selected_index = st.selectbox(
            "Choose Recruiter",
            recruiter_options,
            format_func=lambda index: (
                f"{clean_value(recruiters.loc[index].get('company', ''), 'Unknown')} - "
                f"{clean_value(recruiters.loc[index].get('job_title', ''), 'Unknown')} "
                f"({recruiters.loc[index].get('email', '')})"
            ),
        )

        recruiter = recruiters.loc[selected_index]
        detected_template = detect_role_template(
            clean_value(recruiter.get("job_title", ""), "Internship"),
            clean_value(recruiter.get("job_description", "")),
        )
        template_options = list(ROLE_TEMPLATES.keys())
        selected_template = st.selectbox(
            "Email template / job role",
            template_options,
            index=template_options.index("Auto-detect"),
            help=f"Auto-detect currently suggests: {detected_template}. You can choose another template manually.",
            key=f"email_template_{selected_index}",
        )
        subject, body = generate_email(recruiter, cv_text, selected_template)
        st.caption(f"Selected template: {detected_template if selected_template == 'Auto-detect' else selected_template}")

        st.divider()
        st.subheader("Email Preview")

        st.text_input(
            "Recipient",
            value=clean_value(recruiter.get("email", "")),
            disabled=True,
        )

        edited_subject = st.text_input(
            "Subject",
            value=subject,
            key=f"email_subject_{selected_index}",
        )

        edited_body = st.text_area(
            "Email Body",
            value=body,
            height=300,
            key=f"email_body_{selected_index}",
        )

        if os.path.exists(CV_PATH):
            st.success(f"CV will be attached as {CV_ATTACHMENT_NAME}.")
        else:
            st.warning("Upload your PDF CV; it is required before sending.")

        st.download_button(
            "Download Email Draft",
            data=f"Subject: {edited_subject}\n\n{edited_body}",
            file_name="email_draft.txt",
            mime="text/plain",
        )

        if st.button("Save Draft", type="primary"):
            recipient = clean_value(recruiter.get("email", "")).lower()

            if not recipient:
                st.error("This recruiter does not have a valid email address.")
            elif not edited_subject.strip() or not edited_body.strip():
                st.error("Subject and email body cannot be empty.")
            else:
                save_draft(recipient, edited_subject.strip(), edited_body.strip())
                st.success("Email draft saved successfully. Open Draft Manager to preview and approve it.")

        st.info(
            "Review and save the draft here. Emails are only sent after "
            "you approve them in Draft Manager."
        )


# --------------------------------------------------
# DRAFT MANAGER / APPROVED BATCH SENDING
# --------------------------------------------------

elif page == "Draft Manager":
    st.header("📨 Batch Email Manager")

    drafts = load_drafts()

    if drafts.empty:
        st.info("No saved drafts yet. Generate and save an email first.")
    else:
        # Ensure expected fields are present in the returned draft table.
        required_draft_columns = {
            "id", "recruiter_email", "subject", "body", "status"
        }
        missing_columns = required_draft_columns.difference(drafts.columns)

        if missing_columns:
            st.error(
                "The drafts table is missing these fields: "
                + ", ".join(sorted(missing_columns))
            )
        else:
            st.subheader("Saved Drafts")
            draft_export_col1, draft_export_col2 = st.columns(2)
            with draft_export_col1:
                st.download_button(
                    "Download All Drafts (CSV)",
                    data=drafts.to_csv(index=False).encode("utf-8"),
                    file_name="email_drafts.csv",
                    mime="text/csv",
                    key="download_all_drafts_csv",
                )
            with draft_export_col2:
                drafts_excel = io.BytesIO()
                with pd.ExcelWriter(drafts_excel, engine="openpyxl") as writer:
                    drafts.to_excel(writer, index=False, sheet_name="Email Drafts")
                st.download_button(
                    "Download All Drafts (Excel)",
                    data=drafts_excel.getvalue(),
                    file_name="email_drafts.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_all_drafts_xlsx",
                )

            st.subheader("Preview Email")

            draft_ids = drafts["id"].tolist()
            selected_draft_id = st.selectbox(
                "Choose a saved draft to preview",
                draft_ids,
                format_func=lambda draft_id: (
                    f"{drafts.loc[drafts['id'] == draft_id, 'recruiter_email'].iloc[0]} "
                    f"— {drafts.loc[drafts['id'] == draft_id, 'subject'].iloc[0]}"
                ),
                key="draft_preview_selector",
            )

            selected_draft = drafts.loc[
                drafts["id"] == selected_draft_id
            ].iloc[0]

            st.text_input(
                "Recipient",
                value=str(selected_draft["recruiter_email"]),
                disabled=True,
                key="preview_recipient",
            )
            st.text_input(
                "Subject",
                value=str(selected_draft["subject"]),
                disabled=True,
                key="preview_subject",
            )
            st.text_area(
                "Full Email Body",
                value=str(selected_draft["body"]),
                height=260,
                disabled=True,
                key="preview_body",
            )

            if os.path.exists(CV_PATH):
                st.success(
                    f"Attachment ready: {CV_ATTACHMENT_NAME} "
                    "(this PDF is attached automatically to each email sent)."
                )
            else:
                st.error(
                    "CV PDF is missing. Upload it again before sending any emails."
                )

            st.divider()
            st.subheader("Approve drafts for sending")
            st.caption(
                "Tick only the drafts you have reviewed. The app sends only "
                "the checked rows when you press the button."
            )

            approval_view = drafts[
                ["id", "recruiter_email", "subject", "status"]
            ].copy()
            approval_view.insert(0, "Approve", False)

            edited_approval = st.data_editor(
                approval_view,
                use_container_width=True,
                hide_index=True,
                disabled=[
                    "id",
                    "recruiter_email",
                    "subject",
                    "status",
                ],
                column_config={
                    "Approve": st.column_config.CheckboxColumn(
                        "Approve for sending",
                        help="Tick to approve this draft for the next batch.",
                        default=False,
                    )
                },
                key="draft_approval_table",
            )

            selected_drafts = edited_approval[
                edited_approval["Approve"] == True
            ]

            st.write(f"Approved in this batch: {len(selected_drafts)}")

            if st.button(
                "🚀 Send Approved Batch",
                type="primary",
                disabled=selected_drafts.empty,
            ):
                sent_today = get_sent_today()
                remaining_today = DAILY_SEND_LIMIT - sent_today

                if remaining_today <= 0:
                    st.error(
                        f"Daily app limit reached ({DAILY_SEND_LIMIT} successful "
                        "emails). Try again tomorrow."
                    )
                elif not os.path.exists(CV_PATH):
                    st.error("Please upload your PDF CV before sending.")
                else:
                    successful = 0
                    failed = 0
                    skipped = 0

                    try:
                        gmail_service = connect_gmail()

                        progress = st.progress(0)
                        status_message = st.empty()
                        total_selected = len(selected_drafts)

                        for position, (_, draft) in enumerate(
                            selected_drafts.iterrows(),
                            start=1,
                        ):
                            draft_id = int(draft["id"])

                            # The approval table intentionally contains only
                            # summary columns, so fetch the full saved draft
                            # (including its body) from the original drafts
                            # dataframe before sending.
                            full_draft_rows = drafts.loc[drafts["id"] == draft_id]
                            if full_draft_rows.empty:
                                st.error(
                                    f"Could not find the complete saved draft for ID {draft_id}."
                                )
                                failed += 1
                                progress.progress(position / total_selected)
                                continue

                            full_draft = full_draft_rows.iloc[0]
                            recipient = clean_value(
                                full_draft["recruiter_email"]
                            ).lower()

                            if successful >= remaining_today:
                                status_message.warning(
                                    "The daily limit has been reached. "
                                    "The remaining approved drafts were not sent."
                                )
                                break
                            # Do not send to a recipient who already has a
                            # successful send recorded in this app.
                            if has_sent_email(recipient):
                                update_draft_status(
                                    draft_id,
                                    "Skipped - Already Sent",
                                )
                                skipped += 1
                                progress.progress(position / total_selected)
                                continue

                            # First isolate the Gmail operation. A database
                            # error after Gmail accepts a message must not be
                            # reported as a failed email send.
                            try:
                                gmail_result = send_gmail_email(
                                    gmail_service,
                                    recipient,
                                    full_draft["subject"],
                                    full_draft["body"],
                                )
                            except Exception as send_error:
                                error_message = describe_send_error(send_error)

                                try:
                                    log_email(recipient, "Failed", error_message)
                                except Exception as log_error:
                                    st.error(
                                        f"Could not save the failure log: {log_error}"
                                    )

                                try:
                                    update_draft_status(draft_id, "Failed")
                                except Exception as status_error:
                                    st.error(
                                        f"Could not update draft status: {status_error}"
                                    )

                                st.error(
                                    f"Email sending failed for {recipient}: "
                                    f"{error_message}"
                                )
                                failed += 1
                                progress.progress(position / total_selected)
                                continue

                            # Gmail returned successfully: count this as sent.
                            successful += 1
                            message_id = (
                                gmail_result.get("id", "accepted by Gmail")
                                if isinstance(gmail_result, dict)
                                else "accepted by Gmail"
                            )
                            try:
                                log_email(recipient, "Sent")
                                update_draft_status(draft_id, "Sent")
                                st.success(
                                    f"Gmail accepted the email to {recipient} "
                                    f"(message ID: {message_id})."
                                )
                            except Exception as tracking_error:
                                st.warning(
                                    f"Gmail accepted the email to {recipient}, "
                                    "but the app could not update its tracking "
                                    f"record: {tracking_error}. Do not resend it "
                                    "until you check your Gmail Sent folder."
                                )

                            progress.progress(position / total_selected)

                        st.success(f"Successfully sent: {successful}")

                        if failed:
                            st.error(f"Failed: {failed}")

                        if skipped:
                            st.warning(
                                f"Skipped because an email was already sent "
                                f"to that address: {skipped}"
                            )

                        st.rerun()

                    except Exception as connection_error:
                        st.error(
                            "Gmail connection or batch setup failed: "
                            f"{connection_error}"
                        )
# --------------------------------------------------
# OUTREACH TRACKER
# --------------------------------------------------

elif page == "Outreach Tracker":
    st.header("📊 Outreach Tracker")

    tracker = get_outreach_tracker()

    if tracker.empty:
        st.info("Import recruiters to start tracking outreach.")
    else:
        sent_count = int(tracker["Sent"].sum())
        remaining_count = len(tracker) - sent_count

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Recruiters", len(tracker))
        col2.metric("Emails Sent", sent_count)
        col3.metric("Still Remaining", remaining_count)

        st.divider()
        st.subheader("Recruiter Sending Status")

        st.data_editor(
            tracker,
            use_container_width=True,
            hide_index=True,
            disabled=True,
            column_config={
                "Sent": st.column_config.CheckboxColumn(
                    "Sent",
                    help="Automatically checked after a successful send.",
                )
            },
        )


# --------------------------------------------------
# SETTINGS
# --------------------------------------------------

elif page == "Settings":
    st.header("Settings")
    st.subheader("Gmail Integration")

    st.write(
        "Connect the Gmail account that should send your approved outreach "
        "emails. This app uses Google's OAuth authorization; it does not "
        "ask for or store your Gmail password."
    )

    if st.button("Connect Gmail"):
        try:
            with st.spinner("Verifying Gmail authorization..."):
                connect_gmail()

            st.session_state.gmail_connected = True
            st.success("Gmail authorized successfully.")
            st.info(
                "Gmail sending authorization is active. Emails will only be "
                "sent from Draft Manager after you approve them."
            )
        except Exception as error:
            st.session_state.gmail_connected = False
            st.error(f"Gmail connection failed: {error}")

    if st.session_state.get("gmail_connected", False):
        st.success("Gmail sending authorization is active.")

    st.divider()
    st.subheader("Sending safeguards")
    st.write(f"- App-level daily limit: {DAILY_SEND_LIMIT} successful emails.")
    st.write("- Every outgoing email includes your uploaded CV PDF.")
    st.write("- A recipient with a previous successful send is skipped.")
    st.write("- Failed sends are logged and can be reviewed in the tracker.")
    st.caption(
        "The daily limit is an app safeguard, not a guarantee of Gmail "
        "deliverability or protection from spam filtering."
    )
