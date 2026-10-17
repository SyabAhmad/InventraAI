"""Generate realistic dummy e-commerce inventory + sales data."""
from __future__ import annotations

import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

from src.config import DATABASE_PATH
from src.database.connection import get_connection

CATEGORIES = [
    "Electronics", "Clothing", "Home & Kitchen", "Beauty",
    "Sports", "Books", "Toys", "Groceries",
]

ADJECTIVES = ["Premium", "Classic", "Smart", "Ultra", "Pro", "Basic", "Deluxe", "Eco"]
NOUNS = {
    "Electronics": ["Headphones", "Charger", "Smartwatch", "Keyboard", "Mouse", "Speaker", "Webcam"],
    "Clothing": ["T-Shirt", "Jeans", "Jacket", "Sneakers", "Hoodie", "Dress", "Socks"],
    "Home & Kitchen": ["Mug", "Blender", "Pan", "Lamp", "Pillow", "Towel", "Kettle"],
    "Beauty": ["Shampoo", "Lipstick", "Cream", "Perfume", "Serum", "Soap", "Lotion"],
    "Sports": ["Yoga Mat", "Dumbbell", "Bottle", "Racket", "Ball", "Gloves", "Band"],
    "Books": ["Notebook", "Novel", "Planner", "Cookbook", "Dictionary", "Comic", "Guide"],
    "Toys": ["Puzzle", "Doll", "Car", "Blocks", "Drone", "Robot", "Game"],
    "Groceries": ["Coffee", "Tea", "Rice", "Pasta", "Oil", "Cereal", "Snack"],
}

SUPPLIERS = ["Acme Corp", "Globex", "Initech", "Umbrella", "Soylent", "Hooli"]


def _product_name(cat: str, rng: random.Random) -> str:
    adj = rng.choice(ADJECTIVES)
    noun = rng.choice(NOUNS[cat])
    return f"{adj} {noun}"


def seed_database(db_path: str | None = None, n_products: int = 100,
                  days: int = 90, seed: int = 42, reset: bool = False) -> dict:
    path = db_path or DATABASE_PATH
    conn = get_connection(path)
    cur = conn.cursor()

    # Ensure schema
    schema_path = Path(__file__).resolve().parent / "schema.sql" if False else None
    with open(Path(__file__).resolve().parent / "schema.sql", "r", encoding="utf-8") as f:
        cur.executescript(f.read())

    if reset:
        cur.execute("DELETE FROM sales;")
        cur.execute("DELETE FROM reorder_history;")
        cur.execute("DELETE FROM inventory;")
        cur.execute("DELETE FROM products;")
        conn.commit()

    cur.execute("SELECT COUNT(*) FROM products;")
    existing = cur.fetchone()[0]
    if existing > 0:
        conn.close()
        return {"status": "already_seeded", "products": existing}

    rng = random.Random(seed)
    today = date.today()

    # Insert products
    product_rows = []
    for i in range(1, n_products + 1):
        cat = rng.choice(CATEGORIES)
        name = _product_name(cat, rng)
        sku = f"SKU-{i:04d}"
        price = round(rng.uniform(5, 200), 2)
        cost = round(price * rng.uniform(0.4, 0.75), 2)
        min_stock = rng.choice([10, 15, 20, 25, 30, 50])
        supplier = rng.choice(SUPPLIERS)
        product_rows.append((sku, name, cat, price, cost, min_stock, supplier))

    cur.executemany(
        """INSERT INTO products (sku, name, category, price, cost, min_stock_threshold, supplier)
           VALUES (?,?,?,?,?,?,?)""",
        product_rows,
    )
    conn.commit()

    # Get product ids
    cur.execute("SELECT product_id, min_stock_threshold, price FROM products;")
    products = cur.fetchall()

    # Inventory: varied stock, some low / out
    inv_rows = []
    for pid, min_stock, price in products:
        r = rng.random()
        if r < 0.08:
            stock = 0  # out of stock
        elif r < 0.25:
            stock = rng.randint(1, max(1, min_stock - 1))  # low stock
        else:
            stock = rng.randint(min_stock + 5, min_stock * 6)
        inv_rows.append((pid, stock))
    cur.executemany("INSERT INTO inventory (product_id, current_stock) VALUES (?,?)", inv_rows)
    conn.commit()

    # Sales history: 90 days, trend varies per product (fast/slow movers)
    # Assign a demand tier per product
    tier = {}
    for pid, min_stock, price in products:
        tier[pid] = rng.choices(["fast", "medium", "slow"], weights=[0.25, 0.5, 0.25])[0]

    base_daily = {"fast": (3, 8), "medium": (1, 4), "slow": (0, 2)}

    sales_rows = []
    for pid, min_stock, price in products:
        lo, hi = base_daily[tier[pid]]
        # Add trend: some increasing demand
        increasing = rng.random() < 0.3
        for d in range(days, 0, -1):
            day = today - timedelta(days=d)
            # trend factor increases over time for increasing-demand products
            trend = 1.0 + (0.4 * (days - d) / days) if increasing else 1.0
            qty = rng.randint(lo, hi)
            qty = max(0, int(round(qty * trend)))
            if qty == 0 and rng.random() < 0.3:
                continue
            if qty == 0:
                qty = 1
            # occasional bulk order
            if rng.random() < 0.05:
                qty *= rng.randint(2, 4)
            unit_price = round(float(price), 2)
            sales_rows.append((pid, qty, unit_price, day.isoformat(), rng.choice(["web", "mobile", "marketplace"])))

    cur.executemany(
        "INSERT INTO sales (product_id, quantity, unit_price, sale_date, channel) VALUES (?,?,?,?,?)",
        sales_rows,
    )
    conn.commit()

    counts = {
        "products": cur.execute("SELECT COUNT(*) FROM products;").fetchone()[0],
        "inventory": cur.execute("SELECT COUNT(*) FROM inventory;").fetchone()[0],
        "sales": cur.execute("SELECT COUNT(*) FROM sales;").fetchone()[0],
    }
    conn.close()
    return {"status": "seeded", **counts}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true")
    ap.add_argument("--products", type=int, default=100)
    ap.add_argument("--days", type=int, default=90)
    args = ap.parse_args()
    print(seed_database(n_products=args.products, days=args.days, reset=args.reset))