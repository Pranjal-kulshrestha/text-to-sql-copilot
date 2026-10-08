"""Create a sample e-commerce SQLite database: python -m copilot.seed data/shop.db"""

import random
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

CITIES = ["Bengaluru", "Mumbai", "Delhi", "Pune", "Hyderabad", "Chennai"]
CATEGORIES = {"Electronics": (2000, 60000), "Books": (200, 1500), "Fashion": (500, 5000), "Home": (300, 12000)}


def seed(path: str, seed_value: int = 7) -> None:
    rng = random.Random(seed_value)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).unlink(missing_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT, city TEXT, signup_date TEXT);
        CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT, category TEXT, price REAL);
        CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER REFERENCES customers(id),
                             order_date TEXT, status TEXT);
        CREATE TABLE order_items (order_id INTEGER REFERENCES orders(id),
                                  product_id INTEGER REFERENCES products(id), quantity INTEGER);
        """
    )
    start = date(2025, 1, 1)
    conn.executemany(
        "INSERT INTO customers VALUES (?,?,?,?)",
        [(i, f"Customer {i}", rng.choice(CITIES), str(start + timedelta(days=rng.randint(0, 300))))
         for i in range(1, 201)],
    )
    products = []
    for i in range(1, 41):
        cat = rng.choice(list(CATEGORIES))
        lo, hi = CATEGORIES[cat]
        products.append((i, f"{cat} item {i}", cat, round(rng.uniform(lo, hi), 2)))
    conn.executemany("INSERT INTO products VALUES (?,?,?,?)", products)

    orders, items = [], []
    for oid in range(1, 1501):
        orders.append((oid, rng.randint(1, 200), str(start + timedelta(days=rng.randint(0, 600))),
                       rng.choices(["delivered", "shipped", "cancelled"], [80, 12, 8])[0]))
        for _ in range(rng.randint(1, 3)):
            items.append((oid, rng.randint(1, 40), rng.randint(1, 4)))
    conn.executemany("INSERT INTO orders VALUES (?,?,?,?)", orders)
    conn.executemany("INSERT INTO order_items VALUES (?,?,?)", items)
    conn.commit()
    conn.close()


if __name__ == "__main__":
    seed(sys.argv[1] if len(sys.argv) > 1 else "data/shop.db")
