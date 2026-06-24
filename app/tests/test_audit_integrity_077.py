"""
EP-007 US-077 — Log Integrity Checking (HMAC) Tests (task_077_001 – task_077_004)

Covers all 10 unit test areas from UNIT-TEST-PLAN-077:
  UT-077-001: New audit entry receives deterministic HMAC value
  UT-077-002: Integrity metadata is persisted in safe storage fields
  UT-077-003: Integrity checker flags modified payload with stored hash mismatch
  UT-077-004: Integrity checker passes unchanged payload/hash pairs
  UT-077-005: Periodic validation job scans entries on configured cadence
  UT-077-006: Validation failures are logged and surfaced for review
  UT-077-007: Compliance report includes integrity method and key-handling references
  UT-077-008: Compliance report includes validation run outcomes
  UT-077-009: Chained-hash sequence validator detects broken chain
  UT-077-010: Integrity checker error paths return safe diagnostics
"""
from __future__ import annotations

import copy
import os
import sys
import unittest
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

from src.audit_storage import (
    INTEGRITY_ALGORITHM,
    INTEGRITY_KEY_ENV_VAR,
    _AUDIT_INTEGRITY_SECRET,
    _GENESIS_HASH,
    _compute_entry_hash,
    AuditEntry,
    AuditImmutabilityError,
    AppendOnlyAuditStore,
    AuditIntegrityChecker,
    AuditIntegrityKeyService,
    AuditIntegrityValidationJob,
    IntegrityValidationResult,
    generate_integrity_compliance_report,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _make_store(*events: str) -> AppendOnlyAuditStore:
    """Return an AppendOnlyAuditStore pre-populated with the given event names."""
    store = AppendOnlyAuditStore()
    for evt in events:
        store.append(
            event=evt,
            actor_id="user_1",
            actor_role="staff",
            action="test_action",
            resource_type="appointment",
            resource_id="42",
            outcome="success",
            source_ip="127.0.0.1",
        )
    return store


def _fresh_entry(store: AppendOnlyAuditStore | None = None) -> AuditEntry:
    """Append one event and return the resulting AuditEntry."""
    s = store or AppendOnlyAuditStore()
    return s.append(
        event="TEST",
        actor_id="u1",
        actor_role="admin",
        action="read",
        resource_type="audit_log",
        resource_id="1",
        outcome="success",
    )


# ===========================================================================
# UT-077-001: New audit entry receives deterministic HMAC value
# ===========================================================================

class TestHmacGeneration(unittest.TestCase):
    """UT-077-001: Each appended entry gets a non-empty, deterministic HMAC hash."""

    def test_appended_entry_has_non_empty_integrity_hash(self):
        store = AppendOnlyAuditStore()
        entry = _fresh_entry(store)
        self.assertIsInstance(entry.integrity_hash, str)
        self.assertTrue(len(entry.integrity_hash) > 0)

    def test_integrity_hash_is_64_hex_chars(self):
        """HMAC-SHA256 digest is 32 bytes = 64 hex characters."""
        store = AppendOnlyAuditStore()
        entry = _fresh_entry(store)
        self.assertEqual(len(entry.integrity_hash), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in entry.integrity_hash))

    def test_same_payload_same_key_produces_same_hash(self):
        store = AppendOnlyAuditStore()
        e1 = _fresh_entry(store)
        recomputed = _compute_entry_hash(e1, _AUDIT_INTEGRITY_SECRET)
        self.assertEqual(e1.integrity_hash, recomputed)

    def test_different_entries_produce_different_hashes(self):
        store = AppendOnlyAuditStore()
        e1 = store.append(event="A", actor_role="staff", action="x", resource_type="r")
        e2 = store.append(event="B", actor_role="staff", action="y", resource_type="r")
        self.assertNotEqual(e1.integrity_hash, e2.integrity_hash)

    def test_algorithm_constant_is_hmac_sha256(self):
        self.assertEqual(INTEGRITY_ALGORITHM, "HMAC-SHA256")

    def test_hash_chaining_prev_chain_hash_set_on_first_entry(self):
        store = AppendOnlyAuditStore()
        e1 = _fresh_entry(store)
        self.assertEqual(e1.prev_chain_hash, _GENESIS_HASH)

    def test_hash_chaining_second_entry_uses_prev_hash(self):
        store = AppendOnlyAuditStore()
        e1 = _fresh_entry(store)
        e2 = _fresh_entry(store)
        self.assertEqual(e2.prev_chain_hash, e1.integrity_hash)


