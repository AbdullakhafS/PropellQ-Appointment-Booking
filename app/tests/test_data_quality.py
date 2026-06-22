from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from src import db
from src.data_quality import (
    DataQualityEngine,
    EnforcementMode,
    InMemoryQualityAlertSink,
)


class DataQualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.temp_dir.name) / "quality.db"
        db.initialize_database(cls.db_path)

    @classmethod
    def tearDownClass(cls) -> None:
        try:
            cls.temp_dir.cleanup()
        except PermissionError:
            pass

    def setUp(self) -> None:
        self.connection = db.get_connection(self.db_path)
        self.report_dir = Path(self.temp_dir.name) / "reports"
        self.alert_sink = InMemoryQualityAlertSink()
        self.engine = DataQualityEngine(self.connection, report_dir=self.report_dir, alert_sink=self.alert_sink)

    def tearDown(self) -> None:
        self.connection.close()

    def test_completeness_and_validity_rules_detect_invalid_records(self) -> None:
        report = self.engine.validate_records(
            "appointments",
            [
                {
                    "provider_id": None,
                    "specialty_id": 1,
                    "appointment_date": "2026-07-01",
                    "start_time": "09:00:00",
                    "end_time": "09:30:00",
                    "location": "Clinic",
                    "status": "invalid",
                    "duration_minutes": 0,
                    "appointment_timezone": "America/Chicago",
                }
            ],
            stage_name="ingest",
            enforcement_mode=EnforcementMode.WARN,
            reference_time=datetime(2026, 6, 22, tzinfo=timezone.utc),
        )

        self.assertGreaterEqual(report.violation_count, 2)
        self.assertGreaterEqual(report.warning_count + report.critical_count, 2)
        self.assertTrue(self.report_dir.joinpath(f"quality_{report.run_id}.json").exists())

    def test_duplicate_detection_flags_patient_records(self) -> None:
        report = self.engine.validate_records(
            "patient_profiles",
            [
                {"id": 1, "first_name": "Alex", "last_name": "Morgan", "email": "alex@example.com", "phone": "+155555501", "preferred_timezone": "America/Chicago", "reminder_channels": '["sms"]', "do_not_disturb": 0},
                {"id": 2, "first_name": "Alex", "last_name": "Morgan", "email": "alex@example.com", "phone": "+155555501", "preferred_timezone": "America/Chicago", "reminder_channels": '["sms"]', "do_not_disturb": 0},
            ],
            stage_name="publish",
            enforcement_mode=EnforcementMode.WARN,
        )

        self.assertGreaterEqual(report.violation_count, 1)
        self.assertTrue(any(violation.rule_code == "DQ-PAT-003" for violation in report.violations))
        self.assertTrue(any(alert["ownerTeam"] == "patient-services" for alert in self.alert_sink.alerts))

    def test_consistency_mismatch_reports_cross_table_conflict(self) -> None:
        report = self.engine.validate_records(
            "appointments",
            [
                {
                    "id": 9999,
                    "provider_id": 1,
                    "specialty_id": 999,
                    "appointment_date": "2026-07-01",
                    "start_time": "09:00:00",
                    "end_time": "09:30:00",
                    "location": "Clinic",
                    "status": "available",
                    "duration_minutes": 30,
                    "appointment_timezone": "America/Chicago",
                    "patient_email": "not-an-email",
                }
            ],
            stage_name="publish",
            enforcement_mode=EnforcementMode.BLOCK,
        )

        self.assertGreaterEqual(report.blocked_count, 1)
        self.assertTrue(report.publish_blocked)
        self.assertTrue(any(v.publish_blocking for v in report.violations))

    def test_severity_alert_routing_uses_team_context(self) -> None:
        report = self.engine.validate_records(
            "medications",
            [
                {"medication_name": None, "dosage": -1, "route": None, "status": "unknown"}
            ],
            stage_name="ingest",
            enforcement_mode=EnforcementMode.BLOCK,
        )

        self.assertGreaterEqual(report.critical_count, 1)
        self.assertTrue(any(alert["severity"] == "critical" for alert in self.alert_sink.alerts))
        self.assertTrue(any(alert["triageSlaMinutes"] == 15 for alert in self.alert_sink.alerts))

    def test_trend_report_captures_run_metrics(self) -> None:
        report = self.engine.validate_records(
            "appointments",
            [
                {
                    "provider_id": None,
                    "specialty_id": 1,
                    "appointment_date": "2026-07-01",
                    "start_time": "09:00:00",
                    "end_time": "09:30:00",
                    "location": "Clinic",
                    "status": "invalid",
                    "duration_minutes": 0,
                    "appointment_timezone": "America/Chicago",
                }
            ],
            stage_name="ingest",
            enforcement_mode=EnforcementMode.WARN,
        )
        trend = self.engine.trend_report(days=7)
        self.assertGreaterEqual(trend["totalRuns"], 1)
        self.assertIn("daily", trend)
        self.assertTrue(self.report_dir.joinpath(f"quality_{report.run_id}.json").exists())

    def test_publish_gate_blocks_and_quarantines_severe_failures(self) -> None:
        decision = self.engine.validate_publish_batch(
            {
                "appointments": [
                    {
                        "provider_id": None,
                        "specialty_id": 1,
                        "appointment_date": "2026-07-01",
                        "start_time": "09:00:00",
                        "end_time": "09:30:00",
                        "location": "Clinic",
                        "status": "invalid",
                        "duration_minutes": 0,
                        "appointment_timezone": "America/Chicago",
                    }
                ]
            },
            enforcement_mode=EnforcementMode.BLOCK,
        )

        self.assertTrue(decision.blocked)
        self.assertGreaterEqual(decision.blocked_count, 1)
        self.assertGreaterEqual(decision.quarantine_count, 1)


if __name__ == "__main__":
    unittest.main()
