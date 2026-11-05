"""Clef decision adapter — the CORRECT way to use Clef (decision-only).

Clef is a 27B decision model (Cloudflare). It does NOT chat and does NOT
call tools. It scores a `state` against typed `questions` in ONE pass via
Ollama's System One endpoint:  POST {base}/.../systemone

  - Local Ollama:  http://localhost:11434/v1/systemone, model "clef:27b"
  - Ollama Cloud:  https://ollama.com/v1/systemone,      model "clef"

This module is deliberately separate from the chat benchmark (runner.py)
so the 20 inventory chat cases never accidentally call Clef as a chat LLM.
Use it for routing / policy / tool-call moderation checks, e.g.:
  "Should SKU-0001 be reordered?" -> {"need_reorder": noul}
"""
from __future__ import annotations

import os
from typing import Any

from src.config import CLEF_MODEL, LLM_API_KEY, LLM_BASE_URL


def _systemone_url() -> str:
    """Build the System One URL from the configured base URL."""
    base = (LLM_BASE_URL or "https://ollama.com/v1").rstrip("/")
    # Local Ollama serves /v1/systemone; cloud serves https://ollama.com/v1/systemone
    return base + "/systemone"


def _resolve_model() -> str:
    """Direct ollama.com call uses 'clef'; local needs a sized tag."""
    if (LLM_BASE_URL or "").startswith("http://localhost") or (LLM_BASE_URL or "").startswith("http://127."):
        return CLEF_MODEL  # default clef:27b for local
    return "clef"  # cloud direct-call name (not clef:cloud, not clef:27b-cloud)


def run_clef_decision(state: str | dict | list, questions: dict[str, dict]) -> dict:
    """Run one Clef decision check. Returns the provider's JSON response.

    Args:
        state: text / JSON object / JSON array to judge.
        questions: {name: {"type": "choice"|"noul"|"score",
                            "instructions": str,
                            "criteria": {...}  # choices per type
                           }}
    Raises:
        RuntimeError: if no API key is set for cloud use, or HTTP fails.
    """
    if not questions:
        raise ValueError("questions must have 1+ entries (max 64).")
    if len(questions) > 64:
        raise ValueError("Clef supports at most 64 questions per call.")

    import httpx

    headers = {"Content-Type": "application/json"}
    if LLM_API_KEY:
        headers["Authorization"] = f"Bearer {LLM_API_KEY}"
    elif "ollama.com" in (LLM_BASE_URL or "") and not (LLM_BASE_URL or "").startswith("http://localhost"):
        raise RuntimeError(
            "No LLM_API_KEY configured for Clef cloud calls. "
            "Set LLM_API_KEY (and LLM_BASE_URL / CLEF_MODEL) in .env."
        )

    payload: dict[str, Any] = {"model": _resolve_model(), "state": state, "questions": questions}
    url = _systemone_url()
    try:
        resp = httpx.post(url, json=payload, headers=headers, timeout=60.0)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:  # noqa: BLE001 — surface provider error honestly
        raise RuntimeError(f"Clef decision call failed ({url}): {exc}") from exc
