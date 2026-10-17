# Phase 5 — Dashboard & API

> **Branch:** `phase-5-dashboard`
> **Status:** Complete · Live-tested (server + real agent calls through HTTP)

Phase 5 turns the static dashboard into a **real application**. A FastAPI
backend serves the frontend, reads live data from SQLite, and exposes the
Phase-4 LangGraph agent over HTTP so the web chat uses the real tool-loop —
no more frozen snapshots, no rule-based stand-in answers.

---

## The idea in one paragraph

Before this phase the dashboard was a nice-looking page reading a `data.js`
snapshot, and the "chat" was a small rule engine. Now you start **one server**
and everything is live: pages load fresh numbers from SQLite through REST
endpoints, charts draw real daily sales, each product has a demand forecast,
and questions typed in the chat run through the same agent as
`scripts/chat_cli.py` — real tools, real data, real LLM.

```
Browser (frontend/)
   |  GET /api/dashboard, /api/forecast/..., /api/reorder
   |  POST /api/chat  ──────────────┐
   v                               v
FastAPI (src/api/)          LangGraph agent (src/agent/)
   |                               |
   └── services (Phases 2-4) ──────┘
              |
           SQLite (data/inventory.db)
```

---

## What was built

### Backend — `src/api/`

| File | Purpose |
|---|---|
| `main.py` | FastAPI app: mounts routers + serves `frontend/` at `/`, interactive docs at `/docs` |
| `schemas.py` | Pydantic request/response models |
| `routes/dashboard.py` | Live data endpoints (below) |
| `routes/chat.py` | `POST /api/chat` — runs the real agent, returns answer + tools used + latency |

Endpoints:

| Method | Path | Returns |
|---|---|---|
| GET | `/api/health` | server + model + DB status |
| GET | `/api/dashboard` | full dashboard payload (same shape as `data.js`) |
| GET | `/api/products` | products + sales aggregates |
| GET | `/api/low-stock`, `/api/out-of-stock` | alert lists |
| GET | `/api/top-sellers?limit=&days=` | ranked sellers |
| GET | `/api/sales/summary`, `/api/sales/daily?days=`, `/api/sales/categories` | sales analytics |
| GET | `/api/forecast/{sku}?horizon=` | 90-day history + forecast + MAE/MAPE |
| GET | `/api/reorder?limit=&only_needed=` | reorder recommendations (30 s cache) |
| POST | `/api/chat` | `{answer, tools, steps, latency_ms, model}` |

No-fallback rule: if the LLM provider fails, `/api/chat` returns **502 with the
real error** — it never fabricates an answer.

### Services

- `src/services/dashboard_service.py` — single source of truth for the
  dashboard payload; used by **both** the API and the snapshot generator.
- `src/services/sales_service.py` — new `daily_totals(days)` (gap-filled
  per-day units/revenue for charts).
- `src/agent/graph.py` — `ask_agent` now also reports **which tools ran**.

### Frontend

- **Live mode** — `app.js` fetches `/api/dashboard` on load; if the backend is
  offline it falls back to the bundled `data.js` **snapshot mode** (the
  topbar badge shows which mode is active).
- **Charts** — Chart.js (vendored, works offline):
  revenue + units per day in *Sales Summary*, and a 90-day history + forecast
  chart when you click any product.
- **Product detail modal** — click rows in Products / Low Stock / Out of Stock
  / Reorder Advice for stock details and the forecast chart.
- **Reorder Advice view** — new sidebar page: urgency, reorder point,
  suggested quantity, and the reasoning behind each recommendation.
- **Chat** — live mode posts to `/api/chat` and renders answers as Markdown,
  with small "used: tool" chips showing which tools the agent called.
  Snapshot mode keeps the local intent engine so the static page still works.
- Markdown is rendered safely: HTML is escaped **before** Markdown parsing, so
  model output can never inject tags.

### Tests — `tests/test_api.py`
11 tests, no network needed: health, dashboard shape, 100 products, alert
invariants, contiguous daily series, forecast (known + unknown SKU), reorder
contract, chat validation (422), chat with a stubbed agent, and chat provider
failure (502). Suite total: **31 passed**.

---

## How to run

```bash
# 1. Seed the database once (if not already)
python scripts/init_db.py

# 2. Start the server
uvicorn src.api.main:app --reload

# 3. Open the dashboard
#    http://127.0.0.1:8000/
```

The topbar badge shows the configured model. If it is green (**live**), data
and chat are live. Opening `frontend/index.html` directly still works as a
snapshot — and it will also find the backend automatically if the server is
running on the default port.

Optional snapshot refresh (for the offline file-open mode):

```bash
python scripts/generate_products_html.py
```

---

## Glossary

- **FastAPI** — the Python web framework that serves the API and the frontend.
- **Uvicorn** — the web server that runs the FastAPI app.
- **Endpoint** — a URL the frontend can call, e.g. `GET /api/products`.
- **Live mode / snapshot mode** — whether the page is reading the running
  server (live) or the bundled `data.js` file (snapshot).
- **Tool chip** — the small label under an agent answer showing which Python
  tools the agent actually called.
