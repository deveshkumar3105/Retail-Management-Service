import sqlite3
from contextlib import contextmanager
from pathlib import Path
from .config import DATABASE_PATH

class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc, tb):
        try: return super().__exit__(exc_type, exc, tb)
        finally: self.close()

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS customers (
 customer_id TEXT PRIMARY KEY CHECK(length(customer_id) BETWEEN 1 AND 80),
 first_name TEXT NOT NULL CHECK(length(first_name) BETWEEN 1 AND 80),
 last_name TEXT NOT NULL CHECK(length(last_name) BETWEEN 1 AND 80),
 email TEXT NOT NULL COLLATE NOCASE UNIQUE CHECK(length(email) <= 254),
 phone TEXT CHECK(phone IS NULL OR length(phone) <= 32),
 city TEXT NOT NULL CHECK(length(city) BETWEEN 1 AND 100),
 state TEXT NOT NULL CHECK(length(state) BETWEEN 1 AND 100),
 postal_code TEXT NOT NULL CHECK(length(postal_code) BETWEEN 1 AND 20),
 country TEXT NOT NULL CHECK(length(country) = 2),
 customer_status TEXT NOT NULL CHECK(customer_status IN ('ACTIVE','INACTIVE')),
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL,
 source_version INTEGER NOT NULL CHECK(source_version >= 1),
 change_seq INTEGER NOT NULL CHECK(change_seq >= 1)
);
CREATE INDEX IF NOT EXISTS idx_customers_updated ON customers(updated_at, customer_id);
CREATE INDEX IF NOT EXISTS idx_customers_status ON customers(customer_status, customer_id);
CREATE TABLE IF NOT EXISTS customer_changes (
 change_seq INTEGER PRIMARY KEY AUTOINCREMENT,
 customer_id TEXT NOT NULL,
 operation TEXT NOT NULL CHECK(operation IN ('INSERT','UPDATE')),
 changed_at TEXT NOT NULL,
 source_version INTEGER NOT NULL,
 snapshot_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_customer_changes_customer ON customer_changes(customer_id, change_seq);
CREATE INDEX IF NOT EXISTS idx_customer_changes_timestamp ON customer_changes(changed_at, change_seq);
"""
def connect(path: Path | None = None):
    db_path=path or DATABASE_PATH
    db_path.parent.mkdir(parents=True,exist_ok=True)
    conn=sqlite3.connect(db_path,timeout=10,factory=ClosingConnection)
    conn.row_factory=sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    return conn

def init_db(path: Path | None = None):
    with connect(path) as conn: conn.executescript(SCHEMA)

@contextmanager
def transaction(path: Path | None = None):
    conn=connect(path)
    try:
        conn.execute('BEGIN IMMEDIATE')
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally: conn.close()
