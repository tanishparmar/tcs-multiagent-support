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
│  (Structured output routing via Pydantic)│
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
| **Observability** | Arize Phoenix + OpenTelemetry |
| **UI** | Streamlit |

---

## Production-Grade Features

### Guardrails

Multi-layer guardrail system (`src/guardrails.py`) protecting every query end-to-end:

| Layer | What it catches |
|---|---|
| **Input — length gate** | Empty queries (<3 chars) or spam inputs (>2000 chars) |
| **Input — prompt injection** | 12 regex patterns: jailbreak, DAN mode, `[INST]` tokens, XML system injection, role-override |
| **Input — off-topic blocking** | 7 patterns block unrelated requests (poems, jokes, code, general Q&A) |
| **SQL — SELECT-only enforcement** | Blocks `DROP`, `DELETE`, `UPDATE`, `INSERT` before reaching the DB |
| **SQL — parameterized queries** | All queries use SQLAlchemy `text()` with bound params — no f-string interpolation |
| **Routing — recursion limit** | Graph capped at 18 hops; FINISH forced after first substantive answer |
| **Output — empty fallback** | Returns a safe error message if the LLM produces no content |
| **Output — hallucination signals** | 6 patterns detect LLM uncertainty; appends a human-review disclaimer automatically |
| **Output — length truncation** | Responses capped at 4000 chars to prevent runaway outputs |
| **RAG — faithfulness check** | Word-overlap ≥15% between answer and retrieved chunks; low-grounding answers are flagged |

---

### Observability & Traceability

Full distributed tracing powered by **Arize Phoenix** (OpenTelemetry-based):

- Phoenix starts automatically as a subprocess when the Streamlit app launches — no manual setup
- `LangChainInstrumentor` auto-instruments every LangChain and LangGraph call with zero manual span writing
- Every query generates a complete trace: supervisor decision → agent selection → tool calls → final response
- Latency, token counts, and retrieval scores captured per span
- Access the live Phoenix dashboard at **http://localhost:6006** while the app is running

The agent graph is also visualized as an interactive Mermaid diagram in the **Agent Graph** page of the Streamlit UI.

---

### Evaluations (Evals)

Golden-dataset evaluation framework in `src/evals/` with 10 hand-crafted test cases covering both agents:

| # | Query | Expected Agent | Keywords |
|---|---|---|---|
| 1 | Standard shipping time | rag_agent | 5, 7, business |
| 2 | Overnight shipping cost | rag_agent | 24.99 |
| 3 | Defective item return window | rag_agent | 60 |
| 4 | Lost package process | rag_agent | 24 hours, support |
| 5 | Premium SLA | rag_agent | premium |
| 6 | Customs responsibility | rag_agent | recipient |
| 7 | Ema Johnson loyalty points | sql_agent | 2450 |
| 8 | Ema Johnson account type | sql_agent | premium |
| 9 | Ema's open tickets | sql_agent | Ema |
| 10 | Total customer count | sql_agent | 26 |

**Metrics evaluated per case:**

| Metric | Description |
|---|---|
| `routing_correct` | Did the supervisor route to the right agent? |
| `answer_has_content` | Is the response substantive (≥30 chars)? |
| `keywords_present` | Do expected domain keywords appear in the answer? |
| `latency_ok` | Did it complete within 20 seconds? |
| `retrieval_relevant` | Are retrieval scores ≥0.35? (RAG cases only) |

```bash
# Run evals
pytest tests/ -v
```

---

### Model Context Protocol (MCP)

`src/mcp_server.py` exposes all agent tools as a FastMCP server, allowing any MCP-compatible AI assistant (Claude Desktop, etc.) to query the same customer data and policy knowledge base:

| Tool | Description |
|---|---|
| `get_customer_profile` | Look up customer by name |
| `get_support_tickets` | All tickets for a customer |
| `get_order_history` | Order history for a customer |
| `run_custom_sql` | Custom SELECT query |
| `search_policies` | Semantic search over policy PDFs |
| `list_policy_documents` | List ingested documents |
| `ingest_policy` | Add a new PDF to the knowledge base |

