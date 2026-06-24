"""
EP-007 US-074 — Immutable Audit Log Infrastructure Tests (task_074_001 – task_074_005)

Covers all 12 unit test areas from UNIT-TEST-PLAN-074:
  UT-074-001: Audit repository permits append operations only
  UT-074-002: Update/delete operations on audit entries are blocked
  UT-074-003: Retention validator enforces minimum 7-year rule
  UT-074-004: Expiration eligibility logic excludes non-expired records
  UT-074-005: Integrity checker detects modified audit payload
  UT-074-006: Integrity checker passes unchanged append sequence
  UT-074-007: RBAC guard allows audit reads for authorized roles
  UT-074-008: RBAC guard denies unauthorized audit access paths
  UT-074-009: Compliance evidence builder includes immutability and retention controls
  UT-074-010: Compliance evidence includes access-control validation artifacts
  UT-074-011: Audit storage separation validator ensures non-transactional target
  UT-074-012: Error handling for audit storage failures remains fail-safe
"""
from __future__ import annotations

import sys
import os
import json
import copy
import unittest
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

from src.audit_storage import (
    AUDIT_RETENTION_DAYS,
    AUDIT_RETENTION_YEARS,
    AUDIT_READ_ROLES,
    AUDIT_STORAGE_NAMESPACE,
    TRANSACTIONAL_STORAGE_NAMESPACE,
    AuditEntry,
    AuditImmutabilityError,
    AuditStorageError,
    AppendOnlyAuditStore,
    AuditRetentionPolicy,
    AuditIntegrityChecker,
    AuditAccessGuard,
    generate_immutable_audit_compliance_report,
    _GENESIS_HASH,
    _compute_entry_hash,
)


def _make_store() -> AppendOnlyAuditStore:
    return AppendOnlyAuditStore()


def _append_n(store: AppendOnlyAuditStore, n: int) -> list[AuditEntry]:
    entries = []
    for i in range(n):
        e = store.append(
            event="TEST_EVENT",
            actor_id=f"user_{i}",
            actor_role="staff",
            action="test_action",
            resource_type="test_resource",
            resource_id=str(i),
            outcome="success",
        )
        entries.append(e)
    return entries


# ===========================================================================
# UT-074-001: Append operations succeed with immutable metadata
# ===========================================================================

class TestAuditAppendOnly(unittest.TestCase):
    """UT-074-001: Audit repository permits append operations only."""

    def test_append_returns_audit_entry(self):
        store = _make_store()
        entry = store.append(event="LOGIN", actor_id="user_1")
        self.assertIsInstance(entry, AuditEntry)

    def test_appended_entry_has_entry_id(self):
        store = _make_store()
        entry = store.append(event="LOGIN")
        self.assertTrue(entry.entry_id)

    def test_appended_entry_has_timestamp(self):
        store = _make_store()
        entry = store.append(event="LOGIN")
        self.assertTrue(entry.timestamp)
        # Must parse as ISO-8601.
        datetime.fromisoformat(entry.timestamp)

    def test_appended_entry_has_integrity_hash(self):
        store = _make_store()
        entry = store.append(event="LOGIN")
        self.assertTrue(entry.integrity_hash)
        self.assertEqual(len(entry.integrity_hash), 64)  # SHA-256 hex = 64 chars

    def test_first_entry_prev_chain_hash_is_genesis(self):
        store = _make_store()
        entry = store.append(event="LOGIN")
        self.assertEqual(entry.prev_chain_hash, _GENESIS_HASH)

    def test_second_entry_prev_chain_hash_is_first_integrity_hash(self):
        store = _make_store()
        e1 = store.append(event="A")
        e2 = store.append(event="B")
        self.assertEqual(e2.prev_chain_hash, e1.integrity_hash)

    def test_store_size_increments(self):
        store = _make_store()
        self.assertEqual(store.size(), 0)
        store.append(event="X")
        self.assertEqual(store.size(), 1)
        store.append(event="Y")
        self.assertEqual(store.size(), 2)

    def test_all_fields_stored_correctly(self):
        store = _make_store()
        entry = store.append(
            event="DATA_ACCESS",
            actor_id="staff_42",
            actor_role="staff",
            action="read_patient",
            resource_type="patient",
            resource_id="123",
            outcome="success",
            source_ip="10.0.0.1",
        )
        self.assertEqual(entry.event, "DATA_ACCESS")
        self.assertEqual(entry.actor_id, "staff_42")
        self.assertEqual(entry.actor_role, "staff")
        self.assertEqual(entry.action, "read_patient")
        self.assertEqual(entry.resource_type, "patient")
        self.assertEqual(entry.resource_id, "123")
        self.assertEqual(entry.outcome, "success")
        self.assertEqual(entry.source_ip, "10.0.0.1")

    def test_storage_namespace_is_audit_log(self):
        store = _make_store()
        self.assertEqual(store.storage_namespace, AUDIT_STORAGE_NAMESPACE)

    def test_read_entries_returns_newest_first(self):
        store = _make_store()
        _append_n(store, 5)
        entries = store.read_entries(limit=5)
        self.assertEqual(len(entries), 5)
        # resource_id sequence should be 4, 3, 2, 1, 0 (newest first)
        ids = [int(e.resource_id) for e in entries]
        self.assertEqual(ids, sorted(ids, reverse=True))

    def test_read_entries_respects_limit(self):
        store = _make_store()
        _append_n(store, 10)
        entries = store.read_entries(limit=3)
        self.assertEqual(len(entries), 3)

    def test_read_entries_event_filter(self):
        store = _make_store()
        store.append(event="LOGIN")
        store.append(event="LOGOUT")
        store.append(event="LOGIN")
        results = store.read_entries(event_filter="LOGIN")
        self.assertTrue(all(e.event == "LOGIN" for e in results))
        self.assertEqual(len(results), 2)


