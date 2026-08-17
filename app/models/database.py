"""
app/models/database.py
Enterprise Persistence Layer for NIDA AI Advisor & Social Listening Platform.
Supports multi-turn chat sessions, user feedback (RLHF), and structured social mentions.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "data" / "nida_enterprise.db"


def get_db_connection() -> sqlite3.Connection:
    """Create and return a thread-safe connection to the SQLite database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=15.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize enterprise database schema with required tables and indexes."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Chat Sessions Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT DEFAULT 'guest',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                context_metadata TEXT DEFAULT '{}'
            )
        """)

        # 2. Chat Messages Table (Multi-turn Memory)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                sender TEXT NOT NULL CHECK(sender IN ('user', 'assistant', 'system')),
                message TEXT NOT NULL,
                recommended_programs TEXT DEFAULT '[]',
                tools_used TEXT DEFAULT '[]',
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id)
            )
        """)

        # 3. User Feedback & RLHF Evaluation
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                message_id INTEGER,
                rating INTEGER CHECK(rating IN (1, -1)),
                feedback_text TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 4. Social Mentions Warehouse Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS social_mentions (
                id TEXT PRIMARY KEY,
                platform TEXT NOT NULL,
                title TEXT,
                text TEXT NOT NULL,
                author TEXT,
                published_at TEXT,
                url TEXT,
                sentiment TEXT,
                intent TEXT,
                aspect TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Indexes for rapid retrieval
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_session ON chat_messages(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_social_platform ON social_mentions(platform)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_social_sentiment ON social_mentions(sentiment)")
        conn.commit()


# ─── Chat Session CRUD ───

def save_chat_message(
    session_id: str,
    sender: str,
    message: str,
    recommended_programs: Optional[List[Dict[str, Any]]] = None,
    tools_used: Optional[List[str]] = None,
) -> int:
    """Save a chat message in the session history."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO chat_sessions (session_id, updated_at)
            VALUES (?, CURRENT_TIMESTAMP)
            ON CONFLICT(session_id) DO UPDATE SET updated_at = CURRENT_TIMESTAMP
            """,
            (session_id,),
        )
        cursor.execute(
            """
            INSERT INTO chat_messages (session_id, sender, message, recommended_programs, tools_used)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                session_id,
                sender,
                message,
                json.dumps(recommended_programs or [], ensure_ascii=False),
                json.dumps(tools_used or [], ensure_ascii=False),
            ),
        )
        msg_id = cursor.lastrowid
        conn.commit()
        return msg_id or 0


def get_chat_history(session_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Retrieve chronologically ordered chat messages for a session."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, session_id, sender, message, recommended_programs, tools_used, timestamp
            FROM chat_messages
            WHERE session_id = ?
            ORDER BY timestamp ASC, id ASC
            LIMIT ?
            """,
            (session_id, limit),
        )
        rows = cursor.fetchall()
        history = []
        for r in rows:
            history.append({
                "id": r["id"],
                "session_id": r["session_id"],
                "sender": r["sender"],
                "message": r["message"],
                "recommended_programs": json.loads(r["recommended_programs"] or "[]"),
                "tools_used": json.loads(r["tools_used"] or "[]"),
                "timestamp": r["timestamp"],
            })
        return history


def get_all_chat_sessions(user_id: str = "guest", search_query: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve all chat sessions for a user, optionally filtered by search query."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        query = """
            SELECT s.session_id, s.updated_at, 
                   (SELECT message FROM chat_messages m WHERE m.session_id = s.session_id AND m.sender = 'user' ORDER BY timestamp ASC LIMIT 1) as title
            FROM chat_sessions s
            WHERE s.user_id = ?
        """
        params = [user_id]
        
        if search_query:
            query += " AND (SELECT message FROM chat_messages m WHERE m.session_id = s.session_id AND m.sender = 'user' ORDER BY timestamp ASC LIMIT 1) LIKE ?"
            params.append(f"%{search_query}%")
            
        query += " ORDER BY s.updated_at DESC"
        
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        
        sessions = []
        for r in rows:
            sessions.append({
                "session_id": r["session_id"],
                "updated_at": r["updated_at"],
                "title": r["title"] or "New Chat"
            })
        return sessions


def record_feedback(session_id: str, rating: int, feedback_text: str = "", message_id: Optional[int] = None) -> bool:
    """Record user satisfaction rating (1 = thumbs up, -1 = thumbs down)."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO user_feedback (session_id, message_id, rating, feedback_text)
            VALUES (?, ?, ?, ?)
            """,
            (session_id, message_id, rating, feedback_text),
        )
        conn.commit()
        return True


def ingest_social_mentions(items: List[Dict[str, Any]], platform_override: Optional[str] = None) -> int:
    """Ingest and deduplicate social comments into the database warehouse."""
    init_db()
    inserted = 0
    with get_db_connection() as conn:
        cursor = conn.cursor()
        for item in items:
            text = item.get("text") or item.get("title")
            if not text:
                continue
            item_id = str(item.get("id") or item.get("comment_id") or uuid.uuid5(uuid.NAMESPACE_DNS, str(text)))
            platform = platform_override or item.get("platform") or "online"
            cursor.execute(
                """
                INSERT INTO social_mentions (id, platform, title, text, author, published_at, url, sentiment, intent, aspect)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET sentiment = excluded.sentiment, intent = excluded.intent
                """,
                (
                    item_id,
                    platform,
                    item.get("title", ""),
                    text,
                    item.get("author", "ผู้ใช้ทั่วไป"),
                    item.get("published_at", ""),
                    item.get("url", ""),
                    item.get("sentiment", "Neutral"),
                    item.get("intent", "General Education"),
                    item.get("aspect", "academics_faculty"),
                ),
            )
            inserted += 1
        conn.commit()
    return inserted


def get_system_stats() -> Dict[str, Any]:
    """Retrieve platform usage statistics from SQLite."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total_sessions FROM chat_sessions")
        total_sessions = cursor.fetchone()["total_sessions"]

        cursor.execute("SELECT COUNT(*) as total_messages FROM chat_messages")
        total_messages = cursor.fetchone()["total_messages"]

        cursor.execute("SELECT COUNT(*) as total_positive_feedback FROM user_feedback WHERE rating = 1")
        pos_feedback = cursor.fetchone()["total_positive_feedback"]

        cursor.execute("SELECT COUNT(*) as total_feedback FROM user_feedback")
        total_feedback = cursor.fetchone()["total_feedback"]

        cursor.execute("SELECT COUNT(*) as total_mentions FROM social_mentions")
        total_mentions = cursor.fetchone()["total_mentions"]

        satisfaction_rate = (pos_feedback / total_feedback * 100.0) if total_feedback > 0 else 100.0

        return {
            "total_sessions": total_sessions,
            "total_messages": total_messages,
            "total_feedback": total_feedback,
            "total_mentions_in_db": total_mentions,
            "satisfaction_rate": round(satisfaction_rate, 1),
        }
