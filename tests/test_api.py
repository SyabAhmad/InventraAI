"""Tests for the FastAPI backend (no network / LLM required)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from src.api import main as api_main
from src.api.routes import chat as chat_routes

client = TestClient(api_main.app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["database_ready"] is True


def test_dashboard_payload_shape():
    r = client.get("/api/dashboard")
    assert r.status_code == 200
    body = r.json()
    assert body["summary"]["total_products"] == 100
    assert len(body["products"]) == 100
    for key in ("generated_at", "config", "summary", "low_stock", "out_of_stock", "top_sellers"):
        assert key in body
    # secrets never leave the server
    assert "LLM_API_KEY" not in body["config"]


def test_products_have_sales_aggregates():
    r = client.get("/api/products")
    assert r.status_code == 200
    products = r.json()["products"]
    assert len(products) == 100
    assert {"sku", "current_stock", "total_units_sold", "total_revenue"} <= set(products[0])


def test_low_stock_and_out_of_stock():
    low = client.get("/api/low-stock").json()["items"]
    out = client.get("/api/out-of-stock").json()["items"]
    assert isinstance(low, list) and isinstance(out, list)
    for p in low:
        assert p["current_stock"] < p["min_stock_threshold"]
    for p in out:
        assert p["current_stock"] == 0


def test_sales_daily_series_is_contiguous():
    r = client.get("/api/sales/daily?days=30")
    assert r.status_code == 200
    series = r.json()["series"]
    assert len(series) == 30
    assert series == sorted(series, key=lambda x: x["date"])
    assert all({"date", "units", "revenue"} <= set(point) for point in series)


def test_forecast_known_sku():
    r = client.get("/api/forecast/SKU-0001")
    assert r.status_code == 200
    body = r.json()
    assert body["sku"] == "SKU-0001"
    assert len(body["history"]) == 90
    assert len(body["forecast"]) == 7
    assert body["forecast_total"] >= 0


def test_forecast_unknown_sku_returns_404():
    r = client.get("/api/forecast/SKU-9999")
    assert r.status_code == 404


def test_reorder_endpoint():
    r = client.get("/api/reorder?limit=5")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) <= 5
    if items:
        assert {"urgency", "recommended_reorder_qty", "reason"} <= set(items[0])
        assert items[0]["should_reorder"] is True


def test_chat_rejects_empty_message():
    r = client.post("/api/chat", json={"message": ""})
    assert r.status_code == 422


def test_chat_uses_agent_result(monkeypatch):
    monkeypatch.setattr(
        chat_routes,
        "run_question",
        lambda q: {"answer": "There are 100 products.", "tools": ["inventory_summary"], "steps": 4},
    )
    r = client.post("/api/chat", json={"message": "how many products are there?"})
    assert r.status_code == 200
    body = r.json()
    assert body["answer"] == "There are 100 products."
    assert body["tools"] == ["inventory_summary"]
    assert body["steps"] == 4
    assert body["latency_ms"] >= 0


def test_chat_agent_failure_returns_502(monkeypatch):
    def boom(q):
        raise RuntimeError("provider unreachable")

    monkeypatch.setattr(chat_routes, "run_question", boom)
    r = client.post("/api/chat", json={"message": "hello"})
    assert r.status_code == 502
    assert "provider unreachable" in r.json()["detail"]
