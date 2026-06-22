from __future__ import annotations

import json
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from src import db
from src.booking_service import parse_iso, to_iso, utc_now
from src.web_app import create_app


class BookingPlatformTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.temp_dir.name) / "platform.db"
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
            "PATH_INFO": path.split("?", 1)[0],
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

    def _find_available_slot(self):
        status, payload = self._request("GET", "/api/appointments/search?page=1&pageSize=5")
        self.assertTrue(status.startswith("200"))
        return payload["data"]["items"][0]

    def test_calendar_endpoint_returns_days(self):
        status, payload = self._request("GET", "/api/appointments/calendar?view=week")
        self.assertTrue(status.startswith("200"))
        self.assertEqual(payload["data"]["view"], "week")
        self.assertGreaterEqual(len(payload["data"]["days"]), 14)

    def test_checkout_and_booking_flow(self):
        slot = self._find_available_slot()
        reserve_status, reserve_payload = self._request(
            "POST",
            f"/api/appointments/{slot['id']}/checkout",
            {"idempotencyKey": "reserve-flow-1"},
        )
        self.assertTrue(reserve_status.startswith("200"))
        self.assertIn("reservationToken", reserve_payload["data"])

        book_status, book_payload = self._request(
            "POST",
            "/api/appointments/book",
            {
                "reservationToken": reserve_payload["data"]["reservationToken"],
                "idempotencyKey": "book-flow-1",
                "firstName": "Alex",
                "lastName": "Morgan",
                "email": "alex.morgan@example.com",
                "phone": "+1-312-555-0186",
                "timezone": "America/Chicago",
                "notes": "Needs wheelchair access",
                "reminderChannels": ["sms", "email"],
            },
        )
        self.assertTrue(book_status.startswith("200"))
        self.assertEqual(book_payload["data"]["appointment"]["checkout_status"], "confirmed")

    def test_confirmation_job_processes_queued_delivery(self):
        slot = self._find_available_slot()
        reserve_status, reserve_payload = self._request(
            "POST",
            f"/api/appointments/{slot['id']}/checkout",
            {"idempotencyKey": "reserve-confirmation-1"},
        )
        self.assertTrue(reserve_status.startswith("200"))
        self._request(
            "POST",
            "/api/appointments/book",
            {
                "reservationToken": reserve_payload["data"]["reservationToken"],
                "idempotencyKey": "book-confirmation-1",
                "firstName": "Jamie",
                "lastName": "Lee",
                "email": "jamie.lee@example.com",
                "phone": "+1-312-555-0100",
                "timezone": "America/Chicago",
                "reminderChannels": ["email"],
            },
        )
        status, payload = self._request("POST", "/api/jobs/process-confirmations")
        self.assertTrue(status.startswith("200"))
        self.assertGreaterEqual(payload["data"]["processed"], 1)

    def test_reminder_job_sends_due_entries(self):
        slot = self._find_available_slot()
        reserve_status, reserve_payload = self._request(
            "POST",
            f"/api/appointments/{slot['id']}/checkout",
            {"idempotencyKey": "reserve-reminder-1"},
        )
        self.assertTrue(reserve_status.startswith("200"))
        book_status, book_payload = self._request(
            "POST",
            "/api/appointments/book",
            {
                "reservationToken": reserve_payload["data"]["reservationToken"],
                "idempotencyKey": "book-reminder-1",
                "firstName": "Taylor",
                "lastName": "Stone",
                "email": "taylor.stone@example.com",
                "phone": "+1-312-555-0101",
                "timezone": "America/Chicago",
                "reminderChannels": ["sms", "email"],
            },
        )
        appointment_id = book_payload["data"]["appointment"]["id"]

        with db.get_connection(self.__class__.db_path) as connection:
            target = utc_now() + timedelta(hours=48) - timedelta(minutes=5)
            connection.execute(
                "UPDATE patient_profiles SET preferred_timezone = ? WHERE id = 1",
                ["UTC"],
            )
            connection.execute(
                """
                UPDATE appointments
                SET appointment_date = ?,
                    start_time = ?,
                    end_time = ?,
                    appointment_timezone = ?,
                    patient_timezone = ?
                WHERE id = ?
                """,
                [
                    target.date().isoformat(),
                    target.time().replace(microsecond=0).isoformat(timespec="minutes"),
                    (target + timedelta(minutes=30)).time().replace(microsecond=0).isoformat(timespec="minutes"),
                    "UTC",
                    "UTC",
                    appointment_id,
                ],
            )
            connection.commit()

        status, payload = self._request("POST", "/api/jobs/process-reminders")
        self.assertTrue(status.startswith("200"))
        self.assertGreaterEqual(payload["data"]["sent"], 2)

    def test_google_and_outlook_authorization_and_sync(self):
        status, payload = self._request("GET", "/api/auth/google/authorize")
        self.assertTrue(status.startswith("200"))
        callback_status, callback_payload = self._request("GET", payload["data"]["authorizeUrl"])
        self.assertTrue(callback_status.startswith("200"))
        self.assertTrue(callback_payload["data"]["integration"]["google"]["connected"])

        status, payload = self._request("GET", "/api/auth/outlook/authorize")
        self.assertTrue(status.startswith("200"))
        callback_status, callback_payload = self._request("GET", payload["data"]["authorizeUrl"])
        self.assertTrue(callback_status.startswith("200"))
        self.assertTrue(callback_payload["data"]["integration"]["outlook"]["connected"])

        slot = self._find_available_slot()
        reserve_status, reserve_payload = self._request(
            "POST",
            f"/api/appointments/{slot['id']}/checkout",
            {"idempotencyKey": "reserve-sync-1"},
        )
        self.assertTrue(reserve_status.startswith("200"))
        self._request(
            "POST",
            "/api/appointments/book",
            {
                "reservationToken": reserve_payload["data"]["reservationToken"],
                "idempotencyKey": "book-sync-1",
                "firstName": "Riley",
                "lastName": "West",
                "email": "riley.west@example.com",
                "phone": "+1-312-555-0102",
                "timezone": "America/Chicago",
                "reminderChannels": ["email"],
            },
        )
        sync_status, sync_payload = self._request("POST", "/api/jobs/process-calendar-sync")
        self.assertTrue(sync_status.startswith("200"))
        self.assertGreaterEqual(sync_payload["data"]["processed"], 2)

    def test_disconnect_only_revokes_one_provider(self):
        google_status, google_payload = self._request("GET", "/api/auth/google/authorize")
        self.assertTrue(google_status.startswith("200"))
        self._request("GET", google_payload["data"]["authorizeUrl"])

        outlook_status, outlook_payload = self._request("GET", "/api/auth/outlook/authorize")
        self.assertTrue(outlook_status.startswith("200"))
        self._request("GET", outlook_payload["data"]["authorizeUrl"])

        disconnect_status, disconnect_payload = self._request("POST", "/api/auth/outlook/disconnect")
        self.assertTrue(disconnect_status.startswith("200"))
        self.assertTrue(disconnect_payload["data"]["integration"]["google"]["connected"])
        self.assertFalse(disconnect_payload["data"]["integration"]["outlook"]["connected"])


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
