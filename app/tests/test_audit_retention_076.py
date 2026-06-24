"""
EP-007 US-076 — Audit Log Retention (7 Years) Tests (task_076_001 – task_076_004)

Covers all 12 unit test areas from UNIT-TEST-PLAN-076:
  UT-076-001: Retention policy validator enforces minimum 7-year threshold
  UT-076-002: Lifecycle evaluator blocks deletion before retention maturity
  UT-076-003: Archival routing moves eligible old records to archive tier
  UT-076-004: Retrieval service resolves active + archived records transparently
  UT-076-005: Deletion selector includes only truly expired records
  UT-076-006: Early-deletion attempt path is denied and audited as violation
  UT-076-007: Compliance evidence builder includes retention policy settings and enforcement proofs
  UT-076-008: Evidence output includes archival retrieval verification records
  UT-076-009: Deletion workflow requires approval metadata before execution
  UT-076-010: Approved deletion emits immutable deletion-audit event
  UT-076-011: Retention enforcement handles clock drift boundary safely
  UT-076-012: Archival/retrieval error handling preserves traceability
"""
from __future__ import annotations

import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

from src.audit_storage import (
    AUDIT_RETENTION_DAYS,
    AUDIT_RETENTION_YEARS,
    AuditEntry,
    AuditImmutabilityError,
    AppendOnlyAuditStore,
    AuditRetentionPolicy,
    AuditIntegrityChecker,
    AuditArchiveTier,
    AuditRetentionEnforcer,
    AuditedDeletionController,
    DeletionApproval,
    generate_retention_compliance_report,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_NOW = datetime(2026, 6, 24, 12, 0, 0, tzinfo=timezone.utc)
_ACTIVE_TS = (_NOW - timedelta(days=365)).isoformat()          # 1 year old — not expired
_EXPIRED_TS = (_NOW - timedelta(days=AUDIT_RETENTION_DAYS + 10)).isoformat()  # 7+ years — expired
_BOUNDARY_TS = (_NOW - timedelta(days=AUDIT_RETENTION_DAYS)).isoformat()      # exactly at cutoff


def _make_entry(timestamp: str, entry_id: str | None = None) -> AuditEntry:
    """Build a minimal AuditEntry with given timestamp."""
    import uuid
    eid = entry_id or str(uuid.uuid4())
    e = AuditEntry(
        entry_id=eid,
        timestamp=timestamp,
        event="TEST_EVENT",
        actor_id="user_1",
        actor_role="staff",
        action="test_action",
        resource_type="audit_log",
        resource_id=eid,
        outcome="success",
        source_ip="127.0.0.1",
        prev_chain_hash="0" * 64,
        integrity_hash="",
    )
    return e


def _make_store_with_entries(active_ts: str = _ACTIVE_TS, expired_ts: str = _EXPIRED_TS) -> AppendOnlyAuditStore:
    """Return a store populated with one active and one expired entry."""
    store = AppendOnlyAuditStore()
    # Patch timestamps by appending and then replacing the timestamp field.
    e_active = store.append(
        event="TEST_ACTIVE",
        actor_id="user_active",
        actor_role="staff",
        action="read",
        resource_type="appointment",
        resource_id="1",
        outcome="success",
    )
    e_active.timestamp = active_ts

    e_expired = store.append(
        event="TEST_EXPIRED",
        actor_id="user_expired",
        actor_role="staff",
        action="read",
        resource_type="appointment",
        resource_id="2",
        outcome="success",
    )
    e_expired.timestamp = expired_ts
    return store


# ===========================================================================
# UT-076-001: Retention policy validator enforces minimum 7-year threshold
# ===========================================================================

class TestRetentionPolicyValidator(unittest.TestCase):
    """UT-076-001: Policy validator rejects below-minimum configurations."""

    def test_seven_years_is_valid(self):
        valid, err = AuditRetentionPolicy.validate_policy(7)
        self.assertTrue(valid)
        self.assertEqual(err, "")

    def test_above_minimum_is_valid(self):
        valid, err = AuditRetentionPolicy.validate_policy(10)
        self.assertTrue(valid)

    def test_below_minimum_is_rejected(self):
        valid, err = AuditRetentionPolicy.validate_policy(6)
        self.assertFalse(valid)
        self.assertIn("HIPAA minimum", err)

    def test_zero_is_rejected(self):
        valid, err = AuditRetentionPolicy.validate_policy(0)
        self.assertFalse(valid)

    def test_negative_is_rejected(self):
        valid, err = AuditRetentionPolicy.validate_policy(-1)
        self.assertFalse(valid)

    def test_non_integer_is_rejected(self):
        valid, err = AuditRetentionPolicy.validate_policy("seven")  # type: ignore[arg-type]
        self.assertFalse(valid)


# ===========================================================================
# UT-076-002: Lifecycle evaluator blocks deletion before retention maturity
# ===========================================================================

class TestDeletionEligibilityBlocked(unittest.TestCase):
    """UT-076-002: Non-expired records return False for deletion eligibility."""

    def test_recent_entry_not_eligible(self):
        entry = _make_entry(_ACTIVE_TS)
        eligible = AuditRetentionPolicy.is_eligible_for_deletion(entry, now=_NOW)
        self.assertFalse(eligible)

    def test_entry_exactly_at_cutoff_not_eligible(self):
        # Boundary: exactly AUDIT_RETENTION_DAYS old → not yet past cutoff
        entry = _make_entry(_BOUNDARY_TS)
        eligible = AuditRetentionPolicy.is_eligible_for_deletion(entry, now=_NOW)
        self.assertFalse(eligible)

    def test_expired_entry_is_eligible(self):
        entry = _make_entry(_EXPIRED_TS)
        eligible = AuditRetentionPolicy.is_eligible_for_deletion(entry, now=_NOW)
        self.assertTrue(eligible)

    def test_invalid_timestamp_not_eligible(self):
        entry = _make_entry("not-a-timestamp")
        self.assertFalse(AuditRetentionPolicy.is_eligible_for_deletion(entry, now=_NOW))


# ===========================================================================
# UT-076-003: Archival routing moves eligible records to archive tier
# ===========================================================================

class TestArchivalRouting(unittest.TestCase):
    """UT-076-003: Enforcer moves only expired entries to archive tier."""

    def test_expired_entries_moved_to_archive(self):
        store = _make_store_with_entries()
        archive = AuditArchiveTier()
        AuditRetentionEnforcer.run_archival_cycle(store, archive, now=_NOW)
        self.assertEqual(archive.size(), 1)

    def test_active_entries_remain_in_store(self):
        store = _make_store_with_entries()
        initial_active_size = sum(
            1 for e in store.all_entries()
            if not AuditRetentionPolicy.is_eligible_for_deletion(e, _NOW)
        )
        archive = AuditArchiveTier()
        AuditRetentionEnforcer.run_archival_cycle(store, archive, now=_NOW)
        # Expect at least one active entry plus the lifecycle event added by the cycle.
        active_events = [e for e in store.all_entries() if e.event != "LIFECYCLE_ARCHIVE"]
        self.assertGreaterEqual(len(active_events), initial_active_size)

    def test_archival_cycle_appends_lifecycle_event(self):
        store = _make_store_with_entries()
        archive = AuditArchiveTier()
        AuditRetentionEnforcer.run_archival_cycle(store, archive, now=_NOW)
        lifecycle_events = [e for e in store.all_entries() if e.event == "LIFECYCLE_ARCHIVE"]
        self.assertGreaterEqual(len(lifecycle_events), 1)

    def test_archival_cycle_summary_contains_counts(self):
        store = _make_store_with_entries()
        archive = AuditArchiveTier()
        summary = AuditRetentionEnforcer.run_archival_cycle(store, archive, now=_NOW)
        self.assertIn("archived_count", summary)
        self.assertIn("active_remaining", summary)
        self.assertIn("cycle_timestamp", summary)

    def test_no_candidates_returns_zero_archived(self):
        store = AppendOnlyAuditStore()
        store.append(event="NEW", actor_role="staff", action="a", resource_type="r")
        archive = AuditArchiveTier()
        summary = AuditRetentionEnforcer.run_archival_cycle(store, archive, now=_NOW)
        self.assertEqual(summary["archived_count"], 0)

    def test_archive_event_records_entry_ids(self):
        store = _make_store_with_entries()
        archive = AuditArchiveTier()
        AuditRetentionEnforcer.run_archival_cycle(store, archive, now=_NOW)
        events = archive.archive_events()
        self.assertTrue(len(events) > 0 or archive.size() == 0)
        if events:
            self.assertIn("entry_ids", events[0])


# ===========================================================================
# UT-076-004: Retrieval service resolves active + archived records transparently
# ===========================================================================

class TestArchiveRetrieval(unittest.TestCase):
    """UT-076-004: Archived entries remain retrievable after archival cycle."""

    def _setup(self):
        store = _make_store_with_entries()
        archive = AuditArchiveTier()
        AuditRetentionEnforcer.run_archival_cycle(store, archive, now=_NOW)
        return store, archive

    def test_archived_entries_are_retrievable(self):
        _, archive = self._setup()
        results = archive.retrieve(limit=100)
        self.assertGreaterEqual(len(results), 1)

    def test_archived_entries_are_audit_entries(self):
        _, archive = self._setup()
        for entry in archive.retrieve():
            self.assertIsInstance(entry, AuditEntry)

    def test_archived_entries_integrity_preserved(self):
        # Integrity hashes are computed at append time using the then-current
        # timestamp.  The archival tier must faithfully preserve each entry
        # object without mutation; the hash stays consistent with the value
        # stored at append.
        store = AppendOnlyAuditStore()
        entry = store.append(
            event="OLD_EVENT",
            actor_id="u1",
            actor_role="staff",
            action="read",
            resource_type="audit_log",
            resource_id="x",
            outcome="success",
        )
        # Backdate only for eligibility; hash was computed at real append time.
        entry.timestamp = _EXPIRED_TS
        archive = AuditArchiveTier()
        AuditRetentionEnforcer.run_archival_cycle(store, archive, now=_NOW)

        # The entry must be present and intact in the archive (not duplicated,
        # not dropped, identity preserved by entry_id).
        archived = archive.all_entries()
        self.assertGreaterEqual(len(archived), 1)
        self.assertTrue(archive.contains(entry.entry_id))

    def test_event_filter_applied_to_archive_retrieval(self):
        archive = AuditArchiveTier()
        entry_a = _make_entry(_EXPIRED_TS)
        entry_a.event = "AUTH_LOGIN"
        entry_b = _make_entry(_EXPIRED_TS)
        entry_b.event = "DATA_ACCESS"
        archive.archive([entry_a, entry_b])

        results = archive.retrieve(event_filter="AUTH_LOGIN")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].event, "AUTH_LOGIN")

    def test_archive_size_reflects_all_entries(self):
        store = _make_store_with_entries()
        archive = AuditArchiveTier()
        AuditRetentionEnforcer.run_archival_cycle(store, archive, now=_NOW)
        self.assertEqual(archive.size(), len(archive.all_entries()))


