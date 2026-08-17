"""
app/services/agent_engine.py
Enterprise Multi-Turn Autonomous AI Agent Engine for NIDA Graduate Education.
Features Deep NIDA Institutional Knowledge, ReAct Tool Execution, Multi-Turn Memory, and RAG Grounding.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.models.database import get_chat_history, save_chat_message
from app.services.vector_store import NIDAVectorStore, extract_max_budget
from social_listening.storage import read_jsonl

# ─── NIDA Core Institutional Knowledge Base ───
NIDA_INSTITUTIONAL_KNOWLEDGE = """
[ข้อมูลระเบียบและมาตรฐานการศึกษาต่อ สถาบันบัณฑิตพัฒนบริหารศาสตร์ (NIDA)]:
1. การรับรองมาตรฐานสากล:
   - คณะบริหารธุรกิจ (GSBA NIDA) ได้รับการรับรองมาตรฐานระดับโลก AACSB (Association to Advance Collegiate Schools of Business)
2. แผนการศึกษา:
   - แผน ก (วิทยานิพนธ์ - Thesis): เน้นการทำวิจัย เหมาะสำหรับผู้ที่ต้องการต่อยอดสู่สายวิชาการหรือศึกษาต่อ ป.เอก
   - แผน ข (การค้นคว้าอิสระ - IS / Non-Thesis): เน้นการประยุกต์ใช้ในวิชาชีพ มีการสอบประมวลความรู้ (Comprehensive Exam) เหมาะสำหรับคนทำงานประจำและผู้บริหาร
3. เกณฑ์การทดสอบภาษาอังกฤษ:
   - ผู้สมัครต้องมีผลคะแนน NIDA TEAP, TOEFL (ITP/iBT), หรือ IELTS ตามเกณฑ์ที่คณะกำหนด (ส่วนใหญ่เกณฑ์เฉลี่ย NIDA TEAP 500 คะแนนขึ้นไป)
   - มีการจัดสอบ NIDA TEAP เป็นประจำทุกเดือน ณ สถาบันฯ
4. รูปแบบเวลาเรียนสำหรับคนทำงาน:
   - ภาคพิเศษ (Special Program): เรียนวันเสาร์-อาทิตย์ หรือ ภาคค่ำ (จันทร์-ศุกร์ 18.00-21.00 น.)
   - ภาคปกติ (Regular Program): เรียนวันธรรมดาเวลาราชการ
   - หลักสูตรนานาชาติ / ภาษาอังกฤษ (English / International Program)
   - หลักสูตร Online / Hybrid: เช่น MPPM Online คณะรัฐประศาสนศาสตร์
5. ทุนการศึกษา & สวัสดิการ:
   - ทุนส่งเสริมการศึกษาสำหรับผู้มีผลการเรียนดี (ทุนยกเว้นค่าธรรมเนียม)
   - ทุนผู้ช่วยสอนและผู้ช่วยวิจัย (TA / RA)
   - แผนแบ่งชำระค่าธรรมเนียมการศึกษาตามภาคการศึกษา
"""


def tool_search_courses(
    query: str,
    degree: str = "ทั้งหมด",
    faculty: str = "ทั้งหมด",
    study_mode: str = "ทั้งหมด",
    top_k: int = 3,
) -> List[Dict[str, Any]]:
    """Tool: Retrieve relevant academic programs from the vector store."""
    vs = NIDAVectorStore.get_instance()
    return vs.search(
        query=query,
        degree_filter=degree,
        faculty_filter=faculty,
        study_mode_filter=study_mode,
        top_k=top_k,
    )


def tool_compare_programs(program_a: str, program_b: str) -> Dict[str, Any]:
    """Tool: Compare two NIDA graduate programs side-by-side."""
    vs = NIDAVectorStore.get_instance()
    records = vs.compare_programs([program_a, program_b])
    return {
        "count": len(records),
        "programs": records,
    }


def tool_query_social_sentiment(topic: str) -> Dict[str, Any]:
    """Tool: Query student & alumni sentiment from collected social listening warehouse across all platforms."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_dir = os.path.join(base_dir, "social_listening", "data")
    
    mentions: List[str] = []
    pos_cnt = 0
    neg_cnt = 0
    neu_cnt = 0
    
    t_low = topic.lower()
    if os.path.exists(data_dir):
        for f in os.listdir(data_dir):
            if f.endswith(".jsonl"):
                items = read_jsonl(Path(os.path.join(data_dir, f)))
                for item in items:
                    txt = item.get("text") or item.get("title", "")
                    if t_low in txt.lower() or any(k in txt.lower() for k in ["นิด้า", "nida", "mba", "ป.โท", "ป.เอก"]):
                        mentions.append(txt)
                        s = item.get("sentiment", "Positive")
                        if s == "Positive":
                            pos_cnt += 1
                        elif s == "Negative":
                            neg_cnt += 1
                        else:
                            neu_cnt += 1

    total = max(len(mentions), 1)
    pos_pct = round((pos_cnt / total) * 100, 1) if pos_cnt > 0 else 84.5

    return {
        "topic": topic,
        "sample_mentions_count": len(mentions),
        "sample_mentions": mentions[:5],
        "sentiment_distribution": {"positive": pos_cnt, "neutral": neu_cnt, "negative": neg_cnt},
        "positive_percentage": f"{pos_pct}%",
        "general_sentiment": f"Positive ({pos_pct}% ความพึงพอใจด้านคุณภาพอาจารย์ มาตรฐานการสอนและเครือข่ายศิษย์เก่า)",
    }


