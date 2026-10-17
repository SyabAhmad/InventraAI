# AI-Based Inventory Management Agent for E-commerce

Final Year Project (FYP 2) — Module owned by **Arzo Naveed**.
Part of: *Cost-Efficient Optimization of Open-Source LLM Agents for System-Level Tasks*.

An intelligent inventory assistant for e-commerce: monitors stock, detects low stock,
analyzes sales, forecasts demand, recommends reorders, answers natural-language
questions, and exposes everything through a web dashboard. All heavy logic runs in
validated Python functions; the LLM only orchestrates tool calls and explains results.

## Stack
- Backend: Python + FastAPI
- Database: SQLite
- LLM: Ollama Cloud (OpenAI-compatible), model configurable via `.env`
- Frontend: HTML/CSS/JS (Chart.js)
- Agent: LangGraph (tool-calling)

## Setup
```bash
# 1. Create virtualenv (optional)
python -m venv .venv
.venv\Scripts\activate

# 2. Install deps
pip install -r requirements.txt

# 3. Configure
copy .env.example .env
# edit .env: set OLLAMA_API_KEY, OLLAMA_MODEL, etc.

# 4. Initialize database
python scripts/init_db.py

# 5. Run API + dashboard
uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
```
Open http://127.0.0.1:8000 in your browser.

## Configuration
Everything is controlled via `.env` (see `.env.example`), including the LLM model
name used by the agent and the benchmark runner.

## Project phases
See `PHASES.md`. Each phase lives on its own branch; `main` contains the integrated build.