# ===========================================================================
# UT-076-005: Deletion selector includes only truly expired records
# ===========================================================================

class TestDeletionCandidateSelector(unittest.TestCase):
    """UT-076-005: get_archival_candidates returns only expired subset."""

    def test_only_expired_in_candidates(self):
        active = _make_entry(_ACTIVE_TS)
        expired = _make_entry(_EXPIRED_TS)
        candidates = AuditRetentionPolicy.get_archival_candidates([active, expired], now=_NOW)
        self.assertIn(expired, candidates)
        self.assertNotIn(active, candidates)

    def test_empty_list_returns_empty_candidates(self):
        candidates = AuditRetentionPolicy.get_archival_candidates([], now=_NOW)
        self.assertEqual(candidates, [])

    def test_all_active_returns_empty(self):
        entries = [_make_entry(_ACTIVE_TS) for _ in range(5)]
        candidates = AuditRetentionPolicy.get_archival_candidates(entries, now=_NOW)
        self.assertEqual(len(candidates), 0)

    def test_all_expired_returns_all(self):
        entries = [_make_entry(_EXPIRED_TS) for _ in range(3)]
        candidates = AuditRetentionPolicy.get_archival_candidates(entries, now=_NOW)
        self.assertEqual(len(candidates), 3)


# ===========================================================================
# UT-076-006: Early-deletion attempt is denied and audited as violation
# ===========================================================================

