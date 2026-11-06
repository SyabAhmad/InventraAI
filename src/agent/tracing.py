"""Live trace for benchmark runs (real callbacks only).

Trace events are recorded from LangChain/LangGraph callbacks and runner state:

- LLM request started / finished (model, message count, latency)
- tool started / returned (name, truncated input/output)
- retries / provider errors
- final answer prepared

This module never invents tokens or "private thoughts". If the provider does
not stream intermediate reasoning, the UI can only show "model thinking…" —
and that is still useful because every shown event maps to a real call.
"""
from __future__ import annotations

import json
import time
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler

MAX_TRACE_EVENTS = 250
MAX_FIELD_CHARS = 240


def _now_ms() -> float:
    return round(time.time() * 1000, 1)


def _truncate(value: Any, chars: int = MAX_FIELD_CHARS) -> str:
    try:
        text = json.dumps(value, default=str, ensure_ascii=False)
    except (TypeError, ValueError):
        text = str(value)
    return text if len(text) <= chars else text[:chars] + "…"


def _serialized_model(serialized: Any) -> str:
    if not isinstance(serialized, dict):
        return "llm"
    kwargs = serialized.get("kwargs") or {}
    return str(kwargs.get("model") or kwargs.get("model_name") or serialized.get("name") or "llm")


class BenchmarkTrace:
    """Thread-safe trace container for one benchmark cell (model × prompt)."""

    def __init__(self, *, model: str, prompt_id: str, shared_events: list[dict] | None = None) -> None:
        self.model = model
        self.prompt_id = prompt_id
        self.events: list[dict] = shared_events if shared_events is not None else []

    def emit(self, kind: str, message: str, **data: Any) -> None:
        if len(self.events) >= MAX_TRACE_EVENTS:
            return
        evt = {
            "ts_ms": _now_ms(),
            "kind": kind,
            "model": self.model,
            "prompt_id": self.prompt_id,
            "message": message,
            **data,
        }
        self.events.append(evt)


class BenchmarkTraceCallback(BaseCallbackHandler):
    """LangChain callback that records real LLM/tool events."""

    def __init__(self, trace: BenchmarkTrace) -> None:
        super().__init__()
        self.trace = trace
        self._tokens_by_run: dict[str, int] = {}
        self._tool_by_run: dict[str, str] = {}

    def on_llm_start(self, serialized: dict, prompts: list[str], **kwargs: Any) -> None:  # type: ignore[override]
        model = _serialized_model(serialized)
        run_id = str(kwargs.get("run_id", ""))
        prompt_chars = sum(len(p or "") for p in prompts)
        self._tokens_by_run[run_id] = 0
        self.trace.emit("llm_start", f"Calling {model} ({len(prompts)} prompt(s))",
                        provider_model=model, prompt_chars=prompt_chars, run_id=run_id)

    def on_chat_model_start(self, serialized: dict, messages: list[list[Any]], **kwargs: Any) -> None:  # type: ignore[override]
        model = _serialized_model(serialized)
        run_id = str(kwargs.get("run_id", ""))
        prompt_chars = sum(len(str(m)) for msgs in messages for m in msgs)
        self._tokens_by_run[run_id] = 0
        self.trace.emit("llm_start", f"Calling {model} ({len(messages)} message batch)",
                        provider_model=model, prompt_chars=prompt_chars, run_id=run_id)

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:  # type: ignore[override]
        run_id = str(kwargs.get("run_id", ""))
        generations = getattr(response, "generations", None) or []
        output_chars = 0
        finish_reason = ""
        for batch in generations:
            for gen in batch:
                text = getattr(getattr(gen, "message", None), "content", "") or getattr(gen, "text", "") or ""
                output_chars += len(text)
                meta = getattr(gen, "generation_info", None) or {}
                finish_reason = str(meta.get("finish_reason") or finish_reason or "")
        usage = getattr(getattr(response, "llm_output", None), "get", None)
        self.trace.emit("llm_end", f"Model responded ({output_chars} chars)",
                        output_chars=output_chars, finish_reason=finish_reason, run_id=run_id)

    def on_llm_error(self, error: BaseException, **kwargs: Any) -> None:  # type: ignore[override]
        self.trace.emit("llm_error", f"Model error: {error}", error=str(error))

    def on_retry(self, retry_state: Any, **kwargs: Any) -> None:  # type: ignore[override]
        attempt = getattr(retry_state, "attempt_number", None) or getattr(retry_state, "attempt", "?")
        self.trace.emit("retry", f"Provider retry (attempt {attempt})", attempt=attempt)

    def on_tool_start(self, serialized: dict, input_str: str, **kwargs: Any) -> None:  # type: ignore[override]
        name = serialized.get("name") if isinstance(serialized, dict) else "tool"
        run_id = str(kwargs.get("run_id", ""))
        self._tool_by_run[run_id] = str(name or "tool")
        self.trace.emit("tool_start", f"Calling tool {name}",
                        tool=name, tool_input=_truncate(input_str), run_id=run_id)

    def on_tool_end(self, output: Any, **kwargs: Any) -> None:  # type: ignore[override]
        run_id = str(kwargs.get("run_id", ""))
        name = self._tool_by_run.pop(run_id, "tool")
        self.trace.emit("tool_end", f"Tool {name} returned",
                        tool=name, tool_output=_truncate(output), run_id=run_id)

    def on_tool_error(self, error: BaseException, **kwargs: Any) -> None:  # type: ignore[override]
        self.trace.emit("tool_error", f"Tool error: {error}", error=str(error))
