from __future__ import annotations

import io
import json
import os
import re
from collections import Counter
from typing import Any, Dict, Iterable, List, Optional

from pythainlp.corpus import thai_stopwords
from pythainlp.tokenize import word_tokenize
from wordcloud import WordCloud

# Stopwords set combining PyThaiNLP default stopwords and custom NIDA social listening noise terms
STOPWORDS = set(thai_stopwords()).union({
    "ครับ", "ค่ะ", "นะ", "ครับผม", "นะคะ", "เลย", "ได้", "ให้", "กับ", "ของ", "ที่",
    "ใน", "และ", "จะ", "มี", "เป็น", "ไป", "มา", "ไม่", "ก็", "ว่า", "การ", "ความ",
    "นิด้า", "nida", "มหาวิทยาลัย", "สถาบัน", "เรียน", "ต่อ", "ปริญญา", "โท", "เอก",
    "ปโท", "ปเอก", "เรื่อง", "อย่าง", "หรือ", "จาก", "ผู้", "ต้อง", "คน", "คิด",
    "อยาก", "ก็น่า", "ใคร", "ซึ่ง", "ตาม", "โดย", "เพื่อ", "อีก", "แล้ว", "ถึง",
    "อยู่", "เห็น", "ทำให้", "กรณี", "ข้อมูล", "อะไร", "ตรง", "ยัง", "เพราะ"
})

THAI_FONT_PATH = "C:/Windows/Fonts/tahoma.ttf" if os.path.exists("C:/Windows/Fonts/tahoma.ttf") else "C:/Windows/Fonts/LeelawUI.ttf"


