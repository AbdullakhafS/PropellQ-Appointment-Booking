from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass
from datetime import date
from typing import Any

TIME_OF_DAY = {
    "morning": ("05:00", "11:59"),
    "afternoon": ("12:00", "16:59"),
    "evening": ("17:00", "22:00"),
}
ALLOWED_SORT_BY = {"date", "provider"}
ALLOWED_SORT_DIR = {"asc", "desc"}
MAX_RANGE_DAYS = 180


@dataclass
class ValidationResult:
    data: dict[str, Any]
    errors: list[str]


def parse_filters(params: dict[str, str], connection: sqlite3.Connection) -> ValidationResult:
    errors: list[str] = []
    page = _parse_int(params.get("page"), 1, "page", errors)
    page_size = _parse_int(params.get("pageSize"), 10, "pageSize", errors)
    parsed: dict[str, Any] = {
        "date_from": params.get("dateFrom", "").strip() or None,
        "date_to": params.get("dateTo", "").strip() or None,
        "time_of_day": params.get("timeOfDay", "").strip().lower() or None,
        "provider": params.get("provider", "").strip() or None,
        "specialty": params.get("specialty", "").strip() or None,
        "page": page,
        "page_size": page_size,
        "sort_by": (params.get("sortBy", "date") or "date").strip().lower(),
        "sort_dir": (params.get("sortDir", "asc") or "asc").strip().lower(),
    }

    if parsed["date_from"]:
        _validate_date(parsed["date_from"], "dateFrom", errors)
    if parsed["date_to"]:
        _validate_date(parsed["date_to"], "dateTo", errors)

    if parsed["date_from"] and parsed["date_to"]:
        d1 = date.fromisoformat(parsed["date_from"])
        d2 = date.fromisoformat(parsed["date_to"])
        if d1 > d2:
            errors.append("dateFrom must be before or equal to dateTo")
        if (d2 - d1).days > MAX_RANGE_DAYS:
            errors.append(f"Date range cannot exceed {MAX_RANGE_DAYS} days")

    if parsed["time_of_day"] and parsed["time_of_day"] not in TIME_OF_DAY:
        errors.append("timeOfDay must be one of: morning, afternoon, evening")

    if parsed["page"] < 1:
        errors.append("page must be >= 1")
    if parsed["page_size"] < 1 or parsed["page_size"] > 50:
        errors.append("pageSize must be between 1 and 50")

    if parsed["sort_by"] not in ALLOWED_SORT_BY:
        errors.append("sortBy must be one of: date, provider")

    if parsed["sort_dir"] not in ALLOWED_SORT_DIR:
        errors.append("sortDir must be one of: asc, desc")

    if parsed["specialty"]:
        names = {
            row["name"].lower()
            for row in connection.execute(
                "SELECT name FROM specialties WHERE is_active = 1"
            ).fetchall()
        }
        if parsed["specialty"].lower() not in names:
            errors.append("specialty must be a known active specialty")

    return ValidationResult(data=parsed, errors=errors)


def _validate_date(value: str, field_name: str, errors: list[str]) -> None:
    try:
        date.fromisoformat(value)
    except ValueError:
        errors.append(f"{field_name} must be ISO date (YYYY-MM-DD)")


def _parse_int(raw: str | None, default: int, field_name: str, errors: list[str]) -> int:
    value = (raw or "").strip()
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        errors.append(f"{field_name} must be an integer")
        return default


