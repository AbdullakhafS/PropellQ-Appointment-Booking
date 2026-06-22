from __future__ import annotations

import shutil
import sqlite3
import tempfile
from pathlib import Path
from unittest import TestCase

from src.booking_service import utc_now, to_iso
from src.db import initialize_database, get_connection
from src.restore_verification import (
    RestoreVerificationEngine,
    VerificationStatus,
    VerificationType,
)


class TestRestoreVerificationEngine(TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_appointments.db"
        self.restored_db_path = Path(self.temp_dir.name) / "restored_appointments.db"
        initialize_database(self.db_path)
        # Create a copy for restore testing
        if self.db_path.exists():
            shutil.copy2(self.db_path, self.restored_db_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_record_restore_event(self) -> None:
        with get_connection(self.db_path) as connection:
            engine = RestoreVerificationEngine(connection)

            event_id = engine.record_restore_event(
                backup_execution_id="backup-123",
                dataset_name="appointments",
                restore_type="drill",
                restore_target_environment="dev-restore-box",
                operator_identity="test-operator",
            )

            self.assertIsNotNone(event_id)

            cursor = connection.execute(
                "SELECT * FROM restore_events WHERE event_id = ?",
                [event_id],
            )
            row = cursor.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["dataset_name"], "appointments")
            self.assertEqual(row["status"], "initiated")
            self.assertEqual(row["restore_type"], "drill")

    def test_update_restore_event_status(self) -> None:
        with get_connection(self.db_path) as connection:
            engine = RestoreVerificationEngine(connection)

            event_id = engine.record_restore_event(
                backup_execution_id="backup-123",
                dataset_name="appointments",
                restore_type="drill",
                restore_target_environment="dev-restore-box",
                operator_identity="test-operator",
            )

            completed_at = utc_now()
            engine.update_restore_event_status(
                event_id,
                "completed",
                completed_at=completed_at,
                rpo_achieved=45,
                rto_achieved=90,
            )

            cursor = connection.execute(
                "SELECT * FROM restore_events WHERE event_id = ?",
                [event_id],
            )
            row = cursor.fetchone()
            self.assertEqual(row["status"], "completed")
            self.assertEqual(row["rpo_achieved_minutes"], 45)
            self.assertEqual(row["rto_achieved_minutes"], 90)

    def test_verify_schema_success(self) -> None:
        with get_connection(self.db_path) as connection:
            engine = RestoreVerificationEngine(connection)

            restored_connection = sqlite3.connect(str(self.restored_db_path))
            restored_connection.row_factory = sqlite3.Row
            result = engine._verify_schema("event-123", restored_connection)
            restored_connection.close()

            self.assertEqual(result.verification_type, VerificationType.SCHEMA)
            self.assertEqual(result.status, VerificationStatus.PASSED)

    def test_verify_row_counts(self) -> None:
        with get_connection(self.db_path) as connection:
            engine = RestoreVerificationEngine(connection)

            # Insert test data in original database
            connection.execute(
                "INSERT INTO specialties (name, is_active) VALUES (?, ?)",
                ["Cardiology", 1],
            )
            connection.commit()

            # Copy to restored database
            if self.restored_db_path.exists():
                self.restored_db_path.unlink()
            shutil.copy2(self.db_path, self.restored_db_path)

            # Verify row counts
            restored_connection = sqlite3.connect(str(self.restored_db_path))
            restored_connection.row_factory = sqlite3.Row
            results = engine._verify_row_counts("event-123", restored_connection)
            restored_connection.close()

            self.assertGreater(len(results), 0)
            specialty_result = next(
                (r for r in results if r.verification_target_table == "specialties"),
                None,
            )
            self.assertIsNotNone(specialty_result)
            self.assertEqual(specialty_result.status, VerificationStatus.PASSED)

    def test_verify_referential_integrity(self) -> None:
        with get_connection(self.db_path) as connection:
            engine = RestoreVerificationEngine(connection)

            restored_connection = sqlite3.connect(str(self.restored_db_path))
            restored_connection.row_factory = sqlite3.Row
            results = engine._verify_referential_integrity("event-123", restored_connection)
            restored_connection.close()

            self.assertGreater(len(results), 0)
            referential_result = results[0]
            self.assertEqual(referential_result.verification_type, VerificationType.REFERENTIAL)
            # Should pass with clean data
            self.assertEqual(referential_result.status, VerificationStatus.PASSED)

    def test_verify_critical_queries(self) -> None:
        with get_connection(self.db_path) as connection:
            engine = RestoreVerificationEngine(connection)

            restored_connection = sqlite3.connect(str(self.restored_db_path))
            restored_connection.row_factory = sqlite3.Row
            results = engine._verify_critical_queries("event-123", restored_connection)
            restored_connection.close()

            self.assertGreater(len(results), 0)
            for result in results:
                self.assertEqual(result.verification_type, VerificationType.CRITICAL_QUERY)
                self.assertEqual(result.status, VerificationStatus.PASSED)

    def test_comprehensive_restore_verification(self) -> None:
        with get_connection(self.db_path) as connection:
            engine = RestoreVerificationEngine(connection)

            # Insert test data
            connection.execute(
                "INSERT INTO specialties (name, is_active) VALUES (?, ?)",
                ["Internal Medicine", 1],
            )
            connection.commit()

            # Copy to restored database
            if self.restored_db_path.exists():
                self.restored_db_path.unlink()
            shutil.copy2(self.db_path, self.restored_db_path)

            # Run full verification
            event_id = engine.record_restore_event(
                backup_execution_id="backup-456",
                dataset_name="appointments",
                restore_type="drill",
                restore_target_environment="staging-restore",
                operator_identity="qa-operator",
            )

            all_passed, results = engine.verify_restore(event_id, self.restored_db_path)

            self.assertTrue(all_passed)
            self.assertGreater(len(results), 0)

            # Verify all verification records were persisted
            cursor = connection.execute(
                "SELECT COUNT(*) FROM restore_verification WHERE restore_event_id = ?",
                [event_id],
            )
            count = cursor.fetchone()[0]
            self.assertGreater(count, 0)

    def test_verify_restore_with_corrupted_database(self) -> None:
        with get_connection(self.db_path) as connection:
            engine = RestoreVerificationEngine(connection)

            # Create a corrupted database file (just empty)
            corrupted_db = Path(self.temp_dir.name) / "corrupted.db"
            corrupted_db.write_text("CORRUPTED DATA")

            event_id = engine.record_restore_event(
                backup_execution_id="backup-789",
                dataset_name="appointments",
                restore_type="emergency",
                restore_target_environment="prod-restore",
                operator_identity="dba-operator",
            )

            # This should fail gracefully
            with self.assertRaises(Exception):
                engine.verify_restore(event_id, corrupted_db)

    def test_persist_verification_result(self) -> None:
        with get_connection(self.db_path) as connection:
            engine = RestoreVerificationEngine(connection)

            from src.restore_verification import VerificationResult

            result = VerificationResult(
                verification_id="verify-123",
                restore_event_id="event-456",
                verification_type=VerificationType.ROW_COUNT,
                verification_target_table="appointments",
                expected_result="1000",
                actual_result="1000",
                status=VerificationStatus.PASSED,
                failure_reason=None,
            )

            engine._persist_verification_result(result)

            cursor = connection.execute(
                "SELECT * FROM restore_verification WHERE verification_id = ?",
                ["verify-123"],
            )
            row = cursor.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["status"], "passed")
            self.assertEqual(row["verification_type"], "row_count")


if __name__ == "__main__":
    import unittest

    unittest.main()
