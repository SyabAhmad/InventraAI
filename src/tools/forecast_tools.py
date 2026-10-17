from __future__ import annotations

from src.services.forecast_service import (
    compare_methods,
    forecast_demand,
    validate_forecast,
)


def tool_forecast_demand(product_name_or_sku: str, horizon: int | None = None,
                        method: str | None = None) -> dict:
    from src.services.inventory_service import get_product
    p = get_product(name=product_name_or_sku) or get_product(sku=product_name_or_sku)
    if not p:
        return {"error": f"Product '{product_name_or_sku}' not found."}
    return forecast_demand(p["product_id"], horizon=horizon, method=method)


def tool_validate_forecast(product_name_or_sku: str, method: str = "moving_average") -> dict:
    from src.services.inventory_service import get_product
    p = get_product(name=product_name_or_sku) or get_product(sku=product_name_or_sku)
    if not p:
        return {"error": f"Product '{product_name_or_sku}' not found."}
    return validate_forecast(p["product_id"], method=method)


def tool_compare_forecast_methods(product_name_or_sku: str) -> list[dict]:
    from src.services.inventory_service import get_product
    p = get_product(name=product_name_or_sku) or get_product(sku=product_name_or_sku)
    if not p:
        return [{"error": f"Product '{product_name_or_sku}' not found."}]
    return compare_methods(p["product_id"])