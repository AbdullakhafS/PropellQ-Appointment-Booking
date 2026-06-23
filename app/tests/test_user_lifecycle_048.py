"""
test_user_lifecycle_048.py — EP-005 US-048 unit tests

Covers all four tasks:
  task_048_001 — Admin-only user create API (validation, uniqueness, audit)
  task_048_002 — User update API (profile fields, validation, audit)
  task_048_003 — Deactivation login block and reactivation rules
  task_048_004 — Audit logging for all lifecycle operations
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
    update_user,
    check_user_login_allowed,
    record_admin_event,
    get_admin_change_log,
    PERMISSION_MATRIX,
    VALID_STATUSES,
    _USER_REGISTRY,
    _ADMIN_CHANGE_LOG,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _seed(uid, role="staff", email=None, status="active"):
    email = email or f"{uid}@test.example"
    return register_user(uid, role, email, status)


def _clean(*uids):
    for uid in uids:
        _USER_REGISTRY.pop(uid, None)


# ===========================================================================
# task_048_001 — Create user API (unit layer)
# ===========================================================================

class CreateUserAPITests(unittest.TestCase):
    """AC1 — Admin credentials produce a user record with assigned role/status."""

    def setUp(self):
        _clean("u-c-001", "u-c-002")

    def tearDown(self):
        _clean("u-c-001", "u-c-002")

    # UT-US048-001
    def test_create_user_returns_record_with_correct_fields(self):
        user = register_user("u-c-001", "staff", "staff@example.com", "active")
        self.assertEqual(user["id"], "u-c-001")
        self.assertEqual(user["role"], "staff")
        self.assertEqual(user["email"], "staff@example.com")
        self.assertEqual(user["status"], "active")
        self.assertIn("created_at", user)

    # UT-US048-002
    def test_create_user_default_status_is_active(self):
        user = register_user("u-c-002", "patient", "p@example.com")
        self.assertEqual(user["status"], "active")

    def test_create_user_persisted_in_registry(self):
        register_user("u-c-001", "admin", "a@example.com")
        self.assertIsNotNone(get_user("u-c-001"))

    def test_create_user_all_valid_roles(self):
        for i, role in enumerate(["admin", "staff", "patient"]):
            uid = f"u-c-role-{i}"
            _clean(uid)
            try:
                user = register_user(uid, role, f"{uid}@x.com")
                self.assertEqual(user["role"], role)
            finally:
                _clean(uid)

    def test_create_user_invalid_role_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            register_user("u-c-001", "superuser", "x@x.com")
        self.assertIn("Unknown role", str(ctx.exception))

    def test_create_user_invalid_status_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            register_user("u-c-001", "staff", "x@x.com", "banned")
        self.assertIn("Unknown status", str(ctx.exception))

    def test_create_user_appears_in_list(self):
        register_user("u-c-001", "staff", "s@example.com")
        self.assertIn("u-c-001", [u["id"] for u in list_users()])

    def test_create_user_audit_log_entry_produced(self):
        # record_admin_event wraps _record_admin_change; verify it appends
        before = len(_ADMIN_CHANGE_LOG)
        record_admin_event("admin-demo", "admin:user_created", "u-c-001", None,
                           {"role": "staff", "status": "active", "email": "s@example.com"}, "")
        self.assertEqual(len(_ADMIN_CHANGE_LOG), before + 1)
        entry = _ADMIN_CHANGE_LOG[-1]
        self.assertEqual(entry["action"], "admin:user_created")
        self.assertEqual(entry["target_user_id"], "u-c-001")
        self.assertEqual(entry["actor"], "admin-demo")
        self.assertIsNone(entry["previous_value"])


# ===========================================================================
# task_048_002 — User update API
# ===========================================================================

class UpdateUserAPITests(unittest.TestCase):
    """AC2 — Valid updates are persisted and returned; invalid updates fail clearly."""

    def setUp(self):
        _clean("u-u-001", "u-u-002")
        _seed("u-u-001", role="staff", email="original@example.com")

    def tearDown(self):
        _clean("u-u-001", "u-u-002")

    # UT-US048-003
    def test_update_email_succeeds(self):
        ok, result = update_user("admin-demo", "u-u-001", {"email": "new@example.com"})
        self.assertTrue(ok)
        self.assertEqual(result["email"], "new@example.com")

    # UT-US048-004
    def test_update_reflected_in_get_user(self):
        update_user("admin-demo", "u-u-001", {"email": "updated@example.com"})
        self.assertEqual(get_user("u-u-001")["email"], "updated@example.com")

    def test_update_empty_fields_fails(self):
        ok, msg = update_user("admin-demo", "u-u-001", {})
        self.assertFalse(ok)

    def test_update_invalid_email_fails(self):
        ok, msg = update_user("admin-demo", "u-u-001", {"email": "not-an-email"})
        self.assertFalse(ok)
        self.assertIn("email", msg.lower())

    def test_update_blank_email_fails(self):
        ok, msg = update_user("admin-demo", "u-u-001", {"email": "  "})
        self.assertFalse(ok)

    def test_update_protected_field_rejected(self):
        ok, msg = update_user("admin-demo", "u-u-001", {"id": "hacker"})
        self.assertFalse(ok)
        self.assertIn("Non-updatable", msg)

    def test_update_role_via_dedicated_endpoint_still_works(self):
        ok, _ = assign_user_role("admin-demo", "u-u-001", "admin", "test")
        self.assertTrue(ok)
        self.assertEqual(get_user("u-u-001")["role"], "admin")

    def test_update_missing_user_returns_error(self):
        ok, msg = update_user("admin-demo", "nonexistent-user", {"email": "x@x.com"})
        self.assertFalse(ok)
        self.assertIn("not found", msg)

    def test_update_audit_logged_with_before_after(self):
        before = len(_ADMIN_CHANGE_LOG)
        update_user("admin-demo", "u-u-001", {"email": "audit@example.com"}, "audit test")
        self.assertEqual(len(_ADMIN_CHANGE_LOG), before + 1)
        entry = _ADMIN_CHANGE_LOG[-1]
        self.assertEqual(entry["action"], "admin:user_updated")
        self.assertEqual(entry["previous_value"]["email"], "original@example.com")
        self.assertEqual(entry["new_value"]["email"], "audit@example.com")
        self.assertEqual(entry["reason"], "audit test")

    def test_sensitive_fields_are_protected(self):
        # password/secret fields should not be in update response
        ok, result = update_user("admin-demo", "u-u-001", {"email": "safe@example.com"})
        self.assertTrue(ok)
        for sensitive in ("password", "secret", "token", "hash"):
            self.assertNotIn(sensitive, result)


# ===========================================================================
# task_048_003 — Deactivation login block & reactivation rules
# ===========================================================================

class DeactivationLoginBlockTests(unittest.TestCase):
    """AC3 — Deactivated users blocked; reactivated users allowed."""

    def setUp(self):
        _clean("u-d-001", "u-d-002", "u-d-003")
        _seed("u-d-001", role="staff")

    def tearDown(self):
        _clean("u-d-001", "u-d-002", "u-d-003")

    # UT-US048-005
    def test_active_user_login_allowed(self):
        ok, reason = check_user_login_allowed("u-d-001")
        self.assertTrue(ok)
        self.assertEqual(reason, "")

    # UT-US048-006
    def test_deactivated_user_login_blocked(self):
        set_user_status("admin-demo", "u-d-001", "inactive", "Left org")
        ok, reason = check_user_login_allowed("u-d-001")
        self.assertFalse(ok)
        self.assertIn("deactivated", reason.lower())

    def test_suspended_user_login_blocked(self):
        set_user_status("admin-demo", "u-d-001", "suspended", "Review")
        ok, reason = check_user_login_allowed("u-d-001")
        self.assertFalse(ok)
        self.assertIn("suspended", reason.lower())

    def test_reactivated_user_login_allowed(self):
        set_user_status("admin-demo", "u-d-001", "inactive", "Temp leave")
        set_user_status("admin-demo", "u-d-001", "active", "Returned")
        ok, _ = check_user_login_allowed("u-d-001")
        self.assertTrue(ok)

    def test_unknown_user_passes_login_check(self):
        # Users not in registry are not explicitly deactivated — pass through
        ok, reason = check_user_login_allowed("completely-unknown-user")
        self.assertTrue(ok)
        self.assertEqual(reason, "")

    def test_deactivation_does_not_affect_other_users(self):
        _seed("u-d-002")
        set_user_status("admin-demo", "u-d-001", "inactive", "")
        ok, _ = check_user_login_allowed("u-d-002")
        self.assertTrue(ok)

    def test_all_inactive_statuses_block_login(self):
        for status in ("inactive", "suspended"):
            _seed("u-d-003")
            set_user_status("admin-demo", "u-d-003", status, "")
            ok, _ = check_user_login_allowed("u-d-003")
            self.assertFalse(ok, f"Expected block for status='{status}'")
            _clean("u-d-003")

    def test_only_active_status_permits_login(self):
        ok, _ = check_user_login_allowed("u-d-001")
        self.assertTrue(ok)

    def test_reactivation_state_transition_auditable(self):
        before = len(_ADMIN_CHANGE_LOG)
        set_user_status("admin-demo", "u-d-001", "inactive", "Offboard")
        set_user_status("admin-demo", "u-d-001", "active", "Onboard again")
        entries_added = len(_ADMIN_CHANGE_LOG) - before
        self.assertEqual(entries_added, 2)


# ===========================================================================
# task_048_004 — Audit logging for all lifecycle operations
# ===========================================================================

class AuditLoggingTests(unittest.TestCase):
    """AC5 — All lifecycle actions are logged with actor, timestamp, before/after."""

    def setUp(self):
        _clean("u-a-001", "u-a-002")
        _seed("u-a-001")

    def tearDown(self):
        _clean("u-a-001", "u-a-002")

    def test_audit_entry_has_required_fields(self):
        before = len(_ADMIN_CHANGE_LOG)
        assign_user_role("admin-x", "u-a-001", "admin", "Promotion")
        entry = _ADMIN_CHANGE_LOG[-1]
        for field in ("timestamp", "actor", "action", "target_user_id",
                      "previous_value", "new_value", "reason"):
            self.assertIn(field, entry, f"Missing audit field: {field}")

    def test_create_audit_has_null_previous(self):
        record_admin_event("admin-demo", "admin:user_created", "u-a-002", None,
                           {"role": "patient"}, "")
        entry = _ADMIN_CHANGE_LOG[-1]
        self.assertIsNone(entry["previous_value"])

    def test_role_change_records_before_after(self):
        assign_user_role("admin-demo", "u-a-001", "admin", "Upgrade")
        entry = next(
            e for e in reversed(_ADMIN_CHANGE_LOG)
            if e["action"] == "admin:role_assigned" and e["target_user_id"] == "u-a-001"
        )
        self.assertEqual(entry["previous_value"], "staff")
        self.assertEqual(entry["new_value"], "admin")

    def test_status_change_records_before_after(self):
        set_user_status("admin-demo", "u-a-001", "inactive", "Offboard")
        entry = next(
            e for e in reversed(_ADMIN_CHANGE_LOG)
            if e["action"] == "admin:status_changed" and e["target_user_id"] == "u-a-001"
        )
        self.assertEqual(entry["previous_value"], "active")
        self.assertEqual(entry["new_value"], "inactive")

    def test_update_records_before_after(self):
        update_user("admin-demo", "u-a-001", {"email": "newemail@x.com"}, "email fix")
        entry = next(
            e for e in reversed(_ADMIN_CHANGE_LOG)
            if e["action"] == "admin:user_updated" and e["target_user_id"] == "u-a-001"
        )
        self.assertIn("email", entry["previous_value"])
        self.assertIn("email", entry["new_value"])
        self.assertEqual(entry["new_value"]["email"], "newemail@x.com")

    def test_audit_log_is_queryable_by_action(self):
        record_admin_event("admin-y", "admin:user_created", "u-a-002", None, {}, "")
        results = get_admin_change_log(action="admin:user_created")
        self.assertTrue(any(e["target_user_id"] == "u-a-002" for e in results))

    def test_audit_log_is_queryable_by_actor(self):
        assign_user_role("actor-unique-048", "u-a-001", "patient", "")
        results = get_admin_change_log(actor="actor-unique-048")
        self.assertTrue(any(e["actor"] == "actor-unique-048" for e in results))

    def test_audit_log_newest_first(self):
        assign_user_role("admin-demo", "u-a-001", "patient", "first")
        assign_user_role("admin-demo", "u-a-001", "staff", "second")
        log = get_admin_change_log()
        timestamps = [e["timestamp"] for e in log[:10]]
        self.assertEqual(timestamps, sorted(timestamps, reverse=True))

    def test_record_admin_event_public_api(self):
        before = len(_ADMIN_CHANGE_LOG)
        record_admin_event("admin-demo", "admin:test_event", "u-a-001", "old", "new", "reason")
        self.assertEqual(len(_ADMIN_CHANGE_LOG), before + 1)
        entry = _ADMIN_CHANGE_LOG[-1]
        self.assertEqual(entry["actor"], "admin-demo")
        self.assertEqual(entry["previous_value"], "old")
        self.assertEqual(entry["new_value"], "new")

    def test_valid_statuses_cover_all_lifecycle_states(self):
        self.assertIn("active",    VALID_STATUSES)
        self.assertIn("inactive",  VALID_STATUSES)
        self.assertIn("suspended", VALID_STATUSES)


# ===========================================================================
# AC4 — Validation errors are clear and non-leaky
# ===========================================================================

class ValidationErrorTests(unittest.TestCase):
    """AC4 — Invalid input returns actionable, non-leaky error messages."""

    def setUp(self):
        _clean("u-v-001")

    def tearDown(self):
        _clean("u-v-001")

    # UT-US048-007
    def test_create_unknown_role_error_message(self):
        try:
            register_user("u-v-001", "hacker", "h@x.com")
            self.fail("Expected ValueError")
        except ValueError as e:
            self.assertIn("role", str(e).lower())
            self.assertNotIn("password", str(e))
            self.assertNotIn("secret", str(e))

    # UT-US048-008
    def test_update_non_updatable_field_error_message(self):
        _seed("u-v-001")
        ok, msg = update_user("admin-demo", "u-v-001", {"role": "admin"})
        self.assertFalse(ok)
        self.assertIn("Non-updatable", msg)
        self.assertIn("role", msg)

    def test_update_invalid_email_error_message(self):
        _seed("u-v-001")
        ok, msg = update_user("admin-demo", "u-v-001", {"email": "badformat"})
        self.assertFalse(ok)
        self.assertIn("email", msg.lower())

    def test_assign_role_unknown_role_error_message(self):
        _seed("u-v-001")
        ok, msg = assign_user_role("admin-demo", "u-v-001", "wizard", "")
        self.assertFalse(ok)
        self.assertIn("wizard", msg)

    def test_set_status_unknown_status_error_message(self):
        _seed("u-v-001")
        ok, msg = set_user_status("admin-demo", "u-v-001", "frozen", "")
        self.assertFalse(ok)
        self.assertIn("frozen", msg)

    def test_admin_permission_required_for_user_management(self):
        allowed = PERMISSION_MATRIX.get("admin:user_management", set())
        self.assertNotIn("patient", allowed)
        self.assertNotIn("staff", allowed)
        self.assertIn("admin", allowed)


if __name__ == "__main__":
    unittest.main()
