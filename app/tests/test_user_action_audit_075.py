"""
Tests for EP-007 US-075: Log All User Actions.

task_075_001 — Audit event schema: types, required fields, PHI exclusion.
task_075_002 — Login/access event writers: login, PHI access, appointments.
task_075_003 — Account-change event writers: create, role, status, update.
task_075_004 — Query interface and coverage report.

Design notes:
  - Uses isolated AppendOnlyAuditStore instances per test — avoids polluting
    the module-level _AUDIT_STORE and prevents cross-test contamination.
  - Does NOT import booking_service (avoids zoneinfo Windows crash).
  - Run via:
      cd app
      python -c "import sys; sys.path.insert(0,'.'); import unittest; ..."
"""
import sys
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Allow running from 'app/' directory
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.audit_storage import AppendOnlyAuditStore
from src.audit_events import (
    AuditEventType,
    AUDIT_SCHEMA_REQUIRED_FIELDS,
    AUDIT_PHI_EXCLUDED_FIELDS,
    AUDIT_EVENT_RESOURCE_MAP,
    _safe_resource_id,
    _hash_identity,
    log_login_success,
    log_login_failure,
    log_session_issued,
    log_phi_access,
    log_phi_modify,
    log_appointment_action,
    log_account_create,
    log_account_update,
    log_account_role_change,
    log_account_status_change,
    query_audit_events,
    get_audit_coverage_report,
)


def _fresh_store() -> AppendOnlyAuditStore:
    """Return a fresh in-memory audit store for test isolation."""
    return AppendOnlyAuditStore()


# ---------------------------------------------------------------------------
# task_075_001 — Schema and event type definitions
# ---------------------------------------------------------------------------

class TestAuditEventTypeCatalog(unittest.TestCase):
    """AuditEventType class carries all canonical event-type constants."""

    def test_auth_event_types_defined(self):
        self.assertEqual(AuditEventType.AUTH_LOGIN_SUCCESS,  "AUTH_LOGIN_SUCCESS")
        self.assertEqual(AuditEventType.AUTH_LOGIN_FAILURE,  "AUTH_LOGIN_FAILURE")
        self.assertEqual(AuditEventType.AUTH_LOGOUT,         "AUTH_LOGOUT")
        self.assertEqual(AuditEventType.AUTH_PASSWORD_RESET, "AUTH_PASSWORD_RESET")
        self.assertEqual(AuditEventType.AUTH_SESSION_ISSUE,  "AUTH_SESSION_ISSUE")
        self.assertEqual(AuditEventType.AUTH_SESSION_RENEW,  "AUTH_SESSION_RENEW")
        self.assertEqual(AuditEventType.AUTH_SESSION_EXPIRE, "AUTH_SESSION_EXPIRE")

    def test_phi_event_types_defined(self):
        self.assertEqual(AuditEventType.PHI_ACCESS, "PHI_ACCESS")
        self.assertEqual(AuditEventType.PHI_MODIFY, "PHI_MODIFY")

    def test_appointment_event_types_defined(self):
        self.assertEqual(AuditEventType.APPOINTMENT_BOOK,     "APPOINTMENT_BOOK")
        self.assertEqual(AuditEventType.APPOINTMENT_CHECKIN,  "APPOINTMENT_CHECKIN")
        self.assertEqual(AuditEventType.APPOINTMENT_CHECKOUT, "APPOINTMENT_CHECKOUT")

    def test_account_event_types_defined(self):
        self.assertEqual(AuditEventType.ACCOUNT_CREATE,        "ACCOUNT_CREATE")
        self.assertEqual(AuditEventType.ACCOUNT_UPDATE,        "ACCOUNT_UPDATE")
        self.assertEqual(AuditEventType.ACCOUNT_ROLE_CHANGE,   "ACCOUNT_ROLE_CHANGE")
        self.assertEqual(AuditEventType.ACCOUNT_STATUS_CHANGE, "ACCOUNT_STATUS_CHANGE")

    def test_all_types_returns_sorted_list(self):
        types = AuditEventType.all_types()
        self.assertIsInstance(types, list)
        self.assertGreater(len(types), 10)
        self.assertEqual(types, sorted(types))

    def test_all_types_contains_expected(self):
        types = AuditEventType.all_types()
        for expected in [
            "AUTH_LOGIN_SUCCESS", "AUTH_LOGIN_FAILURE", "PHI_ACCESS",
            "APPOINTMENT_BOOK", "ACCOUNT_CREATE", "ACCOUNT_ROLE_CHANGE",
        ]:
            self.assertIn(expected, types)


