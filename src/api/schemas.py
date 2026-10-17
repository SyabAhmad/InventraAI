"""Request/response models for the InventraAI API."""
from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000, description="User question for the agent")


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
