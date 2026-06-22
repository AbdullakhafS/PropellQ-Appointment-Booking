from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from dataclasses import replace
from pathlib import Path

from src import db
from src.lifecycle_jobs import (
    InMemoryAlertSink,
    LifecycleAction,
    LifecycleJobEngine,
    LifecyclePolicyVersion,
    create_subject,
)


class LifecycleJobTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.temp_dir.name) / "lifecycle.db"
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
        self.alert_sink = InMemoryAlertSink()
        self.engine = LifecycleJobEngine(
            self.connection,
            report_dir=self.report_dir,
            alert_sink=self.alert_sink,
            max_attempts=2,
            base_backoff_seconds=3,
        )

    def tearDown(self) -> None:
        self.connection.close()

    def _policy(self, version_label: str = "2026.06") -> LifecyclePolicyVersion:
        return LifecyclePolicyVersion(
            policy_name="clinical-records-retention",
            dataset_name="clinical_records",
            action_type=LifecycleAction.ARCHIVE,
            retention_days=30,
            archive_after_days=7,
            immutable_retention_days=21,
            timezone_name="America/Chicago",
            owner_email="compliance@example.com",
            version_label=version_label,
            effective_from=datetime(2026, 6, 1, tzinfo=timezone.utc),
        )

    def _register_subject(self, *, created_at: datetime, record_key: str = "record-1", hold: bool = False) -> None:
        policy = self._policy()
        self.engine.register_policy(policy)
        subject = create_subject(
            dataset_name=policy.dataset_name,
            record_key=record_key,
            payload={"recordKey": record_key, "value": "sensitive"},
            created_at=created_at,
            policy=policy,
        )
        if hold:
            subject = replace(subject, legal_hold=True, hold_reason="Regulatory review")
        self.engine.register_subject(subject)

    def test_archive_and_purge_transition_across_timezone_boundary(self) -> None:
        created_at = datetime(2026, 6, 1, 23, 30, tzinfo=timezone.utc)
        self._register_subject(created_at=created_at)

        before_boundary = datetime(2026, 6, 8, 4, 59, tzinfo=timezone.utc)
        before_report = self.engine.run_archive(reference_time=before_boundary)
        self.assertEqual(before_report.archive_count, 0)

        after_boundary = datetime(2026, 6, 8, 5, 1, tzinfo=timezone.utc)
        archive_report = self.engine.run_archive(reference_time=after_boundary)
        self.assertEqual(archive_report.archive_count, 1)
        self.assertTrue((self.report_dir / f"{archive_report.run_id}.json").exists())

        purge_before = datetime(2026, 6, 30, 4, 59, tzinfo=timezone.utc)
        purge_before_report = self.engine.run_purge(reference_time=purge_before)
        self.assertEqual(purge_before_report.purge_count, 0)

        purge_after = datetime(2026, 7, 1, 5, 1, tzinfo=timezone.utc)
        purge_report = self.engine.run_purge(reference_time=purge_after)
        self.assertEqual(purge_report.purge_count, 1)

    def test_immutable_retention_blocks_early_purge(self) -> None:
        policy = LifecyclePolicyVersion(
            policy_name="audit-log-retention",
            dataset_name="audit_logs",
            action_type=LifecycleAction.PURGE,
            retention_days=10,
            archive_after_days=1,
            immutable_retention_days=30,
            timezone_name="America/Chicago",
            owner_email="audit@example.com",
            version_label="2026.06-audit",
            effective_from=datetime(2026, 6, 1, tzinfo=timezone.utc),
        )
        self.engine.register_policy(policy)
        subject = create_subject(
            dataset_name=policy.dataset_name,
            record_key="audit-1",
            payload={"recordKey": "audit-1", "value": "immutable"},
            created_at=datetime(2026, 6, 1, 23, 30, tzinfo=timezone.utc),
            policy=policy,
        )
        self.engine.register_subject(subject)

        archive_report = self.engine.run_archive(reference_time=datetime(2026, 6, 2, 6, 0, tzinfo=timezone.utc))
        self.assertEqual(archive_report.archive_count, 1)

        purge_report = self.engine.run_purge(reference_time=datetime(2026, 6, 11, 5, 1, tzinfo=timezone.utc))
        self.assertEqual(purge_report.blocked_count, 1)
        row = self.connection.execute(
            "SELECT archive_status, purged_at FROM lifecycle_subjects WHERE dataset_name = ? AND record_key = ?",
            [policy.dataset_name, "audit-1"],
        ).fetchone()
        self.assertEqual(row["archive_status"], "archived")
        self.assertIsNone(row["purged_at"])

    def test_legal_hold_excludes_purge_and_logs_exception(self) -> None:
        created_at = datetime(2026, 6, 1, 23, 30, tzinfo=timezone.utc)
        self._register_subject(created_at=created_at, record_key="held-1", hold=True)

        archive_report = self.engine.run_archive(reference_time=datetime(2026, 6, 8, 5, 1, tzinfo=timezone.utc))
        self.assertEqual(archive_report.archive_count, 1)

        purge_report = self.engine.run_purge(reference_time=datetime(2026, 7, 1, 5, 1, tzinfo=timezone.utc))
        self.assertEqual(purge_report.skipped_count, 1)
        event_row = self.connection.execute(
            """
            SELECT event_type, status, reason
            FROM lifecycle_execution_events
            WHERE event_type = 'hold_skip'
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
        self.assertEqual(event_row["status"], "skipped")
        self.assertIn("hold", event_row["reason"].lower())

    def test_retry_backoff_emits_alerts(self) -> None:
        attempts = {"count": 0}

        def always_fail(_run_id: str):
            attempts["count"] += 1
            raise ValueError("transient failure")

        with self.assertRaises(RuntimeError):
            self.engine.execute_with_retry(
                "archive",
                always_fail,
                "clinical_records",
                datetime(2026, 6, 1, tzinfo=timezone.utc),
                False,
                "scheduler",
            )

        self.assertEqual(attempts["count"], 2)
        self.assertEqual(len(self.alert_sink.alerts), 2)
        self.assertEqual(self.alert_sink.alerts[0]["backoffSeconds"], 3)
        self.assertEqual(self.alert_sink.alerts[1]["backoffSeconds"], 6)
        self.assertEqual(self.alert_sink.alerts[1]["severity"], "critical")

    def test_authorized_retrieval_returns_payload_and_logs_audit(self) -> None:
        created_at = datetime(2026, 6, 1, 23, 30, tzinfo=timezone.utc)
        self._register_subject(created_at=created_at, record_key="retrieval-1")
        self.engine.run_archive(reference_time=datetime(2026, 6, 8, 5, 1, tzinfo=timezone.utc))

        payload = self.engine.retrieve_archived_record("clinical_records", "retrieval-1", "auditor")
        self.assertEqual(payload["recordKey"], "retrieval-1")

        archive_row = self.connection.execute(
            "SELECT retrieval_count FROM lifecycle_archive_entries WHERE dataset_name = ? AND record_key = ?",
            ["clinical_records", "retrieval-1"],
        ).fetchone()
        self.assertEqual(archive_row["retrieval_count"], 1)

        event_row = self.connection.execute(
            "SELECT event_type, status FROM lifecycle_execution_events WHERE event_type = 'retrieval' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        self.assertEqual(event_row["status"], "success")

        with self.assertRaises(PermissionError):
            self.engine.retrieve_archived_record("clinical_records", "retrieval-1", "guest")

    def test_report_includes_policy_versions_and_evidence(self) -> None:
        created_at = datetime(2026, 6, 1, 23, 30, tzinfo=timezone.utc)
        self._register_subject(created_at=created_at, record_key="report-1")
        report = self.engine.run_archive(reference_time=datetime(2026, 6, 8, 5, 1, tzinfo=timezone.utc))

        self.assertIn("2026.06", report.policy_versions)
        self.assertIsNotNone(report.evidence_path)
        self.assertTrue(report.evidence_path.exists())

        persisted = json.loads(report.evidence_path.read_text(encoding="utf-8"))
        self.assertIn("2026.06", persisted["policyVersions"])
        self.assertEqual(persisted["counts"]["archived"], 1)


if __name__ == "__main__":
    unittest.main()
