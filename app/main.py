"""Streamlit UI for the TCS Multi-Agent Customer Support System."""
import sys
import traceback
import logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage
from src.observability import init_phoenix


@st.cache_resource
def _start_phoenix():
    return init_phoenix()

from src.agents.graph import run_query
from src.db import vector_db
from src.db.sql_db import get_session, Customer, SupportTicket, Order

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="TCS Support AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session state ─────────────────────────────────────────────────────────────

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []  # list of {"role": "user"|"assistant", "content": str, "trace": list}

if "docs_ingested" not in st.session_state:
    st.session_state.docs_ingested = False


# ── Sidebar ───────────────────────────────────────────────────────────────────

phoenix_url = _start_phoenix()

with st.sidebar:
    st.title("🤖 TCS Support AI")
    st.caption("Multi-Agent Customer Support System")
    st.divider()

    if phoenix_url:
        st.markdown(f"📡 **[Arize Phoenix Traces]({phoenix_url})** — live observability")
        st.divider()

    # Auto-ingest bundled policy docs on first run
    if not st.session_state.docs_ingested:
        with st.spinner("Loading policy documents…"):
            summary = vector_db.ingest_policy_dir()
            st.session_state.docs_ingested = True

    # Upload additional PDFs
    st.subheader("📄 Upload Policy Documents")
    uploaded = st.file_uploader(
        "Upload PDF or TXT policy files",
        type=["pdf", "txt"],
        accept_multiple_files=True,
        help="Uploaded documents are ingested into the vector knowledge base.",
    )
    if uploaded:
        for uf in uploaded:
            tmp = Path("/tmp") / uf.name
            tmp.write_bytes(uf.read())
            count = vector_db.ingest_file(tmp)
            st.success(f"✓ {uf.name} — {count} chunks ingested")

    # Show ingested docs
    st.subheader("📚 Knowledge Base")
    docs = vector_db.list_documents()
    if docs:
        for d in docs:
            st.markdown(f"  • `{d}`")
    else:
        st.caption("No documents loaded yet.")

    st.divider()

    # DB stats
    st.subheader("🗄️ Database Stats")
    try:
        session = get_session()
        n_customers = session.query(Customer).count()
        n_tickets = session.query(SupportTicket).count()
        n_orders = session.query(Order).count()
        session.close()
        col1, col2 = st.columns(2)
        col1.metric("Customers", n_customers)
        col2.metric("Tickets", n_tickets)
        st.metric("Orders", n_orders)
    except Exception:
        st.caption("Run `python setup_db.py` first.")

    st.divider()

    # Example queries
    st.subheader("💡 Try asking")
    examples = [
        "Give me a full overview of customer Ema's profile and tickets",
        "What is the current refund policy?",
        "Show me all open critical tickets",
        "What are the shipping timelines for international orders?",
        "How many tickets does Ema Johnson have and what are their statuses?",
        "What is the SLA for premium account customers?",
    ]
    for ex in examples:
        if st.button(ex, use_container_width=True, key=ex):
            st.session_state.pending_query = ex

    st.divider()
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.chat_history = []
        st.rerun()


# ── Main chat area ────────────────────────────────────────────────────────────

st.title("Customer Support AI Assistant")
st.caption(
    "Ask anything about customers, tickets, orders, or company policies. "
    "Powered by Claude + LangGraph multi-agent system."
)

# Render chat history
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("trace"):
            agent_labels = {"sql_agent": "🗄️ SQL Agent", "rag_agent": "📄 RAG Agent"}
            trace_text = " → ".join(agent_labels.get(a, a) for a in msg["trace"])
            st.caption(f"Routed through: {trace_text}")

# Handle example button clicks
pending = st.session_state.pop("pending_query", None)

# Chat input
user_input = st.chat_input("Ask about a customer, ticket, policy…") or pending

if user_input:
    # Append and display user message
    st.session_state.chat_history.append({"role": "user", "content": user_input, "trace": []})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Run through the agent graph
    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            try:
                answer, trace, _ = run_query(user_input)
                error_detail = None
            except Exception as e:
                answer = f"⚠️ **Error:** `{e}`"
                error_detail = traceback.format_exc()
                trace = []

        st.markdown(answer)
        if error_detail:
            with st.expander("Full error traceback"):
                st.code(error_detail, language="python")
        if trace:
            agent_labels = {"sql_agent": "🗄️ SQL Agent", "rag_agent": "📄 RAG Agent"}
            trace_text = " → ".join(agent_labels.get(a, a) for a in trace)
            st.caption(f"Routed through: {trace_text}")

    st.session_state.chat_history.append(
        {"role": "assistant", "content": answer, "trace": trace}
    )
