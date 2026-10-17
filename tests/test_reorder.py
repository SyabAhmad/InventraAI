import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.reorder_service import recommend_reorder, recommend_all, reorder_summary


def test_single():
    r = recommend_reorder(1)
    assert "recommended_reorder_qty" in r
    assert r["recommended_reorder_qty"] >= 0
    assert r["urgency"] in {"CRITICAL","HIGH","MEDIUM","LOW"}


def test_all():
    recs = recommend_all(only_needed=True)
    assert isinstance(recs, list)
    for r in recs:
        assert r["should_reorder"] is True


def test_summary():
    s = reorder_summary()
    assert s["total_products"] == 100
    assert s["products_needing_reorder"] >= 0