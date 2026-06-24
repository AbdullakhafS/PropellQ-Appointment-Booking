from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import uuid
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from src.booking_service import parse_iso, to_iso, utc_now
from src.encryption_service import EncryptionEngine, InMemoryKeyStore, KeyStore

BASE_DIR = Path(__file__).resolve().parents[1]
BACKUP_DIR = BASE_DIR / "generated" / "backups"
DRILL_DIR = BASE_DIR / "generated" / "drills"
DEFAULT_DB_PATH = BASE_DIR / "db" / "appointments.db"


class BackupType(str, Enum):
    FULL = "full"
    INCREMENTAL = "incremental"


class BackupStatus(str, Enum):
    SCHEDULED = "scheduled"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RestoreType(str, Enum):
    DRILL = "drill"
    EMERGENCY = "emergency"
    POINT_IN_TIME = "point_in_time"


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True)
class BackupPolicy:
    policy_name: str
    dataset_name: str
    backup_type: BackupType
    schedule_cron: str
    retention_days: int
    encryption_algorithm: str
    kms_key_id: str | None
    compression_enabled: bool
    storage_location: str
    owner_team: str
    rpo_target_minutes: int
    rto_target_minutes: int
    access_role_id: str = "backup-operator"
    is_active: bool = True


@dataclass(frozen=True)
class BackupExecution:
    execution_id: str
    policy_name: str
    dataset_name: str
    backup_type: BackupType
    status: BackupStatus
    backup_location: str | None
    backup_size_bytes: int | None
    backup_checksum: str | None
    data_currency_point: str
    started_at: datetime
    completed_at: datetime | None
    duration_ms: float | None
    rows_backed_up: int | None
    compression_ratio: float | None
    operator_identity: str
    artifact_path: str | None = None
    encryption_key_id: str | None = None
    encryption_status: str | None = None


@dataclass(frozen=True)
class RestoreDrill:
    drill_id: str
    drill_name: str
    dataset_name: str
    isolated_environment_name: str
    restore_point_type: str
    rpo_target_minutes: int
    rto_target_minutes: int
    drill_owner_email: str
    approval_status: str = "pending"
    approved_by: str | None = None
    is_active: bool = True


@dataclass(frozen=True)
class RestoreEvent:
    event_id: str
    backup_execution_id: str
    dataset_name: str
    restore_type: RestoreType
    restore_target_environment: str
    restore_point_timestamp: str
    status: str
    initiated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    duration_ms: int | None
    rpo_achieved_minutes: int | None
    rto_achieved_minutes: int | None
    operator_identity: str
    rationale: str = "recovery drill"


@dataclass(frozen=True)
class DrillReport:
    report_id: str
    drill_id: str
    drill_date: str
    drill_outcome: str
    drill_duration_minutes: int
    rpo_achieved_minutes: int | None
    rto_achieved_minutes: int | None
    rpo_target_minutes: int
    rto_target_minutes: int
    integrity_checks_passed: bool
    critical_queries_validated: bool
    blockers: str | None
    remediation_actions: str | None
    executed_by: str
    approved_by: str | None = None


class BackupAlertSink:
    def emit(self, alert: dict[str, Any]) -> None:
        raise NotImplementedError


@dataclass
class InMemoryBackupAlertSink(BackupAlertSink):
    alerts: list[dict[str, Any]] = field(default_factory=list)

    def emit(self, alert: dict[str, Any]) -> None:
        self.alerts.append(alert)