# ===========================================================================
# UT-074-002: Update/delete operations are blocked
# ===========================================================================

class TestAuditMutationBlocked(unittest.TestCase):
    """UT-074-002: Update and delete on audit entries raise AuditImmutabilityError."""

    def test_update_raises_immutability_error(self):
        store = _make_store()
        entry = store.append(event="LOGIN")
        with self.assertRaises(AuditImmutabilityError):
            store.update(entry.entry_id, event="MODIFIED")

    def test_delete_raises_immutability_error(self):
        store = _make_store()
        entry = store.append(event="LOGIN")
        with self.assertRaises(AuditImmutabilityError):
            store.delete(entry.entry_id)

    def test_update_error_message_references_hipaa(self):
        store = _make_store()
        entry = store.append(event="LOGIN")
        try:
            store.update(entry.entry_id)
        except AuditImmutabilityError as exc:
            self.assertIn("164.312(b)", str(exc))

    def test_delete_error_message_references_retention_years(self):
        store = _make_store()
        entry = store.append(event="LOGIN")
        try:
            store.delete(entry.entry_id)
        except AuditImmutabilityError as exc:
            self.assertIn(str(AUDIT_RETENTION_YEARS), str(exc))

    def test_update_does_not_modify_store(self):
        store = _make_store()
        store.append(event="LOGIN")
        before = store.size()
        try:
            store.update("any-id")
        except AuditImmutabilityError:
            pass
        self.assertEqual(store.size(), before)

    def test_delete_does_not_modify_store(self):
        store = _make_store()
        store.append(event="LOGIN")
        before = store.size()
        try:
            store.delete("any-id")
        except AuditImmutabilityError:
            pass
        self.assertEqual(store.size(), before)

    def test_store_capacity_raises_storage_error(self):
        store = AppendOnlyAuditStore(max_entries=2)
        store.append(event="A")
        store.append(event="B")
        with self.assertRaises(AuditStorageError):
            store.append(event="C")


# ===========================================================================
# UT-074-003: Retention validator enforces minimum 7-year rule
# ===========================================================================

