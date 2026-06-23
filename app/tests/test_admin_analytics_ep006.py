"""Unit tests for EP-006 admin analytics tasks US-061 through US-069.

Covers:
  US-061 — No-Show Rate and Trends         (NoShowMetricsTests)
  US-062 — Average Wait Time Metrics       (WaitTimeMetricsTests)
  US-063 — Appointment Utilization         (UtilizationMetricsTests)
  US-064 — Intake Completion Rates         (IntakeCompletionMetricsTests)
  US-065 — Insurance Verification Metrics  (InsuranceVerificationMetricsTests)
  US-066 — AI-Human Agreement Rate         (AgreementRateMetricsTests)
  US-068 — Dashboard Filter Options        (FilterOptionsTests)
  US-069 — CSV Export                      (CsvExportTests)

US-067 (auto-refresh) is front-end only — no Python unit tests required.

IMPORTANT: This module imports ONLY from dashboard_service (no zoneinfo),
           which avoids the Windows pytest fatal crash in booking_service.
"""
from __future__ import annotations

import csv
import io
import os
import sqlite3
import unittest
from datetime import date, timedelta

from src.dashboard_service import (
    export_operational_metrics_csv,
    get_agreement_rate_metrics,
    get_filter_options,
    get_intake_completion_metrics,
    get_insurance_verification_metrics,
    get_no_show_metrics,
    get_utilization_metrics,
    get_wait_time_metrics,
)

_SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "db", "schema.sql")


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    with open(_SCHEMA_PATH, encoding="utf-8") as fh:
        conn.executescript(fh.read())
    conn.executemany(
        "INSERT INTO specialties (id, name) VALUES (?, ?)",
        [(1, "General"), (2, "Cardiology")],
    )
    conn.executemany(
        "INSERT INTO providers (id, name, credentials, specialty_id) VALUES (?, ?, ?, ?)",
        [(1, "Dr. Alpha", "MD", 1), (2, "Dr. Beta", "DO", 2)],
    )
    conn.execute(
        "INSERT INTO patient_profiles (id, first_name, last_name, email, phone) "
        "VALUES (1, 'Alex', 'Morgan', 'alex@example.com', '555-0100')"
    )
    conn.execute(
        "INSERT INTO patient_profiles (id, first_name, last_name, email, phone) "
        "VALUES (2, 'Bob', 'Smith', 'bob@example.com', '555-0200')"
    )
    conn.commit()
    return conn


def _add_appointment(
    conn: sqlite3.Connection,
    appt_date: str,
    status: str = "booked",
    provider_id: int = 1,
    specialty_id: int = 1,
    location: str = "Clinic A",
    duration_minutes: int = 30,
    checkout_status: str = "confirmed",
) -> int:
    cur = conn.execute(
        """INSERT INTO appointments
           (provider_id, specialty_id, appointment_date, start_time, end_time,
            location, status, duration_minutes, checkout_status, appointment_timezone)
           VALUES (?, ?, ?, '09:00', '09:30', ?, ?, ?, ?, 'America/Chicago')""",
        [provider_id, specialty_id, appt_date, location, status, duration_minutes, checkout_status],
    )
    conn.commit()
    return cur.lastrowid


def _add_intake_element(conn: sqlite3.Connection, patient_id: int = 1) -> None:
    conn.execute(
        """INSERT INTO clinical_profile_elements
           (patient_id, element_type, element_value, source_type, source_id, is_active)
           VALUES (?, 'intake_field', 'completed', 'intake', 0, 1)""",
        [patient_id],
    )
    conn.commit()


def _add_code_suggestion(
    conn: sqlite3.Connection,
    patient_id: int = 1,
    code_type: str = "icd10",
    status: str = "pending",
    auto_accepted: int = 0,
    reviewer_id: str | None = None,
) -> int:
    cur = conn.execute(
        """INSERT INTO clinical_code_suggestions
           (patient_id, code_type, code, description, confidence_score,
            status, auto_accepted, reviewer_id, review_required)
           VALUES (?, ?, 'A00', 'Test desc', 0.85, ?, ?, ?, 1)""",
        [patient_id, code_type, status, auto_accepted, reviewer_id],
    )
    conn.commit()
    return cur.lastrowid


