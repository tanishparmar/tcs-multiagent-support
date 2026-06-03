"""
One-command setup: initialise the SQLite DB, seed synthetic data,
and ingest bundled policy documents into ChromaDB.

Usage:
    python setup_db.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.db.sql_db import init_db
from src.db.vector_db import ingest_policy_dir
from data.seed_data import seed


def main():
    print("=" * 50)
    print("  TCS Multi-Agent Support — Setup")
    print("=" * 50)

    print("\n[1/3] Initialising SQL database…")
    init_db()
    print("  ✓ Tables created")

    print("\n[2/3] Seeding synthetic customer data…")
    seed()

    print("\n[3/3] Ingesting policy documents into ChromaDB…")
    summary = ingest_policy_dir()
    for doc, chunks in summary.items():
        print(f"  ✓ {doc} — {chunks} chunks")

    print("\n" + "=" * 50)
    print("  Setup complete!")
    print("  Run the app:   streamlit run app/main.py")
    print("  Run MCP:       python src/mcp_server.py")
    print("  Run tests:     pytest tests/ -v")
    print("=" * 50)


if __name__ == "__main__":
    main()
