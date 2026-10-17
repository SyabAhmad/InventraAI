"""POST /api/chat - run questions through the LangGraph inventory agent.

The agent is the single source of answers: it calls the validated Python
tools and explains their real data. Provider errors surface as HTTP 502 -
there is no fabricated fallback.
"""
from __future__ import annotations

import threading
import time
from typing import Any

from fastapi import APIRouter, HTTPException

from src.agent.graph import ask_agent, create_inventory_agent
from src.api.schemas import ChatRequest, ChatResponse
from src.config import LLM_MODEL

router = APIRouter(prefix="/api", tags=["chat"])

_agent_lock = threading.Lock()
_agent: Any = None


def _get_agent() -> Any:
    """Lazily create the shared agent instance (built once per server run)."""
    global _agent
    if _agent is None:
        _agent = create_inventory_agent()
    return _agent


def run_question(question: str, history: list[dict] | None = None) -> dict:
    """Run one question through the real agent (tests monkeypatch this)."""
    with _agent_lock:
        return ask_agent(_get_agent(), question, history=history)


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    started = time.perf_counter()
    history = [{"role": turn.role, "text": turn.text} for turn in payload.history]
    try:
        result = run_question(payload.message, history)
    except Exception as exc:  # network/provider/agent errors -> honest 502
        raise HTTPException(status_code=502, detail=f"Agent error: {exc}") from exc

    latency_ms = round((time.perf_counter() - started) * 1000, 1)
    return ChatResponse(
        answer=result.get("answer", ""),
        tools=result.get("tools", []),
        charts=result.get("charts", []),
        steps=result.get("steps", 0),
        latency_ms=latency_ms,
        model=LLM_MODEL,
    )
