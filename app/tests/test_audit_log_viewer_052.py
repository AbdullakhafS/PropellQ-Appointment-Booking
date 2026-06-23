"""
EP-005 US-052: Admin Audit Log Viewer — Tests

Covers:
  UT-US052-001  Admin-only access and paginated log list (task_052_001)
  UT-US052-002  Audit filter and search controls (task_052_002)
  UT-US052-003  Audit entry detail panel with masking (task_052_003)
  UT-US052-004  CSV / JSON export with filter and redaction (task_052_004)
  UT-US052-005  Security enforcement and export-vs-query consistency (task_052_005)
"""
import io
import json
import os
import sys
import unittest
from datetime import datetime, timezone
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.rbac import (
    _ADMIN_CHANGE_LOG,
    _AUDIT_SENSITIVE_KEYS,
    _USER_REGISTRY,
    assign_user_role,
    export_admin_change_log,
    get_admin_change_log,
    get_admin_change_log_entry,
    mask_audit_entry,
    query_admin_change_log,
    record_admin_event,
    register_user,
    require_permission,
    set_user_status,
    update_user,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clear():
    _ADMIN_CHANGE_LOG.clear()
    _USER_REGISTRY.clear()


def _env_admin(admin_id: str = "admin-052") -> dict[str, Any]:
    return {
        "HTTP_X_ROLE": "admin",
        "HTTP_X_ADMIN_ID": admin_id,
        "PATH_INFO": "/api/admin/change-log",
        "REQUEST_METHOD": "GET",
    }


def _env_patient() -> dict[str, Any]:
    return {
        "HTTP_X_ROLE": "patient",
        "HTTP_X_PATIENT_ID": "1",
        "PATH_INFO": "/api/admin/change-log",
        "REQUEST_METHOD": "GET",
    }


def _seed_entries(n: int = 3) -> list[str]:
    """Register users and generate n audit entries; return list of target user IDs."""
    targets = []
    for i in range(n):
        uid = f"target-{i}"
        register_user(uid, "staff", f"t{i}@test.com")
        actor = f"actor-{i}"
        assign_user_role(actor, uid, "admin", f"reason-{i}")
        targets.append(uid)
    return targets


# =============================================================================
# UT-US052-001: Admin-only access and paginated list (task_052_001)
# =============================================================================

class AuditLogViewerAccessTests(unittest.TestCase):
    """Admin-only log viewer route and paginated list (task_052_001)."""

    def setUp(self):
        _clear()

    def tearDown(self):
        _clear()

    def test_admin_role_can_query_change_log(self):
        result = query_admin_change_log()
        self.assertIn("entries", result)

    def test_non_admin_denied_on_require_permission(self):
        denial = require_permission(_env_patient(), "admin:change_log")
        self.assertIsNotNone(denial)

    def test_admin_not_denied(self):
        denial = require_permission(_env_admin(), "admin:change_log")
        self.assertIsNone(denial)

    def test_log_returns_entries_list(self):
        _seed_entries(3)
        result = query_admin_change_log()
        self.assertIsInstance(result["entries"], list)
        self.assertGreater(len(result["entries"]), 0)

    def test_result_includes_total(self):
        _seed_entries(2)
        result = query_admin_change_log()
        self.assertIn("total", result)
        self.assertIsInstance(result["total"], int)

    def test_pagination_page_size_limits_entries(self):
        _seed_entries(5)
        result = query_admin_change_log(page=1, page_size=2)
        self.assertLessEqual(len(result["entries"]), 2)

    def test_pagination_total_exceeds_page_size(self):
        _seed_entries(5)
        result = query_admin_change_log(page=1, page_size=2)
        self.assertGreater(result["total"], 2)
        self.assertGreater(result["pages"], 1)

    def test_page_2_returns_different_entries(self):
        _seed_entries(6)
        r1 = query_admin_change_log(page=1, page_size=3)
        r2 = query_admin_change_log(page=2, page_size=3)
        ids1 = {e.get("entry_id") for e in r1["entries"]}
        ids2 = {e.get("entry_id") for e in r2["entries"]}
        self.assertFalse(ids1 & ids2)  # No overlap

    def test_empty_log_returns_zero_total(self):
        result = query_admin_change_log()
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["entries"], [])

    def test_entry_has_expected_fields(self):
        _seed_entries(1)
        result = query_admin_change_log()
        e = result["entries"][0]
        for field in ("entry_id", "timestamp", "actor", "action", "target_user_id"):
            self.assertIn(field, e, f"Missing field: {field}")

    def test_entries_ordered_newest_first(self):
        _seed_entries(3)
        result = query_admin_change_log()
        ts = [e["timestamp"] for e in result["entries"]]
        self.assertEqual(ts, sorted(ts, reverse=True))

    def test_entry_id_is_present_and_non_empty(self):
        _seed_entries(1)
        result = query_admin_change_log()
        self.assertTrue(result["entries"][0].get("entry_id"))

    def test_filters_echo_returned_in_result(self):
        result = query_admin_change_log(actor="test-actor", action="admin:role_assigned")
        self.assertEqual(result["filters"]["actor"], "test-actor")
        self.assertEqual(result["filters"]["action"], "admin:role_assigned")

    def test_page_size_capped_at_500(self):
        result = query_admin_change_log(page=1, page_size=99999)
        self.assertLessEqual(result["page_size"], 500)


