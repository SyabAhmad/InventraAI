"""Chart-building tools for the agent.

Workflow: the agent fetches numbers with a data tool (daily_sales_data,
top_sellers, revenue_by_category, forecast_demand, ...) and then passes
labels/values to one of these tools. The tool only validates and formats -
it never computes or alters numbers - and returns a chart specification
that the chat UI renders as a real chart.
"""
from __future__ import annotations

import json

MAX_POINTS = 40


def _build_spec(chart_type: str, title: str, labels: list, values: list, value_label: str) -> str:
    if not labels or not values:
        return json.dumps({"error": "labels and values must not be empty."})
    if len(labels) != len(values):
        return json.dumps(
            {"error": f"labels and values must have the same length (got {len(labels)} labels and {len(values)} values)."}
        )
    if len(labels) > MAX_POINTS:
        return json.dumps(
            {"error": f"too many points ({len(labels)}); send at most {MAX_POINTS}. Aggregate or take the top items."}
        )
    clean_values: list[float] = []
    for v in values:
        try:
            clean_values.append(round(float(v), 2))
        except (TypeError, ValueError):
            return json.dumps({"error": f"value '{v}' is not numeric."})
    spec = {
        "chart_type": chart_type,
        "title": str(title).strip() or "Chart",
        "value_label": str(value_label).strip() or "Value",
        "labels": [str(x) for x in labels],
        "values": clean_values,
    }
    return json.dumps(spec, ensure_ascii=False)


def tool_make_bar_chart(title: str, labels: list, values: list, value_label: str = "Value") -> str:
    """Validate and format a bar-chart specification."""
    return _build_spec("bar", title, labels, values, value_label)


def tool_make_line_chart(title: str, labels: list, values: list, value_label: str = "Value") -> str:
    """Validate and format a line-chart specification."""
    return _build_spec("line", title, labels, values, value_label)


def tool_make_pie_chart(title: str, labels: list, values: list, value_label: str = "Value") -> str:
    """Validate and format a pie-chart specification."""
    return _build_spec("pie", title, labels, values, value_label)
