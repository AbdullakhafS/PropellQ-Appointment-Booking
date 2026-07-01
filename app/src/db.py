from __future__ import annotations

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = BASE_DIR / "db" / "appointments.db"
SCHEMA_PATH = BASE_DIR / "db" / "schema_v1_production.sql"


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    target = db_path or DEFAULT_DB_PATH
    connection = sqlite3.connect(target)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection


def initialize_database(db_path: Path | None = None) -> None:
    target = db_path or DEFAULT_DB_PATH
    target.parent.mkdir(parents=True, exist_ok=True)

    with get_connection(target) as connection:
        schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
        connection.executescript(schema_sql)
        # Keep local DB deterministic and empty by default.
        # Login/demo user credentials are seeded separately in web_app._seed_demo_accounts.
        connection.commit()


def _seed_if_empty(connection: sqlite3.Connection) -> None:
    return


def _seed_supporting_records(connection: sqlite3.Connection) -> None:
    return
