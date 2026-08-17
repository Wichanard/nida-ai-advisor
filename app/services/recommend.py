import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from pythainlp.tokenize import word_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

BASE_DIR = Path(__file__).resolve().parents[2]
COURSES_PATH = BASE_DIR / "data" / "courses.json"


def extract_max_budget(user_input: str) -> Optional[float]:
    """Extract maximum budget (in THB) from user's natural language input.
    Supports: '1 แสน', '50,000 บาท', '80000', '1.5 แสน', 'ไม่เกิน 2 หมื่น'
    """
    if not user_input:
        return None
    # Match Thai numeral words: แสน (100k), หมื่น (10k), ล้าน (1M)
    m_million = re.search(r'(\d+(?:\.\d+)?)\s*ล้าน', user_input)
    if m_million:
        return float(m_million.group(1)) * 1_000_000.0
    m_lakh = re.search(r'(\d+(?:\.\d+)?)\s*แสน', user_input)
    if m_lakh:
        return float(m_lakh.group(1)) * 100_000.0
    m_tenk = re.search(r'(\d+(?:\.\d+)?)\s*หมื่น', user_input)
    if m_tenk:
        return float(m_tenk.group(1)) * 10_000.0
    # Match explicit numeric amounts: '50,000' or '100000'
    m_num = re.search(r'(\d{1,3}(?:,\d{3})+|\d{5,7})', user_input)
    if m_num:
        return float(m_num.group(1).replace(',', ''))
    return None


def parse_tuition_fee(fee_val: Any) -> Optional[float]:
    """Parse a tuition fee value from courses.json into a float (THB)."""
    if fee_val is None:
        return None
    cleaned = re.sub(r'[^\d]', '', str(fee_val))
    return float(cleaned) if cleaned else None


def thai_tokenizer(text: str) -> List[str]:
    """Thai word tokenizer for TF-IDF Vectorizer."""
    if not text:
        return []
    return [t.strip().lower() for t in word_tokenize(text, engine="newmm") if len(t.strip()) > 1]


def load_programs() -> List[Dict[str, Any]]:
    """Load and flatten all academic programs from data/courses.json."""
    if not COURSES_PATH.exists():
        return []

    with COURSES_PATH.open("r", encoding="utf-8-sig") as f:
        faculties = json.load(f)

    programs: List[Dict[str, Any]] = []
    for faculty in faculties:
        faculty_name = faculty.get("faculty", "")
        for department in faculty.get("departments", []):
            department_name = department.get("department", "")
            for program in department.get("programs", []):
                # Build rich search document
                search_terms = [
                    faculty_name,
                    department_name,
                    program.get("program", ""),
                    program.get("degree", ""),
                    program.get("description", ""),
                    program.get("overview", ""),
                    " ".join(program.get("keywords", [])),
                    " ".join(program.get("career_opportunities", [])),
                    program.get("study_time", ""),
                    program.get("language", ""),
                ]
                search_text = " ".join([str(t) for t in search_terms if t]).strip()

                programs.append({
                    "faculty": faculty_name,
                    "department": department_name,
                    "search_text": search_text,
                    **program,
                })

    return programs


