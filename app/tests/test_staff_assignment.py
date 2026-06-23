"""
EP-005 US-045: Staff Assignment Security Validation (task_045_004)

Covers:
  task_045_001 — Assignment-scoped staff queue access
  task_045_002 — Minimum-necessary patient detail for staff workflows
  task_045_003 — Staff access action logging with assignment context
  task_045_004 — Full assignment-based security validation
"""
from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path

from src.rbac import (
    _AUDIT_LOG,
    _STAFF_ACCESS_LOG,
    _STAFF_ASSIGNMENTS,
    _STAFF_EXCLUDED_PATIENT_FIELDS,
    check_staff_assignment,
    filter_staff_patient_detail,
    get_staff_access_log,
    get_staff_assigned_providers,
    get_staff_id_from_environ,
    log_staff_access_event,
    require_staff_assignment,
    set_staff_assignment,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _env(
    role: str = "staff",
    staff_id: str = "S1",
    path: str = "/api/staff/queue",
    method: str = "GET",
    patient_id: int = 1,
) -> dict:
    return {
        "HTTP_X_ROLE": role,
        "HTTP_X_STAFF_ID": staff_id,
        "HTTP_X_PATIENT_ID": str(patient_id),
        "PATH_INFO": path,
        "REQUEST_METHOD": method,
    }


# ---------------------------------------------------------------------------
# task_045_001: Assignment-scoped queue access — unit tests
# ---------------------------------------------------------------------------

class StaffAssignmentScopingTests(unittest.TestCase):

    def setUp(self):
        _AUDIT_LOG.clear()
        _STAFF_ASSIGNMENTS.clear()

    # ── Positive cases ────────────────────────────────────────────────────

    def test_assigned_staff_has_assignment(self):
        set_staff_assignment("S1", [10, 20])
        self.assertTrue(check_staff_assignment("S1"))

    def test_assigned_staff_matches_specific_provider(self):
        set_staff_assignment("S1", [10, 20])
        self.assertTrue(check_staff_assignment("S1", provider_id=10))

    def test_admin_bypasses_assignment_check(self):
        env = _env(role="admin", staff_id="")
        self.assertIsNone(require_staff_assignment(env))

    def test_assigned_staff_passes_require(self):
        set_staff_assignment("S1", [10])
        env = _env(role="staff", staff_id="S1")
        self.assertIsNone(require_staff_assignment(env))

    def test_assigned_staff_passes_provider_specific_require(self):
        set_staff_assignment("S1", [10])
        env = _env(role="staff", staff_id="S1")
        self.assertIsNone(require_staff_assignment(env, provider_id=10))

    def test_get_staff_assigned_providers_returns_frozenset(self):
        set_staff_assignment("S2", [5, 7])
        result = get_staff_assigned_providers("S2")
        self.assertIn(5, result)
        self.assertIn(7, result)

    # ── Negative cases ────────────────────────────────────────────────────

    def test_unassigned_staff_blocked(self):
        env = _env(role="staff", staff_id="S_UNASSIGNED")
        result = require_staff_assignment(env)
        self.assertIsNotNone(result)
        role, msg = result
        self.assertEqual(role, "staff")
        self.assertIn("no active assignment", msg)

    def test_missing_staff_id_blocked(self):
        env = _env(role="staff", staff_id="")
        result = require_staff_assignment(env)
        self.assertIsNotNone(result)

    def test_cross_provider_access_denied(self):
        """Staff assigned to provider 10 must not access provider 99."""
        set_staff_assignment("S1", [10])
        env = _env(role="staff", staff_id="S1")
        result = require_staff_assignment(env, provider_id=99)
        self.assertIsNotNone(result)
        _, msg = result
        self.assertIn("99", msg)

    def test_patient_role_denied_staff_operations(self):
        env = _env(role="patient", staff_id="")
        result = require_staff_assignment(env)
        self.assertIsNotNone(result)
        role, msg = result
        self.assertEqual(role, "patient")

    def test_unassigned_staff_has_empty_providers(self):
        self.assertEqual(get_staff_assigned_providers("GHOST"), frozenset())

    def test_check_staff_assignment_none_staff_id(self):
        self.assertFalse(check_staff_assignment(None))

    def test_denial_is_audited(self):
        env = _env(role="staff", staff_id="S_UNASSIGNED")
        require_staff_assignment(env)
        self.assertEqual(len(_AUDIT_LOG), 1)
        self.assertEqual(_AUDIT_LOG[0]["action"], "staff:assignment_required")
        self.assertEqual(_AUDIT_LOG[0]["outcome"], "denied")

    def test_cross_provider_denial_is_audited(self):
        set_staff_assignment("S1", [10])
        env = _env(role="staff", staff_id="S1")
        require_staff_assignment(env, provider_id=99)
        self.assertEqual(len(_AUDIT_LOG), 1)
        self.assertEqual(_AUDIT_LOG[0]["action"], "staff:assignment_required")


# ---------------------------------------------------------------------------
# task_045_002: Minimum-necessary patient detail — unit tests
# ---------------------------------------------------------------------------

class MinimumNecessaryDetailTests(unittest.TestCase):

    _FULL_PROFILE = {
        "id": 1,
        "first_name": "Alice",
        "last_name": "Smith",
        "email": "alice@example.com",
        "phone": "555-1234",
        "preferred_timezone": "America/Chicago",
        "reminder_channels": '["sms","email"]',
        "do_not_disturb": 0,
        "patient_email": "alice@example.com",
        "patient_phone": "555-1234",
        "patient_notes": "Allergic to penicillin",
        "created_at": "2025-01-01T00:00:00+00:00",
    }

    def test_excluded_fields_are_absent(self):
        filtered = filter_staff_patient_detail(self._FULL_PROFILE)
        for field in _STAFF_EXCLUDED_PATIENT_FIELDS:
            self.assertNotIn(field, filtered, f"Field '{field}' should be excluded")

    def test_operational_fields_are_present(self):
        filtered = filter_staff_patient_detail(self._FULL_PROFILE)
        for field in ("id", "first_name", "last_name", "preferred_timezone", "created_at"):
            self.assertIn(field, filtered, f"Field '{field}' should be present")

    def test_filter_does_not_mutate_original(self):
        original = dict(self._FULL_PROFILE)
        filter_staff_patient_detail(original)
        self.assertEqual(original, self._FULL_PROFILE)

    def test_filter_handles_empty_dict(self):
        self.assertEqual(filter_staff_patient_detail({}), {})

    def test_filter_passes_through_unknown_fields(self):
        data = {"appointment_id": 42, "start_time": "09:00"}
        result = filter_staff_patient_detail(data)
        self.assertEqual(result, data)


# ---------------------------------------------------------------------------
# task_045_003: Staff access action logging — unit tests
# ---------------------------------------------------------------------------

class StaffAccessLoggingTests(unittest.TestCase):

    def setUp(self):
        _STAFF_ACCESS_LOG.clear()

    def test_log_entry_is_recorded(self):
        log_staff_access_event("S1", "staff:queue_view", 10, "/api/staff/queue")
        self.assertEqual(len(_STAFF_ACCESS_LOG), 1)

    def test_log_entry_fields(self):
        log_staff_access_event("S1", "staff:checkin", 10, "/api/staff/appointments/5/checkin")
        entry = _STAFF_ACCESS_LOG[0]
        self.assertEqual(entry["staff_id"], "S1")
        self.assertEqual(entry["action"], "staff:checkin")
        self.assertEqual(entry["provider_id"], 10)
        self.assertEqual(entry["resource"], "/api/staff/appointments/5/checkin")
        self.assertEqual(entry["outcome"], "success")
        self.assertIn("timestamp", entry)

    def test_denied_outcome_is_recorded(self):
        log_staff_access_event("S1", "staff:checkin", 99, "/api/staff/appointments/5/checkin", outcome="denied")
        self.assertEqual(_STAFF_ACCESS_LOG[0]["outcome"], "denied")

    def test_get_staff_access_log_newest_first(self):
        log_staff_access_event("S1", "staff:queue_view", 10, "/first")
        log_staff_access_event("S2", "staff:checkin", 20, "/second")
        log = get_staff_access_log(limit=10)
        self.assertEqual(log[0]["resource"], "/second")
        self.assertEqual(log[1]["resource"], "/first")

    def test_get_staff_access_log_limit_respected(self):
        for i in range(10):
            log_staff_access_event("S1", "staff:queue_view", i, f"/r{i}")
        log = get_staff_access_log(limit=3)
        self.assertEqual(len(log), 3)

    def test_get_staff_id_from_environ(self):
        env = {"HTTP_X_STAFF_ID": "  S42  "}
        self.assertEqual(get_staff_id_from_environ(env), "S42")

    def test_get_staff_id_missing_returns_none(self):
        self.assertIsNone(get_staff_id_from_environ({}))

    def test_get_staff_id_empty_returns_none(self):
        self.assertIsNone(get_staff_id_from_environ({"HTTP_X_STAFF_ID": "   "}))


# ---------------------------------------------------------------------------
# task_045_004: API integration — 403 enforcement via web_app dispatcher
# ---------------------------------------------------------------------------

class StaffQueueApiTests(unittest.TestCase):
    """Full stack WSGI tests covering assignment-based 403 enforcement."""

    def setUp(self):
        _AUDIT_LOG.clear()
        _STAFF_ACCESS_LOG.clear()
        _STAFF_ASSIGNMENTS.clear()
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        db_path = Path(self.tmp.name) / "test.db"
        from src.db import initialize_database
        initialize_database(db_path)
        from src.web_app import create_app
        self.app = create_app(db_path)
        self.db_path = db_path

    def tearDown(self):
        self.tmp.cleanup()

    def _call(
        self,
        method: str,
        path: str,
        role: str = "staff",
        staff_id: str = "S1",
        patient_id: int = 1,
        body: bytes = b"",
    ) -> tuple[int, dict]:
        responses: list[str] = []

        def start_response(status, headers):
            responses.append(status)

        environ = {
            "REQUEST_METHOD": method,
            "PATH_INFO": path,
            "QUERY_STRING": "",
            "HTTP_X_ROLE": role,
            "HTTP_X_STAFF_ID": staff_id,
            "HTTP_X_PATIENT_ID": str(patient_id),
            "wsgi.input": io.BytesIO(body),
            "CONTENT_LENGTH": str(len(body)),
        }
        result = self.app(environ, start_response)
        status_code = int(responses[0].split(" ", 1)[0])
        body_data = json.loads(b"".join(result).decode())
        return status_code, body_data

    # ── Assigned provider access ──────────────────────────────────────────

    def test_assigned_staff_can_access_queue(self):
        set_staff_assignment("S1", [1, 2])
        status, data = self._call("GET", "/api/staff/queue", role="staff", staff_id="S1")
        self.assertEqual(status, 200)
        self.assertTrue(data["success"])
        self.assertIn("items", data["data"])

    def test_assigned_staff_queue_logs_access(self):
        set_staff_assignment("S1", [1])
        self._call("GET", "/api/staff/queue", role="staff", staff_id="S1")
        log = get_staff_access_log()
        self.assertEqual(len(log), 1)
        self.assertEqual(log[0]["action"], "staff:queue_view")
        self.assertEqual(log[0]["staff_id"], "S1")

    def test_admin_can_access_queue_without_assignment(self):
        status, data = self._call("GET", "/api/staff/queue", role="admin", staff_id="")
        self.assertEqual(status, 200)
        self.assertTrue(data["success"])

    # ── Unassigned staff blocked ──────────────────────────────────────────

    def test_unassigned_staff_queue_returns_403(self):
        status, data = self._call("GET", "/api/staff/queue", role="staff", staff_id="UNASSIGNED")
        self.assertEqual(status, 403)
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["code"], "FORBIDDEN")

    def test_missing_staff_id_queue_returns_403(self):
        status, data = self._call("GET", "/api/staff/queue", role="staff", staff_id="")
        self.assertEqual(status, 403)

    def test_patient_role_queue_returns_403(self):
        """patients have no staff:queue_view permission."""
        status, data = self._call("GET", "/api/staff/queue", role="patient", staff_id="")
        self.assertEqual(status, 403)

    # ── Patient detail minimum-necessary ─────────────────────────────────

    def test_unassigned_staff_patient_detail_returns_403(self):
        status, data = self._call("GET", "/api/staff/patients/1/detail", role="staff", staff_id="UNASSIGNED")
        self.assertEqual(status, 403)

    def test_assigned_staff_patient_detail_excludes_sensitive_fields(self):
        set_staff_assignment("S1", [1])
        # Insert a patient profile so the endpoint returns data.
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO patient_profiles (id, first_name, last_name, email, phone, preferred_timezone) "
            "VALUES (1, 'Test', 'Patient', 'test@example.com', '555-0000', 'UTC')"
        )
        conn.commit()
        conn.close()

        status, data = self._call("GET", "/api/staff/patients/1/detail", role="staff", staff_id="S1")
        self.assertEqual(status, 200)
        profile = data["data"]
        for field in _STAFF_EXCLUDED_PATIENT_FIELDS:
            self.assertNotIn(field, profile, f"Sensitive field '{field}' must not appear in staff response")

    def test_admin_patient_detail_includes_all_fields(self):
        """Admin role skips minimum-necessary filtering."""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO patient_profiles (id, first_name, last_name, email, phone, preferred_timezone, "
            "reminder_channels, do_not_disturb) VALUES (1,'A','B','a@b.com','111','UTC','[\"sms\"]',0)"
        )
        conn.commit()
        conn.close()

        status, data = self._call("GET", "/api/staff/patients/1/detail", role="admin", staff_id="")
        self.assertEqual(status, 200)
        # Admin sees all fields — reminder_channels is present.
        self.assertIn("reminder_channels", data["data"])

    # ── Check-in cross-provider enforcement ──────────────────────────────

    def test_checkin_denied_for_wrong_provider(self):
        """Staff assigned only to provider 1 must be blocked from provider 2's appointments."""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO specialties (id, name) VALUES (1, 'General')"
        )
        conn.execute(
            "INSERT INTO providers (id, name, credentials, specialty_id) VALUES (2, 'Dr. Other', 'MD', 1)"
        )
        conn.execute(
            "INSERT INTO appointments (id, provider_id, specialty_id, appointment_date, start_time, end_time, "
            "location, status) VALUES (99, 2, 1, '2025-01-01', '09:00', '09:30', 'Clinic B', 'booked')"
        )
        conn.commit()
        conn.close()

        set_staff_assignment("S1", [1])  # assigned to provider 1, NOT provider 2
        status, data = self._call(
            "POST", "/api/staff/appointments/99/checkin", role="staff", staff_id="S1"
        )
        self.assertEqual(status, 403)
        self.assertEqual(data["error"]["code"], "FORBIDDEN")

    def test_checkin_denied_outcome_is_logged(self):
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        conn.execute("INSERT INTO specialties (id, name) VALUES (1, 'General')")
        conn.execute(
            "INSERT INTO providers (id, name, credentials, specialty_id) VALUES (2,'Dr. X','MD',1)"
        )
        conn.execute(
            "INSERT INTO appointments (id, provider_id, specialty_id, appointment_date, start_time, "
            "end_time, location, status) VALUES (88, 2, 1, '2025-01-01', '08:00', '08:30', 'X', 'booked')"
        )
        conn.commit()
        conn.close()

        set_staff_assignment("S1", [1])
        self._call("POST", "/api/staff/appointments/88/checkin", role="staff", staff_id="S1")
        log = get_staff_access_log()
        self.assertTrue(any(e["outcome"] == "denied" for e in log))

    def test_assigned_staff_checkin_succeeds(self):
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        conn.execute("INSERT INTO specialties (id, name) VALUES (1, 'General')")
        conn.execute(
            "INSERT INTO providers (id, name, credentials, specialty_id) VALUES (5,'Dr. Y','MD',1)"
        )
        conn.execute(
            "INSERT INTO appointments (id, provider_id, specialty_id, appointment_date, start_time, "
            "end_time, location, status) VALUES (77, 5, 1, '2025-01-01', '10:00', '10:30', 'Y', 'booked')"
        )
        conn.commit()
        conn.close()

        set_staff_assignment("S1", [5])
        status, data = self._call("POST", "/api/staff/appointments/77/checkin", role="staff", staff_id="S1")
        self.assertEqual(status, 200)
        self.assertTrue(data["data"]["checkedIn"])

    # ── Access-log endpoint ───────────────────────────────────────────────

    def test_staff_access_log_requires_admin(self):
        status, data = self._call("GET", "/api/staff/access-log", role="staff", staff_id="S1")
        self.assertEqual(status, 403)

    def test_admin_can_view_staff_access_log(self):
        log_staff_access_event("S1", "staff:queue_view", 10, "/api/staff/queue")
        status, data = self._call("GET", "/api/staff/access-log", role="admin", staff_id="")
        self.assertEqual(status, 200)
        self.assertEqual(len(data["data"]), 1)


if __name__ == "__main__":
    unittest.main()
