from __future__ import annotations

import json
import mimetypes
import re
from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Any
from urllib.parse import parse_qs

from src.db import DEFAULT_DB_PATH, initialize_database, get_connection
from src.search_service import (
    book_appointment,
    get_provider,
    list_specialties,
    parse_filters,
    search_appointments,
    suggest_providers,
)

BASE_DIR = Path(__file__).resolve().parents[1]
PUBLIC_DIR = BASE_DIR / "public"


@dataclass
class SearchMetrics:
    total_queries: int = 0
    empty_results: int = 0
    latencies_ms: list[float] = field(default_factory=list)

    def record(self, latency_ms: float, result_count: int) -> None:
        self.total_queries += 1
        if result_count == 0:
            self.empty_results += 1
        self.latencies_ms.append(latency_ms)
        if len(self.latencies_ms) > 2000:
            self.latencies_ms = self.latencies_ms[-1000:]

    def snapshot(self) -> dict[str, Any]:
        if not self.latencies_ms:
            return {
                "totalQueries": self.total_queries,
                "emptyResults": self.empty_results,
                "emptyResultRate": 0,
                "p95LatencyMs": 0,
                "averageLatencyMs": 0,
                "alertBreached": False,
            }

        ordered = sorted(self.latencies_ms)
        p95_index = max(0, int(len(ordered) * 0.95) - 1)
        p95 = round(ordered[p95_index], 2)
        avg = round(sum(self.latencies_ms) / len(self.latencies_ms), 2)
        empty_rate = round((self.empty_results / max(1, self.total_queries)) * 100, 2)

        return {
            "totalQueries": self.total_queries,
            "emptyResults": self.empty_results,
            "emptyResultRate": empty_rate,
            "p95LatencyMs": p95,
            "averageLatencyMs": avg,
            "alertBreached": p95 > 2000,
        }


def create_app(db_path: Path | None = None):
    selected_db = db_path or DEFAULT_DB_PATH
    initialize_database(selected_db)
    metrics = SearchMetrics()

    def app(environ, start_response):
        started_at = perf_counter()
        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = environ.get("PATH_INFO", "/")

        if method == "GET" and path == "/api/appointments/search":
            return _handle_search(environ, start_response, selected_db, metrics, started_at)

        if method == "GET" and path == "/api/appointments/specialties":
            return _handle_specialties(start_response, selected_db)

        if method == "GET" and path == "/api/providers/suggest":
            return _handle_provider_suggest(environ, start_response, selected_db)

        provider_match = re.match(r"^/api/providers/(\d+)$", path)
        if method == "GET" and provider_match:
            return _handle_provider_details(start_response, selected_db, int(provider_match.group(1)))

        book_match = re.match(r"^/api/appointments/(\d+)/book$", path)
        if method == "POST" and book_match:
            return _handle_book_appointment(start_response, selected_db, int(book_match.group(1)))

        if method == "GET" and path == "/api/metrics/search":
            return _json_response(start_response, 200, {"success": True, "data": metrics.snapshot()})

        if path.startswith("/api/"):
            return _json_response(
                start_response,
                404,
                {
                    "success": False,
                    "error": {
                        "code": "NOT_FOUND",
                        "message": "API route not found",
                    },
                },
            )

        return _serve_static(path, start_response)

    return app


def _handle_search(environ, start_response, db_path: Path, metrics: SearchMetrics, started_at: float):
    query_params = _flat_query_params(environ.get("QUERY_STRING", ""))

    with get_connection(db_path) as connection:
        validated = parse_filters(query_params, connection)
        if validated.errors:
            return _json_response(
                start_response,
                400,
                {
                    "success": False,
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Invalid search parameters",
                        "details": validated.errors,
                    },
                },
            )

        results = search_appointments(connection, validated.data)

    elapsed_ms = (perf_counter() - started_at) * 1000
    metrics.record(elapsed_ms, len(results["items"]))

    return _json_response(
        start_response,
        200,
        {
            "success": True,
            "data": results,
            "meta": {
                "latencyMs": round(elapsed_ms, 2),
            },
        },
    )


def _handle_specialties(start_response, db_path: Path):
    with get_connection(db_path) as connection:
        rows = list_specialties(connection)
    return _json_response(start_response, 200, {"success": True, "data": rows})


def _handle_provider_suggest(environ, start_response, db_path: Path):
    params = _flat_query_params(environ.get("QUERY_STRING", ""))
    query = (params.get("query") or "").strip()
    if len(query) < 2:
        return _json_response(start_response, 200, {"success": True, "data": []})

    with get_connection(db_path) as connection:
        rows = suggest_providers(connection, query)
    return _json_response(start_response, 200, {"success": True, "data": rows})


def _handle_provider_details(start_response, db_path: Path, provider_id: int):
    with get_connection(db_path) as connection:
        data = get_provider(connection, provider_id)

    if data is None:
        return _json_response(
            start_response,
            404,
            {
                "success": False,
                "error": {
                    "code": "PROVIDER_NOT_FOUND",
                    "message": "Provider not found",
                },
            },
        )

    return _json_response(start_response, 200, {"success": True, "data": data})


def _handle_book_appointment(start_response, db_path: Path, appointment_id: int):
    with get_connection(db_path) as connection:
        booked = book_appointment(connection, appointment_id)

    if not booked:
        return _json_response(
            start_response,
            409,
            {
                "success": False,
                "error": {
                    "code": "UNAVAILABLE_SLOT",
                    "message": "Selected appointment slot is no longer available",
                },
            },
        )

    return _json_response(
        start_response,
        200,
        {"success": True, "data": {"appointmentId": appointment_id, "status": "booked"}},
    )


def _serve_static(path: str, start_response):
    requested = "index.html" if path in ("", "/") else path.lstrip("/")
    target = (PUBLIC_DIR / requested).resolve()

    if not str(target).startswith(str(PUBLIC_DIR.resolve())):
        return _plain_response(start_response, 403, b"Forbidden", "text/plain")

    if not target.exists() or target.is_dir():
        target = PUBLIC_DIR / "index.html"

    content = target.read_bytes()
    mime_type, _ = mimetypes.guess_type(target.name)
    return _plain_response(start_response, 200, content, mime_type or "text/html")


def _json_response(start_response, status_code: int, payload: dict[str, Any]):
    body = json.dumps(payload).encode("utf-8")
    status_text = f"{status_code} {_status_text(status_code)}"
    headers = [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Content-Length", str(len(body))),
        ("Cache-Control", "no-store"),
    ]
    start_response(status_text, headers)
    return [body]


def _plain_response(start_response, status_code: int, body: bytes, content_type: str):
    status_text = f"{status_code} {_status_text(status_code)}"
    headers = [
        ("Content-Type", f"{content_type}; charset=utf-8"),
        ("Content-Length", str(len(body))),
    ]
    start_response(status_text, headers)
    return [body]


def _status_text(status_code: int) -> str:
    text = {
        200: "OK",
        400: "Bad Request",
        403: "Forbidden",
        404: "Not Found",
        409: "Conflict",
    }
    return text.get(status_code, "OK")


def _flat_query_params(query_string: str) -> dict[str, str]:
    parsed = parse_qs(query_string, keep_blank_values=False)
    return {key: values[0] for key, values in parsed.items() if values}
