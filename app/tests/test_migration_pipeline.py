from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.migration_pipeline import (
    DB_DIR,
    MigrationDefinition,
    MigrationExecutionContext,
    MigrationPipeline,
)


class MigrationPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "migration.db"
        self.pipeline = MigrationPipeline(self.db_path)
        self.context = MigrationExecutionContext(
            environment="development",
            approver="test.approver@propellq.com",
            rationale="migration rehearsal",
        )

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except PermissionError:
            pass

    def test_manifest_is_versioned(self):
        self.assertGreaterEqual(len(self.pipeline.manifest), 1)
        self.assertEqual(self.pipeline.manifest[0].version, "1.0.0")

    def test_migration_applies_in_order_and_verifies(self):
        records = self.pipeline.migrate(self.context)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].status.value, "applied")
        self.assertTrue(self.db_path.exists())

        verification = self.pipeline.verify_post_deploy("1.0.0")
        self.assertEqual(verification["expected_version"], "1.0.0")
        self.assertEqual(verification["actual_version"], "1")
        self.assertTrue(verification["tables_present"]["appointments"])
        self.assertTrue(verification["tables_present"]["patient_profiles"])

    def test_rollback_restores_previous_database(self):
        self.pipeline.migrate(self.context)
        backup_files = sorted(self.db_path.parent.glob(f"{self.db_path.stem}.backup.*.db"))
        self.assertTrue(backup_files)

        with backup_files[-1].open("rb") as handle:
            expected = handle.read()

        rollback_record = self.pipeline.rollback_last(self.context, backup_files[-1])
        self.assertEqual(rollback_record.status.value, "rolled_back")

        with self.db_path.open("rb") as handle:
            after = handle.read()

        self.assertEqual(expected, after)

    def test_lint_blocks_destructive_patterns(self):
        bad_sql = Path(self.temp_dir.name) / "bad.sql"
        bad_sql.write_text("DROP TABLE appointments;", encoding="utf-8")
        migration = MigrationDefinition(
            version="9.9.9",
            name="bad",
            sql_file=bad_sql.name,
            rollback_sql_file=None,
            rollback_strategy="restore_backup",
            requires_approval=False,
            destructive_patterns_allowed=False,
            verification_tables=[],
            smoke_queries=[],
        )

        with patch("src.migration_pipeline.DB_DIR", Path(self.temp_dir.name)):
            issues = self.pipeline.lint_migration(migration)

        self.assertTrue(any("Forbidden destructive pattern" in issue for issue in issues))

    def test_audit_log_is_written(self):
        self.pipeline.migrate(self.context)
        self.assertTrue(self.pipeline.audit_path.exists())
        audit_lines = self.pipeline.audit_path.read_text(encoding="utf-8").strip().splitlines()
        self.assertGreaterEqual(len(audit_lines), 1)
        payload = json.loads(audit_lines[-1])
        self.assertEqual(payload["status"], "applied")


if __name__ == "__main__":
    unittest.main()
