"""
app/models/database.py
Enterprise Persistence Layer for NIDA AI Advisor & Social Listening Platform.
Supports multi-turn chat sessions, user feedback (RLHF), and structured social mentions.
Now upgraded with SQLAlchemy to support PostgreSQL (Production) and SQLite (Local).
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

BASE_DIR = Path(__file__).resolve().parents[2]
# Default to SQLite if DATABASE_URL is not provided (use /tmp for Render compatibility)
DEFAULT_DATABASE_URL = f"sqlite:////tmp/nida_enterprise.db"
DATABASE_URL = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)

engine: Optional[Engine] = None

def get_engine() -> Engine:
    global engine
    if engine is None:
        if DATABASE_URL.startswith("sqlite"):
            # SQLite specific configuration
            if ":memory:" not in DATABASE_URL and "/tmp" not in DATABASE_URL:
                try:
                    (BASE_DIR / "data").mkdir(parents=True, exist_ok=True)
                except Exception:
                    pass
            engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
        else:
            # PostgreSQL (or other) configuration
            engine = create_engine(DATABASE_URL, pool_size=20, max_overflow=0)
    return engine

def init_db():
    try:
        eng = get_engine()
        with eng.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                session_id VARCHAR(255) PRIMARY KEY,
                inferred_age VARCHAR(255),
                work_experience TEXT,
                interests TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS chat_sessions (
                session_id VARCHAR(255) PRIMARY KEY,
                user_id VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

        id_type = "INTEGER PRIMARY KEY AUTOINCREMENT" if eng.name == "sqlite" else "SERIAL PRIMARY KEY"
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id {id_type},
                session_id VARCHAR(255),
                sender VARCHAR(50),
                message TEXT,
                recommended_programs TEXT,
                tools_used TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS user_feedback (
                id {id_type},
                session_id VARCHAR(255),
                message_id INTEGER,
                rating INTEGER,
                feedback_text TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS social_mentions (
                id VARCHAR(255) PRIMARY KEY,
                platform VARCHAR(100),
                title TEXT,
                text TEXT,
                author VARCHAR(255),
                published_at VARCHAR(100),
                url TEXT,
                sentiment VARCHAR(50),
                intent VARCHAR(100),
                aspect VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
    except Exception as e:
        print(f"CRITICAL ERROR initializing database: {e}")
        print("Fallback to /tmp sqlite to prevent crash.")
        global engine, DATABASE_URL
        DATABASE_URL = "sqlite:////tmp/nida_enterprise_fallback.db"
        engine = None
        try:
            eng = get_engine()
            with eng.begin() as conn:
                conn.execute(text("CREATE TABLE IF NOT EXISTS chat_sessions (session_id VARCHAR(255) PRIMARY KEY, user_id VARCHAR(255), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"))
                # Try to alter if it already exists from a previous bad init
                try:
                    conn.execute(text("ALTER TABLE chat_sessions ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))
                except Exception:
                    pass
                conn.execute(text("CREATE TABLE IF NOT EXISTS chat_messages (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id VARCHAR(255), sender VARCHAR(50), message TEXT, recommended_programs TEXT, tools_used TEXT, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"))
                conn.execute(text("CREATE TABLE IF NOT EXISTS user_profiles (session_id VARCHAR(255) PRIMARY KEY, inferred_age VARCHAR(255), work_experience TEXT, interests TEXT, last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"))
        except Exception:
            pass

def save_chat_message(
    session_id: str,
    sender: str,
    message: str,
    user_id: str = "guest",
    recommended_programs: Optional[List[Dict[str, Any]]] = None,
    tools_used: Optional[List[str]] = None,
) -> int:
    eng = get_engine()
    with eng.begin() as conn:
        res = conn.execute(text("SELECT session_id FROM chat_sessions WHERE session_id = :s"), {"s": session_id}).fetchone()
        if res:
            try:
                conn.execute(text("UPDATE chat_sessions SET updated_at = CURRENT_TIMESTAMP WHERE session_id = :s"), {"s": session_id})
            except Exception:
                pass
        else:
            conn.execute(text("INSERT INTO chat_sessions (session_id, user_id) VALUES (:s, :u)"), {"s": session_id, "u": user_id})

        result = conn.execute(
            text("""
            INSERT INTO chat_messages (session_id, sender, message, recommended_programs, tools_used)
            VALUES (:session_id, :sender, :message, :recommended_programs, :tools_used)
            """),
            {
                "session_id": session_id,
                "sender": sender,
                "message": message,
                "recommended_programs": json.dumps(recommended_programs or [], ensure_ascii=False),
                "tools_used": json.dumps(tools_used or [], ensure_ascii=False)
            }
        )
        return result.lastrowid or 0

def get_chat_history(session_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    eng = get_engine()
    with eng.begin() as conn:
        rows = conn.execute(
            text("""
            SELECT id, session_id, sender, message, recommended_programs, tools_used, timestamp
            FROM chat_messages
            WHERE session_id = :session_id
            ORDER BY timestamp ASC, id ASC
            LIMIT :limit
            """),
            {"session_id": session_id, "limit": limit}
        ).fetchall()
        
        history = []
        for r in rows:
            history.append({
                "id": r[0],
                "session_id": r[1],
                "sender": r[2],
                "message": r[3],
                "recommended_programs": json.loads(r[4] or "[]"),
                "tools_used": json.loads(r[5] or "[]"),
                "timestamp": str(r[6]),
            })
        return history

def get_all_chat_sessions(user_id: str = "guest", search_query: Optional[str] = None) -> List[Dict[str, Any]]:
    eng = get_engine()
    with eng.begin() as conn:
        query = """
            SELECT s.session_id, s.updated_at, 
                   (SELECT message FROM chat_messages m WHERE m.session_id = s.session_id AND m.sender = 'user' ORDER BY timestamp ASC LIMIT 1) as title
            FROM chat_sessions s
            WHERE s.user_id = :user_id
        """
        params = {"user_id": user_id}
        
        if search_query:
            query += " AND (SELECT message FROM chat_messages m WHERE m.session_id = s.session_id AND m.sender = 'user' ORDER BY timestamp ASC LIMIT 1) LIKE :sq"
            params["sq"] = f"%{search_query}%"
            
        query += " ORDER BY s.updated_at DESC"
        
        rows = conn.execute(text(query), params).fetchall()
        
        sessions = []
        for r in rows:
            sessions.append({
                "session_id": r[0],
                "updated_at": str(r[1]),
                "title": r[2] or "New Chat"
            })
        return sessions

def record_feedback(session_id: str, rating: int, feedback_text: str = "", message_id: Optional[int] = None) -> bool:
    eng = get_engine()
    with eng.begin() as conn:
        conn.execute(
            text("""
            INSERT INTO user_feedback (session_id, message_id, rating, feedback_text)
            VALUES (:session_id, :message_id, :rating, :feedback_text)
            """),
            {"session_id": session_id, "message_id": message_id, "rating": rating, "feedback_text": feedback_text}
        )
        return True

def ingest_social_mentions(items: List[Dict[str, Any]], platform_override: Optional[str] = None) -> int:
    eng = get_engine()
    inserted = 0
    with eng.begin() as conn:
        for item in items:
            t = item.get("text") or item.get("title")
            if not t:
                continue
            item_id = str(item.get("id") or item.get("comment_id") or uuid.uuid5(uuid.NAMESPACE_DNS, str(t)))
            platform = platform_override or item.get("platform") or "online"
            
            exists = conn.execute(text("SELECT id FROM social_mentions WHERE id = :id"), {"id": item_id}).fetchone()
            if exists:
                conn.execute(
                    text("""
                    UPDATE social_mentions 
                    SET sentiment = :sentiment, intent = :intent 
                    WHERE id = :id
                    """),
                    {
                        "id": item_id,
                        "sentiment": item.get("sentiment", "Neutral"),
                        "intent": item.get("intent", "General Education")
                    }
                )
            else:
                conn.execute(
                    text("""
                    INSERT INTO social_mentions (id, platform, title, text, author, published_at, url, sentiment, intent, aspect)
                    VALUES (:id, :platform, :title, :text, :author, :published_at, :url, :sentiment, :intent, :aspect)
                    """),
                    {
                        "id": item_id,
                        "platform": platform,
                        "title": item.get("title", ""),
                        "text": t,
                        "author": item.get("author", "Unknown"),
                        "published_at": str(item.get("published_at", "")),
                        "url": item.get("url", ""),
                        "sentiment": item.get("sentiment", "Neutral"),
                        "intent": item.get("intent", "General Education"),
                        "aspect": item.get("aspect", "academics_faculty")
                    }
                )
            inserted += 1
    return inserted

def save_user_profile(session_id: str, inferred_age: str = None, work_experience: str = None, interests: str = None) -> None:
    eng = get_engine()
    with eng.begin() as conn:
        row = conn.execute(text("SELECT inferred_age, work_experience, interests FROM user_profiles WHERE session_id = :session_id"), {"session_id": session_id}).fetchone()
        
        if row:
            new_age = inferred_age if inferred_age else row[0]
            new_exp = work_experience if work_experience else row[1]
            new_int = interests if interests else row[2]
            conn.execute(text("""
                UPDATE user_profiles 
                SET inferred_age = :age, work_experience = :exp, interests = :int, last_updated = CURRENT_TIMESTAMP
                WHERE session_id = :session_id
            """), {"age": new_age, "exp": new_exp, "int": new_int, "session_id": session_id})
        else:
            conn.execute(text("""
                INSERT INTO user_profiles (session_id, inferred_age, work_experience, interests)
                VALUES (:session_id, :age, :exp, :int)
            """), {"session_id": session_id, "age": inferred_age, "exp": work_experience, "int": interests})

def get_user_profile(session_id: str) -> Optional[Dict[str, Any]]:
    eng = get_engine()
    with eng.begin() as conn:
        row = conn.execute(text("SELECT * FROM user_profiles WHERE session_id = :session_id"), {"session_id": session_id}).fetchone()
        if row:
            return {
                "session_id": row[0],
                "inferred_age": row[1],
                "work_experience": row[2],
                "interests": row[3],
                "last_updated": row[4]
            }
        return None
def get_system_stats() -> Dict[str, Any]:
    eng = get_engine()
    with eng.begin() as conn:
        total_sessions = conn.execute(text("SELECT COUNT(*) FROM chat_sessions")).scalar()
        total_messages = conn.execute(text("SELECT COUNT(*) FROM chat_messages")).scalar()
        pos_feedback = conn.execute(text("SELECT COUNT(*) FROM user_feedback WHERE rating = 1")).scalar()
        total_feedback = conn.execute(text("SELECT COUNT(*) FROM user_feedback")).scalar()
        total_mentions = conn.execute(text("SELECT COUNT(*) FROM social_mentions")).scalar()

        satisfaction_rate = (pos_feedback / total_feedback * 100.0) if total_feedback > 0 else 100.0

        return {
            "total_sessions": total_sessions,
            "total_messages": total_messages,
            "total_feedback": total_feedback,
            "total_mentions_in_db": total_mentions,
            "satisfaction_rate": round(satisfaction_rate, 1),
        }
