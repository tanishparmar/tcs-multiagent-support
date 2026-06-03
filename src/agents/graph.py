"""
LangGraph multi-agent supervisor.

Flow:
  START → supervisor → (sql_agent | rag_agent) → supervisor → … → END

The supervisor uses structured output to decide routing.
Each specialist agent is a ReAct loop with its own tool set.
"""
from __future__ import annotations

import logging
import re
import time
from typing import Annotated, Literal, TypedDict

from langchain_ollama import ChatOllama
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel

from src.config import config
from src.tools.rag_tools import get_rag_tools
from src.tools.sql_tools import get_sql_tools, get_db_schema

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# ── Routing schema ────────────────────────────────────────────────────────────

class RouteDecision(BaseModel):
    next: Literal["sql_agent", "rag_agent", "FINISH"]
    reasoning: str


# ── Shared state ──────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    next: str
    agent_trace: list[str]


# ── Prompts ───────────────────────────────────────────────────────────────────

SUPERVISOR_PROMPT = """You are a routing supervisor for a customer support AI system.
Your ONLY job is to decide which agent handles the next step. You do NOT answer questions yourself.

ROUTING RULES — follow these exactly:

1. Choose "rag_agent" for ANY question about:
   - Shipping times, costs, delivery, tracking, carriers
   - Refund or return policy, timelines, procedures
   - Support SLA, response times, priority tiers, escalation
   - Company policies, warranty, terms of service

2. Choose "sql_agent" for ANY question about:
   - A specific customer's profile, account, loyalty points
   - A specific customer's support tickets or history
   - A specific customer's orders or purchases
   - Ticket counts, statistics, open/closed tickets

3. Choose "FINISH" ONLY when an agent has already responded AND the user's question is fully answered.
   NEVER choose FINISH as the first action — always call an agent first.

EXAMPLES:
- "How long does shipping take?" → rag_agent
- "What is the refund policy?" → rag_agent
- "What is the SLA for premium customers?" → rag_agent
- "Show me Ema's profile" → sql_agent
- "How many open tickets are there?" → sql_agent
- "Give me Ema's order history" → sql_agent

Now decide for the current conversation."""

SQL_AGENT_PROMPT = """You are a SQL specialist for a customer support system.
You have access to these database tables:
{schema}

Answer the user's question by querying the database. Be concise and specific.
Always format results in a readable way. If data is missing, say so clearly."""

RAG_AGENT_PROMPT = """You are a policy and document specialist for a customer support system.
Use the search tools to find relevant policy information, then give a clear,
context-aware summary. Cite which document or policy section your answer comes from.
If no relevant document is found, say so and suggest the user contact support."""


def _extract_text(content) -> str:
    """Safely extract plain text from an AIMessage content field.

    Ollama may return content as a list of dicts like [{"type": "text", "text": "..."}]
    instead of a plain string.
    """
    if not content:
        return ""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                parts.append(part.get("text", ""))
            elif isinstance(part, str):
                parts.append(part)
        return " ".join(parts).strip()
    return str(content).strip()


# ── Graph builder ─────────────────────────────────────────────────────────────

