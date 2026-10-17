# Project Phases

This project is delivered in 6 phases, each on its own git branch.
Final `main` merges all phases.

| Phase | Branch | Status |
|---|---|---|
| 1 | phase-1-foundation | Done (pushed) |
| 2 | phase-2-inventory-tools | Pending |
| 3 | phase-3-sales-forecast | Pending |
| 4 | phase-4-agent-reorder | Pending |
| 5 | phase-5-dashboard | Pending |
| 6 | phase-6-benchmark | Pending |

## Phase 1 - Foundation
Repo structure, configuration via .env, SQLite schema, dummy data (100 products, 90 days sales),
README and run instructions.

## Phase 2 - Inventory Tools
DB access layer, inventory queries, low-stock/out-of-stock detection, validation guardrails.

## Phase 3 - Sales Analysis & Demand Forecasting
Sales summaries, top/slow sellers, trend analysis, demand forecasting with validation + MAE/MAPE.

## Phase 4 - Agentic LLM + Reorder Recommendations
LangGraph agent with tool-calling, reorder recommendation engine, natural-language interaction via Ollama Cloud.

## Phase 5 - HTML Dashboard
FastAPI backend + HTML/JS/Chart.js dashboard: stock, alerts, sales, forecasts, reorder recs, chat.

## Phase 6 - Benchmarking & Optimization
Multi-model benchmark harness, baseline vs optimized runs, metrics logging, tests, docs.