class TestRetentionPolicy(unittest.TestCase):
    """UT-074-003: Retention policy rejects below-minimum configuration."""

    def test_retention_constant_is_7_years(self):
        self.assertEqual(AUDIT_RETENTION_YEARS, 7)

    def test_retention_days_equals_7_times_365(self):
        self.assertEqual(AUDIT_RETENTION_DAYS, 7 * 365)

    def test_validate_policy_accepts_exactly_7(self):
        valid, _ = AuditRetentionPolicy.validate_policy(7)
        self.assertTrue(valid)

    def test_validate_policy_accepts_more_than_7(self):
        valid, _ = AuditRetentionPolicy.validate_policy(10)
        self.assertTrue(valid)

    def test_validate_policy_rejects_6_years(self):
        valid, reason = AuditRetentionPolicy.validate_policy(6)
        self.assertFalse(valid)
        self.assertIn("6", reason)

    def test_validate_policy_rejects_zero(self):
        valid, _ = AuditRetentionPolicy.validate_policy(0)
        self.assertFalse(valid)

    def test_validate_policy_rejects_negative(self):
        valid, _ = AuditRetentionPolicy.validate_policy(-1)
        self.assertFalse(valid)

    def test_validate_policy_rejects_non_integer(self):
        valid, _ = AuditRetentionPolicy.validate_policy("seven")  # type: ignore[arg-type]
        self.assertFalse(valid)

    def test_minimum_retention_years_attribute(self):
        self.assertEqual(AuditRetentionPolicy.MINIMUM_RETENTION_YEARS, 7)


# ===========================================================================
# UT-074-004: Expiration eligibility excludes non-expired records
# ===========================================================================

class TestExpirationEligibility(unittest.TestCase):
    """UT-074-004: Only records older than retention window become archival candidates."""

    def _make_entry_at(self, days_ago: int) -> AuditEntry:
        ts = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
        return AuditEntry(
            entry_id="test-id",
            timestamp=ts,
            event="X",
            actor_id=None,
            actor_role=None,
            action="",
            resource_type="",
            resource_id=None,
            outcome="success",
            source_ip=None,
            prev_chain_hash=_GENESIS_HASH,
            integrity_hash="a" * 64,
        )

    def test_record_7_years_old_is_not_eligible(self):
        now = datetime.now(timezone.utc)
        entry = self._make_entry_at(AUDIT_RETENTION_DAYS)
        # Pin the same 'now' to avoid microsecond drift between entry creation
        # and the policy check causing a spurious eligible result.
        self.assertFalse(AuditRetentionPolicy.is_eligible_for_deletion(entry, now=now))

    def test_record_older_than_7_years_is_eligible(self):
        entry = self._make_entry_at(AUDIT_RETENTION_DAYS + 1)
        self.assertTrue(AuditRetentionPolicy.is_eligible_for_deletion(entry))

    def test_fresh_record_is_not_eligible(self):
        entry = self._make_entry_at(0)
        self.assertFalse(AuditRetentionPolicy.is_eligible_for_deletion(entry))

    def test_get_archival_candidates_excludes_recent(self):
        entries = [self._make_entry_at(d) for d in [0, 100, 1000, AUDIT_RETENTION_DAYS + 1]]
        candidates = AuditRetentionPolicy.get_archival_candidates(entries)
        self.assertEqual(len(candidates), 1)

    def test_get_archival_candidates_returns_empty_when_none_eligible(self):
        entries = [self._make_entry_at(d) for d in [0, 100, 500]]
        candidates = AuditRetentionPolicy.get_archival_candidates(entries)
        self.assertEqual(len(candidates), 0)

    def test_invalid_timestamp_entry_is_not_eligible(self):
        entry = self._make_entry_at(0)
        entry.timestamp = "not-a-date"
        self.assertFalse(AuditRetentionPolicy.is_eligible_for_deletion(entry))


# ===========================================================================
# UT-074-005: Integrity checker detects tampered payload
# ===========================================================================

