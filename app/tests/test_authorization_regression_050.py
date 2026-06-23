"""
EP-005 US-050: Authorization Coverage — Role-Based Regression Tests

Covers:
  UT-US050-001  Endpoint-permission map completeness (task_050_001)
  UT-US050-002  Centralized permission enforcement across all roles (task_050_002)
  UT-US050-003  Normalized authorization failure logging (task_050_003)
  UT-US050-004  Allow/deny regression across Patient / Staff / Admin (task_050_004)
"""
import os
import sys
import unittest
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.rbac import (
    _AUDIT_LOG,
    _STAFF_ASSIGNMENTS,
    _USER_REGISTRY,
    ENDPOINT_PERMISSION_MAP,
    PERMISSION_MATRIX,
    ROLES,
    check_appointment_ownership,
    check_permission,
    check_user_login_allowed,
    get_actor_id_from_environ,
    get_audit_log,
    get_endpoint_permission_map,
    log_denied_event,
    register_user,
    require_appointment_ownership,
    require_permission,
    require_resource_scope,
    require_staff_assignment,
    set_staff_assignment,
    set_user_status,
)


def _env(
    role: str = "patient",
    admin_id: str | None = None,
    staff_id: str | None = None,
    patient_id: int | None = None,
    path: str = "/api/test",
    method: str = "GET",
) -> dict[str, Any]:
    """Build a minimal mock WSGI environ for unit tests."""
    e: dict[str, Any] = {
        "HTTP_X_ROLE": role,
        "PATH_INFO": path,
        "REQUEST_METHOD": method,
    }
    if admin_id is not None:
        e["HTTP_X_ADMIN_ID"] = admin_id
    if staff_id is not None:
        e["HTTP_X_STAFF_ID"] = staff_id
    if patient_id is not None:
        e["HTTP_X_PATIENT_ID"] = str(patient_id)
    return e


# =============================================================================
# UT-US050-001: Endpoint-permission coverage matrix (task_050_001)
# =============================================================================

class EndpointPermissionMapTests(unittest.TestCase):
    """Coverage matrix completeness and internal consistency."""

    def test_map_is_non_empty(self):
        self.assertGreater(len(ENDPOINT_PERMISSION_MAP), 20)

    def test_all_admin_endpoints_present(self):
        admin_keys = [k for k in ENDPOINT_PERMISSION_MAP if "/api/admin/" in k]
        self.assertGreater(len(admin_keys), 0)

    def test_all_staff_endpoints_present(self):
        staff_keys = [k for k in ENDPOINT_PERMISSION_MAP if "/api/staff/" in k]
        self.assertGreater(len(staff_keys), 0)

    def test_all_clinical_endpoints_present(self):
        clinical_keys = [k for k in ENDPOINT_PERMISSION_MAP if "/api/clinical/" in k]
        self.assertGreater(len(clinical_keys), 0)

    def test_password_reset_endpoints_marked_public(self):
        req_key = "POST /api/auth/password-reset/request"
        conf_key = "POST /api/auth/password-reset/confirm"
        self.assertIn(req_key, ENDPOINT_PERMISSION_MAP)
        self.assertIn(conf_key, ENDPOINT_PERMISSION_MAP)
        self.assertIsNone(ENDPOINT_PERMISSION_MAP[req_key]["permission"])
        self.assertIsNone(ENDPOINT_PERMISSION_MAP[conf_key]["permission"])

    def test_non_null_permissions_exist_in_permission_matrix(self):
        all_permissions = {
            entry["permission"]
            for entry in ENDPOINT_PERMISSION_MAP.values()
            if entry.get("permission") is not None
        }
        for perm in all_permissions:
            self.assertIn(
                perm, PERMISSION_MATRIX, f"'{perm}' missing from PERMISSION_MATRIX"
            )

    def test_all_entries_have_required_keys(self):
        for route, entry in ENDPOINT_PERMISSION_MAP.items():
            self.assertIn("permission", entry, f"missing 'permission' in {route}")
            self.assertIn("scoping", entry, f"missing 'scoping' in {route}")

    def test_get_endpoint_permission_map_returns_copy(self):
        m1 = get_endpoint_permission_map()
        m2 = get_endpoint_permission_map()
        self.assertEqual(m1, m2)
        # Mutating the returned copy must not affect the canonical map
        m1["FAKE"] = {"permission": "x", "scoping": "y"}
        self.assertNotIn("FAKE", ENDPOINT_PERMISSION_MAP)

    def test_patient_profile_mapped_with_correct_permission(self):
        entry = ENDPOINT_PERMISSION_MAP["GET /api/patient/profile"]
        self.assertEqual(entry["permission"], "appointments:view")
        self.assertEqual(entry["scoping"], "patient_ownership")

    def test_admin_user_management_endpoints_mapped(self):
        # The actual routes use {id} for PATCH; check representative entries
        for key in (
            "POST /api/admin/users",
            "GET /api/admin/users",
            "GET /api/admin/users/{id}",
            "PATCH /api/admin/users/{id}",
            "PATCH /api/admin/users/{id}/role",
            "PATCH /api/admin/users/{id}/status",
        ):
            self.assertIn(key, ENDPOINT_PERMISSION_MAP)
            self.assertEqual(
                ENDPOINT_PERMISSION_MAP[key]["permission"], "admin:user_management"
            )


