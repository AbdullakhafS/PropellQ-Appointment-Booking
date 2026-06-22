from __future__ import annotations

import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest import TestCase

from src.backup_automation import (
    BackupEngine,
    BackupPolicy,
    BackupStatus,
    BackupType,
    InMemoryBackupAlertSink,
)
from src.booking_service import utc_now, to_iso
from src.db import initialize_database, get_connection


class TestBackupEngine(TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_appointments.db"
        initialize_database(self.db_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_register_backup_policy(self) -> None:
        with get_connection(self.db_path) as connection:
            engine = BackupEngine(connection)

            policy = BackupPolicy(
                policy_name="production_full_backup",
                dataset_name="appointments",
                backup_type=BackupType.FULL,
                schedule_cron="0 2 * * *",
                retention_days=30,
                encryption_algorithm="AES-256-GCM",
                kms_key_id="arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012",
                compression_enabled=True,
                storage_location="/mnt/backups",
                owner_team="platform-team",
                rpo_target_minutes=60,
                rto_target_minutes=120,
            )

            engine.register_policy(policy)

            cursor = connection.execute(
                "SELECT * FROM backup_policies WHERE policy_name = ?",
                ["production_full_backup"],
            )
            row = cursor.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["dataset_name"], "appointments")
            self.assertEqual(row["backup_type"], "full")
            self.assertEqual(row["retention_days"], 30)

    def test_execute_backup_success(self) -> None:
        with get_connection(self.db_path) as connection:
            engine = BackupEngine(connection)
            alert_sink = InMemoryBackupAlertSink()
            engine.alert_sink = alert_sink

            policy = BackupPolicy(
                policy_name="test_backup",
                dataset_name="appointments",
                backup_type=BackupType.FULL,
                schedule_cron="0 2 * * *",
                retention_days=30,
                encryption_algorithm="AES-256-GCM",
                kms_key_id=None,
                compression_enabled=True,
                storage_location="/mnt/backups",
                owner_team="platform-team",
                rpo_target_minutes=60,
                rto_target_minutes=120,
            )

            engine.register_policy(policy)
            execution = engine.execute_backup("test_backup", "test-operator")

            self.assertEqual(execution.policy_name, "test_backup")
            self.assertEqual(execution.status, BackupStatus.SUCCEEDED)
            self.assertIsNotNone(execution.backup_location)
            self.assertIsNotNone(execution.backup_checksum)
            self.assertGreater(execution.backup_size_bytes or 0, 0)

            # Verify audit trail recorded
            cursor = connection.execute(
                "SELECT * FROM backup_audit_trail WHERE action_type = 'backup_completed'"
            )
            audit = cursor.fetchone()
            self.assertIsNotNone(audit)

    def test_backup_nonexistent_policy(self) -> None:
        with get_connection(self.db_path) as connection:
            engine = BackupEngine(connection)

            with self.assertRaises(LookupError):
                engine.execute_backup("nonexistent_policy")

    def test_backup_alerts_on_failure(self) -> None:
        with get_connection(self.db_path) as connection:
            alert_sink = InMemoryBackupAlertSink()
            engine = BackupEngine(connection, alert_sink=alert_sink)

            policy = BackupPolicy(
                policy_name="bad_policy",
                dataset_name="appointments",
                backup_type=BackupType.FULL,
                schedule_cron="0 2 * * *",
                retention_days=30,
                encryption_algorithm="AES-256-GCM",
                kms_key_id=None,
                compression_enabled=True,
                storage_location="/nonexistent/dir",
                owner_team="platform-team",
                rpo_target_minutes=60,
                rto_target_minutes=120,
            )

            engine.register_policy(policy)

            with self.assertRaises(Exception):
                engine.execute_backup("bad_policy")

            # Verify alert was emitted
            self.assertGreater(len(alert_sink.alerts), 0)
            alert = alert_sink.alerts[0]
            self.assertEqual(alert["alertType"], "backup_failed")
            self.assertEqual(alert["severity"], "critical")

    def test_latest_execution_success(self) -> None:
        with get_connection(self.db_path) as connection:
            engine = BackupEngine(connection)

            policy = BackupPolicy(
                policy_name="test_policy",
                dataset_name="appointments",
                backup_type=BackupType.FULL,
                schedule_cron="0 2 * * *",
                retention_days=30,
                encryption_algorithm="AES-256-GCM",
                kms_key_id=None,
                compression_enabled=True,
                storage_location="/mnt/backups",
                owner_team="platform-team",
                rpo_target_minutes=60,
                rto_target_minutes=120,
            )

            engine.register_policy(policy)
            execution = engine.execute_backup("test_policy", "operator1")

            latest = engine.latest_execution("appointments")
            self.assertEqual(latest.execution_id, execution.execution_id)
            self.assertEqual(latest.status, BackupStatus.SUCCEEDED)

    def test_backup_execution_persistence(self) -> None:
        with get_connection(self.db_path) as connection:
            engine = BackupEngine(connection)

            policy = BackupPolicy(
                policy_name="persistent_policy",
                dataset_name="appointments",
                backup_type=BackupType.FULL,
                schedule_cron="0 2 * * *",
                retention_days=30,
                encryption_algorithm="AES-256-GCM",
                kms_key_id=None,
                compression_enabled=True,
                storage_location="/mnt/backups",
                owner_team="platform-team",
                rpo_target_minutes=60,
                rto_target_minutes=120,
            )

            engine.register_policy(policy)
            execution1 = engine.execute_backup("persistent_policy", "op1")

            # Query directly from database
            cursor = connection.execute(
                "SELECT * FROM backup_executions WHERE execution_id = ?",
                [execution1.execution_id],
            )
            row = cursor.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["status"], "succeeded")
            self.assertEqual(row["operator_identity"], "op1")


if __name__ == "__main__":
    import unittest

    unittest.main()
