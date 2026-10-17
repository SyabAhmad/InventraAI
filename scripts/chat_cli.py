"""Terminal chat for the inventory agent (LangGraph ReAct tool loop).

The agent decides which tools to call (stock, low stock, sales, forecasts,
reorder) and answers strictly from the data those tools return.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent.graph import ask_agent, create_inventory_agent


def main() -> None:
    print("InventraAI agent chat - type 'exit' to quit.\n")

    agent = create_inventory_agent()
    print("[agent ready]\n")

    while True:
        try:
            question = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break
        if not question:
            continue
        if question.lower() in {"exit", "quit"}:
            print("Bye!")
            break

        try:
            result = ask_agent(agent, question)
            print(f"\nAgent: {result['answer']}")
        except Exception as e:
            print(f"\n[agent error] {e}")


if __name__ == "__main__":
    main()