def _add_review_audit(
    conn: sqlite3.Connection,
    suggestion_id: int,
    patient_id: int = 1,
    action: str = "accept",
    reviewer_id: str = "admin1",
    acted_at: str | None = None,
) -> None:
    new_status = "accepted" if action == "accept" else "rejected"
    conn.execute(
        """INSERT INTO clinical_code_review_audit
           (suggestion_id, patient_id, action, reviewer_id,
            previous_status, new_status, acted_at)
           VALUES (?, ?, ?, ?, 'pending', ?, COALESCE(?, CURRENT_TIMESTAMP))""",
        [suggestion_id, patient_id, action, reviewer_id, new_status, acted_at],
    )
    conn.commit()


FUTURE = (date.today() + timedelta(days=10)).isoformat()
PAST = (date.today() - timedelta(days=10)).isoformat()


# ===========================================================================
# US-061: No-Show Rate and Trends
# ===========================================================================

class NoShowMetricsTests(unittest.TestCase):

    def setUp(self):
        self.conn = _make_db()

    def tearDown(self):
        self.conn.close()

    def test_required_keys_present(self):
        result = get_no_show_metrics(self.conn)
        for key in ("rate", "count", "missed", "total", "prior_period_rate",
                    "delta", "trend", "filters_applied", "last_updated"):
            self.assertIn(key, result)

    def test_zero_rate_with_no_appointments(self):
        result = get_no_show_metrics(self.conn)
        self.assertEqual(result["rate"], 0.0)
        self.assertEqual(result["total"], 0)

    def test_rate_reflects_cancelled_count(self):
        _add_appointment(self.conn, PAST, status="booked")
        _add_appointment(self.conn, PAST, status="cancelled")
        result = get_no_show_metrics(self.conn)
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["missed"], 1)
        self.assertAlmostEqual(result["rate"], 50.0, places=1)

    def test_all_cancelled_gives_100_rate(self):
        _add_appointment(self.conn, PAST, status="cancelled")
        _add_appointment(self.conn, PAST, status="cancelled")
        result = get_no_show_metrics(self.conn)
        self.assertEqual(result["rate"], 100.0)

    def test_no_show_trend_lists_periods(self):
        _add_appointment(self.conn, PAST, status="cancelled")
        result = get_no_show_metrics(self.conn)
        self.assertIsInstance(result["trend"], list)
        self.assertTrue(len(result["trend"]) >= 1)
        self.assertIn("period", result["trend"][0])
        self.assertIn("value", result["trend"][0])

    def test_trend_empty_when_no_cancellations(self):
        _add_appointment(self.conn, PAST, status="booked")
        result = get_no_show_metrics(self.conn)
        self.assertEqual(result["trend"], [])

    def test_provider_id_filter_isolates_provider(self):
        _add_appointment(self.conn, PAST, status="cancelled", provider_id=1)
        _add_appointment(self.conn, PAST, status="cancelled", provider_id=2)
        result = get_no_show_metrics(self.conn, provider_id=1)
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["missed"], 1)

    def test_date_from_filter(self):
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        last_week = (date.today() - timedelta(days=7)).isoformat()
        _add_appointment(self.conn, yesterday, status="cancelled")
        _add_appointment(self.conn, last_week, status="cancelled")
        result = get_no_show_metrics(self.conn, date_from=date.today().isoformat())
        # Neither is today or future, so total=0
        self.assertEqual(result["total"], 0)

    def test_date_range_filter(self):
        d_from = (date.today() - timedelta(days=5)).isoformat()
        d_to = (date.today() - timedelta(days=3)).isoformat()
        in_range = (date.today() - timedelta(days=4)).isoformat()
        out_range = (date.today() - timedelta(days=10)).isoformat()
        _add_appointment(self.conn, in_range, status="cancelled")
        _add_appointment(self.conn, out_range, status="cancelled")
        result = get_no_show_metrics(self.conn, date_from=d_from, date_to=d_to)
        self.assertEqual(result["total"], 1)

    def test_filters_applied_echoed(self):
        result = get_no_show_metrics(self.conn, date_from="2026-01-01", provider_id=1)
        fa = result["filters_applied"]
        self.assertEqual(fa["date_from"], "2026-01-01")
        self.assertEqual(fa["provider_id"], 1)

    def test_delta_computed_when_date_range_given(self):
        d0 = date.today() - timedelta(days=6)
        d1 = date.today() - timedelta(days=1)
        _add_appointment(self.conn, d1.isoformat(), status="cancelled")
        result = get_no_show_metrics(
            self.conn,
            date_from=d0.isoformat(),
            date_to=d1.isoformat(),
        )
        self.assertIsInstance(result["delta"], float)


