from __future__ import annotations

from src.services.reorder_service import recommend_all, recommend_reorder, reorder_summary


def tool_recommend_reorder(product_name_or_sku: str) -> dict:
    from src.services.inventory_service import get_product
    p = get_product(name=product_name_or_sku) or get_product(sku=product_name_or_sku)
    if not p:
        return {"error": f"Product '{product_name_or_sku}' not found."}
    return recommend_reorder(p["product_id"])


def tool_recommend_all(limit: int = 20) -> list[dict]:
    return recommend_all(limit=limit, only_needed=True)


def tool_reorder_summary() -> dict:
    return reorder_summary()