import sqlite3
import os

DB_PATH = os.environ.get("DB_PATH", "amazon_ledger.db")

SCHEMA = """
DROP TABLE IF EXISTS items;
DROP TABLE IF EXISTS packages;
DROP TABLE IF EXISTS orders;

CREATE TABLE orders (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    order_no     TEXT UNIQUE NOT NULL,
    order_date   TEXT,
    order_total  TEXT,
    type         TEXT,
    created_at   TEXT DEFAULT (datetime('now')),
    updated_at   TEXT DEFAULT (datetime('now'))
);

CREATE TABLE packages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id        INTEGER NOT NULL REFERENCES orders(id),
    shipment_id     TEXT UNIQUE,
    shipment_amount TEXT,
    invoice_name    TEXT
);

CREATE TABLE items (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id     INTEGER NOT NULL REFERENCES orders(id),
    package_id   INTEGER REFERENCES packages(id),
    name         TEXT NOT NULL,
    asin         TEXT,
    qty          INTEGER DEFAULT 1,
    seller       TEXT,
    item_amount  TEXT,
    tax_relevant INTEGER DEFAULT 0,
    tax_tag      INTEGER DEFAULT 0,
    invoice_name TEXT
);
"""


def init_db(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    print(f"Database initialised: {db_path}")


if __name__ == "__main__":
    init_db()
