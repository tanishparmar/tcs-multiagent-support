"""
Eval runner — executes the golden test suite and returns scored results.

Usage:
    python src/evals/runner.py          # CLI table output
    results = run_evals()               # from code / Streamlit
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.agents.graph import run_query
from src.evals.metrics import score_response
from src.evals.test_cases import EVAL_CASES


def run_evals(cases: list[dict] | None = None) -> list[dict]:
    """Run eval suite and return scored result dicts."""
    cases = cases or EVAL_CASES
    results = []

    for case in cases:
        start = time.time()
        try:
            answer, agents, meta = run_query(case["query"])
            latency_ms = (time.time() - start) * 1000
            retrieval_scores = meta.get("retrieval_scores", [])
            error = None
        except Exception as exc:
            answer = ""
            agents = []
            latency_ms = (time.time() - start) * 1000
            retrieval_scores = []
            error = str(exc)

        scores = score_response(
            answer=answer,
            actual_agents=agents,
            expected_agent=case["expected_agent"],
            keywords=case["keywords"],
            latency_ms=latency_ms,
            retrieval_scores=retrieval_scores,
        )

        results.append(
            {
                "id": case["id"],
                "query": case["query"],
                "expected_agent": case["expected_agent"],
                "actual_agents": agents,
                "answer_preview": answer[:120] + "…" if len(answer) > 120 else answer,
                "latency_ms": round(latency_ms, 0),
                "error": error,
                **scores,
            }
        )

    return results


def print_report(results: list[dict]) -> None:
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    print(f"\n{'='*70}")
    print(f"  Eval Report — {passed}/{total} passed")
    print(f"{'='*70}")
    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"  [{status}] {r['id']:8s}  {r['latency_ms']:6.0f}ms  {r['query'][:55]}")
        if not r["passed"]:
            if not r["routing_correct"]:
                print(f"           routing: expected={r['expected_agent']} actual={r['actual_agents']}")
            if not r["answer_has_content"]:
                print(f"           answer empty or too short")
            if not r["keywords_present"]:
                print(f"           missing keywords: {r['missing_keywords']}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    print("Running eval suite (requires Ollama to be running)…")
    results = run_evals()
    print_report(results)