# =============================================================================
# UT-US052-002: Filter and search controls (task_052_002)
# =============================================================================

class AuditFilterTests(unittest.TestCase):
    """Audit log filter correctness across all supported parameters (task_052_002)."""

    def setUp(self):
        _clear()
        # Seed two users with distinct actors and actions
        register_user("u-alice", "staff", "alice@test.com")
        register_user("u-bob", "staff", "bob@test.com")
        assign_user_role("actor-alice", "u-alice", "admin", "promotion")
        set_user_status("actor-bob", "u-bob", "inactive", "deactivation")
        # Add a general lifecycle event too
        update_user("actor-alice", "u-alice", {"email": "alice2@test.com"}, "email update")

    def tearDown(self):
        _clear()

    def test_filter_by_actor_returns_matching_entries(self):
        result = query_admin_change_log(actor="actor-alice")
        for e in result["entries"]:
            self.assertEqual(e["actor"], "actor-alice")

    def test_filter_by_actor_excludes_other_actors(self):
        result = query_admin_change_log(actor="actor-alice")
        self.assertTrue(all(e["actor"] == "actor-alice" for e in result["entries"]))
        self.assertFalse(any(e["actor"] == "actor-bob" for e in result["entries"]))

    def test_filter_by_action_role_assigned(self):
        result = query_admin_change_log(action="admin:role_assigned")
        self.assertGreater(result["total"], 0)
        for e in result["entries"]:
            self.assertEqual(e["action"], "admin:role_assigned")

    def test_filter_by_action_status_changed(self):
        result = query_admin_change_log(action="admin:status_changed")
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["entries"][0]["actor"], "actor-bob")

    def test_filter_by_target_user(self):
        result = query_admin_change_log(target_user="u-alice")
        for e in result["entries"]:
            self.assertEqual(e["target_user_id"], "u-alice")

    def test_filter_by_target_user_excludes_others(self):
        result = query_admin_change_log(target_user="u-bob")
        self.assertFalse(any(e["target_user_id"] == "u-alice" for e in result["entries"]))

    def test_filter_by_from_ts_excludes_earlier_entries(self):
        future = "2999-01-01T00:00:00+00:00"
        result = query_admin_change_log(from_ts=future)
        self.assertEqual(result["total"], 0)

    def test_filter_by_to_ts_excludes_later_entries(self):
        past = "2000-01-01T00:00:00+00:00"
        result = query_admin_change_log(to_ts=past)
        self.assertEqual(result["total"], 0)

    def test_from_ts_includes_all_recent_entries(self):
        past = "2000-01-01T00:00:00+00:00"
        result = query_admin_change_log(from_ts=past)
        self.assertGreater(result["total"], 0)

    def test_combined_actor_and_action_filter(self):
        result = query_admin_change_log(actor="actor-alice", action="admin:role_assigned")
        self.assertTrue(all(
            e["actor"] == "actor-alice" and e["action"] == "admin:role_assigned"
            for e in result["entries"]
        ))

    def test_unknown_actor_returns_empty(self):
        result = query_admin_change_log(actor="ghost-actor-xyz")
        self.assertEqual(result["total"], 0)

    def test_unknown_action_returns_empty(self):
        result = query_admin_change_log(action="admin:nonexistent_action")
        self.assertEqual(result["total"], 0)

    def test_unknown_target_user_returns_empty(self):
        result = query_admin_change_log(target_user="nobody-xyz")
        self.assertEqual(result["total"], 0)

    def test_no_filters_returns_all(self):
        result = query_admin_change_log()
        self.assertGreaterEqual(result["total"], 3)

    def test_backward_compat_get_admin_change_log_still_works(self):
        """Existing get_admin_change_log() still returns a plain list."""
        entries = get_admin_change_log(actor="actor-alice")
        self.assertIsInstance(entries, list)

    def test_backward_compat_target_user_kwarg(self):
        """target_user keyword-only param works on existing function."""
        entries = get_admin_change_log(target_user="u-alice")
        self.assertIsInstance(entries, list)
        for e in entries:
            self.assertEqual(e["target_user_id"], "u-alice")