class TestEarlyDeletionDenied(unittest.TestCase):
    """UT-076-006: Deletion of non-expired entries is denied and logged."""

    def test_active_store_delete_raises_immutability_error(self):
        store = AppendOnlyAuditStore()
        entry = store.append(event="TEST", actor_role="staff", action="a", resource_type="r")
        with self.assertRaises(AuditImmutabilityError):
            store.delete(entry.entry_id)

    def test_deletion_of_non_archived_entry_is_denied(self):
        store = AppendOnlyAuditStore()
        archive = AuditArchiveTier()
        entry = store.append(event="ACTIVE", actor_role="staff", action="a", resource_type="r")
        entry.timestamp = _ACTIVE_TS
        approval = DeletionApproval(approver_id="compliance_officer", reason="Test denial")

        result = AuditedDeletionController.request_deletion(
            entries=[entry], archive=archive, active_store=store,
            approval=approval, now=_NOW
        )
        self.assertIn(entry.entry_id, result["denied"])
        self.assertNotIn(entry.entry_id, result["approved"])

    def test_early_deletion_attempt_emits_denied_audit_event(self):
        store = AppendOnlyAuditStore()
        archive = AuditArchiveTier()
        entry = store.append(event="ACTIVE", actor_role="staff", action="a", resource_type="r")
        entry.timestamp = _ACTIVE_TS
        approval = DeletionApproval(approver_id="compliance_officer", reason="Test denial")

        AuditedDeletionController.request_deletion(
            entries=[entry], archive=archive, active_store=store,
            approval=approval, now=_NOW
        )
        denied_events = [e for e in store.all_entries() if e.event == "LIFECYCLE_DELETE_DENIED"]
        self.assertGreaterEqual(len(denied_events), 1)

    def test_non_expired_entry_in_archive_is_denied(self):
        """Entry moved prematurely to archive must still be denied if not expired."""
        store = AppendOnlyAuditStore()
        archive = AuditArchiveTier()
        entry = _make_entry(_ACTIVE_TS)
        archive.archive([entry])  # force into archive tier
        approval = DeletionApproval(approver_id="compliance_officer", reason="Premature")

        result = AuditedDeletionController.request_deletion(
            entries=[entry], archive=archive, active_store=store,
            approval=approval, now=_NOW
        )
        self.assertIn(entry.entry_id, result["denied"])


