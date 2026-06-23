from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src import db
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
