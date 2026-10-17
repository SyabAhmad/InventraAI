"""Smart reorder recommendations based on stock, demand forecast, and stock rules."""
from __future__ import annotations

import math
from datetime import date, timedelta

import numpy as np
import pandas as pd

from src.config import (
    FORECAST_HORIZON_DAYS,
    MAX_REORDER_QTY,
    MIN_REORDER_QTY,
    REORDER_LEAD_TIME_DAYS,
    REORDER_SAFETY_FACTOR,
)
from src.database.connection import get_connection
from src.services.forecast_service import forecast_demand, daily_series
from src.services.inventory_service import get_product


def _daily_stats(product_id: int, days: int = 90) -> tuple[float, float]:
    s = daily_series(product_id, days=days)
    vals = s.values.astype(float)
    if len(vals) == 0:
        return 0.0, 0.0
    return float(np.mean(vals)), float(np.std(vals))


def recommend_reorder(product_id: int, horizon: int | None = None,
                      method: str = "moving_average") -> dict:
    horizon = horizon or FORECAST_HORIZON_DAYS
    p = get_product(product_id=product_id)
    if not p:
        return {"error": f"Product {product_id} not found."}
    current = int(p["current_stock"])
    min_thr = int(p["min_stock_threshold"])
    avg_daily, std_daily = _daily_stats(product_id)
    # safety stock
    safety = REORDER_SAFETY_FACTOR * std_daily * math.sqrt(REORDER_LEAD_TIME_DAYS)
    # demand during lead time
    lead_demand = avg_daily * REORDER_LEAD_TIME_DAYS
    reorder_point = lead_demand + safety
    # forecasted demand over horizon
    f = forecast_demand(product_id, horizon=horizon, method=method)
    forecast_total = int(f["total_predicted"])
    # recommended order qty to cover horizon + safety - current
    needed = (forecast_total + int(round(safety))) - current
    if needed < 0:
        needed = 0
    # enforce min/max
    if needed > 0:
        needed = max(needed, MIN_REORDER_QTY)
        needed = min(needed, MAX_REORDER_QTY)
    # urgency
    if current <= 0:
        urgency = "CRITICAL"
    elif current < min_thr:
        urgency = "HIGH"
    elif current <= reorder_point:
        urgency = "MEDIUM"
    else:
        urgency = "LOW"

    recommend = needed > 0 and (current <= reorder_point or current < min_thr)
    reason = (
        f"current_stock={current}, min_threshold={min_thr}, "
        f"avg_daily_demand={round(avg_daily,2)}, std={round(std_daily,2)}, "
        f"lead_time_days={REORDER_LEAD_TIME_DAYS}, safety_stock={round(safety,1)}, "
        f"reorder_point={round(reorder_point,1)}, forecast_{horizon}d={forecast_total}."
    )
    return {
        "product_id": product_id,
        "sku": p["sku"],
        "name": p["name"],
        "category": p["category"],
        "price": p["price"],
        "current_stock": current,
        "min_stock_threshold": min_thr,
        "avg_daily_demand": round(avg_daily, 2),
        "std_daily_demand": round(std_daily, 2),
        "reorder_point": round(reorder_point, 1),
        "safety_stock": round(safety, 1),
        "forecast_horizon_days": horizon,
        "forecasted_demand": forecast_total,
        "recommended_reorder_qty": int(needed) if recommend else 0,
        "urgency": urgency,
        "should_reorder": bool(recommend),
        "reason": reason,
    }


def recommend_all(limit: int | None = None, only_needed: bool = True) -> list[dict]:
    conn = get_connection()
    try:
        ids = [r[0] for r in conn.execute("SELECT product_id FROM products ORDER BY product_id;").fetchall()]
    finally:
        conn.close()
    out = []
    for pid in ids:
        r = recommend_reorder(pid)
        if "error" in r:
            continue
        if only_needed and not r["should_reorder"]:
            continue
        out.append(r)
    # sort by urgency then recommended qty desc
    urgency_rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    out.sort(key=lambda x: (urgency_rank.get(x["urgency"], 9), -x["recommended_reorder_qty"]))
    if limit:
        out = out[:limit]
    return out


def reorder_summary() -> dict:
    all_recs = recommend_all(only_needed=False)
    needed = [r for r in all_recs if r["should_reorder"]]
    return {
        "total_products": len(all_recs),
        "products_needing_reorder": len(needed),
        "critical": sum(1 for r in needed if r["urgency"] == "CRITICAL"),
        "high": sum(1 for r in needed if r["urgency"] == "HIGH"),
        "medium": sum(1 for r in needed if r["urgency"] == "MEDIUM"),
        "total_recommended_units": sum(r["recommended_reorder_qty"] for r in needed),
    }