# ===========================================================================
# UT-077-002: Integrity metadata is persisted in safe storage fields
# ===========================================================================

class TestIntegrityMetadataSafety(unittest.TestCase):
    """UT-077-002: Hash metadata does not leak key material; stored in correct fields."""

    def test_integrity_hash_stored_in_dedicated_field(self):
        store = AppendOnlyAuditStore()
        entry = _fresh_entry(store)
        self.assertTrue(hasattr(entry, "integrity_hash"))

    def test_integrity_hash_field_not_equal_to_signing_key(self):
        store = AppendOnlyAuditStore()
        entry = _fresh_entry(store)
        self.assertNotEqual(entry.integrity_hash, _AUDIT_INTEGRITY_SECRET.decode())

    def test_key_service_summary_excludes_raw_key(self):
        summary = AuditIntegrityKeyService.key_summary()
        for value in summary.values():
            self.assertNotEqual(value, _AUDIT_INTEGRITY_SECRET.decode())

    def test_key_service_summary_contains_algorithm(self):
        summary = AuditIntegrityKeyService.key_summary()
        self.assertIn("algorithm", summary)
        self.assertEqual(summary["algorithm"], INTEGRITY_ALGORITHM)

    def test_key_service_summary_contains_key_source(self):
        summary = AuditIntegrityKeyService.key_summary()
        self.assertIn("key_source", summary)
        self.assertIn(INTEGRITY_KEY_ENV_VAR, summary["key_source"])

    def test_default_sentinel_key_flagged_as_misconfigured(self):
        """When the env var is not overridden the health should be 'misconfigured'."""
        # The test environment uses the default key.
        if AuditIntegrityKeyService.is_production_key():
            self.skipTest("Production key is configured in this environment.")
        summary = AuditIntegrityKeyService.key_summary()
        self.assertIn("misconfigured", summary["key_health"])

    def test_chain_hash_field_stored_separately_from_integrity_hash(self):
        store = AppendOnlyAuditStore()
        e1 = _fresh_entry(store)
        e2 = _fresh_entry(store)
        # The prev_chain_hash of e2 equals e1's integrity_hash, but the two
        # fields on e2 must be different values (since e2 has its own hash).
        self.assertNotEqual(e2.integrity_hash, e2.prev_chain_hash)


# ===========================================================================
# UT-077-003: Integrity checker flags modified payload
# ===========================================================================

class TestTamperDetection(unittest.TestCase):
    """UT-077-003: verify_entry returns False when entry content is mutated."""

    def test_mutated_event_field_detected(self):
        store = AppendOnlyAuditStore()
        entry = _fresh_entry(store)
        entry.event = "TAMPERED_EVENT"
        checker = AuditIntegrityChecker()
        valid, reason = checker.verify_entry(entry)
        self.assertFalse(valid)
        self.assertIn(entry.entry_id, reason)

    def test_mutated_actor_id_detected(self):
        store = AppendOnlyAuditStore()
        entry = _fresh_entry(store)
        entry.actor_id = "attacker"
        valid, _ = AuditIntegrityChecker().verify_entry(entry)
        self.assertFalse(valid)

    def test_mutated_outcome_detected(self):
        store = AppendOnlyAuditStore()
        entry = _fresh_entry(store)
        entry.outcome = "success_forged"
        valid, _ = AuditIntegrityChecker().verify_entry(entry)
        self.assertFalse(valid)

    def test_mutated_action_detected(self):
        store = AppendOnlyAuditStore()
        entry = _fresh_entry(store)
        entry.action = "delete_all"
        valid, _ = AuditIntegrityChecker().verify_entry(entry)
        self.assertFalse(valid)

    def test_verify_entry_returns_reason_string_on_failure(self):
        store = AppendOnlyAuditStore()
        entry = _fresh_entry(store)
        entry.event = "FORGED"
        _, reason = AuditIntegrityChecker().verify_entry(entry)
        self.assertIsInstance(reason, str)
        self.assertGreater(len(reason), 0)


