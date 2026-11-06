"""LangGraph ReAct agent for inventory management."""
from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.prebuilt import create_react_agent

from src.agent.llm import get_chat_model
from src.tools.agent_tools import AGENT_TOOLS

CHART_TOOL_NAMES = {"make_bar_chart", "make_line_chart", "make_pie_chart"}
MAX_HISTORY_TURNS = 12

# --- FYP PDF §5: Baseline vs Optimized (paired runs) ---
# BASELINE = existing prompt/context and call pattern (original system prompt).
# OPTIMIZED = shorter relevant context + clearer structure + deterministic
# checks where model calls are unnecessary. Same tools, same data, same
# frozen cases and success rules — only the prompt changes, so the
# comparison is fair (see docs/PHASE6.md).
BASELINE_PROMPT = """You are Arzo, an inventory management assistant for an e-commerce store (InventraAI by Arzo Naveed).

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
   a. First fetch the data with a data tool (product_sales_data for one product's
      daily sales, daily_sales_data for store totals, top_sellers,
      revenue_by_category, forecast_demand, list_low_stock, ...).
   b. Then call make_bar_chart / make_line_chart / make_pie_chart with labels and
      values copied EXACTLY from that data. Never alter or invent numbers.
   c. After the chart tool succeeds, reply with ONE short line only - the chart title.
      No summary, no commentary, no extra numbers: the chart IS the answer.
6. Follow-up questions: earlier turns are included in the conversation. Resolve
   "that product", "the above", "it" to the most recent relevant product or topic
   named in the conversation. Never claim you lack context that is present there.
7. If a tool returns an error (e.g. product not found), say so in one line and suggest
   a close match using search_products.
"""

OPTIMIZED_PROMPT = """You are Arzo, inventory assistant (InventraAI by Arzo Naveed).

RULES (optimized):
- Answer ONLY from tool results. Never invent numbers. Never call the model when a deterministic tool already gives the answer — just use the tool data.
- Call the single tool that matches the question. Do not call extra tools.
- Restock advice: call recommend_reorder, quote its reason/urgency/qty.
- Charts: fetch data first (product_sales_data / daily_sales_data / top_sellers / revenue_by_category / forecast_demand), then make_bar_chart / make_line_chart / make_pie_chart with EXACT values. Reply: chart title only.
- Follow-ups: resolve "that/above/it" from history. Not found: say so in one line, suggest search_products.
- Output: lead with the answer/numbers, ≤6 bullets, top 3-5 items only, no fluff.
"""

# Backwards-compatible alias (chat route / tests / CLI use SYSTEM_PROMPT).
SYSTEM_PROMPT = BASELINE_PROMPT

PROMPT_BY_MODE: dict[str, str] = {
    "baseline": BASELINE_PROMPT,
    "optimized": OPTIMIZED_PROMPT,
}

VALID_MODES = ("baseline", "optimized")


def create_inventory_agent(model_name: str | None = None, mode: str = "baseline"):
    """Create the ReAct agent bound to all inventory/sales/forecast/reorder tools.

    Args:
        model_name: benchmark override (defaults to LLM_MODEL from .env).
        mode: "baseline" (original prompt) or "optimized" (shorter prompt).
              Unknown modes fall back to baseline so old callers keep working.
    """
    prompt = PROMPT_BY_MODE.get(mode, PROMPT_BY_MODE["baseline"])
    return create_react_agent(
        model=get_chat_model(model_name),
        tools=AGENT_TOOLS,
        prompt=prompt,
    )


def _history_messages(history: list[dict] | None) -> list:
    """Convert stored chat turns into LangChain messages (oldest first)."""
    messages: list = []
    for turn in (history or [])[-MAX_HISTORY_TURNS:]:
        role = str(turn.get("role", "user")).lower()
        text = str(turn.get("text", "")).strip()
        if not text:
            continue
        messages.append(AIMessage(content=text) if role in ("agent", "assistant") else HumanMessage(content=text))
    return messages


def ask_agent(agent: Any, question: str, history: list[dict] | None = None, trace: Any = None) -> dict:
    """Run one question through the agent.

    `history` holds earlier turns of the current conversation (oldest first),
    so follow-ups like "chart that product" have context. Returns
    {"answer": str, "steps": int, "tools": list[str], "charts": list[dict]}
    where `tools` lists the tools the agent actually called (in order) and
    `charts` contains chart specs produced by the chart tools (rendered by the
    chat UI). Raises on provider/network errors so callers can surface them
    without faking data.

    `trace` (optional) is a BenchmarkTrace collector; when supplied, real
    LangChain callback events are appended to it.
    """
    from src.agent.tracing import BenchmarkTraceCallback

    messages = _history_messages(history) + [HumanMessage(content=question)]
    config: dict[str, Any] = {"recursion_limit": 25}
    if trace is not None:
        config["callbacks"] = [BenchmarkTraceCallback(trace)]
    if trace is not None:
        trace.emit("request", f"Prompt sent to agent ({len(question)} chars)", question_preview=question[:200])
    result = agent.invoke(
        {"messages": messages},
        config=config,
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

    if trace is not None:
        trace.emit("final", f"Answer ready ({len(answer)} chars)",
                   answer_preview=answer[:300], tools=tool_names, steps=len(messages))

    return {"answer": answer, "steps": len(messages), "tools": tool_names, "charts": charts}
