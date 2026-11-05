"""Standalone Clef decision check (via /v1/systemone, not chat).

Usage:
  python scripts/check_clef.py

Clef validates the /v1/systemone endpoint works before you try any
benchmark that involves it. The chat benchmark (run_benchmark.py) does
NOT use Clef — Clef is decision-only (route / policy / moderate).
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.benchmark.clef import run_clef_decision


def main() -> None:
    state = "SKU-0001 has 0 units in stock. Minimum threshold is 50. Lead time is 7 days."
    questions = {
        "need_reorder": {
            "type": "noul",
            "instructions": "Decide if the product needs reordering.",
            "criteria": {"true": "Stock is below minimum, reorder is needed.", "false": "Stock is fine."},
        }
    }
    print("Calling Clef decision API (state + 1 question)...\n")
    try:
        out = run_clef_decision(state, questions)
        print(json.dumps(out, indent=2))
    except Exception as exc:  # noqa: BLE001
        print(f"Clef check failed: {exc}")
        print("Check: CLEF_MODEL in .env, LLM_API_KEY for cloud, ollama pull clef:27b for local.")


if __name__ == "__main__":
    main()