# ===========================================================================
# UT-077-004: Integrity checker passes unchanged payload/hash pairs
# ===========================================================================

class TestIntegrityPass(unittest.TestCase):
    """UT-077-004: verify_entry returns True for unmodified entries."""

    def test_unmodified_entry_passes(self):
        store = AppendOnlyAuditStore()
        entry = _fresh_entry(store)
        valid, err = AuditIntegrityChecker().verify_entry(entry)
        self.assertTrue(valid)
        self.assertEqual(err, "")

    def test_multiple_unmodified_entries_all_pass(self):
        store = _make_store("AUTH_LOGIN", "DATA_ACCESS", "APPOINTMENT_CREATED")
        checker = AuditIntegrityChecker()
        for entry in store.all_entries():
            valid, _ = checker.verify_entry(entry)
            self.assertTrue(valid, f"Entry {entry.entry_id} failed unexpectedly")

    def test_verify_chain_intact_for_clean_store(self):
        store = _make_store("A", "B", "C")
        valid, broken_at = AuditIntegrityChecker().verify_chain(store.all_entries())
        self.assertTrue(valid)
        self.assertIsNone(broken_at)

    def test_empty_store_chain_is_valid(self):
        valid, broken_at = AuditIntegrityChecker().verify_chain([])
        self.assertTrue(valid)
        self.assertIsNone(broken_at)


# ===========================================================================
# UT-077-005: Periodic validation job scans entries on configured cadence
# ===========================================================================

class TestPeriodicValidationJobScanning(unittest.TestCase):
    """UT-077-005: Validation job checks all target entries in the store."""

    def test_run_returns_integrity_validation_result(self):
        store = _make_store("A", "B")
        job = AuditIntegrityValidationJob()
        result = job.run(store)
        self.assertIsInstance(result, IntegrityValidationResult)

    def test_run_checks_all_non_meta_entries(self):
        store = _make_store("EVENT_1", "EVENT_2", "EVENT_3")
        job = AuditIntegrityValidationJob()
        result = job.run(store)
        # All three entries (plus no meta-events appended) must be reflected.
        self.assertEqual(result.entries_checked, 3)

    def test_clean_store_run_has_zero_failures(self):
        store = _make_store("AUTH_LOGIN", "APPOINTMENT_BOOKED")
        result = AuditIntegrityValidationJob().run(store)
        self.assertEqual(result.failed, 0)

    def test_run_result_has_run_at_timestamp(self):
        store = AppendOnlyAuditStore()
        result = AuditIntegrityValidationJob().run(store)
        self.assertIsInstance(result.run_at, str)
        datetime.fromisoformat(result.run_at)  # must be parseable ISO-8601

    def test_emit_pass_event_appended_on_clean_run(self):
        store = _make_store("CLEAN_EVENT")
        before = store.size()
        AuditIntegrityValidationJob().run(store, emit_pass_event=True)
        after = store.size()
        self.assertEqual(after, before + 1)
        pass_events = [
            e for e in store.all_entries()
            if e.event == AuditIntegrityValidationJob.SUCCESS_EVENT
        ]
        self.assertEqual(len(pass_events), 1)

    def test_no_pass_event_on_dirty_run(self):
        store = AppendOnlyAuditStore()
        entry = _fresh_entry(store)
        entry.event = "TAMPERED"  # corrupt after append
        AuditIntegrityValidationJob().run(store, emit_pass_event=True)
        pass_events = [
            e for e in store.all_entries()
            if e.event == AuditIntegrityValidationJob.SUCCESS_EVENT
        ]
        self.assertEqual(len(pass_events), 0)


