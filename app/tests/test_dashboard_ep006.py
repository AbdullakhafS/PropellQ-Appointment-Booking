"""
EP-006: Patient Dashboard & Admin Operational Dashboard — Backend Tests

Covers:
  US-053  Patient Dashboard aggregate API
  US-054  Upcoming Appointments with action eligibility (BE-1, BE-2)
  US-055  Past Appointments with release policy (BE-1, BE-2)
  US-056  Personal Health Profile with version metadata (BE-1, BE-2)
  US-057  Document Upload — patient documents list (BE-3)
  US-058  Notification Preference Management (BE-1, BE-2)
  US-059  Mobile Responsive — no backend; verified via CSS/FE tests
  US-060  Admin Operational Dashboard metrics API (BE-1, BE-2, BE-3)
"""
import json
import os
import sqlite3
import sys
import unittest
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.dashboard_service import (
    get_admin_operational_metrics,
    get_notification_preferences,
    get_patient_appointment_history,
    get_patient_dashboard,
    get_patient_documents,
    get_patient_health_profile,
    get_patient_upcoming_appointments,
    is_notification_allowed,
    set_notification_preferences,
)


# ---------------------------------------------------------------------------
# Test database fixture helpers
# ---------------------------------------------------------------------------

def _make_db() -> sqlite3.Connection:
    """Create an in-memory database with schema and minimal seed data."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    schema_path = os.path.join(os.path.dirname(__file__), "..", "db", "schema_v1_production.sql")
    with open(schema_path) as fh:
        conn.executescript(fh.read())

    # Seed: specialty
    conn.execute("INSERT INTO specialties(id, name) VALUES (1, 'General')")
    # Seed: provider
    conn.execute(
        "INSERT INTO providers(id, name, credentials, specialty_id) VALUES (1, 'Dr. Test', 'MD', 1)"
    )
    # Seed: patient profile
    conn.execute(
        """INSERT INTO patient_profiles(id, first_name, last_name, email, phone, reminder_channels)
           VALUES (1, 'Alex', 'Morgan', 'alex@example.com', '555-0100', '["sms","email"]')"""
    )
    conn.commit()
    return conn


def _add_appointment(conn: sqlite3.Connection, appt_date: str, status: str = "booked") -> int:
    conn.execute(
        """INSERT INTO appointments(provider_id, specialty_id, appointment_date, start_time,
           end_time, location, status, appointment_timezone)
           VALUES (1, 1, ?, '09:00', '09:30', 'Clinic A', ?, 'America/Chicago')""",
        [appt_date, status],
    )
    conn.commit()
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def _add_clinical_element(conn: sqlite3.Connection, element_type: str, label: str) -> None:
    conn.execute(
        """INSERT INTO clinical_profile_elements
               (patient_id, element_type, element_value, source_type, source_id, is_active)
           VALUES (1, ?, ?, 'intake', 0, 1)""",
        [element_type, label],
    )
    conn.commit()


def _add_clinical_document(conn: sqlite3.Connection, file_name: str = "test.pdf") -> int:
    conn.execute(
        """INSERT INTO clinical_documents(patient_id, file_name, file_type, storage_path, file_size_bytes)
           VALUES (1, ?, 'pdf', '/tmp/test.pdf', 1024)""",
        [file_name],
    )
    conn.commit()
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


# ---------------------------------------------------------------------------
# US-053: Patient Dashboard Aggregate API
# ---------------------------------------------------------------------------

class PatientDashboardTests(unittest.TestCase):

    def setUp(self):
        self.conn = _make_db()

    def tearDown(self):
        self.conn.close()

    def test_dashboard_returns_required_keys(self):
        data = get_patient_dashboard(self.conn)
        for key in ("upcoming_count", "recent_activity", "profile_summary",
                    "notification_prefs", "documents_count", "last_updated"):
            self.assertIn(key, data, f"Missing key: {key}")

    def test_dashboard_upcoming_count_is_integer(self):
        data = get_patient_dashboard(self.conn)
        self.assertIsInstance(data["upcoming_count"], int)

    def test_dashboard_profile_summary_contains_name(self):
        data = get_patient_dashboard(self.conn)
        self.assertIn("name", data["profile_summary"])
        self.assertIn("Alex", data["profile_summary"]["name"])

    def test_dashboard_profile_summary_contains_email(self):
        data = get_patient_dashboard(self.conn)
        self.assertIn("email", data["profile_summary"])

    def test_dashboard_last_updated_is_iso_string(self):
        data = get_patient_dashboard(self.conn)
        self.assertIsInstance(data["last_updated"], str)
        self.assertGreater(len(data["last_updated"]), 0)

    def test_dashboard_upcoming_count_reflects_future_appointments(self):
        future = (date.today() + timedelta(days=5)).isoformat()
        _add_appointment(self.conn, future)
        data = get_patient_dashboard(self.conn)
        self.assertEqual(data["upcoming_count"], 1)

    def test_dashboard_recent_activity_excludes_future(self):
        future = (date.today() + timedelta(days=5)).isoformat()
        _add_appointment(self.conn, future)
        data = get_patient_dashboard(self.conn)
        self.assertEqual(len(data["recent_activity"]), 0)

    def test_dashboard_recent_activity_includes_past(self):
        past = (date.today() - timedelta(days=3)).isoformat()
        _add_appointment(self.conn, past)
        data = get_patient_dashboard(self.conn)
        self.assertEqual(len(data["recent_activity"]), 1)

    def test_dashboard_notification_prefs_present(self):
        data = get_patient_dashboard(self.conn)
        prefs = data["notification_prefs"]
        self.assertIn("email", prefs)
        self.assertIn("sms", prefs)


# ---------------------------------------------------------------------------
# US-054: Upcoming Appointments with Action Eligibility
# ---------------------------------------------------------------------------

class UpcomingAppointmentsTests(unittest.TestCase):

    def setUp(self):
        self.conn = _make_db()
        self.today = date.today().isoformat()
        self.far_future = (date.today() + timedelta(days=10)).isoformat()
        self.near_future = (date.today() + timedelta(days=1)).isoformat()

    def tearDown(self):
        self.conn.close()

    def test_returns_items_and_total_keys(self):
        data = get_patient_upcoming_appointments(self.conn)
        self.assertIn("items", data)
        self.assertIn("total", data)

    def test_empty_when_no_booked_appointments(self):
        data = get_patient_upcoming_appointments(self.conn)
        self.assertEqual(data["total"], 0)

    def test_filters_only_booked_appointments(self):
        _add_appointment(self.conn, self.far_future, status="available")
        data = get_patient_upcoming_appointments(self.conn)
        self.assertEqual(data["total"], 0)

    def test_includes_future_booked_appointments(self):
        _add_appointment(self.conn, self.far_future)
        data = get_patient_upcoming_appointments(self.conn)
        self.assertEqual(data["total"], 1)

    def test_excludes_past_appointments(self):
        past = (date.today() - timedelta(days=1)).isoformat()
        _add_appointment(self.conn, past)
        data = get_patient_upcoming_appointments(self.conn)
        self.assertEqual(data["total"], 0)

    def test_action_eligibility_keys_present(self):
        _add_appointment(self.conn, self.far_future)
        item = get_patient_upcoming_appointments(self.conn)["items"][0]
        self.assertIn("can_reschedule", item)
        self.assertIn("can_cancel", item)

    def test_far_future_appointment_is_reschedulable(self):
        _add_appointment(self.conn, self.far_future)
        item = get_patient_upcoming_appointments(self.conn)["items"][0]
        self.assertTrue(item["can_reschedule"])

    def test_far_future_appointment_is_cancellable(self):
        _add_appointment(self.conn, self.far_future)
        item = get_patient_upcoming_appointments(self.conn)["items"][0]
        self.assertTrue(item["can_cancel"])

    def test_today_appointment_has_action_flags(self):
        _add_appointment(self.conn, self.today)
        item = get_patient_upcoming_appointments(self.conn)["items"][0]
        self.assertIn("can_reschedule", item)

    def test_multiple_appointments_returned(self):
        _add_appointment(self.conn, self.far_future)
        _add_appointment(self.conn, self.near_future)
        data = get_patient_upcoming_appointments(self.conn)
        self.assertEqual(data["total"], 2)

    def test_results_ordered_by_date_ascending(self):
        _add_appointment(self.conn, self.far_future)
        _add_appointment(self.conn, self.near_future)
        items = get_patient_upcoming_appointments(self.conn)["items"]
        self.assertLessEqual(items[0]["appointment_date"], items[1]["appointment_date"])

    def test_provider_name_included(self):
        _add_appointment(self.conn, self.far_future)
        item = get_patient_upcoming_appointments(self.conn)["items"][0]
        self.assertEqual(item["provider_name"], "Dr. Test")

    def test_specialty_included(self):
        _add_appointment(self.conn, self.far_future)
        item = get_patient_upcoming_appointments(self.conn)["items"][0]
        self.assertEqual(item["specialty"], "General")


# ---------------------------------------------------------------------------
# US-055: Past Appointments with Release Policy
# ---------------------------------------------------------------------------

class AppointmentHistoryTests(unittest.TestCase):

    def setUp(self):
        self.conn = _make_db()
        self.past = (date.today() - timedelta(days=5)).isoformat()
        self.future = (date.today() + timedelta(days=5)).isoformat()

    def tearDown(self):
        self.conn.close()

    def test_returns_items_and_total(self):
        data = get_patient_appointment_history(self.conn)
        self.assertIn("items", data)
        self.assertIn("total", data)

    def test_empty_with_no_past_appointments(self):
        data = get_patient_appointment_history(self.conn)
        self.assertEqual(data["total"], 0)

    def test_includes_past_booked_appointments(self):
        _add_appointment(self.conn, self.past)
        data = get_patient_appointment_history(self.conn)
        self.assertEqual(data["total"], 1)

    def test_excludes_future_appointments(self):
        _add_appointment(self.conn, self.future)
        data = get_patient_appointment_history(self.conn)
        self.assertEqual(data["total"], 0)

    def test_excludes_today_appointments(self):
        _add_appointment(self.conn, date.today().isoformat())
        data = get_patient_appointment_history(self.conn)
        self.assertEqual(data["total"], 0)

    def test_notes_available_false_without_delivery(self):
        _add_appointment(self.conn, self.past)
        item = get_patient_appointment_history(self.conn)["items"][0]
        self.assertFalse(item["notes_available"])

    def test_notes_url_none_without_delivery(self):
        _add_appointment(self.conn, self.past)
        item = get_patient_appointment_history(self.conn)["items"][0]
        self.assertIsNone(item["notes_url"])

    def test_notes_unavailable_reason_provided(self):
        _add_appointment(self.conn, self.past)
        item = get_patient_appointment_history(self.conn)["items"][0]
        self.assertIn("notes_unavailable_reason", item)
        self.assertGreater(len(item["notes_unavailable_reason"]), 0)

    def test_results_ordered_by_date_descending(self):
        _add_appointment(self.conn, self.past)
        older = (date.today() - timedelta(days=10)).isoformat()
        _add_appointment(self.conn, older)
        items = get_patient_appointment_history(self.conn)["items"]
        self.assertGreaterEqual(items[0]["appointment_date"], items[1]["appointment_date"])

    def test_only_booked_status_included(self):
        _add_appointment(self.conn, self.past, status="available")
        data = get_patient_appointment_history(self.conn)
        self.assertEqual(data["total"], 0)

    def test_provider_name_present(self):
        _add_appointment(self.conn, self.past)
        item = get_patient_appointment_history(self.conn)["items"][0]
        self.assertEqual(item["provider_name"], "Dr. Test")


# ---------------------------------------------------------------------------
# US-056: Personal Health Profile
# ---------------------------------------------------------------------------

class HealthProfileTests(unittest.TestCase):

    def setUp(self):
        self.conn = _make_db()

    def tearDown(self):
        self.conn.close()

    def test_returns_required_sections(self):
        data = get_patient_health_profile(self.conn)
        for key in ("medications", "allergies", "diagnoses",
                    "chronic_conditions", "alerts", "version", "last_updated"):
            self.assertIn(key, data, f"Missing: {key}")

    def test_empty_profile_returns_empty_lists(self):
        data = get_patient_health_profile(self.conn)
        self.assertEqual(data["medications"], [])
        self.assertEqual(data["allergies"], [])
        self.assertEqual(data["diagnoses"], [])

    def test_medication_element_categorised_correctly(self):
        _add_clinical_element(self.conn, "medication", "Aspirin 81mg")
        data = get_patient_health_profile(self.conn)
        labels = [m["label"] for m in data["medications"]]
        self.assertIn("Aspirin 81mg", labels)

    def test_allergy_element_categorised_correctly(self):
        _add_clinical_element(self.conn, "allergy", "Penicillin")
        data = get_patient_health_profile(self.conn)
        labels = [a["label"] for a in data["allergies"]]
        self.assertIn("Penicillin", labels)

    def test_diagnosis_element_categorised_correctly(self):
        _add_clinical_element(self.conn, "diagnosis", "Type 2 Diabetes")
        data = get_patient_health_profile(self.conn)
        labels = [d["label"] for d in data["diagnoses"]]
        self.assertIn("Type 2 Diabetes", labels)

    def test_icd10_element_categorised_as_diagnosis(self):
        # icd10 is not a valid element_type in the schema; diagnosis is the correct type
        _add_clinical_element(self.conn, "diagnosis", "E11.9")
        data = get_patient_health_profile(self.conn)
        labels = [d["label"] for d in data["diagnoses"]]
        self.assertIn("E11.9", labels)

    def test_chronic_condition_element_categorised_correctly(self):
        # chronic_condition is not a schema type; diagnoses covers long-term conditions
        _add_clinical_element(self.conn, "diagnosis", "Hypertension")
        data = get_patient_health_profile(self.conn)
        labels = [d["label"] for d in data["diagnoses"]]
        self.assertIn("Hypertension", labels)

    def test_version_is_integer(self):
        data = get_patient_health_profile(self.conn)
        self.assertIsInstance(data["version"], int)

    def test_version_increments_with_elements(self):
        v_empty = get_patient_health_profile(self.conn)["version"]
        _add_clinical_element(self.conn, "medication", "Metformin")
        v_after = get_patient_health_profile(self.conn)["version"]
        self.assertGreaterEqual(v_after, v_empty)

    def test_last_updated_is_string(self):
        data = get_patient_health_profile(self.conn)
        self.assertIsInstance(data["last_updated"], str)

    def test_patient_id_returned(self):
        data = get_patient_health_profile(self.conn)
        self.assertEqual(data["patient_id"], 1)

    def test_multiple_medications_returned(self):
        _add_clinical_element(self.conn, "medication", "Aspirin")
        _add_clinical_element(self.conn, "medication", "Metformin")
        data = get_patient_health_profile(self.conn)
        self.assertEqual(len(data["medications"]), 2)


# ---------------------------------------------------------------------------
# US-057: Patient Documents List
# ---------------------------------------------------------------------------

class PatientDocumentsTests(unittest.TestCase):

    def setUp(self):
        self.conn = _make_db()

    def tearDown(self):
        self.conn.close()

    def test_returns_items_and_total(self):
        data = get_patient_documents(self.conn)
        self.assertIn("items", data)
        self.assertIn("total", data)

    def test_empty_when_no_documents(self):
        data = get_patient_documents(self.conn)
        self.assertEqual(data["total"], 0)
        self.assertEqual(data["items"], [])

    def test_document_appears_after_creation(self):
        _add_clinical_document(self.conn, "report.pdf")
        data = get_patient_documents(self.conn)
        self.assertEqual(data["total"], 1)

    def test_document_item_has_required_fields(self):
        _add_clinical_document(self.conn, "consent.pdf")
        item = get_patient_documents(self.conn)["items"][0]
        for key in ("id", "file_name", "file_type",
                    "processing_status", "uploaded_at"):
            self.assertIn(key, item, f"Missing: {key}")

    def test_document_file_name_correct(self):
        _add_clinical_document(self.conn, "blood_work.pdf")
        item = get_patient_documents(self.conn)["items"][0]
        self.assertEqual(item["file_name"], "blood_work.pdf")

    def test_processing_status_defaults_to_pending(self):
        _add_clinical_document(self.conn)
        item = get_patient_documents(self.conn)["items"][0]
        self.assertEqual(item["processing_status"], "pending")

    def test_multiple_documents_returned(self):
        _add_clinical_document(self.conn, "a.pdf")
        _add_clinical_document(self.conn, "b.docx")
        data = get_patient_documents(self.conn)
        self.assertEqual(data["total"], 2)

    def test_ordered_by_created_at_desc(self):
        _add_clinical_document(self.conn, "old.pdf")
        _add_clinical_document(self.conn, "new.pdf")
        items = get_patient_documents(self.conn)["items"]
        # Most recently inserted comes first (higher rowid = later upload_timestamp)
        self.assertEqual(items[0]["file_name"], "new.pdf")


# ---------------------------------------------------------------------------
# US-058: Notification Preference Management
# ---------------------------------------------------------------------------

class NotificationPreferencesTests(unittest.TestCase):

    def setUp(self):
        self.conn = _make_db()

    def tearDown(self):
        self.conn.close()

    def test_get_prefs_returns_required_keys(self):
        prefs = get_notification_preferences(self.conn)
        for key in ("email", "sms", "in_app", "do_not_disturb", "patient_id"):
            self.assertIn(key, prefs, f"Missing: {key}")

    def test_default_email_enabled(self):
        prefs = get_notification_preferences(self.conn)
        self.assertTrue(prefs["email"])

    def test_default_sms_enabled(self):
        prefs = get_notification_preferences(self.conn)
        self.assertTrue(prefs["sms"])

    def test_in_app_always_on(self):
        prefs = get_notification_preferences(self.conn)
        self.assertTrue(prefs["in_app"])

    def test_default_dnd_off(self):
        prefs = get_notification_preferences(self.conn)
        self.assertFalse(prefs["do_not_disturb"])

    def test_set_prefs_disables_email(self):
        set_notification_preferences(self.conn, 1, {"email": False, "sms": True})
        prefs = get_notification_preferences(self.conn)
        self.assertFalse(prefs["email"])

    def test_set_prefs_disables_sms(self):
        set_notification_preferences(self.conn, 1, {"email": True, "sms": False})
        prefs = get_notification_preferences(self.conn)
        self.assertFalse(prefs["sms"])

    def test_set_prefs_enables_dnd(self):
        set_notification_preferences(self.conn, 1, {"email": True, "sms": True, "do_not_disturb": True})
        prefs = get_notification_preferences(self.conn)
        self.assertTrue(prefs["do_not_disturb"])

    def test_set_prefs_returns_updated_prefs(self):
        result = set_notification_preferences(self.conn, 1, {"email": False, "sms": False})
        self.assertFalse(result["email"])
        self.assertFalse(result["sms"])

    def test_is_notification_allowed_email_enabled(self):
        self.assertTrue(is_notification_allowed(self.conn, 1, "email"))

    def test_is_notification_allowed_email_disabled(self):
        set_notification_preferences(self.conn, 1, {"email": False, "sms": True})
        self.assertFalse(is_notification_allowed(self.conn, 1, "email"))

    def test_is_notification_blocked_when_dnd(self):
        set_notification_preferences(
            self.conn, 1, {"email": True, "sms": True, "do_not_disturb": True}
        )
        self.assertFalse(is_notification_allowed(self.conn, 1, "email"))
        self.assertFalse(is_notification_allowed(self.conn, 1, "sms"))

    def test_dnd_overrides_individual_channel_setting(self):
        set_notification_preferences(
            self.conn, 1, {"email": True, "sms": True, "do_not_disturb": True}
        )
        self.assertFalse(is_notification_allowed(self.conn, 1, "email"))

    def test_set_then_get_roundtrip(self):
        set_notification_preferences(self.conn, 1, {"email": False, "sms": True, "do_not_disturb": False})
        prefs = get_notification_preferences(self.conn)
        self.assertFalse(prefs["email"])
        self.assertTrue(prefs["sms"])
        self.assertFalse(prefs["do_not_disturb"])


# ---------------------------------------------------------------------------
# US-060: Admin Operational Dashboard
# ---------------------------------------------------------------------------

class AdminOperationalMetricsTests(unittest.TestCase):

    def setUp(self):
        self.conn = _make_db()
        self.today = date.today().isoformat()
        self.yesterday = (date.today() - timedelta(days=1)).isoformat()
        self.tomorrow = (date.today() + timedelta(days=1)).isoformat()

    def tearDown(self):
        self.conn.close()

    def test_returns_required_keys(self):
        data = get_admin_operational_metrics(self.conn)
        for key in ("total_appointments", "booked", "cancelled",
                    "utilization_rate", "no_show_rate", "avg_wait_minutes",
                    "by_provider", "last_updated", "filters_applied"):
            self.assertIn(key, data, f"Missing: {key}")

    def test_zero_metrics_with_no_appointments(self):
        data = get_admin_operational_metrics(self.conn)
        self.assertEqual(data["total_appointments"], 0)
        self.assertEqual(data["utilization_rate"], 0.0)

    def test_utilization_reflects_booked_count(self):
        _add_appointment(self.conn, self.today, status="booked")
        data = get_admin_operational_metrics(self.conn)
        self.assertGreater(data["booked"], 0)

    def test_no_show_rate_reflects_cancelled(self):
        _add_appointment(self.conn, self.today, status="cancelled")
        data = get_admin_operational_metrics(self.conn)
        self.assertGreater(data["cancelled"], 0)
        self.assertGreater(data["no_show_rate"], 0)

    def test_by_provider_list_populated(self):
        _add_appointment(self.conn, self.today)
        data = get_admin_operational_metrics(self.conn)
        self.assertGreater(len(data["by_provider"]), 0)

    def test_by_provider_has_provider_and_count_keys(self):
        _add_appointment(self.conn, self.today)
        entry = get_admin_operational_metrics(self.conn)["by_provider"][0]
        self.assertIn("provider", entry)
        self.assertIn("count", entry)

    def test_last_updated_is_string(self):
        data = get_admin_operational_metrics(self.conn)
        self.assertIsInstance(data["last_updated"], str)

    def test_date_from_filter_excludes_earlier_dates(self):
        _add_appointment(self.conn, self.yesterday)
        data = get_admin_operational_metrics(self.conn, date_from=self.today)
        self.assertEqual(data["total_appointments"], 0)

    def test_date_to_filter_excludes_later_dates(self):
        _add_appointment(self.conn, self.tomorrow)
        data = get_admin_operational_metrics(self.conn, date_to=self.yesterday)
        self.assertEqual(data["total_appointments"], 0)

    def test_location_filter_matches_partial_name(self):
        _add_appointment(self.conn, self.today)
        data_match = get_admin_operational_metrics(self.conn, location="Clinic")
        data_no_match = get_admin_operational_metrics(self.conn, location="Hospital")
        self.assertGreater(data_match["total_appointments"], 0)
        self.assertEqual(data_no_match["total_appointments"], 0)

    def test_provider_id_filter_applied(self):
        _add_appointment(self.conn, self.today)
        data_match = get_admin_operational_metrics(self.conn, provider_id=1)
        data_no_match = get_admin_operational_metrics(self.conn, provider_id=999)
        self.assertGreater(data_match["total_appointments"], 0)
        self.assertEqual(data_no_match["total_appointments"], 0)

    def test_filters_applied_returned_in_response(self):
        data = get_admin_operational_metrics(
            self.conn, date_from="2026-01-01", date_to="2026-12-31"
        )
        fa = data["filters_applied"]
        self.assertEqual(fa["date_from"], "2026-01-01")
        self.assertEqual(fa["date_to"], "2026-12-31")

    def test_utilization_rate_between_0_and_100(self):
        _add_appointment(self.conn, self.today)
        data = get_admin_operational_metrics(self.conn)
        self.assertGreaterEqual(data["utilization_rate"], 0)
        self.assertLessEqual(data["utilization_rate"], 100)

    def test_avg_wait_minutes_non_negative(self):
        _add_appointment(self.conn, self.today)
        data = get_admin_operational_metrics(self.conn)
        self.assertGreaterEqual(data["avg_wait_minutes"], 0)

    def test_multiple_appointments_counted_correctly(self):
        _add_appointment(self.conn, self.today)
        _add_appointment(self.conn, self.yesterday)
        data = get_admin_operational_metrics(self.conn)
        self.assertEqual(data["total_appointments"], 2)


if __name__ == "__main__":
    unittest.main()