# =============================================================================
# UT-US052-003: Audit entry detail panel (task_052_003)
# =============================================================================

class AuditEntryDetailTests(unittest.TestCase):
    """Detail panel — lookup by entry_id and sensitive field masking (task_052_003)."""

    def setUp(self):
        _clear()
        register_user("det-u1", "staff", "det@det.com")
        self.target = "det-u1"
        # Trigger an update that stores email in previous/new value
        update_user("admin-det", "det-u1", {"email": "new@det.com"}, "email change")
        assign_user_role("admin-det", "det-u1", "admin", "promotion")

    def tearDown(self):
        _clear()

    def test_entry_id_generated_on_creation(self):
        result = query_admin_change_log(target_user=self.target)
        for e in result["entries"]:
            self.assertIn("entry_id", e)
            self.assertTrue(e["entry_id"])

    def test_get_entry_by_id_returns_entry(self):
        result = query_admin_change_log(target_user=self.target)
        eid = result["entries"][0]["entry_id"]
        entry = get_admin_change_log_entry(eid)
        self.assertIsNotNone(entry)
        self.assertEqual(entry["entry_id"], eid)

    def test_unknown_entry_id_returns_none(self):
        entry = get_admin_change_log_entry("00000000-0000-0000-0000-000000000000")
        self.assertIsNone(entry)

    def test_sensitive_email_field_masked_in_detail(self):
        result = query_admin_change_log(action="admin:user_updated")
        entry = result["entries"][0]
        masked = mask_audit_entry(entry)
        if isinstance(masked.get("new_value"), dict) and "email" in masked["new_value"]:
            self.assertEqual(masked["new_value"]["email"], "***")
        if isinstance(masked.get("previous_value"), dict) and "email" in masked["previous_value"]:
            self.assertEqual(masked["previous_value"]["email"], "***")

    def test_non_sensitive_fields_not_masked(self):
        result = query_admin_change_log(action="admin:role_assigned")
        entry = result["entries"][0]
        masked = mask_audit_entry(entry)
        self.assertEqual(masked["actor"], entry["actor"])
        self.assertEqual(masked["action"], entry["action"])
        self.assertEqual(masked["target_user_id"], entry["target_user_id"])
        self.assertEqual(masked["timestamp"], entry["timestamp"])

    def test_mask_handles_non_dict_previous_value(self):
        # role changes store string values
        result = query_admin_change_log(action="admin:role_assigned")
        entry = result["entries"][0]
        masked = mask_audit_entry(entry)
        # previous_value is a plain string (the old role) — should pass through
        self.assertIsNotNone(masked["previous_value"])

    def test_mask_preserves_all_keys(self):
        result = query_admin_change_log()
        entry = result["entries"][0]
        masked = mask_audit_entry(entry)
        self.assertEqual(set(masked.keys()), set(entry.keys()))

    def test_detail_has_required_display_fields(self):
        result = query_admin_change_log(target_user=self.target)
        entry = result["entries"][0]
        for field in ("entry_id", "timestamp", "actor", "action", "target_user_id", "reason"):
            self.assertIn(field, entry, f"Missing required detail field: {field}")

    def test_mask_does_not_modify_original(self):
        result = query_admin_change_log(action="admin:user_updated")
        if result["entries"]:
            entry = result["entries"][0]
            original_new_value = dict(entry.get("new_value") or {})
            mask_audit_entry(entry)
            # Original dict must be unchanged
            self.assertEqual(entry.get("new_value"), original_new_value or entry.get("new_value"))

    def test_audit_sensitive_keys_contains_email(self):
        self.assertIn("email", _AUDIT_SENSITIVE_KEYS)

    def test_audit_sensitive_keys_contains_phone(self):
        self.assertIn("phone", _AUDIT_SENSITIVE_KEYS)