class TestAuditSchema(unittest.TestCase):
    """AUDIT_SCHEMA_REQUIRED_FIELDS and PHI exclusion frozensets."""

    def test_required_fields_present(self):
        for f in ("timestamp", "event", "actor_id", "actor_role", "action",
                  "resource_type", "outcome", "source_ip"):
            self.assertIn(f, AUDIT_SCHEMA_REQUIRED_FIELDS)

    def test_phi_excluded_fields_present(self):
        for f in ("email", "password", "token", "ssn", "name", "phone",
                  "date_of_birth", "clinical_notes", "medication_name"):
            self.assertIn(f, AUDIT_PHI_EXCLUDED_FIELDS)

    def test_phi_excluded_is_frozenset(self):
        self.assertIsInstance(AUDIT_PHI_EXCLUDED_FIELDS, frozenset)

    def test_schema_required_is_frozenset(self):
        self.assertIsInstance(AUDIT_SCHEMA_REQUIRED_FIELDS, frozenset)

    def test_resource_map_covers_all_types(self):
        for event_type in AuditEventType.all_types():
            self.assertIn(event_type, AUDIT_EVENT_RESOURCE_MAP, msg=f"Missing: {event_type}")


class TestSafeResourceId(unittest.TestCase):
    """_safe_resource_id normalises IDs to numeric strings."""

    def test_integer_input(self):
        self.assertEqual(_safe_resource_id(42), "42")

    def test_string_integer_input(self):
        self.assertEqual(_safe_resource_id("7"), "7")

    def test_none_input(self):
        self.assertIsNone(_safe_resource_id(None))

    def test_non_numeric_string_returns_none(self):
        self.assertIsNone(_safe_resource_id("alice@example.com"))
        self.assertIsNone(_safe_resource_id("patient_name"))

    def test_float_rounds_to_int(self):
        self.assertEqual(_safe_resource_id(3.0), "3")


class TestHashIdentity(unittest.TestCase):
    """_hash_identity one-way hashes a login identity."""

    def test_returns_hex_string(self):
        result = _hash_identity("user@example.com")
        self.assertIsInstance(result, str)
        int(result, 16)  # must be valid hex

    def test_consistent(self):
        self.assertEqual(_hash_identity("alice"), _hash_identity("alice"))

    def test_different_inputs_different_hashes(self):
        self.assertNotEqual(_hash_identity("alice"), _hash_identity("bob"))

    def test_does_not_contain_original(self):
        result = _hash_identity("sensitive_email@example.com")
        self.assertNotIn("sensitive_email", result)
        self.assertNotIn("@", result)


# ---------------------------------------------------------------------------
# task_075_002 — Login and access event writers
# ---------------------------------------------------------------------------

class TestLoginSuccessWriter(unittest.TestCase):
    def test_appends_correct_event_type(self):
        store = _fresh_store()
        e = log_login_success("user1", "patient", "10.0.0.1", store=store)
        self.assertEqual(e.event, AuditEventType.AUTH_LOGIN_SUCCESS)

    def test_stores_actor_id_and_role(self):
        store = _fresh_store()
        e = log_login_success("user1", "admin", "10.0.0.1", store=store)
        self.assertEqual(e.actor_id, "user1")
        self.assertEqual(e.actor_role, "admin")

    def test_outcome_is_success(self):
        store = _fresh_store()
        e = log_login_success("u", "staff", "127.0.0.1", store=store)
        self.assertEqual(e.outcome, "success")

    def test_source_ip_stored(self):
        store = _fresh_store()
        e = log_login_success("u", "patient", "192.168.1.5", store=store)
        self.assertEqual(e.source_ip, "192.168.1.5")

    def test_default_role_unknown(self):
        store = _fresh_store()
        e = log_login_success("u", source_ip=None, store=store)
        self.assertEqual(e.actor_role, "unknown")

    def test_resource_type_is_session(self):
        store = _fresh_store()
        e = log_login_success("u", "patient", store=store)
        self.assertEqual(e.resource_type, "session")

    def test_integrity_hash_set(self):
        store = _fresh_store()
        e = log_login_success("u", "admin", store=store)
        self.assertIsNotNone(e.integrity_hash)
        self.assertGreater(len(e.integrity_hash), 0)


