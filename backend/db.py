import sqlite3

from flask import current_app, g


SCHEMA = """
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    amount_paise INTEGER NOT NULL,
    category TEXT NOT NULL,
    description TEXT NOT NULL,
    date TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS idempotency_keys (
    key TEXT PRIMARY KEY,
    request_hash TEXT NOT NULL,
    expense_id INTEGER NOT NULL,
    response_json TEXT NOT NULL,
    status_code INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (expense_id) REFERENCES expenses (id)
);
"""


def get_db():
    if "db" not in g:
        conn = sqlite3.connect(current_app.config["DATABASE"])
        conn.row_factory = sqlite3.Row
        g.db = conn
    return g.db


def close_db(_error=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_db(app):
    with sqlite3.connect(app.config["DATABASE"]) as conn:
        conn.executescript(SCHEMA)
    app.teardown_appcontext(close_db)