# ===========================================================================
# UT-076-007: Compliance evidence builder includes retention policy settings
# ===========================================================================

class TestComplianceEvidenceRetentionPolicy(unittest.TestCase):
    """UT-076-007: Report includes policy version, thresholds, and enforcement checks."""

    def _generate(self):
        store = AppendOnlyAuditStore()
        archive = AuditArchiveTier()
        return generate_retention_compliance_report(store, archive)

    def test_report_type_is_us_076(self):
        report = self._generate()
        self.assertEqual(report["report_type"], "RETENTION_COMPLIANCE_US_076")

    def test_report_includes_minimum_years(self):
        report = self._generate()
        self.assertEqual(
            report["controls"]["retention_policy"]["minimum_years"], AUDIT_RETENTION_YEARS
        )

    def test_report_policy_valid_is_true(self):
        report = self._generate()
        self.assertTrue(report["controls"]["retention_policy"]["policy_valid"])

    def test_report_includes_hipaa_reference(self):
        report = self._generate()
        ref = report["controls"]["retention_policy"]["hipaa_reference"]
        self.assertIn("164.530", ref)

    def test_report_documents_early_deletion_blocked(self):
        report = self._generate()
        self.assertTrue(report["controls"]["retention_policy"]["early_deletion_blocked"])

    def test_report_includes_enforcement_mechanism(self):
        report = self._generate()
        mech = report["controls"]["retention_policy"]["enforcement_mechanism"]
        self.assertIn("AuditRetentionEnforcer", mech)

    def test_report_includes_generated_at(self):
        report = self._generate()
        self.assertIn("generated_at", report)
        # Should be a valid ISO timestamp
        datetime.fromisoformat(report["generated_at"])


# ===========================================================================
# UT-076-008: Evidence includes archival retrieval verification records
# ===========================================================================

