"""LLM client factory for the inventory agent (Ollama Cloud / any OpenAI-compatible API)."""
from __future__ import annotations

from src.config import AGENT_TEMPERATURE, LLM_API_KEY, LLM_BASE_URL, LLM_MODEL

# Cache per model name so benchmarking can swap models without recreating clients
_model_cache: dict[str, object] = {}


def get_chat_model(model_name: str | None = None):
    """Return a LangChain ChatOpenAI client for the given (or default) model.

    Ollama Cloud (and Groq, OpenAI, local Ollama) all speak the OpenAI
    wire protocol, so one client covers every provider in .env.
    Raises a clear error when no API key is configured.
    Pass ``model_name`` to benchmark a specific model; defaults to LLM_MODEL.
    """
    if not LLM_API_KEY:
        raise RuntimeError(
            "No LLM API key configured. Set LLM_API_KEY (and LLM_BASE_URL / LLM_MODEL) in .env."
        )
    name = (model_name or LLM_MODEL).strip()
    if name in _model_cache:
        return _model_cache[name]
    from langchain_openai import ChatOpenAI

    client = ChatOpenAI(
        model=name,
        temperature=AGENT_TEMPERATURE,
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL,
        timeout=60,
        max_retries=2,
    )
    _model_cache[name] = client
    return client
