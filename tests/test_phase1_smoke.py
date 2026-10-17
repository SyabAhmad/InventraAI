import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_config_loads():
    from src import config
    assert config.OLLAMA_MODEL
    assert config.DATABASE_PATH
    assert config.DEFAULT_MIN_STOCK > 0


def test_schema_init_and_seed():
    db = os.path.join(tempfile.gettempdir(), "smoke_phase1.db")
    if os.path.exists(db):
        os.remove(db)
    from src.database.seed_data import seed_database
    res = seed_database(db_path=db, n_products=5, days=10, reset=True)
    assert res["status"] == "seeded"
    assert res["products"] == 5
    assert res["sales"] >= 0
    # idempotent
    res2 = seed_database(db_path=db, n_products=5, days=10, reset=False)
    assert res2["status"] == "already_seeded"
    os.remove(db)