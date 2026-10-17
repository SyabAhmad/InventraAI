"""LangGraph ReAct agent for inventory management."""
from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

from src.agent.llm import get_chat_model
from src.tools.agent_tools import AGENT_TOOLS

SYSTEM_PROMPT = """You are InventraAI, an inventory management assistant for an e-commerce store.

Rules:
1. ALWAYS answer from tool results. Never invent stock numbers, prices, or forecasts.
2. Use the tool that matches the question (stock lookup, low stock, sales, forecast, reorder).
3. When asked for advice (e.g. "should I restock X?"), call recommend_reorder and explain
   its reason field using the real data it returned.
4. Be concise: answer the question, show the key numbers, note urgency when relevant.
5. If a tool returns an error (e.g. product not found), say so and suggest a close match
   using search_products.
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

    Returns {"answer": str, "steps": int}. Raises on provider/network errors
    so callers can apply their own fallback.
    """
    result = agent.invoke(
        {"messages": [HumanMessage(content=question)]},
        config={"recursion_limit": 25},
    )
    messages = result.get("messages", [])
    answer = messages[-1].content if messages else ""
    return {"answer": answer, "steps": len(messages)}