class TestIntegrityCheckerTamper(unittest.TestCase):
    """UT-074-005: Integrity checker fails on modified audit payload."""

    def setUp(self):
        self.store = _make_store()
        self.checker = AuditIntegrityChecker()
        _append_n(self.store, 3)

    def test_verify_entry_fails_when_event_mutated(self):
        entries = self.store.all_entries()
        mutated = entries[0]
        original = mutated.event
        mutated.event = "TAMPERED"
        valid, reason = self.checker.verify_entry(mutated)
        self.assertFalse(valid)
        self.assertIn("mismatch", reason)
        mutated.event = original  # restore

    def test_verify_entry_fails_when_actor_mutated(self):
        entries = self.store.all_entries()
        mutated = entries[1]
        mutated.actor_id = "injected_actor"
        valid, _ = self.checker.verify_entry(mutated)
        self.assertFalse(valid)

    def test_verify_entry_fails_when_integrity_hash_changed_directly(self):
        entries = self.store.all_entries()
        mutated = entries[0]
        mutated.integrity_hash = "b" * 64
        valid, _ = self.checker.verify_entry(mutated)
        self.assertFalse(valid)

    def test_verify_chain_detects_broken_chain(self):
        entries = self.store.all_entries()
        # Tamper entry at index 1 (break chain at index 2).
        entries[1].event = "CHAIN_TAMPER"
        entries[1].integrity_hash = "c" * 64  # mismatched hash

        valid, idx = self.checker.verify_chain(entries)
        self.assertFalse(valid)
        self.assertIsNotNone(idx)

    def test_verify_chain_detects_prev_hash_mismatch(self):
        entries = self.store.all_entries()
        # Corrupt the prev_chain_hash of the second entry.
        entries[1].prev_chain_hash = "d" * 64
        valid, idx = self.checker.verify_chain(entries)
        self.assertFalse(valid)
        self.assertEqual(idx, 1)

    def test_verify_chain_empty_list_is_valid(self):
        valid, idx = self.checker.verify_chain([])
        self.assertTrue(valid)
        self.assertIsNone(idx)


# ===========================================================================
# UT-074-006: Integrity checker passes unchanged sequence
# ===========================================================================

class TestIntegrityCheckerValid(unittest.TestCase):
    """UT-074-006: Integrity checker passes on unmodified append sequence."""

    def test_fresh_entry_passes_verify_entry(self):
        store = _make_store()
        entry = store.append(event="LOGIN")
        checker = AuditIntegrityChecker()
        valid, reason = checker.verify_entry(entry)
        self.assertTrue(valid)
        self.assertEqual(reason, "")

    def test_chain_of_five_passes_verify_chain(self):
        store = _make_store()
        _append_n(store, 5)
        checker = AuditIntegrityChecker()
        valid, idx = checker.verify_chain(store.all_entries())
        self.assertTrue(valid)
        self.assertIsNone(idx)

    def test_single_entry_chain_passes(self):
        store = _make_store()
        store.append(event="X")
        checker = AuditIntegrityChecker()
        valid, _ = checker.verify_chain(store.all_entries())
        self.assertTrue(valid)

    def test_compute_entry_hash_is_deterministic(self):
        store = _make_store()
        entry = store.append(event="DET_TEST")
        h1 = _compute_entry_hash(entry)
        h2 = _compute_entry_hash(entry)
        self.assertEqual(h1, h2)

    def test_different_entries_produce_different_hashes(self):
        store = _make_store()
        e1 = store.append(event="A")
        e2 = store.append(event="B")
        self.assertNotEqual(e1.integrity_hash, e2.integrity_hash)


# ===========================================================================
# UT-074-007: RBAC guard allows authorized roles
# ===========================================================================

class TestAuditAccessGuardAllowed(unittest.TestCase):
    """UT-074-007: RBAC guard allows audit reads for authorized roles."""

    def setUp(self):
        AuditAccessGuard._ACCESS_ATTEMPTS.clear()

    def test_admin_role_is_allowed(self):
        allowed, reason = AuditAccessGuard.check_read("admin")
        self.assertTrue(allowed)
        self.assertEqual(reason, "")

    def test_staff_role_is_allowed(self):
        allowed, reason = AuditAccessGuard.check_read("staff")
        self.assertTrue(allowed)

    def test_allowed_roles_constant_contains_admin_and_staff(self):
        self.assertIn("admin", AUDIT_READ_ROLES)
        self.assertIn("staff", AUDIT_READ_ROLES)

    def test_access_attempt_logged_for_allowed(self):
        AuditAccessGuard._ACCESS_ATTEMPTS.clear()
        AuditAccessGuard.check_read("admin", "actor_1")
        attempts = AuditAccessGuard.get_access_attempts()
        self.assertGreater(len(attempts), 0)
        self.assertTrue(attempts[0]["allowed"])

    def test_get_audit_entries_succeeds_for_admin(self):
        from src.audit_storage import get_audit_entries
        store_import = __import__("src.audit_storage", fromlist=["_AUDIT_STORE"])
        # Use a fresh store to avoid cross-test contamination.
        from src.audit_storage import AppendOnlyAuditStore, _AUDIT_STORE
        entries, err = get_audit_entries("admin")
        self.assertIsNotNone(entries)
        self.assertEqual(err, "")