# =============================================================================
# PERMISSION_MATRIX shape tests
# =============================================================================

class PermissionMatrixTests(unittest.TestCase):
    """PERMISSION_MATRIX correctness (task_050_002 / task_050_004)."""

    def test_all_standard_roles_defined(self):
        for r in ("patient", "staff", "admin"):
            self.assertIn(r, ROLES)

    def test_patient_cannot_access_admin_dashboard(self):
        self.assertFalse(check_permission("patient", "admin:dashboard"))

    def test_patient_cannot_access_admin_user_management(self):
        self.assertFalse(check_permission("patient", "admin:user_management"))

    def test_staff_cannot_access_admin_user_management(self):
        self.assertFalse(check_permission("staff", "admin:user_management"))

    def test_admin_can_perform_all_admin_actions(self):
        admin_actions = [a for a in PERMISSION_MATRIX if a.startswith("admin:")]
        for action in admin_actions:
            self.assertTrue(
                check_permission("admin", action),
                f"admin denied for: {action}",
            )

    def test_all_roles_can_search_and_view_appointments(self):
        for role in ROLES:
            self.assertTrue(check_permission(role, "appointments:search"))
            self.assertTrue(check_permission(role, "appointments:view"))

    def test_only_staff_and_admin_can_use_clinical_features(self):
        clinical_actions = [a for a in PERMISSION_MATRIX if a.startswith("clinical:")]
        for action in clinical_actions:
            self.assertFalse(
                check_permission("patient", action),
                f"patient should not have: {action}",
            )
            self.assertTrue(
                check_permission("staff", action) or check_permission("admin", action),
                f"neither staff nor admin has: {action}",
            )

    def test_unknown_action_returns_false_for_all_roles(self):
        for role in ROLES:
            self.assertFalse(check_permission(role, "nonexistent:action"))

    def test_staff_and_admin_can_view_queue(self):
        self.assertTrue(check_permission("staff", "staff:queue_view"))
        self.assertTrue(check_permission("admin", "staff:queue_view"))
        self.assertFalse(check_permission("patient", "staff:queue_view"))


# =============================================================================
# UT-US050-002: Centralized require_permission enforcement
# =============================================================================

