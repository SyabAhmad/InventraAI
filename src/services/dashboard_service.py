"""Dashboard data assembly shared by the API and the static snapshot generator."""
from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any

from src.database.connection import get_connection
from src.services.sales_service import daily_totals


def _safe_config() -> dict[str, Any]:
    """Config snapshot for the dashboard (never exposes the API key)."""
    try:
        from src import config as _cfg

        return {
            "LLM_PROVIDER": _cfg.LLM_PROVIDER,
            "LLM_MODEL": _cfg.LLM_MODEL,
            "LLM_BASE_URL": _cfg.LLM_BASE_URL,
            "DATABASE_PATH": _cfg.DATABASE_PATH,
            "DEFAULT_MIN_STOCK": _cfg.DEFAULT_MIN_STOCK,
            "FORECAST_HORIZON_DAYS": _cfg.FORECAST_HORIZON_DAYS,
        }
    except Exception:  # pragma: no cover - config import should not fail in practice
        return {}


def list_products_with_sales() -> list[dict]:
    """All products joined with inventory and all-time sales aggregates."""
    conn = get_connection()
    try:
        conn.row_factory = sqlite3.Row
        products = [dict(r) for r in conn.execute(
            """SELECT p.product_id, p.sku, p.name, p.category, p.price, p.cost,
                      p.min_stock_threshold, p.supplier,
                      COALESCE(i.current_stock,0) AS current_stock, i.last_updated
               FROM products p LEFT JOIN inventory i ON p.product_id=i.product_id
               ORDER BY p.product_id;"""
        ).fetchall()]
        sales_rows = conn.execute(
            """SELECT product_id, COALESCE(SUM(quantity),0) AS units,
                      COALESCE(SUM(quantity*unit_price),0) AS rev
               FROM sales GROUP BY product_id;"""
        ).fetchall()
    finally:
        conn.close()

    sales_map = {r["product_id"]: {"units": r["units"], "rev": r["rev"]} for r in sales_rows}
    for p in products:
        s = sales_map.get(p["product_id"], {})
        p["total_units_sold"] = int(s.get("units", 0))
        p["total_revenue"] = float(s.get("rev", 0) or 0)
    return products


def build_dashboard_payload() -> dict:
    """Build the full dashboard payload from the SQLite database.

    The shape matches `frontend/js/data.js` so the same frontend renders
    identically from the bundled snapshot or from live API data.
    """
    products = list_products_with_sales()

    conn = get_connection()
    try:
        conn.row_factory = sqlite3.Row
        total_stock = conn.execute("SELECT COALESCE(SUM(current_stock),0) FROM inventory;").fetchone()[0]
        low_count = conn.execute(
            """SELECT COUNT(*) FROM products p JOIN inventory i ON p.product_id=i.product_id
               WHERE i.current_stock < p.min_stock_threshold;"""
        ).fetchone()[0]
        out_count = conn.execute("SELECT COUNT(*) FROM inventory WHERE current_stock=0;").fetchone()[0]
        total_value = conn.execute(
            """SELECT COALESCE(SUM(i.current_stock * p.price),0)
               FROM products p JOIN inventory i ON p.product_id=i.product_id;"""
        ).fetchone()[0]

        low_stock = [dict(r) for r in conn.execute(
            """SELECT p.product_id, p.sku, p.name, p.category, p.price,
                      p.min_stock_threshold, COALESCE(i.current_stock,0) AS current_stock
               FROM products p JOIN inventory i ON p.product_id=i.product_id
               WHERE i.current_stock < p.min_stock_threshold
               ORDER BY i.current_stock ASC;"""
        ).fetchall()]
        out_of_stock = [dict(r) for r in conn.execute(
            """SELECT p.product_id, p.sku, p.name, p.category, p.price,
                      p.min_stock_threshold, COALESCE(i.current_stock,0) AS current_stock
               FROM products p JOIN inventory i ON p.product_id=i.product_id
               WHERE i.current_stock = 0 ORDER BY p.name;"""
        ).fetchall()]

        top_rows = conn.execute(
            """SELECT s.product_id, SUM(s.quantity) AS total_units,
                      SUM(s.quantity*s.unit_price) AS total_revenue
               FROM sales s GROUP BY s.product_id ORDER BY total_units DESC LIMIT 10;"""
        ).fetchall()
    finally:
        conn.close()

    by_id = {p["product_id"]: p for p in products}
    top_sellers = []
    for r in top_rows:
        prod = by_id.get(r["product_id"])
        if prod:
            top_sellers.append({
                "product_id": r["product_id"],
                "name": prod["name"],
                "category": prod["category"],
                "total_units": int(r["total_units"]),
                "total_revenue": float(r["total_revenue"] or 0),
            })

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "config": _safe_config(),
        "summary": {
            "total_products": len(products),
            "total_stock_units": int(total_stock),
            "low_stock_count": int(low_count),
            "out_of_stock_count": int(out_count),
            "inventory_value_at_price": round(float(total_value), 2),
        },
        "low_stock": low_stock,
        "out_of_stock": out_of_stock,
        "top_sellers": top_sellers,
        "products": products,
        "sales_daily_30d": daily_totals(30),
    }
