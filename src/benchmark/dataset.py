"""Benchmark dataset — 20 inventory prompts with expected tool behaviour.

Each entry has:
  id: stable id (p01..p20)
  question: prompt sent to the agent
  category: inventory / sales / forecast / reorder / chart / search
  expected_tools: tools the agent MUST call (subset check; any order OK)
  notes: what "good" looks like
"""
from __future__ import annotations

BENCHMARK_PROMPTS: list[dict] = [
    {"id": "p01", "question": "Show inventory summary", "category": "inventory", "expected_tools": ["inventory_summary"], "notes": "Should give counts + value"},
    {"id": "p02", "question": "Which products are low in stock?", "category": "inventory", "expected_tools": ["list_low_stock"], "notes": "List only below-threshold items"},
    {"id": "p03", "question": "Which products are out of stock?", "category": "inventory", "expected_tools": ["list_out_of_stock"], "notes": "Zero-stock only"},
    {"id": "p04", "question": "How many units of SKU-0001 are available?", "category": "inventory", "expected_tools": ["get_stock"], "notes": "Single product stock lookup"},
    {"id": "p05", "question": "Search products in Books category", "category": "search", "expected_tools": ["search_products"], "notes": "Category search"},
    {"id": "p06", "question": "Show sales summary", "category": "sales", "expected_tools": ["sales_summary"], "notes": "Units + revenue totals"},
    {"id": "p07", "question": "What are the top sellers?", "category": "sales", "expected_tools": ["top_sellers"], "notes": "Ranked by units"},
    {"id": "p08", "question": "Which products are slow movers?", "category": "sales", "expected_tools": ["slow_movers"], "notes": "Lowest units sold"},
    {"id": "p09", "question": "Show revenue by category", "category": "sales", "expected_tools": ["revenue_by_category"], "notes": "Grouped revenue"},
    {"id": "p10", "question": "Forecast demand for SKU-0001", "category": "forecast", "expected_tools": ["forecast_demand"], "notes": "7-day demand forecast"},
    {"id": "p11", "question": "Validate forecast accuracy for SKU-0001", "category": "forecast", "expected_tools": ["validate_forecast"], "notes": "MAE/MAPE on held-out split"},
    {"id": "p12", "question": "Compare forecast methods for SKU-0001", "category": "forecast", "expected_tools": ["compare_forecast_methods"], "notes": "MA vs ES vs linear"},
    {"id": "p13", "question": "Should I restock SKU-0001?", "category": "reorder", "expected_tools": ["recommend_reorder"], "notes": "Urgency + qty from tool"},
    {"id": "p14", "question": "What should I reorder first?", "category": "reorder", "expected_tools": ["recommend_all_reorders"], "notes": "Sorted by urgency"},
    {"id": "p15", "question": "Show reorder summary", "category": "reorder", "expected_tools": ["reorder_summary"], "notes": "Counts by urgency"},
    {"id": "p16", "question": "Make a bar chart of the top sellers", "category": "chart", "expected_tools": ["top_sellers", "make_bar_chart"], "notes": "Data tool then chart tool"},
    {"id": "p17", "question": "Chart daily revenue for the last 30 days", "category": "chart", "expected_tools": ["daily_sales_data", "make_line_chart"], "notes": "Daily series then line chart"},
    {"id": "p18", "question": "Make a pie chart of revenue by category", "category": "chart", "expected_tools": ["revenue_by_category", "make_pie_chart"], "notes": "Category data then pie"},
    {"id": "p19", "question": "Show sales trend for SKU-0001", "category": "chart", "expected_tools": ["product_sales_data"], "notes": "Per-product daily series"},
    {"id": "p20", "question": "What is the stock of XYZ99999?", "category": "search", "expected_tools": ["get_stock", "search_products"], "notes": "Should NOT hallucinate; must say not found (accepts get_stock or search_products)"},
]

__all__ = ["BENCHMARK_PROMPTS"]
