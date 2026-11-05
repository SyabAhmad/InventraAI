"""Offline unit tests for the Phase-6 benchmark runner (no network)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.benchmark.dataset import BENCHMARK_PROMPTS
from src.benchmark.runner import _aggregate, _estimate_tokens, _percentile, _score_tools


def test_dataset_has_frozen_twenty_prompts():
    assert len(BENCHMARK_PROMPTS) == 20
    ids = [p["id"] for p in BENCHMARK_PROMPTS]
    assert ids == [f"p{i:02d}" for i in range(1, 21)]
    for p in BENCHMARK_PROMPTS:
        assert p["question"] and p["category"] and p["expected_tools"]


def test_score_tools_subset_check():
    assert _score_tools(["get_stock"], ["get_stock"]) is True
    assert _score_tools(["top_sellers", "make_bar_chart"], ["top_sellers", "make_bar_chart"]) is True
    assert _score_tools(["top_sellers", "make_bar_chart"], ["top_sellers"]) is False
    assert _score_tools([], []) is True


def test_token_proxy_is_consistent():
    assert _estimate_tokens("abcd") == 1  # 4 chars -> 1 proxy token
    assert _estimate_tokens("") == 0


def test_percentile_p95():
    vals = list(range(1, 101))  # 1..100, p95 -> ~95.05
    p95 = _percentile([float(v) for v in vals], 95)
    assert 94.0 <= p95 <= 96.0
    assert _percentile([], 95) == 0.0


def test_aggregate_computes_median_p95_and_forecast():
    rows = [
        {"total": 1, "success": True, "tool_accuracy": True, "latency_ms": 100.0, "steps": 2, "tokens_proxy": 50,
         "forecast_metrics": {"mae": 1.0, "mape": 10.0}},
        {"total": 1, "success": False, "tool_accuracy": False, "latency_ms": 300.0, "steps": 4, "tokens_proxy": 70,
         "forecast_metrics": {"mae": 3.0, "mape": 30.0}},
    ]
    agg = _aggregate(rows)
    assert agg["total"] == 2
    assert agg["success_rate"] == 50.0
    assert agg["tool_accuracy"] == 50.0
    assert agg["median_latency_ms"] == 200.0
    assert agg["p95_latency_ms"] > 200.0
    assert agg["forecast_mae"] == 2.0
    assert agg["forecast_mape"] == 20.0
