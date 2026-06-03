from langchain_core.tools import tool
from src.db import vector_db
from src.config import config


@tool
def search_policy_documents(query: str) -> str:
    """Search company policy documents for information about refunds, shipping,
    returns, support SLAs, warranties, privacy, or any documented procedure.
    Provide a natural language question and the most relevant policy excerpts are returned."""
    results = vector_db.search(query, n_results=config.RETRIEVAL_TOP_K)
    if not results:
        return (
            "No policy documents are currently loaded. "
            "Please upload policy PDFs via the sidebar in the Streamlit app."
        )
    formatted = []
    for i, r in enumerate(results, 1):
        formatted.append(
            f"[Source: {r['source']} | Relevance: {r['score']}]\n{r['text']}"
        )
    return "\n\n---\n\n".join(formatted)


@tool
def list_ingested_documents() -> str:
    """List all policy documents that have been ingested into the knowledge base.
    Returns document names currently available for search."""
    docs = vector_db.list_documents()
    if not docs:
        return "No documents ingested yet."
    return "Ingested documents:\n" + "\n".join(f"  • {d}" for d in docs)


@tool
def ingest_document_from_path(file_path: str) -> str:
    """Ingest a policy document (PDF or TXT) into the knowledge base from a file path.
    The document will be chunked, embedded, and stored for semantic search."""
    try:
        count = vector_db.ingest_file(file_path)
        return f"Successfully ingested '{file_path}' — {count} chunks stored."
    except FileNotFoundError:
        return f"File not found: {file_path}"
    except Exception as e:
        return f"Error ingesting file: {e}"


def get_rag_tools() -> list:
    return [
        search_policy_documents,
        list_ingested_documents,
        ingest_document_from_path,
    ]
