"""
EP-005 US-044: Patient Role Permission Boundary Tests (task_044_004)

Covers:
  task_044_001 — Patient appointment ownership filtering
  task_044_002 — Patient profile/intake ownership enforcement
  task_044_003 — Patient dashboard data surface restriction (via canPerform)
  task_044_004 — Full role-access matrix (positive + negative)
"""
from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path

from src.rbac import (
    _AUDIT_LOG,
    check_appointment_ownership,
    check_resource_scope,
    get_patient_id_from_environ,
    require_appointment_ownership,
    require_resource_scope,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _env(role: str = "patient", patient_id: int = 1, path: str = "/api/test", method: str = "GET") -> dict:
    return {
        "HTTP_X_ROLE": role,
        "HTTP_X_PATIENT_ID": str(patient_id),
        "PATH_INFO": path,
        "REQUEST_METHOD": method,
    }


def _make_appointment(status: str = "available", checkout: str = "searching") -> dict:
    return {
        "id": 42,
        "status": status,
        "checkout_status": checkout,
        "patient_first_name": "Alex",
        "patient_email": "alex@example.com",
    }


# ---------------------------------------------------------------------------
# task_044_001: Appointment ownership unit tests
# ---------------------------------------------------------------------------

class AppointmentOwnershipTests(unittest.TestCase):

    def setUp(self):
        _AUDIT_LOG.clear()

    # ── Positive cases ────────────────────────────────────────────────────

    def test_admin_can_view_any_booked_appointment(self):
        appt = _make_appointment(status="booked", checkout="confirmed")
        self.assertTrue(check_appointment_ownership("admin", 99, appt, owner_patient_id=1))

    def test_staff_can_view_any_booked_appointment(self):
        appt = _make_appointment(status="booked", checkout="confirmed")
        self.assertTrue(check_appointment_ownership("staff", 99, appt, owner_patient_id=1))

    def test_patient_can_view_available_slot(self):
        appt = _make_appointment(status="available", checkout="searching")
        self.assertTrue(check_appointment_ownership("patient", 1, appt, owner_patient_id=1))

    def test_patient_can_view_own_booked_appointment(self):
        appt = _make_appointment(status="booked", checkout="confirmed")
        self.assertTrue(check_appointment_ownership("patient", 1, appt, owner_patient_id=1))

    # ── Negative cases ────────────────────────────────────────────────────

    def test_patient_denied_other_patients_booked_appointment(self):
        appt = _make_appointment(status="booked", checkout="confirmed")
        self.assertFalse(check_appointment_ownership("patient", 99, appt, owner_patient_id=1))

    def test_patient_denied_reserved_slot_belonging_to_other(self):
        appt = _make_appointment(status="available", checkout="reserved")
        self.assertFalse(check_appointment_ownership("patient", 99, appt, owner_patient_id=1))

    def test_patient_denied_confirmed_slot_of_other(self):
        appt = _make_appointment(status="available", checkout="confirmed")
        self.assertFalse(check_appointment_ownership("patient", 99, appt, owner_patient_id=1))

    def test_require_appointment_ownership_allowed_returns_none(self):
        env = _env(role="patient", patient_id=1)
        appt = _make_appointment(status="booked", checkout="confirmed")
        self.assertIsNone(require_appointment_ownership(env, appt, owner_patient_id=1))

    def test_require_appointment_ownership_denied_returns_tuple(self):
        env = _env(role="patient", patient_id=99)
        appt = _make_appointment(status="booked", checkout="confirmed")
        result = require_appointment_ownership(env, appt, owner_patient_id=1)
        self.assertIsNotNone(result)
        role, msg = result
        self.assertEqual(role, "patient")
        self.assertIn("patients may only view their own", msg)

    def test_ownership_denial_is_audited(self):
        env = _env(role="patient", patient_id=99)
        appt = _make_appointment(status="booked", checkout="confirmed")
        require_appointment_ownership(env, appt, owner_patient_id=1)
        self.assertEqual(len(_AUDIT_LOG), 1)
        self.assertEqual(_AUDIT_LOG[0]["action"], "appointments:ownership")
        self.assertEqual(_AUDIT_LOG[0]["outcome"], "denied")


# ---------------------------------------------------------------------------
# task_044_002: Profile/intake ownership unit tests
# ---------------------------------------------------------------------------

class ProfileOwnershipTests(unittest.TestCase):

    def setUp(self):
        _AUDIT_LOG.clear()

    def test_patient_own_profile_allowed(self):
        env = _env(role="patient", patient_id=1)
        self.assertIsNone(require_resource_scope(env, resource_patient_id=1))

    def test_patient_other_profile_denied(self):
        env = _env(role="patient", patient_id=99)
        result = require_resource_scope(env, resource_patient_id=1)
        self.assertIsNotNone(result)

    def test_staff_can_view_any_profile(self):
        env = _env(role="staff", patient_id=99)
        self.assertIsNone(require_resource_scope(env, resource_patient_id=1))

    def test_admin_can_view_any_profile(self):
        env = _env(role="admin", patient_id=0)
        self.assertIsNone(require_resource_scope(env, resource_patient_id=1))

    def test_patient_profile_denial_logged(self):
        env = _env(role="patient", patient_id=99)
        require_resource_scope(env, resource_patient_id=1)
        self.assertEqual(len(_AUDIT_LOG), 1)
        self.assertEqual(_AUDIT_LOG[0]["role"], "patient")
        self.assertEqual(_AUDIT_LOG[0]["outcome"], "denied")

    def test_get_patient_id_from_environ_parses_header(self):
        env = {"HTTP_X_PATIENT_ID": "5"}
        self.assertEqual(get_patient_id_from_environ(env), 5)

    def test_get_patient_id_from_environ_defaults_to_zero(self):
        self.assertEqual(get_patient_id_from_environ({}), 0)

    def test_get_patient_id_invalid_header_returns_zero(self):
        env = {"HTTP_X_PATIENT_ID": "not-a-number"}
        self.assertEqual(get_patient_id_from_environ(env), 0)


# ---------------------------------------------------------------------------
# task_044_004: API-level 403 enforcement (positive + negative matrix)
# ---------------------------------------------------------------------------

class PatientBoundaryApiTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        db_path = Path(self.tmp.name) / "test.db"
        from src.db import initialize_database
        initialize_database(db_path)
        from src.web_app import create_app
        self.app = create_app(db_path)
        _AUDIT_LOG.clear()

    def tearDown(self):
        self.tmp.cleanup()

    def _call(self, method: str, path: str, role: str = "patient",
              patient_id: int = 1, body: bytes = b"", qs: str = "") -> tuple[int, dict]:
        responses = []

        def start_response(status, headers):
            responses.append(status)

        environ = {
            "REQUEST_METHOD": method,
            "PATH_INFO": path,
            "QUERY_STRING": qs,
            "HTTP_X_ROLE": role,
            "HTTP_X_PATIENT_ID": str(patient_id),
            "wsgi.input": io.BytesIO(body),
            "CONTENT_LENGTH": str(len(body)),
            "CONTENT_TYPE": "application/json",
        }
        result = self.app(environ, start_response)
        status_code = int(responses[0].split(" ", 1)[0])
        payload = json.loads(b"".join(result))
        return status_code, payload

    # ── Positive: patient accesses own resources ──────────────────────────

    def test_patient_own_profile_allowed(self):
        status, _ = self._call("GET", "/api/patient/profile", role="patient", patient_id=1)
        self.assertNotEqual(status, 403)

    def test_patient_search_appointments_allowed(self):
        status, _ = self._call("GET", "/api/appointments/search", role="patient", patient_id=1)
        self.assertNotEqual(status, 403)

    def test_patient_integrations_status_own_allowed(self):
        status, _ = self._call("GET", "/api/integrations/status", role="patient", patient_id=1)
        self.assertNotEqual(status, 403)

    def test_patient_can_view_available_appointment(self):
        # All seeded appointments are 'available'; patient with id=1 should see them
        status, _ = self._call("GET", "/api/appointments/1", role="patient", patient_id=1)
        # Either 200 (found) or 404 (slot not seeded), but NOT 403
        self.assertNotEqual(status, 403)

    # ── Negative: patient accessing other patient's resources ─────────────

    def test_patient_cross_profile_denied(self):
        # patient_id=99 tries to access patient profile (owned by patient 1)
        status, data = self._call("GET", "/api/patient/profile", role="patient", patient_id=99)
        self.assertEqual(status, 403)
        self.assertEqual(data["error"]["code"], "FORBIDDEN")

    def test_patient_cross_integrations_denied(self):
        status, data = self._call("GET", "/api/integrations/status", role="patient", patient_id=99)
        self.assertEqual(status, 403)
        self.assertEqual(data["error"]["code"], "FORBIDDEN")

    def test_patient_denied_clinical_profile(self):
        status, data = self._call("GET", "/api/clinical/patients/1/profile", role="patient", patient_id=1)
        self.assertEqual(status, 403)

    def test_patient_denied_ops_jobs(self):
        for path in [
            "/api/jobs/process-confirmations",
            "/api/jobs/process-reminders",
            "/api/jobs/process-swaps",
            "/api/jobs/process-calendar-sync",
        ]:
            with self.subTest(path=path):
                status, _ = self._call("POST", path, role="patient", patient_id=1)
                self.assertEqual(status, 403)

    def test_patient_denied_dashboard(self):
        status, _ = self._call("GET", "/api/dashboard/metrics", role="patient", patient_id=1)
        self.assertEqual(status, 403)

    def test_all_denied_attempts_return_standardized_403(self):
        """All unauthorized attempts must return {"success": False, "error": {"code": "FORBIDDEN"}}."""
        denied_cases = [
            ("GET",  "/api/dashboard/metrics"),
            ("POST", "/api/jobs/process-confirmations"),
            ("GET",  "/api/clinical/patients/1/profile"),
            ("PUT",  "/api/clinical/thresholds"),
        ]
        for method, path in denied_cases:
            with self.subTest(method=method, path=path):
                status, data = self._call(method, path, role="patient", patient_id=1)
                self.assertEqual(status, 403, f"{method} {path} should be 403")
                self.assertFalse(data.get("success"), f"{method} {path}: success should be False")
                self.assertEqual(data.get("error", {}).get("code"), "FORBIDDEN")

    # ── Staff can access patient-level resources ───────────────────────────

    def test_staff_can_access_patient_profile(self):
        status, _ = self._call("GET", "/api/patient/profile", role="staff", patient_id=99)
        self.assertNotEqual(status, 403)

    def test_staff_can_access_clinical_profile(self):
        status, _ = self._call("GET", "/api/clinical/patients/1/profile", role="staff", patient_id=99)
        self.assertNotEqual(status, 403)

    # ── Admin can access all resources ────────────────────────────────────

    def test_admin_can_access_all_protected_endpoints(self):
        cases = [
            ("GET",  "/api/dashboard/metrics"),
            ("GET",  "/api/patient/profile"),
            ("GET",  "/api/integrations/status"),
        ]
        for method, path in cases:
            with self.subTest(method=method, path=path):
                status, _ = self._call(method, path, role="admin", patient_id=1)
                self.assertNotEqual(status, 403, f"Admin should not get 403 on {method} {path}")

    def test_denied_events_are_logged_and_queryable(self):
        from src.rbac import get_audit_log
        self._call("GET", "/api/dashboard/metrics", role="patient", patient_id=1)
        self._call("GET", "/api/patient/profile", role="patient", patient_id=99)
        log = get_audit_log()
        roles_in_log = {e["role"] for e in log}
        self.assertIn("patient", roles_in_log)
        outcomes = {e["outcome"] for e in log}
        self.assertEqual(outcomes, {"denied"})


if __name__ == "__main__":
    unittest.main()