# ===========================================================================
# US-062: Average Wait Time Metrics
# ===========================================================================

class WaitTimeMetricsTests(unittest.TestCase):

    def setUp(self):
        self.conn = _make_db()

    def tearDown(self):
        self.conn.close()

    def test_required_keys_present(self):
        result = get_wait_time_metrics(self.conn)
        for key in ("avg_wait_minutes", "p95_wait_minutes", "threshold_minutes",
                    "threshold_exceeded", "trend", "sample_count",
                    "filters_applied", "last_updated"):
            self.assertIn(key, result)

    def test_zero_avg_with_no_appointments(self):
        result = get_wait_time_metrics(self.conn)
        self.assertEqual(result["avg_wait_minutes"], 0.0)
        self.assertEqual(result["sample_count"], 0)

    def test_avg_reflects_duration(self):
        _add_appointment(self.conn, PAST, duration_minutes=20)
        _add_appointment(self.conn, PAST, duration_minutes=40)
        result = get_wait_time_metrics(self.conn)
        self.assertAlmostEqual(result["avg_wait_minutes"], 30.0, places=1)

    def test_threshold_exceeded_flag_true_when_above(self):
        _add_appointment(self.conn, PAST, duration_minutes=60)
        result = get_wait_time_metrics(self.conn, threshold_minutes=30)
        self.assertTrue(result["threshold_exceeded"])

    def test_threshold_exceeded_flag_false_when_below(self):
        _add_appointment(self.conn, PAST, duration_minutes=15)
        result = get_wait_time_metrics(self.conn, threshold_minutes=30)
        self.assertFalse(result["threshold_exceeded"])

    def test_p95_is_non_negative(self):
        for _ in range(5):
            _add_appointment(self.conn, PAST, duration_minutes=30)
        result = get_wait_time_metrics(self.conn)
        self.assertGreaterEqual(result["p95_wait_minutes"], 0)

    def test_only_booked_appointments_counted(self):
        _add_appointment(self.conn, PAST, status="booked", duration_minutes=30)
        _add_appointment(self.conn, PAST, status="cancelled", duration_minutes=999)
        result = get_wait_time_metrics(self.conn)
        self.assertEqual(result["sample_count"], 1)
        self.assertAlmostEqual(result["avg_wait_minutes"], 30.0, places=1)

    def test_trend_includes_period_and_value(self):
        _add_appointment(self.conn, PAST, duration_minutes=30)
        result = get_wait_time_metrics(self.conn)
        self.assertTrue(len(result["trend"]) >= 1)
        self.assertIn("period", result["trend"][0])
        self.assertIn("value", result["trend"][0])

    def test_provider_filter_isolates_provider(self):
        _add_appointment(self.conn, PAST, provider_id=1, duration_minutes=10)
        _add_appointment(self.conn, PAST, provider_id=2, duration_minutes=90)
        result = get_wait_time_metrics(self.conn, provider_id=1)
        self.assertEqual(result["sample_count"], 1)
        self.assertAlmostEqual(result["avg_wait_minutes"], 10.0, places=1)

    def test_location_filter(self):
        _add_appointment(self.conn, PAST, location="Clinic A", duration_minutes=20)
        _add_appointment(self.conn, PAST, location="Remote", duration_minutes=90)
        result = get_wait_time_metrics(self.conn, location="Clinic A")
        self.assertEqual(result["sample_count"], 1)


