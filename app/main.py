"""
app/main.py
NIDA Enterprise AI Advisor & Social Intelligence REST API Platform.
Built with FastAPI, Vector Search, Multi-Turn Agentic Reasoning, ABSA, and Persistence.
"""
from __future__ import annotations

import os
import uuid
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.models.database import (
    init_db,
    save_chat_message,
    get_chat_history,
    record_feedback,
    get_system_stats,
)
from app.services.agent_engine import NIDAAgentEngine
from app.services.vector_store import NIDAVectorStore
from social_listening.advanced_analytics import (
    compute_absa_metrics,
    compute_anomaly_radar,
    generate_executive_swot_summary,
)
from social_listening.storage import read_jsonl

# Initialize database on startup
init_db()

app = FastAPI(
    title="NIDA Enterprise AI Agent & Social Intelligence API",
    description="Production-grade REST API powering multi-turn conversational AI advising, hybrid vector search, aspect-based sentiment analysis (ABSA), and crisis radar for NIDA Graduate University.",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for frontend web integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Pydantic Request/Response Models ───

class ChatRequest(BaseModel):
    session_id: Optional[str] = Field(None, example="sess-12345", description="Client session ID for multi-turn conversational memory")
    message: str = Field(..., example="สนใจเรียนต่อ MBA นิด้า ภาคค่ำหรือเสาร์-อาทิตย์ ค่าเทอมประมาณเท่าไหร่ครับ?")
    degree_filter: Optional[str] = Field("ทั้งหมด", example="ป.โท")
    faculty_filter: Optional[str] = Field("ทั้งหมด", example="บริหารธุรกิจ")
    study_mode_filter: Optional[str] = Field("ทั้งหมด", example="เสาร์-อาทิตย์")


class RecommendRequest(BaseModel):
    prompt: str = Field(..., example="สนใจเรียนต่อ MBA วันเสาร์-อาทิตย์ ค่าเทอมไม่เกิน 1 แสนบาท")
    degree_filter: Optional[str] = Field("ทั้งหมด", example="ป.โท")
    faculty_filter: Optional[str] = Field("ทั้งหมด", example="บริหารธุรกิจ")
    study_mode_filter: Optional[str] = Field("ทั้งหมด", example="เสาร์-อาทิตย์")
    top_k: int = Field(4, ge=1, le=10)


class CompareRequest(BaseModel):
    programs: List[str] = Field(..., min_items=2, max_items=4, example=["MBA", "Data Science"])


class FeedbackRequest(BaseModel):
    session_id: str = Field(..., example="sess-12345")
    rating: int = Field(..., ge=-1, le=1, description="1 for positive thumbs up, -1 for negative thumbs down")
    feedback_text: Optional[str] = Field("", example="คำตอบละเอียดและตรงประเด็นมาก")
    message_id: Optional[int] = Field(None)


def _load_all_comments() -> List[Dict[str, Any]]:
    """Helper to load all collected comments from data directories."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dirs = [
        os.path.join(base_dir, "social_listening", "data"),
        os.path.join(base_dir, "data"),
    ]
    comments = []
    for d in data_dirs:
        if os.path.exists(d):
            for fname in os.listdir(d):
                if fname.endswith(".jsonl"):
                    fpath = os.path.join(d, fname)
                    try:
                        comments.extend(read_jsonl(fpath))
                    except Exception:
                        pass
    return comments


# ─── API Endpoints ───

@app.get("/")
def health_check() -> Dict[str, Any]:
    stats = get_system_stats()
    return {
        "status": "online",
        "service": "NIDA Enterprise AI Advisor & Social Intelligence Engine",
        "version": "2.0.0",
        "system_stats": stats,
        "docs_url": "/docs",
    }


@app.post("/api/v1/chat")
def api_chat(req: ChatRequest) -> Dict[str, Any]:
    """Execute multi-turn autonomous conversational AI turn with agent tools and memory."""
    session_id = req.session_id or f"sess-{uuid.uuid4().hex[:8]}"
    result = NIDAAgentEngine.execute_chat(
        session_id=session_id,
        user_message=req.message,
        degree_filter=req.degree_filter or "ทั้งหมด",
        faculty_filter=req.faculty_filter or "ทั้งหมด",
        study_mode_filter=req.study_mode_filter or "ทั้งหมด",
    )
    return result


@app.get("/api/v1/chat/history/{session_id}")
def api_get_chat_history(session_id: str, limit: int = 20) -> Dict[str, Any]:
    """Retrieve multi-turn chat history for a session."""
    history = get_chat_history(session_id=session_id, limit=limit)
    return {
        "session_id": session_id,
        "message_count": len(history),
        "history": history,
    }


@app.post("/api/v1/recommend")
def api_recommend_courses(req: RecommendRequest) -> Dict[str, Any]:
    """Search and recommend NIDA graduate programs using hybrid vector search."""
    vs = NIDAVectorStore.get_instance()
    results = vs.search(
        query=req.prompt,
        degree_filter=req.degree_filter or "ทั้งหมด",
        faculty_filter=req.faculty_filter or "ทั้งหมด",
        study_mode_filter=req.study_mode_filter or "ทั้งหมด",
        top_k=req.top_k,
    )
    return {
        "query": req.prompt,
        "total_results": len(results),
        "programs": results,
    }


@app.post("/api/v1/compare")
def api_compare_programs(req: CompareRequest) -> Dict[str, Any]:
    """Side-by-side comparison of 2-4 NIDA programs."""
    vs = NIDAVectorStore.get_instance()
    records = vs.compare_programs(req.programs)
    return {
        "requested_count": len(req.programs),
        "matched_count": len(records),
        "comparison": records,
    }


@app.get("/api/v1/analytics/absa")
def api_absa_metrics() -> Dict[str, Any]:
    """Aspect-Based Sentiment Analysis (ABSA) metrics across 5 higher-ed dimensions."""
    comments = _load_all_comments()
    absa = compute_absa_metrics(comments)
    return {
        "total_comments_analyzed": len(comments),
        "aspect_sentiment_breakdown": absa,
    }


@app.get("/api/v1/analytics/anomaly-radar")
def api_anomaly_radar() -> Dict[str, Any]:
    """Institutional crisis radar, sentiment volatility, and anomaly detection."""
    comments = _load_all_comments()
    radar = compute_anomaly_radar(comments)
    return radar


@app.get("/api/v1/analytics/executive-summary")
def api_executive_summary() -> Dict[str, Any]:
    """AI Executive Intelligence Brief (SWOT & Strategic Recommendations) for NIDA Leadership."""
    comments = _load_all_comments()
    swot = generate_executive_swot_summary(comments)
    return {
        "total_sources_analyzed": len(comments),
        "executive_swot": swot,
    }


@app.post("/api/v1/feedback")
def api_submit_feedback(req: FeedbackRequest) -> Dict[str, Any]:
    """Submit user satisfaction rating for RLHF and quality evaluation."""
    success = record_feedback(
        session_id=req.session_id,
        rating=req.rating,
        feedback_text=req.feedback_text or "",
        message_id=req.message_id,
    )
    return {"status": "success" if success else "failed"}


@app.get("/api/v1/stats")
def api_system_stats() -> Dict[str, Any]:
    """Retrieve platform usage, chat session counts, and user satisfaction rate."""
    return get_system_stats()