def generate_ai_reasoning(user_input: str, program: Dict[str, Any]) -> str:
    """Generate a personalized AI explanation of why this program fits the user's specific prompt."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            prompt_text = f"""
            คุณเป็นที่ปรึกษาการศึกษาต่อระดับปริญญาโท-เอก สถาบันบัณฑิตพัฒนบริหารศาสตร์ (NIDA)
            ผู้ใช้สอบถามว่า: "{user_input}"
            หลักสูตรที่แนะนำคือ: {program.get('program')} ({program.get('degree')}) คณะ{program.get('faculty')}
            คำอธิบายหลักสูตร: {program.get('description') or program.get('overview')}
            รูปแบบการเรียน: {program.get('study_time')}

            จงเขียนสรุปสั้นๆ 2-3 ประโยค ภาษาไทย อธิบายว่า "ทำไมหลักสูตรนี้จึงตอบโจทย์ผู้ใช้รายนี้มากที่สุด" (เน้นประโยชน์ คอนเนกชัน และความคุ้มค่า)
            """
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt_text,
            )
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            print(f"Gemini API info: {e}")

    # Intelligent Thai Rule-Based Synthesis Fallback
    prog_title = program.get("program", "")
    faculty = program.get("faculty", "")
    degree = program.get("degree", "")
    study_time = program.get("study_time") or "ภาคค่ำ/เสาร์-อาทิตย์"
    careers = ", ".join(program.get("career_opportunities", [])[:3]) or "ผู้บริหารและผู้เชี่ยวชาญระดับสูง"

    reasons: List[str] = []
    if "บริหาร" in user_input or "ธุรกิจ" in user_input or "MBA" in user_input:
        reasons.append("เน้นการพัฒนาทักษะการบริหารเชิงกลยุทธ์และการตัดสินใจในระดับผู้บริหารสากล")
    elif "data" in user_input.lower() or "วิเคราะห์" in user_input or "สถิติ" in user_input or "ai" in user_input.lower():
        reasons.append("เน้นทักษะการวิเคราะห์ข้อมูลขนาดใหญ่ (Big Data) และปัญญาประดิษฐ์เพื่อการประยุกต์ใช้จริง")
    elif "รัฐ" in user_input or "ปกครอง" in user_input or "MPA" in user_input:
        reasons.append("สถาบันมีความโดดเด่นสูงสุดด้านนวัตกรรมการบริหารภาครัฐและการยกระดับนโยบายสาธารณะ")
    else:
        reasons.append("เป็นหลักสูตรคุณภาพสูงของ NIDA ที่เน้นผสมผสานภาคทฤษฎีเข้มข้นกับการประยุกต์ใช้ในการทำงานจริง")

    if "เสาร์" in user_input or "อาทิตย์" in user_input or "ค่ำ" in user_input or "ทำงาน" in user_input:
        reasons.append(f"รองรับรูปแบบ {study_time} เหมาะสำหรับคนทำงานที่ต้องการยกระดับวุฒิการศึกษาโดยไม่ต้องลาออกจากงาน")

    reasons.append(f"ต่อยอดโอกาสก้าวหน้าสู่อาชีพ {careers} พร้อมเครือข่ายศิษย์เก่า NIDA ที่เข้มแข็งทั่วประเทศ")

    return f"หลักสูตร{prog_title} ({degree}) คณะ{faculty} ตอบโจทย์คุณเพราะ: " + " ".join(reasons)


def recommend_courses(
    user_input: str,
    degree_filter: Optional[str] = None,
    faculty_filter: Optional[str] = None,
    study_mode_filter: Optional[str] = None,
    top_k: int = 4,
) -> List[Dict[str, Any]]:
    """Recommend NIDA Master's and Doctoral courses with Hybrid TF-IDF Search and AI Reasoning."""
    programs = load_programs()
    if not programs:
        return []

    # Filter programs by criteria
    filtered_programs: List[Dict[str, Any]] = []
    # Extract budget constraint from user input
    max_budget = extract_max_budget(user_input)

    for prog in programs:
        # Degree Filter
        if degree_filter and degree_filter != "ทั้งหมด":
            deg = prog.get("degree", "")
            if degree_filter not in deg:
                continue

        # Faculty Filter
        if faculty_filter and faculty_filter != "ทั้งหมด":
            if prog.get("faculty") != faculty_filter:
                continue

        # Study Mode Filter
        if study_mode_filter and study_mode_filter != "ทั้งหมด":
            mode_text = (str(prog.get("study_time", "")) + " " + json.dumps(prog.get("semesters", []), ensure_ascii=False)).lower()
            if study_mode_filter.lower() not in mode_text:
                continue

        # ✅ STRICT Budget Filter — hard-exclude programs that exceed user's stated budget
        if max_budget is not None:
            prog_fee = parse_tuition_fee(prog.get("total_fee"))
            if prog_fee is not None and prog_fee > max_budget:
                continue  # skip this program — over budget

        filtered_programs.append(prog)

    if not filtered_programs:
        return []

    if not user_input.strip():
        # If no user query provided, return top programs with reasoning
        results: List[Dict[str, Any]] = []
        for p in filtered_programs[:top_k]:
            item = dict(p)
            item["match_score"] = 100.0
            item["ai_reasoning"] = generate_ai_reasoning("แนะนำหลักสูตรทั่วไป", item)
            results.append(item)
        return results

    # Build TF-IDF Corpus
    corpus = [p["search_text"] for p in filtered_programs]
    vectorizer = TfidfVectorizer(tokenizer=thai_tokenizer, token_pattern=None)

    try:
        tfidf_matrix = vectorizer.fit_transform(corpus)
        query_vector = vectorizer.transform([user_input])
        similarities = cosine_similarity(query_vector, tfidf_matrix).flatten()

        scored_results: List[Dict[str, Any]] = []
        for idx, score in enumerate(similarities):
            item = dict(filtered_programs[idx])
            match_score = round(float(score) * 100, 1)

            # Heuristic boosting based on exact keywords
            user_lower = user_input.lower()
            if "เอก" in user_lower and item.get("degree") == "ป.เอก":
                match_score += 15.0
            elif "โท" in user_lower and item.get("degree") == "ป.โท":
                match_score += 8.0

            if "เสาร์" in user_lower or "อาทิตย์" in user_lower:
                if "เสาร์" in item.get("search_text", "") or "อาทิตย์" in item.get("search_text", ""):
                    match_score += 10.0

            item["match_score"] = min(match_score, 100.0)
            if item["match_score"] > 0:
                item["ai_reasoning"] = generate_ai_reasoning(user_input, item)
                scored_results.append(item)

        scored_results.sort(key=lambda x: x["match_score"], reverse=True)

        # Fallback if top items have low similarity score
        if not scored_results:
            for p in filtered_programs[:top_k]:
                item = dict(p)
                item["match_score"] = 75.0
                item["ai_reasoning"] = generate_ai_reasoning(user_input, item)
                scored_results.append(item)

        return scored_results[:top_k]
    except Exception as e:
        print(f"Vector search warning: {e}")
        results = []
        for p in filtered_programs[:top_k]:
            item = dict(p)
            item["match_score"] = 80.0
            item["ai_reasoning"] = generate_ai_reasoning(user_input, item)
            results.append(item)
        return results
