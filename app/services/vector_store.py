"""
app/services/vector_store.py
Enterprise Hybrid Vector Store & Semantic Index for NIDA Academic Catalog.
Provides semantic embedding matching, attribute filtering, and side-by-side program comparison.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pythainlp.tokenize import word_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

BASE_DIR = Path(__file__).resolve().parents[2]
COURSES_PATH = BASE_DIR / "data" / "courses.json"


def extract_max_budget(user_input: str) -> Optional[float]:
    """Extract maximum budget in THB from natural language string."""
    if not user_input:
        return None
    m_million = re.search(r'(\d+(?:\.\d+)?)\s*ล้าน', user_input)
    if m_million:
        return float(m_million.group(1)) * 1_000_000.0
    m_lakh = re.search(r'(\d+(?:\.\d+)?)\s*แสน', user_input)
    if m_lakh:
        return float(m_lakh.group(1)) * 100_000.0
    m_tenk = re.search(r'(\d+(?:\.\d+)?)\s*หมื่น', user_input)
    if m_tenk:
        return float(m_tenk.group(1)) * 10_000.0
    m_num = re.search(r'(\d{1,3}(?:,\d{3})+|\d{5,7})', user_input)
    if m_num:
        return float(m_num.group(1).replace(',', ''))
    return None


def parse_numeric_fee(fee_val: Any) -> Optional[float]:
    """Extract numeric total fee from program data."""
    if fee_val is None:
        return None
    cleaned = re.sub(r'[^\d]', '', str(fee_val))
    return float(cleaned) if cleaned else None


def tokenize_thai_doc(text: str) -> List[str]:
    """Tokenize Thai document for TF-IDF Vector Space Model."""
    if not text:
        return []
    clean = re.sub(r'[^\w\s\u0E00-\u0E7F]', ' ', text)
    tokens = word_tokenize(clean, engine="newmm")
    return [t.strip().lower() for t in tokens if len(t.strip()) > 1]


def safe_join_list(val: Any) -> str:
    """Safely format list/string field into text."""
    if isinstance(val, list):
        return " ".join([str(v) for v in val if v])
    if isinstance(val, str):
        return val
    return ""


class NIDAVectorStore:
    """Enterprise In-Memory Vector Store for 73+ NIDA Master's and PhD Programs."""

    _instance: Optional[NIDAVectorStore] = None

    def __init__(self) -> None:
        self.programs: List[Dict[str, Any]] = []
        self.corpus: List[str] = []
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.tfidf_matrix = None
        self._load_and_index()

    @classmethod
    def get_instance(cls) -> NIDAVectorStore:
        if cls._instance is None:
            cls._instance = NIDAVectorStore()
        return cls._instance

    def _load_and_index(self) -> None:
        if not COURSES_PATH.exists():
            return

        with COURSES_PATH.open("r", encoding="utf-8-sig") as f:
            faculties_data = json.load(f)

        self.programs = []
        self.corpus = []

        for faculty in faculties_data:
            fac_name = faculty.get("faculty", "")
            for dept in faculty.get("departments", []):
                dept_name = dept.get("department", "")
                for prog in dept.get("programs", []):
                    # --- Data Normalization Fix ---
                    # Some faculties use "program" & "degree", others use "name_th" & "level".
                    # We normalize them here so dashboard.py displays them correctly.
                    normalized_prog = {**prog}
                    prog_name = prog.get("program") or prog.get("name_th") or prog.get("name_en") or "ไม่ระบุชื่อหลักสูตร"
                    prog_degree = prog.get("degree") or prog.get("level") or "ไม่ระบุระดับ"
                    
                    normalized_prog["program"] = prog_name
                    normalized_prog["degree"] = prog_degree
                    
                    raw_fee = prog.get("total_fee") or (prog.get("fees") or {}).get("total_cost_thb")
                    if not raw_fee and prog.get("semesters"):
                        first_sem_fee = prog["semesters"][0].get("tuition")
                        raw_fee = first_sem_fee
                    parsed_fee = parse_numeric_fee(raw_fee)
                    
                    normalized_prog["total_fee"] = str(raw_fee) if raw_fee else "สอบถามสถาบัน"
                    normalized_prog["study_time"] = prog.get("study_time") or prog.get("study_mode") or "ไม่ระบุเวลาเรียน"
                    normalized_prog["application_link"] = prog.get("application_link") or prog.get("source_url") or "https://www.nida.ac.th"

                    doc_parts = [
                        fac_name,
                        dept_name,
                        prog_name,
                        prog_degree,
                        prog.get("description", ""),
                        prog.get("overview", ""),
                        safe_join_list(prog.get("keywords")),
                        safe_join_list(prog.get("career_opportunities")),
                        prog.get("study_time", "") or prog.get("study_mode", ""),
                        prog.get("language", ""),
                        prog.get("admission_requirements", ""),
                        safe_join_list(prog.get("special_features")),
                    ]
                    full_doc = " ".join([str(p) for p in doc_parts if p]).strip()

                    prog_record = {
                        "faculty": fac_name,
                        "department": dept_name,
                        "numeric_fee": parsed_fee,
                        "search_document": full_doc,
                        **normalized_prog,
                    }
                    self.programs.append(prog_record)
                    self.corpus.append(full_doc)

        if self.corpus:
            self.vectorizer = TfidfVectorizer(
                tokenizer=tokenize_thai_doc,
                ngram_range=(1, 2),
                min_df=1,
                sublinear_tf=True,
            )
            self.tfidf_matrix = self.vectorizer.fit_transform(self.corpus)

    def search(
        self,
        query: str,
        degree_filter: str = "ทั้งหมด",
        faculty_filter: str = "ทั้งหมด",
        study_mode_filter: str = "ทั้งหมด",
        max_budget: Optional[float] = None,
        top_k: int = 4,
    ) -> List[Dict[str, Any]]:
        """Perform hybrid vector search + rule-based constraint filtering."""
        if not self.programs or self.vectorizer is None or self.tfidf_matrix is None:
            return []

        if max_budget is None:
            max_budget = extract_max_budget(query)

        query_vec = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix)[0]

        scored_candidates: List[Tuple[float, Dict[str, Any]]] = []
        q_lower = query.lower()

        for idx, prog in enumerate(self.programs):
            if degree_filter and degree_filter != "ทั้งหมด":
                if prog.get("degree") != degree_filter:
                    continue

            if faculty_filter and faculty_filter != "ทั้งหมด":
                if prog.get("faculty") != faculty_filter:
                    continue

            if study_mode_filter and study_mode_filter != "ทั้งหมด":
                study_info = (
                    str(prog.get("study_time", ""))
                    + " "
                    + str(prog.get("language", ""))
                    + " "
                    + json.dumps(prog.get("semesters", []), ensure_ascii=False)
                )
                if study_mode_filter.lower() not in study_info.lower():
                    continue

            base_sim = float(similarities[idx])
            final_score = base_sim

            prog_name = prog.get("program", "").lower()
            keywords_val = prog.get("keywords")
            keywords = [k.lower() for k in keywords_val] if isinstance(keywords_val, list) else []

            for kw in keywords:
                if kw in q_lower:
                    final_score += 0.15
            if any(term in q_lower for term in ["mba", "บริหารธุรกิจ", "บริหาร"]) and "mba" in prog_name:
                final_score += 0.20
            if any(term in q_lower for term in ["data", "ai", "สถิติ", "ปัญญาประดิษฐ์", "big data"]) and any(k in prog_name for k in ["สถิติ", "วิทยาการข้อมูล", "data"]):
                final_score += 0.20
            if any(term in q_lower for term in ["รัฐศาสตร์", "รัฐประศาสนศาสตร์", "mpa", "ราชการ"]) and "รัฐประศาสนศาสตร์" in prog_name:
                final_score += 0.20

            num_fee = prog.get("numeric_fee")
            if max_budget is not None and num_fee is not None:
                if num_fee <= max_budget:
                    final_score += 0.10
                else:
                    final_score -= 0.25

            match_pct = min(round(max(final_score, 0.05) * 100.0, 1), 99.0)
            candidate = dict(prog)
            candidate["match_score"] = match_pct
            scored_candidates.append((final_score, candidate))

        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored_candidates[:top_k]]

    def compare_programs(self, program_names: List[str]) -> List[Dict[str, Any]]:
        """Retrieve full comparison records for specified program names."""
        results: List[Dict[str, Any]] = []
        for name in program_names:
            target = name.strip().lower()
            match = next(
                (p for p in self.programs if target in p.get("program", "").lower() or p.get("program", "").lower() in target),
                None,
            )
            if match:
                results.append(match)
        return results
