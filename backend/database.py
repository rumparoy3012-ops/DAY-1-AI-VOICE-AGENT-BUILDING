import sqlite3
from datetime import datetime

DB_NAME = "roshni_memory.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            name TEXT,
            language_preference TEXT,
            schemes_checked TEXT,
            eligibility_status TEXT,
            last_interaction TEXT
        )
    """)
    conn.commit()
    conn.close()

def get_user(user_id: str):
    init_db()
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    # Normalize phone numbers / IDs (strip spaces and special chars)
    clean_id = str(user_id).strip().replace("-", "").replace(" ", "")
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (clean_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def save_user_profile(user_id: str, name: str, language_preference: str, schemes_checked: str, eligibility_status: str):
    init_db()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    timestamp = datetime.now().isoformat()
    clean_id = str(user_id).strip().replace("-", "").replace(" ", "")
    cursor.execute("""
        INSERT INTO users (user_id, name, language_preference, schemes_checked, eligibility_status, last_interaction)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            name = excluded.name,
            language_preference = excluded.language_preference,
            schemes_checked = excluded.schemes_checked,
            eligibility_status = excluded.eligibility_status,
            last_interaction = excluded.last_interaction
    """, (clean_id, name, language_preference, schemes_checked, eligibility_status, timestamp))
    conn.commit()
    conn.close()