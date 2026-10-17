"""Tests for the agent wiring (no network required)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent.graph import SYSTEM_PROMPT
from src.tools.agent_tools import AGENT_TOOLS


def test_agent_tools_defined():
    names = [t.name for t in AGENT_TOOLS]
    expected = {
        "get_stock", "list_low_stock", "list_out_of_stock", "inventory_summary",
        "search_products", "sales_summary", "top_sellers", "slow_movers",
        "revenue_by_category", "forecast_demand", "validate_forecast",
        "compare_forecast_methods", "recommend_reorder", "recommend_all_reorders",
        "reorder_summary",
    }
    assert expected.issubset(set(names))


def test_tool_schemas_have_descriptions():
    for t in AGENT_TOOLS:
        assert t.description, f"tool {t.name} missing description"


def test_tools_return_real_data():
    summary = next(t for t in AGENT_TOOLS if t.name == "inventory_summary").invoke({})
    assert summary["total_products"] == 100

    low = next(t for t in AGENT_TOOLS if t.name == "list_low_stock").invoke({})
    assert isinstance(low, list)

    rec = next(t for t in AGENT_TOOLS if t.name == "recommend_reorder").invoke(
        {"product_name_or_sku": "SKU-0001"}
    )
    assert "recommended_reorder_qty" in rec
    assert "urgency" in rec


def test_system_prompt_grounded_rules():
    assert "Never invent" in SYSTEM_PROMPT
    assert "tool" in SYSTEM_PROMPT.lower()