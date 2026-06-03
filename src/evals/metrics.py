"""
Eval metric functions — all pure, no LLM calls needed.
"""


def routing_correct(actual_agents: list[str], expected_agent: str) -> bool:
    return expected_agent in actual_agents


def answer_has_content(answer: str, min_chars: int = 30) -> bool:
    return (
        len(answer.strip()) >= min_chars
        and "No response generated" not in answer
        and answer.strip() != ""
    )


def keywords_present(answer: str, keywords: list[str]) -> tuple[bool, list[str]]:
    missing = [kw for kw in keywords if kw.lower() not in answer.lower()]
    return len(missing) == 0, missing


def latency_ok(latency_ms: float, limit_ms: float = 20_000) -> bool:
    return latency_ms <= limit_ms


def retrieval_relevant(scores: list[float], threshold: float = 0.35) -> bool:
    return bool(scores) and max(scores) >= threshold


def score_response(
    answer: str,
    actual_agents: list[str],
    expected_agent: str,
    keywords: list[str],
    latency_ms: float,
    retrieval_scores: list[float],
) -> dict:
    routing = routing_correct(actual_agents, expected_agent)
    content = answer_has_content(answer)
    kw_ok, missing_kw = keywords_present(answer, keywords)
    lat_ok = latency_ok(latency_ms)
    retr_ok = retrieval_relevant(retrieval_scores) if retrieval_scores else None

    passed = routing and content and kw_ok and lat_ok
    return {
        "routing_correct": routing,
        "answer_has_content": content,
        "keywords_present": kw_ok,
        "missing_keywords": missing_kw,
        "latency_ok": lat_ok,
        "retrieval_relevant": retr_ok,
        "passed": passed,
    }
