# 📬 Outreach Studio — Internship Outreach Bot

A local-first, human-in-the-loop **internship application automation workspace** built with **Python + Streamlit**, backed by **SQLite**, integrated with the **Gmail API** for secure sending, and powered by **pandas + pypdf** for spreadsheet ingestion and résumé parsing.

This README explains **how the app is built**, **what every component does**, the **technical decisions behind it**, and the **real-world value** it delivers.

---

## 📖 Table of Contents

1. [Overview](#-overview)
2. [Problem It Solves](#-problem-it-solves)
3. [Feature Walkthrough](#-feature-walkthrough)
4. [Tech Stack](#-tech-stack)
5. [Project Structure](#-project-structure)
6. [Architecture & Data Flow](#-architecture--data-flow)
7. [Database Schema](#-database-schema)
8. [How Each Module Works (Technical Deep Dive)](#-how-each-module-works-technical-deep-dive)
9. [Gmail Integration & Security Model](#-gmail-integration--security-model)
10. [Sending Safeguards (Reliability Engineering)](#-sending-safeguards-reliability-engineering)
11. [Design System & UI](#-design-system--ui)
12. [Setup & Installation](#-setup--installation)
13. [Usage Workflow](#-usage-workflow)
14. [Real-World Contribution](#-real-world-contribution)
15. [Limitations & Future Work](#-limitations--future-work)

---

## 🎯 Overview

**Outreach Studio** is a single-user Streamlit web app that turns a messy spreadsheet of recruiter contacts and job openings into a **reviewed, personalized, tracked email outreach pipeline** — without leaving a private local environment.

It combines four normally-separate activities:

| Activity | Normally done in | This app |
|---|---|---|
| Résumé parsing | Manual copy-paste | `pypdf` extraction |
| Job-fit scoring | Human judgment | Keyword-based matching engine |
| Email personalization | Blank text editor | Role-aware template generator |
| Sending + tracking | Gmail + spreadsheet | Gmail API + SQLite tracker |

The core philosophy is **automation with consent** — the app drafts and prepares, but **nothing is sent until you explicitly tick a checkbox and press a button**.

---

## 🧩 Problem It Solves

Job seekers — especially students applying to internships — face a repetitive loop:

1. Skim a job description.
2. Manually judge if it fits their skills.
3. Write a semi-generic cover email.
4. Copy-paste the same body dozens of times.
5. Forget who was emailed and resend by accident.
6. Lose track of whether the CV was actually attached.

Each step is small, but doing it for 50–200 recruiters creates **human error, duplicated outreach, and reputation risk** (emailing the same person twice or spamming). This app centralizes that whole loop into one **safe, local, auditable** workflow.

---

## ✨ Feature Walkthrough

The app is organised into eight sidebar pages:

### 1. 🏠 Dashboard
- Live counters: **recruiters imported**, **emails sent**, **drafts awaiting approval**.
- **Daily sending activity bar** showing progress against the 20-email app limit.
- Guided "Quick workflow" checklist.

### 2. 📄 Upload CV
- Accepts a **PDF résumé**.
- Extracts readable text with **`pypdf.PdfReader`**.
- Persists the PDF to `uploads/my_cv.pdf` (used later as the **email attachment**) and the extracted text to SQLite (`app_data` table) and `uploads/cv_text.txt`.
- Warns if the PDF is a scanned image (no extractable text).

### 3. 🗂 Recruiter Database
- Uploads an **Excel file** (`.xlsx` / `.xls`).
- **Column normalization**: strips whitespace, lowercases, replaces spaces with underscores.
- **Alias mapping** so that `HR Name`, `Contact Person`, `Email Address`, `Role`, `Description`, etc. all map to canonical fields.
- **Email validation** via regex `^[^@\s]+@[^@\s]+\.[^@\s]+$`.
- **Deduplication** on email (reports how many were removed).
- Persists to SQLite with `INSERT … ON CONFLICT(email) DO UPDATE` — so re-imports refresh data instead of erroring.
- Exports cleaned data as **CSV and Excel**.

### 4. 🎯 Job Matching
- Scores each recruiter/job against the stored CV text.
- Produces a **Match Score (0–100)**, **Priority (High / Medium / Low)**, and a **list of matched skills**.
- Sorts results by score descending.
- Exports matching report as CSV or Excel.

### 5. ✍️ Email Generator
- Select a recruiter → app **auto-detects the target role** from job title + description.
- Generates a **role-specific, personalized email body** (subject + body) using a hand-curated template library.
- Lets the user **edit subject and body freely** before saving.
- Saves a **draft** into SQLite (`email_drafts`) for later review.
- Clearly warns whether the CV PDF is available for attachment.

### 6. 📨 Draft Manager
- Lists all saved drafts.
- Displays a **disabled preview panel** (recipient / subject / body) for the selected draft.
- Shows an **editable approval table** using `st.data_editor` with a **CheckboxColumn** — this is the human consent gate.
- On "🚀 Send Approved Batch":
  - Enforces the **daily limit**.
  - **Skips recipients already successfully emailed** (idempotency).
  - Sends via **Gmail API** with the CV attached.
  - Logs success/failure per email.
  - Shows **live progress bar** and per-recipient status messages.
  - Handles **partial failures gracefully** (see [Sending Safeguards](#-sending-safeguards-reliability-engineering)).

### 7. 📊 Outreach Tracker
- Per-recruiter table showing:
  - Whether an email was **Sent**.
  - **Sent Date**, **Latest Status**, and **Last Attempt**.
- Uses correlated `EXISTS`/`MAX` subqueries in SQL to derive state from the `email_logs` table.
- Real-time aggregate metrics: Total / Sent / Remaining.

### 8. ⚙️ Settings
- Gmail OAuth **connect** button.
- Lists **all active safeguards** so the user knows exactly what protections are running.

---

## 🛠 Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **UI framework** | Streamlit | Turns Python into a reactive web app |
| **Language** | Python 3.9+ | Application logic |
| **Database** | SQLite (`sqlite3`) | Local persistence, no server required |
| **Data manipulation** | pandas | Excel/CSV ingest, transforms, exports |
| **Excel engine** | openpyxl | Writing `.xlsx` downloads |
| **PDF parsing** | pypdf | Extracting text from résumé PDFs |
| **Email sending** | Gmail API (`googleapiclient`, `google-auth`, `google-auth-oauthlib`) | Sending with OAuth 2.0 |
| **MIME construction** | `email.mime.multipart`, `email.mime.text`, `email.mime.application` | Building multipart email with PDF attachment |
| **Encoding** | `base64` | Gmail API raw message encoding |
| **Regex / text** | `re` | Email validation, skill matching, role detection |
| **I/O streaming** | `io.BytesIO` | In-memory PDF and Excel handling |
| **Styling** | Injected CSS via `st.markdown(..., unsafe_allow_html=True)` | Dark theme design system |

> **Design decision:** the entire stack is **local-first**. No external database, no cloud auth for the app itself, and the only outbound network call is to Gmail.

---

## 📂 Project Structure

```
project/
├── app.py                # Streamlit UI + all pages + business logic
├── database.py           # SQLite data access layer
├── outreach.db           # Auto-created SQLite database
├── credentials.json      # Google OAuth Desktop App credentials (user-provided)
├── token.json            # Cached OAuth access/refresh token (auto-created)
└── uploads/
    ├── my_cv.pdf         # The CV attachment sent with every email
    └── cv_text.txt       # Extracted CV text (mirror of DB value)
```

**Separation of concerns:**
- `app.py` owns **all presentation and orchestration**.
- `database.py` owns **all SQL**. No SQL strings leak into `app.py`.
- That makes the DB layer independently testable and swappable.

---

## 🔄 Architecture & Data Flow

```
┌───────────────────────┐
│  User uploads         │
│  - Résumé PDF         │
│  - Recruiter Excel    │
└──────────┬────────────┘
           │
           ▼
┌───────────────────────────┐
│ Streamlit session_state   │
│  - cv_text                │
│  - recruiters (DataFrame) │
│  - gmail_connected        │
└──────────┬────────────────┘
           │
           ▼
┌──────────────────────────────┐
│  Matching Engine             │
│  (skills × job description)  │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│  Email Generator             │
│  (template detection + fill) │
└──────────┬───────────────────┘
           │  save_draft()
           ▼
┌──────────────────────────────┐
│  SQLite: email_drafts        │
│  status = "Pending"          │
└──────────┬───────────────────┘
           │  User ticks checkbox
           ▼
┌──────────────────────────────┐
│  Draft Manager send loop     │
│  - daily limit check         │
│  - has_sent_email() check    │
│  - Gmail API send (with CV)  │
│  - log_email()               │
│  - update_draft_status()     │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│  SQLite: email_logs          │
│  → Outreach Tracker reads it │
└──────────────────────────────┘
```

State is **re-derived from SQLite on each Streamlit rerun**, so the app is resilient to browser refreshes and process restarts.

---

## 🗃 Database Schema

Defined and created idempotently in `init_db()`:

### `app_data`
| Column | Type | Purpose |
|---|---|---|
| `key` | TEXT PRIMARY KEY | e.g. `'cv_text'` |
| `value` | TEXT | The stored CV text |

### `recruiters`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK AUTOINCREMENT | |
| `recruiter_name` | TEXT | |
| `email` | TEXT **UNIQUE** | Enables upsert |
| `company` | TEXT | |
| `job_title` | TEXT | |
| `job_description` | TEXT | |
| `job_link` | TEXT | |
| `status` | TEXT DEFAULT `'New'` | |

### `email_drafts`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `recruiter_email` | TEXT | |
| `subject` | TEXT | |
| `body` | TEXT | |
| `status` | TEXT DEFAULT `'Pending'` | `Pending`, `Sent`, `Failed`, `Skipped - Already Sent` |
| `created_at` | TIMESTAMP | Auto |

### `email_logs`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `recruiter_email` | TEXT | |
| `status` | TEXT | `'Sent'` or `'Failed'` |
| `sent_at` | TIMESTAMP | Auto |
| `error_message` | TEXT | Populated on failure |

> **Why this schema?** Drafts and logs are deliberately **separate tables**: drafts model *intent*, logs model *history*. That lets the app reason about "approved but not yet sent" and "sent successfully before" independently.

---

## 🔬 How Each Module Works (Technical Deep Dive)

### 1. Résumé Extraction (`Upload CV`)

```python
reader = PdfReader(io.BytesIO(cv_upload.getvalue()))
extracted_text = "\n".join(
    pdf_page.extract_text() or "" for pdf_page in reader.pages
).strip()
```

- Reads the PDF **in memory** via `io.BytesIO` — no temp files.
- Joins page text with newlines.
- Guards against image-only PDFs by checking `if not extracted_text`.
- Writes the raw PDF to `uploads/my_cv.pdf` (this exact path is later used for attachment) and the text to both SQLite and a plaintext mirror.

---

### 2. Match Scoring (`calculate_match`)

```python
skills = ["python", "java", "javascript", ..., "problem solving"]

for skill in skills:
    pattern = r"\b" + re.escape(skill) + r"\b"
    if re.search(pattern, job_description) or re.search(pattern, job_title):
        required_skills.append(skill)
        if re.search(pattern, cv_text):
            matched_skills.append(skill)

score = round(len(matched_skills) / len(required_skills) * 100)
```

- **Word-boundary regex** prevents false positives (`"R"` matching inside `"React"`, etc.).
- `re.escape()` safely handles multi-word skills like `"machine learning"`.
- Denominator is **required skills** (skills *in the job*), so a low score always means a genuine gap, not a skills-list mismatch.
- Priority thresholds: **≥70 High**, **≥40 Medium**, otherwise **Low**.

**Trade-off:** this is a **transparent, deterministic** heuristic — not semantic NLP. It's fast, explainable, and free. A future version could swap in embeddings/LLM matching without changing the UI.

---

### 3. Role-Aware Email Generation

#### Template detection (`detect_role_template`)

```python
if re.search(r"\bai\b", text) or any(word in text for word in ["machine learning", ...]):
    return "AI / Machine Learning Intern"
if any(word in text for word in ["data analyst", "data science", ...]):
    return "Data Analyst / Data Science Intern"
# ... frontend, backend, python, software engineer fallbacks
```

- Ordered **most-specific → least-specific** decision tree.
- Falls back to `"General Internship"`.

#### Body generation (`generate_email`)

- **Greeting fallback chain**: `Dear {name},` → `Hello {company} Hiring Team,` → `Hello Hiring Team,`.
- **Dynamic skill list**: intersects `skills` with **both** the CV and the job context (`role_and_description`). Falls back to a generic line if none overlap — so even weak matches produce a coherent email.
- **Seven role-specific opening paragraphs**, each written to sound like a real human applicant.
- Always appends:
  - GitHub profile link (`https://github.com/hamzaahmed213`)
  - Attached-CV sentence
  - Professional sign-off

The user can override the template or edit the output before saving.

---

### 4. Excel Ingest (`Recruiter Database`)

```python
df.columns = (
    df.columns.astype(str)
    .str.strip().str.lower().str.replace(" ", "_", regex=False)
)
```

Followed by an **alias resolution table**:

| Canonical | Accepted aliases |
|---|---|
| `recruiter_name` | `name`, `hr_name`, `contact_person` |
| `email` | `email_address`, `recruiter_email`, `contact_email` |
| `company` | `company_name`, `organization` |
| `job_title` | `role`, `position`, `job_role`, `title` |
| `job_description` | `description`, `job_details`, `requirements` |
| `job_link` | `link`, `application_link`, `url` |

Then:
- Email normalization (trim + lowercase).
- Regex validation.
- Dedup by email (`drop_duplicates(subset=["email"])`).
- Persist via UPSERT so re-importing the same file doesn't error.

---

### 5. Batch Sending Pipeline (`Draft Manager`)

The heart of the app. On click of **"🚀 Send Approved Batch"**:

```python
for position, (_, draft) in enumerate(selected_drafts.iterrows(), start=1):
    draft_id = int(draft["id"])

    # Re-fetch full draft (approval table only has summary columns)
    full_draft = drafts.loc[drafts["id"] == draft_id].iloc[0]
    recipient = clean_value(full_draft["recruiter_email"]).lower()

    # 1. Daily limit
    if successful >= remaining_today:
        status_message.warning(...); break

    # 2. Idempotency
    if has_sent_email(recipient):
        update_draft_status(draft_id, "Skipped - Already Sent")
        skipped += 1; continue

    # 3. Isolated send
    try:
        gmail_result = send_gmail_email(...)
    except Exception as send_error:
        log_email(recipient, "Failed", describe_send_error(send_error))
        update_draft_status(draft_id, "Failed")
        failed += 1; continue

    # 4. Post-send tracking (must not be confused with send failure)
    try:
        log_email(recipient, "Sent")
        update_draft_status(draft_id, "Sent")
    except Exception as tracking_error:
        st.warning("Gmail accepted… but tracking failed. Do not resend.")
```

**Key engineering decisions:**

1. **Approval table has summary columns only** — so the body is re-fetched from the source DataFrame by `id`. This keeps the UI table compact while preserving integrity.
2. **Send and track are in separate try/except blocks.** If Gmail accepts the email but SQLite fails to log it, the user is told *"do not resend — check your Sent folder"*, which prevents double-sends.
3. **`has_sent_email()` is checked against `email_logs` where `status = 'Sent'`** — the historical truth, not the draft's current status. This survives re-imports and multiple draft runs.
4. **`st.rerun()`** at the end refreshes the UI with fresh DB state.

---

### 6. Outreach Tracker SQL

Each row's state is derived by **correlated subqueries**, not stored flags:

```sql
CASE WHEN EXISTS (
    SELECT 1 FROM email_logs l
    WHERE LOWER(TRIM(l.recruiter_email)) = LOWER(TRIM(r.email))
      AND l.status = 'Sent'
) THEN 1 ELSE 0 END AS "Sent"
```

- `LOWER(TRIM(...))` makes the join case- and whitespace-insensitive.
- `MAX(l.sent_at)` + `ORDER BY l.sent_at DESC, l.id DESC LIMIT 1` gives the **latest attempt's status** regardless of ordering ties.

This design means the **log is the single source of truth**; if you ever need to correct something, you fix the log and the tracker reflects it.

---

## 🔐 Gmail Integration & Security Model

### Authentication (`connect_gmail`)

```python
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
```

- Uses **Google OAuth 2.0** with the **Desktop App flow** (`InstalledAppFlow.run_local_server(port=0)`).
- The app **never sees or stores your Gmail password**.
- `credentials.json` (client secret from Google Cloud Console) is required.
- `token.json` caches the authorized token; on future runs, the token is refreshed automatically if expired:

```python
if creds and creds.expired and creds.refresh_token:
    creds.refresh(Request())
```

### Least-Privilege Scope

`gmail.send` is **send-only** — the app **cannot read your inbox, drafts, labels, or contacts**. This is the narrowest possible Gmail scope that still allows sending.

### Attachment Handling (`send_gmail_email`)

```python
message = MIMEMultipart()
message["to"] = recipient
message["subject"] = str(subject)
message.attach(MIMEText(str(body), "plain", "utf-8"))

with open(CV_PATH, "rb") as cv_file:
    attachment = MIMEApplication(cv_file.read(), _subtype="pdf")
    attachment.add_header("Content-Disposition", "attachment",
                          filename=CV_ATTACHMENT_NAME)
    message.attach(attachment)

raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
service.users().messages().send(userId="me", body={"raw": raw_message}).execute()
```

- Standard **MIME multipart** message: plain-text body + PDF attachment.
- The attachment filename is **overridden** to a professional name (`Hamza_Ahmed_CV.pdf`) regardless of the uploaded file's original name.
- Recipient is re-validated with the regex right before send — so a corrupt row in the DB cannot be sent to a malformed address.

### Error Surfacing (`describe_send_error`)

```python
if isinstance(error, HttpError):
    details = error.content.decode("utf-8", errors="replace")
    return f"Gmail API error (HTTP {error.status_code}): {details}"
```

`HttpError` from `googleapiclient` hides the real error body. This helper decodes it so quota limits, invalid-recipient, or auth failures are all actionable.

---

## 🛡 Sending Safeguards (Reliability Engineering)

Every safeguard in the app is explicit and listed in the Settings page:

| Safeguard | Where it lives | What it prevents |
|---|---|---|
| **Human approval gate** | `st.data_editor` checkbox + button | Accidental sends |
| **Draft-body separation** | Draft Manager re-fetches body by `id` | Sending the wrong body / empty body |
| **Daily send limit (20)** | `DAILY_SEND_LIMIT` + `get_sent_today()` | Spam behaviour / Gmail throttling |
| **Per-recipient idempotency** | `has_sent_email()` before each send | Duplicate outreach |
| **Automatic CV attachment** | Every send attaches `my_cv.pdf` | Forgetting the résumé |
| **Recipient re-validation** | `re.fullmatch` in `send_gmail_email` | Sending to malformed addresses |
| **Send/log decoupling** | Two separate try/except blocks | False "failed" reports → double sends |
| **Failure logging** | `log_email(..., "Failed", error_message)` | Silent drop of delivery errors |
| **Fallback status** | `update_draft_status(draft_id, "Failed")` / `"Skipped - Already Sent"` | Ambiguous state |
| **Explicit "do not resend" warning** | `st.warning(...)` after tracking error | User confusion after partial success |

> This is the essence of **sending safety in automation**: the app does the *boring* part at scale, but the *irreversible* action (hitting Send) always waits for a human.

---

## 🎨 Design System & UI

The app ships a custom **dark visual language** (~300 lines of CSS injected at the top of `app.py`):

- **Palette tokens** via CSS custom properties (`--bg`, `--panel`, `--accent`, `--success`, `--warning`, `--danger`).
- **Inter / system UI font stack** with tuned letter-spacing.
- Custom styling for:
  - `stMetric`, `stDataFrame`, `stExpander`, `stAlert`
  - Text / number / select / multiselect inputs
  - `stFileUploader` (dashed drop zone)
  - Buttons (default and `kind="primary"`)
  - Progress bar
  - Sidebar radio (custom active/hover states via `:has(input:checked)` — pure CSS, no JS)
- **Brand lockup** ("Outreach Studio") with an "O" glyph and status pills.
- **Responsive breakpoint** at 800px for mobile.

This gives a polished, product-like feel while remaining a *single Python file* — no React, no build step, no NPM.

---

## ⚙️ Setup & Installation

### 1. Clone and install

```bash
git clone <your-repo>
cd <your-repo>
pip install streamlit pandas pypdf openpyxl \
            google-api-python-client google-auth \
            google-auth-oauthlib google-auth-httplib2
```

### 2. Google Cloud setup (one-time)

1. Go to **Google Cloud Console** → create/select a project.
2. Enable the **Gmail API**.
3. Create **OAuth client ID** → type **Desktop App**.
4. Download the JSON and rename it to **`credentials.json`** in the project root.
5. Add your Gmail address as a **test user** under OAuth consent screen (or publish the app).

### 3. Run

```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`.

### 4. First-run checklist

- [ ] **Upload CV** — the PDF becomes the email attachment.
- [ ] **Recruiter Database** — import your Excel.
- [ ] **Settings → Connect Gmail** — completes the OAuth flow and caches `token.json`.
- [ ] **Email Generator → Save Draft** — draft one email.
- [ ] **Draft Manager → Approve → Send** — your first controlled batch.

---

## 🚀 Usage Workflow

1. **Upload CV** → text is extracted and stored; PDF becomes the attachment.
2. **Import recruiter Excel** → cleaned, deduplicated, persisted.
3. **Review Job Matching** → sort by score to prioritise the best-fit roles.
4. **Generate emails** → pick a recruiter, auto-detect template, edit, and **Save Draft**.
5. **Draft Manager** → preview drafts → **tick the checkbox** → **Send Approved Batch**.
6. **Outreach Tracker** → watch send history grow; use it to plan follow-ups.

Every step **writes to SQLite**, so the workflow can be paused and resumed across days.

---

## 🌍 Real-World Contribution

This is not just a coding exercise — it delivers concrete value on several levels.

### For the job seeker
- **Time saved**: 50 personalized emails that would take 4–6 hours of manual writing and copy-pasting drop to **~30–45 minutes of review**.
- **Reputation protection**: the duplicate-send guard means you never spam a recruiter who already heard from you.
- **Consistency**: every email is role-aware and includes the CV — no "oops, forgot the attachment" moments.
- **Data ownership**: everything lives in `outreach.db` on your laptop. No third party sees your pipeline.
- **Auditable history**: the `email_logs` table is a permanent record of what was sent, when, and whether it failed.

### For the developer portfolio
- Demonstrates **clean separation of concerns** (UI vs. DB layer).
- Shows **defensive engineering**: send/log isolation, idempotency, error decoding.
- Demonstrates **production-grade OAuth** with least-privilege scopes and token refresh.
- Proves you can ship a **polished UI** inside a framework that doesn't give you one for free.

### For the broader ecosystem
- It's an **open pattern** for "human-in-the-loop automation" — a template that applies to cold sales outreach, grant applications, journalist pitches, and academic collaboration — anywhere mass personalized outreach is legitimate but must be reviewable.
- It models **local-first AI-adjacent tooling**: if you replace the keyword matcher with an LLM later, the *safety architecture stays the same*.

### For Gmail / deliverability hygiene
- The **20-email daily cap** aligns with typical Gmail sending limits and helps the user's account maintain healthy sender reputation, reducing the chance of being flagged as spam.
- Plain-text MIME bodies (rather than HTML blasts) are more likely to land in inboxes.

---

## ⚠️ Limitations & Future Work

### Current limitations
- **Matching is keyword-based**, not semantic. A résumé that says "ML" but not "machine learning" may be under-scored.
- **Single-user, single-CV.** One SQLite DB, one `uploads/my_cv.pdf`.
- **Plain-text body only** (no rich HTML email templates).
- **No follow-up scheduling** — the tracker records history but doesn't remind you.
- **No bounce/reply tracking** (would require broader Gmail scopes).
- **No retry queue** — failed sends must be re-drafted manually.

### Natural extensions
- 🔍 **Semantic matching** using sentence embeddings or an LLM to score fit and rewrite templates.
- 📅 **Scheduled follow-ups** with a reminder dashboard.
- 📈 **Analytics page**: open-rate proxies, per-company breakdowns, weekly throughput.
- 🧪 **Dry-run mode**: render the exact MIME message without sending (useful for QA).
- 🗂 **Multi-CV support** per role (e.g., a different résumé for data vs. frontend).
- 🔐 **Encrypted DB** at rest for users who want extra privacy.
- 🧵 **Per-template A/B testing** to see which opening paragraph gets more replies.
- 🤝 **Import from LinkedIn CSV exports** using the same alias table.

---

## 📌 Summary

**Outreach Studio** is a compact, full-stack demonstration of what a careful solo developer can build with Python's richest libraries:

- **Streamlit** for a real app-like UI with custom design.
- **pandas + openpyxl + pypdf** for the messy real-world data (Excel, PDFs).
- **SQLite** for durable, private state.
- **Google OAuth + Gmail API** for authenticated, attachment-aware sending.
- **Defensive engineering** (idempotency, isolated try/except, explicit status transitions) for safety where it matters most.

It turns a fragmented, error-prone outreach loop into one **reviewed, tracked, and private** workflow — and in doing so, it gives back to the user the most valuable resource of a job search: **time and confidence**.

---

*Built with care, one draft at a time.* ✉️