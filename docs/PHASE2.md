# Phase 2 — Inventory Tools

> **Branch:** `phase-2-inventory-tools`
> **Status:** Complete · Not pushed (held by user request)

This phase adds the validated inventory action layer that the agent (Phase 4) and dashboard (Phase 5) will call. Everything is tested manually and automatically.

---

## What Phase 2 does

Before the agent can answer "How many units of this product?" or "Which products are low?", we need reliable functions that read from the database, apply business rules, and return verified results.

Phase 2 builds that layer: typed Python functions for every inventory action.

---

## What was built

### `src/services/inventory_service.py`

Core database access functions. Each opens a connection, validates inputs, and closes cleanly.

Functions:

- `get_all_products()` — full catalogue with current stock
- `get_product(product_id)`, `get_product(sku)`, `get_product(name)` — lookup by ID, SKU, or partial name
- `search_products(query)` — search across name, SKU, category
- `get_stock(product_id)` — current quantity + threshold
- `list_low_stock(threshold)` — products below their min threshold
- `list_out_of_stock()` — products with 0 stock
- `list_overstock(multiplier)` — products with stock 3x above minimum
- `update_stock(product_id, new_qty)` — set quantity (validated: non-negative)
- `adjust_stock(product_id, delta)` — add/subtract (validated: result non-negative)
- `inventory_summary()` — counts, total value, low/out counts
- `validate_product(product_id)` — existence check

### `src/tools/inventory_tools.py`

Agent-facing wrappers. Each returns plain JSON-like dicts and never trusts the LLM for calculations.

Tools:
- `tool_get_stock(name_or_sku)`
- `tool_list_low_stock(threshold)`
- `tool_list_out_of_stock()`
- `tool_inventory_summary()`
- `tool_search_products(query)`
- `tool_update_stock(product_id, qty)`
- `tool_adjust_stock(product_id, delta)`

### `tests/test_inventory_service.py`

5 automated tests covering:
- count verification (100 products)
- low-stock subset logic
- single product lookup
- update + adjust + restore cycle
- out-of-stock filtering

Run with: `python -m pytest tests/test_inventory_service.py -q`

### `tests/test_phase2_manual.py`

A full manual verification script that runs every function against the real database and prints results. This proves the layer works with actual data, not mock fixtures.

Run with: `python tests/test_phase2_manual.py`

---

## How to test Phase 2

### Automated
```bash
python -m pytest tests/test_inventory_service.py -q
```
Expected: `5 passed`

### Manual (with real data)
```bash
python tests/test_phase2_manual.py
```
Expected output:
```
1. All products: 100
2. Summary: {...}
3. Low stock count: 28
4. Out of stock count: 10
...
=== ALL MANUAL CHECKS PASSED ===
```

### Quick command checks
```bash
python -c "from src.services.inventory_service import get_stock, list_low_stock; print('low:', len(list_low_stock()))"
python -c "from src.services.inventory_service import inventory_summary; print(inventory_summary())"
python -c "from src.services.inventory_service import search_products; print('search:', len(search_products('Smart')))
```

---

## Design rules (why it works)

- **All calculations in Python, not the LLM.** Numbers come from SQL + Python arithmetic.
- **Validation guardrails.** `update_stock` and `adjust_stock` reject negative results. The LLM cannot accidentally set stock to -50.
- **Idempotent reads.** Queries never change the database.
- **Clean connections.** Every function opens and closes its own SQLite connection (no leaks).
- **No external APIs.** Everything reads from `data/inventory.db` — works offline.

---

## What comes next (Phase 3)

Phase 2 gives us validated inventory actions. Phase 3 adds **sales analysis** (`sales_service.py`) and **demand forecasting** (`forecast_service.py`). The agent will then combine inventory tools + sales data + forecasts to make reorder recommendations.

---

## Quick reference

| Task | Command |
|---|---|
| Auto tests | `python -m pytest tests/test_inventory_service.py -q` |
| Manual full test | `python tests/test_phase2_manual.py` |
| Low stock query | `python -c "from src.services.inventory_service import list_low_stock; print(len(list_low_stock()))"` |
| Inventory summary | `python -c "from src.services.inventory_service import inventory_summary; print(inventory_summary())"` |

---

*Phase 2 complete. Held locally. Awaiting go-ahead for Phase 3 and final push.*