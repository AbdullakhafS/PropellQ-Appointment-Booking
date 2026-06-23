from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import db
from src import search_service
from src.web_app import create_app


class AppointmentSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.temp_dir.name) / "test.db"
        db.initialize_database(cls.db_path)
        cls.app = create_app(cls.db_path)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.temp_dir.cleanup()
        except PermissionError:
            pass

    def _request(self, method: str, path: str, body: dict | None = None):
        payload = json.dumps(body or {}).encode("utf-8")
        environ = {
            "REQUEST_METHOD": method,
            "PATH_INFO": path.split("?")[0],
            "QUERY_STRING": path.split("?", 1)[1] if "?" in path else "",
            "CONTENT_LENGTH": str(len(payload)) if method == "POST" else "0",
            "wsgi.input": FakeInput(payload),
        }
        meta = {}

        def start_response(status, headers):
            meta["status"] = status
            meta["headers"] = headers

        body_chunks = self.__class__.app(environ, start_response)
        body_text = b"".join(body_chunks).decode("utf-8")
        return meta["status"], json.loads(body_text)

    def _connection(self):
        return db.get_connection(self.db_path)

    def test_parse_filters_normalizes_and_defaults(self):
        with self._connection() as connection:
            result = search_service.parse_filters(
                {
                    "dateFrom": "2026-06-23",
                    "dateTo": "2026-06-30",
                    "timeOfDay": "MORNING",
                    "provider": " Dr. Ava ",
                    "specialty": " Cardiology ",
                    "page": "2",
                    "pageSize": "5",
                    "sortBy": "provider",
                    "sortDir": "desc",
                },
                connection,
            )

        self.assertEqual(result.errors, [])
        self.assertEqual(result.data["date_from"], "2026-06-23")
        self.assertEqual(result.data["date_to"], "2026-06-30")
        self.assertEqual(result.data["time_of_day"], "morning")
        self.assertEqual(result.data["provider"], "Dr. Ava")
        self.assertEqual(result.data["specialty"], "Cardiology")
        self.assertEqual(result.data["page"], 2)
        self.assertEqual(result.data["page_size"], 5)
        self.assertEqual(result.data["sort_by"], "provider")
        self.assertEqual(result.data["sort_dir"], "desc")

    def test_parse_filters_rejects_invalid_values(self):
        with self._connection() as connection:
            result = search_service.parse_filters(
                {
                    "dateFrom": "2026-06-30",
                    "dateTo": "2026-06-01",
                    "timeOfDay": "night",
                    "page": "0",
                    "pageSize": "100",
                    "sortBy": "distance",
                    "sortDir": "sideways",
                    "specialty": "Unknown",
                },
                connection,
            )

        self.assertIn("dateFrom must be before or equal to dateTo", result.errors)
        self.assertIn("timeOfDay must be one of: morning, afternoon, evening", result.errors)
        self.assertIn("page must be >= 1", result.errors)
        self.assertIn("pageSize must be between 1 and 50", result.errors)
        self.assertIn("sortBy must be one of: date, provider", result.errors)
        self.assertIn("sortDir must be one of: asc, desc", result.errors)
        self.assertIn("specialty must be a known active specialty", result.errors)

    def test_search_appointments_applies_cumulative_filters(self):
        with self._connection() as connection:
            results = search_service.search_appointments(
                connection,
                {
                    "date_from": "2026-06-23",
                    "date_to": "2026-07-15",
                    "time_of_day": "morning",
                    "provider": "ava",
                    "specialty": "cardiology",
                    "page": 1,
                    "page_size": 5,
                    "sort_by": "date",
                    "sort_dir": "asc",
                },
            )

        self.assertGreater(results["pagination"]["total"], 0)
        self.assertLessEqual(len(results["items"]), 5)
        self.assertEqual(results["pagination"]["page"], 1)
        self.assertEqual(results["pagination"]["pageSize"], 5)
        for item in results["items"]:
            self.assertIn("Ava", item["provider_name"])
            self.assertEqual(item["specialty"], "Cardiology")
            self.assertGreaterEqual(item["start_time"], "05:00")
            self.assertLessEqual(item["start_time"], "11:59")
            self.assertGreaterEqual(item["appointment_date"], "2026-06-23")
            self.assertLessEqual(item["appointment_date"], "2026-07-15")

    def test_search_returns_available_slots(self):
        status, payload = self._request("GET", "/api/appointments/search?page=1&pageSize=10")
        self.assertTrue(status.startswith("200"))
        self.assertIn("data", payload)
        self.assertGreaterEqual(payload["data"]["pagination"]["total"], 1)
        for item in payload["data"]["items"]:
            self.assertIn("provider_name", item)
            self.assertIn("specialty", item)

    def test_validation_rejects_invalid_specialty(self):
        status, payload = self._request("GET", "/api/appointments/search?specialty=Unknown")
        self.assertTrue(status.startswith("400"))
        self.assertEqual(payload["error"]["code"], "VALIDATION_ERROR")

    def test_filters_are_cumulative(self):
        status, payload = self._request(
            "GET",
            "/api/appointments/search?timeOfDay=morning&specialty=Cardiology&pageSize=5",
        )
        self.assertTrue(status.startswith("200"))
        for item in payload["data"]["items"]:
            self.assertEqual(item["specialty"], "Cardiology")
            self.assertGreaterEqual(item["start_time"], "05:00")
            self.assertLessEqual(item["start_time"], "11:59")

    def test_validation_rejects_non_integer_page(self):
        status, payload = self._request("GET", "/api/appointments/search?page=first")
        self.assertTrue(status.startswith("400"))
        self.assertEqual(payload["error"]["code"], "VALIDATION_ERROR")

    def test_sorting_by_provider_is_deterministic(self):
        status, payload = self._request(
            "GET",
            "/api/appointments/search?sortBy=provider&sortDir=asc&page=1&pageSize=10",
        )
        self.assertTrue(status.startswith("200"))
        names = [item["provider_name"] for item in payload["data"]["items"]]
        self.assertEqual(names, sorted(names))

    def test_provider_suggestions_are_case_insensitive(self):
        with self._connection() as connection:
            suggestions = search_service.suggest_providers(connection, "aVa")

        self.assertGreaterEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0]["name"], "Dr. Ava Patel")

    def test_provider_suggest_endpoint_returns_empty_for_short_queries(self):
        status, payload = self._request("GET", "/api/providers/suggest?query=a")
        self.assertTrue(status.startswith("200"))
        self.assertEqual(payload["data"], [])

    def test_search_endpoint_returns_server_error_on_unexpected_failure(self):
        with patch("src.web_app.search_appointments", side_effect=RuntimeError("boom")):
            status, payload = self._request("GET", "/api/appointments/search?page=1&pageSize=10")

        self.assertTrue(status.startswith("500"))
        self.assertEqual(payload["error"]["code"], "SEARCH_FAILED")

    def test_empty_result_query_returns_zero_items(self):
        status, payload = self._request(
            "GET",
            "/api/appointments/search?dateFrom=2099-01-01&dateTo=2099-01-05&pageSize=10",
        )
        self.assertTrue(status.startswith("200"))
        self.assertEqual(payload["data"]["items"], [])
        self.assertEqual(payload["data"]["pagination"]["total"], 0)

    def test_booking_endpoint_updates_status(self):
        status, payload = self._request("GET", "/api/appointments/search?page=1&pageSize=1")
        self.assertTrue(status.startswith("200"))
        appointment_id = payload["data"]["items"][0]["id"]

        book_status, book_payload = self._request(
            "POST", f"/api/appointments/{appointment_id}/book"
        )
        self.assertTrue(book_status.startswith("200"))
        self.assertEqual(book_payload["data"]["status"], "booked")


class FakeInput:
    def __init__(self, payload: bytes):
        self.payload = payload
        self.read_called = False

    def read(self, _size: int = -1):
        if self.read_called:
            return b""
        self.read_called = True
        return self.payload


if __name__ == "__main__":
    unittest.main()
