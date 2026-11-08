import sqlite3
import pandas as pd
import os

DB_NAME = "outreach.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


def init_db():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS app_data (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recruiters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recruiter_name TEXT,
            email TEXT UNIQUE,
            company TEXT,
            job_title TEXT,
            job_description TEXT,
            job_link TEXT,
            status TEXT DEFAULT 'New'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS email_drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recruiter_email TEXT,
            subject TEXT,
            body TEXT,
            status TEXT DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS email_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recruiter_email TEXT,
            status TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            error_message TEXT
        )
    """)

    conn.commit()
    conn.close()


def save_cv(cv_text):

    conn = get_connection()

    conn.execute("""
        INSERT OR REPLACE INTO app_data (key, value)
        VALUES ('cv_text', ?)
    """, (cv_text,))

    conn.commit()
    conn.close()


def load_cv():

    conn = get_connection()

    result = conn.execute("""
        SELECT value FROM app_data
        WHERE key = 'cv_text'
    """).fetchone()

    conn.close()

    return result[0] if result else ""


def save_recruiters(df):

    conn = get_connection()

    columns = [
        "recruiter_name",
        "email",
        "company",
        "job_title",
        "job_description",
        "job_link"
    ]

    for column in columns:
        if column not in df.columns:
            df[column] = ""

    for _, row in df.iterrows():

        values = []

        for column in columns:
            value = row[column]

            if pd.isna(value):
                value = ""

            values.append(str(value))

        conn.execute("""
            INSERT INTO recruiters (
                recruiter_name, email, company,
                job_title, job_description, job_link
            )
            VALUES (?, ?, ?, ?, ?, ?)

            ON CONFLICT(email) DO UPDATE SET
                recruiter_name = excluded.recruiter_name,
                company = excluded.company,
                job_title = excluded.job_title,
                job_description = excluded.job_description,
                job_link = excluded.job_link
        """, values)

    conn.commit()
    conn.close()


def load_recruiters():

    conn = get_connection()

    df = pd.read_sql_query(
        "SELECT * FROM recruiters",
        conn
    )

    conn.close()

    return df

def get_email_counts():

    conn = get_connection()

    sent = conn.execute("""
        SELECT COUNT(*) FROM email_logs
        WHERE status = 'Sent'
    """).fetchone()[0]

    pending = conn.execute("""
        SELECT COUNT(*) FROM email_drafts
        WHERE status = 'Pending'
    """).fetchone()[0]

    conn.close()

    return sent, pending

def save_draft(recruiter_email, subject, body):

    conn = get_connection()

    conn.execute("""
        INSERT INTO email_drafts (
            recruiter_email, subject, body, status
        )
        VALUES (?, ?, ?, 'Pending')
    """, (recruiter_email, subject, body))

    conn.commit()
    conn.close()


def update_draft_status(draft_id, status):
    conn = get_connection()
    conn.execute(
        "UPDATE email_drafts SET status = ? WHERE id = ?",
        (status, draft_id)
    )
    conn.commit()
    conn.close()


def log_email(email, status, error=None):
    conn = get_connection()
    conn.execute("""
        INSERT INTO email_logs
        (recruiter_email, status, error_message)
        VALUES (?, ?, ?)
    """, (email, status, error))
    conn.commit()
    conn.close()


def get_sent_today():
    conn = get_connection()
    count = conn.execute("""
        SELECT COUNT(*) FROM email_logs
        WHERE status = 'Sent'
        AND date(sent_at) = date('now', 'localtime')
    """).fetchone()[0]
    conn.close()
    return count

def get_outreach_tracker():

    conn = get_connection()

    df = pd.read_sql_query("""
        SELECT
            r.recruiter_name AS "Recruiter",
            r.company AS "Company",
            r.job_title AS "Job Role",
            r.email AS "Email",

            CASE WHEN EXISTS (
                SELECT 1 FROM email_logs l
                WHERE LOWER(TRIM(l.recruiter_email)) =
                      LOWER(TRIM(r.email))
                AND l.status = 'Sent'
            ) THEN 1 ELSE 0 END AS "Sent",

            (
                SELECT MAX(l.sent_at)
                FROM email_logs l
                WHERE LOWER(TRIM(l.recruiter_email)) =
                      LOWER(TRIM(r.email))
                AND l.status = 'Sent'
            ) AS "Sent Date",

            (
                SELECT l.status
                FROM email_logs l
                WHERE LOWER(TRIM(l.recruiter_email)) =
                      LOWER(TRIM(r.email))
                ORDER BY l.sent_at DESC, l.id DESC
                LIMIT 1
            ) AS "Latest Status",

            (
                SELECT l.sent_at
                FROM email_logs l
                WHERE LOWER(TRIM(l.recruiter_email)) =
                      LOWER(TRIM(r.email))
                ORDER BY l.sent_at DESC, l.id DESC
                LIMIT 1
            ) AS "Last Attempt"

        FROM recruiters r
        ORDER BY r.company
    """, conn)

    conn.close()

    df["Sent"] = df["Sent"].astype(bool)

    return df
def load_drafts():

    conn = get_connection()

    df = pd.read_sql_query("""
        SELECT * FROM email_drafts
        ORDER BY created_at DESC
    """, conn)

    conn.close()

    return df

def has_sent_email(email):

    conn = get_connection()

    result = conn.execute("""
        SELECT COUNT(*) FROM email_logs
        WHERE LOWER(TRIM(recruiter_email)) = LOWER(TRIM(?))
        AND status = 'Sent'
    """, (email,)).fetchone()[0]

    conn.close()

    return result > 0