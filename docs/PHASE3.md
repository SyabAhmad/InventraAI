# Phase 3 — Sales Analysis & Demand Forecasting

> **Branch:** `phase-3-sales-forecast`
> **Status:** Complete · Held locally (not pushed per user request)

Phase 3 connects inventory data (Phase 2) to real business insight. Before recommending restocks, the agent must understand which products sell quickly, which sell slowly, and what demand looks like next week.

---

## What was built

### `src/services/sales_service.py`

Reads the `sales` table and computes:

- `sales_summary(days)` — total units, revenue, orders, unique products sold
- `sales_by_product(days)` — per-product totals (units, revenue, orders)
- `top_sellers(n, days)` — fastest-moving products
- `slow_movers(n, days)` — slowest products + zero-sales products
- `sales_trend(product_id, freq)` — time-series by week/day
- `revenue_by_category(days)` — category-level revenue

### `src/services/forecast_service.py`

Demand forecasting with three baseline methods (selected in `.env` via `FORECAST_METHOD`):

- `moving_average` (default) — 7-day rolling mean
- `exponential_smoothing` — alpha=0.3 smoothing
- `linear_trend` — least-squares trend projection

Functions:

- `forecast_demand(product_id, horizon, method)` — predicts next N days
- `validate_forecast(product_id, method)` — hold out last 14 days, report MAE / MAPE / RMSE
- `compare_methods(product_id)` — compare all three methods on the same validation split

Forecast outputs are always rounded to integer quantities. Metrics use real sales history from `data/inventory.db`.

### `src/tools/sales_tools.py`

Agent-facing wrappers for sales queries.

### `src/tools/forecast_tools.py`

Agent-facing wrappers for forecasting.

### `tests/test_sales_forecast.py`

6 automated tests:
- sales summary exists and has positive totals
- top sellers sorted correctly
- slow movers include zero-sales products
- forecast returns expected number of days
- validation returns MAE/MAPE (if enough history)
- method comparison returns sorted results

Run: `python -m pytest tests/test_sales_forecast.py -q`

### `tests/test_phase2_manual.py`

Full manual verification of Phase 2 (inventory layer) with real DB data.

---

## How Phase 3 connects to Phase 2

Phase 2 gives validated inventory actions. Phase 3 adds sales and forecast data so the reorder recommendation (Phase 4) can say:

> "Current stock = 12, min threshold = 20, forecast next 7 days = 35 units, recommend reorder 30."

Without Phase 3, Phase 4 would only know current stock, not future demand.

---

## Design rules

- **Forecasts never override DB data.** Predictions are labeled clearly; current stock remains authoritative.
- **All methods validated on same split.** `compare_methods()` uses the same 14-day holdout for fair comparison.
- **Integer predictions.** Demand is in discrete units, not decimals.
- **Simple baselines first.** Moving average / smoothing / trend — no black-box models. If data is too small, MAE/MAPE is still reported honestly.
- **No external APIs.** Forecasts read only `data/inventory.db`.

---

## Quick reference

| Task | Command |
|---|---|
| Auto tests | `python -m pytest tests/test_sales_forecast.py -q` |
| Manual inventory test | `python tests/test_phase2_manual.py` |
| Forecast product | `python -c "from src.services.forecast_service import forecast_demand; print(forecast_demand(1, horizon=7))"` |
| Validate forecast | `python -c "from src.services.forecast_service import validate_forecast; print(validate_forecast(1, method='moving_average'))"` |
| Compare methods | `python -c "from src.services.forecast_service import compare_methods; print(compare_methods(1))"` |
| Top sellers | `python -c "from src.services.sales_service import top_sellers; print(top_sellers(5))"` |

---

## Chat UI location (answered)

The natural-language chat interface is part of **Phase 5** (`phase-5-dashboard`), not Phase 3. It uses the agent from Phase 4, which calls the inventory tools (Phase 2) and reads forecasts (Phase 3) to explain recommendations.

---

*Phase 3 complete. Held locally. Not pushed until user confirms.*
