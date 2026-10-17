"""LangChain tool definitions for the inventory agent.

Every tool wraps the validated service/tool layer (Phases 2-3), so the LLM
never computes numbers itself - it only chooses which tool to call and
explains the returned data.
"""
from __future__ import annotations

from langchain_core.tools import tool

from src.tools.forecast_tools import (
    tool_compare_forecast_methods,
    tool_forecast_demand,
    tool_validate_forecast,
)
from src.tools.inventory_tools import (
    tool_get_stock,
    tool_inventory_summary,
    tool_list_low_stock,
    tool_list_out_of_stock,
    tool_search_products,
)
from src.tools.reorder_tools import (
    tool_recommend_all,
    tool_recommend_reorder,
    tool_reorder_summary,
)
from src.tools.sales_tools import (
    tool_daily_sales,
    tool_product_daily_sales,
    tool_revenue_by_category,
    tool_sales_summary,
    tool_slow_movers,
    tool_top_sellers,
)
from src.tools.chart_tools import (
    tool_make_bar_chart,
    tool_make_line_chart,
    tool_make_pie_chart,
)


@tool
def get_stock(product_name_or_sku: str) -> dict:
    """Get current stock level, minimum threshold, price and status for one product.
    Use for questions like "how many units of X are available?"."""
    return tool_get_stock(product_name_or_sku)


@tool
def list_low_stock() -> list:
    """List all products whose current stock is below their minimum threshold."""
    return tool_list_low_stock()


@tool
def list_out_of_stock() -> list:
    """List all products with zero units in stock."""
    return tool_list_out_of_stock()


@tool
def inventory_summary() -> dict:
    """High-level inventory summary: total products, stock units, low/out counts, value."""
    return tool_inventory_summary()


@tool
def search_products(query: str) -> list:
    """Search the catalogue by product name, SKU, or category."""
    return tool_search_products(query)


@tool
def sales_summary() -> dict:
    """All-time sales totals: units sold, revenue, order count, products sold."""
    return tool_sales_summary()


@tool
def top_sellers() -> list:
    """Fastest-selling products ranked by units sold."""
    return tool_top_sellers(n=10)


@tool
def slow_movers() -> list:
    """Slowest-selling products (including zero-sales items)."""
    return tool_slow_movers(n=10)


@tool
def revenue_by_category() -> list:
    """Revenue and units grouped by product category."""
    return tool_revenue_by_category()


@tool
def forecast_demand(product_name_or_sku: str) -> dict:
    """Forecast demand for one product over the configured horizon (7 days by default)."""
    return tool_forecast_demand(product_name_or_sku)


@tool
def validate_forecast(product_name_or_sku: str) -> dict:
    """Evaluate forecast accuracy (MAE/MAPE/RMSE) for one product on a held-out split."""
    return tool_validate_forecast(product_name_or_sku)


@tool
def compare_forecast_methods(product_name_or_sku: str) -> list:
    """Compare moving average vs exponential smoothing vs linear trend for one product."""
    return tool_compare_forecast_methods(product_name_or_sku)


@tool
def recommend_reorder(product_name_or_sku: str) -> dict:
    """Full reorder recommendation for one product: reorder point, safety stock,
    forecast demand, suggested quantity, and urgency."""
    return tool_recommend_reorder(product_name_or_sku)


@tool
def recommend_all_reorders() -> list:
    """Reorder recommendations for every product that currently needs restocking."""
    return tool_recommend_all(limit=25)


@tool
def reorder_summary() -> dict:
    """Counts of products needing reorder by urgency (critical/high/medium) and total units."""
    return tool_reorder_summary()


@tool
def daily_sales_data(days: int = 30) -> list:
    """Daily units and revenue for the last N days (chart-ready series).
    Use as the data source before calling a chart tool."""
    return tool_daily_sales(days=days)


@tool
def product_sales_data(product_name_or_sku: str, days: int = 30) -> dict:
    """Daily units sold for ONE product (name or SKU) over the last N days with data.
    Chart-ready: use days[].date as labels and days[].units as values. Use this
    whenever the question is about a specific product's sales trend."""
    return tool_product_daily_sales(product_name_or_sku, days=days)


@tool
def make_bar_chart(title: str, labels: list, values: list, value_label: str = "Value") -> str:
    """Render a BAR chart in the chat. Pass labels (names/dates/categories) and
    values copied EXACTLY from a data tool result. Returns a chart specification."""
    return tool_make_bar_chart(title, labels, values, value_label)


@tool
def make_line_chart(title: str, labels: list, values: list, value_label: str = "Value") -> str:
    """Render a LINE chart in the chat (trends over time). Pass labels and values
    copied EXACTLY from a data tool result. Returns a chart specification."""
    return tool_make_line_chart(title, labels, values, value_label)


@tool
def make_pie_chart(title: str, labels: list, values: list, value_label: str = "Value") -> str:
    """Render a PIE chart in the chat (shares of a total). Pass labels and values
    copied EXACTLY from a data tool result. Returns a chart specification."""
    return tool_make_pie_chart(title, labels, values, value_label)


AGENT_TOOLS = [
    get_stock,
    list_low_stock,
    list_out_of_stock,
    inventory_summary,
    search_products,
    sales_summary,
    top_sellers,
    slow_movers,
    revenue_by_category,
    forecast_demand,
    validate_forecast,
    compare_forecast_methods,
    recommend_reorder,
    recommend_all_reorders,
    reorder_summary,
    daily_sales_data,
    product_sales_data,
    make_bar_chart,
    make_line_chart,
    make_pie_chart,
]