"""
EP-005 US-043: RBAC End-to-End Test Suite (task_043_005)

Covers:
  - Role allow/deny matrix for all defined actions
  - Ownership and assignment scoping rules
  - Audit log population on denied events
  - API-level 403 responses via web_app dispatcher
"""
from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path

from src.rbac import (
    PERMISSION_MATRIX,
    ROLES,
    _AUDIT_LOG,
    check_permission,
    check_resource_scope,
    get_audit_log,
    get_permission_matrix,
    get_role_from_environ,
    log_denied_event,
    require_permission,
    require_resource_scope,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_environ(role: str = "patient", patient_id: int = 1, path: str = "/api/test", method: str = "GET") -> dict:
    return {
        "HTTP_X_ROLE": role,
        "HTTP_X_PATIENT_ID": str(patient_id),
        "PATH_INFO": path,
        "REQUEST_METHOD": method,
    }


# ---------------------------------------------------------------------------
# task_043_001: Permission Matrix Tests
# ---------------------------------------------------------------------------

class PermissionMatrixTests(unittest.TestCase):

    def test_matrix_covers_all_roles(self):
        for action, roles in PERMISSION_MATRIX.items():
            for role in roles:
                self.assertIn(role, ROLES, f"Unknown role '{role}' in action '{action}'")

    def test_patient_allowed_appointment_search(self):
        self.assertTrue(check_permission("patient", "appointments:search"))

    def test_patient_allowed_book(self):
        self.assertTrue(check_permission("patient", "appointments:book"))

    def test_patient_denied_dashboard(self):
        self.assertFalse(check_permission("patient", "admin:dashboard"))

    def test_patient_denied_clinical_view_profile(self):
        self.assertFalse(check_permission("patient", "clinical:view_profile"))

    def test_patient_denied_manage_thresholds(self):
        self.assertFalse(check_permission("patient", "clinical:manage_thresholds"))

    def test_staff_allowed_clinical_view_profile(self):
        self.assertTrue(check_permission("staff", "clinical:view_profile"))

    def test_staff_allowed_code_review(self):
        self.assertTrue(check_permission("staff", "clinical:code_review"))

    def test_staff_denied_manage_thresholds(self):
        self.assertFalse(check_permission("staff", "clinical:manage_thresholds"))

    def test_staff_denied_dashboard(self):
        self.assertFalse(check_permission("staff", "admin:dashboard"))

    def test_admin_allowed_manage_thresholds(self):
        self.assertTrue(check_permission("admin", "clinical:manage_thresholds"))

    def test_admin_allowed_dashboard(self):
        self.assertTrue(check_permission("admin", "admin:dashboard"))

    def test_admin_allowed_ops_jobs(self):
        self.assertTrue(check_permission("admin", "admin:ops_jobs"))

    def test_unknown_role_denied_everything(self):
        self.assertFalse(check_permission("superuser", "appointments:search"))

    def test_unknown_action_denied_for_all_roles(self):
        for role in ROLES:
            self.assertFalse(check_permission(role, "nonexistent:action"))

    def test_get_permission_matrix_serialisable(self):
        matrix = get_permission_matrix()
        self.assertIsInstance(matrix, dict)
        # Every value is a list of strings (JSON-serialisable)
        for action, roles in matrix.items():
            self.assertIsInstance(roles, list)
            self.assertTrue(all(isinstance(r, str) for r in roles))


# ---------------------------------------------------------------------------
# task_043_002: Authorization Middleware Tests
# ---------------------------------------------------------------------------

class AuthorizationMiddlewareTests(unittest.TestCase):

    def setUp(self):
        _AUDIT_LOG.clear()

    def test_allowed_returns_none(self):
        env = _make_environ(role="admin", path="/api/dashboard/metrics", method="GET")
        self.assertIsNone(require_permission(env, "admin:dashboard"))

    def test_denied_returns_tuple(self):
        env = _make_environ(role="patient", path="/api/dashboard/metrics", method="GET")
        result = require_permission(env, "admin:dashboard")
        self.assertIsNotNone(result)
        role, msg = result
        self.assertEqual(role, "patient")
        self.assertIn("patient", msg)

    def test_denied_logs_audit_entry(self):
        env = _make_environ(role="patient", path="/api/dashboard/metrics", method="GET")
        require_permission(env, "admin:dashboard")
        self.assertEqual(len(_AUDIT_LOG), 1)
        entry = _AUDIT_LOG[0]
        self.assertEqual(entry["role"], "patient")
        self.assertEqual(entry["action"], "admin:dashboard")
        self.assertEqual(entry["outcome"], "denied")

    def test_unknown_role_falls_back_to_patient(self):
        env = _make_environ(role="ghost")
        self.assertEqual(get_role_from_environ(env), "patient")

    def test_missing_role_header_falls_back_to_patient(self):
        env = {}
        self.assertEqual(get_role_from_environ(env), "patient")

    def test_role_header_case_insensitive(self):
        env = {"HTTP_X_ROLE": "ADMIN"}
        self.assertEqual(get_role_from_environ(env), "admin")

    def test_staff_denied_ops_returns_message(self):
        env = _make_environ(role="staff", path="/api/jobs/process-confirmations", method="POST")
        result = require_permission(env, "admin:ops_jobs")
        self.assertIsNotNone(result)
        _, msg = result
        self.assertIn("staff", msg)

    def test_get_audit_log_returns_newest_first(self):
        log_denied_event("patient", "admin:dashboard", "/api/dashboard/metrics", "GET")
        log_denied_event("staff", "clinical:manage_thresholds", "/api/clinical/thresholds", "PUT")
        log = get_audit_log(limit=10)
        self.assertEqual(log[0]["role"], "staff")
        self.assertEqual(log[1]["role"], "patient")

    def test_audit_log_limit_respected(self):
        for i in range(10):
            log_denied_event("patient", "admin:dashboard", "/api/test", "GET")
        log = get_audit_log(limit=3)
        self.assertEqual(len(log), 3)


# ---------------------------------------------------------------------------
# task_043_003: Ownership & Scoping Tests
# ---------------------------------------------------------------------------

class OwnershipScopingTests(unittest.TestCase):

    def setUp(self):
        _AUDIT_LOG.clear()

    def test_admin_can_access_any_patient(self):
        self.assertTrue(check_resource_scope("admin", requesting_patient_id=1, resource_patient_id=99))

    def test_staff_can_access_any_patient(self):
        self.assertTrue(check_resource_scope("staff", requesting_patient_id=1, resource_patient_id=99))

    def test_patient_can_access_own_record(self):
        self.assertTrue(check_resource_scope("patient", requesting_patient_id=5, resource_patient_id=5))

    def test_patient_denied_other_patient_record(self):
        self.assertFalse(check_resource_scope("patient", requesting_patient_id=5, resource_patient_id=6))

    def test_patient_denied_when_no_id_supplied(self):
        self.assertFalse(check_resource_scope("patient", requesting_patient_id=None, resource_patient_id=5))

    def test_require_resource_scope_admin_passes(self):
        env = _make_environ(role="admin", patient_id=1)
        self.assertIsNone(require_resource_scope(env, resource_patient_id=99))

    def test_require_resource_scope_patient_own_record_passes(self):
        env = _make_environ(role="patient", patient_id=5)
        self.assertIsNone(require_resource_scope(env, resource_patient_id=5))

    def test_require_resource_scope_patient_other_record_denied(self):
        env = _make_environ(role="patient", patient_id=5)
        result = require_resource_scope(env, resource_patient_id=99)
        self.assertIsNotNone(result)

    def test_scope_denial_is_audited(self):
        env = _make_environ(role="patient", patient_id=5)
        require_resource_scope(env, resource_patient_id=99)
        self.assertEqual(len(_AUDIT_LOG), 1)
        self.assertEqual(_AUDIT_LOG[0]["action"], "resource:scope")


# ---------------------------------------------------------------------------
# task_043_005: API Integration (403 enforcement) Tests
# ---------------------------------------------------------------------------

class RbacApiIntegrationTests(unittest.TestCase):
    """
    Call the web_app WSGI dispatcher directly and assert RBAC enforcement.
    Skips the zoneinfo import path by importing web_app lazily inside test.
    """

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
              patient_id: int = 1, body: bytes = b"") -> tuple[int, dict]:
        responses = []

        def start_response(status, headers):
            responses.append(status)

        environ = {
            "REQUEST_METHOD": method,
            "PATH_INFO": path,
            "QUERY_STRING": "",
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

    def test_patient_can_search_appointments(self):
        status, data = self._call("GET", "/api/appointments/search", role="patient")
        self.assertNotEqual(status, 403)

    def test_patient_denied_dashboard(self):
        status, data = self._call("GET", "/api/dashboard/metrics", role="patient")
        self.assertEqual(status, 403)
        self.assertEqual(data["error"]["code"], "FORBIDDEN")

    def test_admin_allowed_dashboard(self):
        status, data = self._call("GET", "/api/dashboard/metrics", role="admin")
        self.assertNotEqual(status, 403)

    def test_patient_denied_ops_jobs(self):
        status, data = self._call("POST", "/api/jobs/process-confirmations", role="patient")
        self.assertEqual(status, 403)

    def test_staff_denied_ops_jobs(self):
        status, data = self._call("POST", "/api/jobs/process-reminders", role="staff")
        self.assertEqual(status, 403)

    def test_admin_allowed_ops_jobs(self):
        status, _ = self._call("POST", "/api/jobs/process-reminders", role="admin")
        self.assertNotEqual(status, 403)

    def test_patient_denied_clinical_profile(self):
        status, data = self._call("GET", "/api/clinical/patients/1/profile", role="patient")
        self.assertEqual(status, 403)

    def test_staff_allowed_clinical_profile(self):
        status, _ = self._call("GET", "/api/clinical/patients/1/profile", role="staff")
        self.assertNotEqual(status, 403)

    def test_staff_denied_manage_thresholds(self):
        body = json.dumps({"codeType": "icd10", "thresholdValue": 0.8, "updatedBy": "s1", "role": "staff"}).encode()
        status, data = self._call("PUT", "/api/clinical/thresholds", role="staff", body=body)
        self.assertEqual(status, 403)

    def test_admin_allowed_manage_thresholds(self):
        body = json.dumps({"codeType": "icd10", "thresholdValue": 0.8, "updatedBy": "a1", "role": "admin"}).encode()
        status, _ = self._call("PUT", "/api/clinical/thresholds", role="admin", body=body)
        self.assertNotEqual(status, 403)

    def test_denied_events_queryable_via_audit_log(self):
        self._call("GET", "/api/dashboard/metrics", role="patient")
        self._call("GET", "/api/dashboard/metrics", role="staff")
        log = get_audit_log()
        denied_roles = {e["role"] for e in log if e["endpoint"] == "/api/dashboard/metrics"}
        self.assertIn("patient", denied_roles)
        self.assertIn("staff", denied_roles)

    def test_rbac_me_returns_role_and_permissions(self):
        status, data = self._call("GET", "/api/auth/me", role="staff")
        self.assertEqual(status, 200)
        self.assertEqual(data["data"]["role"], "staff")
        self.assertIn("clinical:view_profile", data["data"]["permissions"])

    def test_rbac_permissions_endpoint_staff_allowed(self):
        status, _ = self._call("GET", "/api/rbac/permissions", role="staff")
        self.assertNotEqual(status, 403)

    def test_rbac_permissions_endpoint_patient_denied(self):
        status, data = self._call("GET", "/api/rbac/permissions", role="patient")
        self.assertEqual(status, 403)

    def test_no_critical_bypass_path_for_patient(self):
        """Patient must not be able to reach any admin or clinical action."""
        protected = [
            ("GET",  "/api/dashboard/metrics"),
            ("POST", "/api/jobs/process-confirmations"),
            ("POST", "/api/jobs/process-reminders"),
            ("GET",  "/api/clinical/patients/1/profile"),
            ("POST", "/api/clinical/documents/upload"),
            ("PUT",  "/api/clinical/thresholds"),
        ]
        for method, path in protected:
            with self.subTest(method=method, path=path):
                status, _ = self._call(method, path, role="patient")
                self.assertEqual(status, 403, f"Expected 403 for patient on {method} {path}")


if __name__ == "__main__":
    unittest.main()