class TestLoginFailureWriter(unittest.TestCase):
    def test_appends_correct_event_type(self):
        store = _fresh_store()
        e = log_login_failure("unknown_user@bad.com", "10.0.0.2", store=store)
        self.assertEqual(e.event, AuditEventType.AUTH_LOGIN_FAILURE)

    def test_identity_is_hashed_not_raw(self):
        store = _fresh_store()
        e = log_login_failure("sensitive@domain.com", store=store)
        self.assertNotIn("@", e.actor_id)
        self.assertNotIn("sensitive", e.actor_id)
        self.assertNotIn("domain", e.actor_id)

    def test_outcome_is_denied(self):
        store = _fresh_store()
        e = log_login_failure("x", store=store)
        self.assertEqual(e.outcome, "denied")

    def test_empty_identity_uses_unknown(self):
        store = _fresh_store()
        e = log_login_failure("", store=store)
        self.assertEqual(e.actor_id, "unknown")


class TestSessionIssuedWriter(unittest.TestCase):
    def test_appends_session_issue_event(self):
        store = _fresh_store()
        e = log_session_issued("user2", "staff", "10.1.1.1", store=store)
        self.assertEqual(e.event, AuditEventType.AUTH_SESSION_ISSUE)

    def test_actor_id_and_role(self):
        store = _fresh_store()
        e = log_session_issued("user2", "staff", store=store)
        self.assertEqual(e.actor_id, "user2")
        self.assertEqual(e.actor_role, "staff")

    def test_outcome_success(self):
        store = _fresh_store()
        e = log_session_issued("u", "admin", store=store)
        self.assertEqual(e.outcome, "success")


class TestPhiAccessWriter(unittest.TestCase):
    def test_appends_phi_access_event(self):
        store = _fresh_store()
        e = log_phi_access("staff1", "staff", "patient", 5, store=store)
        self.assertEqual(e.event, AuditEventType.PHI_ACCESS)

    def test_resource_id_normalised(self):
        store = _fresh_store()
        e = log_phi_access("s", "staff", "patient", 99, store=store)
        self.assertEqual(e.resource_id, "99")

    def test_non_numeric_resource_id_normalised_to_none(self):
        store = _fresh_store()
        e = log_phi_access("s", "staff", "patient", "not-a-number", store=store)
        self.assertIsNone(e.resource_id)

    def test_default_action_is_read(self):
        store = _fresh_store()
        e = log_phi_access("s", "staff", "patient", 1, store=store)
        self.assertEqual(e.action, "read")

    def test_custom_action(self):
        store = _fresh_store()
        e = log_phi_access("s", "staff", "patient", 1, action="read_clinical_profile", store=store)
        self.assertEqual(e.action, "read_clinical_profile")

    def test_outcome_is_success(self):
        store = _fresh_store()
        e = log_phi_access("s", "staff", "patient", 1, store=store)
        self.assertEqual(e.outcome, "success")


class TestPhiModifyWriter(unittest.TestCase):
    def test_appends_phi_modify_event(self):
        store = _fresh_store()
        e = log_phi_modify("doc1", "admin", "patient", 3, store=store)
        self.assertEqual(e.event, AuditEventType.PHI_MODIFY)

    def test_resource_type_and_id(self):
        store = _fresh_store()
        e = log_phi_modify("d", "admin", "clinical_record", 12, store=store)
        self.assertEqual(e.resource_type, "clinical_record")
        self.assertEqual(e.resource_id, "12")

    def test_default_action_modify(self):
        store = _fresh_store()
        e = log_phi_modify("d", "admin", "patient", 1, store=store)
        self.assertEqual(e.action, "modify")


