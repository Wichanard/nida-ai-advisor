"""
tests/test_report_generator.py
Unit tests for Executive Briefing Report Generator and Social Sentiment RAG integration.
"""
from __future__ import annotations

import pytest
from social_listening.report_generator import (
    generate_executive_html_report,
    generate_executive_csv_summary,
)
from app.services.agent_engine import NIDAAgentEngine, tool_query_social_sentiment
from app.services.document_rag import NIDADocumentRAG


def test_executive_html_report_generation():
    """Test generating a valid executive HTML report with SWOT and KPIs."""
    sentiment_counts = {"Positive": 1200, "Negative": 150, "Neutral": 250}
    intent_counts = {"interest_apply": 800, "inquire_tuition": 400, "ask_scholarship": 200}
    swot_data = {
        "strengths": ["คณาจารย์ระดับแนวหน้า", "เครือข่ายศิษย์เก่าแข็งแกร่ง"],
        "weaknesses": ["ค่าเทอมบางสาขาสูง", "การบ้านเข้มข้น"],
        "opportunities": ["ขยายหลักสูตร Online/Hybrid"],
        "threats": ["การแข่งขันจากสถาบันต่างประเทศ"],
    }
    anomalies = [
        {"severity": "MEDIUM", "topic": "NIDA TEAP", "insight": "ผู้สมัครต้องการเตรียมตัวล่วงหน้า"}
    ]

    html = generate_executive_html_report(
        total_comments=1600,
        sentiment_counts=sentiment_counts,
        intent_counts=intent_counts,
        swot_data=swot_data,
        anomalies=anomalies,
        user_role="Dean - GSBA",
    )

    assert "<!DOCTYPE html>" in html
    assert "NIDA Executive Intelligence Report" in html
    assert "Dean - GSBA" in html
    assert "คณาจารย์ระดับแนวหน้า" in html
    assert "1,600" in html or "1600" in html


def test_executive_csv_summary():
    """Test CSV generation contains key summary metrics."""
    sentiment_counts = {"Positive": 500, "Negative": 50}
    intent_counts = {"interest_apply": 300}
    swot_data = {"strengths": ["AACSB Standard"], "weaknesses": ["Traffic"]}

    csv_text = generate_executive_csv_summary(sentiment_counts, intent_counts, swot_data)
    assert "Sentiment Distribution" in csv_text
    assert "Positive" in csv_text
    assert "AACSB Standard" in csv_text


def test_social_sentiment_tool_and_rag():
    """Test social listening query tool returns structured data and positive percentage."""
    res = tool_query_social_sentiment("นิด้า MBA")
    assert "topic" in res
    assert "sample_mentions" in res
    assert "positive_percentage" in res
    assert isinstance(res["sample_mentions"], list)


def test_social_review_intent_query():
    """Test that when user asks for social reviews, AI responds with sentiment and alumni voice."""
    res = NIDAAgentEngine.chat(session_id="test-sentiment", user_message="คนใน Pantip พูดถึง ป.โท นิด้า ยังไงบ้าง ดีไหม")
    assert "reply" in res
    txt = res["reply"]
    assert any(w in txt for w in ["เสียงสะท้อน", "Pantip", "ความรู้สึก", "เชิงบวก", "ศิษย์เก่า", "อาจารย์"])
    assert "recommendation_cards" not in res or len(res.get("recommendation_cards", [])) == 0


def test_chromadb_chunks_expanded():
    """Verify ChromaDB has indexed comprehensive regulation chunks."""
    rag = NIDADocumentRAG.get_instance()
    assert rag.collection.count() >= 30