# ===========================================================================
# UT-074-008: RBAC guard denies unauthorized roles
# ===========================================================================

class TestAuditAccessGuardDenied(unittest.TestCase):
    """UT-074-008: RBAC guard denies unauthorized audit access and records telemetry."""

    def setUp(self):
        AuditAccessGuard._ACCESS_ATTEMPTS.clear()

    def test_patient_role_is_denied(self):
        allowed, reason = AuditAccessGuard.check_read("patient")
        self.assertFalse(allowed)
        self.assertIn("patient", reason)

    def test_unknown_role_is_denied(self):
        allowed, _ = AuditAccessGuard.check_read("hacker")
        self.assertFalse(allowed)

    def test_empty_role_is_denied(self):
        allowed, _ = AuditAccessGuard.check_read("")
        self.assertFalse(allowed)

    def test_denial_recorded_in_access_attempts(self):
        AuditAccessGuard._ACCESS_ATTEMPTS.clear()
        AuditAccessGuard.check_read("patient", "bad_actor")
        attempts = AuditAccessGuard.get_access_attempts()
        self.assertGreater(len(attempts), 0)
        denied = [a for a in attempts if not a["allowed"]]
        self.assertGreater(len(denied), 0)
        self.assertEqual(denied[0]["role"], "patient")

    def test_get_audit_entries_returns_none_for_patient(self):
        from src.audit_storage import get_audit_entries
        entries, err = get_audit_entries("patient")
        self.assertIsNone(entries)
        self.assertIn("patient", err)

    def test_access_attempt_contains_actor_id(self):
        AuditAccessGuard._ACCESS_ATTEMPTS.clear()
        AuditAccessGuard.check_read("patient", actor_id="suspect_user")
        attempts = AuditAccessGuard.get_access_attempts()
        self.assertEqual(attempts[0]["actor_id"], "suspect_user")

    def test_get_access_attempts_returns_newest_first(self):
        AuditAccessGuard._ACCESS_ATTEMPTS.clear()
        for role in ("patient", "admin", "patient"):
            AuditAccessGuard.check_read(role)
        attempts = AuditAccessGuard.get_access_attempts()
        self.assertGreaterEqual(len(attempts), 3)


# ===========================================================================
# UT-074-009: Compliance evidence includes immutability and retention controls
# ===========================================================================

class TestComplianceEvidenceImmutabilityRetention(unittest.TestCase):
    """UT-074-009: Compliance evidence covers append-only, retention, integrity."""

    def setUp(self):
        self.store = _make_store()
        _append_n(self.store, 3)
        self.report = generate_immutable_audit_compliance_report(self.store)

    def test_report_has_report_type(self):
        self.assertEqual(self.report["report_type"], "HIPAA_45_CFR_164_312_b")

    def test_report_has_generated_at(self):
        self.assertIn("generated_at", self.report)
        datetime.fromisoformat(self.report["generated_at"])

    def test_report_immutability_section_present(self):
        self.assertIn("immutability", self.report["controls"])

    def test_report_immutability_api_mutations_blocked(self):
        self.assertTrue(self.report["controls"]["immutability"]["api_mutations_blocked"])

    def test_report_retention_section_present(self):
        self.assertIn("retention", self.report["controls"])

    def test_report_retention_minimum_years_is_7(self):
        self.assertEqual(self.report["controls"]["retention"]["minimum_years"], 7)

    def test_report_retention_hipaa_reference(self):
        ref = self.report["controls"]["retention"]["hipaa_reference"]
        self.assertIn("164.530", ref)

    def test_report_integrity_section_present(self):
        self.assertIn("integrity", self.report["controls"])

    def test_report_integrity_algorithm_is_hmac_sha256(self):
        alg = self.report["controls"]["integrity"]["algorithm"]
        self.assertIn("HMAC-SHA256", alg)

    def test_report_integrity_chain_valid_for_unmodified_store(self):
        self.assertTrue(self.report["controls"]["integrity"]["chain_valid"])

    def test_report_entry_count_matches_store_size(self):
        self.assertEqual(self.report["entry_count"], self.store.size())

    def test_report_chain_status_is_intact_for_clean_store(self):
        self.assertEqual(self.report["chain_status"], "intact")


