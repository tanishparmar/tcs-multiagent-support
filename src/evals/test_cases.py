"""
Golden eval dataset — ground-truth query/agent/keyword triples.

Each case defines:
  query          — the user input
  expected_agent — which specialist should handle it
  keywords       — substrings that must appear in a correct answer
"""

EVAL_CASES = [
    # ── RAG cases (policy documents) ─────────────────────────────────────────
    {
        "id": "rag_01",
        "query": "How long does standard shipping take?",
        "expected_agent": "rag_agent",
        "keywords": ["5", "7", "business"],
    },
    {
        "id": "rag_02",
        "query": "How much does overnight shipping cost?",
        "expected_agent": "rag_agent",
        "keywords": ["24.99"],
    },
    {
        "id": "rag_03",
        "query": "What is the return window for a defective product?",
        "expected_agent": "rag_agent",
        "keywords": ["60"],
    },
    {
        "id": "rag_04",
        "query": "My package says delivered but I never received it. What should I do?",
        "expected_agent": "rag_agent",
        "keywords": ["24 hours", "support"],
    },
    {
        "id": "rag_05",
        "query": "What is the SLA response time for premium account customers?",
        "expected_agent": "rag_agent",
        "keywords": ["premium"],
    },
    {
        "id": "rag_06",
        "query": "Who pays customs duties on international orders?",
        "expected_agent": "rag_agent",
        "keywords": ["recipient"],
    },
    # ── SQL cases (structured customer data) ──────────────────────────────────
    {
        "id": "sql_01",
        "query": "How many loyalty points does Ema Johnson have?",
        "expected_agent": "sql_agent",
        "keywords": ["2450"],
    },
    {
        "id": "sql_02",
        "query": "What account type does Ema Johnson have?",
        "expected_agent": "sql_agent",
        "keywords": ["premium"],
    },
    {
        "id": "sql_03",
        "query": "Show me the open support tickets for Ema Johnson.",
        "expected_agent": "sql_agent",
        "keywords": ["Ema"],
    },
    {
        "id": "sql_04",
        "query": "How many customers are in the database?",
        "expected_agent": "sql_agent",
        "keywords": ["26"],
    },
]
