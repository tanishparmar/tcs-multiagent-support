"""Tests for SQL tools — requires DB to be seeded (run setup_db.py first)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from src.db.sql_db import init_db, get_session, Customer, SupportTicket


@pytest.fixture(autouse=True, scope="module")
def setup_database():
    """Ensure tables exist before any SQL tool test."""
    init_db()


def test_search_customers_by_name():
    from src.tools.sql_tools import search_customers
    result = search_customers.invoke({"query": "Ema"})
    assert "Ema Johnson" in result or "ema" in result.lower()


def test_search_customers_no_match():
    from src.tools.sql_tools import search_customers
    result = search_customers.invoke({"query": "ZZZNOMATCH12345"})
    assert "No customers found" in result


def test_get_customer_tickets():
    from src.tools.sql_tools import get_customer_tickets
    result = get_customer_tickets.invoke({"customer_name": "Ema"})
    # Either finds tickets or correctly reports none
    assert isinstance(result, str)
    assert len(result) > 0


def test_get_customer_orders():
    from src.tools.sql_tools import get_customer_orders
    result = get_customer_orders.invoke({"customer_name": "Ema"})
    assert isinstance(result, str)


def test_get_customer_full_profile():
    from src.tools.sql_tools import get_customer_full_profile
    result = get_customer_full_profile.invoke({"customer_name": "Ema"})
    assert "CUSTOMER PROFILE" in result
    assert "SUPPORT TICKETS" in result
    assert "ORDER HISTORY" in result


def test_run_sql_query_select():
    from src.tools.sql_tools import run_sql_query
    result = run_sql_query.invoke({"sql": "SELECT COUNT(*) FROM customers"})
    assert isinstance(result, str)
    # Should return a number
    assert any(char.isdigit() for char in result)


def test_run_sql_query_blocked_non_select():
    from src.tools.sql_tools import run_sql_query
    result = run_sql_query.invoke({"sql": "DROP TABLE customers"})
    assert "only SELECT" in result


def test_ticket_statistics():
    from src.tools.sql_tools import get_ticket_statistics
    result = get_ticket_statistics.invoke({})
    assert isinstance(result, str)
