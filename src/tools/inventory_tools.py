"""Tool functions exposed to the inventory agent.

Each function returns plain JSON-serializable data and performs all
calculations/validation in Python (never trusts the LLM for numbers).
"""
from __future__ import annotations

from src.services.inventory_service import (
    adjust_stock,
    get_product,
    get_stock,
    inventory_summary,
    list_low_stock,
    list_out_of_stock,
    list_overstock,
    search_products,
    update_stock,
)


def tool_get_stock(product_name_or_sku: str) -> dict:
    """Look up current stock for a product by name or SKU."""
    p = get_product(name=product_name_or_sku)
    if p is None:
        # try sku
        p = get_product(sku=product_name_or_sku)
    if p is None:
        return {"error": f"Product '{product_name_or_sku}' not found."}
    return {
        "product_id": p["product_id"],
        "sku": p["sku"],
        "name": p["name"],
        "category": p["category"],
        "price": p["price"],
        "min_stock_threshold": p["min_stock_threshold"],
        "current_stock": p["current_stock"],
        "last_updated": p["last_updated"],
    }


def tool_list_low_stock(threshold: int | None = None) -> list[dict]:
    """List products whose current stock is below the minimum threshold."""
    return list_low_stock(threshold=threshold)


def tool_list_out_of_stock() -> list[dict]:
    """List products with zero stock."""
    return list_out_of_stock()


def tool_inventory_summary() -> dict:
    """High-level inventory summary (counts, value)."""
    return inventory_summary()


def tool_search_products(query: str) -> list[dict]:
    """Search products by name, SKU, or category."""
    return search_products(query)


def tool_update_stock(product_id: int, new_qty: int) -> dict:
    """Set a product's stock to a new quantity (validated, non-negative)."""
    try:
        return update_stock(product_id, new_qty)
    except ValueError as e:
        return {"error": str(e)}


def tool_adjust_stock(product_id: int, delta: int) -> dict:
    """Adjust a product's stock by a delta (can be negative)."""
    try:
        return adjust_stock(product_id, delta)
    except ValueError as e:
        return {"error": str(e)}