class RequirePermissionTests(unittest.TestCase):
    """Centralized permission assertions (task_050_002)."""

    def setUp(self):
        _AUDIT_LOG.clear()

    def tearDown(self):
        _AUDIT_LOG.clear()

    def test_admin_allowed_on_admin_user_management(self):
        self.assertIsNone(
            require_permission(_env("admin"), "admin:user_management")
        )

    def test_patient_denied_on_admin_user_management(self):
        result = require_permission(_env("patient"), "admin:user_management")
        self.assertIsNotNone(result)
        role, msg = result
        self.assertEqual(role, "patient")
        self.assertIn("not authorised", msg)

    def test_staff_denied_on_admin_user_management(self):
        self.assertIsNotNone(
            require_permission(_env("staff"), "admin:user_management")
        )

    def test_staff_allowed_on_staff_queue_view(self):
        self.assertIsNone(require_permission(_env("staff"), "staff:queue_view"))

    def test_patient_denied_on_staff_queue_view(self):
        self.assertIsNotNone(require_permission(_env("patient"), "staff:queue_view"))

    def test_admin_allowed_on_staff_endpoints(self):
        self.assertIsNone(require_permission(_env("admin"), "staff:queue_view"))
        self.assertIsNone(require_permission(_env("admin"), "staff:checkin"))

    def test_denial_is_audit_logged(self):
        require_permission(_env("patient"), "admin:dashboard")
        log = get_audit_log()
        self.assertGreater(len(log), 0)
        self.assertEqual(log[0]["outcome"], "denied")

    def test_allowed_returns_none(self):
        self.assertIsNone(require_permission(_env("admin"), "admin:dashboard"))

    def test_all_roles_allowed_for_appointments_view(self):
        for role in ROLES:
            self.assertIsNone(
                require_permission(_env(role), "appointments:view"),
                f"Role {role} should be allowed for appointments:view",
            )

    def test_unknown_role_defaults_to_patient_restrictions(self):
        e = {"HTTP_X_ROLE": "superuser", "PATH_INFO": "/api/admin/users",
             "REQUEST_METHOD": "GET"}
        denial = require_permission(e, "admin:user_management")
        self.assertIsNotNone(denial)

    def test_missing_role_header_defaults_to_patient(self):
        e = {"PATH_INFO": "/api/admin/users", "REQUEST_METHOD": "GET"}
        denial = require_permission(e, "admin:user_management")
        self.assertIsNotNone(denial)


# =============================================================================
# Resource scope enforcement
# =============================================================================

class ResourceScopeTests(unittest.TestCase):
    """Patient ownership enforcement (task_050_002 / task_050_004)."""

    def setUp(self):
        _AUDIT_LOG.clear()

    def tearDown(self):
        _AUDIT_LOG.clear()

    def test_patient_allowed_own_resource(self):
        self.assertIsNone(require_resource_scope(_env("patient", patient_id=42), 42))

    def test_patient_denied_other_resource(self):
        self.assertIsNotNone(
            require_resource_scope(_env("patient", patient_id=42), 99)
        )

    def test_staff_always_allowed_any_resource(self):
        self.assertIsNone(require_resource_scope(_env("staff"), 99))

    def test_admin_always_allowed_any_resource(self):
        self.assertIsNone(require_resource_scope(_env("admin"), 99))

    def test_scope_violation_is_audit_logged(self):
        require_resource_scope(_env("patient", patient_id=1), 99)
        log = get_audit_log()
        self.assertGreater(len(log), 0)
        self.assertEqual(log[0]["action"], "resource:scope")

    def test_scope_violation_message_contains_patient_id(self):
        _, msg = require_resource_scope(_env("patient", patient_id=1), 99)
        # Detailed message for the legitimate caller — not in log entry
        self.assertIn("patient_id=99", msg)


# =============================================================================
# Staff assignment enforcement
# =============================================================================

class StaffAssignmentTests(unittest.TestCase):
    """Assignment-scoped access enforcement (task_050_002 / task_050_004)."""

    def setUp(self):
        _AUDIT_LOG.clear()
        _STAFF_ASSIGNMENTS.clear()

    def tearDown(self):
        _AUDIT_LOG.clear()
        _STAFF_ASSIGNMENTS.clear()

    def test_assigned_staff_allowed(self):
        set_staff_assignment("s1", [10, 20])
        self.assertIsNone(
            require_staff_assignment(_env("staff", staff_id="s1"))
        )

    def test_unassigned_staff_denied(self):
        self.assertIsNotNone(
            require_staff_assignment(_env("staff", staff_id="s-unknown"))
        )

    def test_admin_bypasses_assignment_check(self):
        self.assertIsNone(
            require_staff_assignment(_env("admin", admin_id="a1"))
        )

    def test_patient_role_denied_for_staff_operations(self):
        result = require_staff_assignment(_env("patient"))
        self.assertIsNotNone(result)
        _, msg = result
        self.assertIn("not authorised", msg)

    def test_specific_provider_assignment_enforced(self):
        set_staff_assignment("s2", [30])
        # Staff is assigned to provider 30 but requesting provider 99
        self.assertIsNotNone(
            require_staff_assignment(_env("staff", staff_id="s2"), provider_id=99)
        )

    def test_assignment_denial_is_audit_logged(self):
        require_staff_assignment(_env("patient"))
        log = get_audit_log()
        self.assertTrue(
            any(e["action"] == "staff:assignment_required" for e in log)
        )


