"""Tests for chart tools and the chart pipeline (no network required)."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tools.agent_tools import AGENT_TOOLS
from src.tools.chart_tools import (
    tool_make_bar_chart,
    tool_make_line_chart,
    tool_make_pie_chart,
)
from src.tools.sales_tools import tool_daily_sales


def test_new_tools_registered():
    names = {t.name for t in AGENT_TOOLS}
    assert {"daily_sales_data", "make_bar_chart", "make_line_chart", "make_pie_chart"} <= names


def test_daily_sales_data_is_chart_ready():
    series = tool_daily_sales(days=14)
    assert len(series) == 14
    assert all({"date", "units", "revenue"} <= set(p) for p in series)


def test_bar_chart_spec():
    spec = json.loads(tool_make_bar_chart("Top sellers", ["A", "B"], [5, 3], "Units"))
    assert spec["chart_type"] == "bar"
    assert spec["title"] == "Top sellers"
    assert spec["labels"] == ["A", "B"]
    assert spec["values"] == [5.0, 3.0]
    assert spec["value_label"] == "Units"


def test_line_and_pie_specs():
    for fn, kind in ((tool_make_line_chart, "line"), (tool_make_pie_chart, "pie")):
        spec = json.loads(fn("T", ["x", "y", "z"], [1, 2, 3]))
        assert spec["chart_type"] == kind
        assert spec["values"] == [1.0, 2.0, 3.0]


def test_chart_tool_validation_errors():
    assert "error" in json.loads(tool_make_bar_chart("T", ["a"], [1, 2]))          # length mismatch
    assert "error" in json.loads(tool_make_bar_chart("T", [], []))                  # empty
    assert "error" in json.loads(tool_make_bar_chart("T", ["a", "b"], ["x", 2]))    # non-numeric
    too_many = list(range(50))
    assert "error" in json.loads(tool_make_bar_chart("T", [str(i) for i in too_many], too_many))


def test_product_sales_data_is_per_product_and_anchored():
    from src.services.sales_service import latest_sale_date
    from src.tools.sales_tools import tool_product_daily_sales

    res = tool_product_daily_sales("SKU-0010", days=3)
    assert res["sku"] == "SKU-0010"
    assert len(res["days"]) == 3
    assert res["days"][-1]["date"] == latest_sale_date().isoformat()
    assert all({"date", "units"} <= set(day) for day in res["days"])
    assert sum(day["units"] for day in res["days"]) > 0


def test_daily_totals_end_on_latest_data_day():
    from src.services.sales_service import latest_sale_date

    series = tool_daily_sales(days=3)
    assert len(series) == 3
    assert series[-1]["date"] == latest_sale_date().isoformat()
    assert series[-1]["units"] > 0
    assert series[-2]["units"] > 0


def test_product_sales_data_unknown_product():
    from src.tools.sales_tools import tool_product_daily_sales

    res = tool_product_daily_sales("No Such Product", days=3)
    assert "error" in res