# ===========================================================================
# US-063: Appointment Utilization Analytics
# ===========================================================================

class UtilizationMetricsTests(unittest.TestCase):

    def setUp(self):
        self.conn = _make_db()

    def tearDown(self):
        self.conn.close()

    def test_required_keys_present(self):
        result = get_utilization_metrics(self.conn)
        for key in ("utilization_rate", "booked", "available", "total",
                    "by_provider", "by_specialty", "filters_applied", "last_updated"):
            self.assertIn(key, result)

    def test_zero_utilization_with_no_appointments(self):
        result = get_utilization_metrics(self.conn)
        self.assertEqual(result["utilization_rate"], 0.0)
        self.assertEqual(result["total"], 0)

    def test_utilization_rate_computed(self):
        _add_appointment(self.conn, FUTURE, status="booked")
        _add_appointment(self.conn, FUTURE, status="available")
        result = get_utilization_metrics(self.conn)
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["booked"], 1)
        self.assertEqual(result["available"], 1)
        self.assertAlmostEqual(result["utilization_rate"], 50.0, places=1)

    def test_full_utilization_when_all_booked(self):
        _add_appointment(self.conn, FUTURE, status="booked")
        _add_appointment(self.conn, FUTURE, status="booked")
        result = get_utilization_metrics(self.conn)
        self.assertEqual(result["utilization_rate"], 100.0)

    def test_by_provider_populated(self):
        _add_appointment(self.conn, FUTURE, status="booked", provider_id=1)
        result = get_utilization_metrics(self.conn)
        self.assertTrue(len(result["by_provider"]) >= 1)
        prov = result["by_provider"][0]
        self.assertIn("provider", prov)
        self.assertIn("utilization_rate", prov)

    def test_by_specialty_populated(self):
        _add_appointment(self.conn, FUTURE, status="booked", specialty_id=1)
        result = get_utilization_metrics(self.conn)
        self.assertTrue(len(result["by_specialty"]) >= 1)
        spec = result["by_specialty"][0]
        self.assertIn("specialty", spec)
        self.assertIn("utilization_rate", spec)

    def test_provider_filter(self):
        _add_appointment(self.conn, FUTURE, status="booked", provider_id=1)
        _add_appointment(self.conn, FUTURE, status="booked", provider_id=2)
        result = get_utilization_metrics(self.conn, provider_id=1)
        self.assertEqual(result["total"], 1)

    def test_location_filter_partial_match(self):
        _add_appointment(self.conn, FUTURE, location="Main Street Clinic")
        _add_appointment(self.conn, FUTURE, location="Remote")
        result = get_utilization_metrics(self.conn, location="main")
        self.assertEqual(result["total"], 1)

    def test_rate_is_within_0_to_100(self):
        _add_appointment(self.conn, FUTURE, status="booked")
        result = get_utilization_metrics(self.conn)
        self.assertGreaterEqual(result["utilization_rate"], 0.0)
        self.assertLessEqual(result["utilization_rate"], 100.0)

    def test_filters_applied_echoed(self):
        result = get_utilization_metrics(self.conn, specialty_id=1, location="Clinic")
        fa = result["filters_applied"]
        self.assertEqual(fa["specialty_id"], 1)
        self.assertEqual(fa["location"], "Clinic")


# ===========================================================================
# US-064: Intake Completion Rates
# ===========================================================================

