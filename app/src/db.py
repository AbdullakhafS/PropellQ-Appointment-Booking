from __future__ import annotations

import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = BASE_DIR / "db" / "appointments.db"
SCHEMA_PATH = BASE_DIR / "db" / "schema.sql"


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
        _seed_if_empty(connection)


def _seed_if_empty(connection: sqlite3.Connection) -> None:
    existing = connection.execute("SELECT COUNT(*) AS count FROM appointments").fetchone()["count"]
    if existing > 0:
        return

    specialties = [
        (1, "Cardiology"),
        (2, "Dermatology"),
        (3, "General Medicine"),
        (4, "Neurology"),
        (5, "Orthopedics"),
        (6, "Pediatrics"),
    ]
    providers = [
        (1, "Dr. Ava Patel", "MD", 1, "https://example.com/providers/ava.jpg"),
        (2, "Dr. Lucas Kim", "MD", 2, "https://example.com/providers/lucas.jpg"),
        (3, "Dr. Nora Singh", "DO", 3, "https://example.com/providers/nora.jpg"),
        (4, "Dr. Ethan Brooks", "MD", 4, "https://example.com/providers/ethan.jpg"),
        (5, "Dr. Mia Chen", "MD", 5, "https://example.com/providers/mia.jpg"),
        (6, "Dr. Sophia Diaz", "MD", 6, "https://example.com/providers/sophia.jpg"),
    ]
    locations = [
        "Downtown Clinic",
        "Northside Care Center",
        "Lakeside Medical Pavilion",
    ]

    connection.executemany(
        "INSERT INTO specialties(id, name, is_active) VALUES (?, ?, 1)", specialties
    )
    connection.executemany(
        "INSERT INTO providers(id, name, credentials, specialty_id, photo_url, is_active) VALUES (?, ?, ?, ?, ?, 1)",
        providers,
    )

    random.seed(42)
    slots = []
    slot_id = 1
    start_day = date.today()
    time_blocks = [
        ("08:30", "09:00"),
        ("12:30", "13:00"),
        ("17:30", "18:00"),
    ]

    for offset in range(0, 45):
        day_value = (start_day + timedelta(days=offset)).isoformat()
        for provider_id, _name, _credentials, specialty_id, _photo_url in providers:
            for start_time, end_time in time_blocks:
                status = "available" if random.random() > 0.15 else "booked"
                slots.append(
                    (
                        slot_id,
                        provider_id,
                        specialty_id,
                        day_value,
                        start_time,
                        end_time,
                        random.choice(locations),
                        status,
                    )
                )
                slot_id += 1

    connection.executemany(
        """
        INSERT INTO appointments(
            id,
            provider_id,
            specialty_id,
            appointment_date,
            start_time,
            end_time,
            location,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        slots,
    )
    connection.commit()
