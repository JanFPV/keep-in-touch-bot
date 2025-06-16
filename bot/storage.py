import sqlite3
import os
from datetime import datetime

DB_PATH = os.getenv("DATABASE_PATH", "data/kitbot.db")

def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                chat_id INTEGER PRIMARY KEY,
                avg_days INTEGER DEFAULT 30,
                is_active BOOLEAN DEFAULT 1,
                last_ping_at TEXT
            );
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS participants (
                chat_id INTEGER,
                user_id INTEGER,
                username TEXT,
                is_included BOOLEAN DEFAULT 1,
                PRIMARY KEY (chat_id, user_id)
            );
        """)
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_participants_chatid_included
            ON participants (chat_id, is_included);
        """)
        conn.commit()

# GROUP functions

def register_group(chat_id: int, default_avg: int = 30):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            INSERT OR IGNORE INTO groups (chat_id, avg_days, is_active)
            VALUES (?, ?, 1);
        """, (chat_id, default_avg))
        conn.commit()

def set_avg_days(chat_id: int, days: int):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("UPDATE groups SET avg_days = ? WHERE chat_id = ?", (days, chat_id))
        conn.commit()

def get_avg_days(chat_id: int) -> int:
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT avg_days FROM groups WHERE chat_id = ?", (chat_id,))
        row = c.fetchone()
        return row[0] if row else 30

def set_group_active(chat_id: int, active: bool):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("UPDATE groups SET is_active = ? WHERE chat_id = ?", (1 if active else 0, chat_id))
        conn.commit()

def is_group_active(chat_id: int) -> bool:
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT is_active FROM groups WHERE chat_id = ?", (chat_id,))
        row = c.fetchone()
        return row and row[0] == 1

def get_active_groups():
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT chat_id FROM groups WHERE is_active = 1")
        return [{"chat_id": row[0]} for row in c.fetchall()]

def update_last_ping(chat_id: int):
    now = datetime.utcnow().isoformat()
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("UPDATE groups SET last_ping_at = ? WHERE chat_id = ?", (now, chat_id))
        conn.commit()


# PARTICIPANT functions

def add_or_update_participant(chat_id: int, user_id: int, username: str, include: bool = True):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            INSERT INTO participants (chat_id, user_id, username, is_included)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(chat_id, user_id) DO UPDATE SET
            username = excluded.username,
            is_included = excluded.is_included;
        """, (chat_id, user_id, username, 1 if include else 0))
        conn.commit()

def set_participant_included(chat_id: int, user_id: int, included: bool):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            UPDATE participants
            SET is_included = ?
            WHERE chat_id = ? AND user_id = ?;
        """, (1 if included else 0, chat_id, user_id))
        conn.commit()

def get_random_included_participant(chat_id: int):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT user_id, username FROM participants
            WHERE chat_id = ? AND is_included = 1
            ORDER BY RANDOM()
            LIMIT 1;
        """, (chat_id,))
        result = c.fetchone()
        return {"id": result[0], "username": result[1]} if result else None

def get_included_participants(chat_id: int):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT user_id, username FROM participants
            WHERE chat_id = ? AND is_included = 1;
        """, (chat_id,))
        return [{"id": row[0], "username": row[1]} for row in c.fetchall()]

def get_excluded_participants(chat_id: int):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT user_id, username FROM participants
            WHERE chat_id = ? AND is_included = 0;
        """, (chat_id,))
        return [{"id": row[0], "username": row[1]} for row in c.fetchall()]