class IntakeCompletionMetricsTests(unittest.TestCase):

    def setUp(self):
        self.conn = _make_db()

    def tearDown(self):
        self.conn.close()

    def test_required_keys_present(self):
        result = get_intake_completion_metrics(self.conn)
        for key in ("completion_rate", "completed", "total",
                    "low_completion_flag", "threshold", "filters_applied", "last_updated"):
            self.assertIn(key, result)

    def test_zero_rate_with_no_appointments(self):
        result = get_intake_completion_metrics(self.conn)
        self.assertEqual(result["completion_rate"], 0.0)
        self.assertEqual(result["total"], 0)

    def test_low_completion_flag_true_when_no_intake(self):
        _add_appointment(self.conn, PAST, status="booked")
        result = get_intake_completion_metrics(self.conn)
        self.assertTrue(result["low_completion_flag"])

    def test_full_completion_when_all_have_intake(self):
        _add_appointment(self.conn, PAST, status="booked")
        _add_intake_element(self.conn, patient_id=1)
        result = get_intake_completion_metrics(self.conn)
        self.assertEqual(result["completion_rate"], 100.0)
        self.assertFalse(result["low_completion_flag"])

    def test_threshold_is_70(self):
        result = get_intake_completion_metrics(self.conn)
        self.assertEqual(result["threshold"], 70)

    def test_only_booked_appointments_counted_in_total(self):
        _add_appointment(self.conn, PAST, status="booked")
        _add_appointment(self.conn, PAST, status="available")
        _add_appointment(self.conn, PAST, status="cancelled")
        result = get_intake_completion_metrics(self.conn)
        self.assertEqual(result["total"], 1)

    def test_provider_filter_applied_to_total(self):
        _add_appointment(self.conn, PAST, status="booked", provider_id=1)
        _add_appointment(self.conn, PAST, status="booked", provider_id=2)
        result = get_intake_completion_metrics(self.conn, provider_id=1)
        self.assertEqual(result["total"], 1)

    def test_date_filter_applied_to_total(self):
        old_date = (date.today() - timedelta(days=30)).isoformat()
        _add_appointment(self.conn, PAST, status="booked")
        _add_appointment(self.conn, old_date, status="booked")
        result = get_intake_completion_metrics(
            self.conn,
            date_from=(date.today() - timedelta(days=15)).isoformat(),
        )
        self.assertEqual(result["total"], 1)

    def test_completion_rate_is_non_negative(self):
        result = get_intake_completion_metrics(self.conn)
        self.assertGreaterEqual(result["completion_rate"], 0.0)


# ===========================================================================
# US-065: Insurance Verification Status Metrics
# ===========================================================================