class TestAppointmentActionWriter(unittest.TestCase):
    def test_book_action_maps_to_appointment_book(self):
        store = _fresh_store()
        e = log_appointment_action("u", "patient", "book", 7, store=store)
        self.assertEqual(e.event, AuditEventType.APPOINTMENT_BOOK)

    def test_checkin_action_maps_to_appointment_checkin(self):
        store = _fresh_store()
        e = log_appointment_action("u", "staff", "checkin", 8, store=store)
        self.assertEqual(e.event, AuditEventType.APPOINTMENT_CHECKIN)

    def test_checkout_action_maps_to_appointment_checkout(self):
        store = _fresh_store()
        e = log_appointment_action("u", "patient", "checkout", 9, store=store)
        self.assertEqual(e.event, AuditEventType.APPOINTMENT_CHECKOUT)

    def test_unknown_action_maps_to_phi_access(self):
        store = _fresh_store()
        e = log_appointment_action("u", "patient", "view_summary", 5, store=store)
        self.assertEqual(e.event, AuditEventType.PHI_ACCESS)

    def test_outcome_stored(self):
        store = _fresh_store()
        e = log_appointment_action("u", "patient", "book", 1, outcome="error", store=store)
        self.assertEqual(e.outcome, "error")

    def test_appointment_id_normalised(self):
        store = _fresh_store()
        e = log_appointment_action("u", "patient", "book", 42, store=store)
        self.assertEqual(e.resource_id, "42")

    def test_resource_type_is_appointment(self):
        store = _fresh_store()
        e = log_appointment_action("u", "patient", "book", 1, store=store)
        self.assertEqual(e.resource_type, "appointment")


# ---------------------------------------------------------------------------
# task_075_003 — Account-change event writers
# ---------------------------------------------------------------------------

class TestAccountCreateWriter(unittest.TestCase):
    def test_appends_account_create_event(self):
        store = _fresh_store()
        e = log_account_create("admin1", "new_user", "staff", store=store)
        self.assertEqual(e.event, AuditEventType.ACCOUNT_CREATE)

    def test_actor_is_admin_role(self):
        store = _fresh_store()
        e = log_account_create("admin1", "new_user", "patient", store=store)
        self.assertEqual(e.actor_role, "admin")

    def test_resource_id_is_target_user(self):
        store = _fresh_store()
        e = log_account_create("admin1", "target_user_99", "staff", store=store)
        self.assertEqual(e.resource_id, "target_user_99")

    def test_outcome_success(self):
        store = _fresh_store()
        e = log_account_create("admin1", "u", "patient", store=store)
        self.assertEqual(e.outcome, "success")

    def test_resource_type_is_user_account(self):
        store = _fresh_store()
        e = log_account_create("a", "u", "staff", store=store)
        self.assertEqual(e.resource_type, "user_account")


class TestAccountUpdateWriter(unittest.TestCase):
    def test_appends_account_update_event(self):
        store = _fresh_store()
        e = log_account_update("admin1", "user2", ["email", "status"], store=store)
        self.assertEqual(e.event, AuditEventType.ACCOUNT_UPDATE)

    def test_action_contains_field_names_not_values(self):
        store = _fresh_store()
        e = log_account_update("admin1", "user2", ["email", "phone"], store=store)
        # Field names should be in the action
        self.assertIn("email", e.action)
        self.assertIn("phone", e.action)
        # Raw PII values must not appear (we pass field names only)
        self.assertNotIn("@", e.action)

    def test_empty_fields_list_is_safe(self):
        store = _fresh_store()
        e = log_account_update("admin1", "user2", [], store=store)
        self.assertEqual(e.event, AuditEventType.ACCOUNT_UPDATE)

    def test_resource_id_is_target_user(self):
        store = _fresh_store()
        e = log_account_update("admin1", "target_99", ["status"], store=store)
        self.assertEqual(e.resource_id, "target_99")


class TestAccountRoleChangeWriter(unittest.TestCase):
    def test_appends_role_change_event(self):
        store = _fresh_store()
        e = log_account_role_change("admin1", "user3", "patient", "staff", store=store)
        self.assertEqual(e.event, AuditEventType.ACCOUNT_ROLE_CHANGE)

    def test_action_encodes_role_transition(self):
        store = _fresh_store()
        e = log_account_role_change("admin1", "user3", "patient", "staff", store=store)
        self.assertIn("patient", e.action)
        self.assertIn("staff", e.action)

    def test_resource_id_is_target_user(self):
        store = _fresh_store()
        e = log_account_role_change("admin1", "user3", "staff", "admin", store=store)
        self.assertEqual(e.resource_id, "user3")

    def test_actor_role_is_admin(self):
        store = _fresh_store()
        e = log_account_role_change("admin1", "u", "staff", "patient", store=store)
        self.assertEqual(e.actor_role, "admin")

    def test_outcome_success(self):
        store = _fresh_store()
        e = log_account_role_change("a", "u", "patient", "staff", store=store)
        self.assertEqual(e.outcome, "success")