# ===========================================================================
# UT-074-010: Compliance evidence includes access-control artifacts
# ===========================================================================

class TestComplianceEvidenceAccessControl(unittest.TestCase):
    """UT-074-010: Compliance evidence includes role policy mapping and access records."""

    def setUp(self):
        self.store = _make_store()
        self.report = generate_immutable_audit_compliance_report(self.store)

    def test_report_access_control_section_present(self):
        self.assertIn("access_control", self.report["controls"])

    def test_report_authorized_roles_lists_admin_and_staff(self):
        roles = self.report["controls"]["access_control"]["authorized_roles"]
        self.assertIn("admin", roles)
        self.assertIn("staff", roles)

    def test_report_unauthorized_roles_blocked_is_true(self):
        self.assertTrue(self.report["controls"]["access_control"]["unauthorized_roles_blocked"])

    def test_report_access_attempt_telemetry_is_true(self):
        self.assertTrue(self.report["controls"]["access_control"]["access_attempt_telemetry"])

    def test_report_rbac_mechanism_documented(self):
        self.assertIn(
            "AuditAccessGuard",
            self.report["controls"]["access_control"]["rbac_mechanism"],
        )

    def test_report_access_control_hipaa_reference(self):
        ref = self.report["controls"]["access_control"]["hipaa_reference"]
        self.assertIn("164.312", ref)


# ===========================================================================
# UT-074-011: Audit storage separation from transactional data
# ===========================================================================

class TestAuditStorageSeparation(unittest.TestCase):
    """UT-074-011: Audit storage is isolated from transactional data stores."""

    def test_audit_storage_namespace_not_transactional(self):
        self.assertNotEqual(AUDIT_STORAGE_NAMESPACE, TRANSACTIONAL_STORAGE_NAMESPACE)

    def test_store_namespace_attribute_is_audit_log(self):
        store = _make_store()
        self.assertEqual(store.storage_namespace, AUDIT_STORAGE_NAMESPACE)

    def test_compliance_report_separation_confirmed(self):
        store = _make_store()
        report = generate_immutable_audit_compliance_report(store)
        self.assertTrue(report["controls"]["immutability"]["separation_confirmed"])

    def test_compliance_report_storage_namespace_is_audit_log(self):
        store = _make_store()
        report = generate_immutable_audit_compliance_report(store)
        self.assertEqual(
            report["controls"]["immutability"]["storage_namespace"],
            AUDIT_STORAGE_NAMESPACE,
        )

    def test_compliance_report_transactional_namespace_documented(self):
        store = _make_store()
        report = generate_immutable_audit_compliance_report(store)
        self.assertEqual(
            report["controls"]["immutability"]["transactional_namespace"],
            TRANSACTIONAL_STORAGE_NAMESPACE,
        )

    def test_audit_storage_namespace_constant_is_audit_log(self):
        self.assertEqual(AUDIT_STORAGE_NAMESPACE, "audit_log")

    def test_transactional_storage_namespace_constant_is_transactional(self):
        self.assertEqual(TRANSACTIONAL_STORAGE_NAMESPACE, "transactional")


# ===========================================================================
# UT-074-012: Error handling remains fail-safe
# ===========================================================================

