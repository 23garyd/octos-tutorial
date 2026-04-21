import os
import socket
from urllib.parse import urlparse

import pytest

from .conftest import assert_markers, requires_dora, run_dataflow
from .expected_markers import EXAMPLE_03

DEFAULT_OLLAMA_URL = "http://localhost:11434/v1"


def _llm_reachable(base: str) -> bool:
    """Cheap TCP probe — does not perform an HTTP request."""
    u = urlparse(base)
    host = u.hostname or "localhost"
    port = u.port or (443 if u.scheme == "https" else 80)
    try:
        with socket.create_connection((host, port), timeout=1.5):
            return True
    except OSError:
        return False


@pytest.mark.smoke
@requires_dora
@pytest.mark.skipif(
    not _llm_reachable(os.environ.get("OPENAI_API_BASE", DEFAULT_OLLAMA_URL)),
    reason="no reachable OpenAI-compatible LLM endpoint (set OPENAI_API_BASE or run Ollama)",
)
def test_03_llm_agent(dora_daemon):
    """03-llm-agent hard-codes OpenAIProvider (no MockProvider fallback in the
    example). Skip when no LLM endpoint is reachable; run when one is."""
    run = run_dataflow("03-llm-agent")
    assert run.returncode == 0, f"dora exited {run.returncode}\nstderr:\n{run.stderr[-1000:]}"
    assert_markers(run.stdout, EXAMPLE_03)
