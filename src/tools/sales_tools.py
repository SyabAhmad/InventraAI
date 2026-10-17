from __future__ import annotations

from src.services.sales_service import (
    daily_totals,
    revenue_by_category,
    sales_summary,
    slow_movers,
    top_sellers,
)
from src.services.sales_service import sales_trend as _trend


def tool_sales_summary(days: int | None = None) -> dict:
    return sales_summary(days=days)


def tool_daily_sales(days: int = 30) -> list[dict]:
    """Units and revenue per day - chart-ready series."""
    return daily_totals(days=days)


def tool_top_sellers(n: int = 10, days: int | None = None) -> list[dict]:
    return top_sellers(n=n, days=days)


def tool_slow_movers(n: int = 10, days: int | None = None) -> list[dict]:
    return slow_movers(n=n, days=days)


def tool_sales_trend(product_name_or_sku: str, freq: str = "W") -> list[dict]:
    from src.services.inventory_service import get_product
    p = get_product(name=product_name_or_sku) or get_product(sku=product_name_or_sku)
    if not p:
        return [{"error": f"Product '{product_name_or_sku}' not found."}]
    return _trend(p["product_id"], freq=freq)


def tool_revenue_by_category(days: int | None = None) -> list[dict]:
    return revenue_by_category(days=days)