# =============================================================================
# UT-US052-004: CSV / JSON export (task_052_004)
# =============================================================================

class ExportTests(unittest.TestCase):
    """Export respects filters, masks sensitive data, and formats correctly (task_052_004)."""

    def setUp(self):
        _clear()
        register_user("exp-u1", "staff", "exp1@exp.com")
        register_user("exp-u2", "admin", "exp2@exp.com")
        assign_user_role("actor-exp-1", "exp-u1", "admin", "r1")
        set_user_status("actor-exp-2", "exp-u2", "inactive", "r2")
        update_user("actor-exp-1", "exp-u1", {"email": "new_exp@exp.com"}, "email update")

    def tearDown(self):
        _clear()

    # ── JSON export ──────────────────────────────────────────────────────

    def test_json_export_returns_bytes(self):
        content, ct, fn = export_admin_change_log(fmt="json")
        self.assertIsInstance(content, bytes)

    def test_json_export_content_type(self):
        _, ct, _ = export_admin_change_log(fmt="json")
        self.assertEqual(ct, "application/json")

    def test_json_export_filename_has_json_extension(self):
        _, _, fn = export_admin_change_log(fmt="json")
        self.assertTrue(fn.endswith(".json"))

    def test_json_export_is_valid_json(self):
        content, _, _ = export_admin_change_log(fmt="json")
        data = json.loads(content)
        self.assertIn("entries", data)
        self.assertIn("total", data)
        self.assertIn("exported_at", data)

    def test_json_export_contains_all_entries(self):
        content, _, _ = export_admin_change_log(fmt="json")
        data = json.loads(content)
        self.assertGreaterEqual(data["total"], 3)

    def test_json_export_masks_sensitive_fields(self):
        content, _, _ = export_admin_change_log(fmt="json")
        data = json.loads(content)
        for e in data["entries"]:
            nv = e.get("new_value")
            if isinstance(nv, dict) and "email" in nv:
                self.assertEqual(nv["email"], "***")

    # ── CSV export ──────────────────────────────────────────────────────

    def test_csv_export_returns_bytes(self):
        content, ct, fn = export_admin_change_log(fmt="csv")
        self.assertIsInstance(content, bytes)

    def test_csv_export_content_type(self):
        _, ct, _ = export_admin_change_log(fmt="csv")
        self.assertEqual(ct, "text/csv")

    def test_csv_export_filename_has_csv_extension(self):
        _, _, fn = export_admin_change_log(fmt="csv")
        self.assertTrue(fn.endswith(".csv"))

    def test_csv_export_has_header_row(self):
        content, _, _ = export_admin_change_log(fmt="csv")
        first_line = content.decode("utf-8").splitlines()[0]
        self.assertIn("entry_id", first_line)
        self.assertIn("actor", first_line)
        self.assertIn("action", first_line)
        self.assertIn("timestamp", first_line)

    def test_csv_export_contains_data_rows(self):
        content, _, _ = export_admin_change_log(fmt="csv")
        lines = content.decode("utf-8").strip().splitlines()
        self.assertGreater(len(lines), 1)  # header + at least one data row

    def test_csv_export_masks_sensitive_fields(self):
        content, _, _ = export_admin_change_log(fmt="csv")
        # email values must not appear unmasked in the CSV bytes
        self.assertNotIn(b"new_exp@exp.com", content)
        self.assertNotIn(b"exp1@exp.com", content)

    # ── Filter + export ─────────────────────────────────────────────────

    def test_export_respects_actor_filter(self):
        content, _, _ = export_admin_change_log(actor="actor-exp-1", fmt="json")
        data = json.loads(content)
        for e in data["entries"]:
            self.assertEqual(e["actor"], "actor-exp-1")

    def test_export_respects_action_filter(self):
        content, _, _ = export_admin_change_log(action="admin:role_assigned", fmt="json")
        data = json.loads(content)
        self.assertGreater(data["total"], 0)
        for e in data["entries"]:
            self.assertEqual(e["action"], "admin:role_assigned")

    def test_export_respects_target_user_filter(self):
        content, _, _ = export_admin_change_log(target_user="exp-u1", fmt="json")
        data = json.loads(content)
        for e in data["entries"]:
            self.assertEqual(e["target_user_id"], "exp-u1")

    def test_export_respects_date_filter_future_from(self):
        content, _, _ = export_admin_change_log(from_ts="2999-01-01T00:00:00+00:00", fmt="json")
        data = json.loads(content)
        self.assertEqual(data["total"], 0)

    def test_invalid_format_defaults_to_json(self):
        content, ct, fn = export_admin_change_log(fmt="xml")
        self.assertEqual(ct, "application/json")
        self.assertTrue(fn.endswith(".json"))

    def test_default_format_is_json(self):
        content, ct, fn = export_admin_change_log()
        self.assertEqual(ct, "application/json")

    def test_export_excludes_non_required_sensitive_fields(self):
        """Password hash must never appear in export output."""
        # Seed a password hash directly to simulate stored credential
        if _ADMIN_CHANGE_LOG:
            entry = _ADMIN_CHANGE_LOG[0]
            entry["previous_value"] = {"password_hash": "abc123secret"}
        content, _, _ = export_admin_change_log(fmt="json")
        self.assertNotIn(b"abc123secret", content)