---

## Project Structure

```
tcs-multiagent-support/
├── README.md
├── requirements.txt
├── .env.example
├── setup_db.py                 # One-command setup (DB + seed + ingest)
│
├── data/
│   ├── seed_data.py            # Synthetic customer data generator (Faker)
│   └── policies/               # Policy PDF documents
│       ├── refund_policy.pdf
│       ├── shipping_policy.pdf
│       └── support_policy.pdf
│
├── src/
│   ├── config.py               # Central config from .env
│   ├── guardrails.py           # Input / output / RAG guardrail system
│   ├── db/
│   │   ├── sql_db.py           # SQLAlchemy models (Customer, Ticket, Order, Product)
│   │   └── vector_db.py        # ChromaDB client (ingest, search, list)
│   ├── tools/
│   │   ├── sql_tools.py        # LangChain @tool wrappers for SQL queries
│   │   └── rag_tools.py        # LangChain @tool wrappers for RAG search
│   ├── agents/
│   │   └── graph.py            # LangGraph supervisor + specialist agents
│   ├── observability/
│   │   └── phoenix_setup.py    # Arize Phoenix auto-instrumentation setup
│   ├── evals/
│   │   ├── metrics.py          # Eval metric functions
│   │   ├── test_cases.py       # 10 golden test cases
│   │   └── runner.py           # Eval runner (returns per-case scores)
│   └── mcp_server.py           # FastMCP server
│
├── app/
│   ├── main.py                 # Streamlit chat UI
│   └── pages/
│       └── 2_Agent_Graph.py    # Mermaid agent graph visualization
│
└── tests/
    ├── test_sql_tools.py
    └── test_rag_tools.py
```

---

## Quick Start

### 1. Prerequisites

- Python 3.11+
- [Ollama](https://ollama.com) installed (`brew install --cask ollama`)

```bash
# Pull the model (one-time, ~2 GB)
ollama pull llama3.2
```

### 2. Install dependencies

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

### 4. One-time setup

```bash
python setup_db.py
```

Creates the SQLite DB, seeds 26 synthetic customers/tickets/orders, and ingests 3 policy PDFs into ChromaDB.

### 5. Launch the app

```bash
# Terminal 1 — Ollama (skip if Ollama app is already open)
ollama serve

# Terminal 2 — Streamlit app
streamlit run app/main.py
```

Open **http://localhost:8501** — Phoenix traces at **http://localhost:6006**.

### 6. (Optional) MCP Server

```bash
python src/mcp_server.py
```

---

## Example Queries

| Query | Agent |
|---|---|
| "Give me an overview of Ema Johnson's profile and ticket history" | SQL Agent |
| "What is the current refund policy?" | RAG Agent |
| "Show me all open critical support tickets" | SQL Agent |
| "What are the shipping timelines for international orders?" | RAG Agent |
| "How many loyalty points does Ema Johnson have?" | SQL Agent |
| "What is the SLA for premium account customers?" | RAG Agent |

---

## Data Model

```sql
customers        -- id, name, email, phone, account_type, location, join_date, loyalty_points
support_tickets  -- id, customer_id, subject, description, category, status, priority, dates, agent_notes
products         -- id, name, category, price, description
orders           -- id, customer_id, product_id, quantity, total_amount, order_date, status
```

**Pre-seeded test customer:** `Ema Johnson` — premium account, New York NY, 2450 loyalty points, 4 support tickets.

---

## Key Design Decisions

- **Pydantic structured output for routing** — supervisor decisions are deterministic, not parsed from free-form LLM text
- **FINISH guard** — code-level rule forces FINISH after first substantive answer, preventing infinite loops regardless of model quality
- **Parameterized SQL everywhere** — SQLAlchemy `text()` with bound params in all tools and MCP server; no raw string interpolation
- **Zero-config tracing** — `LangChainInstrumentor` auto-instruments all LangChain/LangGraph calls without any manual span writing
- **Faithfulness over recall** — RAG answers not grounded in retrieved context get a human-review disclaimer rather than being silently returned