def search_appointments(connection: sqlite3.Connection, filters: dict[str, Any]) -> dict[str, Any]:
    where_clauses = ["a.status = 'available'", "p.is_active = 1", "s.is_active = 1"]
    values: list[Any] = []

    if filters["date_from"]:
        where_clauses.append("a.appointment_date >= ?")
        values.append(filters["date_from"])

    if filters["date_to"]:
        where_clauses.append("a.appointment_date <= ?")
        values.append(filters["date_to"])

    if filters["provider"]:
        where_clauses.append("LOWER(p.name) LIKE ?")
        values.append(f"%{filters['provider'].lower()}%")

    if filters["specialty"]:
        where_clauses.append("LOWER(s.name) = ?")
        values.append(filters["specialty"].lower())

    if filters["time_of_day"]:
        start_time, end_time = TIME_OF_DAY[filters["time_of_day"]]
        where_clauses.append("a.start_time BETWEEN ? AND ?")
        values.extend([start_time, end_time])

    where_sql = " AND ".join(where_clauses)

    if filters["sort_by"] == "provider":
        order_sql = "p.name {dir}, a.appointment_date ASC, a.start_time ASC, a.id ASC".format(
            dir=filters["sort_dir"].upper()
        )
    else:
        order_sql = "a.appointment_date {dir}, a.start_time ASC, a.id ASC".format(
            dir=filters["sort_dir"].upper()
        )

    total_sql = f"""
        SELECT COUNT(*) AS count
        FROM appointments a
        INNER JOIN providers p ON p.id = a.provider_id
        INNER JOIN specialties s ON s.id = a.specialty_id
        WHERE {where_sql}
    """
    total = connection.execute(total_sql, values).fetchone()["count"]

    limit = filters["page_size"]
    offset = (filters["page"] - 1) * limit

    items_sql = f"""
        SELECT
            a.id,
            a.appointment_date,
            a.start_time,
            a.end_time,
            a.location,
            a.duration_minutes,
            a.appointment_timezone,
            p.id AS provider_id,
            p.name AS provider_name,
            p.credentials,
            p.photo_url,
            p.review_count,
            p.bio,
            s.name AS specialty
        FROM appointments a
        INNER JOIN providers p ON p.id = a.provider_id
        INNER JOIN specialties s ON s.id = a.specialty_id
        WHERE {where_sql}
        ORDER BY {order_sql}
        LIMIT ? OFFSET ?
    """
    rows = connection.execute(items_sql, [*values, limit, offset]).fetchall()

    total_pages = max(1, math.ceil(total / limit)) if limit else 1
    items = [dict(row) for row in rows]

    return {
        "items": items,
        "pagination": {
            "page": filters["page"],
            "pageSize": limit,
            "total": total,
            "totalPages": total_pages,
            "hasNext": filters["page"] < total_pages,
        },
    }


def list_specialties(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = connection.execute(
        "SELECT id, name FROM specialties WHERE is_active = 1 ORDER BY name ASC"
    ).fetchall()
    return [dict(row) for row in rows]


def suggest_providers(connection: sqlite3.Connection, query: str) -> list[dict[str, Any]]:
    value = f"%{query.lower()}%"
    rows = connection.execute(
        """
        SELECT p.id, p.name, p.credentials, p.photo_url, p.review_count, p.bio, s.name AS specialty
        FROM providers p
        INNER JOIN specialties s ON s.id = p.specialty_id
        WHERE p.is_active = 1
          AND LOWER(p.name) LIKE ?
        ORDER BY p.name ASC
        LIMIT 8
        """,
        [value],
    ).fetchall()
    return [dict(row) for row in rows]


def get_provider(connection: sqlite3.Connection, provider_id: int) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT p.id, p.name, p.credentials, p.photo_url, p.review_count, p.bio, s.name AS specialty
        FROM providers p
        INNER JOIN specialties s ON s.id = p.specialty_id
        WHERE p.id = ?
        """,
        [provider_id],
    ).fetchone()
    return dict(row) if row else None


def book_appointment(connection: sqlite3.Connection, appointment_id: int) -> bool:
    row = connection.execute(
        "SELECT status FROM appointments WHERE id = ?",
        [appointment_id],
    ).fetchone()
    if row is None or row["status"] != "available":
        return False

    connection.execute(
        "UPDATE appointments SET status = 'booked' WHERE id = ?",
        [appointment_id],
    )
    connection.commit()
    return True