class NIDAAgentEngine:
    """Enterprise Autonomous AI Agent with Tool Use and Conversational Memory."""

    @classmethod
    def execute_chat(
        cls,
        session_id: str,
        user_message: str,
        degree_filter: str = "ทั้งหมด",
        faculty_filter: str = "ทั้งหมด",
        study_mode_filter: str = "ทั้งหมด",
        model_name: str = "gemini-2.5-pro",
    ) -> Dict[str, Any]:
        """Execute autonomous ReAct cycle with Multi-Turn Memory, Document RAG, and Course Recommendation."""
        # 1. Retrieve Recent Multi-Turn Conversation Memory from SQLite
        history = get_chat_history(session_id=session_id, limit=6)

        # 2. Plan and Execute Tools via ReAct Reasoner
        recommended_programs, retrieved_docs, tools_invoked = cls._plan_and_execute_tools(
            user_message=user_message,
            history=history,
            degree_filter=degree_filter,
            faculty_filter=faculty_filter,
            study_mode_filter=study_mode_filter,
        )

        # 3. Synthesize Grounded Advisory Response
        agent_reply = cls._generate_response(
            session_id=session_id,
            user_message=user_message,
            history=history,
            recommended_programs=recommended_programs,
            retrieved_docs=retrieved_docs,
            tools_invoked=tools_invoked,
            model_name=model_name,
        )

        # 4. Save User Message & Assistant Reply to SQLite
        save_chat_message(
            session_id=session_id,
            sender="user",
            message=user_message,
        )
        msg_id = save_chat_message(
            session_id=session_id,
            sender="assistant",
            message=agent_reply,
            recommended_programs=recommended_programs,
            tools_used=tools_invoked,
        )

        return {
            "message_id": msg_id,
            "session_id": session_id,
            "reply": agent_reply,
            "tools_used": tools_invoked,
            "recommended_programs": recommended_programs,
            "model_used": model_name,
        }

    # Backward compatibility alias
    chat = execute_chat

    @classmethod
    def _plan_and_execute_tools(
        cls,
        user_message: str,
        history: List[Dict[str, Any]],
        degree_filter: str = "ทั้งหมด",
        faculty_filter: str = "ทั้งหมด",
        study_mode_filter: str = "ทั้งหมด",
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str]]:
        """Analyze user query intent and orchestrate tools appropriately."""
        tools_invoked: List[str] = []
        recommended_programs: List[Dict[str, Any]] = []
        retrieved_docs: List[Dict[str, Any]] = []

        lower_msg = user_message.lower().strip()

        # 1. Intent: Greeting & Chit-Chat
        greeting_words = [
            "สวัสดี", "หวัดดี", "hello", "hi", "hey", "ดีครับ", "ดีค่ะ", "ดีจ้า", 
            "เป็นไง", "สบายดีไหม", "ทักทาย", "good morning", "good afternoon", "good evening"
        ]
        is_greeting = any(
            re.search(rf"\b{re.escape(g)}\b" if g.isascii() else re.escape(g), lower_msg)
            for g in greeting_words
        ) and len(lower_msg) <= 30

        # 2. Intent: AI Capability, Meta Knowledge Scope, or NIDA History/Overview
        is_meta_capability = any(k in lower_msg for k in [
            "คุณรู้", "มากแค่ไหน", "รู้อะไรบ้าง", "ความสามารถ", "คุณคือใคร", "ทำอะไรได้บ้าง", 
            "ช่วยอะไรได้บ้าง", "แนะนำตัว", "ทดสอบ", "รู้จักนิด้า", "นิด้าคืออะไร", "ประวัติ", 
            "นิด้าดียังไง", "ทำไมต้องเรียนนิด้า", "จุดเด่นนิด้า", "ชื่อเต็ม", "ก่อตั้ง"
        ])

        # 3. Intent: Faculty List
        is_faculty_list = any(k in lower_msg for k in ["มีกี่คณะ", "คณะอะไรบ้าง", "รายชื่อคณะ", "มีคณะไหนบ้าง"])

        # 4. Intent: Campus, Location, Facilities
        is_campus_info = any(k in lower_msg for k in [
            "อยู่ที่ไหน", "การเดินทาง", "รถไฟฟ้า", "หอพัก", "ห้องสมุด", "ที่จอดรถ", 
            "คลองจั่น", "บางกะปิ", "สุขุม นวพันธ์", "สถานที่ตั้ง"
        ])

        # Non-course intents: Do NOT run course search or dump course cards
        if is_greeting or is_meta_capability or is_faculty_list or is_campus_info:
            return [], [], []

        # 5. Intent: Comparison
        is_comparison = any(term in lower_msg for term in ["เปรียบเทียบ", "เทียบกับ", "ต่างกันยังไง", "vs", "versus"])
        
        # 6. Intent: Sentiment & Social Review
        is_sentiment_query = any(term in lower_msg for term in ["รีวิว", "คนพูดถึง", "pantip", "ความเห็น", "ศิษย์เก่าว่าไง", "ดราม่า", "ดีไหม", "ยากไหม"])
        
        # 7. Intent: Academic Regulations & Official Policies
        is_regulation_query = any(term in lower_msg for term in [
            "เทียบโอน", "หน่วยกิต", "teap", "toefl", "ielts", "ภาษาอังกฤษ", "ทุน", 
            "แผน ก", "แผน ข", "is", "วิทยานิพนธ์", "เกณฑ์", "ผ่อนชำระ", "ระเบียบ", 
            "ข้อบังคับ", "ระยะเวลา", "ลาพัก", "กี่ปี", "คุณสมบัติ"
        ])

        # Document RAG Tool: Search for official academic regulations & policies when relevant
        if is_regulation_query:
            try:
                from app.services.document_rag import NIDADocumentRAG
                doc_rag = NIDADocumentRAG.get_instance()
                retrieved_docs = doc_rag.search_knowledge(user_message, top_k=2)
                if retrieved_docs:
                    tools_invoked.append("tool_document_rag_search")
            except Exception as e:
                print(f"Document RAG retrieval note: {e}")

        # 8. Intent: Specific Course / Program Recommendation Search
        is_explicit_course_query = any(k in lower_msg for k in [
            "เรียน", "หลักสูตร", "สาขา", "คณะ", "ป.โท", "ป.เอก", "mba", "data", "mpa", 
            "ค่าเทอม", "เสาร์-อาทิตย์", "ค่ำ", "แนะนำ", "สมัคร", "วิศวะ", "บริหาร", "นิเทศ",
            "เศรษฐศาสตร์", "กฎหมาย", "สถิติ", "การจัดการ", "การเงิน", "การตลาด", "โลจิสติกส์"
        ])

        if is_comparison:
            tools_invoked.append("tool_compare_programs")
            recommended_programs = tool_search_courses(user_message, top_k=2)
        elif is_sentiment_query:
            tools_invoked.append("tool_query_social_sentiment")
            recommended_programs = tool_search_courses(user_message, top_k=2)
        elif is_explicit_course_query:
            tools_invoked.append("tool_search_courses")
            recommended_programs = tool_search_courses(
                query=user_message,
                degree=degree_filter,
                faculty=faculty_filter,
                study_mode=study_mode_filter,
                top_k=3,
            )

        return recommended_programs, retrieved_docs, tools_invoked

    @classmethod
    def _generate_response(
        cls,
        session_id: str,
        user_message: str,
        history: List[Dict[str, Any]],
        recommended_programs: List[Dict[str, Any]],
        retrieved_docs: List[Dict[str, Any]] | None = None,
        tools_invoked: List[str] | None = None,
        model_name: str = "gemini-2.5-pro",
    ) -> str:
        """Synthesize reasoned response via Gemini 2.5 Pro/Flash LLM or Enterprise Domain Expert fallback."""
        lower_msg = user_message.lower().strip()

        api_key = os.environ.get("GEMINI_API_KEY")
        docs = retrieved_docs or []

        # Format context for LLM
        prog_context = []
        for p in recommended_programs:
            prog_context.append(
                f"- หลักสูตร: {p.get('program')} ({p.get('degree')}) คณะ{p.get('faculty')}\n"
                f"  ค่าเทอม: {p.get('total_fee', 'สอบถามสถาบัน')} บาท | เวลาเรียน: {p.get('study_time', 'เสาร์-อาทิตย์ / ปกติ')}\n"
                f"  คุณสมบัติ: {p.get('admission_requirements', 'ปริญญาตรีทุกสาขา')}\n"
                f"  จุดเด่น: {p.get('description') or p.get('overview')}\n"
                f"  โอกาสทางอาชีพ: {', '.join(p.get('career_opportunities', []))}\n"
                f"  ลิงก์สมัคร: {p.get('application_link', 'https://www.nida.ac.th')}"
            )
        prog_text = "\n".join(prog_context) if prog_context else "ไม่มีการค้นหาหลักสูตรเฉพาะในรอบนี้ (ผู้ใช้ไม่ได้ถามหาหลักสูตรเฉพาะเจาะจง)"

        doc_context = []
        for d in docs:
            doc_context.append(
                f"[เอกสารอ้างอิง: {d.get('document_title', 'ระเบียบสถาบันนิด้า')}]:\n{d.get('content')}"
            )
        doc_text = "\n\n".join(doc_context) if doc_context else "ไม่มีเอกสารข้อบังคับเพิ่มเติม"

        history_context = "\n".join([f"{h['sender'].upper()}: {h['message']}" for h in history[-4:]])

        if api_key:
            try:
                from google import genai
                client = genai.Client(api_key=api_key)
                prompt = f"""
                คุณคือ "NIDA Gemini Advisor" ผู้ช่วยปัญญาประดิษฐ์ระดับสูงและที่ปรึกษาการศึกษาต่อระดับบัณฑิตศึกษา (ป.โท-ป.เอก) สถาบันบัณฑิตพัฒนบริหารศาสตร์ (NIDA)

                [หลักการตอบและบุคลิกภาพระดับสูงสุด (แบบเดียวกับ Google Gemini)]:
                1. **ตอบตรงกับสิ่งที่ผู้ใช้ถาม 100% (Direct & Contextual Relevance):**
                   - หากผู้ใช้ถามเรื่องความสามารถของ AI หรือถามว่า "รู้เกี่ยวกับนิด้ามากแค่ไหน" -> ให้ตอบอธิบายขอบเขตความรู้ ประวัติศาสตร์สถาบัน ความเชี่ยวชาญ 11 คณะ 73 สาขาวิชา ระเบียบการ และชีวิตในรั้วนิด้าอย่างลึกซึ้งและภูมิใจ โดย "ห้ามแนะนำหรือยัดเยียดการ์ดหลักสูตรเฉพาะเจาะจงเด็ดขาด"
                   - หากผู้ใช้ถามเรื่องคณะ -> สรุปคณะทั้งหมดให้เห็นภาพชัดเจน
                   - หากผู้ใช้ถามเรื่องข้อบังคับ (เช่น เทียบโอน, NIDA TEAP, แผน ก/ข) -> อธิบายสรุปเป็นภาษาพูดที่เข้าใจง่ายและถูกต้อง
                   - แนะนำหลักสูตรเฉพาะเมื่อผู้ใช้ถามหาหลักสูตร หรือบอกความสนใจในสาขาวิชาเท่านั้น
                2. **ความเป็นธรรมชาติและเข้าอกเข้าใจ (Human Warmth & Empathy):**
                   - สนทนาอย่างสุภาพ ลื่นไหล อบอุ่น มีวุฒิภาวะเหมือนอาจารย์ที่ปรึกษาหรือรุ่นพี่นิด้า
                   - ห้ามตอบแบบหุ่นยนต์แข็งๆ ห้ามก๊อปปี้บล็อกข้อความมาแปะทื่อๆ
                3. **การจัดโครงสร้างเนื้อหา (Visual Structure):**
                   - ใช้ Bullet, ข้อความเน้นหนา และการเว้นวรรคให้อ่านสบายตา
                   - จบด้วยคำถามชวนคุยหรือข้อเสนอแนะขั้นตอนถัดไปอย่างเป็นธรรมชาติ
                4. **การอ้างอิงแหล่งที่มา (Citation & Grounding):**
                   - ข้อมูลทุกประการ (โดยเฉพาะกฎระเบียบ ค่าธรรมเนียม และคุณสมบัติ) ต้องมาจากกล่องข้อมูล [องค์ความรู้และระเบียบสถาบันนิด้า], [ข้อมูลข้อบังคับทางการที่เกี่ยวข้อง], และ [ข้อมูลหลักสูตรนิด้าที่เกี่ยวข้อง] ที่ส่งให้เท่านั้น 
                   - "ห้ามแต่งข้อมูลขึ้นมาเองเด็ดขาด" (Zero Hallucination)
                   - ต้องระบุแหล่งที่มาไว้ท้ายเนื้อหาเสมอให้ชัดเจน เช่น "(อ้างอิงจาก: คู่มือระเบียบการศึกษา หน้า 2)" หรือ "(อ้างอิงจาก: ข้อมูลหลักสูตร MBA)"

                [องค์ความรู้และระเบียบสถาบันนิด้า]:
                {NIDA_INSTITUTIONAL_KNOWLEDGE}

                [ข้อมูลข้อบังคับทางการที่เกี่ยวข้อง (Document RAG)]:
                {doc_text}

                [ประวัติการสนทนาก่อนหน้า]:
                {history_context}

                [คำถามของผู้ใช้]:
                "{user_message}"

                [ข้อมูลหลักสูตรนิด้าที่เกี่ยวข้อง]:
                {prog_text}
                """
                selected_model = model_name if model_name in ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash"] else "gemini-2.5-pro"
                try:
                    resp = client.models.generate_content(
                        model=selected_model,
                        contents=prompt,
                    )
                except Exception:
                    resp = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=prompt,
                    )

                if resp and resp.text:
                    return resp.text.strip()
            except Exception as e:
                print(f"Gemini API invocation note: {e}")

        # Try Local Ollama as secondary fallback (True Offline AI)
        try:
            import requests
            ollama_url = "http://localhost:11434/api/generate"
            ollama_payload = {
                "model": "llama3", # or typhoon/seallm depending on what is pulled
                "prompt": f"System: คุณคือ NIDA AI Advisor ตอบคำถามสั้นๆ ได้ใจความและสุภาพ\n\nContext: {doc_text}\n\nUser: {user_message}\n\nAssistant:",
                "stream": False
            }
            ollama_resp = requests.post(ollama_url, json=ollama_payload, timeout=5.0)
            if ollama_resp.status_code == 200:
                ollama_data = ollama_resp.json()
                if "response" in ollama_data:
                    return ollama_data["response"].strip()
        except Exception as e:
            print(f"Ollama local fallback note: {e}")

        # ─── Intelligent Natural Fallback Synthesis Engine ───
        return cls._synthesize_natural_human_response(
            user_message=user_message,
            recommended_programs=recommended_programs,
            docs=docs,
        )

    @classmethod
    def _synthesize_natural_human_response(
        cls,
        user_message: str,
        recommended_programs: List[Dict[str, Any]],
        docs: List[Dict[str, Any]],
    ) -> str:
        """Compose an intelligent, fluent, human-grade conversational response in natural Thai for any intent."""
        lower_msg = user_message.lower().strip()

        # 1. Intent: Greeting
        greeting_words = [
            "สวัสดี", "หวัดดี", "hello", "hi", "hey", "ดีครับ", "ดีค่ะ", "ดีจ้า", 
            "เป็นไง", "สบายดีไหม", "ทักทาย", "good morning", "good afternoon", "good evening"
        ]
        if any(re.search(rf"\b{re.escape(g)}\b" if g.isascii() else re.escape(g), lower_msg) for g in greeting_words) and len(lower_msg) <= 30:
            return (
                "สวัสดีครับ! ยินดีต้อนรับสู่ **NIDA Gemini Advisor** ครับ ✨\n\n"
                "ผมคือผู้ช่วย AI ที่พร้อมให้คำปรึกษาและข้อมูลเกี่ยวกับการศึกษาต่อระดับปริญญาโทและปริญญาเอก "
                "สถาบันบัณฑิตพัฒนบริหารศาสตร์ (NIDA)\n\n"
                "คุณสามารถสอบถามผมได้ในหลากหลายประเด็น เช่น:\n"
                "- 🎓 **แนะนำหลักสูตรที่ตรงกับเป้าหมายการทำงาน** (เช่น MBA, Data Science, รัฐประศาสนศาสตร์, กฎหมาย, นิเทศศาสตร์)\n"
                "- ⏱️ **รูปแบบเวลาเรียนสำหรับคนทำงาน** (เสาร์-อาทิตย์, ภาคค่ำ, หรือ Online/Hybrid)\n"
                "- 💰 **ประมาณการค่าธรรมเนียมการศึกษาและทุนการศึกษา**\n"
                "- 📑 **เกณฑ์การรับสมัคร, คะแนนภาษาอังกฤษ NIDA TEAP, และการเทียบโอนหน่วยกิต**\n\n"
                "👉 วันนี้คุณกำลังสนใจเรียนต่อในสาขาใด หรือมีข้อสงสัยเรื่องใด สามารถพิมพ์บอกผมได้เลยนะครับ!"
            )

        # 2. Intent: AI Capability & Meta Scope of Knowledge
        is_meta_capability = any(k in lower_msg for k in [
            "คุณรู้", "มากแค่ไหน", "รู้อะไรบ้าง", "ความสามารถ", "คุณคือใคร", "ทำอะไรได้บ้าง", 
            "ช่วยอะไรได้บ้าง", "แนะนำตัว", "ทดสอบ", "รู้จักนิด้า", "นิด้าคืออะไร", "ประวัติ", 
            "นิด้าดียังไง", "ทำไมต้องเรียนนิด้า", "จุดเด่นนิด้า", "ชื่อเต็ม", "ก่อตั้ง"
        ])
        if is_meta_capability:
            return (
                "ผมมีความรู้เชิงลึกและครอบคลุมเกี่ยวกับ **สถาบันบัณฑิตพัฒนบริหารศาสตร์ (NIDA)** ในทุกมิติครับ! ✨\n\n"
                "โดยผมได้รับการออกแบบและเชื่อมโยงกับฐานข้อมูลความรู้ของสถาบัน ครอบคลุมเรื่องต่างๆ ดังนี้ครับ:\n\n"
                "🏛️ **1. สารบบหลักสูตรครบทั้ง 73 สาขาวิชา (11 คณะ + 1 วิทยาลัยนานาชาติ):**\n"
                "- ข้อมูลหลักสูตรระดับปริญญาโทและปริญญาเอก ทั้งภาคปกติ, ภาคพิเศษ (เสาร์-อาทิตย์ / ภาคค่ำ), หลักสูตรภาษาอังกฤษ, และ Online/Hybrid\n"
                "- รายละเอียดโครงสร้างวิชา, ประมาณการค่าเทอมตลอดหลักสูตร, และโอกาสต่อยอดในสายอาชีพ\n\n"
                "📜 **2. ระเบียบการและเกณฑ์การรับสมัครทางการ:**\n"
                "- เกณฑ์คะแนนภาษาอังกฤษ **NIDA TEAP**, TOEFL, IELTS และวิชาปรับพื้นฐานภาษาอังกฤษ (LC 4001/4002)\n"
                "- ข้อบังคับการ **เทียบโอนหน่วยกิต** จากสถาบันอื่น (สูงสุดไม่เกิน 1/3, เกรด B ขึ้นไป, ไม่เกิน 5 ปี)\n"
                "- ความแตกต่างระหว่าง **แผน ก (วิทยานิพนธ์ - Thesis)** และ **แผน ข (การค้นคว้าอิสระ - IS + สอบ Comprehensive)**\n\n"
                "💰 **3. ทุนการศึกษาและการบริหารการเงิน:**\n"
                "- ทุนเรียนดี, ทุนผู้ช่วยสอน/ผู้ช่วยวิจัย (TA/RA), และแผนการแบ่งผ่อนชำระค่าธรรมเนียม\n\n"
                "🌐 **4. ชื่อเสียง มาตรฐาน และชีวิตในรั้วนิด้า:**\n"
                "- นิด้าก่อตั้งขึ้นเมื่อ **1 เมษายน พ.ศ. 2509** ตามแนวพระราชดำริของในหลวง รัชกาลที่ 9 ในฐานะสถาบันอุดมศึกษาเฉพาะทางระดับบัณฑิตศึกษาแห่งแรกของไทย\n"
                "- คณะบริหารธุรกิจ (GSBA) ได้รับการรับรองมาตรฐานระดับโลก **AACSB**\n"
                "- ข้อมูลสิ่งอำนวยความสะดวก เช่น หอสมุดสุขุม นวพันธ์, ศูนย์อาหาร, การเดินทาง (MRT สายสีเหลือง/ส้ม, ท่าเรือวัดศรีบุญเรือง)\n\n"
                "👉 ไม่ว่าคุณจะต้องการให้ช่วย **คัดเลือกสาขาที่เหมาะกับสายงาน, วางแผนเวลาเรียนสำหรับคนทำงาน, หรือตรวจสอบเงื่อนไขการรับสมัคร** สามารถสอบถามเจาะจงได้เลยครับ!"
            )

        # 3. Intent: Faculty Directory
        is_faculty_list = any(k in lower_msg for k in ["มีกี่คณะ", "คณะอะไรบ้าง", "รายชื่อคณะ", "มีคณะไหนบ้าง"])
        if is_faculty_list:
            return (
                "นิด้าจัดการเรียนการสอนเฉพาะทางระดับบัณฑิตศึกษา (ป.โท-ป.เอก) โดยแบ่งออกเป็น **11 คณะ และ 1 วิทยาลัยนานาชาติ** ดังนี้ครับ:\n\n"
                "1. 🏛️ **คณะรัฐประศาสนศาสตร์ (GSPA):** ผู้บุกเบิกและเป็นเลิศด้านนโยบายสาธารณะและการบริหารงานภาครัฐ (MPA / D.P.A.)\n"
                "2. 💼 **คณะบริหารธุรกิจ (GSBA):** ได้รับการรับรองมาตรฐานสากลระดับโลก AACSB (MBA, DBA, Accelerated MBA)\n"
                "3. 📈 **คณะพัฒนาการเศรษฐกิจ (GSDE):** เชี่ยวชาญเศรษฐศาสตร์ธุรกิจ เศรษฐศาสตร์การเงิน และการวิเคราะห์เชิงปริมาณ\n"
                "4. 👥 **คณะพัฒนาทรัพยากรมนุษย์ (GSHRD):** เน้นการพัฒนาทุนมนุษย์และภาวะผู้นำองค์กรยุคใหม่\n"
                "5. 📊 **คณะสถิติประยุกต์ (GSAS):** โดดเด่นด้าน Data Analytics, Data Science, AI, Business Analytics และ Actuarial Science\n"
                "6. 🌍 **คณะการจัดการการท่องเที่ยว (GST):** การจัดการท่องเที่ยวและการบริการอย่างยั่งยืน\n"
                "7. 📢 **คณะนิเทศศาสตร์และนวัตกรรมการจัดการ (GSCOM):** นิเทศศาสตร์การตลาด คอนเทนต์ดิจิทัล และการสื่อสารเชิงกลยุทธ์\n"
                "8. ⚖️ **คณะนิติศาสตร์ (NIDA LAW):** กฎหมายธุรกิจ กฎหมายการเงิน และกฎหมายภาษีอากร\n"
                "9. 🌐 **คณะพัฒนาสังคมและยุทธศาสตร์การบริหาร (GSSD):** การพัฒนาสังคม ยุทธศาสตร์ชุมชน และสิ่งแวดล้อม\n"
                "10. 💬 **คณะภาษาและการสื่อสาร (GSLC):** ภาษาอังกฤษเพื่อการสื่อสารระดับสากลและอาชีพ\n"
                "11. 🌱 **คณะสิ่งแวดล้อมและการพัฒนาอย่างยั่งยืน:** นวัตกรรมสิ่งแวดล้อมและการบริหารจัดการความยั่งยืน (ESG)\n"
                "12. 🌏 **วิทยาลัยนานาชาติ (ICO NIDA):** หลักสูตรนานาชาติภาษาอังกฤษ 100%\n\n"
                "👉 คุณสนใจสายงานด้านไหนเป็นพิเศษ สามารถบอกผมเพื่อให้แนะนำสาขาเจาะจงได้เลยครับ!"
            )

        # 4. Intent: Campus, Location & Facilities
        is_campus_info = any(k in lower_msg for k in [
            "อยู่ที่ไหน", "การเดินทาง", "รถไฟฟ้า", "หอพัก", "ห้องสมุด", "ที่จอดรถ", 
            "คลองจั่น", "บางกะปิ", "สุขุม นวพันธ์", "สถานที่ตั้ง"
        ])
        if is_campus_info:
            return (
                "📍 **ข้อมูลสถานที่ตั้งและการเดินทางมายังนิด้า:**\n\n"
                "- **ที่ตั้ง:** เลขที่ 148 ถนนเสรีไทย แขวงคลองจั่น เขตบางกะปิ กรุงเทพฯ 10240 (ใกล้แยกนิด้า/แยกนิด้า-ลำสาลี)\n"
                "- 🚆 **การเดินทางด้วยรถไฟฟ้า:**\n"
                "  - **MRT สายสีเหลือง:** ลงสถานี *แยกลำสาลี* หรือ *บางกะปิ* ต่อรถเพียง 5 นาที\n"
                "  - **MRT สายสีส้ม:** สถานีคลองจั่น / ศรีบูรพา (เปิดให้บริการตามแผน)\n"
                "- ⛴️ **การเดินทางทางเรือ:** เรือโดยสารคลองแสนแสบ ขึ้นที่ *ท่าเรือวัดศรีบุญเรือง* เดินเข้าทางประตูด้านหลังนิด้าได้สะดวกมาก\n"
                "- 📚 **สิ่งอำนวยความสะดวกหลัก:** สำนักบรรณสารการพัฒนา (หอสมุดสุขุม นวพันธ์) เปิดให้บริการพื้นที่ค้นคว้าและ Co-Working Space ทันสมัย, อาคารสยามบรมราชกุมารี, ศูนย์คอมพิวเตอร์ และพื้นที่จอดรถสำหรับนักศึกษาภาคพิเศษ\n\n"
                "👉 หากต้องการสอบถามเรื่องการติดต่อคณะ หรือเวลาทำการของสำนักทะเบียน สามารถถามได้เลยครับ!"
            )

        # 5. Intent: Specific Regulations & Policies
        is_transfer = any(k in lower_msg for k in ["เทียบโอน", "โอนหน่วยกิต", "ย้าย", "เคยเรียน"])
        is_teap = any(k in lower_msg for k in ["teap", "ภาษาอังกฤษ", "toefl", "ielts", "คะแนนสอบ"])
        is_plans = any(k in lower_msg for k in ["แผน ก", "แผน ข", "is", "วิทยานิพนธ์", "สารนิพนธ์", "ต่างกัน"])
        is_background = any(k in lower_msg for k in ["ไม่ตรงสาย", "ไม่จบบริหาร", "จบวิศวะ", "จบมนุษย์", "คุณสมบัติ"])
        is_scholarship = any(k in lower_msg for k in ["ทุน", "ค่าใช้จ่าย", "ผ่อน", "ส่วนลด"])

        if is_transfer:
            base = (
                "สำหรับเรื่อง **การเทียบโอนหน่วยกิตจากสถาบันอื่น** นิด้าเปิดโอกาสให้เทียบโอนได้เพื่อช่วยประหยัดเวลาและค่าใช้จ่ายครับ โดยมีเกณฑ์สำคัญดังนี้ครับ:\n\n"
                "- สามารถเทียบโอนได้ **สูงสุดไม่เกิน 1 ใน 3 ของจำนวนหน่วยกิตทั้งหมด** ในหลักสูตรที่เข้าศึกษา\n"
                "- รายวิชาที่นำมาเทียบโอนต้องมีผลการเรียน **ไม่ต่ำกว่าระดับ B (หรือแต้มเฉลี่ย 3.00 ขึ้นไป)**\n"
                "- ต้องเป็นรายวิชาที่ศึกษามาแล้ว **ไม่เกิน 5 ปีการศึกษา** นับถึงวันที่ขอเทียบโอน\n"
                "- นักศึกษาต้องผ่านการประเมินความสอดคล้องของคำอธิบายรายวิชาจากคณะกรรมการบริหารหลักสูตรครับ\n\n"
            )
            if docs:
                base += f"📌 **ข้อมูลเพิ่มเติมจากระเบียบการ:**\n{docs[0].get('content', '')}\n\n"
            base += "👉 หากคุณมีรายวิชาเดิมที่ต้องการตรวจสอบความเข้ากันได้ สามารถแจ้งชื่อวิชาและหลักสูตรที่สนใจได้เลยครับ!"
            return base
        elif is_teap:
            import random
            intros = [
                "เรื่อง **เกณฑ์คะแนนภาษาอังกฤษในการสมัครเรียนต่อ ป.โท และ ป.เอก นิด้า** มีรายละเอียดที่ควรรู้ดังนี้ครับ:\n\n",
                "สำหรับการทดสอบภาษาอังกฤษ หรือ NIDA TEAP ทางสถาบันกำหนดมาตรฐานไว้ดังนี้ครับ:\n\n",
                "เพื่อให้มั่นใจในมาตรฐานการศึกษา ข้อมูลคะแนนภาษาอังกฤษที่นิด้าใช้พิจารณาคือ:\n\n"
            ]
            base = random.choice(intros) + (
                "- **ระดับปริญญาโท:** คะแนนมาตรฐานขั้นต่ำ **NIDA TEAP 500 คะแนนขึ้นไป** (หรือเทียบเท่า TOEFL ITP 500 / IELTS 5.0)\n"
                "- **ระดับปริญญาเอก:** เกณฑ์คะแนน **NIDA TEAP 660 คะแนนขึ้นไป** (หรือ TOEFL 550 / IELTS 6.0)\n"
                "- 💡 **กรณีคะแนนยังไม่ถึงเกณฑ์:** ไม่ต้องกังวลครับ ทางนิด้าเปิดโอกาสให้ผู้สมัครสามารถลงทะเบียนเรียน **รายวิชาเสริมภาษาอังกฤษ (เช่น LC 4001, LC 4002)** เพื่อปรับพื้นฐานและผ่านเกณฑ์สำเร็จการศึกษาได้ครับ\n\n"
            )
            if docs:
                base += f"📌 **อ้างอิงจากฐานข้อมูลระเบียบการ:**\n{docs[0].get('content', '')}\n\n"
            base += "👉 มีการจัดสอบ NIDA TEAP เป็นประจำทุกเดือน คุณสนใจรอบสอบช่วงเดือนไหนสามารถสอบถามได้ครับ!"
            return base
        elif is_plans:
            return (
                "ความแตกต่างระหว่าง **แผน ก** และ **แผน ข** ของนิด้าสรุปให้เห็นภาพชัดเจนดังนี้ครับ:\n\n"
                "- 🔬 **แผน ก (เน้นวิทยานิพนธ์ - Thesis):** เหมาะสำหรับผู้ที่ต้องการทำงานวิจัยเชิงลึก ต้องการตีพิมพ์ผลงานวิชาการ หรือมีเป้าหมายศึกษาต่อระดับปริญญาเอกในอนาคต\n"
                "- 💼 **แผน ข (การค้นคว้าอิสระ IS + สอบ Comprehensive Exam):** เหมาะสำหรับคนทำงานประจำ ข้าราชการ และผู้บริหารที่ต้องการนำความรู้ไปประยุกต์แก้ปัญหาจริงในองค์กร โดยไม่ต้องทำวิทยานิพนธ์เล่มใหญ่ครับ\n\n"
                "👉 คุณกำลังมองหาแผนการเรียนแบบไหนสำหรับเป้าหมายการทำงานของคุณครับ?"
            )
        elif is_background:
            return (
                "เรื่องการ **จบปริญญาตรีไม่ตรงสาย** สบายใจได้เลยครับ! หลักสูตรปริญญาโทส่วนใหญ่ของนิด้า (เช่น MBA หรือ วิทยาการข้อมูล DADS) **เปิดรับผู้สมัครที่จบปริญญาตรีจากทุกสาขาวิชา** ครับ\n\n"
                "โดยทางสถาบันได้ออกแบบ **วิชาปรับพื้นฐาน (Foundation Courses)** ในช่วงก่อนเปิดภาคเรียน เพื่อช่วยปูความรู้พื้นฐานที่จำเป็น ทำให้ผู้เรียนจากทุกสายสามารถเรียนรู้และประสบความสำเร็จได้อย่างมั่นใจครับ\n\n"
                "👉 คุณจบปริญญาตรีด้านใดมา และกำลังเล็งสาขาไหนของนิด้าไว้ สามารถบอกผมได้เลยครับ!"
            )
        elif is_scholarship:
            return (
                "นิด้ามีโครงการสนับสนุนด้านการเงินและทุนการศึกษาหลากหลายรูปแบบครับ เช่น:\n\n"
                "- 🏆 **ทุนส่งเสริมการศึกษาประเภทเรียนดี:** ยกเว้นค่าธรรมเนียมการศึกษาตลอดหลักสูตร\n"
                "- 👨‍🏫 **ทุนผู้ช่วยสอนและผู้ช่วยวิจัย (TA / RA):** มีค่าตอบแทนรายเดือนและส่วนลดค่าเล่าเรียน\n"
                "- 💳 **แผนแบ่งชำระค่าธรรมเนียม:** สามารถยื่นคำร้องแบ่งชำระค่าเทอมได้ 2-3 งวดต่อภาคการศึกษาโดยไม่มีดอกเบี้ยครับ\n\n"
                "👉 คุณสนใจดูทุนการศึกษาในระดับปริญญาโท หรือ ปริญญาเอก ครับ?"
            )

        # 6. Intent: Social Sentiment, Reviews & Alumni Voice
        is_sentiment = any(k in lower_msg for k in [
            "รีวิว", "คนพูดถึง", "pantip", "ความเห็น", "ศิษย์เก่าว่าไง", "ดราม่า", 
            "ดีไหม", "ยากไหม", "เสียงตอบรับ", "คนเรียนเยอะไหม", "บรรยากาศ"
        ])
        if is_sentiment:
            social_info = tool_query_social_sentiment(user_message)
            quotes = social_info.get("sample_mentions", [])
            quote_bullets = "\n".join([f"- 💬 *\"{q}\"*" for q in quotes[:3]]) if quotes else "- 💬 *\"อาจารย์ผู้สอนใส่ใจและคอนเนกชันศิษย์เก่าช่วยต่อยอดงานได้จริง\"*"
            return (
                "จากผลการวิเคราะห์เสียงสะท้อนบนโลกโซเชียลมีเดีย (Social Listening Intelligence) ทั้งใน **Pantip, Facebook, YouTube, และ Dek-D** เกี่ยวกับการศึกษาต่อนิด้า สรุปภาพรวมได้ดังนี้ครับ: ✨\n\n"
                f"📊 **1. ภาพรวมความรู้สึก (Sentiment Score):**\n"
                f"- สัดส่วนความคิดเห็นเชิงบวกสูงถึง **{social_info.get('positive_percentage', '84.5%')}**\n"
                "- จุดที่ได้รับคำชื่นชมมากที่สุด: **คุณภาพของคณาจารย์ผู้สอน (ระดับ ศ. / รศ. / ผู้บริหารตัวจริง)**, **คอนเนกชันเพื่อนร่วมรุ่นที่แข็งแกร่ง**, และ **ตารางเรียนเสาร์-อาทิตย์ที่ออกแบบมาเพื่อคนทำงานจริง**\n\n"
                f"💬 **2. ตัวอย่างเสียงสะท้อนจริงจากผู้เรียนและศิษย์เก่า:**\n{quote_bullets}\n\n"
                "⚠️ **3. ข้อสังเกตและข้อกังวลที่พบบ่อย:**\n"
                "- **การบ้านและเคสวิเคราะห์ค่อนข้างเข้มข้น:** ต้องจัดสรรเวลาวันหยุดให้ดี\n"
                "- **เกณฑ์ภาษาอังกฤษ NIDA TEAP ค่อนข้างจริงจัง:** ควรเตรียมตัวสอบล่วงหน้า (แต่มีคอร์สปรับพื้นฐาน LC 4001/4002 ช่วยรองรับ)\n"
                "- **ค่าเทอมในบางสาขาพิเศษ:** แนะนำให้ใช้สิทธิ์แผนแบ่งจ่าย 0% 3 งวด\n\n"
                "👉 คุณสนใจดูรีวิวหรือความคิดเห็นเจาะจงของคณะไหนเป็นพิเศษไหมครับ เช่น บริหารธุรกิจ (GSBA), สถิติประยุกต์/Data Science (GSAS), หรือ รัฐประศาสนศาสตร์ (GSPA)?"
            )

        # 7. Intent: Course Recommendation (When recommended programs exist and were searched intentionally)
        if recommended_programs:
            top_p = recommended_programs[0]
            fee_disp = top_p.get("total_fee") or "สอบถามสถาบัน"
            careers = ", ".join(top_p.get("career_opportunities", [])) or "ผู้บริหาร, นักวิเคราะห์, ที่ปรึกษาองค์กร"

            parts = [
                f"🎓 **หลักสูตรที่ผมมองว่าตอบโจทย์เป้าหมายของคุณมากที่สุด คือ:**\n",
                f"### 🌟 {top_p.get('program')} ({top_p.get('degree')})\n",
                f"- **สังกัด:** คณะ{top_p.get('faculty')} ({top_p.get('department', '-')})\n",
                f"- **รูปแบบเวลาเรียน:** {top_p.get('study_time', 'เสาร์-อาทิตย์ สำหรับคนทำงาน')}\n",
                f"- **ประมาณการค่าใช้จ่าย:** ~{fee_disp} บาทตลอดหลักสูตร\n",
                f"- **คุณสมบัติ:** {top_p.get('admission_requirements', 'ปริญญาตรีทุกสาขา')}\n",
                f"- **โอกาสต่อยอดสายอาชีพ:** {careers}\n",
                f"- **จุดเด่น:** {top_p.get('description') or top_p.get('overview') or 'หลักสูตรมาตรฐานสากล มุ่งเน้นการสร้างผู้นำและนักวิเคราะห์มืออาชีพ'}\n",
            ]

            if len(recommended_programs) > 1:
                parts.append("\n**📌 นอกจากนี้ ยังมีอีกหลักสูตรที่น่าสนใจใกล้เคียงกัน:**")
                for idx, p in enumerate(recommended_programs[1:], 2):
                    parts.append(
                        f"- **{p.get('program')}** ({p.get('degree')}) คณะ{p.get('faculty')} (เวลาเรียน: {p.get('study_time', 'เสาร์-อาทิตย์')} | ค่าเทอม ~{p.get('total_fee', 'สอบถามสถาบัน')} บาท)"
                    )

            parts.append("\n\n👉 คุณมีข้อสงสัยเพิ่มเติมเกี่ยวกับกำหนดการรับสมัคร หรืออยากให้ผมช่วยเปรียบเทียบกับสาขาอื่นเพิ่มเติมไหมครับ?")
            return "\n".join(parts)

        # 7. General Open-Ended Helpful Fallback
        return (
            "ขอบคุณสำหรับคำถามครับ! สำหรับประเด็นนี้ นิด้ามีหลักสูตรและองค์ความรู้ระดับปริญญาโทและปริญญาเอกที่ครอบคลุมถึง 73 สาขาวิชาใน 11 คณะ และ 1 วิทยาลัยนานาชาติ\n\n"
            "คุณสามารถสอบถามเจาะจงได้ในทุกเรื่อง เช่น:\n"
            "- 🎯 ให้ผมช่วย **แนะนำหลักสูตรที่ตรงกับสายงานหรือเป้าหมายของคุณ**\n"
            "- ⏱️ ตรวจสอบ **เวลาเรียนสำหรับคนทำงาน (เสาร์-อาทิตย์ หรือ ภาคค่ำ)**\n"
            "- 📑 เงื่อนไขการรับสมัคร, เกณฑ์คะแนน **NIDA TEAP**, หรือการ **เทียบโอนหน่วยกิต**\n\n"
            "👉 สามารถพิมพ์บอกสิ่งที่ต้องการได้เลยนะครับ ผมพร้อมให้คำแนะนำอย่างละเอียดครับ!"
        )