class TestAccountStatusChangeWriter(unittest.TestCase):
    def test_appends_status_change_event(self):
        store = _fresh_store()
        e = log_account_status_change("admin1", "user4", "active", "inactive", store=store)
        self.assertEqual(e.event, AuditEventType.ACCOUNT_STATUS_CHANGE)

    def test_action_encodes_status_transition(self):
        store = _fresh_store()
        e = log_account_status_change("admin1", "user4", "active", "suspended", store=store)
        self.assertIn("active", e.action)
        self.assertIn("suspended", e.action)

    def test_resource_id_is_target_user(self):
        store = _fresh_store()
        e = log_account_status_change("admin1", "u4", "active", "inactive", store=store)
        self.assertEqual(e.resource_id, "u4")

    def test_actor_role_is_admin(self):
        store = _fresh_store()
        e = log_account_status_change("a", "u", "active", "inactive", store=store)
        self.assertEqual(e.actor_role, "admin")

    def test_outcome_success(self):
        store = _fresh_store()
        e = log_account_status_change("a", "u", "inactive", "active", store=store)
        self.assertEqual(e.outcome, "success")


# ---------------------------------------------------------------------------
# task_075_004 — Query interface and coverage report
# ---------------------------------------------------------------------------

class TestQueryAuditEvents(unittest.TestCase):
    def setUp(self):
        self.store = _fresh_store()
        log_login_success("user_a", "admin", "1.2.3.4", store=self.store)
        log_phi_access("user_b", "staff", "patient", 1, store=self.store)
        log_phi_access("user_b", "staff", "patient", 2, store=self.store)
        log_account_create("admin1", "new_user", "staff", store=self.store)

    def test_rbac_denied_for_patient_role(self):
        entries, err = query_audit_events("patient", "some_patient", store=self.store)
        self.assertIsNone(entries)
        self.assertGreater(len(err), 0)

    def test_rbac_allowed_for_admin(self):
        entries, err = query_audit_events("admin", "admin1", store=self.store)
        self.assertIsNotNone(entries)
        self.assertEqual(err, "")

    def test_rbac_allowed_for_staff(self):
        entries, err = query_audit_events("staff", "user_b", store=self.store)
        self.assertIsNotNone(entries)

    def test_no_filter_returns_all_entries(self):
        entries, _ = query_audit_events("admin", "admin1", store=self.store)
        self.assertEqual(len(entries), 4)

    def test_event_type_filter(self):
        entries, _ = query_audit_events(
            "admin", "admin1", event_type=AuditEventType.PHI_ACCESS, store=self.store
        )
        self.assertEqual(len(entries), 2)
        for e in entries:
            self.assertEqual(e.event, AuditEventType.PHI_ACCESS)

    def test_resource_type_filter(self):
        entries, _ = query_audit_events(
            "admin", "admin1", resource_type="session", store=self.store
        )
        for e in entries:
            self.assertEqual(e.resource_type, "session")

    def test_limit_respected(self):
        entries, _ = query_audit_events("admin", "admin1", limit=2, store=self.store)
        self.assertLessEqual(len(entries), 2)

    def test_newest_first_ordering(self):
        entries, _ = query_audit_events("admin", "admin1", store=self.store)
        timestamps = [e.timestamp for e in entries]
        self.assertEqual(timestamps, sorted(timestamps, reverse=True))

    def test_from_ts_filter_excludes_older(self):
        entries_all, _ = query_audit_events("admin", "admin1", store=self.store)
        if len(entries_all) < 2:
            self.skipTest("Need at least 2 entries for from_ts test")
        cut = entries_all[-1].timestamp  # oldest
        entries_filtered, _ = query_audit_events(
            "admin", "admin1", from_ts=cut, store=self.store
        )
        for e in entries_filtered:
            self.assertGreaterEqual(e.timestamp, cut)

    def test_to_ts_filter_excludes_newer(self):
        entries_all, _ = query_audit_events("admin", "admin1", store=self.store)
        if not entries_all:
            self.skipTest("No entries")
        cut = entries_all[0].timestamp  # newest
        entries_filtered, _ = query_audit_events(
            "admin", "admin1", to_ts=cut, store=self.store
        )
        for e in entries_filtered:
            self.assertLessEqual(e.timestamp, cut)


