import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent_memory.db"))

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Existing user profile table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            name TEXT,
            language_preference TEXT,
            schemes_checked TEXT,
            eligibility_status TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Day 8: Call Analytics Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS call_analytics (
            call_id TEXT PRIMARY KEY,
            timestamp TEXT,
            outcome TEXT, -- 'SUCCESS' or 'FAILED'
            reason TEXT,  -- e.g., 'Completed Scheme Rate Lookup', 'Incomplete Inquiry'
            duration_seconds INTEGER DEFAULT 0
        )
    """)
    
    conn.commit()
    conn.close()

# Initialize DB on module import
init_db()

def save_user_profile(user_id, name, language_preference, schemes_checked, eligibility_status):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO users (user_id, name, language_preference, schemes_checked, eligibility_status, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, name, language_preference, schemes_checked, eligibility_status, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name, language_preference, schemes_checked, eligibility_status FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "name": row[0],
            "language_preference": row[1],
            "schemes_checked": row[2],
            "eligibility_status": row[3]
        }
    return None

def record_call_outcome(call_id, outcome, reason, duration_seconds=None):
    """Save call outcome to SQLite database for analytics tracking."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    now = datetime.now()
    timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")
    
    # Retrieve previous timestamp if it exists to maintain the original call start time
    cursor.execute("SELECT timestamp FROM call_analytics WHERE call_id = ?", (call_id,))
    row = cursor.fetchone()
    
    if row:
        # Preserve original start timestamp
        timestamp = row[0]
        if duration_seconds is None:
            try:
                start_dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                duration_seconds = int((now - start_dt).total_seconds())
            except Exception:
                duration_seconds = 0
    else:
        timestamp = timestamp_str
        if duration_seconds is None:
            duration_seconds = 0
            
    cursor.execute("""
        INSERT OR REPLACE INTO call_analytics (call_id, timestamp, outcome, reason, duration_seconds)
        VALUES (?, ?, ?, ?, ?)
    """, (call_id, timestamp, outcome, reason, duration_seconds))
    conn.commit()
    conn.close()

def get_analytics_summary():
    """Fetch call statistics: Total, Successful, Failed, and Success Rate."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM call_analytics")
    total_calls = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM call_analytics WHERE outcome = 'SUCCESS'")
    successful_calls = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM call_analytics WHERE outcome = 'FAILED'")
    failed_calls = cursor.fetchone()[0]
    
    cursor.execute("SELECT call_id, timestamp, outcome, reason FROM call_analytics ORDER BY timestamp DESC LIMIT 5")
    recent_calls = [
        {"call_id": row[0], "timestamp": row[1], "outcome": row[2], "reason": row[3]}
        for row in cursor.fetchall()
    ]
    
    conn.close()
    
    success_rate = round((successful_calls / total_calls * 100), 1) if total_calls > 0 else 0.0
    
    return {
        "total_calls": total_calls,
        "successful_calls": successful_calls,
        "failed_calls": failed_calls,
        "success_rate": success_rate,
        "recent_calls": recent_calls
    }