# =============================================================================
# Appointment ownership enforcement
# =============================================================================

class AppointmentOwnershipTests(unittest.TestCase):
    """Per-role appointment access rules (task_050_002 / task_050_004)."""

    def setUp(self):
        _AUDIT_LOG.clear()

    def tearDown(self):
        _AUDIT_LOG.clear()

    def test_patient_can_access_own_confirmed_appointment(self):
        appt = {"status": "confirmed", "checkout_status": "confirmed"}
        self.assertTrue(check_appointment_ownership("patient", 42, appt, 42))

    def test_patient_denied_other_patients_confirmed_appointment(self):
        appt = {"status": "confirmed", "checkout_status": "confirmed"}
        self.assertFalse(check_appointment_ownership("patient", 42, appt, 99))

    def test_staff_can_access_any_appointment(self):
        appt = {"status": "confirmed", "checkout_status": "confirmed"}
        self.assertTrue(check_appointment_ownership("staff", 0, appt, 99))

    def test_admin_can_access_any_appointment(self):
        appt = {"status": "confirmed", "checkout_status": "confirmed"}
        self.assertTrue(check_appointment_ownership("admin", 0, appt, 99))

    def test_all_roles_can_view_available_slots(self):
        appt = {"status": "available", "checkout_status": ""}
        for role in ROLES:
            result = require_appointment_ownership(_env(role), appt, 99)
            self.assertIsNone(result, f"Role {role} should see available slot")

    def test_patient_denied_other_patients_booked_slot(self):
        appt = {"status": "booked", "checkout_status": "confirmed"}
        result = require_appointment_ownership(
            _env("patient", patient_id=1), appt, 99
        )
        self.assertIsNotNone(result)


# =============================================================================
# UT-US050-003: Normalized authorization failure logging
# =============================================================================

