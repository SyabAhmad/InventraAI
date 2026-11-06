"""Benchmark prompt suites.

Suite v1 (legacy):
  Twenty simple route-selection prompts (p01..p20). Kept unchanged so older
  benchmark files remain comparable.

Suite v2 (complex, active):
  Twenty multi-step inventory-decision prompts (c01..c20). These require the
  agent to combine evidence, compare conflicting signals, recommend an action,
  and respect guardrails (do not invent missing data).

Schema:
  id             unique stable case ID
  question       exact prompt sent to the agent
  category       inventory / forecast / reorder / sales / chart / guardrail
  expected_tools all listed tools MUST be called, any order
  expected_any   optional list of groups; each group must have ≥1 tool called
  notes          what a good answer must mention (for manual viva audit)
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
    {"id": "p20", "question": "What is the stock of XYZ99999?", "category": "search", "expected_tools": ["get_stock"], "expected_any": [["get_stock", "search_products"]], "notes": "Should NOT hallucinate; must say not found (get_stock or search_products)"},
]

BENCHMARK_PROMPTS_V2: list[dict] = [
    {
        "id": "c01",
        "question": "Run an inventory-reset review. Give me overall inventory health, the 3 most important replenishment actions, and the sales evidence supporting those actions. Finish with a prioritized next-step plan.",
        "category": "cross_functional",
        "expected_tools": ["inventory_summary", "recommend_all_reorders", "sales_summary"],
        "notes": "Must combine stock health + replenishment urgency + all-time sales evidence; do not give isolated counts.",
    },
    {
        "id": "c02",
        "question": "Low stock review: identify the below-minimum items, group them by replenishment urgency, return the top 5 actions with quantities, and flag anything you cannot conclude from the data.",
        "category": "reorder",
        "expected_tools": ["list_low_stock", "recommend_all_reorders", "reorder_summary"],
        "notes": "Must not list everything; rank top actions and mention uncertainty/limits.",
    },
    {
        "id": "c03",
        "question": "Dead-stock audit: inspect slow movers and all-time sales results, then classify which slow movers need markdown/bundling/monitor actions and why.",
        "category": "sales",
        "expected_tools": ["slow_movers", "sales_summary"],
        "notes": "Must combine slow sales evidence with overall sales context, not just restate list.",
    },
    {
        "id": "c04",
        "question": "Find cross-category mismatch risk: revenue by category and inventory health. Identify which categories look commercially important but may need replenishment focus, and give one action per priority category.",
        "category": "cross_functional",
        "expected_tools": ["revenue_by_category", "inventory_summary"],
        "notes": "Must connect category revenue with inventory actions; no invented demand.",
    },
    {
        "id": "c05",
        "question": "Which below-minimum products are also likely top sellers? Cross-check low-stock and top-seller evidence, prioritise the overlap as lost-sales risk, and explain the ranking.",
        "category": "inventory",
        "expected_tools": ["list_low_stock", "top_sellers"],
        "notes": "Must identify overlap / explain uncertainty instead of pretending exact join if fuzzy.",
    },
    {
        "id": "c06",
        "question": "Out-of-stock emergency: identify zero-stock products, cross-check them against top sellers, and produce a rescue order with recommended reorder priority and reason.",
        "category": "reorder",
        "expected_tools": ["list_out_of_stock", "top_sellers", "recommend_all_reorders"],
        "notes": "Must call all three; should distinguish known out-of-stock from top seller ranking.",
    },
    {
        "id": "c07",
        "question": "Decide whether to reorder SKU-0001. Before recommending, report current stock, 7-day forecast, validation MAE/MAPE, and the reorder recommendation with urgency.",
        "category": "reorder",
        "expected_tools": ["get_stock", "forecast_demand", "validate_forecast", "recommend_reorder"],
        "notes": "Must answer with all four evidence points; no invented values.",
    },
    {
        "id": "c08",
        "question": "Choose the best forecast method for SKU-0001. Compare moving average, exponential smoothing and linear trend, inspect validation errors, and state which method to use plus why.",
        "category": "forecast",
        "expected_tools": ["compare_forecast_methods", "validate_forecast", "forecast_demand"],
        "notes": "Must explicitly compare methods and select one using error metrics.",
    },
    {
        "id": "c09",
        "question": "Create a 30-day revenue chart for the store and give a 3-line readout: trend, highest-risk anomaly, and one management action.",
        "category": "chart",
        "expected_tools": ["daily_sales_data", "sales_summary", "make_line_chart"],
        "notes": "Must chart actual daily series and explain trend/risk using returned numbers.",
    },
    {
        "id": "c10",
        "question": "Create a product-level demand chart for SKU-0001 using daily sales, then overlay the forecast recommendation in your explanation.",
        "category": "chart",
        "expected_tools": ["product_sales_data", "forecast_demand", "make_line_chart"],
        "notes": "Must use SKU-0001 data and forecast; chart should contain actual evidence.",
    },
    {
        "id": "c11",
        "question": "Build a category revenue concentration chart, then explain whether the company depends too heavily on a few categories and what purchasing action to take next.",
        "category": "chart",
        "expected_tools": ["revenue_by_category", "make_pie_chart"],
        "notes": "Must call chart tool; interpretation must discuss concentration, not just labels.",
    },
    {
        "id": "c12",
        "question": "Build a bar chart of the top sellers and assess whether sales are overly dependent on them. Include overall sales context in the recommendation.",
        "category": "chart",
        "expected_tools": ["top_sellers", "sales_summary", "make_bar_chart"],
        "notes": "Must combine total sales with top-seller list, not chart blindly.",
    },
    {
        "id": "c13",
        "question": "Inventory evidence request: give me stock for SKU-0001, a 7-day demand forecast, and a reorder recommendation. If any evidence is missing, say so instead of filling the gap.",
        "category": "reorder",
        "expected_tools": ["get_stock", "forecast_demand", "recommend_reorder"],
        "notes": "Must be complete but explicit about missing evidence; no hallucination.",
    },
    {
        "id": "c14",
        "question": "Inventory health audit focused on overstock: inspect all-time sales, slow movers, and inventory summary. Recommend whether to reduce purchasing, discount, or hold stock.",
        "category": "cross_functional",
        "expected_tools": ["sales_summary", "slow_movers", "inventory_summary"],
        "notes": "Must integrate three data sources and make one recommendation.",
    },
    {
        "id": "c15",
        "question": "Books category buying review: search Books, cross-check top sellers and slow movers, and recommend where to allocate inventory budget.",
        "category": "category",
        "expected_tools": ["search_products", "top_sellers", "slow_movers"],
        "notes": "Must not claim exact Books ranking if top sellers are not category-filtered; state limitation.",
    },
    {
        "id": "c16",
        "question": "Which low-stock item is the most important single lost-sales risk right now? Cross-check low-stock, out-of-stock and top sellers, then justify one priority.",
        "category": "inventory",
        "expected_tools": ["list_low_stock", "list_out_of_stock", "top_sellers"],
        "notes": "Must choose one priority and explain why; can say which evidence is missing/uncertain.",
    },
    {
        "id": "c17",
        "question": "Reorder approval for SKU-0001, SKU-0002 and SKU-0003: fetch current stock and reorder recommendation for each, then rank the three by urgency and total recommended quantity.",
        "category": "reorder",
        "expected_tools": ["get_stock", "recommend_reorder"],
        "notes": "Must repeat tools for three products and produce ranked approval order.",
    },
    {
        "id": "c18",
        "question": "Morning operating report: give me overall sales, inventory health, reorder pressure and a 7-day outlook trend. Keep it to a 5-bullet board summary.",
        "category": "cross_functional",
        "expected_tools": ["sales_summary", "inventory_summary", "reorder_summary", "daily_sales_data"],
        "notes": "Must combine 4 sources; board-style output, not nested detail.",
    },
    {
        "id": "c19",
        "question": "Forecast procurement scenario for SKU-0001: report 7-day forecast, validate accuracy, list the top reorder recommendation, and state whether the evidence is strong enough to approve replenishment.",
        "category": "forecast",
        "expected_tools": ["forecast_demand", "validate_forecast", "recommend_reorder"],
        "notes": "Must give a clear approve/hold recommendation based on forecast quality.",
    },
    {
        "id": "c20",
        "question": "Research request for XYZ99999: locate the product in the catalogue if possible, verify exact stock or lack of it, and never invent a forecast or price. If it is absent, reply with exact wording 'XYZ99999 not found'.",
        "category": "guardrail",
        "expected_tools": [],
        "expected_any": [["search_products", "get_stock"]],
        "notes": "Must refuse hallucination; exact phrase when absent.",
    },
]

BENCHMARK_SUITES = {
    "v1": {
        "name": "v1 — Basic router (legacy)",
        "description": "20 simple one-tool prompts; useful for regression compares.",
        "prompts": BENCHMARK_PROMPTS,
    },
    "v2": {
        "name": "v2 — Complex inventory decisions",
        "description": "20 multi-step prompts combining evidence, recommendation and guardrails.",
        "prompts": BENCHMARK_PROMPTS_V2,
    },
}

# Active suite (UI default). v2 is the serious benchmark now.
DEFAULT_SUITE = "v2"

# Backwards-compatible alias used by the UI / older CLI code.
BENCHMARK_PROMPTS_ACTIVE = BENCHMARK_SUITES[DEFAULT_SUITE]["prompts"]

__all__ = [
    "BENCHMARK_PROMPTS",
    "BENCHMARK_PROMPTS_V2",
    "BENCHMARK_SUITES",
    "DEFAULT_SUITE",
    "BENCHMARK_PROMPTS_ACTIVE",
]
