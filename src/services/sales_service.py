"""Sales data analysis for e-commerce inventory."""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

import pandas as pd

from src.database.connection import get_connection


def _load_sales(product_id: int | None = None, days: int | None = None) -> pd.DataFrame:
    conn = get_connection()
    try:
        q = "SELECT sale_id, product_id, quantity, unit_price, sale_date, channel FROM sales WHERE 1=1"
        params: list = []
        if product_id is not None:
            q += " AND product_id = ?"
            params.append(product_id)
        if days is not None:
            cutoff = (date.today() - timedelta(days=days)).isoformat()
            q += " AND sale_date >= ?"
            params.append(cutoff)
        df = pd.read_sql_query(q, conn, params=params)
    finally:
        conn.close()
    if not df.empty:
        df["sale_date"] = pd.to_datetime(df["sale_date"])
        df["revenue"] = df["quantity"] * df["unit_price"]
    return df


def sales_summary(days: int | None = None) -> dict:
    df = _load_sales(days=days)
    if df.empty:
        return {"total_units": 0, "total_revenue": 0.0, "total_orders": 0, "avg_order_qty": 0.0}
    return {
        "total_units": int(df["quantity"].sum()),
        "total_revenue": round(float(df["revenue"].sum()), 2),
        "total_orders": int(len(df)),
        "avg_order_qty": round(float(df["quantity"].mean()), 2),
        "unique_products_sold": int(df["product_id"].nunique()),
    }


def sales_by_product(days: int | None = None) -> pd.DataFrame:
    df = _load_sales(days=days)
    if df.empty:
        return pd.DataFrame()
    g = df.groupby("product_id").agg(
        total_units=("quantity", "sum"),
        total_revenue=("revenue", "sum"),
        orders=("sale_id", "count"),
        avg_qty=("quantity", "mean"),
    ).reset_index()
    return g.sort_values("total_units", ascending=False)


def top_sellers(n: int = 10, days: int | None = None) -> list[dict]:
    g = sales_by_product(days=days)
    if g.empty:
        return []
    # attach product names
    conn = get_connection()
    try:
        prod = pd.read_sql_query("SELECT product_id, sku, name, category FROM products", conn)
    finally:
        conn.close()
    g = g.merge(prod, on="product_id", how="left")
    return g.head(n).to_dict(orient="records")


def slow_movers(n: int = 10, days: int | None = None) -> list[dict]:
    g = sales_by_product(days=days)
    if g.empty:
        return []
    conn = get_connection()
    try:
        prod = pd.read_sql_query("SELECT product_id, sku, name, category FROM products", conn)
    finally:
        conn.close()
    g = g.merge(prod, on="product_id", how="left")
    # include products with zero sales
    all_ids = prod["product_id"].tolist()
    sold_ids = set(g["product_id"].tolist())
    zero = prod[~prod["product_id"].isin(sold_ids)].copy()
    zero["total_units"] = 0
    zero["total_revenue"] = 0.0
    zero["orders"] = 0
    zero["avg_qty"] = 0.0
    g = pd.concat([g, zero], ignore_index=True)
    g = g.sort_values("total_units", ascending=True)
    return g.head(n).to_dict(orient="records")


def sales_trend(product_id: int, freq: str = "W") -> list[dict]:
    df = _load_sales(product_id=product_id)
    if df.empty:
        return []
    s = df.set_index("sale_date")["quantity"].resample(freq).sum()
    out = [{"period": str(idx.date()), "units": int(v)} for idx, v in s.items()]
    return out


def daily_series(product_id: int, days: int = 90) -> pd.Series:
    df = _load_sales(product_id=product_id, days=days)
    if df.empty:
        idx = pd.date_range(end=date.today(), periods=days, freq="D")
        return pd.Series(0, index=idx)
    s = df.set_index("sale_date")["quantity"].resample("D").sum()
    # reindex to full range
    full = pd.date_range(end=date.today(), periods=days, freq="D")
    s = s.reindex(full, fill_value=0)
    return s


def revenue_by_category(days: int | None = None) -> list[dict]:
    df = _load_sales(days=days)
    if df.empty:
        return []
    conn = get_connection()
    try:
        prod = pd.read_sql_query("SELECT product_id, category FROM products", conn)
    finally:
        conn.close()
    df = df.merge(prod, on="product_id", how="left")
    g = df.groupby("category").agg(units=("quantity", "sum"), revenue=("revenue", "sum")).reset_index()
    return g.to_dict(orient="records")