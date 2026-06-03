"""
Arize Phoenix observability setup.

Starts the Phoenix server as a subprocess on port 6006, then registers
OpenTelemetry to auto-instrument all LangChain / LangGraph calls.

Phoenix UI: http://localhost:6006
"""
import logging
import subprocess
import sys
import time

log = logging.getLogger(__name__)

PHOENIX_URL = "http://localhost:6006"
_initialized = False


def _phoenix_ready(timeout: int = 10) -> bool:
    import urllib.request, urllib.error
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(PHOENIX_URL, timeout=1)
            return True
        except Exception:
            time.sleep(0.5)
    return False


def init_phoenix(project_name: str = "tcs-multiagent-support") -> str | None:
    """Start the Phoenix server (if not already running) and instrument LangChain."""
    global _initialized
    if _initialized:
        return PHOENIX_URL

    try:
        from openinference.instrumentation.langchain import LangChainInstrumentor
        from phoenix.otel import register

        # Start Phoenix server as a background subprocess if not already running
        if not _phoenix_ready(timeout=1):
            log.info("Starting Arize Phoenix server…")
            subprocess.Popen(
                [sys.executable, "-m", "phoenix.server.main", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if not _phoenix_ready(timeout=12):
                log.warning("Phoenix server did not start in time.")
                return None

        # Register OTEL tracer → Phoenix
        tracer_provider = register(
            project_name=project_name,
            endpoint=f"{PHOENIX_URL}/v1/traces",
        )

        # Auto-instrument every LangChain / LangGraph call
        LangChainInstrumentor().instrument(tracer_provider=tracer_provider)

        _initialized = True
        log.info("Arize Phoenix ready at %s", PHOENIX_URL)
        return PHOENIX_URL

    except ImportError:
        log.warning("Install: pip install arize-phoenix openinference-instrumentation-langchain")
        return None
    except Exception as exc:
        log.warning("Could not start Phoenix: %s", exc)
        return None
