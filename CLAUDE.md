# TCS Multi-Agent Customer Support System

## RTK Rule
Always use rtk instead of raw shell commands (e.g. `rtk git status`, `rtk ls .`, `rtk read file.py`).

## Project Overview
Generative AI Multi-Agent System for customer support. Handles both structured SQL queries (customers, tickets, orders) and unstructured document queries (policy PDFs) via a LangGraph supervisor that routes to specialist agents.

## Architecture
- **Supervisor Agent** — routes queries to SQL or RAG agents using Claude + structured output
- **SQL Agent** — ReAct agent with SQLAlchemy toolkit; answers customer/ticket/order questions
- **RAG Agent** — ReAct agent with ChromaDB retrieval; answers policy/document questions
- **MCP Server** — FastMCP server exposing all tools via Model Context Protocol

## Stack
| Layer | Choice |
|---|---|
| LLM | Claude Sonnet (`claude-sonnet-4-6`) via `langchain-anthropic` |
| Agent framework | LangGraph `StateGraph` + `create_react_agent` |
| SQL DB | SQLite via SQLAlchemy |
| Vector DB | ChromaDB (persistent) |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` |
| MCP | `mcp[cli]` FastMCP |
| UI | Streamlit |

## Key Commands
```bash
# One-time setup
python setup_db.py

# Run the app
streamlit run app/main.py

# Run MCP server (separate terminal)
python src/mcp_server.py

# Run tests
pytest tests/ -v
```

## Environment
Copy `.env.example` → `.env` and set `ANTHROPIC_API_KEY`.