class InsuranceVerificationMetricsTests(unittest.TestCase):

    def setUp(self):
        self.conn = _make_db()

    def tearDown(self):
        self.conn.close()

    def test_required_keys_present(self):
        result = get_insurance_verification_metrics(self.conn)
        for key in ("verified", "pending", "failed", "total",
                    "issue_flag", "filters_applied", "last_updated"):
            self.assertIn(key, result)

    def test_all_zero_with_no_appointments(self):
        result = get_insurance_verification_metrics(self.conn)
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["verified"], 0)
        self.assertFalse(result["issue_flag"])

    def test_confirmed_counts_as_verified(self):
        _add_appointment(self.conn, PAST, checkout_status="confirmed")
        result = get_insurance_verification_metrics(self.conn)
        self.assertEqual(result["verified"], 1)
        self.assertEqual(result["pending"], 0)
        self.assertEqual(result["failed"], 0)

    def test_reserved_counts_as_pending(self):
        _add_appointment(self.conn, PAST, checkout_status="reserved")
        result = get_insurance_verification_metrics(self.conn)
        self.assertEqual(result["pending"], 1)
        self.assertTrue(result["issue_flag"])

    def test_searching_counts_as_pending(self):
        _add_appointment(self.conn, PAST, checkout_status="searching")
        result = get_insurance_verification_metrics(self.conn)
        self.assertEqual(result["pending"], 1)

    def test_expired_counts_as_failed(self):
        _add_appointment(self.conn, PAST, checkout_status="expired")
        result = get_insurance_verification_metrics(self.conn)
        self.assertEqual(result["failed"], 1)
        self.assertTrue(result["issue_flag"])

    def test_cancelled_checkout_counts_as_failed(self):
        _add_appointment(self.conn, PAST, checkout_status="cancelled")
        result = get_insurance_verification_metrics(self.conn)
        self.assertEqual(result["failed"], 1)

    def test_total_is_sum_of_buckets(self):
        _add_appointment(self.conn, PAST, checkout_status="confirmed")
        _add_appointment(self.conn, PAST, checkout_status="reserved")
        _add_appointment(self.conn, PAST, checkout_status="expired")
        result = get_insurance_verification_metrics(self.conn)
        self.assertEqual(result["total"], result["verified"] + result["pending"] + result["failed"])

    def test_provider_filter(self):
        _add_appointment(self.conn, PAST, checkout_status="confirmed", provider_id=1)
        _add_appointment(self.conn, PAST, checkout_status="confirmed", provider_id=2)
        result = get_insurance_verification_metrics(self.conn, provider_id=1)
        self.assertEqual(result["verified"], 1)

    def test_issue_flag_false_when_all_confirmed(self):
        _add_appointment(self.conn, PAST, checkout_status="confirmed")
        result = get_insurance_verification_metrics(self.conn)
        self.assertFalse(result["issue_flag"])

    def test_date_range_filter(self):
        d_from = (date.today() - timedelta(days=3)).isoformat()
        d_to = date.today().isoformat()
        in_range = (date.today() - timedelta(days=2)).isoformat()
        out_range = (date.today() - timedelta(days=10)).isoformat()
        _add_appointment(self.conn, in_range, checkout_status="confirmed")
        _add_appointment(self.conn, out_range, checkout_status="confirmed")
        result = get_insurance_verification_metrics(self.conn, date_from=d_from, date_to=d_to)
        self.assertEqual(result["verified"], 1)


# ===========================================================================
# US-066: AI-Human Agreement Rate
# ===========================================================================

class AgreementRateMetricsTests(unittest.TestCase):

    def setUp(self):
        self.conn = _make_db()

    def tearDown(self):
        self.conn.close()

    def test_required_keys_present(self):
        result = get_agreement_rate_metrics(self.conn)
        for key in ("agreement_rate", "reviewed", "agreed", "auto_accepted",
                    "trend", "by_category", "filters_applied", "last_updated"):
            self.assertIn(key, result)

    def test_zero_rate_with_no_reviews(self):
        result = get_agreement_rate_metrics(self.conn)
        self.assertEqual(result["agreement_rate"], 0.0)
        self.assertEqual(result["reviewed"], 0)

    def test_100_rate_when_all_accepted(self):
        sid = _add_code_suggestion(self.conn, status="pending")
        _add_review_audit(self.conn, sid, action="accept")
        result = get_agreement_rate_metrics(self.conn)
        self.assertEqual(result["agreement_rate"], 100.0)
        self.assertEqual(result["agreed"], 1)
        self.assertEqual(result["reviewed"], 1)

    def test_0_rate_when_all_rejected(self):
        sid = _add_code_suggestion(self.conn, status="pending")
        _add_review_audit(self.conn, sid, action="reject")
        result = get_agreement_rate_metrics(self.conn)
        self.assertEqual(result["agreement_rate"], 0.0)

    def test_mixed_outcomes_compute_rate(self):
        sid1 = _add_code_suggestion(self.conn)
        sid2 = _add_code_suggestion(self.conn)
        _add_review_audit(self.conn, sid1, action="accept")
        _add_review_audit(self.conn, sid2, action="reject")
        result = get_agreement_rate_metrics(self.conn)
        self.assertAlmostEqual(result["agreement_rate"], 50.0, places=1)

    def test_by_category_populated(self):
        sid1 = _add_code_suggestion(self.conn, code_type="icd10")
        sid2 = _add_code_suggestion(self.conn, code_type="cpt")
        _add_review_audit(self.conn, sid1, action="accept")
        _add_review_audit(self.conn, sid2, action="reject")
        result = get_agreement_rate_metrics(self.conn)
        categories = {c["category"] for c in result["by_category"]}
        self.assertIn("icd10", categories)
        self.assertIn("cpt", categories)

    def test_auto_accepted_counted(self):
        _add_code_suggestion(self.conn, status="accepted", auto_accepted=1)
        result = get_agreement_rate_metrics(self.conn)
        self.assertEqual(result["auto_accepted"], 1)

    def test_trend_entries_have_period_and_value(self):
        sid = _add_code_suggestion(self.conn)
        _add_review_audit(self.conn, sid, action="accept",
                          acted_at="2026-01-15 10:00:00")
        result = get_agreement_rate_metrics(self.conn)
        self.assertTrue(len(result["trend"]) >= 1)
        self.assertIn("period", result["trend"][0])
        self.assertIn("value", result["trend"][0])

    def test_date_from_filter(self):
        sid1 = _add_code_suggestion(self.conn)
        sid2 = _add_code_suggestion(self.conn)
        _add_review_audit(self.conn, sid1, action="accept",
                          acted_at="2025-01-01 10:00:00")
        _add_review_audit(self.conn, sid2, action="reject",
                          acted_at="2026-06-01 10:00:00")
        result = get_agreement_rate_metrics(self.conn, date_from="2026-01-01")
        # Only the 2026 review (reject) is in scope
        self.assertEqual(result["reviewed"], 1)
        self.assertEqual(result["agreed"], 0)

    def test_agreement_rate_between_0_and_100(self):
        sid = _add_code_suggestion(self.conn)
        _add_review_audit(self.conn, sid, action="accept")
        result = get_agreement_rate_metrics(self.conn)
        self.assertGreaterEqual(result["agreement_rate"], 0.0)
        self.assertLessEqual(result["agreement_rate"], 100.0)

    def test_category_rate_within_bounds(self):
        sid = _add_code_suggestion(self.conn, code_type="icd10")
        _add_review_audit(self.conn, sid, action="accept")
        result = get_agreement_rate_metrics(self.conn)
        for cat in result["by_category"]:
            self.assertGreaterEqual(cat["agreement_rate"], 0.0)
            self.assertLessEqual(cat["agreement_rate"], 100.0)


