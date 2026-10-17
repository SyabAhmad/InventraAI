"""Generate frontend/js/data.js from the SQLite database (Phase-1 compatible)."""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import DATABASE_PATH


def _conn():
    c = sqlite3.connect(DATABASE_PATH)
    c.row_factory = sqlite3.Row
    return c


def build_data() -> dict:
    conn = _conn()
    try:
        products = [dict(r) for r in conn.execute(
            """SELECT p.product_id, p.sku, p.name, p.category, p.price, p.cost,
                      p.min_stock_threshold, p.supplier,
                      COALESCE(i.current_stock,0) AS current_stock, i.last_updated
               FROM products p LEFT JOIN inventory i ON p.product_id=i.product_id
               ORDER BY p.product_id;"""
        ).fetchall()]

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

        sales_rows = conn.execute(
            """SELECT product_id, COALESCE(SUM(quantity),0) AS units, COALESCE(SUM(quantity*unit_price),0) AS rev
               FROM sales GROUP BY product_id;"""
        ).fetchall()
        sales_map = {r["product_id"]: {"units": r["units"], "rev": r["rev"]} for r in sales_rows}
        for p in products:
            s = sales_map.get(p["product_id"], {})
            p["total_units_sold"] = int(s.get("units", 0))
            p["total_revenue"] = float(s.get("rev", 0) or 0)

        top_rows = conn.execute(
            """SELECT s.product_id, SUM(s.quantity) AS total_units, SUM(s.quantity*s.unit_price) AS total_revenue
               FROM sales s GROUP BY s.product_id ORDER BY total_units DESC LIMIT 10;"""
        ).fetchall()
        top_sellers = []
        for r in top_rows:
            prod = next((p for p in products if p["product_id"] == r["product_id"]), None)
            if prod:
                top_sellers.append({
                    "product_id": r["product_id"],
                    "name": prod["name"],
                    "category": prod["category"],
                    "total_units": int(r["total_units"]),
                    "total_revenue": float(r["total_revenue"] or 0),
                })
    finally:
        conn.close()

    # safe config snapshot (no secrets)
    try:
        from src import config as _cfg
        cfg = {
            "LLM_PROVIDER": _cfg.LLM_PROVIDER,
            "LLM_MODEL": _cfg.LLM_MODEL,
            "LLM_BASE_URL": _cfg.LLM_BASE_URL,
            "DATABASE_PATH": _cfg.DATABASE_PATH,
            "DEFAULT_MIN_STOCK": _cfg.DEFAULT_MIN_STOCK,
            "FORECAST_HORIZON_DAYS": _cfg.FORECAST_HORIZON_DAYS,
        }
    except Exception:
        cfg = {}

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "config": cfg,
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
    }


def main():
    data = build_data()
    out_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "js", "data.js")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("window.PRODUCTS_DATA = " + json.dumps(data) + ";\n")
    print("Generated:", out_path)
    print("Products:", len(data["products"]), "| Low stock:", data["summary"]["low_stock_count"], "| Out of stock:", data["summary"]["out_of_stock_count"])


if __name__ == "__main__":
    main()