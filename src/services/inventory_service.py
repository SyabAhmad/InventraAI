"""Inventory data access and business logic."""
from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any

from src.config import LOW_STOCK_ALERT_THRESHOLD
from src.database.connection import get_connection


def _rows_to_dicts(rows) -> list[dict]:
    return [dict(r) for r in rows]


def get_all_products() -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT p.product_id, p.sku, p.name, p.category, p.price, p.cost,
                      p.min_stock_threshold, p.supplier,
                      COALESCE(i.current_stock, 0) AS current_stock, i.last_updated
               FROM products p LEFT JOIN inventory i ON p.product_id = i.product_id
               ORDER BY p.product_id;"""
        ).fetchall()
        return _rows_to_dicts(rows)
    finally:
        conn.close()


def get_product(product_id: int | None = None, sku: str | None = None,
                name: str | None = None) -> dict | None:
    conn = get_connection()
    try:
        if product_id is not None:
            row = conn.execute(
                """SELECT p.*, COALESCE(i.current_stock,0) AS current_stock, i.last_updated
                   FROM products p LEFT JOIN inventory i ON p.product_id=i.product_id
                   WHERE p.product_id=?""", (product_id,)).fetchone()
        elif sku:
            row = conn.execute(
                """SELECT p.*, COALESCE(i.current_stock,0) AS current_stock, i.last_updated
                   FROM products p LEFT JOIN inventory i ON p.product_id=i.product_id
                   WHERE p.sku=?""", (sku,)).fetchone()
        elif name:
            row = conn.execute(
                """SELECT p.*, COALESCE(i.current_stock,0) AS current_stock, i.last_updated
                   FROM products p LEFT JOIN inventory i ON p.product_id=i.product_id
                   WHERE LOWER(p.name) LIKE LOWER(?)""", (f"%{name}%",)).fetchone()
        else:
            return None
        return dict(row) if row else None
    finally:
        conn.close()


def search_products(query: str) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT p.product_id, p.sku, p.name, p.category, p.price,
                      p.min_stock_threshold, COALESCE(i.current_stock,0) AS current_stock
               FROM products p LEFT JOIN inventory i ON p.product_id=i.product_id
               WHERE LOWER(p.name) LIKE LOWER(?) OR LOWER(p.sku) LIKE LOWER(?)
                  OR LOWER(p.category) LIKE LOWER(?)
               ORDER BY p.name;""",
            (f"%{query}%", f"%{query}%", f"%{query}%"),
        ).fetchall()
        return _rows_to_dicts(rows)
    finally:
        conn.close()


def get_stock(product_id: int) -> dict | None:
    p = get_product(product_id=product_id)
    if not p:
        return None
    return {
        "product_id": p["product_id"],
        "sku": p["sku"],
        "name": p["name"],
        "current_stock": p["current_stock"],
        "min_stock_threshold": p["min_stock_threshold"],
        "last_updated": p["last_updated"],
    }


def list_low_stock(threshold: int | None = None) -> list[dict]:
    thr = threshold if threshold is not None else LOW_STOCK_ALERT_THRESHOLD
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT p.product_id, p.sku, p.name, p.category, p.price,
                      p.min_stock_threshold, COALESCE(i.current_stock,0) AS current_stock
               FROM products p LEFT JOIN inventory i ON p.product_id=i.product_id
               WHERE COALESCE(i.current_stock,0) < COALESCE(p.min_stock_threshold, ?)
               ORDER BY (COALESCE(i.current_stock,0) - p.min_stock_threshold) ASC;""",
            (thr,),
        ).fetchall()
        return _rows_to_dicts(rows)
    finally:
        conn.close()


def list_out_of_stock() -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT p.product_id, p.sku, p.name, p.category, p.price,
                      p.min_stock_threshold, COALESCE(i.current_stock,0) AS current_stock
               FROM products p LEFT JOIN inventory i ON p.product_id=i.product_id
               WHERE COALESCE(i.current_stock,0) = 0
               ORDER BY p.name;"""
        ).fetchall()
        return _rows_to_dicts(rows)
    finally:
        conn.close()


def list_overstock(multiplier: float = 3.0) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT p.product_id, p.sku, p.name, p.category, p.price,
                      p.min_stock_threshold, COALESCE(i.current_stock,0) AS current_stock
               FROM products p LEFT JOIN inventory i ON p.product_id=i.product_id
               WHERE COALESCE(i.current_stock,0) > p.min_stock_threshold * ?
               ORDER BY current_stock DESC;""",
            (multiplier,),
        ).fetchall()
        return _rows_to_dicts(rows)
    finally:
        conn.close()


def update_stock(product_id: int, new_qty: int, reason: str = "manual") -> dict:
    if new_qty < 0:
        raise ValueError("Stock quantity cannot be negative.")
    conn = get_connection()
    try:
        cur = conn.execute(
            "UPDATE inventory SET current_stock=?, last_updated=? WHERE product_id=?",
            (new_qty, datetime.now().isoformat(), product_id),
        )
        if cur.rowcount == 0:
            raise ValueError(f"Product {product_id} not found in inventory.")
        conn.commit()
        return get_stock(product_id) or {}
    finally:
        conn.close()


def adjust_stock(product_id: int, delta: int, reason: str = "adjustment") -> dict:
    p = get_product(product_id=product_id)
    if not p:
        raise ValueError(f"Product {product_id} not found.")
    new_qty = p["current_stock"] + delta
    if new_qty < 0:
        raise ValueError("Resulting stock cannot be negative.")
    return update_stock(product_id, new_qty, reason=reason)


def inventory_summary() -> dict:
    conn = get_connection()
    try:
        total_products = conn.execute("SELECT COUNT(*) FROM products;").fetchone()[0]
        total_stock = conn.execute("SELECT COALESCE(SUM(current_stock),0) FROM inventory;").fetchone()[0]
        low = conn.execute(
            """SELECT COUNT(*) FROM products p JOIN inventory i ON p.product_id=i.product_id
               WHERE i.current_stock < p.min_stock_threshold;"""
        ).fetchone()[0]
        out = conn.execute("SELECT COUNT(*) FROM inventory WHERE current_stock=0;").fetchone()[0]
        total_value = conn.execute(
            """SELECT COALESCE(SUM(i.current_stock * p.price),0)
               FROM products p JOIN inventory i ON p.product_id=i.product_id;"""
        ).fetchone()[0]
        return {
            "total_products": total_products,
            "total_stock_units": total_stock,
            "low_stock_count": low,
            "out_of_stock_count": out,
            "inventory_value_at_price": round(float(total_value), 2),
        }
    finally:
        conn.close()


def validate_product(product_id: int) -> bool:
    conn = get_connection()
    try:
        row = conn.execute("SELECT 1 FROM products WHERE product_id=?", (product_id,)).fetchone()
        return row is not None
    finally:
        conn.close()