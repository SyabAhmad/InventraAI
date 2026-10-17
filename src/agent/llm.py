"""LLM client factory for the inventory agent (Ollama Cloud / any OpenAI-compatible API)."""
from __future__ import annotations

from functools import lru_cache

from src.config import AGENT_TEMPERATURE, LLM_API_KEY, LLM_BASE_URL, LLM_MODEL


@lru_cache(maxsize=1)
def get_chat_model():
    """Return a LangChain ChatOpenAI client pointed at the configured provider.

    Ollama Cloud (and Groq, OpenAI, local Ollama) all speak the OpenAI
    wire protocol, so one client covers every provider in .env.
    Raises a clear error when no API key is configured.
    """
    if not LLM_API_KEY:
        raise RuntimeError(
            "No LLM API key configured. Set LLM_API_KEY (and LLM_BASE_URL / LLM_MODEL) in .env."
        )
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=LLM_MODEL,
        temperature=AGENT_TEMPERATURE,
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL,
        timeout=60,
        max_retries=2,
    )