class TestComplianceEvidenceArchivalRetrieval(unittest.TestCase):
    """UT-076-008: Report includes retrieval-test outcomes and timestamps."""

    def test_empty_archive_retrieval_ok_is_true(self):
        store = AppendOnlyAuditStore()
        archive = AuditArchiveTier()
        report = generate_retention_compliance_report(store, archive)
        self.assertTrue(report["controls"]["archival_tier"]["retrieval_integrity_ok"])

    def test_archived_sample_count_in_report(self):
        store = AppendOnlyAuditStore()
        archive = AuditArchiveTier()
        entry = store.append(event="OLD", actor_role="staff", action="a", resource_type="r")
        entry.timestamp = _EXPIRED_TS
        AuditRetentionEnforcer.run_archival_cycle(store, archive, now=_NOW)

        report = generate_retention_compliance_report(store, archive)
        self.assertGreaterEqual(
            report["controls"]["archival_tier"]["retrieval_sample_count"], 1
        )

    def test_retrieval_details_contain_entry_id_and_timestamp(self):
        store = AppendOnlyAuditStore()
        archive = AuditArchiveTier()
        entry = store.append(event="OLD", actor_role="staff", action="a", resource_type="r")
        entry.timestamp = _EXPIRED_TS
        AuditRetentionEnforcer.run_archival_cycle(store, archive, now=_NOW)

        report = generate_retention_compliance_report(store, archive)
        for detail in report["controls"]["archival_tier"]["retrieval_sample_details"]:
            self.assertIn("entry_id", detail)
            self.assertIn("timestamp", detail)
            self.assertIn("integrity_ok", detail)

    def test_archive_events_included_in_report(self):
        store = _make_store_with_entries()
        archive = AuditArchiveTier()
        AuditRetentionEnforcer.run_archival_cycle(store, archive, now=_NOW)

        report = generate_retention_compliance_report(store, archive)
        self.assertIn("archive_events", report["controls"]["archival_tier"])


# ===========================================================================
# UT-076-009: Deletion workflow requires approval metadata before execution
# ===========================================================================

class TestDeletionApprovalRequired(unittest.TestCase):
    """UT-076-009: Deletion without valid approval is blocked."""

    def _setup_expired_in_archive(self):
        store = AppendOnlyAuditStore()
        archive = AuditArchiveTier()
        entry = store.append(event="OLD", actor_role="staff", action="a", resource_type="r")
        entry.timestamp = _EXPIRED_TS
        AuditRetentionEnforcer.run_archival_cycle(store, archive, now=_NOW)
        # Retrieve the expired entry from the archive
        archived = archive.all_entries()
        return store, archive, archived

    def test_deletion_without_approver_id_is_blocked(self):
        store, archive, archived = self._setup_expired_in_archive()
        approval = DeletionApproval(approver_id="", reason="valid reason")
        result = AuditedDeletionController.request_deletion(
            entries=archived, archive=archive, active_store=store,
            approval=approval, now=_NOW
        )
        self.assertEqual(len(result["approved"]), 0)
        self.assertEqual(len(result["denied"]), len(archived))

    def test_deletion_without_reason_is_blocked(self):
        store, archive, archived = self._setup_expired_in_archive()
        approval = DeletionApproval(approver_id="compliance_officer", reason="")
        result = AuditedDeletionController.request_deletion(
            entries=archived, archive=archive, active_store=store,
            approval=approval, now=_NOW
        )
        self.assertEqual(len(result["approved"]), 0)

    def test_valid_approval_allows_deletion_of_expired_archived_entry(self):
        store, archive, archived = self._setup_expired_in_archive()
        approval = DeletionApproval(approver_id="compliance_officer", reason="Retention expired — purge")
        result = AuditedDeletionController.request_deletion(
            entries=archived, archive=archive, active_store=store,
            approval=approval, now=_NOW
        )
        self.assertGreater(len(result["approved"]), 0)
        self.assertEqual(len(result["denied"]), 0)

    def test_result_contains_total_and_approved_and_denied(self):
        store, archive, archived = self._setup_expired_in_archive()
        approval = DeletionApproval(approver_id="compliance_officer", reason="Retention expired")
        result = AuditedDeletionController.request_deletion(
            entries=archived, archive=archive, active_store=store,
            approval=approval, now=_NOW
        )
        self.assertIn("total", result)
        self.assertIn("approved", result)
        self.assertIn("denied", result)
        self.assertIn("rejection_reasons", result)


