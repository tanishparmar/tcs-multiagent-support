"""
FastMCP server — exposes SQL and RAG tools via the Model Context Protocol.

Run:  python src/mcp_server.py
Test: mcp dev src/mcp_server.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.server.fastmcp import FastMCP
from src.db import vector_db
from src.db.sql_db import engine
from langchain_community.utilities import SQLDatabase

mcp = FastMCP(
    "Customer Support Agent",
    instructions=(
        "This MCP server provides tools to query customer data from a SQL database "
        "and search company policy documents from a vector knowledge base."
    ),
)

_db = SQLDatabase(engine, include_tables=["customers", "support_tickets", "products", "orders"])


# ── SQL Tools ─────────────────────────────────────────────────────────────────

@mcp.tool()
def get_customer_profile(customer_name: str) -> str:
    """Retrieve a customer's profile (account type, email, location, loyalty points)
    by searching their name. Returns the best matching customer."""
    sql = f"""
        SELECT id, name, email, phone, account_type, location, join_date, loyalty_points
        FROM customers WHERE name LIKE '%{customer_name}%' LIMIT 5
    """
    result = _db.run(sql)
    return result or f"No customer found matching '{customer_name}'."


@mcp.tool()
def get_support_tickets(customer_name: str) -> str:
    """Get all support tickets for a customer, including subject, status,
    priority, category, dates, and agent resolution notes."""
    sql = f"""
        SELECT t.id, t.subject, t.category, t.status, t.priority,
               t.created_at, t.resolved_at, t.agent_notes
        FROM support_tickets t
        JOIN customers c ON t.customer_id = c.id
        WHERE c.name LIKE '%{customer_name}%'
        ORDER BY t.created_at DESC
    """
    result = _db.run(sql)
    return result or f"No tickets found for '{customer_name}'."


@mcp.tool()
def get_order_history(customer_name: str) -> str:
    """Get the order history for a customer, including product names,
    quantities, amounts, dates, and fulfilment status."""
    sql = f"""
        SELECT o.id, p.name AS product, o.quantity,
               o.total_amount, o.order_date, o.status
        FROM orders o
        JOIN customers c ON o.customer_id = c.id
        JOIN products p ON o.product_id = p.id
        WHERE c.name LIKE '%{customer_name}%'
        ORDER BY o.order_date DESC
    """
    result = _db.run(sql)
    return result or f"No orders found for '{customer_name}'."


@mcp.tool()
def run_custom_sql(query: str) -> str:
    """Execute a custom read-only SQL SELECT query.
    Available tables: customers, support_tickets, products, orders."""
    if not query.strip().upper().startswith("SELECT"):
        return "Error: only SELECT queries are allowed."
    try:
        return _db.run(query) or "No results."
    except Exception as e:
        return f"SQL error: {e}"


# ── RAG Tools ─────────────────────────────────────────────────────────────────

@mcp.tool()
def search_policies(query: str) -> str:
    """Search the company policy knowledge base for information about
    refunds, returns, shipping, support SLAs, warranties, and procedures."""
    results = vector_db.search(query)
    if not results:
        return "No policy documents loaded. Ingest documents first."
    parts = [
        f"[{r['source']} | score={r['score']}]\n{r['text']}"
        for r in results
    ]
    return "\n\n---\n\n".join(parts)


@mcp.tool()
def list_policy_documents() -> str:
    """List all company policy documents currently in the knowledge base."""
    docs = vector_db.list_documents()
    return "\n".join(docs) if docs else "No documents ingested."


@mcp.tool()
def ingest_policy(file_path: str) -> str:
    """Ingest a policy document (PDF or TXT) into the knowledge base.
    Provide the absolute file path to the document."""
    try:
        count = vector_db.ingest_file(file_path)
        return f"Ingested '{file_path}' — {count} chunks stored."
    except Exception as e:
        return f"Error: {e}"


# ── Resource ──────────────────────────────────────────────────────────────────

@mcp.resource("schema://database")
def database_schema() -> str:
    """Returns the SQL database schema for the customer support system."""
    return _db.get_table_info()


if __name__ == "__main__":
    mcp.run()