# ===========================================================================
# US-068: Filter Options
# ===========================================================================

class FilterOptionsTests(unittest.TestCase):

    def setUp(self):
        self.conn = _make_db()

    def tearDown(self):
        self.conn.close()

    def test_required_keys_present(self):
        result = get_filter_options(self.conn)
        for key in ("providers", "specialties", "locations"):
            self.assertIn(key, result)

    def test_providers_list_is_list(self):
        result = get_filter_options(self.conn)
        self.assertIsInstance(result["providers"], list)

    def test_seeded_providers_returned(self):
        result = get_filter_options(self.conn)
        names = [p["name"] for p in result["providers"]]
        self.assertIn("Dr. Alpha", names)
        self.assertIn("Dr. Beta", names)

    def test_provider_has_required_fields(self):
        result = get_filter_options(self.conn)
        for p in result["providers"]:
            self.assertIn("id", p)
            self.assertIn("name", p)
            self.assertIn("credentials", p)

    def test_specialties_returned(self):
        result = get_filter_options(self.conn)
        names = [s["name"] for s in result["specialties"]]
        self.assertIn("General", names)
        self.assertIn("Cardiology", names)

    def test_specialty_has_id_and_name(self):
        result = get_filter_options(self.conn)
        for s in result["specialties"]:
            self.assertIn("id", s)
            self.assertIn("name", s)

    def test_locations_list_is_list(self):
        result = get_filter_options(self.conn)
        self.assertIsInstance(result["locations"], list)

    def test_locations_populated_from_appointments(self):
        _add_appointment(self.conn, FUTURE, location="West Wing")
        _add_appointment(self.conn, FUTURE, location="East Wing")
        result = get_filter_options(self.conn)
        self.assertIn("West Wing", result["locations"])
        self.assertIn("East Wing", result["locations"])

    def test_inactive_provider_excluded(self):
        self.conn.execute(
            "INSERT INTO providers (id, name, credentials, specialty_id, is_active) "
            "VALUES (99, 'Retired Dr', 'MD', 1, 0)"
        )
        self.conn.commit()
        result = get_filter_options(self.conn)
        names = [p["name"] for p in result["providers"]]
        self.assertNotIn("Retired Dr", names)