# =============================================================================
# UT-US052-005a: Security Enforcement Validation (task_052_005)
# =============================================================================

class AuditViewerSecurityTests(unittest.TestCase):
    """Admin-only access enforcement across all three audit viewer operations (task_052_005)."""

    def setUp(self):
        _clear()
        register_user("sec-target", "staff", "sec@sec.com")
        assign_user_role("sec-admin", "sec-target", "admin", "promotion")
        set_user_status("sec-admin", "sec-target", "inactive", "deactivation")

    def tearDown(self):
        _clear()

    def _env(self, role: str, admin_id: str | None = None) -> dict:
        e = {
            "HTTP_X_ROLE": role,
            "PATH_INFO": "/api/admin/change-log",
            "REQUEST_METHOD": "GET",
        }
        if admin_id:
            e["HTTP_X_ADMIN_ID"] = admin_id
        return e

    # ── Change-log list endpoint ─────────────────────────────────────────

    def test_admin_permitted_on_change_log(self):
        denial = require_permission(self._env("admin", "admin-1"), "admin:change_log")
        self.assertIsNone(denial)

    def test_staff_denied_on_change_log(self):
        denial = require_permission(self._env("staff"), "admin:change_log")
        self.assertIsNotNone(denial)
        _, msg = denial
        self.assertIn("not authorised", msg)

    def test_patient_denied_on_change_log(self):
        denial = require_permission(self._env("patient"), "admin:change_log")
        self.assertIsNotNone(denial)

    def test_unknown_role_denied_on_change_log(self):
        denial = require_permission(self._env("superadmin"), "admin:change_log")
        self.assertIsNotNone(denial)

    # ── Entry detail endpoint (same permission) ──────────────────────────

    def test_admin_permitted_on_entry_detail(self):
        e = self._env("admin", "admin-1")
        e["PATH_INFO"] = "/api/admin/change-log/entry/abc"
        denial = require_permission(e, "admin:change_log")
        self.assertIsNone(denial)

    def test_staff_denied_on_entry_detail(self):
        e = self._env("staff")
        e["PATH_INFO"] = "/api/admin/change-log/entry/abc"
        denial = require_permission(e, "admin:change_log")
        self.assertIsNotNone(denial)

    def test_patient_denied_on_entry_detail(self):
        e = self._env("patient")
        e["PATH_INFO"] = "/api/admin/change-log/entry/abc"
        denial = require_permission(e, "admin:change_log")
        self.assertIsNotNone(denial)

    # ── Export endpoint (same permission) ────────────────────────────────

    def test_admin_permitted_on_export(self):
        e = self._env("admin", "admin-1")
        e["PATH_INFO"] = "/api/admin/change-log/export"
        denial = require_permission(e, "admin:change_log")
        self.assertIsNone(denial)

    def test_staff_denied_on_export(self):
        e = self._env("staff")
        e["PATH_INFO"] = "/api/admin/change-log/export"
        denial = require_permission(e, "admin:change_log")
        self.assertIsNotNone(denial)

    def test_patient_denied_on_export(self):
        e = self._env("patient")
        e["PATH_INFO"] = "/api/admin/change-log/export"
        denial = require_permission(e, "admin:change_log")
        self.assertIsNotNone(denial)

    # ── Denial is audited ────────────────────────────────────────────────

    def test_unauthorized_access_emits_audit_event(self):
        from src.rbac import _AUDIT_LOG
        _AUDIT_LOG.clear()
        require_permission(self._env("staff"), "admin:change_log")
        self.assertGreater(len(_AUDIT_LOG), 0)
        self.assertEqual(_AUDIT_LOG[-1]["outcome"], "denied")

    def test_denial_tuple_structure_is_role_and_message(self):
        denial = require_permission(self._env("patient"), "admin:change_log")
        self.assertIsNotNone(denial)
        role, msg = denial
        self.assertEqual(role, "patient")
        self.assertIsInstance(msg, str)
        self.assertGreater(len(msg), 0)

    def test_admin_permission_matrix_includes_change_log(self):
        from src.rbac import check_permission
        self.assertTrue(check_permission("admin", "admin:change_log"))

    def test_staff_permission_matrix_excludes_change_log(self):
        from src.rbac import check_permission
        self.assertFalse(check_permission("staff", "admin:change_log"))

    def test_patient_permission_matrix_excludes_change_log(self):
        from src.rbac import check_permission
        self.assertFalse(check_permission("patient", "admin:change_log"))


