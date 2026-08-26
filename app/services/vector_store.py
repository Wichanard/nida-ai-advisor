import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from google import genai

try:
    from pinecone import Pinecone, ServerlessSpec
    HAS_PINECONE = True
except ImportError:
    HAS_PINECONE = False
    
import chromadb
from chromadb.config import Settings

BASE_DIR = Path(__file__).resolve().parents[2]
COURSES_PATH = BASE_DIR / "data" / "courses.json"
CHROMA_DB_PATH = BASE_DIR / "chroma_db"
PINECONE_INDEX_NAME = "nida-chat"

class GeminiEmbeddingFunction:
    """Custom Embedding Function using Google Gemini text-embedding-004"""
    def __init__(self):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            from dotenv import load_dotenv
            load_dotenv(BASE_DIR / ".env")
            api_key = os.environ.get("GEMINI_API_KEY")
        
        self.client = genai.Client(api_key=api_key) if api_key else None

    def __call__(self, input: List[str]) -> List[List[float]]:
        if not self.client:
            return [[0.0]*768 for _ in input]
            
        embeddings = []
        for text in input:
            try:
                res = self.client.models.embed_content(
                    model="text-embedding-004",
                    contents=text
                )
                embeddings.append(res.embeddings[0].values)
            except Exception as e:
                print(f"Embedding error: {e}")
                embeddings.append([0.0]*768)
        return embeddings

def extract_max_budget(user_input: str) -> Optional[float]:
    if not user_input: return None
    m_million = re.search(r'(\d+(?:\.\d+)?)\s*ล้าน', user_input)
    if m_million: return float(m_million.group(1)) * 1_000_000.0
    m_lakh = re.search(r'(\d+(?:\.\d+)?)\s*แสน', user_input)
    if m_lakh: return float(m_lakh.group(1)) * 100_000.0
    m_tenk = re.search(r'(\d+(?:\.\d+)?)\s*หมื่น', user_input)
    if m_tenk: return float(m_tenk.group(1)) * 10_000.0
    m_num = re.search(r'(\d{1,3}(?:,\d{3})+|\d{5,7})', user_input)
    if m_num: return float(m_num.group(1).replace(',', ''))
    return None

def parse_numeric_fee(fee_val: Any) -> Optional[float]:
    if fee_val is None: return None
    cleaned = re.sub(r'[^\d]', '', str(fee_val))
    return float(cleaned) if cleaned else None

def safe_join_list(val: Any) -> str:
    if isinstance(val, list): return " ".join([str(v) for v in val if v])
    if isinstance(val, str): return val
    return ""