# ===========================================================================
# UT-077-006: Validation failures are logged and surfaced for review
# ===========================================================================

class TestValidationFailureLogging(unittest.TestCase):
    """UT-077-006: Tamper-alert events are appended for each failing entry."""

    def test_tampered_entry_triggers_failure_event(self):
        store = AppendOnlyAuditStore()
        entry = _fresh_entry(store)
        entry.event = "FORGED"
        AuditIntegrityValidationJob().run(store)
        failure_events = [
            e for e in store.all_entries()
            if e.event == AuditIntegrityValidationJob.FAILURE_EVENT
        ]
        self.assertGreaterEqual(len(failure_events), 1)

    def test_failure_event_references_tampered_entry_id(self):
        store = AppendOnlyAuditStore()
        entry = _fresh_entry(store)
        original_id = entry.entry_id
        entry.event = "FORGED"
        AuditIntegrityValidationJob().run(store)
        failure_events = [
            e for e in store.all_entries()
            if e.event == AuditIntegrityValidationJob.FAILURE_EVENT
        ]
        self.assertTrue(any(e.resource_id == original_id for e in failure_events))

    def test_failure_event_outcome_is_error(self):
        store = AppendOnlyAuditStore()
        entry = _fresh_entry(store)
        entry.action = "forged_action"
        AuditIntegrityValidationJob().run(store)
        failure_events = [
            e for e in store.all_entries()
            if e.event == AuditIntegrityValidationJob.FAILURE_EVENT
        ]
        for ev in failure_events:
            self.assertEqual(ev.outcome, "error")

    def test_failure_event_is_immutable(self):
        store = AppendOnlyAuditStore()
        entry = _fresh_entry(store)
        entry.actor_id = "forged"
        AuditIntegrityValidationJob().run(store)
        failure_events = [
            e for e in store.all_entries()
            if e.event == AuditIntegrityValidationJob.FAILURE_EVENT
        ]
        if failure_events:
            with self.assertRaises(AuditImmutabilityError):
                store.delete(failure_events[0].entry_id)

    def test_result_failure_ids_list_matches_tampered_entries(self):
        store = AppendOnlyAuditStore()
        e1 = _fresh_entry(store)
        e2 = _fresh_entry(store)
        e1.event = "TAMPERED_1"
        e2.event = "TAMPERED_2"
        result = AuditIntegrityValidationJob().run(store)
        self.assertEqual(result.failed, 2)
        self.assertIn(e1.entry_id, result.failure_ids)
        self.assertIn(e2.entry_id, result.failure_ids)


# ===========================================================================
# UT-077-007: Compliance report includes integrity method and key-handling
# ===========================================================================

class TestComplianceReportStructure(unittest.TestCase):
    """UT-077-007: Report contains HMAC method identifiers and control references."""

    def _generate(self):
        store = AppendOnlyAuditStore()
        return generate_integrity_compliance_report(store)

    def test_report_type_is_us_077(self):
        report = self._generate()
        self.assertEqual(report["report_type"], "INTEGRITY_COMPLIANCE_US_077")

    def test_report_includes_algorithm_name(self):
        report = self._generate()
        self.assertEqual(
            report["controls"]["hmac_generation"]["algorithm"], INTEGRITY_ALGORITHM
        )

    def test_report_includes_hipaa_standard_reference(self):
        report = self._generate()
        self.assertIn("164.312", report["standard"])

    def test_report_includes_chaining_description(self):
        report = self._generate()
        self.assertIn("chaining", report["controls"]["hmac_generation"])

    def test_report_key_handling_present(self):
        report = self._generate()
        self.assertIn("key_handling", report["controls"])
        self.assertIn("algorithm", report["controls"]["key_handling"])

    def test_report_key_handling_excludes_raw_key(self):
        report = self._generate()
        key_section = str(report["controls"]["key_handling"])
        self.assertNotIn(_AUDIT_INTEGRITY_SECRET.decode(), key_section)

    def test_report_tamper_detection_mechanism_documented(self):
        report = self._generate()
        mech = report["controls"]["tamper_detection"]["mechanism"]
        self.assertIn("AuditIntegrityChecker", mech)

    def test_report_includes_generated_at_timestamp(self):
        report = self._generate()
        datetime.fromisoformat(report["generated_at"])


