"""Dashboard and data endpoints - live reads through the service layer."""
from __future__ import annotations

import os
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from src.api.schemas import HealthResponse
from src.config import DATABASE_PATH, LLM_MODEL
from src.services.dashboard_service import build_dashboard_payload, list_products_with_sales
from src.services.forecast_service import forecast_demand, validate_forecast
from src.services.inventory_service import get_product, list_low_stock, list_out_of_stock
from src.services.reorder_service import recommend_all
from src.services.sales_service import (
    daily_series,
    daily_totals,
    revenue_by_category,
    sales_summary,
    top_sellers,
)

router = APIRouter(prefix="/api", tags=["dashboard"])

# Reorder recommendations run a forecast per product; cache briefly so
# repeated dashboard loads stay snappy without serving stale-old data.
_reorder_cache: dict = {"ts": 0.0, "key": None, "items": None}
_REORDER_TTL_SECONDS = 30.0


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        model=LLM_MODEL,
        database_ready=os.path.exists(DATABASE_PATH),
    )


@router.get("/dashboard")
def dashboard() -> dict:
    """Full dashboard payload (same shape as the offline data.js snapshot)."""
    return build_dashboard_payload()


@router.get("/products")
def products() -> dict:
    return {"products": list_products_with_sales()}


@router.get("/low-stock")
def low_stock(threshold: Optional[int] = Query(default=None, ge=0)) -> dict:
    return {"items": list_low_stock(threshold=threshold)}


@router.get("/out-of-stock")
def out_of_stock() -> dict:
    return {"items": list_out_of_stock()}


@router.get("/top-sellers")
def top_sellers_endpoint(
    limit: int = Query(default=10, ge=1, le=100),
    days: Optional[int] = Query(default=None, ge=1, le=3650),
) -> dict:
    return {"items": top_sellers(n=limit, days=days)}


@router.get("/sales/summary")
def sales_summary_endpoint(days: Optional[int] = Query(default=None, ge=1, le=3650)) -> dict:
    return sales_summary(days=days)


@router.get("/sales/daily")
def sales_daily(days: int = Query(default=30, ge=7, le=365)) -> dict:
    return {"days": days, "series": daily_totals(days=days)}


@router.get("/sales/categories")
def sales_categories(days: Optional[int] = Query(default=None, ge=1, le=3650)) -> dict:
    return {"items": revenue_by_category(days=days)}


@router.get("/forecast/{sku}")
def forecast(sku: str, horizon: int = Query(default=7, ge=1, le=90)) -> dict:
    """History plus demand forecast for one product (by SKU)."""
    p = get_product(sku=sku) or get_product(sku=sku.upper())
    if not p:
        raise HTTPException(status_code=404, detail=f"SKU '{sku}' not found.")

    series = daily_series(p["product_id"], days=90)
    history = [{"date": idx.date().isoformat(), "units": int(v)} for idx, v in series.items()]
    f = forecast_demand(p["product_id"], horizon=horizon)
    validation = validate_forecast(p["product_id"])
    return {
        "sku": p["sku"],
        "name": p["name"],
        "category": p["category"],
        "price": p["price"],
        "current_stock": p["current_stock"],
        "min_stock_threshold": p["min_stock_threshold"],
        "method": f["method"],
        "history": history,
        "forecast": f["forecast"],
        "forecast_total": f["total_predicted"],
        "metrics": validation.get("metrics", {}),
    }


@router.get("/reorder")
def reorder(
    limit: int = Query(default=50, ge=1, le=200),
    only_needed: bool = Query(default=True),
) -> dict:
    """Reorder recommendations, most urgent first."""
    key = (limit, only_needed)
    now = time.time()
    if _reorder_cache["key"] == key and now - _reorder_cache["ts"] < _REORDER_TTL_SECONDS:
        return {"items": _reorder_cache["items"]}
    items = recommend_all(limit=limit, only_needed=only_needed)
    _reorder_cache.update({"ts": now, "key": key, "items": items})
    return {"items": items}
