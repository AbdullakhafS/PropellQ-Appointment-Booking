from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from src.booking_service import parse_iso, to_iso, utc_now

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = BASE_DIR / "db" / "appointments.db"


class VerificationType(str, Enum):
    ROW_COUNT = "row_count"
    CHECKSUM = "checksum"
    REFERENTIAL = "referential"
    CRITICAL_QUERY = "critical_query"
    SCHEMA = "schema"


class VerificationStatus(str, Enum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class VerificationResult:
    verification_id: str
    restore_event_id: str
    verification_type: VerificationType
    verification_target_table: str | None
    expected_result: str
    actual_result: str
    status: VerificationStatus
    failure_reason: str | None = None


class RestoreVerificationEngine:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.row_factory = sqlite3.Row

    def verify_restore(
        self,
        restore_event_id: str,
        restored_db_path: Path,
    ) -> tuple[bool, list[VerificationResult]]:
        """Execute comprehensive restore verification suite."""
        connection_restored = sqlite3.connect(str(restored_db_path))
        connection_restored.row_factory = sqlite3.Row
        results: list[VerificationResult] = []

        try:
            # Verify schema integrity
            schema_result = self._verify_schema(restore_event_id, connection_restored)
            results.append(schema_result)

            # Verify row counts
            row_count_results = self._verify_row_counts(restore_event_id, connection_restored)
            results.extend(row_count_results)

            # Verify referential integrity
            referential_results = self._verify_referential_integrity(
                restore_event_id,
                connection_restored,
            )
            results.extend(referential_results)

            # Verify critical queries
            critical_query_results = self._verify_critical_queries(
                restore_event_id,
                connection_restored,
            )
            results.extend(critical_query_results)

            # Persist results
            for result in results:
                self._persist_verification_result(result)

            all_passed = all(r.status == VerificationStatus.PASSED for r in results)
            return all_passed, results
        finally:
            connection_restored.close()

    def _verify_schema(
        self,
        restore_event_id: str,
        restored_connection: sqlite3.Connection,
    ) -> VerificationResult:
        """Verify schema tables exist and match expected structure."""
        verification_id = uuid.uuid4().hex
        expected_tables = [
            "specialties",
            "providers",
            "appointments",
            "patient_profiles",
            "appointment_reservations",
            "calendar_sync_queue",
            "backup_policies",
            "backup_executions",
            "restore_events",
            "restore_verification",
        ]

        cursor = restored_connection.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        actual_tables = sorted([row[0] for row in cursor.fetchall()])
        expected_sorted = sorted(expected_tables)

        status = (
            VerificationStatus.PASSED
            if set(expected_tables).issubset(set(actual_tables))
            else VerificationStatus.FAILED
        )
        failure_reason = (
            None
            if status == VerificationStatus.PASSED
            else f"Missing tables: {set(expected_tables) - set(actual_tables)}"
        )

        result = VerificationResult(
            verification_id=verification_id,
            restore_event_id=restore_event_id,
            verification_type=VerificationType.SCHEMA,
            verification_target_table=None,
            expected_result=json.dumps(expected_sorted),
            actual_result=json.dumps(actual_tables),
            status=status,
            failure_reason=failure_reason,
        )
        return result

    def _verify_row_counts(
        self,
        restore_event_id: str,
        restored_connection: sqlite3.Connection,
    ) -> list[VerificationResult]:
        """Verify row counts match between original and restored databases."""
        results: list[VerificationResult] = []
        cursor_restored = restored_connection.cursor()
        cursor_original = self.connection.cursor()

        tables = [
            "specialties",
            "providers",
            "appointments",
            "patient_profiles",
            "appointment_reservations",
        ]

        for table in tables:
            verification_id = uuid.uuid4().hex

            try:
                cursor_original.execute(f"SELECT COUNT(*) FROM {table}")
                expected_count = cursor_original.fetchone()[0]

                cursor_restored.execute(f"SELECT COUNT(*) FROM {table}")
                actual_count = cursor_restored.fetchone()[0]

                status = (
                    VerificationStatus.PASSED
                    if expected_count == actual_count
                    else VerificationStatus.FAILED
                )
                failure_reason = (
                    None
                    if status == VerificationStatus.PASSED
                    else f"Expected {expected_count}, got {actual_count}"
                )

                result = VerificationResult(
                    verification_id=verification_id,
                    restore_event_id=restore_event_id,
                    verification_type=VerificationType.ROW_COUNT,
                    verification_target_table=table,
                    expected_result=str(expected_count),
                    actual_result=str(actual_count),
                    status=status,
                    failure_reason=failure_reason,
                )
                results.append(result)
            except Exception as exc:
                result = VerificationResult(
                    verification_id=verification_id,
                    restore_event_id=restore_event_id,
                    verification_type=VerificationType.ROW_COUNT,
                    verification_target_table=table,
                    expected_result="N/A",
                    actual_result="N/A",
                    status=VerificationStatus.FAILED,
                    failure_reason=str(exc),
                )
                results.append(result)

        return results

    def _verify_referential_integrity(
        self,
        restore_event_id: str,
        restored_connection: sqlite3.Connection,
    ) -> list[VerificationResult]:
        """Verify foreign key referential integrity."""
        results: list[VerificationResult] = []
        verification_id = uuid.uuid4().hex

        restored_connection.execute("PRAGMA foreign_keys = ON;")
        cursor = restored_connection.cursor()
        cursor.execute("PRAGMA foreign_key_check;")
        violations = cursor.fetchall()

        status = VerificationStatus.PASSED if not violations else VerificationStatus.FAILED
        failure_reason = (
            None if not violations else f"Found {len(violations)} referential integrity violations"
        )

        result = VerificationResult(
            verification_id=verification_id,
            restore_event_id=restore_event_id,
            verification_type=VerificationType.REFERENTIAL,
            verification_target_table=None,
            expected_result="0 violations",
            actual_result=f"{len(violations)} violations",
            status=status,
            failure_reason=failure_reason,
        )
        results.append(result)
        return results

    def _verify_critical_queries(
        self,
        restore_event_id: str,
        restored_connection: sqlite3.Connection,
    ) -> list[VerificationResult]:
        """Verify critical business queries execute successfully."""
        results: list[VerificationResult] = []

        critical_queries = [
            ("Available Appointments Count", "SELECT COUNT(*) FROM appointments WHERE status = 'available'"),
            ("Patient Count", "SELECT COUNT(*) FROM patient_profiles WHERE email IS NOT NULL"),
            ("Active Providers", "SELECT COUNT(*) FROM providers WHERE is_active = 1"),
            ("Reservation Queue", "SELECT COUNT(*) FROM appointment_reservations WHERE status = 'active'"),
        ]

        cursor = restored_connection.cursor()
        for query_name, query_sql in critical_queries:
            verification_id = uuid.uuid4().hex

            try:
                cursor.execute(query_sql)
                result_row = cursor.fetchone()
                result_value = result_row[0] if result_row else 0

                result = VerificationResult(
                    verification_id=verification_id,
                    restore_event_id=restore_event_id,
                    verification_type=VerificationType.CRITICAL_QUERY,
                    verification_target_table=query_name,
                    expected_result="executable",
                    actual_result=str(result_value),
                    status=VerificationStatus.PASSED,
                    failure_reason=None,
                )
                results.append(result)
            except Exception as exc:
                result = VerificationResult(
                    verification_id=verification_id,
                    restore_event_id=restore_event_id,
                    verification_type=VerificationType.CRITICAL_QUERY,
                    verification_target_table=query_name,
                    expected_result="executable",
                    actual_result="error",
                    status=VerificationStatus.FAILED,
                    failure_reason=str(exc),
                )
                results.append(result)

        return results

    def _persist_verification_result(self, result: VerificationResult) -> None:
        self.connection.execute(
            """
            INSERT INTO restore_verification(
                verification_id, restore_event_id, verification_type,
                verification_target_table, expected_result, actual_result,
                status, failure_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                result.verification_id,
                result.restore_event_id,
                result.verification_type.value,
                result.verification_target_table,
                result.expected_result,
                result.actual_result,
                result.status.value,
                result.failure_reason,
            ],
        )
        self.connection.commit()

    def record_restore_event(
        self,
        backup_execution_id: str,
        dataset_name: str,
        restore_type: str,
        restore_target_environment: str,
        operator_identity: str,
        rationale: str = "recovery drill",
    ) -> str:
        """Record a restore event and return the event ID."""
        event_id = uuid.uuid4().hex
        initiated_at = utc_now()

        self.connection.execute(
            """
            INSERT INTO restore_events(
                event_id, backup_execution_id, dataset_name, restore_type,
                restore_target_environment, restore_point_timestamp,
                status, initiated_at, operator_identity, rationale
            ) VALUES (?, ?, ?, ?, ?, ?, 'initiated', ?, ?, ?)
            """,
            [
                event_id,
                backup_execution_id,
                dataset_name,
                restore_type,
                restore_target_environment,
                to_iso(initiated_at),
                to_iso(initiated_at),
                operator_identity,
                rationale,
            ],
        )
        self.connection.commit()
        return event_id

    def update_restore_event_status(
        self,
        event_id: str,
        status: str,
        completed_at: datetime | None = None,
        rpo_achieved: int | None = None,
        rto_achieved: int | None = None,
    ) -> None:
        """Update restore event status and metrics."""
        now = completed_at or utc_now()
        duration_ms = None

        if status == "completed":
            started_row = self.connection.execute(
                "SELECT started_at FROM restore_events WHERE event_id = ?",
                [event_id],
            ).fetchone()
            if started_row and started_row["started_at"]:
                start = parse_iso(started_row["started_at"])
                if start:
                    duration_ms = int((now - start).total_seconds() * 1000)

        self.connection.execute(
            """
            UPDATE restore_events
            SET status = ?, completed_at = ?, duration_ms = ?,
                rpo_achieved_minutes = ?, rto_achieved_minutes = ?
            WHERE event_id = ?
            """,
            [status, to_iso(now), duration_ms, rpo_achieved, rto_achieved, event_id],
        )
        self.connection.commit()