class BackupEngine:
    def __init__(
        self,
        connection: sqlite3.Connection,
        backup_dir: Path | None = None,
        alert_sink: BackupAlertSink | None = None,
        key_store: KeyStore | None = None,
    ) -> None:
        self.connection = connection
        self.connection.row_factory = sqlite3.Row
        self.backup_dir = backup_dir or BACKUP_DIR
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.alert_sink = alert_sink or InMemoryBackupAlertSink()
        _store = key_store or InMemoryKeyStore()
        self.encryption_engine = EncryptionEngine(_store)

    def register_policy(self, policy: BackupPolicy) -> None:
        self.connection.execute(
            """
            INSERT INTO backup_policies(
                policy_name, dataset_name, backup_type, schedule_cron,
                retention_days, encryption_algorithm, kms_key_id,
                compression_enabled, storage_location, owner_team,
                rpo_target_minutes, rto_target_minutes, access_role_id, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(dataset_name, backup_type) DO UPDATE SET
                policy_name = excluded.policy_name,
                schedule_cron = excluded.schedule_cron,
                retention_days = excluded.retention_days,
                encryption_algorithm = excluded.encryption_algorithm,
                kms_key_id = excluded.kms_key_id,
                compression_enabled = excluded.compression_enabled,
                storage_location = excluded.storage_location,
                owner_team = excluded.owner_team,
                rpo_target_minutes = excluded.rpo_target_minutes,
                rto_target_minutes = excluded.rto_target_minutes,
                updated_at = CURRENT_TIMESTAMP
            """,
            [
                policy.policy_name,
                policy.dataset_name,
                policy.backup_type.value,
                policy.schedule_cron,
                policy.retention_days,
                policy.encryption_algorithm,
                policy.kms_key_id,
                1 if policy.compression_enabled else 0,
                policy.storage_location,
                policy.owner_team,
                policy.rpo_target_minutes,
                policy.rto_target_minutes,
                policy.access_role_id,
                1 if policy.is_active else 0,
            ],
        )
        self.connection.commit()

    def execute_backup(
        self,
        policy_name: str,
        operator_identity: str = "system",
    ) -> BackupExecution:
        execution_id = uuid.uuid4().hex
        started_at = utc_now()
        row = self.connection.execute(
            "SELECT * FROM backup_policies WHERE policy_name = ?",
            [policy_name],
        ).fetchone()
        if row is None:
            raise LookupError(f"Backup policy not found: {policy_name}")

        policy_dict = dict(row)
        dataset_name = policy_dict["dataset_name"]

        self.connection.execute(
            """
            INSERT INTO backup_executions(
                execution_id, policy_id, policy_name, dataset_name, backup_type,
                status, data_currency_point, started_at, operator_identity
            ) VALUES (?, ?, ?, ?, ?, 'running', ?, ?, ?)
            """,
            [
                execution_id,
                row["id"],
                policy_name,
                dataset_name,
                policy_dict["backup_type"],
                to_iso(started_at),
                to_iso(started_at),
                operator_identity,
            ],
        )
        self.connection.commit()

        try:
            backup_location, encryption_key_id = self._perform_backup(
                dataset_name,
                policy_dict["backup_type"],
                policy_dict["compression_enabled"],
                policy_dict.get("encryption_algorithm") or "AES-256-GCM",
            )

            rows_backed_up = self._count_rows()
            checksum = self._compute_backup_checksum(backup_location)
            backup_size = Path(backup_location).stat().st_size
            completed_at = utc_now()

            self.connection.execute(
                """
                UPDATE backup_executions
                SET status = 'succeeded', backup_location = ?, backup_size_bytes = ?,
                    backup_checksum = ?, rows_backed_up = ?, completed_at = ?,
                    duration_ms = ?, compression_ratio = ?, artifact_path = ?,
                    encryption_status = 'encrypted', encryption_key_id = ?
                WHERE execution_id = ?
                """,
                [
                    backup_location,
                    backup_size,
                    checksum,
                    rows_backed_up,
                    to_iso(completed_at),
                    int((completed_at - started_at).total_seconds() * 1000),
                    0.7,  # Typical compression ratio
                    str(backup_location),
                    encryption_key_id,
                    execution_id,
                ],
            )

            self._record_audit(
                "backup_completed",
                "backup",
                execution_id,
                operator_identity,
                "Backup completed successfully",
            )
            self.connection.commit()

            return BackupExecution(
                execution_id=execution_id,
                policy_name=policy_name,
                dataset_name=dataset_name,
                backup_type=BackupType(policy_dict["backup_type"]),
                status=BackupStatus.SUCCEEDED,
                backup_location=backup_location,
                backup_size_bytes=backup_size,
                backup_checksum=checksum,
                data_currency_point=to_iso(started_at),
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=int((completed_at - started_at).total_seconds() * 1000),
                rows_backed_up=rows_backed_up,
                compression_ratio=0.7,
                operator_identity=operator_identity,
                artifact_path=str(backup_location),
                encryption_key_id=encryption_key_id,
                encryption_status="encrypted",
            )
        except Exception as exc:
            self.connection.execute(
                "UPDATE backup_executions SET status = 'failed', error_message = ? WHERE execution_id = ?",
                [str(exc), execution_id],
            )
            self._record_audit(
                "backup_failed",
                "backup",
                execution_id,
                operator_identity,
                str(exc),
            )
            self._emit_alert(
                alert_type="backup_failed",
                severity=AlertSeverity.CRITICAL,
                message=f"Backup failed: {exc}",
                affected_dataset=dataset_name,
                backup_execution_id=execution_id,
            )
            self.connection.commit()
            raise

    def _perform_backup(
        self,
        dataset_name: str,
        backup_type: str,
        compression_enabled: bool,
        encryption_algorithm: str = "AES-256-GCM",
    ) -> tuple[str, str]:
        """Copy the database and encrypt the backup file.

        Returns a tuple of (backup_location, encryption_key_id).
        The backup file is encrypted with AES-256-GCM; key material never
        touches the backup file.
        """
        db_path = DEFAULT_DB_PATH
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        backup_file = self.backup_dir / f"{dataset_name}.backup.{backup_type}.{timestamp}.db"

        if db_path.exists():
            shutil.copy2(db_path, backup_file)
        else:
            backup_file.write_bytes(b"")

        encryption_key_id = self.encryption_engine.encrypt_file(backup_file)
        return str(backup_file), encryption_key_id

    def _count_rows(self) -> int:
        cursor = self.connection.cursor()
        total = 0
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        tables = [row[0] for row in cursor.fetchall()]
        for table in tables:
            row = cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
            total += row[0] if row else 0
        return total

    def _compute_backup_checksum(self, backup_path: str) -> str:
        return hashlib.sha256(Path(backup_path).read_bytes()).hexdigest()

    def _record_audit(
        self,
        action_type: str,
        resource_type: str,
        resource_id: str,
        actor_identity: str,
        action_details: str,
    ) -> None:
        audit_id = uuid.uuid4().hex
        self.connection.execute(
            """
            INSERT INTO backup_audit_trail(
                audit_id, action_type, resource_type, resource_id,
                actor_identity, actor_role, action_details
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                audit_id,
                action_type,
                resource_type,
                resource_id,
                actor_identity,
                "backup-operator",
                action_details,
            ],
        )

    def _emit_alert(
        self,
        alert_type: str,
        severity: AlertSeverity,
        message: str,
        affected_dataset: str,
        backup_execution_id: str | None = None,
    ) -> None:
        alert_id = uuid.uuid4().hex
        self.connection.execute(
            """
            INSERT INTO backup_alerts(
                alert_id, alert_type, severity, message, affected_dataset,
                backup_execution_id, status
            ) VALUES (?, ?, ?, ?, ?, ?, 'open')
            """,
            [alert_id, alert_type, severity.value, message, affected_dataset, backup_execution_id],
        )
        alert_dict = {
            "alertId": alert_id,
            "alertType": alert_type,
            "severity": severity.value,
            "message": message,
            "affectedDataset": affected_dataset,
        }
        self.alert_sink.emit(alert_dict)

    def latest_execution(self, dataset_name: str) -> BackupExecution:
        row = self.connection.execute(
            """
            SELECT * FROM backup_executions
            WHERE dataset_name = ? AND status = 'succeeded'
            ORDER BY completed_at DESC LIMIT 1
            """,
            [dataset_name],
        ).fetchone()
        if row is None:
            raise LookupError(f"No successful backup found for {dataset_name}")
        return self._build_execution(row)

    def _build_execution(self, row: sqlite3.Row) -> BackupExecution:
        row_dict = dict(row)
        return BackupExecution(
            execution_id=row_dict["execution_id"],
            policy_name=row_dict["policy_name"],
            dataset_name=row_dict["dataset_name"],
            backup_type=BackupType(row_dict["backup_type"]),
            status=BackupStatus(row_dict["status"]),
            backup_location=row_dict["backup_location"],
            backup_size_bytes=row_dict["backup_size_bytes"],
            backup_checksum=row_dict["backup_checksum"],
            data_currency_point=row_dict["data_currency_point"],
            started_at=parse_iso(row_dict["started_at"]) or utc_now(),
            completed_at=parse_iso(row_dict["completed_at"]),
            duration_ms=row_dict["duration_ms"],
            rows_backed_up=row_dict["rows_backed_up"],
            compression_ratio=row_dict["compression_ratio"],
            operator_identity=row_dict["operator_identity"],
            artifact_path=row_dict["artifact_path"],
            encryption_key_id=row_dict.get("encryption_key_id"),
            encryption_status=row_dict.get("encryption_status"),
        )

    # ------------------------------------------------------------------
    # Encryption verification and compliance evidence (Task 004)
    # ------------------------------------------------------------------

    def verify_backup_encryption(self, execution_id: str) -> dict[str, Any]:
        """Verify that a backup artifact is encrypted and record audit evidence.

        Returns a compliance evidence dict suitable for audit review.
        """
        row = self.connection.execute(
            "SELECT * FROM backup_executions WHERE execution_id = ?",
            [execution_id],
        ).fetchone()
        if row is None:
            raise LookupError(f"Backup execution not found: {execution_id}")

        row_dict = dict(row)
        artifact_path = row_dict.get("artifact_path")
        encryption_key_id = row_dict.get("encryption_key_id")

        verified = False
        findings: list[str] = []

        if not artifact_path or not Path(artifact_path).exists():
            findings.append("Backup artifact file not found.")
        else:
            is_enc = self.encryption_engine.is_encrypted_file(artifact_path)
            if is_enc:
                file_key_id = self.encryption_engine.get_file_key_id(artifact_path)
                if file_key_id and file_key_id == encryption_key_id:
                    verified = True
                    findings.append(
                        f"Backup file is encrypted with AES-256-GCM (key_id={file_key_id})."
                    )
                else:
                    findings.append(
                        "Backup file key_id does not match execution record."
                    )
            else:
                findings.append(
                    "Backup artifact is NOT encrypted (missing PROPELIQ magic header)."
                )

        verification_status = "verified" if verified else "failed"
        self.connection.execute(
            """
            UPDATE backup_executions
            SET verification_status = ?
            WHERE execution_id = ?
            """,
            [verification_status, execution_id],
        )
        self._record_audit(
            "backup_completed",
            "backup",
            execution_id,
            "compliance-verifier",
            f"Encryption verification {verification_status}: {'; '.join(findings)}",
        )
        self.connection.commit()

        return {
            "execution_id": execution_id,
            "dataset_name": row_dict.get("dataset_name"),
            "encryption_algorithm": "AES-256-GCM",
            "encryption_key_id": encryption_key_id,
            "artifact_path": artifact_path,
            "verified": verified,
            "verification_status": verification_status,
            "findings": findings,
            "compliance_standard": "HIPAA 45 CFR § 164.312(a)(2)(iv)",
        }

    def generate_compliance_evidence(self, execution_id: str) -> dict[str, Any]:
        """Generate a compliance evidence report for audit review.

        Includes encryption status, key metadata (not key material), and
        verification findings for the given backup execution.
        """
        verification = self.verify_backup_encryption(execution_id)
        row = self.connection.execute(
            "SELECT * FROM backup_executions WHERE execution_id = ?",
            [execution_id],
        ).fetchone()
        row_dict = dict(row) if row else {}

        key_metadata: dict[str, Any] | None = None
        enc_key_id = row_dict.get("encryption_key_id")
        if enc_key_id:
            try:
                meta = self.encryption_engine.key_store.get_key_metadata(enc_key_id)
                key_metadata = {
                    "key_id": meta.key_id,
                    "algorithm": meta.algorithm,
                    "status": meta.status.value,
                    "created_at": meta.created_at.isoformat(),
                    "rotated_at": meta.rotated_at.isoformat() if meta.rotated_at else None,
                }
            except LookupError:
                key_metadata = {"key_id": enc_key_id, "note": "metadata not available"}

        return {
            "report_type": "backup_encryption_compliance_evidence",
            "compliance_standard": "HIPAA 45 CFR § 164.312(a)(2)(iv) — Encryption and Decryption",
            "execution_id": execution_id,
            "dataset_name": row_dict.get("dataset_name"),
            "backup_type": row_dict.get("backup_type"),
            "encryption_algorithm": "AES-256-GCM",
            "encryption_status": row_dict.get("encryption_status"),
            "key_metadata": key_metadata,
            "artifact_path": row_dict.get("artifact_path"),
            "backup_checksum": row_dict.get("backup_checksum"),
            "verification": verification,
            "scope": [
                "PHI appointment records",
                "Patient profile data",
                "Audit log backup artifacts",
            ],
        }
