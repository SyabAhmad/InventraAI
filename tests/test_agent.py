"""Tests for the agent wiring (no network required)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.messages import AIMessage, HumanMessage

from src.agent.graph import SYSTEM_PROMPT, ask_agent
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
    assert "MenteE" in SYSTEM_PROMPT
    assert "product_sales_data" in SYSTEM_PROMPT


class _FakeAgent:
    def __init__(self):
        self.seen = None

    def invoke(self, payload, config=None):
        self.seen = payload["messages"]
        return {"messages": payload["messages"] + [AIMessage(content="ok")]}


def test_ask_agent_includes_history_for_follow_ups():
    agent = _FakeAgent()
    out = ask_agent(
        agent,
        "chart the above book",
        history=[
            {"role": "user", "text": "which book sells most?"},
            {"role": "agent", "text": "Ultra Comic is the top-selling book."},
        ],
    )
    assert isinstance(agent.seen[0], HumanMessage)
    assert isinstance(agent.seen[1], AIMessage)
    assert agent.seen[-1].content == "chart the above book"
    assert out["answer"] == "ok"


def test_ask_agent_limits_history_and_skips_empty_turns():
    agent = _FakeAgent()
    history = [{"role": "user", "text": f"turn {i}"} for i in range(30)]
    history.insert(1, {"role": "user", "text": "   "})
    ask_agent(agent, "last question", history=history)
    assert len(agent.seen) == 13  # 12 history turns + the question
    assert agent.seen[-1].content == "last question"