def summarize_texts(texts: Iterable[str]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for raw in texts:
        text = raw.strip().lower()
        if not text:
            continue
        counts[text] = counts.get(text, 0) + 1
    return counts


def extract_keywords(text: str, keywords: Iterable[str]) -> List[str]:
    normalized_text = text.lower()
    found: List[str] = []
    for keyword in keywords:
        if keyword.lower() in normalized_text:
            found.append(keyword)
    return found


def tokenize_thai(text: str) -> List[str]:
    """Tokenize Thai text, clean punctuation/numbers, and filter out stopwords."""
    if not text:
        return []
    clean_text = re.sub(r"https?://\S+|www\.\S+|<.*?>|\d+|[^\w\s\u0E00-\u0E7F]", " ", text)
    tokens = word_tokenize(clean_text, engine="newmm")
    filtered: List[str] = []
    for t in tokens:
        word = t.strip().lower()
        if len(word) > 1 and word not in STOPWORDS and not word.isnumeric():
            filtered.append(word)
    return filtered


def get_word_frequencies(texts: Iterable[str], top_n: int = 50) -> Dict[str, int]:
    """Count token frequencies across all given texts."""
    counts = Counter()
    for text in texts:
        tokens = tokenize_thai(text)
        counts.update(tokens)
    return dict(counts.most_common(top_n))


def generate_wordcloud_image(texts: Iterable[str]) -> bytes | None:
    """Generate WordCloud PNG image bytes from Thai texts."""
    freqs = get_word_frequencies(texts, top_n=100)
    if not freqs:
        return None

    try:
        wc = WordCloud(
            font_path=THAI_FONT_PATH if os.path.exists(THAI_FONT_PATH) else None,
            width=800,
            height=400,
            background_color="white",
            colormap="viridis",
            max_words=100,
            regexp=r"[\u0E00-\u0E7F\w]+",
        ).generate_from_frequencies(freqs)

        img = wc.to_image()
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception as e:
        print(f"Error generating WordCloud: {e}")
        return None


def analyze_sentiment_and_intent_llm(text: str) -> Optional[Dict[str, str]]:
    """Analyze sentiment & intent using Gemini 2.5 Flash API for high precision & sarcasm/negation resolution."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        prompt = f"""
        คุณเป็นนักวิเคราะห์ระบบ Social Listening ภาษาไทยสำหรับการศึกษาต่อ NIDA
        วิเคราะห์ข้อความต่อไปนี้: "{text}"

        ตอบกลับในรูปแบบ JSON เท่านั้น โดยมี key 2 ตัว:
        "sentiment": เลือกจากหนึ่งในคำต่อไปนี้ [Positive, Negative, Neutral, Question, Mixed]
        "intent": เลือกจากหนึ่งในคำต่อไปนี้ [Tuition & Cost, Schedule & Study Mode, Admission & Requirements, Career & Value, Alumni Network, Thesis & Academic, General Education]

        ตัวอย่างผลลัพธ์:
        {{"sentiment": "Positive", "intent": "Career & Value"}}
        """
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        if response and response.text:
            cleaned = response.text.strip().replace("```json", "").replace("```", "").strip()
            data = json.loads(cleaned)
            if "sentiment" in data and "intent" in data:
                return data
    except Exception as e:
        print(f"Gemini LLM Analyzer warning: {e}")

    return None


def analyze_sentiment_and_intent(text: str) -> Dict[str, str]:
    """Analyze sentiment and student intent for NIDA education, with LLM priority and intelligent Thai Rule-Based fallback with negation support."""
    if not text:
        return {"sentiment": "Neutral", "intent": "General Education"}

    # Attempt LLM first if available
    llm_res = analyze_sentiment_and_intent_llm(text)
    if llm_res:
        return llm_res

    t_lower = text.lower()

    # Negation Handling Prefix Check
    negation_prefixes = ["ไม่", "ไม่ได้", "ไม่ค่อย", "อย่า", "ห้าม", "แทบไม่"]
    
    pos_words = [
        "อยากเรียน", "น่าเรียน", "คุ้ม", "แนะนำ", "ชอบ", "ดีมาก", "ชื่นชม",
        "หลักสูตรดี", "อาจารย์เก่ง", "อาจารย์ดีมาก", "สังคมดี", "โอกาสดี", "ก้าวหน้า",
        "คุณภาพ", "มีชื่อเสียง", "น่าเชื่อถือ", "ภูมิใจ", "มีประโยชน์", "คุ้มค่า",
        "ได้ความรู้", "ได้คอนเนกชัน", "ได้เครือข่าย", "network ดี", "alumni ดี", "ศิษย์เก่าดี",
        "เรียนสนุก", "เพื่อนดี", "บรรยากาศดี", "ยกระดับ", "พัฒนาตัวเอง", "มาถูกทาง", "ตัดสินใจถูก",
        "ผ่านสัมภาษณ์", "ติด", "ได้รับการตอบรับ", "ชมสถาบัน", "ชอบมาก", "เลื่อนตำแหน่ง", "ขึ้นเงินเดือน",
    ]

    neg_words = [
        "แพงมาก", "แพงเกิน", "ค่าเทอมสูง", "ไม่มีทุน", "ทุนยาก", "ไม่คุ้ม",
        "เดินทางยาก", "ไกลมาก", "ไกล", "รถติด", "ไม่มีรถไฟฟ้า", "ที่จอดรถน้อย", "ที่จอดรถไม่พอ",
        "ยากมาก", "เหนื่อยมาก", "หนักมาก", "ท้อ", "เครียด", "กดดัน", "สอบตก",
        "เขียนวิทยานิพนธ์ยาก", "สารนิพนธ์ยาก", "อาจารย์ที่ปรึกษาไม่มีเวลา",
        "ระบบแย่", "ลงทะเบียนยาก", "บริการแย่", "เจ้าหน้าที่ไม่ช่วย", "ข้อมูลไม่ชัด",
        "รอนาน", "ช้า", "วุ่นวาย", "ขั้นตอนเยอะ", "ไม่มีเวลา", "ไม่ผ่านสัมภาษณ์", "สอบไม่ผ่าน",
        "ข้อเสีย", "ปัญหา", "อุปสรรค", "น่าเสียดาย", "ผิดหวัง", "ไม่ตรงปก", "ยกเลิก",
    ]

    inquiry_words = [
        "เท่าไหร่", "เกรด", "คุณสมบัติ", "สอบยังไง", "เปิดรับเมื่อไหร่", "รับกี่คน",
        "สัมภาษณ์ยังไง", "ค่าเทอมกี่บาท", "เรียนวันไหน", "เรียนกี่ปี", "สมัครอย่างไร",
        "มีทุนไหม", "ทุนมีไหม", "เทียบโอน", "กี่หน่วยกิต", "teap", "ielts", "toeic",
        "ข้อสอบเข้า", "เดินทางยังไง", "หอพัก", "?", "สอบถาม", "ขอถาม", "รบกวนถาม",
    ]

    # Explicit Negation Checking ("ไม่ได้ดี", "ไม่ค่อยดี")
    has_negated_pos = any(f"{neg}{pos}" in t_lower for neg in negation_prefixes for pos in ["ดี", "ชอบ", "คุ้ม", "แนะนำ", "โอเค"])
    
    has_pos = any(w in t_lower for w in pos_words) and not has_negated_pos
    has_neg = any(w in t_lower for w in neg_words) or has_negated_pos
    has_inquiry = any(w in t_lower for w in inquiry_words)

    if has_inquiry:
        sentiment = "Question"
    elif has_pos and not has_neg:
        sentiment = "Positive"
    elif has_neg and not has_pos:
        sentiment = "Negative"
    elif has_pos and has_neg:
        sentiment = "Mixed"
    else:
        sentiment = "Neutral"

    # Intent Classification
    tuition_kws = ["ค่าเทอม", "ค่าใช้จ่าย", "ทุนการศึกษา", "ทุน", "เงิน", "กู้", "ผ่อนชำระ", "บาท", "แสน", "หมื่น"]
    schedule_kws = ["เสาร์", "อาทิตย์", "ภาคค่ำ", "ภาคปกติ", "เวลาเรียน", "ออนไลน์", "ภาคพิเศษ", "นอกเวลาราชการ"]
    admission_kws = ["คุณสมบัติ", "สอบ", "เกรด", "สัมภาษณ์", "รับสมัคร", "สมัคร", "สอบเข้า", "เกณฑ์", "วุฒิ", "gpa"]
    career_kws = ["ทำงาน", "อาชีพ", "เงินเดือน", "ตำแหน่ง", "ก้าวหน้า", "ผู้บริหาร", "เลื่อนขั้น", "เจ้าของกิจการ"]
    network_kws = ["คอนเนกชัน", "เครือข่าย", "alumni", "ศิษย์เก่า", "เพื่อนในคลาส", "รุ่นพี่", "community"]
    thesis_kws = ["วิทยานิพนธ์", "สารนิพนธ์", "ค้นคว้าอิสระ", "แผน ก", "แผน ข", "งานวิจัย", "อาจารย์ที่ปรึกษา"]

    if any(w in t_lower for w in tuition_kws):
        intent = "Tuition & Cost"
    elif any(w in t_lower for w in schedule_kws):
        intent = "Schedule & Study Mode"
    elif any(w in t_lower for w in admission_kws):
        intent = "Admission & Requirements"
    elif any(w in t_lower for w in network_kws):
        intent = "Alumni Network"
    elif any(w in t_lower for w in career_kws):
        intent = "Career & Value"
    elif any(w in t_lower for w in thesis_kws):
        intent = "Thesis & Academic"
    else:
        intent = "General Education"

    return {"sentiment": sentiment, "intent": intent}


def summarize_dataset(comments: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Perform dataset-wide analysis for NIDA Social Listening."""
    sentiments = Counter()
    intents = Counter()
    texts: List[str] = []

    for item in comments:
        text = item.get("text", "")
        if not text:
            continue
        texts.append(text)
        res = item.get("sentiment") and item.get("intent")
        if res:
            sentiments[item["sentiment"]] += 1
            intents[item["intent"]] += 1
        else:
            analysis = analyze_sentiment_and_intent(text)
            sentiments[analysis["sentiment"]] += 1
            intents[analysis["intent"]] += 1

    word_freqs = get_word_frequencies(texts, top_n=20)
    return {
        "total_comments": len(texts),
        "sentiments": dict(sentiments),
        "intents": dict(intents),
        "top_words": word_freqs,
    }