class NIDAVectorStore:
    _instance: Optional['NIDAVectorStore'] = None

    def __init__(self):
        self.embedding_fn = GeminiEmbeddingFunction()
        self.programs: List[Dict[str, Any]] = []
        
        # Determine if we use Pinecone or Chroma
        self.pc_api_key = os.environ.get("PINECONE_API_KEY")
        self.use_pinecone = HAS_PINECONE and self.pc_api_key
        
        if self.use_pinecone:
            print("Initializing Pinecone Cloud Vector DB...")
            self.pc = Pinecone(api_key=self.pc_api_key)
            # Create index if not exists
            if PINECONE_INDEX_NAME not in [idx.name for idx in self.pc.list_indexes()]:
                self.pc.create_index(
                    name=PINECONE_INDEX_NAME,
                    dimension=768,
                    metric='cosine',
                    spec=ServerlessSpec(cloud='aws', region='us-east-1')
                )
            self.pc_index = self.pc.Index(PINECONE_INDEX_NAME)
            self.chroma_client = None
            self.collection = None
        else:
            print("Fallback to local ChromaDB...")
            self.chroma_client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))
            class ChromaGeminiWrapper:
                def __init__(self, embed_fn): self.embed_fn = embed_fn
                def name(self): return "gemini-text-embedding-004"
                def __call__(self, input): return self.embed_fn(input)
            self.collection = self.chroma_client.get_or_create_collection(
                name="nida_courses",
                embedding_function=ChromaGeminiWrapper(self.embedding_fn)
            )
            self.pc_index = None
            
        self._load_and_index()

    @classmethod
    def get_instance(cls) -> 'NIDAVectorStore':
        if cls._instance is None:
            cls._instance = NIDAVectorStore()
        return cls._instance

    def _load_and_index(self) -> None:
        if not COURSES_PATH.exists():
            return
            
        with COURSES_PATH.open("r", encoding="utf-8-sig") as f:
            faculties_data = json.load(f)

        self.programs = []
        docs_to_insert = []
        metadatas = []
        ids = []

        for f_idx, faculty in enumerate(faculties_data):
            fac_name = faculty.get("faculty", "")
            for d_idx, dept in enumerate(faculty.get("departments", [])):
                dept_name = dept.get("department", "")
                for p_idx, prog in enumerate(dept.get("programs", [])):
                    prog_name = prog.get("program") or prog.get("name_th") or prog.get("name_en") or "ไม่ระบุชื่อหลักสูตร"
                    prog_degree = prog.get("degree") or prog.get("level") or "ปริญญาโท"
                    
                    normalized_prog = {**prog}
                    normalized_prog["program"] = prog_name
                    normalized_prog["degree"] = prog_degree
                    
                    raw_fee = prog.get("total_fee") or (prog.get("fees") or {}).get("total_cost_thb")
                    if not raw_fee and prog.get("semesters"):
                        raw_fee = prog["semesters"][0].get("tuition")
                    parsed_fee = parse_numeric_fee(raw_fee)
                    
                    normalized_prog["total_fee"] = str(raw_fee) if raw_fee else "โปรดสอบถามเพิ่มเติม"
                    normalized_prog["study_time"] = prog.get("study_time") or prog.get("study_mode") or "ไม่ระบุเวลาเรียน"
                    normalized_prog["application_link"] = prog.get("application_link") or prog.get("source_url") or "https://www.nida.ac.th"

                    doc_parts = [
                        fac_name, dept_name, prog_name, prog_degree,
                        prog.get("description", ""), prog.get("overview", ""),
                        safe_join_list(prog.get("keywords")),
                        safe_join_list(prog.get("career_opportunities")),
                        normalized_prog["study_time"],
                        prog.get("language", ""),
                        prog.get("admission_requirements", "")
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
                    
                    doc_id = f"prog_{f_idx}_{d_idx}_{p_idx}"
                    docs_to_insert.append(full_doc)
                    
                    metadatas.append({
                        "faculty": fac_name,
                        "degree": prog_degree,
                        "study_mode": normalized_prog["study_time"],
                        "numeric_fee": float(parsed_fee) if parsed_fee else -1.0,
                        "program_name": prog_name
                    })
                    ids.append(doc_id)

        if self.use_pinecone:
            stats = self.pc_index.describe_index_stats()
            if stats.total_vector_count == 0 and docs_to_insert:
                print(f"Indexing {len(docs_to_insert)} courses into Pinecone...")
                embeddings = self.embedding_fn(docs_to_insert)
                vectors = []
                for i in range(len(ids)):
                    vectors.append({
                        "id": ids[i],
                        "values": embeddings[i],
                        "metadata": {"text": docs_to_insert[i], **metadatas[i]}
                    })
                # Batch upsert to Pinecone
                batch_size = 50
                for i in range(0, len(vectors), batch_size):
                    self.pc_index.upsert(vectors=vectors[i:i+batch_size])
        else:
            if self.collection.count() == 0 and docs_to_insert:
                print("Skipping ChromaDB auto-ingestion to prevent Render rate limit hangs. Fallback to keyword search.")

    def search(self, query: str, degree_filter: str = "ทั้งหมด", faculty_filter: str = "ทั้งหมด", study_mode_filter: str = "ทั้งหมด", max_budget: Optional[float] = None, top_k: int = 4) -> List[Dict[str, Any]]:
        if self.use_pinecone:
            query_embedding = self.embedding_fn([query])[0]
            filter_dict = {}
            if degree_filter and degree_filter != "ทั้งหมด":
                filter_dict["degree"] = {"$eq": degree_filter}
            if faculty_filter and faculty_filter != "ทั้งหมด":
                filter_dict["faculty"] = {"$eq": faculty_filter}
            
            results = self.pc_index.query(
                vector=query_embedding,
                top_k=top_k * 2,
                include_metadata=True,
                filter=filter_dict if filter_dict else None
            )
            matched_ids = [match['id'] for match in results.get('matches', [])]
        else:
            if self.collection.count() == 0:
                # Fallback to simple keyword search if DB is empty
                keywords = [k for k in query.split() if len(k) > 2]
                scored = []
                for p in self.programs:
                    text_search = p.get("search_document", "").lower()
                    score = sum(1 for k in keywords if k.lower() in text_search)
                    if score > 0:
                        scored.append({"prog": p, "score": score})
                scored.sort(key=lambda x: x["score"], reverse=True)
                
                final_results = []
                for item in scored:
                    prog = item["prog"]
                    if degree_filter and degree_filter != "ทั้งหมด" and prog.get("degree") != degree_filter: continue
                    if faculty_filter and faculty_filter != "ทั้งหมด" and prog.get("faculty") != faculty_filter: continue
                    if max_budget is not None and prog.get("numeric_fee") is not None and prog["numeric_fee"] > max_budget: continue
                    if study_mode_filter and study_mode_filter != "ทั้งหมด" and study_mode_filter not in prog.get("study_time", ""): continue
                    
                    final_results.append(prog)
                    if len(final_results) >= top_k: break
                return final_results
                
            where_clause = {}
            if degree_filter and degree_filter != "ทั้งหมด":
                where_clause["degree"] = degree_filter
            if faculty_filter and faculty_filter != "ทั้งหมด":
                where_clause["faculty"] = faculty_filter
                
            try:
                results = self.collection.query(
                    query_texts=[query],
                    n_results=top_k * 2,
                    where=where_clause if where_clause else None
                )
            except:
                return []
                
            if not results["ids"] or not results["ids"][0]:
                return []
            matched_ids = results["ids"][0]
        
        # Build local id_to_prog
        id_to_prog = {}
        idx = 0
        for f_idx, faculty in enumerate(json.loads(COURSES_PATH.read_text(encoding="utf-8-sig"))):
            for d_idx, dept in enumerate(faculty.get("departments", [])):
                for p_idx, prog in enumerate(dept.get("programs", [])):
                    doc_id = f"prog_{f_idx}_{d_idx}_{p_idx}"
                    if idx < len(self.programs):
                        id_to_prog[doc_id] = self.programs[idx]
                    idx += 1
                    
        final_results = []
        for doc_id in matched_ids:
            if doc_id in id_to_prog:
                prog = id_to_prog[doc_id]
                if max_budget is not None and prog["numeric_fee"] is not None:
                    if prog["numeric_fee"] > max_budget:
                        continue
                if study_mode_filter and study_mode_filter != "ทั้งหมด":
                    if study_mode_filter not in prog.get("study_time", ""):
                        continue
                final_results.append(prog)
                if len(final_results) >= top_k:
                    break
                    
        return final_results

    def compare_programs(self, program_names: List[str]) -> List[Dict[str, Any]]:
        results = []
        for name in program_names:
            matches = self.search(query=name, top_k=1)
            if matches:
                results.append(matches[0])
        return results

    def upsert_pdf_document(self, text: str, filename: str):
        """Used by Admin API to upload new documents directly into Pinecone"""
        if not self.use_pinecone:
            raise Exception("Pinecone is not initialized")
            
        doc_id = f"pdf_{filename.replace(' ', '_')}"
        embeddings = self.embedding_fn([text])[0]
        self.pc_index.upsert(vectors=[{
            "id": doc_id,
            "values": embeddings,
            "metadata": {
                "text": text,
                "program_name": filename,
                "degree": "ทั้งหมด",
                "faculty": "ทั้งหมด",
                "study_mode": "ทั้งหมด"
            }
        }])
