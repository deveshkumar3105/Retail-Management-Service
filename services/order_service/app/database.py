import sqlite3
from contextlib import contextmanager
from pathlib import Path
from .config import DATABASE_PATH

class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc, tb):
        try:
            return super().__exit__(exc_type, exc, tb)
        finally:
            self.close()

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS orders (
 order_id TEXT PRIMARY KEY,
 customer_id TEXT NOT NULL,
 order_status TEXT NOT NULL CHECK(order_status IN ('CREATED','CONFIRMED','SHIPPED','DELIVERED','CANCELLED')),
 order_timestamp TEXT NOT NULL,
 currency TEXT NOT NULL CHECK(length(currency)=3),
 order_total_cents INTEGER NOT NULL CHECK(order_total_cents >= 0),
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL,
 source_version INTEGER NOT NULL CHECK(source_version >= 1)
);
CREATE INDEX IF NOT EXISTS idx_orders_updated ON orders(updated_at, order_id);
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
CREATE TABLE IF NOT EXISTS order_items (
 order_item_id TEXT PRIMARY KEY,
 order_id TEXT NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
 product_id TEXT NOT NULL,
 quantity INTEGER NOT NULL CHECK(quantity > 0),
 unit_price_cents INTEGER NOT NULL CHECK(unit_price_cents >= 0),
 discount_amount_cents INTEGER NOT NULL CHECK(discount_amount_cents >= 0),
 line_total_cents INTEGER NOT NULL CHECK(line_total_cents >= 0)
);
CREATE INDEX IF NOT EXISTS idx_items_order ON order_items(order_id, order_item_id);
"""

def connect(path: Path | None = None):
    db_path = path or DATABASE_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=10, factory=ClosingConnection)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db(path: Path | None = None):
    with connect(path) as conn:
        conn.executescript(SCHEMA)

@contextmanager
def transaction(path: Path | None = None):
    conn = connect(path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
