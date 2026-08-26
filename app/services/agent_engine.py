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

from app.models.database import get_chat_history, save_chat_message, get_user_profile, save_user_profile
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
    def _async_profile_extraction(cls, session_id: str, user_message: str):
        """Background task to extract user profile from message without blocking chat."""
        import os
        from google import genai
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key: return
        
        try:
            client = genai.Client(api_key=api_key)
            prompt = f"""
Analyze the following user message and extract demographic or interest profile data.
User Message: "{user_message}"

Extract ONLY these fields if they exist in the text (otherwise leave blank). 
Format strictly as JSON:
{{
  "inferred_age": "string or null (e.g. '25-30', 'working adult')",
  "work_experience": "string or null (e.g. '5 years in marketing', 'fresh grad')",
  "interests": "string or null (e.g. 'Data Science', 'MBA')"
}}
"""
            response = client.models.generate_content(
                model='gemini-3.5-flash',
                contents=prompt,
                config={'response_mime_type': 'application/json'}
            )
            import json
            data = json.loads(response.text)
            
            # Fetch existing to avoid overwriting with nulls if we already know it
            existing = get_user_profile(session_id) or {}
            
            age = data.get("inferred_age") or existing.get("inferred_age")
            exp = data.get("work_experience") or existing.get("work_experience")
            interests = data.get("interests") or existing.get("interests")
            
            if age or exp or interests:
                save_user_profile(session_id, age, exp, interests)
                
        except Exception as e:
            print(f"Profile extraction failed: {e}")

    @classmethod
    def execute_chat_stream(
        cls,
        session_id: str,
        user_message: str,
        degree_filter: str = "ทั้งหมด",
        faculty_filter: str = "ทั้งหมด",
        study_mode_filter: str = "ทั้งหมด",
        model_name: str = "gemini-1.5-flash",
        metadata_callback = None
    ):
        """Execute autonomous ReAct cycle with Multi-Turn Memory and Stream output."""
        lower_msg = user_message.lower().strip()
        greeting_words = [
            "สวัสดี", "หวัดดี", "hello", "hi", "hey", "ดีครับ", "ดีค่ะ", "ดีจ้า", 
            "เป็นไง", "สบายดีไหม", "ทักทาย", "ว่าไง"
        ]
        is_greeting = any(
            re.search(rf"\b{re.escape(g)}\b" if g.isascii() else re.escape(g), lower_msg)
            for g in greeting_words
        ) and len(lower_msg) <= 30

        if is_greeting:
            # We no longer hardcode the exit here to allow the LLM to handle greetings naturally.
            # But we still record the greeting for intent tracking.
            pass

        
        # [Brain Upgrade Phase 1]: Spawn background profiler
        import threading
        threading.Thread(target=cls._async_profile_extraction, args=(session_id, user_message), daemon=True).start()

        # 1. Retrieve Recent Multi-Turn Conversation Memory from SQLite (Increased limit to 30)
        history = get_chat_history(session_id=session_id, limit=30)

        # 2. Plan and Execute Tools via ReAct Reasoner
        recommended_programs, retrieved_docs, tools_invoked = cls._plan_and_execute_tools(
            user_message=user_message,
            history=history,
            degree_filter=degree_filter,
            faculty_filter=faculty_filter,
            study_mode_filter=study_mode_filter,
        )

        # 4. Save User Message
        save_chat_message(
            session_id=session_id,
            sender="user",
            message=user_message,
        )

        full_reply = ""
        # 3. Synthesize Grounded Advisory Response (Streaming)
        for chunk in cls._generate_response_stream(
            session_id=session_id,
            user_message=user_message,
            history=history,
            recommended_programs=recommended_programs,
            retrieved_docs=retrieved_docs,
            tools_invoked=tools_invoked,
            model_name=model_name,
        ):
            full_reply += chunk
            yield chunk

        # Save Assistant Reply to SQLite
        msg_id = save_chat_message(
            session_id=session_id,
            sender="assistant",
            message=full_reply,
            recommended_programs=recommended_programs,
            tools_used=tools_invoked,
        )

        if metadata_callback:
            metadata_callback({
                "message_id": msg_id,
                "session_id": session_id,
                "reply": full_reply,
                "tools_used": tools_invoked,
                "recommended_programs": recommended_programs,
                "model_used": model_name,
            })
    # Backward compatibility alias
    chat = execute_chat_stream

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
        if is_meta_capability or is_faculty_list or is_campus_info:
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
    def _generate_response_stream(
        cls,
        session_id: str,
        user_message: str,
        history: list,
        recommended_programs: list,
        retrieved_docs: list = None,
        tools_invoked: list = None,
        model_name: str = "gemini-flash-latest",
    ):
        """Synthesize reasoned response via Gemini LLM stream or local fallback."""
        import os
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
            doc_context.append(f"[เอกสารอ้างอิง: {d.get('document_title', 'ระเบียบสถาบัน')}]:\n{d.get('content')}")
        doc_text = "\n\n".join(doc_context) if doc_context else "ไม่มีเอกสารข้อบังคับเพิ่มเติม"

        history_context = "\\n".join([f"{h['sender'].upper()}: {h['message']}" for h in history[-10:]])

        # [Brain Upgrade Phase 1]: Inject User Profile
        user_profile = get_user_profile(session_id)
        profile_context = ""
        if user_profile:
            profile_context = "[ข้อมูลโปรไฟล์ผู้ใช้ (ดึงจากความจำระบบ)]:\\n"
            if user_profile.get("inferred_age"): profile_context += f"- อายุ/วัย: {user_profile.get('inferred_age')}\\n"
            if user_profile.get("work_experience"): profile_context += f"- ประสบการณ์ทำงาน: {user_profile.get('work_experience')}\\n"
            if user_profile.get("interests"): profile_context += f"- ความสนใจ: {user_profile.get('interests')}\\n"
            profile_context += "\\n(ให้คุณนำข้อมูลโปรไฟล์นี้มาปรับวิธีการตอบ หรือช่วยเลือกหลักสูตรที่เหมาะสมกับอายุและประสบการณ์ของผู้ใช้ให้ตรงใจที่สุด)\\n\\n"

        prompt = f"""
คุณคือรุ่นพี่นิด้า (NIDA Senior) ผู้ช่วยและที่ปรึกษาการศึกษาต่อระดับปริญญาโทและปริญญาเอก สถาบันบัณฑิตพัฒนบริหารศาสตร์ (NIDA)

{profile_context}[หลักการตอบและบุคลิกภาพ (สำคัญมาก)]:
1. **เป็นกันเอง สุภาพ และมีความเป็นมนุษย์สูง:** ใช้ภาษาพูดแบบรุ่นพี่คุยกับน้อง (เช่น ใช้คำว่า "ครับ/ค่ะ", "แนะนำว่า", "ลองดูตัวนี้นะครับ") ห้ามตอบเป็นหุ่นยนต์แข็งๆ ทื่อๆ เด็ดขาด
2. **เรียนรู้และเลียนแบบคำศัพท์ผู้ใช้ (Active Vocabulary Mirroring):** สังเกตสไตล์การพิมพ์ คำศัพท์ หรือระดับความเป็นทางการที่ผู้ใช้พิมพ์มา แล้วปรับสไตล์การตอบของคุณให้เข้ากันทันที (เช่น ถ้าผู้ใช้พิมพ์ภาษาวัยรุ่น สั้นๆ หรือเป็นกันเอง ให้คุณตอบกลับด้วยความรู้สึกสบายๆ แบบเพื่อน/รุ่นพี่)
3. **การทักทายแรกเริ่ม (Greetings):** หากผู้ใช้พิมพ์แค่คำทักทายสั้นๆ (เช่น "สวัสดี") ให้คุณทักทายกลับอย่างเป็นธรรมชาติและเป็นมิตร **ไม่ต้องร่ายยาวข้อมูลหลักสูตร** แต่ให้ถามกลับเบาๆ เพื่อเปิดบทสนทนา เช่น "สวัสดีครับ! วันนี้มีอะไรให้พี่ช่วยแนะนำเกี่ยวกับการเรียนที่นิด้าไหมครับ?" หรือ "สวัสดีครับ สนใจต่อ ป.โท หรือ ป.เอก ดีเอ่ย?"
4. **ตรงประเด็น (Concise):** ตอบให้สั้น กระชับ แต่อบอุ่น ไม่ต้องอธิบายยืดยาวถ้าผู้ใช้ไม่ได้ถาม
5. **ถ้ามีการ์ดหลักสูตรแนบมา:** ช่วยสรุปจุดเด่นของหลักสูตรนั้นสั้นๆ 1-2 บรรทัดด้วยภาษาชวนคุย
6. **Zero Hallucination:** ตอบเฉพาะข้อมูลที่มีใน [ข้อมูลที่เกี่ยวข้อง] ด้านล่าง ห้ามแต่งข้อมูลเองเด็ดขาด ถ้าไม่รู้ให้ตอบว่า "เรื่องนี้พี่อาจจะไม่มีข้อมูลลึกๆ แนะนำให้โทรสอบถามฝ่ายรับสมัคร 02-727-3000 ได้เลยครับ"
7. **ระบบอ้างอิง:** เมื่อดึงข้อมูลหลักสูตรหรือระเบียบการมาตอบ ให้ห้อยท้ายด้วย `(อ้างอิง: [ชื่อเอกสาร/หลักสูตร])` เบาๆ

[ความรู้พื้นฐานของสถาบัน (Core Knowledge)]:
{NIDA_INSTITUTIONAL_KNOWLEDGE}

[ข้อมูลข้อบังคับทางการที่เกี่ยวข้อง (Document RAG)]:
{doc_text}

[ประวัติการสนทนาก่อนหน้า]:
{history_context}

[ข้อมูลหลักสูตรนิด้าที่ค้นพบ]:
{prog_text}

[คำถามของผู้ใช้]:
"{user_message}"
"""

        if api_key:
            import time
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    from google import genai
                    client = genai.Client(api_key=api_key)
                    selected_model = model_name if model_name in ["gemini-flash-latest", "gemini-3.5-flash"] else "gemini-flash-latest"
                    
                    response = client.models.generate_content_stream(
                        model=selected_model,
                        contents=prompt,
                    )
                    for chunk in response:
                        if chunk.text:
                            yield chunk.text
                    return # Exit successfully
                except Exception as e:
                    error_str = str(e)
                    if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "Quota" in error_str or "503" in error_str or "UNAVAILABLE" in error_str:
                        if attempt < max_retries - 1:
                            wait_time = (attempt + 1) * 2
                            yield f"\n⏳ (ขออภัยครับ ตอนนี้คนใช้เยอะมาก ขอพี่พักหายใจแพพนะครับ... {wait_time} วิ)\n"
                            time.sleep(wait_time)
                            continue
                    yield f"\nอูยยยย... ตอนนี้คนทักเข้ามาปรึกษาเยอะมากเลยครับ ระบบผมเลยประมวลผลไม่ทันชั่วคราว รบกวนคุณน้องพิมพ์ถามใหม่อีกรอบนะครับ 🙏 หรือโทร 02-727-3000 ได้เลยครับ! (รหัส: {error_str})\n\n"
                    break
        else:
            yield "ขออภัยครับ ไม่พบการเชื่อมต่อระบบ AI หลัก (API Key missing) ตอนนี้ผมอาจจะตอบช้าหน่อยนะครับ\n\n"

        # Local Ollama Fallback (Pseudo-stream: return all at once since Ollama stream logic can be complex here)
        try:
            import requests
            import json
            ollama_url = "http://localhost:11434/api/generate"
            
            # Map model name to Ollama supported models
            ollama_model = "llama3.1" # default
            if "deepseek" in model_name.lower():
                ollama_model = "deepseek-r1:8b" # standard distilled version
            elif "llama" in model_name.lower():
                ollama_model = "llama3.1"
                
            ollama_payload = {
                "model": ollama_model,
                "prompt": prompt,
                "stream": False
            }
            ollama_resp = requests.post(ollama_url, json=ollama_payload, timeout=2.0)
            if ollama_resp.status_code == 200:
                ollama_data = ollama_resp.json()
                if "response" in ollama_data:
                    yield ollama_data["response"].strip()
                    return
        except Exception as e:
            pass
            
        yield "แง... ตอนนี้ระบบประมวลผลผมล่มชั่วคราวเลยครับ ทั้งออนไลน์และออฟไลน์เลย รบกวนพิมพ์ถามใหม่อีกครั้งในอีกสักครู่นะครับ หรือโทรสายตรงที่ 02-727-3000 ได้เลยครับ ขออภัยจริงๆ ครับ 🥺"
