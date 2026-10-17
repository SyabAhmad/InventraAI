"""LangGraph ReAct agent for inventory management."""
from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent

from src.agent.llm import get_chat_model
from src.tools.agent_tools import AGENT_TOOLS

CHART_TOOL_NAMES = {"make_bar_chart", "make_line_chart", "make_pie_chart"}

SYSTEM_PROMPT = """You are MenteE, an inventory management assistant for an e-commerce store.

Rules:
1. ALWAYS answer from tool results. Never invent stock numbers, prices, or forecasts.
2. Use the tool that matches the question (stock lookup, low stock, sales, forecast, reorder).
3. When asked for advice (e.g. "should I restock X?"), call recommend_reorder and explain
   its reason field using the real data it returned.
4. Be SHORT and to the point - this matters:
   - Lead with the direct answer or key number(s). No preamble, never restate the question.
   - Keep a normal answer to a few short lines or at most ~6 bullets.
   - NEVER dump full lists. Summarize: give the total count and only the 3-5 most
     important items (most urgent, biggest seller, etc.).
   - No closing fluff, no "let me know if...", no extra background sections.
   - Only expand beyond this when the user explicitly asks for the full list or details.
5. Charts - when the user asks for a chart, graph, or plot:
   a. First fetch the data with a data tool (daily_sales_data, top_sellers,
      revenue_by_category, forecast_demand, list_low_stock, ...).
   b. Then call make_bar_chart / make_line_chart / make_pie_chart with labels and
      values copied EXACTLY from that data. Never alter or invent numbers.
   c. After the chart tool succeeds, reply with ONE short line only - the chart title.
      No summary, no commentary, no extra numbers: the chart IS the answer.
6. If a tool returns an error (e.g. product not found), say so in one line and suggest
   a close match using search_products.
"""


def create_inventory_agent():
    """Create the ReAct agent bound to all inventory/sales/forecast/reorder tools."""
    return create_react_agent(
        model=get_chat_model(),
        tools=AGENT_TOOLS,
        prompt=SYSTEM_PROMPT,
    )


def ask_agent(agent: Any, question: str) -> dict:
    """Run one question through the agent.

    Returns {"answer": str, "steps": int, "tools": list[str], "charts": list[dict]}
    where `tools` lists the tools the agent actually called (in order) and
    `charts` contains chart specs produced by the chart tools (rendered by the
    chat UI). Raises on provider/network errors so callers can surface them
    without faking data.
    """
    result = agent.invoke(
        {"messages": [HumanMessage(content=question)]},
        config={"recursion_limit": 25},
    )
    messages = result.get("messages", [])
    answer = messages[-1].content if messages else ""

    tool_names: list[str] = []
    charts: list[dict] = []
    for m in messages:
        for call in getattr(m, "tool_calls", None) or []:
            name = call.get("name") if isinstance(call, dict) else getattr(call, "name", None)
            if name:
                tool_names.append(name)
        # collect chart specs from chart-tool results
        if getattr(m, "name", None) in CHART_TOOL_NAMES:
            content = getattr(m, "content", None)
            if isinstance(content, str):
                try:
                    spec = json.loads(content)
                    if isinstance(spec, dict) and "chart_type" in spec:
                        charts.append(spec)
                except (ValueError, TypeError):
                    pass

    return {"answer": answer, "steps": len(messages), "tools": tool_names, "charts": charts}