# ===========================================================================
# UT-077-008: Compliance report includes validation run outcomes
# ===========================================================================

class TestComplianceReportValidationOutcomes(unittest.TestCase):
    """UT-077-008: Report includes run timestamp, pass/fail totals, and anomaly refs."""

    def test_no_last_run_noted_in_report(self):
        store = AppendOnlyAuditStore()
        report = generate_integrity_compliance_report(store, last_validation_result=None)
        last_run = report["controls"]["periodic_validation"]["last_run"]
        self.assertIsNone(last_run["run_at"])

    def test_last_run_summary_included_when_provided(self):
        store = _make_store("A", "B")
        job = AuditIntegrityValidationJob()
        result = job.run(store)

        report = generate_integrity_compliance_report(store, last_validation_result=result)
        last_run = report["controls"]["periodic_validation"]["last_run"]
        self.assertIsNotNone(last_run["run_at"])
        self.assertIn("entries_checked", last_run)
        self.assertIn("passed", last_run)
        self.assertIn("failed", last_run)

    def test_last_run_failure_ids_present(self):
        store = AppendOnlyAuditStore()
        entry = _fresh_entry(store)
        entry.event = "FORGED"
        job = AuditIntegrityValidationJob()
        result = job.run(store)

        report = generate_integrity_compliance_report(store, last_validation_result=result)
        last_run = report["controls"]["periodic_validation"]["last_run"]
        self.assertIn("failure_ids", last_run)

    def test_tamper_alerts_logged_count_in_report(self):
        store = AppendOnlyAuditStore()
        entry = _fresh_entry(store)
        entry.outcome = "forged"
        AuditIntegrityValidationJob().run(store)

        report = generate_integrity_compliance_report(store)
        self.assertGreaterEqual(
            report["controls"]["tamper_detection"]["tamper_alerts_logged"], 1
        )

    def test_hash_coverage_complete_for_all_entry_store(self):
        store = _make_store("X", "Y", "Z")
        report = generate_integrity_compliance_report(store)
        self.assertTrue(report["controls"]["hmac_generation"]["hash_coverage_complete"])

    def test_chain_status_intact_for_clean_store(self):
        store = _make_store("A", "B")
        report = generate_integrity_compliance_report(store)
        self.assertEqual(report["chain_status"], "intact")


# ===========================================================================
# UT-077-009: Chained-hash sequence validator detects broken chain
# ===========================================================================