class TestAuditCoverageReport(unittest.TestCase):
    def setUp(self):
        self.store = _fresh_store()
        # Seed several event types
        log_login_success("u1", "admin", store=self.store)
        log_phi_access("u2", "staff", "patient", 1, store=self.store)
        log_account_create("admin1", "new_u", "staff", store=self.store)

    def test_rbac_denied_for_patient(self):
        report, err = get_audit_coverage_report("patient", store=self.store)
        self.assertIsNone(report)
        self.assertGreater(len(err), 0)

    def test_rbac_allowed_for_admin(self):
        report, err = get_audit_coverage_report("admin", "admin1", store=self.store)
        self.assertIsNotNone(report)
        self.assertEqual(err, "")

    def test_report_contains_required_keys(self):
        report, _ = get_audit_coverage_report("admin", "admin1", store=self.store)
        for key in ("total_entries", "event_type_counts", "covered_event_types",
                    "expected_event_types", "coverage_gaps", "date_range",
                    "schema_fields", "phi_excluded_fields", "compliance_note"):
            self.assertIn(key, report)

    def test_total_entries_accurate(self):
        report, _ = get_audit_coverage_report("admin", "admin1", store=self.store)
        self.assertEqual(report["total_entries"], 3)

    def test_event_type_counts_correct(self):
        report, _ = get_audit_coverage_report("admin", "admin1", store=self.store)
        counts = report["event_type_counts"]
        self.assertEqual(counts.get(AuditEventType.AUTH_LOGIN_SUCCESS, 0), 1)
        self.assertEqual(counts.get(AuditEventType.PHI_ACCESS, 0), 1)
        self.assertEqual(counts.get(AuditEventType.ACCOUNT_CREATE, 0), 1)

    def test_gaps_lists_missing_event_types(self):
        report, _ = get_audit_coverage_report("admin", "admin1", store=self.store)
        gaps = report["coverage_gaps"]
        # Types we didn't seed should be gaps
        self.assertIn(AuditEventType.APPOINTMENT_BOOK, gaps)
        self.assertIn(AuditEventType.ACCOUNT_ROLE_CHANGE, gaps)

    def test_covered_types_excludes_gaps(self):
        report, _ = get_audit_coverage_report("admin", "admin1", store=self.store)
        covered = set(report["covered_event_types"])
        gaps = set(report["coverage_gaps"])
        self.assertEqual(covered & gaps, set())  # no overlap

    def test_date_range_present(self):
        report, _ = get_audit_coverage_report("admin", "admin1", store=self.store)
        dr = report["date_range"]
        self.assertIsNotNone(dr["earliest"])
        self.assertIsNotNone(dr["latest"])
        self.assertLessEqual(dr["earliest"], dr["latest"])

    def test_phi_excluded_fields_in_report(self):
        report, _ = get_audit_coverage_report("admin", "admin1", store=self.store)
        phi_fields = set(report["phi_excluded_fields"])
        self.assertIn("email", phi_fields)
        self.assertIn("password", phi_fields)

    def test_compliance_note_in_report(self):
        report, _ = get_audit_coverage_report("admin", "admin1", store=self.store)
        self.assertIsInstance(report["compliance_note"], str)
        self.assertGreater(len(report["compliance_note"]), 20)

    def test_empty_store_date_range_is_none(self):
        empty = _fresh_store()
        report, _ = get_audit_coverage_report("admin", "admin1", store=empty)
        self.assertIsNone(report["date_range"]["earliest"])
        self.assertIsNone(report["date_range"]["latest"])

    def test_empty_store_zero_total(self):
        empty = _fresh_store()
        report, _ = get_audit_coverage_report("admin", "admin1", store=empty)
        self.assertEqual(report["total_entries"], 0)

    def test_all_types_appear_in_expected(self):
        report, _ = get_audit_coverage_report("admin", "admin1", store=self.store)
        expected = set(report["expected_event_types"])
        for t in AuditEventType.all_types():
            self.assertIn(t, expected)


# ---------------------------------------------------------------------------
# PHI exclusion correctness across all writers
# ---------------------------------------------------------------------------