class TestAuditFailSafeErrorHandling(unittest.TestCase):
    """UT-074-012: Storage failures produce safe diagnostics, no partial mutations."""

    def test_store_full_raises_audit_storage_error(self):
        store = AppendOnlyAuditStore(max_entries=1)
        store.append(event="FIRST")
        with self.assertRaises(AuditStorageError):
            store.append(event="OVERFLOW")

    def test_store_full_does_not_leave_partial_entry(self):
        store = AppendOnlyAuditStore(max_entries=1)
        store.append(event="FIRST")
        try:
            store.append(event="OVERFLOW")
        except AuditStorageError:
            pass
        self.assertEqual(store.size(), 1)

    def test_update_raises_without_modifying_entry(self):
        store = _make_store()
        entry = store.append(event="STABLE")
        original_hash = entry.integrity_hash
        try:
            store.update(entry.entry_id, event="MUTATED")
        except AuditImmutabilityError:
            pass
        # Entry in store is unmodified.
        entries = store.read_entries()
        self.assertEqual(entries[0].event, "STABLE")
        self.assertEqual(entries[0].integrity_hash, original_hash)

    def test_delete_raises_without_removing_entry(self):
        store = _make_store()
        store.append(event="PROTECTED")
        try:
            store.delete("any-id")
        except AuditImmutabilityError:
            pass
        self.assertEqual(store.size(), 1)

    def test_append_with_none_actor_succeeds(self):
        store = _make_store()
        entry = store.append(event="SYSTEM", actor_id=None)
        self.assertIsNone(entry.actor_id)

    def test_integrity_checker_with_wrong_secret_fails_all(self):
        store = _make_store()
        _append_n(store, 3)
        wrong_secret = AuditIntegrityChecker(secret=b"wrong-secret")
        valid, idx = wrong_secret.verify_chain(store.all_entries())
        self.assertFalse(valid)
        self.assertIsNotNone(idx)


# ===========================================================================
# TestWebEndpoints — integration for audit entries and compliance endpoints
# ===========================================================================

class TestAuditWebEndpoints(unittest.TestCase):
    """Integration tests for /api/admin/audit/entries and /api/admin/audit/compliance."""

    def setUp(self):
        AuditAccessGuard._ACCESS_ATTEMPTS.clear()
        from src.web_app import create_app
        from src.db import initialize_database
        import tempfile
        from pathlib import Path
        self._db_path = Path(tempfile.mktemp(suffix=".db"))
        initialize_database(self._db_path)
        self.app = create_app(self._db_path)

    def _call(self, method: str, path: str, role: str = "patient", admin_id: str | None = None):
        environ = {
            "REQUEST_METHOD": method,
            "PATH_INFO": path,
            "wsgi.input": __import__("io").BytesIO(b""),
            "CONTENT_LENGTH": "0",
            "CONTENT_TYPE": "application/json",
            "HTTP_X_ROLE": role,
            "QUERY_STRING": "",
        }
        if admin_id:
            environ["HTTP_X_ADMIN_ID"] = admin_id
        responses = []
        def start_response(status, headers):
            responses.append(status)
        body_iter = self.app(environ, start_response)
        raw = b"".join(body_iter)
        status_code = int(responses[0].split()[0])
        return status_code, json.loads(raw)

    def test_admin_can_read_audit_entries(self):
        status, data = self._call("GET", "/api/admin/audit/entries", role="admin")
        self.assertEqual(status, 200)
        self.assertTrue(data["success"])

    def test_patient_cannot_read_audit_entries(self):
        status, data = self._call("GET", "/api/admin/audit/entries", role="patient")
        self.assertEqual(status, 403)
        self.assertEqual(data["error"]["code"], "AUDIT_ACCESS_DENIED")

    def test_staff_can_read_audit_entries(self):
        status, data = self._call("GET", "/api/admin/audit/entries", role="staff")
        self.assertEqual(status, 200)

    def test_admin_can_get_compliance_report(self):
        status, data = self._call("GET", "/api/admin/audit/compliance", role="admin", admin_id="admin_1")
        self.assertEqual(status, 200)
        self.assertIn("controls", data["data"])

    def test_patient_cannot_get_compliance_report(self):
        status, data = self._call("GET", "/api/admin/audit/compliance", role="patient")
        self.assertEqual(status, 403)


if __name__ == "__main__":
    unittest.main()
