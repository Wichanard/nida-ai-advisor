"""
tests/test_document_rag.py
Unit tests for Enterprise Document RAG & ChromaDB Vector Store.
"""
import pytest
from app.services.document_rag import NIDADocumentRAG


class TestDocumentRAG:

    def test_document_rag_singleton_and_ingestion(self):
        rag = NIDADocumentRAG.get_instance()
        assert rag is not None
        assert rag.collection is not None
        assert rag.collection.count() > 0

    def test_search_academic_regulations(self):
        rag = NIDADocumentRAG.get_instance()
        results = rag.search_knowledge("การเทียบโอนหน่วยกิตจากสถาบันอื่น", top_k=3)
        assert len(results) > 0
        top_doc = results[0]
        assert "content" in top_doc
        assert "document_title" in top_doc
        assert "relevance_score" in top_doc
        # Check if any retrieved chunk contains credit transfer concepts
        has_transfer = any("เทียบโอน" in r["content"] or "หน่วยกิต" in r["content"] for r in results)
        assert has_transfer

    def test_search_teap_english_criteria(self):
        rag = NIDADocumentRAG.get_instance()
        results = rag.search_knowledge("เกณฑ์คะแนนภาษาอังกฤษ NIDA TEAP ต้องได้เท่าไหร่", top_k=2)
        assert len(results) > 0
        matched = any("teap" in r["content"].lower() or "500" in r["content"] for r in results)
        assert matched