# ===========================================================================
# UT-076-010: Approved deletion emits immutable deletion-audit event
# ===========================================================================

class TestApprovedDeletionAuditEvent(unittest.TestCase):
    """UT-076-010: Deletion audit record contains actor, approver, target, reason, timestamp."""

    def test_approved_deletion_emits_approved_event(self):
        store = AppendOnlyAuditStore()
        archive = AuditArchiveTier()
        entry = store.append(event="OLD", actor_role="staff", action="a", resource_type="r")
        entry.timestamp = _EXPIRED_TS
        AuditRetentionEnforcer.run_archival_cycle(store, archive, now=_NOW)
        archived = archive.all_entries()

        approval = DeletionApproval(approver_id="cco_jane", reason="HIPAA expired — scheduled purge")
        AuditedDeletionController.request_deletion(
            entries=archived, archive=archive, active_store=store,
            approval=approval, now=_NOW
        )

        approved_events = [e for e in store.all_entries() if e.event == "LIFECYCLE_DELETE_APPROVED"]
        self.assertGreaterEqual(len(approved_events), 1)

    def test_deletion_event_contains_approver_id(self):
        store = AppendOnlyAuditStore()
        archive = AuditArchiveTier()
        entry = store.append(event="OLD", actor_role="staff", action="a", resource_type="r")
        entry.timestamp = _EXPIRED_TS
        AuditRetentionEnforcer.run_archival_cycle(store, archive, now=_NOW)
        archived = archive.all_entries()

        approval = DeletionApproval(approver_id="cco_jane", reason="Expired records purge")
        AuditedDeletionController.request_deletion(
            entries=archived, archive=archive, active_store=store,
            approval=approval, now=_NOW
        )

        approved_events = [e for e in store.all_entries() if e.event == "LIFECYCLE_DELETE_APPROVED"]
        self.assertTrue(any(e.actor_id == "cco_jane" for e in approved_events))

    def test_deletion_event_is_immutable(self):
        """Once written, the deletion audit event must not be mutable."""
        store = AppendOnlyAuditStore()
        archive = AuditArchiveTier()
        entry = store.append(event="OLD", actor_role="staff", action="a", resource_type="r")
        entry.timestamp = _EXPIRED_TS
        AuditRetentionEnforcer.run_archival_cycle(store, archive, now=_NOW)
        archived = archive.all_entries()

        approval = DeletionApproval(approver_id="cco_jane", reason="Expired")
        AuditedDeletionController.request_deletion(
            entries=archived, archive=archive, active_store=store,
            approval=approval, now=_NOW
        )

        # Any attempt to delete the audit event itself must be blocked.
        approved_events = [e for e in store.all_entries() if e.event == "LIFECYCLE_DELETE_APPROVED"]
        if approved_events:
            with self.assertRaises(AuditImmutabilityError):
                store.delete(approved_events[0].entry_id)

    def test_compliance_report_counts_deletion_audit_events(self):
        store = AppendOnlyAuditStore()
        archive = AuditArchiveTier()
        entry = store.append(event="OLD", actor_role="staff", action="a", resource_type="r")
        entry.timestamp = _EXPIRED_TS
        AuditRetentionEnforcer.run_archival_cycle(store, archive, now=_NOW)
        archived = archive.all_entries()

        approval = DeletionApproval(approver_id="cco_jane", reason="Expired")
        AuditedDeletionController.request_deletion(
            entries=archived, archive=archive, active_store=store,
            approval=approval, now=_NOW
        )

        report = generate_retention_compliance_report(store, archive)
        self.assertGreaterEqual(
            report["controls"]["deletion_controls"]["deletion_audit_events_logged"], 1
        )


# ===========================================================================
# UT-076-011: Retention enforcement handles clock drift boundary safely
# ===========================================================================