class DenialLoggingTests(unittest.TestCase):
    """Normalized 403 telemetry (task_050_003)."""

    def setUp(self):
        _AUDIT_LOG.clear()

    def tearDown(self):
        _AUDIT_LOG.clear()

    def test_numeric_ids_normalized_in_endpoint(self):
        log_denied_event(
            "patient", "admin:dashboard",
            "/api/clinical/patients/42/profile", "GET",
        )
        entry = get_audit_log()[0]
        self.assertEqual(entry["endpoint"], "/api/clinical/patients/{id}/profile")

    def test_multiple_numeric_segments_normalized(self):
        log_denied_event("patient", "test:action", "/api/items/123/sub/456/detail", "GET")
        self.assertEqual(
            get_audit_log()[0]["endpoint"], "/api/items/{id}/sub/{id}/detail"
        )

    def test_non_numeric_segments_not_modified(self):
        log_denied_event("patient", "test:action", "/api/admin/users", "GET")
        self.assertEqual(get_audit_log()[0]["endpoint"], "/api/admin/users")

    def test_actor_id_included_when_provided(self):
        log_denied_event(
            "staff", "admin:dashboard", "/api/dashboard", "GET",
            actor_id="staff-007",
        )
        self.assertEqual(get_audit_log()[0]["actor_id"], "staff-007")

    def test_reason_included_when_provided(self):
        log_denied_event(
            "patient", "admin:ops_jobs", "/api/jobs", "POST",
            reason="Role 'patient' is not authorised.",
        )
        entry = get_audit_log()[0]
        self.assertIn("reason", entry)
        self.assertIn("patient", entry["reason"])

    def test_actor_id_absent_when_not_provided(self):
        log_denied_event("patient", "admin:dashboard", "/api/dashboard", "GET")
        self.assertNotIn("actor_id", get_audit_log()[0])

    def test_require_permission_denial_includes_actor_id(self):
        environ = _env("patient", patient_id=5, path="/api/admin/users")
        require_permission(environ, "admin:user_management")
        entry = get_audit_log()[0]
        self.assertIn("actor_id", entry)
        self.assertEqual(entry["actor_id"], "patient:5")

    def test_require_permission_denial_includes_reason(self):
        environ = _env("staff", staff_id="s1", path="/api/admin/users")
        require_permission(environ, "admin:user_management")
        entry = get_audit_log()[0]
        self.assertIn("reason", entry)

    def test_resource_scope_denial_does_not_include_patient_id_in_log(self):
        require_resource_scope(_env("patient", patient_id=1), 99)
        entry = get_audit_log()[0]
        # The log reason must not contain patient ID (99) — stays in response only
        reason = entry.get("reason", "")
        self.assertNotIn("99", reason)

    def test_denial_log_searchable_by_action(self):
        log_denied_event("patient", "admin:user_management", "/api/admin/users", "GET")
        log_denied_event("patient", "admin:dashboard", "/api/dashboard", "GET")
        entries = get_audit_log()
        mgmt_entries = [e for e in entries if e["action"] == "admin:user_management"]
        self.assertEqual(len(mgmt_entries), 1)

    def test_get_actor_id_returns_admin_id_first(self):
        e = {"HTTP_X_ADMIN_ID": "admin-x", "HTTP_X_STAFF_ID": "staff-y"}
        self.assertEqual(get_actor_id_from_environ(e), "admin-x")

    def test_get_actor_id_returns_staff_id_when_no_admin(self):
        e = {"HTTP_X_STAFF_ID": "staff-y"}
        self.assertEqual(get_actor_id_from_environ(e), "staff-y")

    def test_get_actor_id_prefixes_patient_id(self):
        e = {"HTTP_X_PATIENT_ID": "42"}
        self.assertEqual(get_actor_id_from_environ(e), "patient:42")

    def test_get_actor_id_returns_none_when_no_headers(self):
        self.assertIsNone(get_actor_id_from_environ({}))

    def test_get_actor_id_ignores_zero_patient_id(self):
        e = {"HTTP_X_PATIENT_ID": "0"}
        self.assertIsNone(get_actor_id_from_environ(e))


# =============================================================================
# UT-US050-004: Comprehensive cross-role allow/deny regression
# =============================================================================

