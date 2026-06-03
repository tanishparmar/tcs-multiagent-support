import os
from pathlib import Path
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from src.config import config

os.makedirs(config.VECTOR_DB_PATH, exist_ok=True)

_embedding_fn = SentenceTransformerEmbeddingFunction(model_name=config.EMBEDDING_MODEL)
_client = chromadb.PersistentClient(path=config.VECTOR_DB_PATH)
_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)


def _get_collection():
    return _client.get_or_create_collection(
        name=config.VECTOR_COLLECTION,
        embedding_function=_embedding_fn,
        metadata={"hnsw:space": "cosine"},
    )


def ingest_text(text: str, doc_name: str, metadata: dict | None = None) -> int:
    collection = _get_collection()
    chunks = _splitter.split_text(text)
    if not chunks:
        return 0
    ids = [f"{doc_name}_{i}" for i in range(len(chunks))]
    metas = [{**(metadata or {}), "source": doc_name, "chunk": i} for i in range(len(chunks))]
    collection.upsert(documents=chunks, ids=ids, metadatas=metas)
    return len(chunks)


def ingest_file(file_path: str | Path) -> int:
    path = Path(file_path)
    if path.suffix.lower() == ".pdf":
        reader = PdfReader(str(path))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    else:
        text = path.read_text(encoding="utf-8", errors="ignore")
    return ingest_text(text, doc_name=path.stem, metadata={"filename": path.name})


def search(query: str, n_results: int | None = None) -> list[dict]:
    collection = _get_collection()
    k = n_results or config.RETRIEVAL_TOP_K
    count = collection.count()
    if count == 0:
        return []
    results = collection.query(query_texts=[query], n_results=min(k, count))
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]
    return [
        {"text": doc, "source": meta.get("source", ""), "score": round(1 - dist, 4)}
        for doc, meta, dist in zip(docs, metas, distances)
    ]


def list_documents() -> list[str]:
    collection = _get_collection()
    if collection.count() == 0:
        return []
    results = collection.get(include=["metadatas"])
    sources = {m.get("source", "") for m in results.get("metadatas", [])}
    return sorted(sources)


def ingest_policy_dir() -> dict[str, int]:
    summary = {}
    policy_dir = config.POLICY_DIR
    for path in sorted(policy_dir.iterdir()):
        if path.suffix.lower() in (".txt", ".pdf", ".md"):
            count = ingest_file(path)
            summary[path.name] = count
    return summary
