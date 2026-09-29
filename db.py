"""
Data Layer
----------
Thin wrapper around sqlite3 used by the whole application. A file-based
SQLite database (lostfound.db) is used so the prototype runs with zero
external setup; the schema mirrors the entities suggested in Section 8.6
of the synopsis and can be pointed at MySQL/Postgres later by swapping
this module only (the rest of the app talks to `get_db()` exclusively).
"""

import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "lostfound.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(reset=False):
    if reset and os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    first_time = not os.path.exists(DB_PATH)
    conn = get_db()
    if first_time or reset:
        with open(SCHEMA_PATH, "r") as f:
            conn.executescript(f.read())
        conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db(reset=True)
    print(f"Database initialised at {DB_PATH}")
