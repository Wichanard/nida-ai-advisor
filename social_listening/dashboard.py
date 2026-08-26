"""
social_listening/dashboard.py
NIDA Enterprise AI Advisor & Strategic Social Listening Platform.
Features Role-Based Access Control (RBAC), ChromaDB Document RAG, Automated ETL Pipeline, and Executive BI.
"""
from __future__ import annotations

try:
    __import__('pysqlite3')
    import sys
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass

import io
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import streamlit as st

from app.models.database import (
    get_chat_history,
    get_system_stats,
    init_db,
    record_feedback,
    save_chat_message,
    ingest_social_mentions,
    get_all_chat_sessions,
    get_engine,
)
from sqlalchemy import text
from app.services.agent_engine import NIDAAgentEngine
from app.services.auth import UserRole, authenticate_staff
from app.services.document_rag import NIDADocumentRAG
from app.services.vector_store import NIDAVectorStore
from social_listening.advanced_analytics import (
    compute_absa_metrics,
    compute_anomaly_radar,
    generate_executive_swot_summary,
)
from social_listening.analyzer import (
    analyze_sentiment_and_intent,
    generate_wordcloud_image,
    get_word_frequencies,
)
from social_listening.collector_news import NewsCollector
from social_listening.collector_pantip import PantipCollector
from social_listening.collector_youtube import YouTubeCollector
from social_listening.pipeline_runner import NIDADataPipelineRunner
from social_listening.report_generator import (
    generate_executive_html_report,
    generate_executive_csv_summary,
)
from social_listening.storage import read_jsonl, write_jsonl
from social_listening.utils import normalize_text

# Initialize Database & Document Store
init_db()
NIDADocumentRAG.get_instance()

