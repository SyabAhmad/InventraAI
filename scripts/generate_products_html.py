"""Generate frontend/js/data.js (offline snapshot) from the SQLite database.

The live dashboard is served by the FastAPI backend (`uvicorn src.api.main:app`),
which builds the same payload from `src.services.dashboard_service`. This script
keeps the double-click-friendly snapshot in sync for offline use.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.dashboard_service import build_dashboard_payload


def main() -> None:
    data = build_dashboard_payload()
    out_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "frontend", "js", "data.js",
    )
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("window.PRODUCTS_DATA = " + json.dumps(data) + ";\n")
    print("Generated:", out_path)
    print(
        "Products:", len(data["products"]),
        "| Low stock:", data["summary"]["low_stock_count"],
        "| Out of stock:", data["summary"]["out_of_stock_count"],
    )


if __name__ == "__main__":
    main()
