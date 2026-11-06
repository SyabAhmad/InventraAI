"""Request/response models for the InventraAI API."""
from __future__ import annotations

from typing import List, Optional, Union

from pydantic import BaseModel, Field


class ChatTurn(BaseModel):
    role: str = Field(default="user", pattern="^(user|agent|assistant)$")
    text: str = Field(min_length=1, max_length=8000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000, description="User question for the agent")
    history: list[ChatTurn] = Field(
        default_factory=list,
        max_length=40,
        description="Earlier turns of this conversation, oldest first (for follow-ups)",
    )


class ChatResponse(BaseModel):
    answer: str
    tools: list[str] = Field(default_factory=list, description="Tools the agent called, in order")
    charts: list[dict] = Field(default_factory=list, description="Chart specs produced by chart tools")
    steps: int = 0
    latency_ms: float = 0.0
    model: str = ""


class HealthResponse(BaseModel):
    status: str
    model: str
    database_ready: bool
    live_mode: bool = True


class BenchmarkPrompt(BaseModel):
    id: str
    question: str
    category: str
    expected_tools: list[str] = Field(default_factory=list)
    expected_any: List[List[str]] = Field(default_factory=list, description="Optional alternative tool groups; each group needs ≥1 call")
    notes: str = ""


class BenchmarkConfig(BaseModel):
    models: list[str] = Field(default_factory=list)
    default_model: str = ""
    provider: str = ""
    base_url: str = ""
    prompts: list[BenchmarkPrompt] = Field(default_factory=list)
    repeats_default: int = 1
    modes: list[str] = Field(default_factory=lambda: ["baseline", "optimized"], description="Paired run modes (FYP PDF §5)")
    metadata: dict = Field(default_factory=dict, description="Hardware + settings snapshot for evidence")
    default_suite: str = "v2"
    suites: dict = Field(default_factory=dict, description="Available suites; key -> name/description/prompt_count")


class BenchmarkRunRequest(BaseModel):
    # Optional[...] instead of `| None` for Python 3.9 + pydantic compat
    models: Optional[List[str]] = Field(default=None, description="Model names from .env LLM_BENCHMARK_MODELS; defaults to all")
    prompt_ids: Optional[List[str]] = Field(default=None, description="Prompt ids to run; defaults to all 20")
    repeats: int = Field(default=1, ge=1, le=5)
    mode: str = Field(default="baseline", pattern="^(baseline|optimized)$", description="baseline = original prompt; optimized = shorter context")
    suite: str = Field(default="v2", pattern="^(v1|v2)$", description="v1 = legacy router; v2 = complex inventory decisions")


class ClefCheckRequest(BaseModel):
    state: Union[str, dict, list] = Field(description="Text/JSON to judge (e.g. a reorder case)")
    questions: dict = Field(description="{name: {type: choice|noul|score, instructions, criteria}}")
