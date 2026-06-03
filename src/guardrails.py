"""
Guardrails for the TCS Multi-Agent Customer Support System.

Layers:
  1. Input guardrails  — validate user query before hitting the LLM
  2. Output guardrails — validate / sanitize LLM response before showing user
  3. SQL guardrails    — enforced inside sql_tools.py (SELECT-only + parameterized)
"""
import re
import logging

log = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

MIN_QUERY_LEN = 3
MAX_QUERY_LEN = 2000
MAX_RESPONSE_LEN = 4000

# ── Prompt injection patterns ──────────────────────────────────────────────────

_INJECTION_PATTERNS = [
    r"ignore\s+(previous|all|prior|above)\s+instructions",
    r"forget\s+(everything|all|your\s+instructions)",
    r"you\s+are\s+now\s+a",
    r"act\s+as\s+(a|an)\s+\w+",
    r"pretend\s+(you\s+are|to\s+be)",
    r"(disregard|override|bypass)\s+(your|the)\s+(system|instructions|rules|prompt)",
    r"jailbreak",
    r"DAN\s+mode",
    r"developer\s+mode",
    r"prompt\s+injection",
    r"<\s*system\s*>",           # XML-style system prompt injection
    r"\[INST\]|\[\/INST\]",      # Llama instruction tokens
]

# ── Off-topic patterns (not customer support) ─────────────────────────────────

_OFF_TOPIC_PATTERNS = [
    r"write\s+(me\s+)?(a\s+)?(poem|song|story|essay|novel|lyrics)",
    r"(what\s+is\s+the\s+)?(meaning\s+of\s+life|capital\s+of|population\s+of)",
    r"(tell\s+me\s+a\s+joke|make\s+me\s+laugh)",
    r"play\s+(a\s+game|chess|tic.tac.toe)",
    r"(translate|summarise|summarize)\s+this\s+(text|document|article|book)",
    r"write\s+(code|a\s+function|a\s+script)\s+for",
    r"(what\s+is\s+|explain\s+)(quantum|general\s+relativity|black\s+hole)",
]

# ── Hallucination / uncertainty signals in responses ─────────────────────────

_HALLUCINATION_SIGNALS = [
    r"i\s+(don'?t|do\s+not)\s+(have\s+access|know)\s+to",
    r"i\s+cannot\s+(access|provide|find)\s+real.time",
    r"as\s+of\s+my\s+(last\s+)?(knowledge\s+)?cutoff",
    r"i\s+am\s+(just\s+)?an?\s+(ai|language\s+model)",
    r"i\s+may\s+be\s+(wrong|hallucinating|mistaken)",
    r"i\s+made\s+(that\s+)?(up|an\s+error)",
]


# ── Input Guardrails ──────────────────────────────────────────────────────────

class InputGuardrailError(ValueError):
    pass


def validate_input(query: str) -> str:
    """Validate user query. Returns cleaned query or raises InputGuardrailError."""
    query = query.strip()

    # 1. Length
    if len(query) < MIN_QUERY_LEN:
        raise InputGuardrailError("Query is too short. Please ask a complete question.")
    if len(query) > MAX_QUERY_LEN:
        raise InputGuardrailError(
            f"Query exceeds maximum length ({MAX_QUERY_LEN} chars). Please shorten your question."
        )

    # 2. Prompt injection
    for pattern in _INJECTION_PATTERNS:
        if re.search(pattern, query, re.IGNORECASE):
            log.warning("Prompt injection attempt blocked: %s", query[:100])
            raise InputGuardrailError(
                "I can only assist with customer support queries. "
                "Please ask about customers, orders, tickets, or company policies."
            )

    # 3. Off-topic
    for pattern in _OFF_TOPIC_PATTERNS:
        if re.search(pattern, query, re.IGNORECASE):
            log.info("Off-topic query blocked: %s", query[:100])
            raise InputGuardrailError(
                "I'm a customer support assistant. I can only help with "
                "customer profiles, orders, support tickets, and company policies."
            )

    return query


# ── Output Guardrails ─────────────────────────────────────────────────────────

def validate_output(answer: str, query: str) -> str:
    """Validate and sanitize LLM response. Returns cleaned answer."""
    if not answer or len(answer.strip()) < 5:
        log.warning("Empty or trivial response for query: %s", query[:80])
        return (
            "I was unable to find information to answer your question. "
            "Please rephrase or contact support directly."
        )

    # Detect hallucination signals and add a disclaimer
    for pattern in _HALLUCINATION_SIGNALS:
        if re.search(pattern, answer, re.IGNORECASE):
            log.warning("Potential hallucination detected in response.")
            answer = (
                answer
                + "\n\n⚠️ _Note: This response may contain uncertain information. "
                "Please verify with a human agent for critical decisions._"
            )
            break

    # Truncate excessively long responses
    if len(answer) > MAX_RESPONSE_LEN:
        answer = answer[:MAX_RESPONSE_LEN] + "\n\n_(Response truncated for brevity.)_"
        log.info("Response truncated to %d chars.", MAX_RESPONSE_LEN)

    return answer


# ── RAG Faithfulness Check ────────────────────────────────────────────────────

def check_rag_faithfulness(answer: str, retrieved_chunks: list[str]) -> bool:
    """
    Basic faithfulness check: does the answer contain at least some
    tokens that appear in the retrieved context?

    Returns True if answer appears grounded, False if likely hallucinated.
    """
    if not retrieved_chunks:
        return True  # No context to check against

    context = " ".join(retrieved_chunks).lower()
    answer_words = set(re.findall(r"\b[a-z]{4,}\b", answer.lower()))
    context_words = set(re.findall(r"\b[a-z]{4,}\b", context))

    if not answer_words:
        return False

    overlap = answer_words & context_words
    score = len(overlap) / len(answer_words)
    log.info("RAG faithfulness overlap score: %.2f (%d/%d words)", score, len(overlap), len(answer_words))
    return score >= 0.15  # At least 15% of answer words appear in retrieved context
