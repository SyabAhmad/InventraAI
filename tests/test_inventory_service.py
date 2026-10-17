import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.inventory_service import (
    get_all_products, get_product, get_stock, list_low_stock,
    list_out_of_stock, inventory_summary, update_stock, adjust_stock,
)


def test_counts():
    products = get_all_products()
    assert len(products) == 100
    s = inventory_summary()
    assert s["total_products"] == 100
    assert s["low_stock_count"] >= 0


def test_low_stock_subset():
    low = list_low_stock()
    for p in low:
        assert p["current_stock"] < p["min_stock_threshold"]


def test_get_stock():
    p = get_all_products()[0]
    st = get_stock(p["product_id"])
    assert st["product_id"] == p["product_id"]
    assert st["current_stock"] == p["current_stock"]


def test_update_and_adjust():
    p = get_all_products()[0]
    orig = p["current_stock"]
    update_stock(p["product_id"], orig + 5)
    assert get_stock(p["product_id"])["current_stock"] == orig + 5
    adjust_stock(p["product_id"], -5)
    assert get_stock(p["product_id"])["current_stock"] == orig
    # restore
    update_stock(p["product_id"], orig)


def test_out_of_stock():
    out = list_out_of_stock()
    for p in out:
        assert p["current_stock"] == 0