def build_graph() -> "CompiledGraph":
    log.info("Building agent graph with model=%s", config.LLM_MODEL)
    llm = ChatOllama(
        model=config.LLM_MODEL,
        temperature=0,
    )

    supervisor_llm = llm.with_structured_output(RouteDecision)

    sql_agent = create_react_agent(
        llm,
        get_sql_tools(),
        prompt=SQL_AGENT_PROMPT.format(schema=get_db_schema()),
    )
    rag_agent = create_react_agent(
        llm,
        get_rag_tools(),
        prompt=RAG_AGENT_PROMPT,
    )

    def supervisor_node(state: AgentState) -> dict:
        log.info("Supervisor node called. Messages so far: %d", len(state["messages"]))

        # Find if any agent has already produced a substantive text response
        substantive_answer = None
        for m in state["messages"]:
            if isinstance(m, AIMessage):
                text = _extract_text(m.content)
                if text and len(text) > 20:
                    substantive_answer = text

        # If an agent already answered, always FINISH — don't let the small model loop
        if substantive_answer:
            log.info("Agent already gave a substantive response — forcing FINISH")
            return {"next": "FINISH"}

        decision: RouteDecision = supervisor_llm.invoke(
            [SystemMessage(content=SUPERVISOR_PROMPT)] + state["messages"]
        )
        log.info("Supervisor routed to: %s | reason: %s", decision.next, decision.reasoning)

        # Safety: never FINISH before any agent has been called
        if decision.next == "FINISH":
            log.warning("Supervisor chose FINISH before any agent responded — overriding to rag_agent")
            decision.next = "rag_agent"

        return {"next": decision.next}

    def make_agent_node(agent, label: str):
        def node(state: AgentState) -> dict:
            log.info("Running agent: %s", label)
            result = agent.invoke({"messages": state["messages"]})
            new_messages = result["messages"][len(state["messages"]):]
            log.info(
                "Agent %s produced %d new message(s): %s",
                label,
                len(new_messages),
                [type(m).__name__ for m in new_messages],
            )
            for m in new_messages:
                text = _extract_text(m.content)
                if text:
                    log.info("  [%s] content preview: %s", type(m).__name__, text[:200])
            trace = state.get("agent_trace", []) + [label]
            return {"messages": new_messages, "agent_trace": trace}
        return node

    sql_node = make_agent_node(sql_agent, "sql_agent")
    rag_node = make_agent_node(rag_agent, "rag_agent")

    graph = StateGraph(AgentState)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("sql_agent", sql_node)
    graph.add_node("rag_agent", rag_node)

    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges(
        "supervisor",
        lambda s: s["next"],
        {"sql_agent": "sql_agent", "rag_agent": "rag_agent", "FINISH": END},
    )
    graph.add_edge("sql_agent", "supervisor")
    graph.add_edge("rag_agent", "supervisor")

    log.info("Graph compiled successfully.")
    return graph.compile()


_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def _extract_retrieval_scores(messages: list) -> list[float]:
    scores = []
    for m in messages:
        if isinstance(m, ToolMessage):
            for match in re.finditer(r"Relevance:\s*([\d.]+)", str(m.content)):
                scores.append(float(match.group(1)))
    return scores


def run_query(user_message: str) -> tuple[str, list[str], dict]:
    """Run a query through the multi-agent graph.

    Returns (answer, agent_trace, meta) where meta contains latency_ms and
    retrieval_scores for observability / evals.
    """
    log.info("run_query called: %s", user_message)
    t0 = time.time()
    graph = get_graph()
    had_error = False

    try:
        result = graph.invoke(
            {
                "messages": [HumanMessage(content=user_message)],
                "next": "",
                "agent_trace": [],
            },
            config={"recursion_limit": config.MAX_AGENT_ITERATIONS * 3},
        )
    except Exception:
        log.exception("Graph invocation failed")
        raise
    finally:
        latency_ms = (time.time() - t0) * 1000

    messages = result.get("messages", [])
    agent_trace = result.get("agent_trace", [])

    log.info("Graph finished. messages=%d trace=%s latency=%.0fms", len(messages), agent_trace, latency_ms)
    for i, m in enumerate(messages):
        log.info("  msg[%d] %s: %r", i, type(m).__name__, str(m.content)[:150])

    # Find the last AIMessage with actual text
    answer = ""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            text = _extract_text(msg.content)
            if text:
                answer = text
                log.info("Answer selected: %s", answer[:200])
                break

    if not answer:
        for msg in reversed(messages):
            if isinstance(msg, ToolMessage):
                text = _extract_text(msg.content)
                if text:
                    answer = text
                    log.info("Fallback to ToolMessage answer")
                    break

    if not answer:
        answer = "_(No response generated. Check terminal logs for details.)_"
        had_error = True
        log.warning("No answer found in any message.")

    retrieval_scores = _extract_retrieval_scores(messages)
    meta = {"latency_ms": latency_ms, "retrieval_scores": retrieval_scores}

    return answer, agent_trace, meta
