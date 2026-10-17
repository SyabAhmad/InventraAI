"""Central configuration loaded from environment variables / .env."""
from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root (parent of src/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

PROJECT_ROOT = _PROJECT_ROOT


def _get(key: str, default: str = "") -> str:
    return os.getenv(key, default)


def _get_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, default))
    except (TypeError, ValueError):
        return default


def _get_float(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, default))
    except (TypeError, ValueError):
        return default


# --- LLM provider (OpenAI-compatible) ---
# Supports any OpenAI-compatible endpoint: Ollama Cloud, Groq, OpenAI, etc.
# Switch providers by changing these values in .env (no code changes).
LLM_PROVIDER = _get("LLM_PROVIDER", _get("OLLAMA_PROVIDER", "ollama"))
LLM_BASE_URL = _get("LLM_BASE_URL", _get("OLLAMA_BASE_URL", "https://ollama.com/v1"))
LLM_API_KEY = _get("LLM_API_KEY", _get("OLLAMA_API_KEY", ""))
LLM_MODEL = _get("LLM_MODEL", _get("OLLAMA_MODEL", "llama3.1:8b"))
LLM_BENCHMARK_MODELS = [
    m.strip() for m in _get(
        "LLM_BENCHMARK_MODELS",
        _get("OLLAMA_BENCHMARK_MODELS", "llama3.1:8b"),
    ).split(",") if m.strip()
]

# Backward-compatible aliases (existing code / .env may use OLLAMA_* names)
OLLAMA_PROVIDER = LLM_PROVIDER
OLLAMA_BASE_URL = LLM_BASE_URL
OLLAMA_API_KEY = LLM_API_KEY
OLLAMA_MODEL = LLM_MODEL
OLLAMA_BENCHMARK_MODELS = LLM_BENCHMARK_MODELS

# --- Database ---
DATABASE_PATH = _get("DATABASE_PATH", "data/inventory.db")
if not os.path.isabs(DATABASE_PATH):
    DATABASE_PATH = str(PROJECT_ROOT / DATABASE_PATH)

# --- Inventory rules ---
DEFAULT_MIN_STOCK = _get_int("DEFAULT_MIN_STOCK", 20)
LOW_STOCK_ALERT_THRESHOLD = _get_int("LOW_STOCK_ALERT_THRESHOLD", 20)
REORDER_SAFETY_FACTOR = _get_float("REORDER_SAFETY_FACTOR", 1.5)
REORDER_LEAD_TIME_DAYS = _get_int("REORDER_LEAD_TIME_DAYS", 7)
MIN_REORDER_QTY = _get_int("MIN_REORDER_QTY", 10)
MAX_REORDER_QTY = _get_int("MAX_REORDER_QTY", 500)

# --- Forecasting ---
FORECAST_HORIZON_DAYS = _get_int("FORECAST_HORIZON_DAYS", 7)
FORECAST_VALIDATION_DAYS = _get_int("FORECAST_VALIDATION_DAYS", 14)
FORECAST_METHOD = _get("FORECAST_METHOD", "moving_average")

# --- Agent ---
AGENT_MAX_ITERATIONS = _get_int("AGENT_MAX_ITERATIONS", 8)
AGENT_TEMPERATURE = _get_float("AGENT_TEMPERATURE", 0.2)

# --- Benchmarking ---
BENCHMARK_REPEATS = _get_int("BENCHMARK_REPEATS", 3)
BENCHMARK_OUTPUT_DIR = _get("BENCHMARK_OUTPUT_DIR", "benchmark_results")
if not os.path.isabs(BENCHMARK_OUTPUT_DIR):
    BENCHMARK_OUTPUT_DIR = str(PROJECT_ROOT / BENCHMARK_OUTPUT_DIR)

# --- API ---
API_HOST = _get("API_HOST", "127.0.0.1")
API_PORT = _get_int("API_PORT", 8000)