# =============================================================================
# UT-US052-005b: Export-vs-Query Consistency (task_052_005)
# =============================================================================

class ExportConsistencyTests(unittest.TestCase):
    """Export and on-screen (query) results are identical for the same filters (task_052_005)."""

    def setUp(self):
        _clear()
        register_user("cons-u1", "staff", "c1@c.com")
        register_user("cons-u2", "admin", "c2@c.com")
        register_user("cons-u3", "staff", "c3@c.com")
        assign_user_role("cons-actor-a", "cons-u1", "admin", "r1")
        set_user_status("cons-actor-b", "cons-u2", "inactive", "r2")
        assign_user_role("cons-actor-a", "cons-u3", "admin", "r3")
        update_user("cons-actor-b", "cons-u1", {"email": "new@c.com"}, "email")

    def tearDown(self):
        _clear()

    def _query_ids(self, **kwargs) -> list[str]:
        result = query_admin_change_log(**kwargs, page=1, page_size=500)
        return [e["entry_id"] for e in result["entries"]]

    def _export_ids(self, fmt: str = "json", **kwargs) -> list[str]:
        content, _, _ = export_admin_change_log(**kwargs, fmt=fmt)
        data = json.loads(content)
        return [e["entry_id"] for e in data["entries"]]

    def _csv_entry_ids(self, **kwargs) -> list[str]:
        import csv
        content, _, _ = export_admin_change_log(**kwargs, fmt="csv")
        reader = csv.DictReader(content.decode("utf-8").splitlines())
        return [row["entry_id"] for row in reader if row.get("entry_id")]

    # ── Unfiltered consistency ───────────────────────────────────────────

    def test_json_export_entry_ids_match_query(self):
        q_ids = self._query_ids()
        e_ids = self._export_ids()
        self.assertEqual(sorted(q_ids), sorted(e_ids))

    def test_csv_export_row_count_matches_query_total(self):
        result = query_admin_change_log(page=1, page_size=500)
        csv_ids = self._csv_entry_ids()
        self.assertEqual(len(csv_ids), result["total"])

    def test_csv_entry_ids_match_query_entry_ids(self):
        q_ids = self._query_ids()
        csv_ids = self._csv_entry_ids()
        self.assertEqual(sorted(q_ids), sorted(csv_ids))

    # ── Filter-scoped consistency ────────────────────────────────────────

    def test_actor_filter_consistent_across_query_and_export(self):
        q_ids = self._query_ids(actor="cons-actor-a")
        e_ids = self._export_ids(actor="cons-actor-a")
        self.assertEqual(sorted(q_ids), sorted(e_ids))

    def test_action_filter_consistent_across_query_and_export(self):
        q_ids = self._query_ids(action="admin:role_assigned")
        e_ids = self._export_ids(action="admin:role_assigned")
        self.assertEqual(sorted(q_ids), sorted(e_ids))

    def test_target_user_filter_consistent_across_query_and_export(self):
        q_ids = self._query_ids(target_user="cons-u1")
        e_ids = self._export_ids(target_user="cons-u1")
        self.assertEqual(sorted(q_ids), sorted(e_ids))

    def test_future_date_filter_gives_empty_in_both(self):
        q = query_admin_change_log(from_ts="2999-01-01T00:00:00+00:00")
        content, _, _ = export_admin_change_log(from_ts="2999-01-01T00:00:00+00:00")
        e = json.loads(content)
        self.assertEqual(q["total"], 0)
        self.assertEqual(e["total"], 0)

    def test_past_date_filter_gives_same_results_in_both(self):
        past = "2000-01-01T00:00:00+00:00"
        q_ids = self._query_ids(from_ts=past)
        e_ids = self._export_ids(from_ts=past)
        self.assertEqual(sorted(q_ids), sorted(e_ids))

    # ── Detail vs list consistency ───────────────────────────────────────

    def test_detail_entry_matches_list_entry(self):
        result = query_admin_change_log(page=1, page_size=10)
        if not result["entries"]:
            return
        first = result["entries"][0]
        detail = get_admin_change_log_entry(first["entry_id"])
        self.assertIsNotNone(detail)
        # All fields present in the list entry must be present in detail
        for key in first:
            self.assertIn(key, detail, f"Field '{key}' missing from detail")

    def test_detail_action_matches_list_action(self):
        result = query_admin_change_log(action="admin:role_assigned")
        if not result["entries"]:
            return
        for e in result["entries"]:
            detail = get_admin_change_log_entry(e["entry_id"])
            self.assertIsNotNone(detail)
            self.assertEqual(detail["action"], e["action"])

    # ── Full pagination coverage ─────────────────────────────────────────

    def test_paginating_all_pages_yields_same_total(self):
        """Walking through all pages must collect every entry exactly once."""
        total_result = query_admin_change_log()
        total = total_result["total"]
        if total == 0:
            return

        collected = []
        page = 1
        page_size = 2
        while True:
            r = query_admin_change_log(page=page, page_size=page_size)
            collected.extend(e["entry_id"] for e in r["entries"])
            if page >= r["pages"]:
                break
            page += 1

        self.assertEqual(len(collected), total)
        self.assertEqual(len(set(collected)), total)  # no duplicates

    def test_export_total_field_matches_entries_length(self):
        content, _, _ = export_admin_change_log(fmt="json")
        data = json.loads(content)
        self.assertEqual(data["total"], len(data["entries"]))

    def test_filtered_export_total_matches_entries_length(self):
        content, _, _ = export_admin_change_log(actor="cons-actor-a", fmt="json")
        data = json.loads(content)
        self.assertEqual(data["total"], len(data["entries"]))


if __name__ == "__main__":
    unittest.main()