class CrossRoleRegressionTests(unittest.TestCase):
    """Allow/deny matrix regression across all three roles (task_050_004)."""

    def setUp(self):
        _AUDIT_LOG.clear()
        _USER_REGISTRY.clear()
        _STAFF_ASSIGNMENTS.clear()

    def tearDown(self):
        _AUDIT_LOG.clear()
        _USER_REGISTRY.clear()
        _STAFF_ASSIGNMENTS.clear()

    # ── Patient must be denied restricted resources ────────────────────────

    def test_patient_denied_staff_queue_view(self):
        self.assertIsNotNone(require_permission(_env("patient"), "staff:queue_view"))

    def test_patient_denied_admin_user_management(self):
        self.assertIsNotNone(
            require_permission(_env("patient"), "admin:user_management")
        )

    def test_patient_denied_admin_change_log(self):
        self.assertIsNotNone(require_permission(_env("patient"), "admin:change_log"))

    def test_patient_denied_clinical_code_review(self):
        self.assertIsNotNone(require_permission(_env("patient"), "clinical:code_review"))

    def test_patient_denied_clinical_manage_thresholds(self):
        self.assertIsNotNone(
            require_permission(_env("patient"), "clinical:manage_thresholds")
        )

    def test_patient_allowed_appointment_search(self):
        self.assertIsNone(require_permission(_env("patient"), "appointments:search"))

    def test_patient_allowed_appointment_book(self):
        self.assertIsNone(require_permission(_env("patient"), "appointments:book"))

    # ── Staff must be denied admin-only resources ──────────────────────────

    def test_staff_denied_admin_user_management(self):
        self.assertIsNotNone(
            require_permission(_env("staff"), "admin:user_management")
        )

    def test_staff_denied_admin_change_log(self):
        self.assertIsNotNone(require_permission(_env("staff"), "admin:change_log"))

    def test_staff_denied_admin_ops_jobs(self):
        self.assertIsNotNone(require_permission(_env("staff"), "admin:ops_jobs"))

    def test_staff_denied_clinical_manage_thresholds(self):
        self.assertIsNotNone(
            require_permission(_env("staff"), "clinical:manage_thresholds")
        )

    def test_staff_allowed_clinical_view_profile(self):
        self.assertIsNone(require_permission(_env("staff"), "clinical:view_profile"))

    def test_staff_allowed_staff_checkin(self):
        self.assertIsNone(require_permission(_env("staff"), "staff:checkin"))

    def test_staff_without_assignment_denied_queue(self):
        result = require_staff_assignment(
            _env("staff", staff_id="unassigned-staff")
        )
        self.assertIsNotNone(result)

    # ── Admin must be allowed all operations ──────────────────────────────

    def test_admin_allowed_admin_user_management(self):
        self.assertIsNone(
            require_permission(_env("admin"), "admin:user_management")
        )

    def test_admin_allowed_admin_change_log(self):
        self.assertIsNone(require_permission(_env("admin"), "admin:change_log"))

    def test_admin_allowed_all_clinical_features(self):
        clinical_actions = [a for a in PERMISSION_MATRIX if a.startswith("clinical:")]
        for action in clinical_actions:
            self.assertIsNone(
                require_permission(_env("admin"), action),
                f"admin denied: {action}",
            )

    def test_admin_allowed_staff_endpoints(self):
        self.assertIsNone(require_permission(_env("admin"), "staff:queue_view"))
        self.assertIsNone(require_permission(_env("admin"), "staff:checkin"))

    # ── Account-status lifecycle ───────────────────────────────────────────

    def test_deactivated_user_cannot_authenticate(self):
        register_user("deact-050", "staff", "d@d.com", status="active")
        set_user_status("admin-x", "deact-050", "inactive", "test")
        ok, _ = check_user_login_allowed("deact-050")
        self.assertFalse(ok)

    def test_suspended_user_cannot_authenticate(self):
        register_user("susp-050", "staff", "s@s.com", status="active")
        set_user_status("admin-x", "susp-050", "suspended", "test")
        ok, _ = check_user_login_allowed("susp-050")
        self.assertFalse(ok)

    def test_active_user_can_authenticate(self):
        register_user("active-050", "staff", "a@a.com", status="active")
        ok, _ = check_user_login_allowed("active-050")
        self.assertTrue(ok)

    def test_unknown_user_not_blocked(self):
        ok, _ = check_user_login_allowed("never-registered")
        self.assertTrue(ok)

    # ── Authorization bypass prevention ───────────────────────────────────

    def test_fabricated_role_header_defaults_to_patient(self):
        e = {
            "HTTP_X_ROLE": "superadmin",
            "PATH_INFO": "/api/admin/users",
            "REQUEST_METHOD": "GET",
        }
        denial = require_permission(e, "admin:user_management")
        self.assertIsNotNone(denial)

    def test_empty_role_header_defaults_to_patient(self):
        e = {"HTTP_X_ROLE": "", "PATH_INFO": "/api/admin/users", "REQUEST_METHOD": "GET"}
        denial = require_permission(e, "admin:user_management")
        self.assertIsNotNone(denial)

    def test_every_denial_emits_audit_event(self):
        """Deny attempts across all three roles must all appear in audit log."""
        _AUDIT_LOG.clear()
        require_permission(_env("patient"), "admin:user_management")
        require_permission(_env("staff"), "admin:change_log")
        log = get_audit_log()
        self.assertEqual(len(log), 2)
        self.assertTrue(all(e["outcome"] == "denied" for e in log))


if __name__ == "__main__":
    unittest.main()
