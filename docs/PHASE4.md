# Phase 4 — Agentic LLM & Reorder Recommendations

> **Branch:** `phase-4-agent-reorder`
> **Status:** Complete · Live-tested against Ollama Cloud

Phase 4 turns the validated data layer (Phases 2-3) into an **agent**: a LangGraph
ReAct tool-loop that decides which tools to call, collects real data, and answers
natural-language questions using only that data.

---

## The idea in one paragraph

The user asks a question. The LLM does not know the inventory - and that is the
point. It reasons about the question, picks a **tool** (e.g. `list_low_stock`,
`forecast_demand`, `recommend_reorder`), receives verified data from SQLite and
Python, and repeats until it can answer. Every number in every answer comes from
a tool result, never from the model.

```
User question
   |
[LLM reasons] -- choose tool --> [tool runs Python/SQL] -- data back --> [LLM]
   |                                                        (repeat if needed)
[Final answer, grounded in tool results]
```

---

## What was built

### `src/agent/llm.py`
LLM client factory. One OpenAI-compatible client covers Ollama Cloud, Groq,
OpenAI, or local Ollama - whatever `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL`
are set to in `.env`.

### `src/tools/agent_tools.py`
15 LangChain tools, each a thin wrapper over the validated Phase 2-3 layer:

| Area | Tools |
|---|---|
| Inventory | `get_stock`, `list_low_stock`, `list_out_of_stock`, `inventory_summary`, `search_products` |
| Sales | `sales_summary`, `top_sellers`, `slow_movers`, `revenue_by_category` |
| Forecasting | `forecast_demand`, `validate_forecast`, `compare_forecast_methods` |
| Reorder | `recommend_reorder`, `recommend_all_reorders`, `reorder_summary` |

### `src/agent/graph.py`
`create_inventory_agent()` builds the LangGraph ReAct agent with a system prompt
that enforces grounding ("never invent stock numbers; answer from tool results").
`ask_agent(agent, question)` runs one question and returns the answer.

### `src/services/reorder_service.py`
The reorder engine (stock rules from `.env`):

- `safety_stock = REORDER_SAFETY_FACTOR * stddev(daily demand) * sqrt(lead_time)`
- `reorder_point = avg_daily_demand * REORDER_LEAD_TIME_DAYS + safety_stock`
- `recommended_qty = forecast_demand(horizon) + safety_stock - current_stock`
  (clamped to `MIN_REORDER_QTY`..`MAX_REORDER_QTY`)
- Urgency: `CRITICAL` (0 stock) / `HIGH` (below min) / `MEDIUM` (below reorder point) / `LOW`

### `scripts/chat_cli.py`
Terminal chat: type a question, the agent answers via the tool loop.

### Tests — `tests/test_agent.py`, `tests/test_reorder.py`
No network required. Verify all 15 tools are defined with descriptions, that
tools return real DB data (100 products, valid reorder fields), and that the
reorder engine produces sensible urgency/quantities.

---

## How to run

```bash
# 1. Configure .env (already done on this machine)
LLM_PROVIDER=ollama
LLM_BASE_URL=https://ollama.com/v1
LLM_API_KEY=...
LLM_MODEL=gemma4:31b

# 2. Terminal chat
python scripts/chat_cli.py
```

Example session:

```
You: Show me the inventory summary.
Agent: Total Products: 100 | Stock: 6,514 units | Low: 28 | Out: 10 | Value: $602,160.96

You: Should I restock SKU-0001?
Agent: Premium Dress (SKU-0001) is at 0 units (min 50)...
       Recommended reorder: 44 units [urgency: CRITICAL] ...
```

All tests:

```bash
python -m pytest tests/ -q     # 20 passed
```

---

## Design rules

- **The LLM is the router and the narrator - never the calculator.** All numbers
  come from tools backed by SQLite and Python.
- **Grounded system prompt.** Explicit rules: answer from tool results, say so
  when a product is not found, prefer the matching tool.
- **No fallback answer engine.** If the LLM/provider fails, the error is shown
  honestly instead of pretending.
- **Deterministic reorder math.** Safety stock, reorder point, and quantities
  follow the fixed formulas in `reorder_service.py` - identical inputs give
  identical recommendations, which makes benchmarking meaningful.
- **Provider-agnostic.** Swap `LLM_MODEL` in `.env` to benchmark another model;
  nothing else changes (Phase 6 uses this).

---

## What comes next (Phase 5)

Phase 5 adds the FastAPI backend: it serves the HTML dashboard and exposes
`/api/chat`, so the browser chat UI (built in Phase 3) talks to this agent over
HTTP instead of answering locally. The agent code does not change.

---

*Phase 4 complete. Held locally. Not pushed until user confirms.*
