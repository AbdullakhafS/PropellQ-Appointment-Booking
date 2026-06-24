"""
EP-007 US-078 — Audit Log Query Interface (Admin Only) Tests
(task_078_001 – task_078_005)

Covers all 12 unit test areas from UNIT-TEST-PLAN-078:
  UT-078-001: Admin role passes query interface authorization guard
  UT-078-002: Non-admin role is denied interface access
  UT-078-003: Filter query maps actor/action/date/resource/outcome to results
  UT-078-004: Pagination and sorting return deterministic subsets
  UT-078-005: Record selection shows actor/resource/action/timestamp/outcome metadata
  UT-078-006: Missing optional metadata fields display safe fallback values
  UT-078-007: CSV export matches current filtered result set
  UT-078-008: JSON export preserves schema and policy-compliant fields
  UT-078-009: Unauthorized API query attempt returns None with reason
  UT-078-010: Unauthorized export attempt is blocked
  UT-078-011: Read-only enforcement — service never mutates entries
  UT-078-012: Query performance guardrails apply default limits
"""
from __future__ import annotations

import csv
import io
import json
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

from src.audit_storage import (
    AUDIT_EXPORT_FIELDS,
    AUDIT_QUERY_ADMIN_ROLE,
    AUDIT_QUERY_DEFAULT_PAGE_SIZE,
    AUDIT_QUERY_MAX_PAGE_SIZE,
    AuditEntry,
    AuditImmutabilityError,
    AuditQueryParams,
    AuditQueryResult,
    AuditQueryService,
    AppendOnlyAuditStore,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_NOW = datetime(2026, 6, 24, 12, 0, 0, tzinfo=timezone.utc)


def _make_store(n: int = 5) -> AppendOnlyAuditStore:
    """Return a store with *n* test entries covering varied actors and events."""
    store = AppendOnlyAuditStore()
    roles = ["admin", "staff", "patient"]
    events = ["AUTH_LOGIN_SUCCESS", "PHI_ACCESS", "APPOINTMENT_BOOK", "DATA_ACCESS", "AUTH_LOGOUT"]
    outcomes = ["success", "denied", "error"]
    for i in range(n):
        store.append(
            event=events[i % len(events)],
            actor_id=f"user_{i % 3}",
            actor_role=roles[i % len(roles)],
            action=f"action_{i}",
            resource_type="appointment" if i % 2 == 0 else "patient",
            resource_id=str(i + 100),
            outcome=outcomes[i % len(outcomes)],
            source_ip=f"10.0.0.{i + 1}",
        )
    return store


def _default_params(**kwargs) -> AuditQueryParams:
    p = AuditQueryParams()
    for k, v in kwargs.items():
        setattr(p, k, v)
    return p


# ===========================================================================
# UT-078-001: Admin role passes query interface authorization guard
# ===========================================================================

class TestAdminAccessGranted(unittest.TestCase):
    """UT-078-001: Admin role can access the query interface."""

    def test_admin_role_allowed(self):
        allowed, reason = AuditQueryService._check_admin("admin")
        self.assertTrue(allowed)
        self.assertEqual(reason, "")

    def test_admin_query_returns_result(self):
        store = _make_store(3)
        result, err = AuditQueryService.query(store, AuditQueryParams(), role="admin")
        self.assertIsNotNone(result)
        self.assertEqual(err, "")

    def test_admin_query_result_type(self):
        store = _make_store(3)
        result, _ = AuditQueryService.query(store, AuditQueryParams(), role="admin")
        self.assertIsInstance(result, AuditQueryResult)

    def test_admin_role_constant_is_admin(self):
        self.assertEqual(AUDIT_QUERY_ADMIN_ROLE, "admin")


# ===========================================================================
# UT-078-002: Non-admin role is denied interface access
# ===========================================================================

class TestNonAdminAccessDenied(unittest.TestCase):
    """UT-078-002: Staff, patient, and unknown roles cannot access the interface."""

    def _assert_denied(self, role: str):
        store = _make_store()
        result, err = AuditQueryService.query(store, AuditQueryParams(), role=role)
        self.assertIsNone(result, f"Role '{role}' should be denied but got a result")
        self.assertIn("not authorised", err)

    def test_staff_role_denied(self):
        self._assert_denied("staff")

    def test_patient_role_denied(self):
        self._assert_denied("patient")

    def test_unknown_role_denied(self):
        self._assert_denied("unknown")

    def test_empty_role_denied(self):
        self._assert_denied("")

    def test_check_admin_staff_returns_false(self):
        allowed, reason = AuditQueryService._check_admin("staff")
        self.assertFalse(allowed)
        self.assertIn("admin", reason)


# ===========================================================================
# UT-078-003: Filter query maps actor/action/date/resource/outcome to results
# ===========================================================================

class TestFilterBehavior(unittest.TestCase):
    """UT-078-003: Each filter correctly narrows the result set."""

    def setUp(self):
        self.store = _make_store(10)

    def _query(self, **kwargs):
        params = _default_params(**kwargs)
        result, _ = AuditQueryService.query(self.store, params, role="admin")
        return result

    def test_filter_by_actor_id(self):
        result = self._query(actor_id="user_0")
        for e in result.entries:
            self.assertEqual(e.actor_id, "user_0")

    def test_filter_by_actor_role(self):
        result = self._query(actor_role="staff")
        for e in result.entries:
            self.assertEqual(e.actor_role, "staff")

    def test_filter_by_event(self):
        result = self._query(event="PHI_ACCESS")
        for e in result.entries:
            self.assertEqual(e.event, "PHI_ACCESS")

    def test_filter_by_outcome(self):
        result = self._query(outcome="success")
        for e in result.entries:
            self.assertEqual(e.outcome, "success")

    def test_filter_by_resource_type(self):
        result = self._query(resource_type="appointment")
        for e in result.entries:
            self.assertEqual(e.resource_type, "appointment")

    def test_combined_filters_narrow_results(self):
        result_all = self._query()
        result_filtered = self._query(actor_role="admin", outcome="success")
        self.assertLessEqual(result_filtered.total_matched, result_all.total_matched)

    def test_from_ts_excludes_older_entries(self):
        # Add an entry with a known old timestamp.
        store = AppendOnlyAuditStore()
        old_entry = store.append(
            event="OLD", actor_role="staff", action="a", resource_type="r"
        )
        old_ts = (_NOW - timedelta(days=30)).isoformat()
        old_entry.timestamp = old_ts

        new_entry = store.append(
            event="NEW", actor_role="staff", action="b", resource_type="r"
        )
        # from_ts = 2 days ago → old_entry should be excluded
        cutoff = (_NOW - timedelta(days=2)).isoformat()
        params = _default_params(from_ts=cutoff)
        result, _ = AuditQueryService.query(store, params, role="admin")
        entry_ids = [e.entry_id for e in result.entries]
        self.assertNotIn(old_entry.entry_id, entry_ids)

    def test_no_filters_returns_all(self):
        result = self._query()
        self.assertEqual(result.total_matched, 10)


# ===========================================================================
# UT-078-004: Pagination and sorting return deterministic subsets
# ===========================================================================

class TestPaginationAndSorting(unittest.TestCase):
    """UT-078-004: Pagination boundaries, sort order, and count accuracy."""

    def setUp(self):
        self.store = _make_store(15)

    def test_page_size_limits_entries_returned(self):
        params = _default_params(page=1, page_size=5)
        result, _ = AuditQueryService.query(self.store, params, role="admin")
        self.assertEqual(len(result.entries), 5)

    def test_second_page_is_different_from_first(self):
        p1 = _default_params(page=1, page_size=5)
        p2 = _default_params(page=2, page_size=5)
        r1, _ = AuditQueryService.query(self.store, p1, role="admin")
        r2, _ = AuditQueryService.query(self.store, p2, role="admin")
        ids1 = {e.entry_id for e in r1.entries}
        ids2 = {e.entry_id for e in r2.entries}
        self.assertTrue(ids1.isdisjoint(ids2), "Page 1 and page 2 should not share entries")

    def test_total_pages_calculation(self):
        params = _default_params(page=1, page_size=4)
        result, _ = AuditQueryService.query(self.store, params, role="admin")
        expected_pages = -(-15 // 4)  # ceiling division
        self.assertEqual(result.total_pages, expected_pages)

    def test_total_matched_reflects_full_set(self):
        params = _default_params(page=1, page_size=3)
        result, _ = AuditQueryService.query(self.store, params, role="admin")
        self.assertEqual(result.total_matched, 15)

    def test_sort_desc_first_entry_is_latest(self):
        params = _default_params(sort_by="timestamp", sort_dir="desc")
        result, _ = AuditQueryService.query(self.store, params, role="admin")
        if len(result.entries) >= 2:
            self.assertGreaterEqual(result.entries[0].timestamp, result.entries[-1].timestamp)

    def test_sort_asc_first_entry_is_earliest(self):
        params = _default_params(sort_by="timestamp", sort_dir="asc")
        result, _ = AuditQueryService.query(self.store, params, role="admin")
        if len(result.entries) >= 2:
            self.assertLessEqual(result.entries[0].timestamp, result.entries[-1].timestamp)

    def test_invalid_sort_field_falls_back_to_timestamp(self):
        params = _default_params(sort_by="nonexistent_field")
        self.assertEqual(params.validated_sort_by(), "timestamp")

    def test_last_page_may_have_fewer_entries(self):
        params = _default_params(page=4, page_size=5)
        result, _ = AuditQueryService.query(self.store, params, role="admin")
        # 15 entries / 5 per page = 3 full pages; page 4 should be empty
        self.assertEqual(len(result.entries), 0)


# ===========================================================================
# UT-078-005: Record selection shows full metadata details
# ===========================================================================

class TestRecordDetailView(unittest.TestCase):
    """UT-078-005: entry_detail returns all required metadata fields."""

    def test_detail_contains_all_required_fields(self):
        store = AppendOnlyAuditStore()
        entry = store.append(
            event="AUTH_LOGIN_SUCCESS",
            actor_id="user_99",
            actor_role="admin",
            action="login",
            resource_type="session",
            resource_id="42",
            outcome="success",
            source_ip="192.168.1.1",
        )
        detail = AuditQueryService.entry_detail(entry)
        required = ["entry_id", "timestamp", "event", "actor_id", "actor_role",
                    "action", "resource_type", "resource_id", "outcome", "source_ip"]
        for field in required:
            self.assertIn(field, detail, f"Missing field '{field}' in detail")

    def test_detail_values_match_entry(self):
        store = AppendOnlyAuditStore()
        entry = store.append(
            event="PHI_ACCESS",
            actor_id="user_5",
            actor_role="staff",
            action="read_profile",
            resource_type="patient",
            resource_id="77",
            outcome="success",
        )
        detail = AuditQueryService.entry_detail(entry)
        self.assertEqual(detail["event"], "PHI_ACCESS")
        self.assertEqual(detail["actor_id"], "user_5")
        self.assertEqual(detail["action"], "read_profile")
        self.assertEqual(detail["outcome"], "success")

    def test_detail_timestamp_is_iso8601(self):
        store = AppendOnlyAuditStore()
        entry = store.append(event="TEST", actor_role="admin", action="a", resource_type="r")
        detail = AuditQueryService.entry_detail(entry)
        datetime.fromisoformat(detail["timestamp"])


# ===========================================================================
# UT-078-006: Missing optional metadata fields display safe fallback values
# ===========================================================================

class TestDetailFallbackValues(unittest.TestCase):
    """UT-078-006: Null optional fields render safe placeholders, not exceptions."""

    def _make_entry_no_optionals(self) -> AuditEntry:
        store = AppendOnlyAuditStore()
        entry = store.append(
            event="TEST",
            actor_id=None,
            actor_role=None,
            action="test",
            resource_type="audit_log",
            resource_id=None,
            outcome="success",
            source_ip=None,
        )
        return entry

    def test_null_actor_id_shows_system_fallback(self):
        entry = self._make_entry_no_optionals()
        detail = AuditQueryService.entry_detail(entry)
        self.assertEqual(detail["actor_id"], "(system)")

    def test_null_actor_role_shows_unknown_fallback(self):
        entry = self._make_entry_no_optionals()
        detail = AuditQueryService.entry_detail(entry)
        self.assertEqual(detail["actor_role"], "(unknown)")

    def test_null_resource_id_shows_none_fallback(self):
        entry = self._make_entry_no_optionals()
        detail = AuditQueryService.entry_detail(entry)
        self.assertEqual(detail["resource_id"], "(none)")

    def test_null_source_ip_shows_unknown_fallback(self):
        entry = self._make_entry_no_optionals()
        detail = AuditQueryService.entry_detail(entry)
        self.assertEqual(detail["source_ip"], "(unknown)")

    def test_detail_does_not_raise_for_partial_entry(self):
        entry = self._make_entry_no_optionals()
        try:
            AuditQueryService.entry_detail(entry)
        except Exception as exc:
            self.fail(f"entry_detail raised unexpectedly: {exc}")


# ===========================================================================
# UT-078-007: CSV export matches current filtered result set
# ===========================================================================

class TestCsvExport(unittest.TestCase):
    """UT-078-007: CSV export has correct row count and content parity."""

    def test_csv_header_matches_export_fields(self):
        store = _make_store(3)
        params = AuditQueryParams()
        result, _ = AuditQueryService.query(store, params, role="admin")
        csv_str = AuditQueryService.export_csv(result.entries)
        reader = csv.DictReader(io.StringIO(csv_str))
        self.assertEqual(set(reader.fieldnames or []), set(AUDIT_EXPORT_FIELDS))

    def test_csv_row_count_matches_entries(self):
        store = _make_store(7)
        params = AuditQueryParams()
        result, _ = AuditQueryService.query(store, params, role="admin")
        csv_str = AuditQueryService.export_csv(result.entries)
        rows = list(csv.DictReader(io.StringIO(csv_str)))
        self.assertEqual(len(rows), len(result.entries))

    def test_csv_filtered_export_matches_filtered_count(self):
        store = _make_store(10)
        params = _default_params(outcome="success")
        result, _ = AuditQueryService.query(store, params, role="admin")
        csv_str = AuditQueryService.export_csv(result.entries)
        rows = list(csv.DictReader(io.StringIO(csv_str)))
        self.assertEqual(len(rows), result.total_matched)

    def test_csv_does_not_include_integrity_hash(self):
        store = _make_store(3)
        result, _ = AuditQueryService.query(store, AuditQueryParams(), role="admin")
        csv_str = AuditQueryService.export_csv(result.entries)
        self.assertNotIn("integrity_hash", csv_str)

    def test_csv_does_not_include_chain_hash(self):
        store = _make_store(3)
        result, _ = AuditQueryService.query(store, AuditQueryParams(), role="admin")
        csv_str = AuditQueryService.export_csv(result.entries)
        self.assertNotIn("prev_chain_hash", csv_str)

    def test_empty_store_produces_header_only_csv(self):
        store = AppendOnlyAuditStore()
        csv_str = AuditQueryService.export_csv([])
        reader = csv.DictReader(io.StringIO(csv_str))
        rows = list(reader)
        self.assertEqual(len(rows), 0)
        self.assertIsNotNone(reader.fieldnames)


# ===========================================================================
# UT-078-008: JSON export preserves schema and policy-compliant fields
# ===========================================================================

class TestJsonExport(unittest.TestCase):
    """UT-078-008: JSON export contains only allowed fields and correct structure."""

    def test_json_export_returns_list_of_dicts(self):
        store = _make_store(4)
        result, _ = AuditQueryService.query(store, AuditQueryParams(), role="admin")
        exported = AuditQueryService.export_json(result.entries)
        self.assertIsInstance(exported, list)
        for row in exported:
            self.assertIsInstance(row, dict)

    def test_json_export_contains_only_allowed_fields(self):
        store = _make_store(4)
        result, _ = AuditQueryService.query(store, AuditQueryParams(), role="admin")
        exported = AuditQueryService.export_json(result.entries)
        allowed = set(AUDIT_EXPORT_FIELDS)
        for row in exported:
            self.assertTrue(set(row.keys()).issubset(allowed),
                            f"Unexpected fields: {set(row.keys()) - allowed}")

    def test_json_export_does_not_contain_integrity_hash(self):
        store = _make_store(3)
        result, _ = AuditQueryService.query(store, AuditQueryParams(), role="admin")
        exported = AuditQueryService.export_json(result.entries)
        for row in exported:
            self.assertNotIn("integrity_hash", row)
            self.assertNotIn("prev_chain_hash", row)

    def test_json_export_row_count_matches_entries(self):
        store = _make_store(6)
        result, _ = AuditQueryService.query(store, AuditQueryParams(), role="admin")
        exported = AuditQueryService.export_json(result.entries)
        self.assertEqual(len(exported), len(result.entries))

    def test_json_export_entry_id_matches_source(self):
        store = _make_store(2)
        result, _ = AuditQueryService.query(store, AuditQueryParams(), role="admin")
        exported = AuditQueryService.export_json(result.entries)
        source_ids = {e.entry_id for e in result.entries}
        exported_ids = {row["entry_id"] for row in exported}
        self.assertEqual(source_ids, exported_ids)

    def test_json_export_is_serialisable(self):
        store = _make_store(3)
        result, _ = AuditQueryService.query(store, AuditQueryParams(), role="admin")
        exported = AuditQueryService.export_json(result.entries)
        try:
            json.dumps(exported)
        except TypeError as exc:
            self.fail(f"export_json produced non-serialisable output: {exc}")


# ===========================================================================
# UT-078-009: Unauthorized API query attempt returns None with reason
# ===========================================================================

class TestUnauthorizedQueryBlocked(unittest.TestCase):
    """UT-078-009: Non-admin roles receive None result with error message."""

    def test_staff_role_returns_none(self):
        store = _make_store()
        result, err = AuditQueryService.query(store, AuditQueryParams(), role="staff")
        self.assertIsNone(result)
        self.assertIsInstance(err, str)
        self.assertGreater(len(err), 0)

    def test_patient_role_returns_none(self):
        store = _make_store()
        result, err = AuditQueryService.query(store, AuditQueryParams(), role="patient")
        self.assertIsNone(result)

    def test_error_message_references_admin_role(self):
        store = _make_store()
        _, err = AuditQueryService.query(store, AuditQueryParams(), role="staff")
        self.assertIn("admin", err)

    def test_error_message_does_not_leak_data(self):
        store = _make_store(3)
        _, err = AuditQueryService.query(store, AuditQueryParams(), role="hacker")
        # Error must not reveal entry count or content
        self.assertNotIn("entries", err.lower())


# ===========================================================================
# UT-078-010: Unauthorized export attempt is blocked with no data leak
# ===========================================================================

class TestUnauthorizedExportBlocked(unittest.TestCase):
    """UT-078-010: Non-admin roles cannot obtain export data."""

    def test_staff_export_query_returns_none(self):
        store = _make_store(5)
        result, err = AuditQueryService.query(store, AuditQueryParams(), role="staff")
        self.assertIsNone(result)
        # No entries accessible to build an export from
        self.assertIsNotNone(err)

    def test_patient_export_query_returns_none(self):
        store = _make_store(5)
        result, _ = AuditQueryService.query(store, AuditQueryParams(), role="patient")
        self.assertIsNone(result)

    def test_admin_can_export_csv(self):
        store = _make_store(3)
        result, _ = AuditQueryService.query(store, AuditQueryParams(), role="admin")
        csv_str = AuditQueryService.export_csv(result.entries)
        self.assertIsInstance(csv_str, str)
        self.assertGreater(len(csv_str), 0)

    def test_admin_can_export_json(self):
        store = _make_store(3)
        result, _ = AuditQueryService.query(store, AuditQueryParams(), role="admin")
        exported = AuditQueryService.export_json(result.entries)
        self.assertIsInstance(exported, list)


# ===========================================================================
# UT-078-011: Read-only enforcement — service never mutates entries
# ===========================================================================

class TestReadOnlyEnforcement(unittest.TestCase):
    """UT-078-011: AuditQueryService does not mutate store or entries."""

    def test_query_does_not_change_store_size(self):
        store = _make_store(8)
        before = store.size()
        AuditQueryService.query(store, AuditQueryParams(), role="admin")
        self.assertEqual(store.size(), before)

    def test_query_does_not_modify_entry_fields(self):
        store = _make_store(3)
        original_events = [e.event for e in store.all_entries()]
        AuditQueryService.query(store, AuditQueryParams(), role="admin")
        after_events = [e.event for e in store.all_entries()]
        self.assertEqual(original_events, after_events)

    def test_export_csv_does_not_change_store(self):
        store = _make_store(3)
        result, _ = AuditQueryService.query(store, AuditQueryParams(), role="admin")
        size_before = store.size()
        AuditQueryService.export_csv(result.entries)
        self.assertEqual(store.size(), size_before)

    def test_store_delete_still_blocked_after_query(self):
        store = _make_store(2)
        AuditQueryService.query(store, AuditQueryParams(), role="admin")
        entry = store.all_entries()[0]
        with self.assertRaises(AuditImmutabilityError):
            store.delete(entry.entry_id)

    def test_store_update_still_blocked_after_query(self):
        store = _make_store(2)
        AuditQueryService.query(store, AuditQueryParams(), role="admin")
        entry = store.all_entries()[0]
        with self.assertRaises(AuditImmutabilityError):
            store.update(entry.entry_id, event="HACKED")


# ===========================================================================
# UT-078-012: Query performance guardrails apply default limits
# ===========================================================================

class TestPerformanceGuardrails(unittest.TestCase):
    """UT-078-012: Default page sizes and max limits are enforced."""

    def test_default_page_size_constant(self):
        self.assertEqual(AUDIT_QUERY_DEFAULT_PAGE_SIZE, 50)

    def test_max_page_size_constant(self):
        self.assertEqual(AUDIT_QUERY_MAX_PAGE_SIZE, 200)

    def test_page_size_clamped_to_max(self):
        params = AuditQueryParams(page_size=9999)
        self.assertEqual(params.validated_page_size(), AUDIT_QUERY_MAX_PAGE_SIZE)

    def test_page_size_clamped_to_min(self):
        params = AuditQueryParams(page_size=0)
        self.assertEqual(params.validated_page_size(), 1)

    def test_negative_page_size_clamped_to_one(self):
        params = AuditQueryParams(page_size=-5)
        self.assertEqual(params.validated_page_size(), 1)

    def test_page_clamped_to_min_one(self):
        params = AuditQueryParams(page=0)
        self.assertEqual(params.validated_page(), 1)

    def test_large_page_request_respects_max_entries(self):
        store = _make_store(10)
        params = AuditQueryParams(page=1, page_size=9999)
        result, _ = AuditQueryService.query(store, params, role="admin")
        # page_size clamped to 200, but store only has 10 entries
        self.assertLessEqual(len(result.entries), AUDIT_QUERY_MAX_PAGE_SIZE)
        self.assertEqual(result.page_size, AUDIT_QUERY_MAX_PAGE_SIZE)

    def test_default_params_use_default_page_size(self):
        params = AuditQueryParams()
        self.assertEqual(params.validated_page_size(), AUDIT_QUERY_DEFAULT_PAGE_SIZE)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
