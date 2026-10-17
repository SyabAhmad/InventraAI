"""Initialize (or reset) the SQLite database with seed data."""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import DATABASE_PATH
from src.database.seed_data import seed_database


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="Drop and reseed all data")
    ap.add_argument("--products", type=int, default=100)
    ap.add_argument("--days", type=int, default=90)
    args = ap.parse_args()
    res = seed_database(n_products=args.products, days=args.days, reset=args.reset)
    print(res)
    print("DB path:", DATABASE_PATH)


if __name__ == "__main__":
    main()