# ===========================================================================
# US-069: CSV Export
# ===========================================================================

class CsvExportTests(unittest.TestCase):

    def setUp(self):
        self.conn = _make_db()

    def tearDown(self):
        self.conn.close()

    def _parse_csv(self, csv_bytes: bytes) -> list[dict]:
        reader = csv.DictReader(io.StringIO(csv_bytes.decode("utf-8")))
        return list(reader)

    def test_returns_bytes(self):
        result = export_operational_metrics_csv(self.conn)
        self.assertIsInstance(result, bytes)

    def test_headers_present(self):
        result = export_operational_metrics_csv(self.conn)
        text = result.decode("utf-8")
        self.assertIn("ID", text)
        self.assertIn("Date", text)
        self.assertIn("Provider", text)
        self.assertIn("Specialty", text)
        self.assertIn("Status", text)

    def test_empty_export_has_only_header_row(self):
        rows = self._parse_csv(export_operational_metrics_csv(self.conn))
        self.assertEqual(len(rows), 0)

    def test_row_count_matches_appointments(self):
        _add_appointment(self.conn, PAST)
        _add_appointment(self.conn, FUTURE)
        rows = self._parse_csv(export_operational_metrics_csv(self.conn))
        self.assertEqual(len(rows), 2)

    def test_row_fields_correct(self):
        _add_appointment(self.conn, PAST, location="Test Clinic")
        rows = self._parse_csv(export_operational_metrics_csv(self.conn))
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["Location"], "Test Clinic")
        self.assertEqual(row["Provider"], "Dr. Alpha")
        self.assertEqual(row["Specialty"], "General")

    def test_date_from_filter(self):
        d_in = date.today().isoformat()
        d_out = (date.today() - timedelta(days=5)).isoformat()
        _add_appointment(self.conn, d_in)
        _add_appointment(self.conn, d_out)
        rows = self._parse_csv(
            export_operational_metrics_csv(self.conn, date_from=d_in)
        )
        self.assertEqual(len(rows), 1)

    def test_date_to_filter(self):
        d_past = (date.today() - timedelta(days=1)).isoformat()
        _add_appointment(self.conn, d_past)
        _add_appointment(self.conn, FUTURE)
        rows = self._parse_csv(
            export_operational_metrics_csv(self.conn, date_to=d_past)
        )
        self.assertEqual(len(rows), 1)

    def test_provider_id_filter(self):
        _add_appointment(self.conn, PAST, provider_id=1)
        _add_appointment(self.conn, PAST, provider_id=2)
        rows = self._parse_csv(
            export_operational_metrics_csv(self.conn, provider_id=1)
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["Provider"], "Dr. Alpha")

    def test_location_filter(self):
        _add_appointment(self.conn, PAST, location="Clinic North")
        _add_appointment(self.conn, PAST, location="Remote")
        rows = self._parse_csv(
            export_operational_metrics_csv(self.conn, location="clinic")
        )
        self.assertEqual(len(rows), 1)

    def test_ordered_by_date_ascending(self):
        earlier = (date.today() - timedelta(days=5)).isoformat()
        later = (date.today() - timedelta(days=1)).isoformat()
        _add_appointment(self.conn, later)
        _add_appointment(self.conn, earlier)
        rows = self._parse_csv(export_operational_metrics_csv(self.conn))
        self.assertEqual(len(rows), 2)
        self.assertLessEqual(rows[0]["Date"], rows[1]["Date"])

    def test_utf8_encoded(self):
        result = export_operational_metrics_csv(self.conn)
        # Should decode without errors
        result.decode("utf-8")


if __name__ == "__main__":
    unittest.main()