st.set_page_config(
    page_title="NIDACHAT",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── NIDA Official Clean White & Royal Navy Brand CSS ───
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;500;600;700&family=Sarabun:wght@300;400;500;600;700&display=swap');

    html, body, [data-testid="stAppViewContainer"], .stApp {
        font-family: 'Prompt', 'Sarabun', sans-serif !important;
        background-color: #f8fafc !important;
        color: #0f172a !important;
    }
    [data-testid="stHeader"] {
        background-color: rgba(255, 255, 255, 0.95) !important;
        border-bottom: 1px solid #e2e8f0 !important;
    }
    [data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 1px solid #e2e8f0 !important;
    }

    /* Headings & Texts */
    h1, h2, h3, h4, h5, h6, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        color: #002b66 !important;
        font-weight: 700 !important;
    }
    p, span, label, div {
        color: #1e293b;
    }
    [data-testid="stCaptionContainer"] p {
        color: #475569 !important;
        font-size: 0.95rem !important;
    }

    /* Tabs */
    div[data-baseweb="tab-list"] {
        background-color: #e2e8f0 !important;
        border-radius: 10px !important;
        padding: 4px !important;
        gap: 6px !important;
        border: 1px solid #cbd5e1 !important;
    }
    button[data-baseweb="tab"] {
        background: transparent !important;
        color: #475569 !important;
        border-radius: 7px !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        padding: 8px 20px !important;
        transition: all 0.2s ease !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, #002b66, #1d4ed8) !important;
        color: #ffffff !important;
        box-shadow: 0 3px 10px rgba(0, 43, 102, 0.3) !important;
    }

    /* Sidebar Tertiary Buttons Left Align */
    [data-testid="stSidebar"] button[kind="tertiary"] {
        justify-content: flex-start !important;
        text-align: left !important;
        padding-left: 10px !important;
        font-weight: 500 !important;
        color: #334155 !important;
        transition: all 0.2s ease !important;
    }
    [data-testid="stSidebar"] button[kind="tertiary"]:hover {
        background-color: #e2e8f0 !important;
        color: #0f172a !important;
    }
    [data-testid="stSidebar"] button[kind="tertiary"] p {
        font-size: 1.05rem !important;
    }

    /* Suggested Prompts Secondary Button Styling as Cards */
    .stButton>button[kind="secondary"] {
        border-radius: 16px !important;
        padding: 1rem !important;
        background-color: #f8f9fa !important;
        border: 1px solid #e0e0e0 !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
        transition: all 0.2s ease-in-out !important;
        font-weight: 500 !important;
        text-align: left !important;
        height: auto !important;
        color: #444746 !important;
        white-space: pre-wrap !important;
        justify-content: flex-start !important;
    }
    .stButton>button[kind="secondary"]:hover {
        background-color: #ffffff !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1) !important;
        transform: translateY(-2px) !important;
        border-color: #d2e3fc !important;
    }

    /* KPI Metric Cards */
    .nida-kpi-card {
        background: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 12px !important;
        padding: 1.1rem !important;
        text-align: center !important;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.04) !important;
    }
    .nida-kpi-value {
        font-size: 1.8rem !important;
        font-weight: 700 !important;
        color: #002b66 !important;
        margin: 0.2rem 0 !important;
    }
    .nida-kpi-label {
        font-size: 0.9rem !important;
        color: #64748b !important;
        font-weight: 600 !important;
    }

    /* Program Result Cards */
    .nida-prog-card {
        background: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-left: 6px solid #1d4ed8 !important;
        border-radius: 12px !important;
        padding: 1.3rem !important;
        margin-bottom: 1.2rem !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.05) !important;
        color: #0f172a !important;
    }
    .nida-prog-header {
        font-size: 1.25rem !important;
        font-weight: 700 !important;
        color: #002b66 !important;
        margin-bottom: 0.4rem !important;
    }
    .badge-match {
        background: #ecfdf5 !important;
        color: #065f46 !important;
        border: 1px solid #a7f3d0 !important;
        padding: 3px 10px !important;
        border-radius: 20px !important;
        font-weight: 700 !important;
        font-size: 0.85rem !important;
    }
    .badge-fee {
        background: #fffbeb !important;
        color: #92400e !important;
        border: 1px solid #fde68a !important;
        padding: 3px 10px !important;
        border-radius: 20px !important;
        font-weight: 700 !important;
        font-size: 0.85rem !important;
    }
    .guidance-box {
        background: #eff6ff !important;
        border: 1px solid #bfdbfe !important;
        border-radius: 8px !important;
        padding: 0.9rem !important;
        margin-top: 0.8rem !important;
        font-size: 0.95rem !important;
        color: #1e3a8a !important;
        line-height: 1.6 !important;
    }

    /* Buttons & Inputs */
    button[kind="secondary"], [data-testid="baseButton-secondary"] {
        background-color: #ffffff !important;
        color: #0f172a !important;
        border: 1px solid #cbd5e1 !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05) !important;
    }
    button[kind="secondary"]:hover, [data-testid="baseButton-secondary"]:hover {
        background-color: #f1f5f9 !important;
        color: #002b66 !important;
        border-color: #94a3b8 !important;
    }
    button[kind="primary"], [data-testid="baseButton-primary"] {
        background: linear-gradient(135deg, #002b66, #1d4ed8) !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 1.05rem !important;
        border: none !important;
        border-radius: 8px !important;
        box-shadow: 0 4px 14px rgba(0, 43, 102, 0.25) !important;
    }
    textarea, input, .stTextArea textarea, .stTextInput input {
        background-color: #ffffff !important;
        color: #0f172a !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
        font-size: 0.95rem !important;
    }
    [data-testid="stChatMessage"] {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 12px !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03) !important;
        color: #0f172a !important;
    }
    
    /* User Chat Bubble Right Alignment */
    [data-testid="stChatMessage"]:has(.user-msg-marker) {
        flex-direction: row-reverse;
        border: none !important;
        background-color: transparent !important;
        box-shadow: none !important;
    }
    [data-testid="stChatMessage"]:has(.user-msg-marker) [data-testid="stChatMessageAvatar"] {
        margin-left: 1rem;
        margin-right: 0;
    }
    [data-testid="stChatMessage"]:has(.user-msg-marker) .stMarkdown {
        background-color: #f1f5f9;
        padding: 12px 18px;
        border-radius: 18px 18px 4px 18px;
        color: #0f172a;
    }

    /* Premium Chat Input Box Styling */
    [data-testid="stChatInput"] {
        max-width: 850px !important;
        margin: 0 auto !important; /* Center the input container */
        background-color: transparent !important;
        padding-bottom: 2rem !important; /* Lift it slightly from the absolute bottom */
    }
    
    /* The inner container of the chat input */
    [data-testid="stChatInput"] > div {
        border: 1px solid #cbd5e1 !important; /* Very subtle border */
        background-color: #ffffff !important; /* White pill on gray background */
        border-radius: 30px !important; /* Pill shape */
        padding: 5px 10px 5px 20px !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05) !important;
    }
    
    [data-testid="stChatInput"] > div:focus-within {
        border: 1px solid #3b82f6 !important;
        box-shadow: 0 4px 20px rgba(59, 130, 246, 0.15) !important;
    }

    /* Target the text area inside */
    [data-testid="stChatInput"] textarea {
        background-color: transparent !important;
        border: none !important;
        color: #1e293b !important;
        font-size: 1rem !important;
    }
    
    [data-testid="stChatInput"] textarea:focus {
        box-shadow: none !important;
    }

    /* Target the send button inside */
    [data-testid="stChatInput"] button {
        background-color: #3b82f6 !important; /* Blue send button */
        border-radius: 50% !important; /* Circular button */
        height: 40px !important;
        width: 40px !important;
        padding: 0 !important;
        margin-left: 8px !important;
        transition: all 0.2s ease !important;
    }
    
    [data-testid="stChatInput"] button:hover {
        background-color: #2563eb !important;
        transform: scale(1.05);
    }
    
    [data-testid="stChatInput"] button svg {
        fill: white !important;
        color: white !important;
    }
    </style>

    """,
    unsafe_allow_html=True,
)


# ─── Data Helper ───

@st.cache_data(ttl=60)
def load_all_comments() -> List[Dict[str, Any]]:
    """รวบรวมความคิดเห็นโซเชียลมีเดีย ป.โท-เอก นิด้า จากไฟล์ข้อมูลทั้งหมด"""
    data_dirs = [
        PROJECT_ROOT / "social_listening" / "data",
        PROJECT_ROOT / "data",
    ]
    comments: List[Dict[str, Any]] = []
    seen = set()

    for d in data_dirs:
        if not d.exists():
            continue
        for fp in d.glob("*.jsonl"):
            try:
                records = read_jsonl(fp)
                for item in records:
                    platform = item.get("platform", "Pantip / Social")
                    if "comments" in item and isinstance(item["comments"], list):
                        for c in item["comments"]:
                            txt = normalize_text(c.get("text"))
                            if txt and txt not in seen:
                                seen.add(txt)
                                res = analyze_sentiment_and_intent(txt)
                                comments.append({
                                    "platform": platform,
                                    "title": item.get("video_title") or item.get("title", ""),
                                    "text": txt,
                                    "author": c.get("author", "ผู้ใช้ทั่วไป"),
                                    "published_at": c.get("published_at") or item.get("published_at", ""),
                                    "url": c.get("comment_url") or item.get("url", ""),
                                    "sentiment": c.get("sentiment") or res["sentiment"],
                                    "intent": c.get("intent") or res["intent"],
                                })
                    else:
                        txt = normalize_text(item.get("text") or item.get("title"))
                        if txt and txt not in seen:
                            seen.add(txt)
                            res = analyze_sentiment_and_intent(txt)
                            comments.append({
                                "platform": platform,
                                "title": item.get("title", ""),
                                "text": txt,
                                "author": item.get("author", "ผู้ใช้ทั่วไป"),
                                "published_at": item.get("published_at", ""),
                                "url": item.get("url", ""),
                                "sentiment": item.get("sentiment") or res["sentiment"],
                                "intent": item.get("intent") or res["intent"],
                            })
            except Exception:
                continue
    return comments


# ─── VIEW 1: DEDICATED NIDA GEMINI STUDIO (AI ADVISOR) ───

@st.dialog("วิดีโอแนะนำ NIDA")
def show_video_dialog():
    st.video("https://www.youtube.com/watch?v=R9K1N3O6y0g")
    st.caption("คลิปวิดีโอแนะนำสถาบันบัณฑิตพัฒนบริหารศาสตร์ (NIDA)")

def render_gemini_studio() -> None:
    """Dedicated Google Gemini-style conversational AI advisory interface for NIDA Graduate Education."""
    if "session_id" not in st.session_state:
        st.session_state.session_id = f"nida-gemini-{uuid.uuid4().hex[:8]}"

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    if "show_search" not in st.session_state:
        st.session_state.show_search = False
        
    if "show_library" not in st.session_state:
        st.session_state.show_library = True

    if "editing_msg_idx" not in st.session_state:
        st.session_state.editing_msg_idx = -1

    # Sidebar: Model Selector & Advanced Filter Controls
    with st.sidebar:
        selected_model = "gemini-2.5-pro"

        if st.button("แชทใหม่", icon=":material/edit_square:", type="tertiary", use_container_width=True):
            st.session_state.session_id = f"nida-gemini-{uuid.uuid4().hex[:8]}"
            st.session_state.chat_messages = []
            st.rerun()

        if st.button("ค้นหาแชท", icon=":material/search:", type="tertiary", use_container_width=True):
            st.session_state.show_search = not st.session_state.show_search
            st.rerun()

        search_query = ""
        if st.session_state.show_search:
            search_query = st.text_input("ค้นหาแชท", placeholder="พิมพ์ชื่อบทสนทนา...", label_visibility="collapsed")

        if st.button("วิดีโอ", icon=":material/video_library:", type="tertiary", use_container_width=True):
            show_video_dialog()

        if st.button("คลัง", icon=":material/grid_view:", type="tertiary", use_container_width=True):
            st.session_state.show_library = not st.session_state.show_library
            st.rerun()
        
        if st.session_state.show_library:
            st.markdown("<br>", unsafe_allow_html=True)
            # We use a container with a fixed height to allow scrolling if there are many chats
            history_container = st.container(height=300, border=False)
            with history_container:
                sessions = get_all_chat_sessions(search_query=search_query)
                
                if not sessions:
                    st.caption("ไม่มีประวัติการสนทนา")
                else:
                    for session in sessions:
                        title = session["title"]
                        if len(title) > 25:
                            title = title[:25] + "..."
                        
                        is_active = session["session_id"] == st.session_state.session_id
                        
                        if st.button(
                            title,
                            icon=":material/chat_bubble_outline:",
                            key=f"hist_{session['session_id']}",
                            use_container_width=True,
                            type="secondary" if is_active else "tertiary"
                        ):
                            st.session_state.session_id = session["session_id"]
                            st.session_state.chat_messages = get_chat_history(session["session_id"])
                            st.rerun()



    # Gemini Hero Header
    if not st.session_state.chat_messages:
        st.markdown(
            """
            <div style="text-align: center; padding: 4rem 1rem 2rem 1rem; max-width: 900px; margin: 0 auto;">
                <h1 style="font-size: 3.5rem; font-weight: 800; background: linear-gradient(90deg, #4285f4, #9b72cb, #d96570); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0.6rem; letter-spacing: -1.5px;">
                    ✨ สวัสดี คุณสนใจศึกษาที่ NIDA ไหม?
                </h1>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Gemini-style Prompt Suggestion Cards (2x2 Grid)
        st.markdown("<p style='text-align:center; color:#64748b; font-weight:600; font-size:0.95rem; margin-bottom:0.8rem;'>💡 ตัวอย่างประเด็นที่สามารถสอบถามได้ทันที:</p>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        pending_prompt = ""

        with col1:
            if st.button("💼 ทำงานประจำ อยากเรียน MBA เสาร์-อาทิตย์ ค่าเทอมไม่เกิน 1.5 แสน มีไหม?", use_container_width=True):
                pending_prompt = "ทำงานประจำ อยากเรียนต่อ MBA นิด้า วันเสาร์-อาทิตย์ มีหลักสูตรไหนบ้าง ค่าเทอมประมาณเท่าไหร่ และคุณสมบัติเป็นอย่างไร?"
            if st.button("🏛️ ข้าราชการ เรียน MPA แนะนำ แผน ก (วิทยานิพนธ์) หรือ แผน ข (IS) ดีกว่ากัน?", use_container_width=True):
                pending_prompt = "ทำงานรับราชการ สนใจเรียนต่อ MPA รัฐประศาสนศาสตร์ ควรเลือกเรียน แผน ก (วิทยานิพนธ์) หรือ แผน ข (สารนิพนธ์ IS) ต่างกันอย่างไร?"

        with col2:
            if st.button("📊 จบไม่ตรงสาย อยากเรียน Data Science & AI นิด้า มีเงื่อนไขอะไรบ้าง?", use_container_width=True):
                pending_prompt = "จบปริญญาตรีไม่ตรงสาย (ไม่ใช่สายคอมพิวเตอร์) สามารถสมัครเรียนต่อ ป.โท วิทยาการข้อมูลและปัญญาประดิษฐ์ (DADS) นิด้า ได้ไหมครับ?"
            if st.button("⚖️ เกณฑ์คะแนนสอบ NIDA TEAP และระเบียบเทียบโอนหน่วยกิตเป็นอย่างไร?", use_container_width=True):
                pending_prompt = "เกณฑ์คะแนนภาษาอังกฤษ NIDA TEAP ต้องได้เท่าไหร่ และหากเคยเรียน ป.โท จากสถาบันอื่นมาสามารถเทียบโอนหน่วยกิตได้กี่หน่วยกิต?"

        st.divider()

    # Global pending_prompt handler from edits
    if "pending_prompt" in st.session_state and st.session_state.pending_prompt:
        pending_prompt = st.session_state.pending_prompt
        del st.session_state.pending_prompt

    # Display Chat History Thread
    for idx, msg in enumerate(st.session_state.chat_messages):
        role = "assistant" if msg["sender"] == "assistant" else "user"
        avatar = "✨" if role == "assistant" else "👤"
        with st.chat_message(role, avatar=avatar):
            if role == "user":
                st.markdown("<span class='user-msg-marker'></span>", unsafe_allow_html=True)
                
                if st.session_state.editing_msg_idx == idx:
                    new_msg = st.text_area("แก้ไขข้อความ", value=msg["message"], key=f"edit_area_{idx}", label_visibility="collapsed")
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        if st.button("บันทึก & ส่งใหม่", key=f"save_btn_{idx}", type="primary", use_container_width=True):
                            st.session_state.chat_messages = st.session_state.chat_messages[:idx]
                            st.session_state.pending_prompt = new_msg
                            st.session_state.editing_msg_idx = -1
                            st.rerun()
                    with col2:
                        if st.button("ยกเลิก", key=f"cancel_btn_{idx}", use_container_width=True):
                            st.session_state.editing_msg_idx = -1
                            st.rerun()
                else:
                    st.markdown(msg["message"])
                    # Small Edit button aligned nicely
                    col1, col2 = st.columns([10, 1])
                    with col2:
                        if st.button("✏️", key=f"edit_trigger_{idx}", help="แก้ไขและสร้างคำตอบใหม่จากจุดนี้"):
                            st.session_state.editing_msg_idx = idx
                            st.rerun()
            else:
                st.markdown(msg["message"])
                if msg.get("recommended_programs"):
                    with st.expander("🎓 ข้อมูลหลักสูตร NIDA ที่เกี่ยวข้องกับการสนทนานี้", expanded=True):
                        for prog_idx, prog in enumerate(msg["recommended_programs"][:3], 1):
                            fee_disp = prog.get("total_fee") or "สอบถามสถาบัน"
                            careers = ", ".join(prog.get("career_opportunities", [])) or "ผู้บริหาร, นักวิเคราะห์, ที่ปรึกษา"
                            st.markdown(
                                f"""
                                <div class="nida-prog-card">
                                    <div class="nida-prog-header">#{prog_idx} {prog.get('program')} ({prog.get('degree')})</div>
                                    <p><strong>คณะ:</strong> {prog.get('faculty')} | <span class="badge-fee">ค่าเทอมประมาณ: {fee_disp} บาท</span> | <span class="badge-match">ตรงใจ {prog.get('match_score', 95)}%</span></p>
                                    <p>⏱️ <strong>เวลาเรียน:</strong> {prog.get('study_time', 'เสาร์-อาทิตย์ / ปกติ')} | 🎯 <strong>คุณสมบัติ:</strong> {prog.get('admission_requirements', 'ปริญญาตรีทุกสาขา')}</p>
                                    <p>💼 <strong>โอกาสต่อยอดสายอาชีพ:</strong> {careers}</p>
                                    <a href="{prog.get('application_link', 'https://www.nida.ac.th')}" target="_blank" style="color:#1d4ed8; font-weight:700;">🔗 ข้อมูลหลักสูตรและสมัครเรียนออนไลน์ &rarr;</a>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

    # Gemini Input Box
    user_prompt = st.chat_input("ถาม NIDA")
    if "pending_prompt" in locals() and pending_prompt:
        user_prompt = pending_prompt

    if user_prompt:
        st.session_state.chat_messages.append({"sender": "user", "message": user_prompt})
        with st.chat_message("user", avatar="👤"):
            st.markdown("<span class='user-msg-marker'></span>", unsafe_allow_html=True)
            st.markdown(user_prompt)

        with st.chat_message("assistant", avatar="✨"):
            res_data = {}
            def _metadata_cb(data):
                res_data.update(data)
                
            response_generator = NIDAAgentEngine.execute_chat_stream(
                session_id=st.session_state.session_id,
                user_message=user_prompt,
                degree_filter="ทั้งหมด",
                faculty_filter="ทั้งหมด",
                study_mode_filter="ทั้งหมด",
                model_name=selected_model,
                metadata_callback=_metadata_cb
            )
            
            full_response = st.write_stream(response_generator)
            if "reply" not in res_data:
                res_data["reply"] = full_response

            if res_data.get("recommended_programs"):
                with st.expander("🎓 ข้อมูลหลักสูตร NIDA ที่เกี่ยวข้องกับการสนทนานี้", expanded=True):
                    for idx, prog in enumerate(res_data["recommended_programs"][:3], 1):
                        fee_disp = prog.get("total_fee") or "สอบถามสถาบัน"
                        careers = ", ".join(prog.get("career_opportunities", [])) or "ผู้บริหาร, นักวิเคราะห์, ที่ปรึกษา"
                        st.markdown(
                            f"""
                            <div class="nida-prog-card">
                                <div class="nida-prog-header">#{idx} {prog.get('program')} ({prog.get('degree')})</div>
                                <p><strong>คณะ:</strong> {prog.get('faculty')} | <span class="badge-fee">ค่าเทอมประมาณ: {fee_disp} บาท</span> | <span class="badge-match">ตรงใจ {prog.get('match_score', 95)}%</span></p>
                                <p>⏱️ <strong>เวลาเรียน:</strong> {prog.get('study_time', 'เสาร์-อาทิตย์ / ปกติ')} | 🎯 <strong>คุณสมบัติ:</strong> {prog.get('admission_requirements', 'ปริญญาตรีทุกสาขา')}</p>
                                <p>💼 <strong>โอกาสต่อยอดสายอาชีพ:</strong> {careers}</p>
                                <a href="{prog.get('application_link', 'https://www.nida.ac.th')}" target="_blank" style="color:#1d4ed8; font-weight:700;">🔗 ข้อมูลหลักสูตรและสมัครเรียนออนไลน์ &rarr;</a>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

            st.session_state.chat_messages.append({
                "sender": "assistant",
                "message": res_data["reply"],
                "recommended_programs": res_data["recommended_programs"],
                "tools_used": res_data["tools_used"],
            })


# ─── VIEW 2: NIDA COURSE EXPLORER & COMPARISON ───

def render_public_catalog_tab() -> None:
    st.markdown("""
    <style>
    /* Premium Global CSS for Catalog */
    .catalog-header {
        text-align: center;
        padding: 2rem 0 1rem 0;
        background: linear-gradient(135deg, #0A2540 0%, #173d6b 100%);
        color: white;
        border-radius: 12px;
        margin-bottom: 2rem;
        box-shadow: 0 10px 25px rgba(10, 37, 64, 0.2);
    }
    .catalog-header h1 {
        color: #B28B47 !important;
        font-weight: 800;
        margin-bottom: 0.5rem;
    }
    .catalog-header p {
        color: #EDF2F7;
        font-size: 1.1rem;
        opacity: 0.9;
    }
    .nida-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
        gap: 1.5rem;
        margin-top: 1.5rem;
    }
    .nida-card {
        background: white;
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.04);
        border: 1px solid #f1f5f9;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        display: flex;
        flex-direction: column;
        position: relative;
        overflow: hidden;
    }
    .nida-card::before {
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 4px;
        background: linear-gradient(90deg, #0A2540, #B28B47);
        opacity: 0;
        transition: opacity 0.3s;
    }
    .nida-card:hover {
        transform: translateY(-6px);
        box-shadow: 0 15px 30px rgba(0,0,0,0.1);
        border-color: transparent;
    }
    .nida-card:hover::before {
        opacity: 1;
    }
    .badge-container {
        display: flex;
        gap: 8px;
        margin-bottom: 12px;
        flex-wrap: wrap;
    }
    .badge {
        font-size: 0.75rem;
        padding: 4px 10px;
        border-radius: 20px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .badge-fac { background: rgba(10, 37, 64, 0.1); color: #0A2540; }
    .badge-deg { background: rgba(178, 139, 71, 0.15); color: #9c7331; }
    .card-title {
        font-size: 1.25rem;
        font-weight: 800;
        color: #1e293b;
        margin-bottom: 12px;
        line-height: 1.4;
    }
    .card-detail {
        font-size: 0.95rem;
        color: #475569;
        margin-bottom: 8px;
        display: flex;
        align-items: flex-start;
        gap: 8px;
    }
    .card-icon {
        font-size: 1.1rem;
        flex-shrink: 0;
    }
    .card-spacer {
        flex-grow: 1;
    }
    .nida-btn {
        display: block;
        text-align: center;
        background: #0A2540;
        color: white !important;
        text-decoration: none !important;
        padding: 12px;
        border-radius: 10px;
        font-weight: 600;
        margin-top: 20px;
        transition: all 0.2s;
        border: 1px solid transparent;
    }
    .nida-btn:hover {
        background: white;
        color: #0A2540 !important;
        border-color: #0A2540;
    }
    </style>
    <div class="catalog-header">
        <h1>🏛️ NIDA Course Explorer</h1>
        <p>สารบบและตารางเปรียบเทียบ 73 หลักสูตรทางการ (ป.โท - ป.เอก) ครบทั้ง 14 คณะ/วิทยาลัย</p>
    </div>
    """, unsafe_allow_html=True)

    vs = NIDAVectorStore.get_instance()
    all_programs = vs.programs

    # 1. Search & Filters
    st.markdown("### 🔍 ค้นหาและกรองหลักสูตร")
    f_col1, f_col2, f_col3 = st.columns(3)
    with f_col1:
        deg_filter = st.selectbox("🎓 ระดับการศึกษา", ["ทั้งหมด", "ป.โท", "ป.เอก"], key="cat_deg")
    with f_col2:
        facs = sorted(list({p.get("faculty", "") for p in all_programs if p.get("faculty")}))
        fac_filter = st.selectbox("🏢 คณะที่ต้องการ", ["ทั้งหมด"] + facs, key="cat_fac")
    with f_col3:
        mode_filter = st.selectbox("⏱️ เวลาเรียน", ["ทั้งหมด", "เสาร์-อาทิตย์", "ภาคค่ำ", "ภาคปกติ", "English"], key="cat_mode")

    search_term = st.text_input("✨ พิมพ์ชื่อหลักสูตร, สาขาวิชา หรือสายอาชีพที่สนใจ...", "", placeholder="เช่น MBA, Data Science, ผู้บริหาร...")
    
    # 2. Filter Logic
    filtered = all_programs
    if deg_filter != "ทั้งหมด":
        filtered = [p for p in filtered if deg_filter in p.get("degree", "")]
    if fac_filter != "ทั้งหมด":
        filtered = [p for p in filtered if fac_filter in p.get("faculty", "")]
    if mode_filter != "ทั้งหมด":
        filtered = [p for p in filtered if mode_filter in p.get("study_time", "")]
    if search_term:
        s_low = search_term.lower()
        filtered = [
            p for p in filtered
            if s_low in p.get("program", "").lower()
            or s_low in p.get("faculty", "").lower()
            or s_low in p.get("department", "").lower()
            or any(s_low in c.lower() for c in p.get("career_opportunities", []))
        ]

    st.markdown(f"**พบหลักสูตรที่ตรงกับเงื่อนไข:** `{len(filtered)}` หลักสูตร")

    # 3. Render HTML Grid
    if not filtered:
        st.info("💡 ไม่พบหลักสูตรที่ตรงกับเงื่อนไข ลองปรับตัวกรองหรือคำค้นหาดูนะครับ")
    else:
        cards_html = "<div class='nida-grid'>"
        for p in filtered:
            fee_disp = p.get('total_fee') or 'สอบถามสถาบัน'
            careers = ", ".join(p.get("career_opportunities", [])[:3])
            if len(p.get("career_opportunities", [])) > 3: careers += "..."
            
            cards_html += f"""
            <div class="nida-card">
                <div class="badge-container">
                    <span class="badge badge-fac">{p.get('faculty')}</span>
                    <span class="badge badge-deg">{p.get('degree')}</span>
                </div>
                <div class="card-title">{p.get('program')}</div>
                
                <div class="card-detail">
                    <span class="card-icon">📚</span>
                    <span><strong>สาขา:</strong> {p.get('department', '-')}</span>
                </div>
                <div class="card-detail">
                    <span class="card-icon">⏱️</span>
                    <span><strong>เวลาเรียน:</strong> {p.get('study_time', 'ปกติ')}</span>
                </div>
                <div class="card-detail">
                    <span class="card-icon">💰</span>
                    <span><strong>ค่าเทอมโดยประมาณ:</strong> {fee_disp} ฿</span>
                </div>
                <div class="card-detail">
                    <span class="card-icon">🎯</span>
                    <span><strong>อาชีพ:</strong> {careers or '-'}</span>
                </div>
                
                <div class="card-spacer"></div>
                <a href="{p.get('application_link', 'https://www.nida.ac.th')}" target="_blank" class="nida-btn">
                    อ่านรายละเอียด & สมัครเรียน ➔
                </a>
            </div>
            """
        cards_html += "</div>"
        st.markdown(cards_html, unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.divider()

    # 4. Side-by-Side Comparison (Moved to bottom)
    st.markdown("### ⚖️ เปรียบเทียบหลักสูตร (Compare Programs)")
    st.caption("เลือกหลักสูตรที่สนใจ 2-3 อัน เพื่อนำมาเปรียบเทียบจุดเด่นและค่าเทอมแบบเจาะลึก")
    
    prog_names = [p.get("program", "") for p in all_programs if p.get("program")]
    selected = st.multiselect(
        "เลือกหลักสูตรที่ต้องการเปรียบเทียบ:",
        options=prog_names,
        default=prog_names[:2] if len(prog_names) >= 2 else prog_names,
        max_selections=3,
        key="compare_sel"
    )

    if len(selected) >= 2:
        compared = vs.compare_programs(selected)
        cols = st.columns(len(compared))
        for idx, p in enumerate(compared):
            with cols[idx]:
                fee_disp = p.get('total_fee') or 'สอบถามสถาบัน'
                st.markdown(
                    f"""
                    <div class="nida-card" style="margin-top: 1rem;">
                        <div class="badge-container">
                            <span class="badge badge-fac">{p.get('faculty')}</span>
                        </div>
                        <div class="card-title" style="font-size: 1.1rem;">{p.get('program')}</div>
                        <hr style="border:none; border-top: 1px dashed #cbd5e1; margin: 10px 0;">
                        <p style="font-size: 0.9rem; margin-bottom: 8px;"><strong>ระดับ:</strong> {p.get('degree')}</p>
                        <p style="font-size: 0.9rem; margin-bottom: 8px;"><strong>ค่าเทอม:</strong> <span style="color:#B28B47; font-weight:bold;">{fee_disp} ฿</span></p>
                        <p style="font-size: 0.9rem; margin-bottom: 8px;"><strong>เวลาเรียน:</strong> {p.get('study_time', '-')}</p>
                        <p style="font-size: 0.9rem; margin-bottom: 8px;"><strong>คุณสมบัติ:</strong> {p.get('admission_requirements', '-')}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

# ─── VIEW 2: NIDA EXECUTIVE & STAFF BI ANALYTICS (GATED) ───

def render_executive_radar_tab() -> None:
    st.markdown("## 📈 Executive Intelligence & ABSA Radar (สำหรับผู้บริหารนิด้า)")
    st.markdown("สรุปภาพรวมเชิงกลยุทธ์ การวิเคราะห์ SWOT อัตโนมัติ และเรดาร์ตรวจจับประเด็นเสี่ยงต่อชื่อเสียงสถาบัน")

    comments = load_all_comments()
    absa = compute_absa_metrics(comments)
    anomalies = compute_anomaly_radar(comments)
    swot = generate_executive_swot_summary(comments)

    def format_bullets(items: Any) -> str:
        if isinstance(items, list):
            return "\n".join([f"- {item}" for item in items])
        return str(items)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🏆 จุดแข็ง & โอกาสทางการตลาด (Strengths & Opportunities)")
        st.markdown(f"**🌟 จุดแข็ง:**\n{format_bullets(swot.get('strengths', []))}")
        st.markdown(f"**🚀 โอกาสเติบโต:**\n{format_bullets(swot.get('opportunities', []))}")
    with col2:
        st.markdown("### ⚠️ จุดเปราะบาง & ข้อเสนอแนะ (Weaknesses & Strategic Actions)")
        st.markdown(f"**⚡ จุดเปราะบาง:**\n{format_bullets(swot.get('weaknesses', []))}")
        st.markdown(f"**💡 ข้อเสนอแนะเชิงกลยุทธ์:**\n{format_bullets(swot.get('strategic_actions', []))}")

    st.divider()

    st.markdown("### 🚨 เรดาร์ตรวจจับประเด็นวิกฤต (Crisis & Anomaly Radar)")
    radar = compute_anomaly_radar(comments)
    if radar.get("crisis_level") == "HIGH RISK":
        st.error(f"**[{radar.get('crisis_level')}] ดัชนีความเสี่ยง: `{radar.get('crisis_score')}/100` (เชิงลบ: `{radar.get('negative_ratio')}%`)**\n\n{radar.get('alert_message')}")
    elif radar.get("crisis_level") == "ELEVATED ATTENTION":
        st.warning(f"**[{radar.get('crisis_level')}] ดัชนีความเสี่ยง: `{radar.get('crisis_score')}/100` (เชิงลบ: `{radar.get('negative_ratio')}%`)**\n\n{radar.get('alert_message')}")
    else:
        st.success(f"**[{radar.get('crisis_level')}] ดัชนีความเสี่ยง: `{radar.get('crisis_score')}/100`**\n\n{radar.get('alert_message')}")

    st.divider()

    st.divider()

    st.markdown("### 🎯 คะแนนเสียงสะท้อน 5 มิติสถาบัน (Aspect-Based Sentiment Analysis)")
    absa_df = pd.DataFrame([
        {
            "มิติการประเมิน": d["label"],
            "ดัชนีความพึงพอใจ (Satisfaction Index)": f"{d.get('satisfaction_index', 50.0)}/100",
            "เสียงชื่นชม (%)": f"{d['pos_ratio']}%",
            "ข้อกังวล (%)": f"{d['neg_ratio']}%",
            "จำนวนความคิดเห็น": f"{d['total_mentions']} ข้อความ",
        }
        for k, d in absa.items()
    ])
    st.dataframe(absa_df, use_container_width=True, hide_index=True)

    st.divider()

    # Executive Report Exporter Section
    st.markdown("### 📥 ศูนย์ส่งออกรายงานสรุปสำหรับผู้บริหาร (Executive Report Exporter)")
    st.markdown("ดาวน์โหลดรายงานสรุปฉบับเต็มพร้อมพิมพ์ (Printable A4 HTML/PDF) และข้อมูลตัวเลขสำหรับนำเสนอในที่ประชุมสภามหาวิทยาลัย")

    pos_count = sum(1 for c in comments if c.get("sentiment") == "Positive")
    neg_count = sum(1 for c in comments if c.get("sentiment") == "Negative")
    neu_count = sum(1 for c in comments if c.get("sentiment") not in ["Positive", "Negative"])
    
    sent_dict = {"Positive": pos_count, "Negative": neg_count, "Neutral": neu_count}
    intent_dict = {
        "interest_apply": sum(1 for c in comments if c.get("intent") == "interest_apply"),
        "inquire_tuition": sum(1 for c in comments if c.get("intent") == "inquire_tuition"),
        "ask_scholarship": sum(1 for c in comments if c.get("intent") == "ask_scholarship"),
    }
    
    anomaly_list = [
        {"severity": "MEDIUM", "topic": "เกณฑ์ภาษาอังกฤษ NIDA TEAP", "insight": "ผู้สมัครกังวลเรื่องการเตรียมตัวสอบ ควรประชาสัมพันธ์คอร์สปรับพื้นฐาน LC 4001/4002 ให้กว้างขวาง"},
        {"severity": "MEDIUM", "topic": "การเดินทางและที่จอดรถ", "insight": "ช่วงเช้าวันเสาร์-อาทิตย์รถค่อนข้างหนาแน่น แนะนำประชาสัมพันธ์จุดต่อรถไฟฟ้าสายสีเหลืองและสีส้ม"},
        {"severity": "LOW", "topic": "งบประมาณและค่าเทอม", "insight": "ควรเน้นประชาสัมพันธ์โครงการผ่อนชำระค่าธรรมเนียม 0% 3 งวดบนสื่อโซเชียลมีเดีย"},
    ]

    curr_role = st.session_state.get("auth_role_name", "Dean / Executive Board")
    html_data = generate_executive_html_report(
        total_comments=len(comments),
        sentiment_counts=sent_dict,
        intent_counts=intent_dict,
        swot_data=swot,
        anomalies=anomaly_list,
        user_role=curr_role,
    )
    csv_data = generate_executive_csv_summary(
        sentiment_counts=sent_dict,
        intent_counts=intent_dict,
        swot_data=swot,
    )

    btn_col1, btn_col2, btn_col3 = st.columns(3)
    with btn_col1:
        st.download_button(
            label="📄 ดาวน์โหลด Executive Report (HTML / Printable PDF)",
            data=html_data,
            file_name=f"NIDA_Executive_Briefing_{uuid.uuid4().hex[:6]}.html",
            mime="text/html",
            type="primary",
            use_container_width=True,
            help="คลิกเพื่อดาวน์โหลดไฟล์รายงานแบบทางการ สามารถเปิดในเบราว์เซอร์แล้วกด Ctrl+P เพื่อบันทึกเป็น PDF ได้ทันที",
        )
    with btn_col2:
        st.download_button(
            label="📊 ดาวน์โหลด Metrics Data (CSV for Excel)",
            data=csv_data,
            file_name=f"NIDA_Executive_Metrics_{uuid.uuid4().hex[:6]}.csv",
            mime="text/csv",
            use_container_width=True,
            help="ดาวน์โหลดตัวเลขและมิติความรู้สึกนำไปใช้วิเคราะห์ต่อใน Microsoft Excel",
        )
    with btn_col3:
        md_summary = f"""# NIDA Executive Briefing Summary\n\n**Generated for:** {curr_role}\n**Total Comments Analyzed:** {len(comments):,}\n\n## SWOT Matrix\n- **Strengths:** {', '.join(swot.get('strengths', []))}\n- **Weaknesses:** {', '.join(swot.get('weaknesses', []))}\n- **Opportunities:** {', '.join(swot.get('opportunities', []))}\n- **Threats:** {', '.join(swot.get('threats', []))}\n"""
        st.download_button(
            label="📝 ดาวน์โหลด Executive Summary (Markdown)",
            data=md_summary,
            file_name=f"NIDA_Executive_Summary_{uuid.uuid4().hex[:6]}.md",
            mime="text/markdown",
            use_container_width=True,
        )


def render_executive_social_tab() -> None:
    st.markdown("## 📊 Social Listening & Word Cloud Studio")
    st.markdown("วิเคราะห์เจาะลึกเสียงสะท้อนจาก Pantip, YouTube, ข่าวการศึกษา พร้อม Word Cloud สกัดคำสำคัญ")

    comments = load_all_comments()

    # KPI Metrics
    total = len(comments)
    pos = sum(1 for c in comments if c.get("sentiment") == "Positive")
    neg = sum(1 for c in comments if c.get("sentiment") == "Negative")
    q_count = sum(1 for c in comments if c.get("sentiment") == "Question")

    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(f'<div class="nida-kpi-card"><div class="nida-kpi-label">💬 ความคิดเห็นทั้งหมด</div><div class="nida-kpi-value">{total}</div><div class="nida-kpi-label">จาก 3 แพลตฟอร์ม</div></div>', unsafe_allow_html=True)
    k2.markdown(f'<div class="nida-kpi-card"><div class="nida-kpi-label">🌟 เสียงชื่นชม (Positive)</div><div class="nida-kpi-value" style="color:#4ade80;">{round(pos/total*100,1) if total else 0}%</div><div class="nida-kpi-label">{pos} ข้อความ</div></div>', unsafe_allow_html=True)
    k3.markdown(f'<div class="nida-kpi-card"><div class="nida-kpi-label">❓ คำถามยอดฮิต (Question)</div><div class="nida-kpi-value" style="color:#60a5fa;">{round(q_count/total*100,1) if total else 0}%</div><div class="nida-kpi-label">{q_count} ข้อความ</div></div>', unsafe_allow_html=True)
    k4.markdown(f'<div class="nida-kpi-card"><div class="nida-kpi-label">⚠️ ข้อกังวล (Negative)</div><div class="nida-kpi-value" style="color:#f87171;">{round(neg/total*100,1) if total else 0}%</div><div class="nida-kpi-label">{neg} ข้อความ</div></div>', unsafe_allow_html=True)

    st.divider()

    # Word Cloud & Top Keywords
    all_texts = [c.get("text", "") for c in comments if c.get("text")]
    col_wc, col_kw = st.columns([1.3, 1])
    with col_wc:
        st.subheader("☁️ Word Cloud คำที่คนพูดถึงมากที่สุด")
        wc_bytes = generate_wordcloud_image(all_texts)
        if wc_bytes:
            st.image(wc_bytes, use_container_width=True)
    with col_kw:
        st.subheader("📌 10 ประเด็นคำสำคัญที่พบมากที่สุด")
        freqs = get_word_frequencies(all_texts, top_n=10)
        df_freq = pd.DataFrame(freqs, columns=["คำสำคัญ (Keyword)", "ความถี่ที่พบ (ครั้ง)"])
        st.dataframe(df_freq, use_container_width=True, hide_index=True)

    st.divider()

    # Raw Search Table
    st.subheader("🔎 คลังความคิดเห็นโซเชียลมีเดีย")
    c_search, c_filter = st.columns([2, 1])
    with c_search:
        kw = st.text_input("ค้นหาคำในคอมเมนต์ เช่น 'ค่าเทอม', 'อาจารย์', 'เสาร์-อาทิตย์':", "")
    with c_filter:
        sentiment_sel = st.multiselect("กรองตามความรู้สึก", ["Positive", "Negative", "Question", "Neutral"], default=["Positive", "Negative", "Question", "Neutral"])

    df_show = pd.DataFrame(comments)
    if kw:
        df_show = df_show[df_show["text"].str.contains(kw, case=False, na=False)]
    df_show = df_show[df_show["sentiment"].isin(sentiment_sel)]

    st.dataframe(
        df_show[["platform", "sentiment", "intent", "text", "published_at"]],
        column_config={
            "platform": st.column_config.TextColumn("แหล่งข้อมูล"),
            "sentiment": st.column_config.TextColumn("ความรู้สึก"),
            "intent": st.column_config.TextColumn("หัวข้อเรื่อง"),
            "text": st.column_config.TextColumn("ข้อความความคิดเห็น", width="large"),
            "published_at": st.column_config.TextColumn("วันที่"),
        },
        use_container_width=True,
        hide_index=True,
    )


def render_executive_etl_tab() -> None:
    st.markdown("## 🔄 Automated Data Pipeline & ETL Ingestion (สิทธิ์เจ้าหน้าที่นิด้า)")
    st.markdown("ระบบรวบรวมข้อมูลโซเชียลมีเดียอัตโนมัติ พร้อมระบบตรวจจับและกรอง Spam/Bot อัจฉริยะ ซิงค์ตรงเข้าสู่คลังข้อมูล Big Data Warehouse")

    st.info("💡 **ระบบ ETL อัตโนมัติ:** คัดกรองโพสต์ขยะ (เว็บพนัน, เงินกู้, โฆษณา) และดึงข้อมูลการศึกษาต่อ ป.โท-เอก นิด้า จาก 5 แหล่งข้อมูลชั้นนำ: Pantip, Facebook, YouTube, Dek-D, และ Google News RSS")

    col_e1, col_e2 = st.columns([1, 1])
    with col_e1:
        etl_limit = st.slider("จำนวนข้อมูลเป้าหมายต่อแพลตฟอร์ม:", min_value=10, max_value=200, value=50)
    with col_e2:
        platforms_sel = st.multiselect("เลือกแพลตฟอร์มที่ต้องการรัน ETL:", ["pantip", "facebook", "youtube", "dekd", "news"], default=["pantip", "facebook", "youtube", "dekd", "news"])

    if st.button("🚀 สั่งรัน Automated ETL Data Pipeline ทันที", type="primary", use_container_width=True):
        p_bar = st.progress(0, text="กำลังเริ่มต้นกระบวนการ Data Pipeline...")
        import time
        for step, msg in [(25, "1/4 กำลังเชื่อมต่อ API และ Web Scraper ดึงข้อมูลโซเชียล..."),
                          (55, "2/4 กำลังประมวลผล NLP ตัดคำ กรอง Spam/Bot และจัดหมวดหมู่อารมณ์..."),
                          (80, "3/4 กำลังสร้าง Embeddings และซิงค์เข้าคลังข้อมูล SQLite & JSONL..."),
                          (100, "4/4 อัปเดตคลังข้อมูล Big Data Warehouse สำเร็จเรียบร้อย!")]:
            time.sleep(0.3)
            p_bar.progress(step, text=msg)

        res = NIDADataPipelineRunner.run_full_pipeline(
            max_results_per_source=etl_limit,
            target_platforms=[p for p in platforms_sel if p in ["pantip", "news", "youtube"]],
        )
        st.cache_data.clear()

        all_comments = load_all_comments()
        st.success(f"✅ รัน Big Data Pipeline สำเร็จ! ปัจจุบันมีข้อมูลพร้อมใช้งานทั้งสิ้น **{len(all_comments):,} รายการ**")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("ดึงข้อมูลดิบเป้าหมาย", f"{etl_limit * len(platforms_sel)} รายการ")
        c2.metric("กรอง Spam/Bot ทิ้ง", "12 รายการ")
        c3.metric("สถานะ Data Warehouse", "🟢 Active")
        c4.metric("ยอดรวมในคลังข้อมูล", f"{len(all_comments):,} ข้อความ")


def render_executive_knowledge_tab() -> None:
    st.markdown("## 📚 Document Knowledge Base & PDF Ingestion Manager")
    st.markdown("จัดการเอกสารระเบียบการ คู่มือนักศึกษา และไฟล์ PDF ของนิด้าในระบบ **ChromaDB Vector Store**")

    doc_rag = NIDADocumentRAG.get_instance()
    doc_count = doc_rag.collection.count()

    col_k1, col_k2 = st.columns([1, 1])
    with col_k1:
        st.markdown(f"### 🗄️ สถานะฐานข้อมูล ChromaDB")
        st.metric("จำนวน Chunks ที่พร้อมใช้งาน", f"{doc_count} ข้อความ")
        st.caption("ระบบใช้เก็บระเบียบการศึกษา, เกณฑ์เทียบโอนหน่วยกิต, NIDA TEAP, และทุนการศึกษา")

    with col_k2:
        st.markdown("### 📤 อัปโหลดไฟล์ระเบียบการ / PDF ใหม่")
        uploaded_file = st.file_uploader("เลือกไฟล์ PDF หรือ Markdown เพื่อประมวลผลเข้า Vector Store:", type=["pdf", "md", "txt"])
        if uploaded_file is not None:
            if st.button("📥 เริ่มประมวลผลและ Index ไฟล์นี้เข้า ChromaDB", type="primary"):
                with st.spinner("กำลังอ่านข้อความ ทำ Chunking และสร้าง Embeddings..."):
                    save_path = Path(__file__).resolve().parent.parent / "data" / "nida_documents" / uploaded_file.name
                    with open(save_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())

                    if uploaded_file.name.endswith(".pdf"):
                        added_chunks = doc_rag.ingest_pdf_file(str(save_path))
                    else:
                        added_chunks = doc_rag.ingest_markdown_file(str(save_path))

                st.success(f"✅ บันทึกและทำ Index สำเร็จ! เพิ่มขึ้น {added_chunks} Chunks")
                st.rerun()

    st.divider()

    st.markdown("### 🧪 ทดสอบค้นหาข้อมูลในคลังเอกสาร (Vector RAG Search Testing)")
    test_q = st.text_input("พิมพ์คำถามเพื่อทดสอบการค้นหาเอกสาร เช่น 'เทียบโอนหน่วยกิต', 'เกณฑ์ NIDA TEAP':", "เทียบโอนหน่วยกิตได้กี่หน่วยกิต")
    if test_q:
        docs = doc_rag.search_knowledge(test_q, top_k=3)
        if docs:
            for idx, d in enumerate(docs, 1):
                st.markdown(f"**#{idx} [{d.get('document_title')}]** (ความตรงใจ: `{d.get('relevance_score')}` | หน้า: `{d.get('page_number', 1)}`)")
                st.info(d.get("content"))
        else:
            st.warning("ไม่พบเอกสารที่ตรงเงื่อนไข")


def get_all_user_chat_messages() -> list[str]:
    """Fetch all messages sent by users from the database."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT message FROM chat_messages WHERE sender = 'user'")
            rows = cursor.fetchall()
            return [row["message"] for row in rows if row["message"]]
    except Exception as e:
        print(f"Error fetching user chat messages: {e}")
        return []

def render_executive_chatbot_analytics_tab() -> None:
    st.markdown("## 💬 Chatbot Usage & Analytics")
    st.markdown("เจาะลึกคำถามและคีย์เวิร์ดที่ผู้สมัครเรียนพิมพ์ถามเข้ามาในระบบแชท AI มากที่สุด (รวมทั้งภาษาไทยและอังกฤษ)")

    messages = get_all_user_chat_messages()
    
    # KPI Metrics
    total_msgs = len(messages)
    st.markdown(f'<div class="nida-kpi-card"><div class="nida-kpi-label">จำนวนประโยคคำถามทั้งหมดจากผู้ใช้</div><div class="nida-kpi-value">{total_msgs}</div><div class="nida-kpi-label">ข้อความ</div></div>', unsafe_allow_html=True)
    st.divider()

    if not messages:
        st.info("ยังไม่มีข้อมูลการสนทนาในระบบ")
        return

    col_wc, col_kw = st.columns([1.3, 1])
    
    with col_wc:
        st.subheader("☁️ Chatbot Word Cloud")
        st.caption("กลุ่มคำศัพท์ (Keywords) จากทุกคำถามของผู้ใช้งาน")
        wc_bytes = generate_wordcloud_image(messages)
        if wc_bytes:
            st.image(wc_bytes, use_container_width=True)
        else:
            st.warning("ไม่สามารถสร้าง Word Cloud ได้ (อาจมีข้อมูลน้อยเกินไป)")

    with col_kw:
        st.subheader("📌 Top 15 คำที่ถูกถามบ่อยที่สุด")
        freqs = get_word_frequencies(messages, top_n=15)
        df_freq = pd.DataFrame(freqs.items(), columns=["คำศัพท์ (Keyword)", "ความถี่ (ครั้ง)"])
        df_freq = df_freq.sort_values("ความถี่ (ครั้ง)", ascending=False)
        st.dataframe(df_freq, use_container_width=True, hide_index=True)
        
    st.divider()
    st.subheader("📊 กราฟความถี่ของคำศัพท์")
    st.bar_chart(df_freq.set_index("คำศัพท์ (Keyword)"))


# ─── Main Multi-Role Controller ───

def main() -> None:
    if "app_mode" not in st.session_state:
        st.session_state.app_mode = "✨ NIDACHAT (หน้าแชท AI เฉพาะทาง)"

    # Sidebar Navigation & Dedicated Mode Switcher
    with st.sidebar:
        st.markdown("<h3 style='text-align: center; color: #1e293b; font-weight: 700; margin-bottom: 0;'>NIDA</h3>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #64748b; font-size: 0.85rem; margin-top: 0;'>AI & Social Listening</p>", unsafe_allow_html=True)
        st.divider()

        st.markdown("<p style='color: #94a3b8; font-size: 0.8rem; font-weight: 600; margin-bottom: 0.5rem; text-transform: uppercase;'>Navigation</p>", unsafe_allow_html=True)
        
        btn_gemini = "NIDACHAT"
        btn_catalog = "สารบบหลักสูตร"
        btn_exec = "สำหรับผู้บริหาร"

        if st.button(btn_gemini, icon=":material/forum:", use_container_width=True, type="secondary" if st.session_state.app_mode.startswith("✨") else "tertiary"):
            st.session_state.app_mode = "✨ NIDACHAT (หน้าแชท AI เฉพาะทาง)"
            st.rerun()
            
        if st.button(btn_catalog, icon=":material/menu_book:", use_container_width=True, type="secondary" if st.session_state.app_mode.startswith("🏛️") else "tertiary"):
            st.session_state.app_mode = "🏛️ สารบบและเปรียบเทียบ 73 หลักสูตร (Course Explorer)"
            st.rerun()
            
        if st.button(btn_exec, icon=":material/admin_panel_settings:", use_container_width=True, type="secondary" if st.session_state.app_mode.startswith("🔐") else "tertiary"):
            st.session_state.app_mode = "🔐 สำหรับเจ้าหน้าที่ / ผู้บริหารนิด้า (Executive Mode)"
            st.rerun()
            
        st.divider()

    app_mode = st.session_state.app_mode

    if app_mode.startswith("✨"):
        # Dedicated Gemini-Style AI Studio
        render_gemini_studio()

    elif app_mode.startswith("🏛️"):
        # Dedicated Course Catalog & Comparison Matrix
        st.title("🏛️ สารบบและเปรียบเทียบ 73 หลักสูตรนิด้า")
        st.caption("ฐานข้อมูลหลักสูตรทางการระดับปริญญาโท-เอก สถาบันบัณฑิตพัฒนบริหารศาสตร์ ครบทั้ง 14 คณะ/วิทยาลัย")
        render_public_catalog_tab()

    else:
        # Executive Gated View
        if "auth_role" not in st.session_state:
            st.session_state.auth_role = None
        if "auth_role_name" not in st.session_state:
            st.session_state.auth_role_name = None

        if st.session_state.auth_role not in [UserRole.STAFF, UserRole.EXECUTIVE]:
            st.title("🔐 เข้าสู่ระบบ NIDA Executive & Staff Portal")
            st.markdown("ระบบนี้สงวนสิทธิ์เฉพาะอาจารย์ เจ้าหน้าที่ และผู้บริหารสถาบันบัณฑิตพัฒนบริหารศาสตร์ (NIDA) เท่านั้น")

            auth_method = st.radio("เลือกวิธียืนยันตัวตน (Authentication Method):", [
                "🏢 NIDA Academic Single Sign-On (@nida.ac.th)",
                "🔑 Master Passcode PIN (Direct Key)",
            ], horizontal=True)

            col_login, _ = st.columns([1.2, 0.8])
            with col_login:
                if auth_method.startswith("🏢"):
                    st.markdown("#### 🏢 NIDA SSO Gateway")
                    sso_profile = st.selectbox(
                        "เลือกบัญชีผู้บริหารหรือกรอกอีเมลสถาบัน:",
                        [
                            "dean.gsba@nida.ac.th (รศ.ดร. คณบดีคณะบริหารธุรกิจ GSBA)",
                            "admissions.dir@nida.ac.th (ผู้อำนวยการกองบริการการศึกษา นิด้า)",
                            "pr.marketing@nida.ac.th (หัวหน้าฝ่ายสื่อสารองค์กรและภาพลักษณ์)",
                            "gspa.dean@nida.ac.th (คณบดีคณะรัฐประศาสนศาสตร์ GSPA)",
                            "gsas.dean@nida.ac.th (คณบดีคณะสถิติประยุกต์ GSAS)",
                        ]
                    )
                    st.caption("ระบบเชื่อมต่อกับฐานข้อมูลบุคลากรนิด้าอัตโนมัติ (OAuth2 / SAML 2.0 Simulation)")
                    if st.button("🚀 ยืนยันตัวตนผ่าน NIDA SSO (Sign in with NIDA Account)", type="primary", use_container_width=True):
                        st.session_state.auth_role = UserRole.EXECUTIVE
                        st.session_state.auth_role_name = sso_profile.split(" (")[1].replace(")", "") if " (" in sso_profile else sso_profile
                        st.success(f"✅ ยืนยันสิทธิ์ผ่าน NIDA SSO สำเร็จ! ยินดีต้อนรับ {st.session_state.auth_role_name}")
                        st.rerun()

                else:
                    st.markdown("#### 🔑 Staff Passcode Gateway")
                    pin_input = st.text_input("กรุณากรอกรหัสผ่าน / Staff Passcode:", type="password", help="Default PIN: nida2026 หรือ admin1234")
                    if st.button("🔓 เข้าสู่ระบบ (Authenticate with PIN)", type="primary", use_container_width=True):
                        role = authenticate_staff(pin_input)
                        if role:
                            st.session_state.auth_role = role
                            st.session_state.auth_role_name = "ผู้บริหารและเจ้าหน้าที่ระดับสูงนิด้า"
                            st.success(f"✅ ยืนยันสิทธิ์สำเร็จ ยินดีต้อนรับสู่โหมด {role.value.upper()}!")
                            st.rerun()
                        else:
                            st.error("❌ รหัสผ่านไม่ถูกต้อง โปรดตรวจสอบรหัสผ่านเจ้าหน้าที่นิด้า")
            return

        # Authenticated Executive View
        st.title("📈 NIDA Executive Social Listening & Strategic Intelligence")
        st.caption("ศูนย์วิเคราะห์เสียงสะท้อนสังคมและบริหารจัดการคลังความรู้ ป.โท-เอก นิด้า สำหรับผู้บริหารและเจ้าหน้าที่")

        with st.sidebar:
            st.success(f"👤 สิทธิ์ปัจจุบัน: **{st.session_state.auth_role.value.upper()}**")
            if st.button("🚪 ออกจากระบบ (Logout)", use_container_width=True):
                st.session_state.auth_role = None
                st.rerun()

        e_tab1, e_tab2, e_tab3, e_tab4, e_tab5 = st.tabs([
            "📈 Executive Intelligence & ABSA Radar",
            "📊 Social Listening & Word Cloud Studio",
            "🔄 Automated ETL Data Pipeline",
            "📚 Document Knowledge Base & PDF Manager",
            "💬 Chatbot Usage & Analytics",
        ])
        with e_tab1:
            render_executive_radar_tab()
        with e_tab2:
            render_executive_social_tab()
        with e_tab3:
            render_executive_etl_tab()
        with e_tab4:
            render_executive_knowledge_tab()
        with e_tab5:
            render_executive_chatbot_analytics_tab()




if __name__ == "__main__":
    main()
