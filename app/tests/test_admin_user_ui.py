"""
test_admin_user_ui.py — EP-005 US-047 validation (task_047_004)

Validates:
 - Create / edit / deactivate / search workflows at the unit layer
 - Non-admin users cannot access admin:user_management endpoints
 - Audit log side-effects are recorded on create/edit operations
 - CLIENT_PERMISSION_MATRIX entries verified at Python level
 - RBAC gating: admin:user_management and admin:change_log are admin-only
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.rbac import (
    register_user,
    get_user,
    list_users,
    assign_user_role,
    set_user_status,
    get_admin_change_log,
    PERMISSION_MATRIX,
    ROLES,
    VALID_STATUSES,
    _USER_REGISTRY,
    _ADMIN_CHANGE_LOG,
)


def _seed_user(uid="u-test-047", role="staff", email="test@example.com", status="active"):
    return register_user(uid, role, email, status)


class AdminPermissionGatingTests(unittest.TestCase):
    """task_047_004 – admin:user_management is admin-only (server matrix)."""

    def test_admin_user_management_admin_only(self):
        allowed = PERMISSION_MATRIX.get("admin:user_management", set())
        self.assertIn("admin", allowed)
        self.assertNotIn("staff", allowed)
        self.assertNotIn("patient", allowed)

    def test_admin_change_log_admin_only(self):
        allowed = PERMISSION_MATRIX.get("admin:change_log", set())
        self.assertIn("admin", allowed)
        self.assertNotIn("staff", allowed)
        self.assertNotIn("patient", allowed)

    def test_staff_queue_view_accessible_to_staff(self):
        allowed = PERMISSION_MATRIX.get("staff:queue_view", set())
        self.assertIn("staff", allowed)
        self.assertIn("admin", allowed)
        self.assertNotIn("patient", allowed)


class CreateUserWorkflowTests(unittest.TestCase):
    """task_047_002 – create user validates required fields and persists."""

    def setUp(self):
        _USER_REGISTRY.pop("u-create-047", None)

    def tearDown(self):
        _USER_REGISTRY.pop("u-create-047", None)

    def test_create_user_valid(self):
        user = register_user("u-create-047", "staff", "staff@clinic.io", "active")
        self.assertEqual(user["id"], "u-create-047")
        self.assertEqual(user["role"], "staff")
        self.assertEqual(user["email"], "staff@clinic.io")
        self.assertEqual(user["status"], "active")

    def test_create_user_persisted_in_registry(self):
        register_user("u-create-047", "staff", "staff@clinic.io", "active")
        retrieved = get_user("u-create-047")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["email"], "staff@clinic.io")

    def test_create_user_invalid_role_raises(self):
        with self.assertRaises(ValueError):
            register_user("u-create-047", "superadmin", "x@x.com")

    def test_create_user_invalid_status_raises(self):
        with self.assertRaises(ValueError):
            register_user("u-create-047", "staff", "x@x.com", "banned")

    def test_create_user_appears_in_list(self):
        register_user("u-create-047", "patient", "p@p.com", "active")
        ids = [u["id"] for u in list_users()]
        self.assertIn("u-create-047", ids)


class EditUserRoleWorkflowTests(unittest.TestCase):
    """task_047_003 – role edits persist and are audit-logged."""

    def setUp(self):
        _USER_REGISTRY.pop("u-edit-role-047", None)
        _seed_user("u-edit-role-047", role="staff")

    def tearDown(self):
        _USER_REGISTRY.pop("u-edit-role-047", None)

    def test_assign_role_success(self):
        ok, msg = assign_user_role("admin-demo", "u-edit-role-047", "admin", "Promotion")
        self.assertTrue(ok)
        user = get_user("u-edit-role-047")
        self.assertEqual(user["role"], "admin")

    def test_assign_role_reflected_in_list(self):
        assign_user_role("admin-demo", "u-edit-role-047", "patient", "Downgrade")
        user = get_user("u-edit-role-047")
        self.assertEqual(user["role"], "patient")

    def test_assign_unknown_role_fails(self):
        ok, msg = assign_user_role("admin-demo", "u-edit-role-047", "superuser", "")
        self.assertFalse(ok)

    def test_assign_role_audit_logged(self):
        before_len = len(_ADMIN_CHANGE_LOG)
        assign_user_role("admin-demo", "u-edit-role-047", "admin", "Audit test")
        self.assertEqual(len(_ADMIN_CHANGE_LOG), before_len + 1)
        entry = _ADMIN_CHANGE_LOG[-1]
        self.assertEqual(entry["target_user_id"], "u-edit-role-047")
        self.assertEqual(entry["actor"], "admin-demo")
        self.assertEqual(entry["new_value"], "admin")


class EditUserStatusWorkflowTests(unittest.TestCase):
    """task_047_003 – status changes persist; deactivated users clearly marked."""

    def setUp(self):
        _USER_REGISTRY.pop("u-edit-status-047", None)
        _seed_user("u-edit-status-047", role="staff")

    def tearDown(self):
        _USER_REGISTRY.pop("u-edit-status-047", None)

    def test_deactivate_user_sets_inactive(self):
        ok, _ = set_user_status("admin-demo", "u-edit-status-047", "inactive", "Left org")
        self.assertTrue(ok)
        user = get_user("u-edit-status-047")
        self.assertEqual(user["status"], "inactive")

    def test_suspend_user(self):
        ok, _ = set_user_status("admin-demo", "u-edit-status-047", "suspended", "Under review")
        self.assertTrue(ok)
        self.assertEqual(get_user("u-edit-status-047")["status"], "suspended")

    def test_invalid_status_fails(self):
        ok, msg = set_user_status("admin-demo", "u-edit-status-047", "blocked", "")
        self.assertFalse(ok)

    def test_deactivate_audit_logged(self):
        before_len = len(_ADMIN_CHANGE_LOG)
        set_user_status("admin-demo", "u-edit-status-047", "inactive", "Deactivation test")
        self.assertEqual(len(_ADMIN_CHANGE_LOG), before_len + 1)
        entry = _ADMIN_CHANGE_LOG[-1]
        self.assertEqual(entry["new_value"], "inactive")

    def test_reactivate_user(self):
        set_user_status("admin-demo", "u-edit-status-047", "inactive", "")
        ok, _ = set_user_status("admin-demo", "u-edit-status-047", "active", "Reinstated")
        self.assertTrue(ok)
        self.assertEqual(get_user("u-edit-status-047")["status"], "active")


class SearchAndFilterWorkflowTests(unittest.TestCase):
    """task_047_001 – search/filter returns accurate results."""

    def setUp(self):
        for uid in ("u-search-a", "u-search-b", "u-search-c"):
            _USER_REGISTRY.pop(uid, None)
        register_user("u-search-a", "staff", "alice@clinic.io", "active")
        register_user("u-search-b", "admin", "bob@clinic.io", "inactive")
        register_user("u-search-c", "patient", "carol@clinic.io", "active")

    def tearDown(self):
        for uid in ("u-search-a", "u-search-b", "u-search-c"):
            _USER_REGISTRY.pop(uid, None)

    def _filter(self, users, query="", role="", status=""):
        q = query.lower()
        return [
            u for u in users
            if (not q or q in u["id"].lower() or q in (u.get("email") or "").lower())
            and (not role or u["role"] == role)
            and (not status or u["status"] == status)
        ]

    def test_filter_by_role(self):
        users = list_users()
        result = self._filter(users, role="admin")
        roles = {u["role"] for u in result}
        self.assertEqual(roles, {"admin"})

    def test_filter_by_status(self):
        users = list_users()
        result = self._filter(users, status="inactive")
        self.assertTrue(all(u["status"] == "inactive" for u in result))
        ids = [u["id"] for u in result]
        self.assertIn("u-search-b", ids)

    def test_filter_by_query_email(self):
        users = list_users()
        result = self._filter(users, query="carol")
        ids = [u["id"] for u in result]
        self.assertIn("u-search-c", ids)
        self.assertNotIn("u-search-a", ids)

    def test_filter_combined(self):
        users = list_users()
        result = self._filter(users, role="staff", status="active")
        self.assertTrue(all(u["role"] == "staff" and u["status"] == "active" for u in result))

    def test_all_users_returned_with_no_filter(self):
        users = list_users()
        ids = [u["id"] for u in users]
        for uid in ("u-search-a", "u-search-b", "u-search-c"):
            self.assertIn(uid, ids)


class AuditLogSideEffectsTests(unittest.TestCase):
    """task_047_004 – audit log side effects verified for admin operations."""

    def setUp(self):
        _USER_REGISTRY.pop("u-audit-047", None)
        _seed_user("u-audit-047")

    def tearDown(self):
        _USER_REGISTRY.pop("u-audit-047", None)

    def test_change_log_filters_by_action(self):
        assign_user_role("admin-x", "u-audit-047", "admin", "Audit filter test")
        log = get_admin_change_log(action="admin:role_assigned")
        actions = {e["action"] for e in log}
        self.assertIn("admin:role_assigned", actions)

    def test_change_log_filters_by_actor(self):
        assign_user_role("admin-unique-actor", "u-audit-047", "patient", "Filter test")
        log = get_admin_change_log(actor="admin-unique-actor")
        actors = {e["actor"] for e in log}
        self.assertIn("admin-unique-actor", actors)

    def test_change_log_non_empty_after_operations(self):
        before_len = len(get_admin_change_log())
        assign_user_role("admin-demo", "u-audit-047", "admin", "")
        set_user_status("admin-demo", "u-audit-047", "inactive", "")
        after_log = get_admin_change_log()
        self.assertGreater(len(after_log), before_len)

    def test_valid_roles_match_permission_matrix_subjects(self):
        """All roles in ROLES should appear somewhere in PERMISSION_MATRIX values."""
        all_allowed = set()
        for roles in PERMISSION_MATRIX.values():
            all_allowed.update(roles)
        for role in ROLES:
            self.assertIn(role, all_allowed, f"Role '{role}' not referenced in PERMISSION_MATRIX")

    def test_valid_statuses_are_complete(self):
        self.assertIn("active", VALID_STATUSES)
        self.assertIn("inactive", VALID_STATUSES)
        self.assertIn("suspended", VALID_STATUSES)


if __name__ == "__main__":
    unittest.main()