class TestPhiExclusionAcrossWriters(unittest.TestCase):
    """Verify that no PHI field names/values appear in any stored audit entry."""

    PHI_TOKENS = ["@", "password", "ssn", "dob", "insurance", "clinical_notes"]

    def _assert_no_phi_tokens(self, entry):
        fields = [
            str(entry.actor_id or ""),
            str(entry.actor_role or ""),
            str(entry.action or ""),
            str(entry.resource_type or ""),
            str(entry.resource_id or ""),
            str(entry.outcome or ""),
            str(entry.source_ip or ""),
        ]
        combined = " ".join(fields).lower()
        for token in self.PHI_TOKENS:
            self.assertNotIn(token.lower(), combined, msg=f"PHI token '{token}' found in entry")

    def test_login_success_no_phi(self):
        store = _fresh_store()
        e = log_login_success("user_id_only", "patient", "10.0.0.1", store=store)
        self._assert_no_phi_tokens(e)

    def test_login_failure_identity_hashed(self):
        store = _fresh_store()
        e = log_login_failure("patient@clinic.org", "10.0.0.1", store=store)
        self.assertNotIn("@", e.actor_id)
        self.assertNotIn("clinic", e.actor_id)

    def test_phi_access_resource_id_numeric(self):
        store = _fresh_store()
        e = log_phi_access("staff1", "staff", "patient", 42, store=store)
        self.assertEqual(e.resource_id, "42")
        self._assert_no_phi_tokens(e)

    def test_account_update_field_names_only(self):
        store = _fresh_store()
        # Values not stored — only field names
        e = log_account_update("admin1", "user99", ["email", "phone"], store=store)
        self.assertIn("email", e.action)
        self.assertIn("phone", e.action)
        # No actual email value stored
        self.assertNotIn("@", e.action)


# ---------------------------------------------------------------------------
# task_075_004 — Web endpoint integration (web layer)
# ---------------------------------------------------------------------------

class TestAuditWebEndpoints(unittest.TestCase):
    """Light integration tests for the new /api/admin/audit/events and
    /api/admin/audit/coverage endpoints."""

    def setUp(self):
        import tempfile
        from pathlib import Path
        from src.web_app import create_app
        self._db = Path(tempfile.mktemp(suffix=".db"))
        self.app = create_app(self._db)

    def tearDown(self):
        try:
            if self._db.exists():
                self._db.unlink()
        except PermissionError:
            pass  # Windows: SQLite may hold file lock briefly

    def _call(self, method, path, headers=None, body=None):
        import io
        environ = {
            "REQUEST_METHOD": method,
            "PATH_INFO": path,
            "QUERY_STRING": "",
            "wsgi.input": io.BytesIO(body or b""),
            "CONTENT_LENGTH": str(len(body or b"")),
        }
        if headers:
            environ.update(headers)
        responses = []

        def start_response(status, headers):
            responses.append(status)

        result = self.app(environ, start_response)
        import json
        body_out = b"".join(result)
        return responses[0], json.loads(body_out)

    def test_audit_events_requires_admin_role(self):
        status, body = self._call("GET", "/api/admin/audit/events",
                                  headers={"HTTP_X_ROLE": "patient"})
        self.assertIn("403", status)

    def test_audit_events_admin_allowed(self):
        status, body = self._call("GET", "/api/admin/audit/events",
                                  headers={"HTTP_X_ROLE": "admin", "HTTP_X_ADMIN_ID": "admin1"})
        self.assertIn("200", status)
        self.assertTrue(body["success"])
        self.assertIn("entries", body["data"])

    def test_audit_coverage_requires_admin_role(self):
        status, body = self._call("GET", "/api/admin/audit/coverage",
                                  headers={"HTTP_X_ROLE": "staff"})
        self.assertIn("403", status)

    def test_audit_coverage_admin_allowed(self):
        status, body = self._call("GET", "/api/admin/audit/coverage",
                                  headers={"HTTP_X_ROLE": "admin", "HTTP_X_ADMIN_ID": "admin1"})
        self.assertIn("200", status)
        self.assertTrue(body["success"])
        data = body["data"]
        self.assertIn("total_entries", data)
        self.assertIn("coverage_gaps", data)
        self.assertIn("expected_event_types", data)

    def test_audit_events_returns_data_structure(self):
        status, body = self._call("GET", "/api/admin/audit/events",
                                  headers={"HTTP_X_ROLE": "admin", "HTTP_X_ADMIN_ID": "admin1"})
        data = body["data"]
        self.assertIn("entries", data)
        self.assertIn("returned", data)
        self.assertIsInstance(data["entries"], list)


if __name__ == "__main__":
    unittest.main(verbosity=2)
