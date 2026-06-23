"""
EP-005 US-046: Admin Role Boundaries and Compliance Validation (task_046_004)

Covers:
  task_046_001 — Admin-only access for management endpoints
  task_046_002 — Role and user status change operations with audit metadata
  task_046_003 — Admin audit log read-only access with filters
  task_046_004 — Full admin role boundary and compliance validation
"""
from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path

from src.rbac import (
    _ADMIN_CHANGE_LOG,
    _AUDIT_LOG,
    _USER_REGISTRY,
    ROLES,
    VALID_STATUSES,
    assign_user_role,
    check_permission,
    get_admin_change_log,
    get_admin_id_from_environ,
    get_user,
    list_users,
    register_user,
    set_user_status,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _env(
    role: str = "admin",
    admin_id: str = "A1",
    path: str = "/api/admin/users",
    method: str = "GET",
) -> dict:
    return {
        "HTTP_X_ROLE": role,
        "HTTP_X_ADMIN_ID": admin_id,
        "PATH_INFO": path,
        "REQUEST_METHOD": method,
    }


def _setup_registry():
    """Seed the user registry with test users."""
    register_user("U1", "staff", "u1@clinic.com")
    register_user("U2", "patient", "u2@example.com")
    register_user("U3", "admin", "u3@clinic.com")


# ---------------------------------------------------------------------------
# task_046_001: Admin-only permission matrix checks
# ---------------------------------------------------------------------------

class AdminPermissionMatrixTests(unittest.TestCase):

    def test_admin_has_user_management(self):
        self.assertTrue(check_permission("admin", "admin:user_management"))

    def test_admin_has_change_log(self):
        self.assertTrue(check_permission("admin", "admin:change_log"))

    def test_staff_denied_user_management(self):
        self.assertFalse(check_permission("staff", "admin:user_management"))

    def test_patient_denied_user_management(self):
        self.assertFalse(check_permission("patient", "admin:user_management"))

    def test_staff_denied_change_log(self):
        self.assertFalse(check_permission("staff", "admin:change_log"))

    def test_patient_denied_change_log(self):
        self.assertFalse(check_permission("patient", "admin:change_log"))

    def test_admin_retains_dashboard_permission(self):
        self.assertTrue(check_permission("admin", "admin:dashboard"))

    def test_admin_retains_ops_jobs_permission(self):
        self.assertTrue(check_permission("admin", "admin:ops_jobs"))


# ---------------------------------------------------------------------------
# task_046_002: User registry operations
# ---------------------------------------------------------------------------

class UserRegistryTests(unittest.TestCase):

    def setUp(self):
        _USER_REGISTRY.clear()
        _ADMIN_CHANGE_LOG.clear()

    def test_register_user_creates_record(self):
        user = register_user("U1", "staff", "u@clinic.com")
        self.assertEqual(user["id"], "U1")
        self.assertEqual(user["role"], "staff")
        self.assertEqual(user["status"], "active")

    def test_register_unknown_role_raises(self):
        with self.assertRaises(ValueError):
            register_user("U1", "superuser", "x@x.com")

    def test_register_unknown_status_raises(self):
        with self.assertRaises(ValueError):
            register_user("U1", "staff", "x@x.com", status="banned")

    def test_get_user_returns_record(self):
        register_user("U1", "patient", "p@p.com")
        user = get_user("U1")
        self.assertIsNotNone(user)
        self.assertEqual(user["role"], "patient")

    def test_get_user_missing_returns_none(self):
        self.assertIsNone(get_user("GHOST"))

    def test_list_users_returns_all(self):
        register_user("U1", "staff", "a@a.com")
        register_user("U2", "admin", "b@b.com")
        users = list_users()
        self.assertEqual(len(users), 2)

    def test_get_admin_id_from_environ(self):
        env = {"HTTP_X_ADMIN_ID": "  A99  "}
        self.assertEqual(get_admin_id_from_environ(env), "A99")

    def test_get_admin_id_missing_returns_none(self):
        self.assertIsNone(get_admin_id_from_environ({}))


# ---------------------------------------------------------------------------
# task_046_002: Role assignment with audit metadata
# ---------------------------------------------------------------------------

class RoleAssignmentTests(unittest.TestCase):

    def setUp(self):
        _USER_REGISTRY.clear()
        _ADMIN_CHANGE_LOG.clear()
        register_user("U1", "staff", "u1@clinic.com")

    def test_assign_valid_role_succeeds(self):
        success, msg = assign_user_role("A1", "U1", "admin", reason="Promotion")
        self.assertTrue(success)
        self.assertIn("admin", msg)
        self.assertEqual(get_user("U1")["role"], "admin")

    def test_assign_role_logs_change(self):
        assign_user_role("A1", "U1", "patient", reason="Demotion")
        self.assertEqual(len(_ADMIN_CHANGE_LOG), 1)
        entry = _ADMIN_CHANGE_LOG[0]
        self.assertEqual(entry["actor"], "A1")
        self.assertEqual(entry["action"], "admin:role_assigned")
        self.assertEqual(entry["target_user_id"], "U1")
        self.assertEqual(entry["previous_value"], "staff")
        self.assertEqual(entry["new_value"], "patient")
        self.assertEqual(entry["reason"], "Demotion")
        self.assertIn("timestamp", entry)

    def test_assign_unknown_role_fails(self):
        success, msg = assign_user_role("A1", "U1", "superuser")
        self.assertFalse(success)
        self.assertIn("Unknown role", msg)

    def test_assign_role_missing_user_fails(self):
        success, msg = assign_user_role("A1", "GHOST", "admin")
        self.assertFalse(success)
        self.assertIn("not found", msg)

    def test_all_valid_roles_assignable(self):
        for role in ROLES:
            ok, _ = assign_user_role("A1", "U1", role)
            self.assertTrue(ok, f"Expected role '{role}' to be assignable")


# ---------------------------------------------------------------------------
# task_046_002: Status change with audit metadata
# ---------------------------------------------------------------------------

class StatusChangeTests(unittest.TestCase):

    def setUp(self):
        _USER_REGISTRY.clear()
        _ADMIN_CHANGE_LOG.clear()
        register_user("U1", "staff", "u1@clinic.com", status="active")

    def test_deactivate_user_succeeds(self):
        success, msg = set_user_status("A1", "U1", "inactive", reason="Left org")
        self.assertTrue(success)
        self.assertEqual(get_user("U1")["status"], "inactive")

    def test_status_change_logs_entry(self):
        set_user_status("A1", "U1", "suspended", reason="Policy violation")
        self.assertEqual(len(_ADMIN_CHANGE_LOG), 1)
        entry = _ADMIN_CHANGE_LOG[0]
        self.assertEqual(entry["action"], "admin:status_changed")
        self.assertEqual(entry["previous_value"], "active")
        self.assertEqual(entry["new_value"], "suspended")
        self.assertEqual(entry["reason"], "Policy violation")

    def test_unknown_status_fails(self):
        success, msg = set_user_status("A1", "U1", "deleted")
        self.assertFalse(success)
        self.assertIn("Unknown status", msg)

    def test_status_change_missing_user_fails(self):
        success, msg = set_user_status("A1", "GHOST", "inactive")
        self.assertFalse(success)
        self.assertIn("not found", msg)

    def test_all_valid_statuses_assignable(self):
        for status in VALID_STATUSES:
            ok, _ = set_user_status("A1", "U1", status)
            self.assertTrue(ok, f"Expected status '{status}' to be settable")


# ---------------------------------------------------------------------------
# task_046_003: Admin change log filtering
# ---------------------------------------------------------------------------

class AdminChangeLogFilterTests(unittest.TestCase):

    def setUp(self):
        _USER_REGISTRY.clear()
        _ADMIN_CHANGE_LOG.clear()
        register_user("U1", "staff", "u@x.com")
        register_user("U2", "patient", "v@x.com")
        assign_user_role("A1", "U1", "admin", reason="r1")
        assign_user_role("A2", "U2", "staff", reason="r2")
        set_user_status("A1", "U1", "inactive", reason="r3")

    def test_unfiltered_returns_all_newest_first(self):
        log = get_admin_change_log()
        self.assertEqual(len(log), 3)
        # newest first — status change was last
        self.assertEqual(log[0]["action"], "admin:status_changed")

    def test_filter_by_actor(self):
        log = get_admin_change_log(actor="A1")
        self.assertTrue(all(e["actor"] == "A1" for e in log))
        self.assertEqual(len(log), 2)

    def test_filter_by_action(self):
        log = get_admin_change_log(action="admin:role_assigned")
        self.assertTrue(all(e["action"] == "admin:role_assigned" for e in log))
        self.assertEqual(len(log), 2)

    def test_filter_by_action_status(self):
        log = get_admin_change_log(action="admin:status_changed")
        self.assertEqual(len(log), 1)

    def test_limit_respected(self):
        log = get_admin_change_log(limit=1)
        self.assertEqual(len(log), 1)

    def test_from_ts_filter(self):
        # All entries are newer than epoch — should include all.
        log = get_admin_change_log(from_ts="2000-01-01T00:00:00+00:00")
        self.assertEqual(len(log), 3)

    def test_to_ts_filter_excludes_future_entries(self):
        # Nothing should be newer than the year 2000 from the past.
        log = get_admin_change_log(to_ts="2000-01-01T00:00:00+00:00")
        self.assertEqual(len(log), 0)

    def test_change_log_is_read_only_structure(self):
        """Returned list must not be the internal log object (mutation guard)."""
        log1 = get_admin_change_log()
        log1.clear()
        log2 = get_admin_change_log()
        self.assertEqual(len(log2), 3)


# ---------------------------------------------------------------------------
# task_046_004: API integration — 403 enforcement via web_app dispatcher
# ---------------------------------------------------------------------------

class AdminRoleApiTests(unittest.TestCase):
    """WSGI-level enforcement tests for admin-only management endpoints."""

    def setUp(self):
        _USER_REGISTRY.clear()
        _ADMIN_CHANGE_LOG.clear()
        _AUDIT_LOG.clear()
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        db_path = Path(self.tmp.name) / "test.db"
        from src.db import initialize_database
        initialize_database(db_path)
        from src.web_app import create_app
        self.app = create_app(db_path)

    def tearDown(self):
        self.tmp.cleanup()

    def _call(
        self,
        method: str,
        path: str,
        role: str = "admin",
        admin_id: str = "A1",
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
            "HTTP_X_ADMIN_ID": admin_id,
            "HTTP_X_PATIENT_ID": "1",
            "wsgi.input": io.BytesIO(body),
            "CONTENT_LENGTH": str(len(body)),
            "CONTENT_TYPE": "application/json",
        }
        result = self.app(environ, start_response)
        status_code = int(responses[0].split(" ", 1)[0])
        body_data = json.loads(b"".join(result).decode())
        return status_code, body_data

    # ── Admin allowed actions ──────────────────────────────────────────────

    def test_admin_can_list_users(self):
        register_user("U1", "staff", "u@x.com")
        status, data = self._call("GET", "/api/admin/users")
        self.assertEqual(status, 200)
        self.assertTrue(data["success"])
        self.assertEqual(len(data["data"]), 1)

    def test_admin_can_get_user(self):
        register_user("U9", "patient", "p@x.com")
        status, data = self._call("GET", "/api/admin/users/U9")
        self.assertEqual(status, 200)
        self.assertEqual(data["data"]["id"], "U9")

    def test_admin_get_unknown_user_returns_404(self):
        status, data = self._call("GET", "/api/admin/users/GHOST")
        self.assertEqual(status, 404)

    def test_admin_can_assign_role(self):
        register_user("U1", "staff", "u@x.com")
        body = json.dumps({"role": "admin", "reason": "Elevated"}).encode()
        status, data = self._call("PATCH", "/api/admin/users/U1/role", body=body)
        self.assertEqual(status, 200)
        self.assertEqual(get_user("U1")["role"], "admin")

    def test_admin_can_set_status(self):
        register_user("U2", "staff", "u2@x.com")
        body = json.dumps({"status": "inactive", "reason": "Left"}).encode()
        status, data = self._call("PATCH", "/api/admin/users/U2/status", body=body)
        self.assertEqual(status, 200)
        self.assertEqual(get_user("U2")["status"], "inactive")

    def test_admin_can_view_change_log(self):
        register_user("U1", "staff", "u@x.com")
        assign_user_role("A1", "U1", "admin")
        status, data = self._call("GET", "/api/admin/change-log")
        self.assertEqual(status, 200)
        self.assertEqual(len(data["data"]), 1)

    def test_role_change_missing_role_field_returns_400(self):
        register_user("U1", "staff", "u@x.com")
        body = json.dumps({"reason": "no role"}).encode()
        status, data = self._call("PATCH", "/api/admin/users/U1/role", body=body)
        self.assertEqual(status, 400)

    def test_status_change_missing_status_field_returns_400(self):
        register_user("U1", "staff", "u@x.com")
        body = json.dumps({"reason": "no status"}).encode()
        status, data = self._call("PATCH", "/api/admin/users/U1/status", body=body)
        self.assertEqual(status, 400)

    # ── Non-admin blocked from admin operations ───────────────────────────

    def test_staff_blocked_from_user_list(self):
        status, data = self._call("GET", "/api/admin/users", role="staff")
        self.assertEqual(status, 403)
        self.assertEqual(data["error"]["code"], "FORBIDDEN")

    def test_patient_blocked_from_user_list(self):
        status, data = self._call("GET", "/api/admin/users", role="patient")
        self.assertEqual(status, 403)

    def test_staff_blocked_from_role_assignment(self):
        register_user("U1", "patient", "u@x.com")
        body = json.dumps({"role": "staff"}).encode()
        status, data = self._call("PATCH", "/api/admin/users/U1/role", role="staff", body=body)
        self.assertEqual(status, 403)

    def test_patient_blocked_from_status_change(self):
        register_user("U1", "staff", "u@x.com")
        body = json.dumps({"status": "inactive"}).encode()
        status, data = self._call("PATCH", "/api/admin/users/U1/status", role="patient", body=body)
        self.assertEqual(status, 403)

    def test_staff_blocked_from_change_log(self):
        status, data = self._call("GET", "/api/admin/change-log", role="staff")
        self.assertEqual(status, 403)

    def test_patient_blocked_from_change_log(self):
        status, data = self._call("GET", "/api/admin/change-log", role="patient")
        self.assertEqual(status, 403)

    # ── PHI / compliance exposure controls ───────────────────────────────

    def test_user_list_does_not_expose_clinical_data(self):
        """User registry records contain only identity/role fields, not PHI."""
        register_user("U1", "staff", "u@clinic.com")
        status, data = self._call("GET", "/api/admin/users")
        self.assertEqual(status, 200)
        user = data["data"][0]
        phi_fields = {"patient_notes", "reminder_channels", "do_not_disturb",
                      "patient_email", "patient_phone"}
        for field in phi_fields:
            self.assertNotIn(field, user, f"PHI field '{field}' must not appear in user list")

    def test_change_log_is_read_only_via_api(self):
        """Change log endpoint only supports GET — POST must return 404."""
        status, _ = self._call("POST", "/api/admin/change-log")
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
