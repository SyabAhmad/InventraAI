"""Demand forecasting for products based on historical sales."""
from __future__ import annotations

import math
from datetime import date, timedelta

import numpy as np
import pandas as pd

from src.config import FORECAST_HORIZON_DAYS, FORECAST_VALIDATION_DAYS
from src.services.sales_service import daily_series


def _mae(actual, pred) -> float:
    actual = np.asarray(actual, dtype=float)
    pred = np.asarray(pred, dtype=float)
    if len(actual) == 0:
        return 0.0
    return float(np.mean(np.abs(actual - pred)))


def _mape(actual, pred) -> float:
    actual = np.asarray(actual, dtype=float)
    pred = np.asarray(pred, dtype=float)
    mask = actual != 0
    if mask.sum() == 0:
        return 0.0
    return float(np.mean(np.abs((actual[mask] - pred[mask]) / actual[mask])) * 100.0)


def _rmse(actual, pred) -> float:
    actual = np.asarray(actual, dtype=float)
    pred = np.asarray(pred, dtype=float)
    if len(actual) == 0:
        return 0.0
    return float(np.sqrt(np.mean((actual - pred) ** 2)))


def forecast_moving_average(series: pd.Series, horizon: int, window: int = 7) -> np.ndarray:
    vals = series.values.astype(float)
    window = min(window, len(vals)) if len(vals) > 0 else 1
    if window < 1:
        window = 1
    last = vals[-window:] if len(vals) >= window else vals
    base = float(np.mean(last)) if len(last) else 0.0
    return np.array([max(0.0, base)] * horizon)


def forecast_exponential_smoothing(series: pd.Series, horizon: int, alpha: float = 0.3) -> np.ndarray:
    vals = series.values.astype(float)
    if len(vals) == 0:
        return np.array([0.0] * horizon)
    level = vals[0]
    for v in vals[1:]:
        level = alpha * v + (1 - alpha) * level
    return np.array([max(0.0, level)] * horizon)


def forecast_linear_trend(series: pd.Series, horizon: int) -> np.ndarray:
    vals = series.values.astype(float)
    n = len(vals)
    if n < 2:
        base = float(vals[-1]) if n else 0.0
        return np.array([max(0.0, base)] * horizon)
    x = np.arange(n)
    coef = np.polyfit(x, vals, 1)
    future_x = np.arange(n, n + horizon)
    pred = np.polyval(coef, future_x)
    return np.array([max(0.0, float(p)) for p in pred])


METHODS = {
    "moving_average": forecast_moving_average,
    "exponential_smoothing": forecast_exponential_smoothing,
    "linear_trend": forecast_linear_trend,
}


def forecast_demand(product_id: int, horizon: int | None = None,
                   method: str | None = None, days: int = 90) -> dict:
    horizon = horizon or FORECAST_HORIZON_DAYS
    method = method or "moving_average"
    series = daily_series(product_id, days=days)
    fn = METHODS.get(method, forecast_moving_average)
    if method == "moving_average":
        pred = fn(series, horizon, window=7)
    elif method == "exponential_smoothing":
        pred = fn(series, horizon, alpha=0.3)
    else:
        pred = fn(series, horizon)
    # round to integers
    pred_int = [int(round(float(p))) for p in pred]
    future_dates = [(date.today() + timedelta(days=i + 1)).isoformat() for i in range(horizon)]
    return {
        "product_id": product_id,
        "method": method,
        "horizon_days": horizon,
        "forecast": [{"date": d, "predicted_qty": q} for d, q in zip(future_dates, pred_int)],
        "total_predicted": int(sum(pred_int)),
        "avg_daily_predicted": round(float(np.mean(pred)), 2) if len(pred) else 0.0,
    }


def validate_forecast(product_id: int, method: str = "moving_average",
                     validation_days: int | None = None, horizon: int | None = None) -> dict:
    """Hold out the last `validation_days` days and evaluate forecast accuracy."""
    validation_days = validation_days or FORECAST_VALIDATION_DAYS
    horizon = horizon or 7
    series = daily_series(product_id, days=90)
    if len(series) <= validation_days + 7:
        return {"error": "Not enough history for validation."}
    train = series.iloc[:-validation_days]
    test = series.iloc[-validation_days:]
    # Forecast validation_days ahead from train
    fn = METHODS.get(method, forecast_moving_average)
    if method == "moving_average":
        pred = fn(train, validation_days, window=7)
    elif method == "exponential_smoothing":
        pred = fn(train, validation_days, alpha=0.3)
    else:
        pred = fn(train, validation_days)
    actual = test.values.astype(float)
    metrics = {
        "mae": round(_mae(actual, pred), 3),
        "mape": round(_mape(actual, pred), 3),
        "rmse": round(_rmse(actual, pred), 3),
    }
    return {
        "product_id": product_id,
        "method": method,
        "validation_days": validation_days,
        "metrics": metrics,
        "actual_total": int(actual.sum()),
        "predicted_total": int(round(float(pred.sum()))),
    }


def compare_methods(product_id: int, validation_days: int | None = None) -> list[dict]:
    out = []
    for m in METHODS:
        r = validate_forecast(product_id, method=m, validation_days=validation_days)
        if "error" not in r:
            out.append({"method": m, **r["metrics"]})
    return sorted(out, key=lambda x: x["mae"])