import os
import time

import psycopg
from fastapi import FastAPI, HTTPException

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://shop:shop@localhost:5432/shop")
# "atomic" is correct; "naive" has a read-then-write race (oversells under concurrency).
BUY_MODE = os.environ.get("BUY_MODE", "atomic")

app = FastAPI()


def connect():
    return psycopg.connect(DATABASE_URL, autocommit=True)


@app.on_event("startup")
def init_db():
    for _ in range(30):
        try:
            with connect() as conn:
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS products ("
                    "id INT PRIMARY KEY, name TEXT NOT NULL, stock INT NOT NULL)"
                )
                conn.execute(
                    "INSERT INTO products VALUES (1, 'Widget', 10), (2, 'Gadget', 1000) "
                    "ON CONFLICT DO NOTHING"
                )
            return
        except psycopg.OperationalError:
            time.sleep(1)
    raise RuntimeError("database not reachable")


@app.get("/health")
def health():
    return {"status": "ok", "buy_mode": BUY_MODE}


@app.get("/products")
def products():
    with connect() as conn:
        rows = conn.execute("SELECT id, name, stock FROM products ORDER BY id").fetchall()
    return [{"id": r[0], "name": r[1], "stock": r[2]} for r in rows]


@app.post("/buy/{product_id}")
def buy(product_id: int):
    with connect() as conn:
        if BUY_MODE == "naive":
            row = conn.execute("SELECT stock FROM products WHERE id = %s", (product_id,)).fetchone()
            if row is None:
                raise HTTPException(404, "no such product")
            if row[0] <= 0:
                raise HTTPException(409, "sold out")
            time.sleep(0.01)  # widen the race window so the bug shows reliably
            conn.execute("UPDATE products SET stock = %s WHERE id = %s", (row[0] - 1, product_id))
        else:
            cur = conn.execute(
                "UPDATE products SET stock = stock - 1 WHERE id = %s AND stock > 0", (product_id,)
            )
            if cur.rowcount == 0:
                exists = conn.execute("SELECT 1 FROM products WHERE id = %s", (product_id,)).fetchone()
                raise HTTPException(409 if exists else 404, "sold out" if exists else "no such product")
    return {"ok": True}


@app.post("/admin/stock/{product_id}/{stock}")
def set_stock(product_id: int, stock: int):
    """Test helper: reset a product's stock before a scenario."""
    with connect() as conn:
        conn.execute("UPDATE products SET stock = %s WHERE id = %s", (stock, product_id))
    return {"ok": True}
