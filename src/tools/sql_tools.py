from langchain_core.tools import tool
from langchain_community.utilities import SQLDatabase
from src.config import config
from src.db.sql_db import engine

_db = SQLDatabase(engine, include_tables=["customers", "support_tickets", "products", "orders"])


def get_db_schema() -> str:
    return _db.get_table_info()


@tool
def search_customers(query: str) -> str:
    """Search for customers by name, email, account type, or location.
    Provide a partial name, email address, or any customer attribute.
    Returns matching customer profiles with loyalty points and account details."""
    sql = f"""
        SELECT id, name, email, phone, account_type, location, join_date, loyalty_points
        FROM customers
        WHERE name LIKE '%{query}%'
           OR email LIKE '%{query}%'
           OR account_type LIKE '%{query}%'
           OR location LIKE '%{query}%'
        LIMIT 10
    """
    result = _db.run(sql)
    return result if result else f"No customers found matching '{query}'."


@tool
def get_customer_tickets(customer_name: str) -> str:
    """Retrieve all support tickets for a specific customer by name.
    Returns ticket subjects, categories, statuses, priorities, dates, and agent notes."""
    sql = f"""
        SELECT t.id, t.subject, t.category, t.status, t.priority,
               t.created_at, t.resolved_at, t.agent_notes
        FROM support_tickets t
        JOIN customers c ON t.customer_id = c.id
        WHERE c.name LIKE '%{customer_name}%'
        ORDER BY t.created_at DESC
    """
    result = _db.run(sql)
    return result if result else f"No tickets found for customer '{customer_name}'."


@tool
def get_customer_orders(customer_name: str) -> str:
    """Retrieve all orders placed by a specific customer.
    Returns product names, quantities, amounts, order dates, and statuses."""
    sql = f"""
        SELECT o.id AS order_id, p.name AS product, o.quantity,
               o.total_amount, o.order_date, o.status
        FROM orders o
        JOIN customers c ON o.customer_id = c.id
        JOIN products p ON o.product_id = p.id
        WHERE c.name LIKE '%{customer_name}%'
        ORDER BY o.order_date DESC
    """
    result = _db.run(sql)
    return result if result else f"No orders found for customer '{customer_name}'."


@tool
def get_customer_full_profile(customer_name: str) -> str:
    """Get the complete 360° profile of a customer: personal details, account info,
    all support tickets, and order history. Use this for a comprehensive overview."""
    profile_sql = f"""
        SELECT id, name, email, phone, account_type, location, join_date, loyalty_points
        FROM customers WHERE name LIKE '%{customer_name}%' LIMIT 1
    """
    profile = _db.run(profile_sql)
    if not profile:
        return f"Customer '{customer_name}' not found."

    tickets_sql = f"""
        SELECT t.id, t.subject, t.category, t.status, t.priority, t.created_at, t.resolved_at
        FROM support_tickets t
        JOIN customers c ON t.customer_id = c.id
        WHERE c.name LIKE '%{customer_name}%'
        ORDER BY t.created_at DESC
    """
    tickets = _db.run(tickets_sql)

    orders_sql = f"""
        SELECT o.id, p.name AS product, o.quantity, o.total_amount, o.order_date, o.status
        FROM orders o
        JOIN customers c ON o.customer_id = c.id
        JOIN products p ON o.product_id = p.id
        WHERE c.name LIKE '%{customer_name}%'
        ORDER BY o.order_date DESC
    """
    orders = _db.run(orders_sql)

    return (
        f"=== CUSTOMER PROFILE ===\n{profile}\n\n"
        f"=== SUPPORT TICKETS ===\n{tickets or 'No tickets.'}\n\n"
        f"=== ORDER HISTORY ===\n{orders or 'No orders.'}"
    )


@tool
def run_sql_query(sql: str) -> str:
    """Execute a read-only SQL SELECT query against the customer support database.
    Tables: customers, support_tickets, products, orders.
    Only SELECT statements are allowed. Use this for custom analytical queries."""
    sql_clean = sql.strip().rstrip(";")
    if not sql_clean.upper().startswith("SELECT"):
        return "Error: only SELECT queries are permitted."
    try:
        return _db.run(sql_clean) or "Query returned no results."
    except Exception as e:
        return f"SQL error: {e}"


@tool
def get_ticket_statistics() -> str:
    """Get aggregate statistics about support tickets: counts by status, category,
    and priority. Useful for understanding overall support volume and patterns."""
    sql = """
        SELECT
            status,
            COUNT(*) AS ticket_count,
            COUNT(CASE WHEN priority = 'critical' THEN 1 END) AS critical,
            COUNT(CASE WHEN priority = 'high' THEN 1 END) AS high
        FROM support_tickets
        GROUP BY status
        ORDER BY ticket_count DESC
    """
    return _db.run(sql) or "No ticket data available."


def get_sql_tools() -> list:
    return [
        search_customers,
        get_customer_tickets,
        get_customer_orders,
        get_customer_full_profile,
        run_sql_query,
        get_ticket_statistics,
    ]
