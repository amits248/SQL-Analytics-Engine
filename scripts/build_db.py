"""
Builds db/retail.db from the CSVs in data/raw/ using the schema in sql/01_schema.sql.
Indexes (sql/02_indexes.sql) are applied separately by run_analysis.py so the
before/after query-optimization benchmark has something real to measure.
"""
import sqlite3
import csv
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT, "db", "retail.db")
RAW = os.path.join(ROOT, "data", "raw")


def load_csv(conn, table, path):
    with open(path) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    if not rows:
        return
    cols = list(rows[0].keys())
    placeholders = ",".join(["?"] * len(cols))
    sql = f"INSERT INTO {table} ({','.join(cols)}) VALUES ({placeholders})"
    conn.executemany(sql, [[r[c] for c in cols] for r in rows])


def main():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = sqlite3.connect(DB_PATH)

    with open(os.path.join(ROOT, "sql", "01_schema.sql")) as f:
        conn.executescript(f.read())

    load_csv(conn, "customers", os.path.join(RAW, "customers.csv"))
    load_csv(conn, "products", os.path.join(RAW, "products.csv"))
    load_csv(conn, "orders", os.path.join(RAW, "orders.csv"))
    load_csv(conn, "order_items", os.path.join(RAW, "order_items.csv"))
    load_csv(conn, "marketing_spend", os.path.join(RAW, "marketing_spend.csv"))

    conn.commit()

    counts = {}
    for t in ["customers", "products", "orders", "order_items", "marketing_spend"]:
        counts[t] = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    conn.close()

    for t, n in counts.items():
        print(f"{t:18s} {n:,} rows loaded")
    print(f"\nDatabase built at {DB_PATH}")


if __name__ == "__main__":
    main()