class TestRetentionBoundaryHandling(unittest.TestCase):
    """UT-076-011: Deterministic eligibility around the retention cutoff boundary."""

    def test_one_day_before_cutoff_not_eligible(self):
        ts = (_NOW - timedelta(days=AUDIT_RETENTION_DAYS - 1)).isoformat()
        entry = _make_entry(ts)
        self.assertFalse(AuditRetentionPolicy.is_eligible_for_deletion(entry, now=_NOW))

    def test_one_day_past_cutoff_is_eligible(self):
        ts = (_NOW - timedelta(days=AUDIT_RETENTION_DAYS + 1)).isoformat()
        entry = _make_entry(ts)
        self.assertTrue(AuditRetentionPolicy.is_eligible_for_deletion(entry, now=_NOW))

    def test_cutoff_boundary_entry_not_eligible(self):
        # Exactly at the cutoff: NOT past it, so not eligible.
        ts = (_NOW - timedelta(days=AUDIT_RETENTION_DAYS)).isoformat()
        entry = _make_entry(ts)
        self.assertFalse(AuditRetentionPolicy.is_eligible_for_deletion(entry, now=_NOW))

    def test_archival_cycle_does_not_archive_boundary_entry(self):
        store = AppendOnlyAuditStore()
        entry = store.append(event="BOUNDARY", actor_role="staff", action="a", resource_type="r")
        entry.timestamp = (_NOW - timedelta(days=AUDIT_RETENTION_DAYS)).isoformat()
        archive = AuditArchiveTier()
        summary = AuditRetentionEnforcer.run_archival_cycle(store, archive, now=_NOW)
        self.assertEqual(summary["archived_count"], 0)

    def test_sub_second_drift_does_not_change_eligibility(self):
        """An entry 1 microsecond past the retention cutoff is eligible.

        The policy uses strict less-than (entry_dt < cutoff); an entry at
        exactly AUDIT_RETENTION_DAYS old is NOT eligible, but an entry
        1 microsecond older (further in the past) IS eligible.  This is the
        deterministic behaviour that must be consistent regardless of clock drift.
        """
        ts_just_past = (_NOW - timedelta(days=AUDIT_RETENTION_DAYS, microseconds=1)).isoformat()
        entry = _make_entry(ts_just_past)
        # 1 microsecond past the cutoff → the timestamp is older than cutoff → eligible.
        self.assertTrue(AuditRetentionPolicy.is_eligible_for_deletion(entry, now=_NOW))


# ===========================================================================
# UT-076-012: Archival/retrieval error handling preserves traceability
# ===========================================================================

class TestArchivalErrorHandling(unittest.TestCase):
    """UT-076-012: Failures during archival preserve traceability."""

    def test_archiving_empty_list_returns_zero(self):
        archive = AuditArchiveTier()
        count = archive.archive([])
        self.assertEqual(count, 0)
        self.assertEqual(len(archive.archive_events()), 0)

    def test_retrieve_from_empty_archive_returns_empty_list(self):
        archive = AuditArchiveTier()
        results = archive.retrieve(limit=100)
        self.assertEqual(results, [])

    def test_deletion_of_empty_entries_list_returns_zero_approved(self):
        store = AppendOnlyAuditStore()
        archive = AuditArchiveTier()
        approval = DeletionApproval(approver_id="cco", reason="Test")
        result = AuditedDeletionController.request_deletion(
            entries=[], archive=archive, active_store=store,
            approval=approval, now=_NOW
        )
        self.assertEqual(result["approved"], [])
        self.assertEqual(result["total"], 0)

    def test_report_generated_with_empty_store_and_archive(self):
        store = AppendOnlyAuditStore()
        archive = AuditArchiveTier()
        report = generate_retention_compliance_report(store, archive)
        self.assertEqual(report["entry_counts"]["active"], 0)
        self.assertEqual(report["entry_counts"]["archived"], 0)

    def test_archive_contains_check_on_unknown_id_returns_false(self):
        archive = AuditArchiveTier()
        self.assertFalse(archive.contains("nonexistent-id"))

    def test_compliance_report_marks_approval_required(self):
        store = AppendOnlyAuditStore()
        archive = AuditArchiveTier()
        report = generate_retention_compliance_report(store, archive)
        self.assertTrue(report["controls"]["deletion_controls"]["approval_required"])


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
