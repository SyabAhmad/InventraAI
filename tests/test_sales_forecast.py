import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.sales_service import sales_summary, top_sellers, slow_movers, daily_series
from src.services.forecast_service import forecast_demand, validate_forecast, compare_methods


def test_sales_summary():
    s = sales_summary()
    assert s["total_units"] > 0
    assert s["total_orders"] > 0


def test_top_sellers():
    ts = top_sellers(n=5)
    assert len(ts) == 5
    assert ts[0]["total_units"] >= ts[-1]["total_units"]


def test_slow_movers():
    sm = slow_movers(n=5)
    assert len(sm) == 5


def test_forecast():
    f = forecast_demand(1, horizon=7, method="moving_average")
    assert len(f["forecast"]) == 7
    assert f["total_predicted"] >= 0


def test_validate():
    v = validate_forecast(1, method="linear_trend")
    if "error" not in v:
        assert "mae" in v["metrics"]
        assert "mape" in v["metrics"]


def test_compare():
    c = compare_methods(1)
    assert isinstance(c, list)