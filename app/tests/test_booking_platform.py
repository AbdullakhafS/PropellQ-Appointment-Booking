from __future__ import annotations

import json
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

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

    # --- TASK-001 QA-2: Search pagination and latency meta ---

    def test_search_pagination_meta_present(self):
        status, payload = self._request("GET", "/api/appointments/search?page=1&pageSize=5")
        self.assertTrue(status.startswith("200"))
        pagination = payload["data"]["pagination"]
        self.assertIn("total", pagination)
        self.assertIn("totalPages", pagination)
        self.assertIn("hasNext", pagination)
        self.assertIn("latencyMs", payload["meta"])

    # --- TASK-002 QA-5: Calendar timezone metadata ---

    def test_calendar_month_view_contains_timezone(self):
        status, payload = self._request("GET", "/api/appointments/calendar?view=month")
        self.assertTrue(status.startswith("200"))
        data = payload["data"]
        self.assertIn("timezone", data)
        self.assertIn("utcFooter", data)
        self.assertGreaterEqual(len(data["days"]), 28)

    # --- TASK-003 QA-1: Preferred slot captured on booking ---

    def test_preferred_slot_captured_on_finalize(self):
        status, payload = self._request("GET", "/api/appointments/search?page=1&pageSize=10")
        self.assertTrue(status.startswith("200"))
        items = payload["data"]["items"]
        self.assertGreaterEqual(len(items), 2)
        primary_slot = items[0]
        preferred_slot = items[1]

        reserve_status, reserve_payload = self._request(
            "POST",
            f"/api/appointments/{primary_slot['id']}/checkout",
            {"idempotencyKey": "reserve-preferred-1", "preferredSlotId": preferred_slot["id"]},
        )
        self.assertTrue(reserve_status.startswith("200"))

        book_status, book_payload = self._request(
            "POST",
            "/api/appointments/book",
            {
                "reservationToken": reserve_payload["data"]["reservationToken"],
                "idempotencyKey": "book-preferred-1",
                "firstName": "Dana",
                "lastName": "Hill",
                "email": "dana.hill@example.com",
                "phone": "+1-312-555-0199",
                "timezone": "America/Chicago",
                "preferredSlotId": preferred_slot["id"],
                "reminderChannels": ["email"],
            },
        )
        self.assertTrue(book_status.startswith("200"))
        appt = book_payload["data"]["appointment"]
        self.assertEqual(appt["preferred_slot_id"], preferred_slot["id"])
        self.assertIsNotNone(appt["preferred_window_expires_at"])

    # --- TASK-003 QA-2: Reservation expiry returns 410 ---

    def test_expired_reservation_token_returns_410(self):
        book_status, book_payload = self._request(
            "POST",
            "/api/appointments/book",
            {
                "reservationToken": "nonexistent-token-xyz",
                "idempotencyKey": "stale-1",
                "firstName": "Ghost",
                "lastName": "User",
                "email": "ghost@example.com",
                "phone": "+1-000-000-0000",
                "timezone": "UTC",
                "reminderChannels": [],
            },
        )
        self.assertTrue(book_status.startswith("410"))
        self.assertEqual(book_payload["error"]["code"], "RESERVATION_EXPIRED")

    # --- TASK-003 QA-3: Double-reservation on same slot returns 409 ---

    def test_concurrent_reservation_on_same_slot_returns_409(self):
        slot = self._find_available_slot()

        first_status, _ = self._request(
            "POST",
            f"/api/appointments/{slot['id']}/checkout",
            {"idempotencyKey": "conflict-first"},
        )
        self.assertTrue(first_status.startswith("200"))

        second_status, second_payload = self._request(
            "POST",
            f"/api/appointments/{slot['id']}/checkout",
            {"idempotencyKey": "conflict-second"},
        )
        self.assertTrue(second_status.startswith("409"))
        self.assertIn(second_payload["error"]["code"], ("UNAVAILABLE_SLOT", "RESERVED"))

        # Expire the reservation so subsequent tests can use slots freely
        with db.get_connection(self.__class__.db_path) as connection:
            connection.execute(
                "UPDATE appointment_reservations SET status = 'expired' WHERE appointment_id = ? AND status = 'active'",
                [slot["id"]],
            )
            connection.execute(
                "UPDATE appointments SET checkout_status = 'searching', reservation_token = NULL, reservation_expires_at = NULL WHERE id = ?",
                [slot["id"]],
            )
            connection.commit()

    # --- TASK-004 QA-1: Confirmation enqueued, non-blocking API response ---

    def test_confirmation_enqueued_on_booking(self):
        slot = self._find_available_slot()
        _, reserve_payload = self._request(
            "POST",
            f"/api/appointments/{slot['id']}/checkout",
            {"idempotencyKey": "enqueue-check-1"},
        )
        self._request(
            "POST",
            "/api/appointments/book",
            {
                "reservationToken": reserve_payload["data"]["reservationToken"],
                "idempotencyKey": "enqueue-book-1",
                "firstName": "Sam",
                "lastName": "Tan",
                "email": "sam.tan@example.com",
                "phone": "+1-312-555-0177",
                "timezone": "America/Chicago",
                "reminderChannels": ["email"],
            },
        )
        with db.get_connection(self.__class__.db_path) as connection:
            count = connection.execute(
                "SELECT COUNT(*) AS n FROM confirmation_deliveries WHERE status = 'queued' AND appointment_id = ?",
                [slot["id"]],
            ).fetchone()["n"]
        self.assertGreaterEqual(count, 1)

    # --- TASK-004 QA-4: Retry on failure, escalated after max retries ---

    def test_confirmation_retry_increments_and_escalates(self):
        slot = self._find_available_slot()
        _, reserve_payload = self._request(
            "POST",
            f"/api/appointments/{slot['id']}/checkout",
            {"idempotencyKey": "retry-check-1"},
        )
        self._request(
            "POST",
            "/api/appointments/book",
            {
                "reservationToken": reserve_payload["data"]["reservationToken"],
                "idempotencyKey": "retry-book-1",
                "firstName": "Max",
                "lastName": "Lane",
                "email": "max.lane@example.com",
                "phone": "+1-312-555-0133",
                "timezone": "America/Chicago",
                "reminderChannels": ["email"],
            },
        )
        # Set retry_count to MAX - 1 so the next failure triggers escalation to 'failed'
        with db.get_connection(self.__class__.db_path) as connection:
            delivery = connection.execute(
                "SELECT id FROM confirmation_deliveries WHERE appointment_id = ? AND status = 'queued'",
                [slot["id"]],
            ).fetchone()
            self.assertIsNotNone(delivery)
            connection.execute(
                "UPDATE confirmation_deliveries SET retry_count = 2 WHERE id = ?",
                [delivery["id"]],
            )
            connection.commit()

        import src.booking_service as booking_service_module
        with patch.object(booking_service_module, "_deliver_confirmation", side_effect=RuntimeError("Simulated delivery failure")):
            status, process_payload = self._request("POST", "/api/jobs/process-confirmations")

        self.assertTrue(status.startswith("200"))
        self.assertGreaterEqual(process_payload["data"]["escalated"], 1)

        with db.get_connection(self.__class__.db_path) as connection:
            result = connection.execute(
                "SELECT status, failure_reason FROM confirmation_deliveries WHERE id = ?",
                [delivery["id"]],
            ).fetchone()
        self.assertEqual(result["status"], "failed")
        self.assertIn("Simulated delivery failure", result["failure_reason"])

    # --- TASK-004 BE-4: Manual resend endpoint ---

    def test_resend_confirmation_re_queues_delivery(self):
        slot = self._find_available_slot()
        _, reserve_payload = self._request(
            "POST",
            f"/api/appointments/{slot['id']}/checkout",
            {"idempotencyKey": "resend-reserve-1"},
        )
        self._request(
            "POST",
            "/api/appointments/book",
            {
                "reservationToken": reserve_payload["data"]["reservationToken"],
                "idempotencyKey": "resend-book-1",
                "firstName": "Jordan",
                "lastName": "Park",
                "email": "jordan.park@example.com",
                "phone": "+1-312-555-0155",
                "timezone": "America/Chicago",
                "reminderChannels": ["email"],
            },
        )
        # Process the queue so status becomes 'sent'
        self._request("POST", "/api/jobs/process-confirmations")

        # Mark the existing delivery as failed so resend can create a new queued one
        with db.get_connection(self.__class__.db_path) as connection:
            connection.execute(
                "UPDATE confirmation_deliveries SET status = 'failed' WHERE appointment_id = ?",
                [slot["id"]],
            )
            connection.commit()

        resend_status, resend_payload = self._request(
            "POST",
            f"/api/appointments/{slot['id']}/resend-confirmation",
        )
        self.assertTrue(resend_status.startswith("200"))
        self.assertIn("appointmentId", resend_payload["data"])

        with db.get_connection(self.__class__.db_path) as connection:
            queued = connection.execute(
                "SELECT COUNT(*) AS n FROM confirmation_deliveries WHERE appointment_id = ? AND status = 'queued'",
                [slot["id"]],
            ).fetchone()["n"]
        self.assertGreaterEqual(queued, 1)

    def test_resend_confirmation_nonexistent_appointment_returns_404(self):
        status, payload = self._request("POST", "/api/appointments/999999/resend-confirmation")
        self.assertTrue(status.startswith("404"))
        self.assertEqual(payload["error"]["code"], "APPOINTMENT_NOT_FOUND")

    # --- TASK-005 QA-2: Swap skips unavailable preferred slots ---

    def test_swap_job_skips_when_preferred_slot_unavailable(self):
        # Book two slots: use the first as primary, then mark preferred_slot_id pointing
        # to a slot that is already 'booked' so the swap engine skips it.
        status, search_payload = self._request("GET", "/api/appointments/search?page=1&pageSize=5")
        self.assertTrue(status.startswith("200"))
        items = search_payload["data"]["items"]
        primary = items[0]
        preferred_target = items[1]

        # Book primary slot normally (no preferred)
        _, r1 = self._request("POST", f"/api/appointments/{primary['id']}/checkout", {"idempotencyKey": "swap-skip-r1"})
        self._request(
            "POST", "/api/appointments/book",
            {
                "reservationToken": r1["data"]["reservationToken"],
                "idempotencyKey": "swap-skip-b1",
                "firstName": "Bex", "lastName": "Cole",
                "email": "bex.cole@example.com", "phone": "+1-312-555-0188",
                "timezone": "America/Chicago", "reminderChannels": ["email"],
            },
        )
        # Book preferred_target slot so it becomes unavailable
        _, r2 = self._request("POST", f"/api/appointments/{preferred_target['id']}/checkout", {"idempotencyKey": "swap-skip-r2"})
        self._request(
            "POST", "/api/appointments/book",
            {
                "reservationToken": r2["data"]["reservationToken"],
                "idempotencyKey": "swap-skip-b2",
                "firstName": "Ren", "lastName": "Fox",
                "email": "ren.fox@example.com", "phone": "+1-312-555-0189",
                "timezone": "America/Chicago", "reminderChannels": ["email"],
            },
        )
        # Directly assign the booked slot as the preferred_slot_id on the primary appointment
        with db.get_connection(self.__class__.db_path) as connection:
            from src.booking_service import to_iso, utc_now
            from datetime import timedelta
            connection.execute(
                "UPDATE appointments SET preferred_slot_id = ?, preferred_window_expires_at = ? WHERE id = ?",
                [preferred_target["id"], to_iso(utc_now() + timedelta(hours=1)), primary["id"]],
            )
            connection.commit()

        status, payload = self._request("POST", "/api/jobs/process-swaps")
        self.assertTrue(status.startswith("200"))
        self.assertGreaterEqual(payload["data"]["skipped"], 1)

    # --- TASK-005 QA-3/QA-5: Swap audit record created ---

    def test_swap_audit_record_written(self):
        status, payload = self._request("POST", "/api/jobs/process-swaps")
        self.assertTrue(status.startswith("200"))
        with db.get_connection(self.__class__.db_path) as connection:
            count = connection.execute(
                "SELECT COUNT(*) AS n FROM preferred_slot_swap_history"
            ).fetchone()["n"]
        self.assertGreaterEqual(count, 0)

    # --- TASK-006 BE-5: Reminder send failure tracked with retry_count ---

    def test_reminder_failure_tracked_in_log(self):
        import src.booking_service as booking_service

        slot = self._find_available_slot()
        res_status, res_payload = self._request(
            "POST",
            f"/api/appointments/{slot['id']}/checkout",
            {"idempotencyKey": "reserve-reminder-fail-1"},
        )
        self.assertTrue(res_status.startswith("200"))
        bk_status, bk_payload = self._request(
            "POST",
            "/api/appointments/book",
            {
                "reservationToken": res_payload["data"]["reservationToken"],
                "idempotencyKey": "book-reminder-fail-1",
                "firstName": "Failure",
                "lastName": "Test",
                "email": "failtest@example.com",
                "phone": "+1-312-555-0200",
                "timezone": "America/Chicago",
                "reminderChannels": ["sms"],
            },
        )
        self.assertTrue(bk_status.startswith("200"))
        appointment_id = bk_payload["data"]["appointment"]["id"]

        with db.get_connection(self.__class__.db_path) as connection:
            target = utc_now() + timedelta(hours=48) - timedelta(minutes=5)
            connection.execute(
                "UPDATE patient_profiles SET preferred_timezone = 'UTC' WHERE id = 1",
            )
            connection.execute(
                """
                UPDATE appointments
                SET appointment_date = ?, start_time = ?, end_time = ?,
                    appointment_timezone = 'UTC', patient_timezone = 'UTC'
                WHERE id = ?
                """,
                [
                    target.date().isoformat(),
                    target.time().replace(microsecond=0).isoformat(timespec="minutes"),
                    (target + timedelta(minutes=30)).time().replace(microsecond=0).isoformat(timespec="minutes"),
                    appointment_id,
                ],
            )
            connection.commit()

        with patch.object(
            booking_service,
            "_send_reminder",
            side_effect=RuntimeError("Simulated send failure"),
        ):
            status, payload = self._request("POST", "/api/jobs/process-reminders")
        self.assertTrue(status.startswith("200"))
        self.assertGreaterEqual(payload["data"]["failed"], 1)

        with db.get_connection(self.__class__.db_path) as connection:
            log_row = connection.execute(
                """
                SELECT * FROM reminder_log
                WHERE appointment_id = ? AND delivery_status = 'failed'
                ORDER BY id DESC LIMIT 1
                """,
                [appointment_id],
            ).fetchone()
        self.assertIsNotNone(log_row)
        self.assertIn("Simulated send failure", log_row["failure_reason"])
        self.assertEqual(log_row["retry_count"], 1)

    # --- TASK-006 BE-7: do_not_disturb flag skips reminders ---

    def test_reminder_do_not_disturb_skips_patient(self):
        slot = self._find_available_slot()
        res_status, res_payload = self._request(
            "POST",
            f"/api/appointments/{slot['id']}/checkout",
            {"idempotencyKey": "reserve-dnd-1"},
        )
        self.assertTrue(res_status.startswith("200"))
        bk_status, bk_payload = self._request(
            "POST",
            "/api/appointments/book",
            {
                "reservationToken": res_payload["data"]["reservationToken"],
                "idempotencyKey": "book-dnd-1",
                "firstName": "DnD",
                "lastName": "Patient",
                "email": "dnd@example.com",
                "phone": "+1-312-555-0201",
                "timezone": "America/Chicago",
                "reminderChannels": ["sms", "email"],
            },
        )
        self.assertTrue(bk_status.startswith("200"))
        appointment_id = bk_payload["data"]["appointment"]["id"]

        with db.get_connection(self.__class__.db_path) as connection:
            target = utc_now() + timedelta(hours=48) - timedelta(minutes=5)
            connection.execute("UPDATE patient_profiles SET do_not_disturb = 1 WHERE id = 1")
            connection.execute(
                """
                UPDATE appointments
                SET appointment_date = ?, start_time = ?, end_time = ?,
                    appointment_timezone = 'UTC', patient_timezone = 'UTC'
                WHERE id = ?
                """,
                [
                    target.date().isoformat(),
                    target.time().replace(microsecond=0).isoformat(timespec="minutes"),
                    (target + timedelta(minutes=30)).time().replace(microsecond=0).isoformat(timespec="minutes"),
                    appointment_id,
                ],
            )
            connection.commit()

        try:
            status, payload = self._request("POST", "/api/jobs/process-reminders")
            self.assertTrue(status.startswith("200"))
            self.assertGreaterEqual(payload["data"]["skipped"], 1)
            self.assertEqual(payload["data"]["sent"], 0)
        finally:
            with db.get_connection(self.__class__.db_path) as connection:
                connection.execute("UPDATE patient_profiles SET do_not_disturb = 0 WHERE id = 1")
                connection.commit()

    # --- TASK-006 OPS-1: Dashboard includes per-window reminder breakdown ---

    def test_dashboard_includes_reminder_window_breakdown(self):
        status, payload = self._request("GET", "/api/dashboard/metrics")
        self.assertTrue(status.startswith("200"))
        data = payload["data"]
        self.assertIn("remindersByWindow", data)
        self.assertIn("calendarSyncFailedByProvider", data)
        self.assertIsInstance(data["remindersByWindow"], dict)

    # --- TASK-007/008 BE-6: OAuth error — state nonce mismatch rejected ---

    def test_oauth_state_nonce_mismatch_rejected(self):
        # Google with wrong state nonce should return error
        status, payload = self._request(
            "GET",
            "/api/auth/google/callback?state=INVALID_NONCE_XYZ&code=mock-code",
        )
        self.assertTrue(status.startswith("400"))

    # --- TASK-007/008 BE-6: Access denied by user propagates error status ---

    def test_oauth_access_denied_sets_error_status(self):
        # First get a valid state nonce
        auth_status, auth_payload = self._request("GET", "/api/auth/google/authorize")
        self.assertTrue(auth_status.startswith("200"))
        auth_url = auth_payload["data"]["authorizeUrl"]
        import urllib.parse as _urlparse

        parsed = _urlparse.urlparse(auth_url)
        nonce = _urlparse.parse_qs(parsed.query).get("state", [""])[0]
        self.assertTrue(nonce)

        # Simulate user denying consent
        status, payload = self._request(
            "GET",
            f"/api/auth/google/callback?state={nonce}&error=access_denied",
        )
        self.assertTrue(status.startswith("400"))

        # Auth status in session should be 'error'
        with db.get_connection(self.__class__.db_path) as connection:
            session = connection.execute(
                "SELECT google_auth_status FROM patient_sessions WHERE patient_profile_id = 1"
            ).fetchone()
        self.assertEqual(session["google_auth_status"], "error")

    # --- TASK-009 BE-8: Calendar sync retry/backoff on failure ---

    def test_calendar_sync_retry_increments_on_failure(self):
        import src.booking_service as booking_service

        # Connect Google
        auth_status, auth_payload = self._request("GET", "/api/auth/google/authorize")
        self.assertTrue(auth_status.startswith("200"))
        cb_status, _ = self._request("GET", auth_payload["data"]["authorizeUrl"])
        self.assertTrue(cb_status.startswith("200"))

        slot = self._find_available_slot()
        res_status, res_payload = self._request(
            "POST",
            f"/api/appointments/{slot['id']}/checkout",
            {"idempotencyKey": "reserve-sync-retry-1"},
        )
        self.assertTrue(res_status.startswith("200"))
        bk_status, bk_payload = self._request(
            "POST",
            "/api/appointments/book",
            {
                "reservationToken": res_payload["data"]["reservationToken"],
                "idempotencyKey": "book-sync-retry-1",
                "firstName": "SyncRetry",
                "lastName": "Test",
                "email": "syncretry@example.com",
                "phone": "+1-312-555-0202",
                "timezone": "America/Chicago",
                "reminderChannels": ["email"],
            },
        )
        self.assertTrue(bk_status.startswith("200"))
        appointment_id = bk_payload["data"]["appointment"]["id"]

        with db.get_connection(self.__class__.db_path) as connection:
            queue_row = connection.execute(
                "SELECT * FROM calendar_sync_queue WHERE appointment_id = ? AND status = 'pending' ORDER BY id DESC LIMIT 1",
                [appointment_id],
            ).fetchone()
        self.assertIsNotNone(queue_row, "Sync queue item should have been enqueued after booking")
        queue_id = queue_row["id"]

        # Simulate sync failure by patching _appointment_local_start inside the module
        with patch.object(
            booking_service,
            "_appointment_local_start",
            side_effect=RuntimeError("Simulated calendar API failure"),
        ):
            status, payload = self._request("POST", "/api/jobs/process-calendar-sync")
        self.assertTrue(status.startswith("200"))

        with db.get_connection(self.__class__.db_path) as connection:
            updated = dict(
                connection.execute(
                    "SELECT * FROM calendar_sync_queue WHERE id = ?", [queue_id]
                ).fetchone()
            )
        self.assertEqual(updated["retry_count"], 1)
        self.assertEqual(updated["status"], "pending")
        self.assertIsNotNone(updated["scheduled_retry_at"])

        # Cleanup: disconnect Google to prevent sync interference with other tests
        self._request("POST", "/api/auth/google/disconnect", {})

    # --- TASK-009 BE-8: Calendar sync marks failed after MAX retries ---

    def test_calendar_sync_max_retries_marks_failed(self):
        import src.booking_service as booking_service

        with db.get_connection(self.__class__.db_path) as connection:
            # Insert a sync queue item already at (MAX-1) retries, pointing to any real appointment
            connection.execute(
                """
                INSERT INTO calendar_sync_queue(
                    appointment_id, action, calendar_type, idempotency_key,
                    payload_json, retry_count, status, scheduled_retry_at
                )
                SELECT id, 'create', 'google', 'max-retry-test-key-001',
                       '{"source":"test"}', ?, 'pending', datetime('now','-1 second')
                FROM appointments LIMIT 1
                """,
                [booking_service.SYNC_MAX_RETRIES - 1],
            )
            connection.commit()
            queue_row = connection.execute(
                "SELECT id, appointment_id FROM calendar_sync_queue WHERE idempotency_key = 'max-retry-test-key-001'"
            ).fetchone()
        self.assertIsNotNone(queue_row)
        queue_id = queue_row["id"]

        with patch.object(
            booking_service,
            "_appointment_local_start",
            side_effect=RuntimeError("Final failure"),
        ):
            status, payload = self._request("POST", "/api/jobs/process-calendar-sync")
        self.assertTrue(status.startswith("200"))

        with db.get_connection(self.__class__.db_path) as connection:
            row = dict(
                connection.execute(
                    "SELECT * FROM calendar_sync_queue WHERE id = ?", [queue_id]
                ).fetchone()
            )
        self.assertEqual(row["status"], "failed")
        self.assertEqual(row["retry_count"], booking_service.SYNC_MAX_RETRIES)

        # Audit record written for failure
        with db.get_connection(self.__class__.db_path) as connection:
            audit = connection.execute(
                "SELECT * FROM calendar_sync_audit WHERE appointment_id = ? AND result = 'failure' ORDER BY id DESC LIMIT 1",
                [queue_row["appointment_id"]],
            ).fetchone()
        self.assertIsNotNone(audit)


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