class TestChainValidation(unittest.TestCase):
    """UT-077-009: verify_chain detects broken hash-chain links."""

    def test_broken_prev_chain_hash_detected(self):
        store = _make_store("A", "B", "C")
        entries = store.all_entries()
        # Corrupt the chain link on the second entry.
        entries[1] = AuditEntry(
            entry_id=entries[1].entry_id,
            timestamp=entries[1].timestamp,
            event=entries[1].event,
            actor_id=entries[1].actor_id,
            actor_role=entries[1].actor_role,
            action=entries[1].action,
            resource_type=entries[1].resource_type,
            resource_id=entries[1].resource_id,
            outcome=entries[1].outcome,
            source_ip=entries[1].source_ip,
            prev_chain_hash="deadbeef" * 8,       # broken link
            integrity_hash=entries[1].integrity_hash,
        )
        valid, broken_at = AuditIntegrityChecker().verify_chain(entries)
        self.assertFalse(valid)
        self.assertEqual(broken_at, 1)

    def test_single_tampered_entry_detected(self):
        store = _make_store("A", "B")
        entries = store.all_entries()
        entries[0].event = "TAMPERED"
        valid, broken_at = AuditIntegrityChecker().verify_chain(entries)
        self.assertFalse(valid)
        self.assertEqual(broken_at, 0)

    def test_chain_break_index_returned_correctly(self):
        store = _make_store("A", "B", "C", "D")
        entries = store.all_entries()
        entries[2].action = "injected"
        valid, broken_at = AuditIntegrityChecker().verify_chain(entries)
        self.assertFalse(valid)
        self.assertIsNotNone(broken_at)

    def test_validation_job_reports_chain_break(self):
        store = AppendOnlyAuditStore()
        e1 = _fresh_entry(store)
        e2 = _fresh_entry(store)
        # Directly corrupt the chain link in the store's internal list.
        store._entries[1] = AuditEntry(
            entry_id=e2.entry_id,
            timestamp=e2.timestamp,
            event=e2.event,
            actor_id=e2.actor_id,
            actor_role=e2.actor_role,
            action=e2.action,
            resource_type=e2.resource_type,
            resource_id=e2.resource_id,
            outcome=e2.outcome,
            source_ip=e2.source_ip,
            prev_chain_hash="badhash" * 9,
            integrity_hash=e2.integrity_hash,
        )
        result = AuditIntegrityValidationJob().run(store)
        self.assertFalse(result.chain_intact)
        self.assertIsNotNone(result.chain_break_at)

    def test_genesis_hash_used_for_first_entry_chain(self):
        store = AppendOnlyAuditStore()
        entry = _fresh_entry(store)
        self.assertEqual(entry.prev_chain_hash, _GENESIS_HASH)


# ===========================================================================
# UT-077-010: Integrity checker error paths return safe diagnostics
# ===========================================================================

class TestErrorPathDiagnostics(unittest.TestCase):
    """UT-077-010: Failure paths return actionable, non-sensitive error messages."""

    def test_verify_entry_reason_does_not_contain_key_material(self):
        store = AppendOnlyAuditStore()
        entry = _fresh_entry(store)
        entry.event = "FORGED"
        _, reason = AuditIntegrityChecker().verify_entry(entry)
        self.assertNotIn(_AUDIT_INTEGRITY_SECRET.decode(), reason)

    def test_verify_entry_reason_contains_entry_id(self):
        store = AppendOnlyAuditStore()
        entry = _fresh_entry(store)
        entry.action = "forged"
        _, reason = AuditIntegrityChecker().verify_entry(entry)
        self.assertIn(entry.entry_id, reason)

    def test_validation_job_with_empty_store_does_not_raise(self):
        store = AppendOnlyAuditStore()
        try:
            result = AuditIntegrityValidationJob().run(store)
        except Exception as exc:
            self.fail(f"run() raised unexpectedly: {exc}")
        self.assertEqual(result.entries_checked, 0)
        self.assertEqual(result.failed, 0)

    def test_validation_result_has_all_expected_fields(self):
        store = _make_store("A")
        result = AuditIntegrityValidationJob().run(store)
        self.assertIsInstance(result.entries_checked, int)
        self.assertIsInstance(result.passed, int)
        self.assertIsInstance(result.failed, int)
        self.assertIsInstance(result.chain_intact, bool)
        self.assertIsInstance(result.failure_ids, list)

    def test_compliance_report_with_empty_store_does_not_raise(self):
        store = AppendOnlyAuditStore()
        try:
            report = generate_integrity_compliance_report(store)
        except Exception as exc:
            self.fail(f"generate_integrity_compliance_report raised: {exc}")
        self.assertEqual(report["entry_count"], 0)

    def test_compliance_report_hash_coverage_zero_for_empty_store(self):
        store = AppendOnlyAuditStore()
        report = generate_integrity_compliance_report(store)
        self.assertEqual(report["controls"]["hmac_generation"]["entries_total"], 0)
        self.assertTrue(report["controls"]["hmac_generation"]["hash_coverage_complete"])


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
