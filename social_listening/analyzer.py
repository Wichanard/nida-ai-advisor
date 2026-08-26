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
    "อยู่", "เห็น", "ทำให้", "กรณี", "ข้อมูล", "อะไร", "ตรง", "ยัง", "เพราะ",
    "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your",
    "yours", "yourself", "yourselves", "he", "him", "his", "himself", "she",
    "her", "hers", "herself", "it", "its", "itself", "they", "them", "their",
    "theirs", "themselves", "what", "which", "who", "whom", "this", "that",
    "these", "those", "am", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "having", "do", "does", "did", "doing", "a", "an",
    "the", "and", "but", "if", "or", "because", "as", "until", "while", "of",
    "at", "by", "for", "with", "about", "against", "between", "into", "through",
    "during", "before", "after", "above", "below", "to", "from", "up", "down",
    "in", "out", "on", "off", "over", "under", "again", "further", "then",
    "once", "here", "there", "when", "where", "why", "how", "all", "any", "both",
    "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not",
    "only", "own", "same", "so", "than", "too", "very", "s", "t", "can", "will",
    "just", "don", "should", "now"
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


from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def analyze_sentiment_and_intent_llm(text: str) -> Optional[Dict[str, str]]:
    """Analyze sentiment & intent using Gemini 2.5 Flash API with retry logic for high precision & sarcasm/negation resolution."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Warning: GEMINI_API_KEY not found. LLM Analysis will fail.")
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
        print(f"Gemini LLM Analyzer exception: {e}")
        raise # Reraise to trigger tenacity retry

    return None


def analyze_sentiment_and_intent(text: str) -> Dict[str, str]:
    """Analyze sentiment and student intent for NIDA education, with LLM priority."""
    if not text:
        return {"sentiment": "Neutral", "intent": "General Education"}

    try:
        llm_res = analyze_sentiment_and_intent_llm(text)
        if llm_res:
            return llm_res
    except Exception as e:
        print(f"Failed to get LLM response after retries: {e}")

    # Safe fallback if LLM completely fails (API quota exceeded or key missing)
    t_lower = text.lower()
    sentiment = "Neutral"
    intent = "General Education"
    
    if any(q in t_lower for q in ["?", "ไหม", "ยังไง", "รบกวนถาม"]):
        sentiment = "Question"
    
    return {"sentiment": sentiment, "intent": intent}



def summarize_dataset(comments: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Perform dataset-wide analysis for NIDA Social Listening."""
    import concurrent.futures
    
    sentiments = Counter()
    intents = Counter()
    texts: List[str] = []

    def _process_item(item):
        text = item.get("text", "")
        if not text:
            return None
        res = item.get("sentiment") and item.get("intent")
        if res:
            return {"text": text, "sentiment": item["sentiment"], "intent": item["intent"]}
        else:
            analysis = analyze_sentiment_and_intent(text)
            return {"text": text, "sentiment": analysis["sentiment"], "intent": analysis["intent"]}

    # Use ThreadPoolExecutor to run LLM analysis concurrently for much faster processing
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(_process_item, comments))

    for r in results:
        if r:
            texts.append(r["text"])
            sentiments[r["sentiment"]] += 1
            intents[r["intent"]] += 1

    word_freqs = get_word_frequencies(texts, top_n=20)
    return {
        "total_comments": len(texts),
        "sentiments": dict(sentiments),
        "intents": dict(intents),
        "top_words": word_freqs,
    }
