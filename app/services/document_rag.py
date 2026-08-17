"""
app/services/document_rag.py
Enterprise Document RAG & PDF Ingestion Engine for NIDA Academic Regulations & Handbooks.
Features Persistent ChromaDB Storage, Metadata Chunking, and Citation Extraction.
"""
from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings
from pypdf import PdfReader


class NIDADocumentRAG:
    """Enterprise RAG engine for official NIDA regulations, handbooks, and PDFs."""

    _instance: Optional[NIDADocumentRAG] = None

    def __init__(self, persist_directory: Optional[str] = None) -> None:
        base_dir = Path(__file__).resolve().parent.parent.parent
        self.persist_dir = persist_directory or str(base_dir / "data" / "chroma_db")
        self.docs_dir = base_dir / "data" / "nida_documents"
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB persistent client
        self.client = chromadb.PersistentClient(path=self.persist_dir)
        self.collection = self.client.get_or_create_collection(
            name="nida_academic_knowledge",
            metadata={"description": "Official NIDA Academic Regulations & Curriculums"},
        )

        # Index knowledge documents if collection is empty
        if self.collection.count() == 0:
            self.ingest_all_documents()

    @classmethod
    def get_instance(cls) -> NIDADocumentRAG:
        if cls._instance is None:
            cls._instance = NIDADocumentRAG()
        return cls._instance

    def ingest_all_documents(self) -> int:
        """Scan data/nida_documents and index all Markdown and PDF files."""
        total_chunks = 0
        for file_path in self.docs_dir.glob("*"):
            if file_path.suffix.lower() in [".md", ".txt"]:
                total_chunks += self.ingest_markdown_file(str(file_path))
            elif file_path.suffix.lower() == ".pdf":
                total_chunks += self.ingest_pdf_file(str(file_path))
        return total_chunks

    def ingest_markdown_file(self, file_path: str) -> int:
        """Parse markdown file, chunk by sections, and store in ChromaDB."""
        p = Path(file_path)
        if not p.exists():
            return 0

        with open(p, "r", encoding="utf-8") as f:
            content = f.read()

        title = p.stem.replace("_", " ").title()
        chunks = self._chunk_text(content, chunk_size=600, overlap=100)
        
        ids: List[str] = []
        docs: List[str] = []
        metadatas: List[Dict[str, Any]] = []

        for idx, chunk in enumerate(chunks):
            chunk_id = hashlib.md5(f"{p.name}_{idx}_{chunk[:30]}".encode()).hexdigest()
            ids.append(chunk_id)
            docs.append(chunk)
            metadatas.append({
                "source_file": p.name,
                "document_title": title,
                "chunk_index": idx,
                "file_type": "markdown",
            })

        if ids:
            self.collection.upsert(ids=ids, documents=docs, metadatas=metadatas)
        return len(ids)

    def ingest_pdf_file(self, file_path: str) -> int:
        """Parse PDF document, extract text page-by-page, chunk and store in ChromaDB."""
        p = Path(file_path)
        if not p.exists():
            return 0

        reader = PdfReader(str(p))
        title = p.stem.replace("_", " ").title()
        
        ids: List[str] = []
        docs: List[str] = []
        metadatas: List[Dict[str, Any]] = []

        for page_idx, page in enumerate(reader.pages, 1):
            text = page.extract_text() or ""
            if not text.strip():
                continue
            chunks = self._chunk_text(text, chunk_size=600, overlap=100)
            for c_idx, chunk in enumerate(chunks):
                chunk_id = hashlib.md5(f"{p.name}_p{page_idx}_{c_idx}".encode()).hexdigest()
                ids.append(chunk_id)
                docs.append(chunk)
                metadatas.append({
                    "source_file": p.name,
                    "document_title": title,
                    "page_number": page_idx,
                    "chunk_index": c_idx,
                    "file_type": "pdf",
                })

        if ids:
            self.collection.upsert(ids=ids, documents=docs, metadatas=metadatas)
        return len(ids)

    def search_knowledge(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Query ChromaDB for relevant regulation and academic policy chunks with hybrid lexical re-ranking."""
        if self.collection.count() == 0:
            return []

        # Retrieve a broader candidate pool
        candidate_count = min(max(top_k * 3, 10), self.collection.count())
        results = self.collection.query(
            query_texts=[query],
            n_results=candidate_count,
        )

        candidates: List[Dict[str, Any]] = []
        if results and "documents" in results and results["documents"]:
            docs_list = results["documents"][0]
            meta_list = results["metadatas"][0] if results["metadatas"] else [{}] * len(docs_list)
            dist_list = results["distances"][0] if results.get("distances") else [0.0] * len(docs_list)

            # Tokenize query for keyword boost
            from social_listening.analyzer import tokenize_thai
            q_tokens = [t.lower() for t in tokenize_thai(query) if len(t.strip()) > 1]

            for doc, meta, dist in zip(docs_list, meta_list, dist_list):
                dense_score = max(0.0, 1.0 - (dist / 2.0))
                doc_lower = doc.lower()
                
                # Keyword overlap boost
                kw_matches = sum(1 for t in q_tokens if t in doc_lower)
                kw_boost = min(kw_matches * 0.25, 0.75)

                hybrid_score = round(dense_score + kw_boost, 3)
                candidates.append({
                    "content": doc,
                    "document_title": meta.get("document_title", "ระเบียบสถาบัน NIDA"),
                    "source_file": meta.get("source_file", ""),
                    "page_number": meta.get("page_number", 1),
                    "relevance_score": hybrid_score,
                })

        # Sort by hybrid score descending
        candidates.sort(key=lambda x: x["relevance_score"], reverse=True)
        return candidates[:top_k]

    @staticmethod
    def _chunk_text(text: str, chunk_size: int = 600, overlap: int = 100) -> List[str]:
        """Split text into overlapping semantic blocks respecting paragraph boundaries."""
        paragraphs = re.split(r"\n\s*\n", text)
        chunks: List[str] = []
        current_chunk = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            if len(current_chunk) + len(para) <= chunk_size:
                current_chunk += ("\n\n" if current_chunk else "") + para
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = para

        if current_chunk:
            chunks.append(current_chunk)

        # Fallback if chunks are still too large
        final_chunks: List[str] = []
        for c in chunks:
            if len(c) > chunk_size * 1.5:
                for i in range(0, len(c), chunk_size - overlap):
                    final_chunks.append(c[i : i + chunk_size])
            else:
                final_chunks.append(c)
        return final_chunks
