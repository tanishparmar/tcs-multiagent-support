import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent


class Config:
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama3.2")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

    SQL_DB_URL: str = f"sqlite:///{BASE_DIR / 'data' / 'db' / 'customer_support.db'}"
    VECTOR_DB_PATH: str = str(BASE_DIR / "data" / "db" / "chroma")
    VECTOR_COLLECTION: str = "policy_documents"

    POLICY_DIR: Path = BASE_DIR / "data" / "policies"

    MCP_HOST: str = os.getenv("MCP_HOST", "localhost")
    MCP_PORT: int = int(os.getenv("MCP_PORT", "8765"))

    MAX_AGENT_ITERATIONS: int = 6
    RETRIEVAL_TOP_K: int = 5


config = Config()
