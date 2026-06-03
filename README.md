# TCS Multi-Agent Customer Support System

A production-ready Generative AI **Multi-Agent System** built for the TCS AI/ML Developer Pre-Qualification Assessment. It enables natural language interaction with both structured customer data (SQL) and unstructured policy documents (RAG) through a LangGraph supervisor that intelligently routes queries to specialist agents.

---

## Architecture

```
User Query
    │
    ▼
┌─────────────────────────────────────────┐
│          Supervisor Agent               │
│   (Claude + structured output routing)  │
└───────────────┬─────────────────────────┘
                │
        ┌───────┴────────┐
        ▼                ▼
┌──────────────┐  ┌──────────────┐
│  SQL Agent   │  │  RAG Agent   │
│  (ReAct)     │  │  (ReAct)     │
│              │  │              │
│ ▸ customers  │  │ ▸ refund     │
│ ▸ tickets    │  │   policy     │
│ ▸ orders     │  │ ▸ shipping   │
│ ▸ products   │  │   policy     │
└──────┬───────┘  └──────┬───────┘
       │                 │
       ▼                 ▼
  SQLite DB         ChromaDB
  (SQLAlchemy)   (sentence-transformers)
       │
       ▼
  FastMCP Server  ←─── External AI tools
```

| Component | Technology |
|---|---|
| **LLM** | Llama 3.2 (local, free) via Ollama + `langchain-ollama` |
| **Agent Framework** | LangGraph `StateGraph` + `create_react_agent` |
| **SQL Database** | SQLite via SQLAlchemy |
| **Vector Database** | ChromaDB (persistent) |
| **Embeddings** | `sentence-transformers/all-MiniLM-L6-v2` |
| **MCP Server** | FastMCP (`mcp[cli]`) |
| **UI** | Streamlit |

---

## Project Structure

```
tcs-multiagent-support/
├── CLAUDE.md                   # RTK rule + project docs for Claude Code
├── README.md
├── requirements.txt
├── .env.example
├── setup_db.py                 # One-command setup (DB + seed + ingest)
│
├── data/
│   ├── seed_data.py            # Synthetic customer data generator
│   └── policies/               # Policy documents (TXT/PDF)
│       ├── refund_policy.txt
│       ├── shipping_policy.txt
│       └── support_policy.txt
│
├── src/
│   ├── config.py               # Central config from .env
│   ├── db/
│   │   ├── sql_db.py           # SQLAlchemy models (Customer, Ticket, Order, Product)
│   │   └── vector_db.py        # ChromaDB client (ingest, search, list)
│   ├── tools/
│   │   ├── sql_tools.py        # LangChain @tool wrappers for SQL queries
│   │   └── rag_tools.py        # LangChain @tool wrappers for RAG search
│   ├── agents/
│   │   └── graph.py            # LangGraph supervisor + specialist agents
│   └── mcp_server.py           # FastMCP server
│
├── app/
│   └── main.py                 # Streamlit chat UI
│
└── tests/
    ├── test_sql_tools.py
    └── test_rag_tools.py
```

---

## Quick Start

### 1. Prerequisites

- Python 3.11+
- [Ollama](https://ollama.com) installed and running (free, local LLM — no API key needed)

```bash
# Install Ollama (macOS)
brew install ollama

# Pull the model (one-time download ~2 GB)
ollama pull llama3.2
```

### 2. Create virtual environment and install dependencies

```bash
cd tcs-multiagent-support
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# No changes needed — defaults work out of the box
```

### 4. Run one-time setup

```bash
python setup_db.py
```

This will:
- Create the SQLite database with all tables
- Seed 26 synthetic customers, tickets, and orders (including test customer **Ema Johnson**)
- Ingest the 3 bundled policy documents into ChromaDB

### 5. Launch the app

```bash
streamlit run app/main.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

### 6. (Optional) Run the MCP Server

In a separate terminal:

```bash
python src/mcp_server.py
```

---

## Example Queries

| Query | Agent Used |
|---|---|
| "Give me an overview of customer Ema's profile and ticket history" | SQL Agent |
| "What is the current refund policy?" | RAG Agent |
| "Show me all open critical support tickets" | SQL Agent |
| "What are the shipping timelines for international orders?" | RAG Agent |
| "How many loyalty points does Ema Johnson have?" | SQL Agent |
| "What is the SLA for premium account customers?" | RAG Agent |

---

## Data Model

```sql
customers        -- id, name, email, phone, account_type, location, join_date, loyalty_points
support_tickets  -- id, customer_id, subject, description, category, status, priority, dates
products         -- id, name, category, price, description
orders           -- id, customer_id, product_id, quantity, total_amount, order_date, status
```

**Pre-seeded test customer:** `Ema Johnson` (premium account, New York, NY) with 4 rich support tickets covering returns, technical issues, and billing disputes.

---

## Running Tests

```bash
# Requires setup_db.py to have been run first
pytest tests/ -v
```

---

## MCP Server Tools

The FastMCP server exposes these tools for external AI assistants:

| Tool | Description |
|---|---|
| `get_customer_profile` | Look up a customer by name |
| `get_support_tickets` | Get all tickets for a customer |
| `get_order_history` | Get order history for a customer |
| `run_custom_sql` | Run a custom SELECT query |
| `search_policies` | Semantic search over policy documents |
| `list_policy_documents` | List all ingested documents |
| `ingest_policy` | Add a new document to the knowledge base |

---

## Key Design Decisions

- **Supervisor uses structured output** (`pydantic` schema) so routing decisions are deterministic — no parsing fragile LLM text.
- **Max iterations guard** — the graph returns to supervisor after each agent call, preventing infinite loops.
- **ChromaDB `upsert`** — re-ingesting the same document replaces existing chunks, avoiding duplicates.
- **SQL injection prevention** — all tool inputs use `LIKE '%query%'` on known columns; `run_sql_query` enforces SELECT-only.
- **RTK hook** — all Bash commands in this project are automatically rewritten through `rtk hook claude` for 60–90% token savings.
