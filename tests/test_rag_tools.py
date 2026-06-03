"""Tests for RAG tools — requires policy docs to be ingested (run setup_db.py first)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from src.db.vector_db import ingest_policy_dir, list_documents


@pytest.fixture(autouse=True, scope="module")
def ingest_policies():
    """Ensure policy docs are ingested before RAG tests."""
    ingest_policy_dir()


def test_list_ingested_documents():
    from src.tools.rag_tools import list_ingested_documents
    result = list_ingested_documents.invoke({})
    assert isinstance(result, str)
    assert "No documents" not in result or len(list_documents()) == 0


def test_search_policy_refund():
    from src.tools.rag_tools import search_policy_documents
    result = search_policy_documents.invoke({"query": "refund timeline"})
    assert isinstance(result, str)
    assert len(result) > 0


def test_search_policy_shipping():
    from src.tools.rag_tools import search_policy_documents
    result = search_policy_documents.invoke({"query": "international shipping cost"})
    assert isinstance(result, str)


def test_search_policy_sla():
    from src.tools.rag_tools import search_policy_documents
    result = search_policy_documents.invoke({"query": "SLA response time premium"})
    assert isinstance(result, str)


def test_ingest_nonexistent_file():
    from src.tools.rag_tools import ingest_document_from_path
    result = ingest_document_from_path.invoke({"file_path": "/nonexistent/path/doc.pdf"})
    assert "not found" in result.lower() or "Error" in result


def test_vector_db_direct_search():
    from src.db.vector_db import search
    results = search("refund policy 30 days")
    assert isinstance(results, list)
    if results:
        assert "text" in results[0]
        assert "source" in results[0]
        assert "score" in results[0]
