# InventraAI — AI-Based Inventory Management Agent for E-commerce

> **Phase 5 — Dashboard & API.** This branch contains the full build through
> Phase 5: foundation, inventory tools, sales/forecasting, the LangGraph agent,
> and the FastAPI backend serving the live dashboard. Benchmarking (Phase 6)
> lives on its own branch; everything merges into `main`.

Final Year Project (FYP 2) module owned by **Arzo Naveed**.
Part of: *Cost-Efficient Optimization of Open-Source LLM Agents for System-Level Tasks*.

InventraAI is an intelligent inventory assistant for e-commerce: it monitors stock,
detects low/out-of-stock items, analyzes sales, forecasts demand, recommends reorders,
answers natural-language questions, and exposes everything through a web dashboard.
All heavy logic runs in validated Python functions; the LLM only orchestrates tool
calls and explains results using real data.

---

## Table of contents

- [Features (target)](#features-target)
- [Tech stack](#tech-stack)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [Project structure](#project-structure)
- [Database schema](#database-schema)
- [Dummy data](#dummy-data)
- [Testing](#testing)
- [Git workflow / phases](#git-workflow--phases)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## Features (target)

- **Inventory monitoring** — product records, stock quantities, prices, min-stock thresholds.
- **Low-stock detection** — automatic alerts when stock falls below threshold.
- **Inventory queries** — stock lookups, out-of-stock lists, low-stock lists.
- **Sales analysis** — fast/slow sellers, revenue by category, trends over time.
- **Demand forecasting** — moving average / exponential smoothing / linear trend with MAE/MAPE.
- **Smart reorder recommendations** — reorder point, safety stock, recommended quantities.
- **Natural-language interaction** — the **MenteE** assistant powered by Ollama Cloud (model configurable via `.env`).
- **Charts in chat** — MenteE fetches data with a tool, builds bar/line/pie charts with a chart tool, rendered inline in the chat.
- **Web dashboard** — FastAPI backend + HTML/JS (Chart.js) frontend.
- **Model benchmarking** — compare multiple Ollama models on accuracy, success rate, latency, tokens, cost.

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3.9+, FastAPI, Uvicorn |
| Database | SQLite (via `sqlite3`) |
| Data/ML | pandas, numpy, scikit-learn |
| LLM | Ollama Cloud (OpenAI-compatible), model name from `.env` |
| Agent | LangGraph (tool-calling) — Phase 4 |
| Frontend | HTML / CSS / JS (Chart.js) — Phase 5 |
| Testing | pytest |

---

## Quick start

### 1. Clone and enter

```bash
git clone https://github.com/<your-username>/InventraAI.git
cd InventraAI
git checkout phase-1-foundation
```

### 2. Create virtual environment (recommended)

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure environment

```bash
# Windows
copy .env.example .env
# macOS / Linux
cp .env.example .env
```

Edit `.env` and set at least:

- `OLLAMA_API_KEY` — your Ollama Cloud key (required for cloud models)
- `OLLAMA_MODEL` — default model, e.g. `llama3.1:8b`
- `DATABASE_PATH` — defaults to `data/inventory.db`

Everything else has sensible defaults.

> **LLM provider flexibility:** Any OpenAI-compatible provider works out of the
> box (Ollama Cloud, Groq, OpenAI, local Ollama). Just set `LLM_BASE_URL`,
> `LLM_API_KEY`, and `LLM_MODEL` in `.env` — no code changes needed.

### 5. Initialize the database (seed dummy data)

```bash
python scripts/init_db.py
```

Expected output:

```text
{'status': 'seeded', 'products': 100, 'inventory': 100, 'sales': <n>}
DB path: ...\data\inventory.db
```

To wipe and re-seed:

```bash
python scripts/init_db.py --reset --products 100 --days 90
```

### 6. Run tests

```bash
python -m pytest -q
```

---

## Configuration

All runtime behavior is controlled through `.env` (see `.env.example`).
The LLM model name is read from `OLLAMA_MODEL` and can be swapped freely —
including in the benchmark runner (`OLLAMA_BENCHMARK_MODELS`).

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_BASE_URL` | `https://ollama.com/v1` | Ollama Cloud endpoint |
| `OLLAMA_API_KEY` | _(empty)_ | Cloud API key |
| `OLLAMA_MODEL` | `llama3.1:8b` | Default agent model |
| `OLLAMA_BENCHMARK_MODELS` | `llama3.1:8b` | Comma-separated benchmark models |
| `DATABASE_PATH` | `data/inventory.db` | SQLite file location |
| `DEFAULT_MIN_STOCK` | `20` | Default minimum stock threshold |
| `REORDER_SAFETY_FACTOR` | `1.5` | Safety stock multiplier |
| `REORDER_LEAD_TIME_DAYS` | `7` | Supplier lead time |
| `FORECAST_HORIZON_DAYS` | `7` | Forecast horizon |
| `FORECAST_VALIDATION_DAYS` | `14` | Validation split size |
| `AGENT_MAX_ITERATIONS` | `8` | Max agent tool-call loops |
| `API_HOST` / `API_PORT` | `127.0.0.1` / `8000` | API bind address |

---

## Project structure

```text
InventraAI/
├── .env.example            # environment template
├── .gitignore
├── LICENSE
├── PHASES.md               # phase/branch plan
├── README.md
├── requirements.txt
├── scripts/
│   └── init_db.py          # DB init / seed entrypoint
├── src/
│   ├── __init__.py
│   ├── config.py           # env-driven configuration
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py  # SQLite connection helper
│   │   ├── schema.sql     # table definitions
│   │   └── seed_data.py   # dummy data generator
│   ├── services/           # (Phase 2+)
│   ├── tools/              # (Phase 2+)
│   ├── agent/              # (Phase 4)
│   ├── api/                # (Phase 5)
│   └── benchmark/          # (Phase 6)
├── frontend/               # (Phase 5)
├── tests/
│   └── test_phase1_smoke.py
└── data/                   # SQLite DB (gitignored)
```

---

## Database schema

- **products** — `product_id, sku, name, category, price, cost, min_stock_threshold, supplier, created_at`
- **inventory** — `product_id (PK/FK), current_stock, last_updated`
- **sales** — `sale_id, product_id (FK), quantity, unit_price, sale_date, channel`
- **reorder_history** — `rec_id, product_id (FK), recommended_qty, reason, created_at, status`

Indexes on `sales(product_id, sale_date)` and `products(category)`.

---

## Dummy data

`src/database/seed_data.py` generates realistic sample e-commerce data:

- 100 products across 8 categories (Electronics, Clothing, Home & Kitchen, Beauty,
  Sports, Books, Toys, Groceries)
- Varied stock levels: ~8% out of stock, ~17% low stock, rest healthy
- 90 days of sales with fast/medium/slow movers and some increasing-demand trends

Seeding is **idempotent** — re-running skips if data already exists. Use `--reset`
to wipe and re-seed.

---

## Testing

```bash
python -m pytest -q
```

Phase 1 smoke tests verify:

- Configuration loads correctly
- Schema initializes
- Seeding produces expected counts
- Seeding is idempotent

---

## Git workflow / phases

Each phase lives on its own branch. `main` holds the integrated build.

| Phase | Branch | Scope |
|---|---|---|
| 1 | `phase-1-foundation` | Scaffold, config, schema, dummy data |
| 2 | `phase-2-inventory-tools` | DB access layer, alerts, validation |
| 3 | `phase-3-sales-forecast` | Sales analysis, demand forecasting |
| 4 | `phase-4-agent-reorder` | LangGraph agent, reorder recommendations |
| 5 | `phase-5-dashboard` | FastAPI + HTML dashboard |
| 6 | `phase-6-benchmark` | Multi-model benchmarking, optimization |

```bash
# Work on a phase
git checkout phase-1-foundation

# Push a phase branch
git push -u origin phase-1-foundation
```

---

## Troubleshooting

- **`ModuleNotFoundError`** — ensure your venv is activated and `pip install -r requirements.txt` ran.
- **DB not found** — run `python scripts/init_db.py`; check `DATABASE_PATH` in `.env`.
- **Re-seed from scratch** — `python scripts/init_db.py --reset`.
- **Ollama errors** — verify `OLLAMA_API_KEY` and `OLLAMA_BASE_URL` in `.env`; the model
  name must be available on your Ollama Cloud account.
- **Tests fail on import** — run from the project root so `src` is importable.

---

## License

MIT — see [LICENSE](LICENSE).