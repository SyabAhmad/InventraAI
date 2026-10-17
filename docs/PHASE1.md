# Phase 1 — Foundation

> **Branch:** `phase-1-foundation`
> **Status:** Complete · Pushed (live-tested)
> **Owner:** Arzo Naveed (AI Inventory Management Agent module)

This document explains, in plain language, everything that was built in Phase 1
and how to use it. If you are new to the project, start here.

---

## 1. What Phase 1 is about

Phase 1 is the **foundation** of InventraAI. Before we can build an inventory
agent, a dashboard, or run model benchmarks, we need three things:

1. A **place to store data** (the database and its tables).
2. A **way to configure the app** without editing code (environment variables).
3. **Sample data** so every later phase has something realistic to work with.

Phase 1 delivers exactly that. No agent logic, no UI yet — just solid ground.

---

## 2. What was built

### 2.1 Project scaffold

A clean, predictable folder layout so every team member knows where things live:

- `src/` — all Python source code
- `scripts/` — command-line entry points (e.g. database setup)
- `tests/` — automated tests
- `frontend/` — web UI files (filled in Phase 5)
- `data/` — SQLite database file (generated, not committed to git)
- `docs/` — human-readable documentation (this file)

Each Python package has an `__init__.py` so imports work consistently.

### 2.2 Configuration via `.env`

Instead of hard-coding values, every setting lives in a `.env` file. You copy
`.env.example` to `.env` and edit it. The app reads these values at startup.

Why this matters for our FYP: the **LLM model name** is also in `.env`. That means
we can switch models (for benchmarking) by changing one line — no code changes.

Key settings:

- `OLLAMA_MODEL` — which model the agent uses
- `OLLAMA_BENCHMARK_MODELS` — comma-separated list of models to benchmark
- `DATABASE_PATH` — where the SQLite file lives
- Stock rules: `DEFAULT_MIN_STOCK`, `REORDER_SAFETY_FACTOR`, `REORDER_LEAD_TIME_DAYS`
- Forecast settings: `FORECAST_HORIZON_DAYS`, `FORECAST_VALIDATION_DAYS`

### 2.3 SQLite database

We use SQLite because it needs no server, is file-based, and is perfect for a
student project and demos.

Four tables:

1. **products** — the catalogue (SKU, name, category, price, cost, min stock threshold, supplier).
2. **inventory** — current stock per product (linked to products).
3. **sales** — every sale transaction (product, quantity, price, date, channel).
4. **reorder_history** — record of suggested reorders (for audit/tracking).

Two indexes make queries fast: sales by product+date, and products by category.

The schema is stored in `src/database/schema.sql` and applied automatically when
seeding.

### 2.4 Dummy data generator

`src/database/seed_data.py` creates realistic sample e-commerce data:

- **100 products** across 8 categories (Electronics, Clothing, Home & Kitchen,
  Beauty, Sports, Books, Toys, Groceries).
- **Varied stock levels**: about 8% out of stock, ~17% low stock, the rest healthy.
- **90 days of sales** with a mix of fast, medium, and slow sellers, plus some
  products whose demand is increasing over time.

This gives every later phase something meaningful to analyze, forecast, and
recommend on.

### 2.5 Database init script

`scripts/init_db.py` is the one command you run to set everything up:

```bash
python scripts/init_db.py
```

It creates the tables and inserts the dummy data. Run it with `--reset` to wipe
and start fresh.

### 2.6 Smoke tests

`tests/test_phase1_smoke.py` checks that:

- configuration loads correctly,
- the schema initializes,
- seeding produces the expected counts,
- seeding is **idempotent** (running twice doesn't duplicate data).

All tests pass.

---

## 3. How to use Phase 1

### Step 1 — Install

```bash
pip install -r requirements.txt
```

### Step 2 — Configure

```bash
copy .env.example .env   # Windows
# cp .env.example .env    # macOS/Linux
```

Open `.env` and fill in your Ollama Cloud key (`OLLAMA_API_KEY`).

### Step 3 — Create the database

```bash
python scripts/init_db.py
```

You should see:

```text
{'status': 'seeded', 'products': 100, 'inventory': 100, 'sales': 8745}
DB path: ...\data\inventory.db
```

### Step 4 — Verify with tests

```bash
python -m pytest -q
```

Expected: `2 passed`.

### Step 5 — Re-seed if needed

```bash
python scripts/init_db.py --reset
```

---

## 4. Files added in Phase 1

| File | Purpose |
|---|---|
| `.env.example` | Template for all configuration |
| `.gitignore` | Keeps secrets, DB, caches out of git |
| `LICENSE` | MIT license |
| `README.md` | Project overview and quick start |
| `PHASES.md` | Phase/branch plan |
| `requirements.txt` | Python dependencies |
| `src/config.py` | Reads `.env` into typed settings |
| `src/database/connection.py` | SQLite connection helper |
| `src/database/schema.sql` | Table definitions |
| `src/database/seed_data.py` | Dummy data generator |
| `scripts/init_db.py` | DB setup entrypoint |
| `tests/test_phase1_smoke.py` | Smoke tests |
| `docs/PHASE1.md` | This document |

---

## 5. Design decisions (and why)

- **SQLite over Postgres/MySQL**: no server to install, file-based, trivial to
  back up and share. Perfect for an FYP demo.
- **`.env` for everything**: lets us swap LLM models for benchmarking without
  touching code; keeps secrets out of git.
- **Idempotent seeding**: re-running setup never duplicates data, which makes
  demos and tests reliable.
- **Validation in Python, not the LLM**: numbers come from real DB queries and
  real calculations. The LLM only explains results.
- **Phase branches**: each phase is isolated on its own git branch, so we can
  review and push incrementally.

---

## 6. What comes next (Phase 2+)

Phase 2 will add the **inventory tools layer**: typed functions to query stock,
detect low/out-of-stock items, and validate updates. These functions become the
tools the AI agent calls in Phase 4.

See `PHASES.md` for the full plan.

---

## 7. Quick reference

| Task | Command |
|---|---|
| Install deps | `pip install -r requirements.txt` |
| Init database | `python scripts/init_db.py` |
| Reset database | `python scripts/init_db.py --reset` |
| Run tests | `python -m pytest -q` |
| Check config | `python -c "from src import config; print(config.OLLAMA_MODEL)"` |

---

## 8. In one sentence

Phase 1 gives us a **working database full of realistic sample data** and a
**configurable app** that we can run and test — the solid ground every other
phase builds on.

## 9. Glossary (plain English)

- **SQLite** — a small database stored in a single file on your computer. No
  server needed.
- **Schema** — the blueprint of the database: which tables exist and what
  columns they have.
- **Seed data** — fake but realistic data we insert so the app has something
  to show and test with.
- **Idempotent** — running the same command twice gives the same result (no
  duplicates).
- **`.env` file** — a text file holding settings (like passwords and model
  names) that the app reads at startup. Kept out of git for safety.
- **Branch** — a separate line of work in git. Each phase has its own branch.
- **Smoke test** — a quick test that checks the basics work.

---

*Phase 1 complete. Pushed.*