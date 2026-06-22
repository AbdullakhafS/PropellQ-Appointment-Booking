from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Iterable


BASE_DIR = Path(__file__).resolve().parents[1]
DB_DIR = BASE_DIR / "db"
DEFAULT_DB_PATH = DB_DIR / "appointments.db"
SCHEMA_V1_PATH = DB_DIR / "schema_v1_production.sql"
MIGRATION_MANIFEST_PATH = DB_DIR / "migration_manifest.json"


class MigrationStatus(str, Enum):
    PENDING = "pending"
    APPLIED = "applied"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class MigrationSafetyError(RuntimeError):
    pass


class MigrationVerificationError(RuntimeError):
    pass


@dataclass(frozen=True)
class MigrationDefinition:
    version: str
    name: str
    sql_file: str
    rollback_sql_file: str | None
    rollback_strategy: str
    requires_approval: bool
    destructive_patterns_allowed: bool
    verification_tables: list[str]
    smoke_queries: list[str]


@dataclass
class MigrationRecord:
    version: str
    name: str
    environment: str
    status: MigrationStatus
    started_at: str
    finished_at: str | None = None
    duration_ms: float | None = None
    checksum: str | None = None
    approver: str | None = None
    rationale: str | None = None
    artifact_path: str | None = None
    rollback_path: str | None = None
    verification_result: dict[str, Any] | None = None
    error_message: str | None = None


@dataclass
class MigrationExecutionContext:
    environment: str
    approver: str | None = None
    rationale: str | None = None
    dry_run: bool = False


class MigrationPipeline:
    """Versioned migration pipeline with rollback, verification, and audit logging."""

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.manifest = self._load_manifest()
        self.log_dir = self.db_path.parent / "migration_logs"
        self.audit_path = self.db_path.parent / "migration_audit.jsonl"
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _load_manifest(self) -> list[MigrationDefinition]:
        manifest_data = json.loads(MIGRATION_MANIFEST_PATH.read_text(encoding="utf-8"))
        migrations: list[MigrationDefinition] = []
        for item in manifest_data.get("migrations", []):
            item.setdefault("rollback_sql_file", None)
            migrations.append(MigrationDefinition(**item))
        return migrations

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON;")
        return connection

    def lint_migration(self, migration: MigrationDefinition) -> list[str]:
        sql = (DB_DIR / migration.sql_file).read_text(encoding="utf-8")
        issues: list[str] = []
        upper_sql = sql.upper()

        forbidden_patterns = ["DROP TABLE", "DROP COLUMN", "ALTER TABLE .* DROP", "PRAGMA writable_schema"]
        if not migration.destructive_patterns_allowed:
            for pattern in forbidden_patterns:
                if pattern in upper_sql:
                    issues.append(f"Forbidden destructive pattern detected: {pattern}")

        if "IF NOT EXISTS" not in upper_sql:
            issues.append("Idempotency guard missing: use IF NOT EXISTS for schema objects")

        if "CHECK (" not in upper_sql:
            issues.append("Safety check expectations not documented in migration SQL")

        return issues

    def check_expand_contract_guardrails(self, migration: MigrationDefinition) -> list[str]:
        sql = (DB_DIR / migration.sql_file).read_text(encoding="utf-8").upper()
        issues: list[str] = []

        if "DROP COLUMN" in sql or "DROP TABLE" in sql:
            issues.append("Breaking change detected: drop operation requires expand-and-contract sequencing")

        if "ALTER TABLE" in sql and "ADD COLUMN" not in sql and "RENAME" not in sql:
            issues.append("ALTER TABLE used without additive change or explicit migration window")

        return issues

    def _schema_checksum(self, migration: MigrationDefinition) -> str:
        sql_file = DB_DIR / migration.sql_file
        digest = hashlib.sha256(sql_file.read_bytes()).hexdigest()
        return digest

    def _current_schema_version(self, connection: sqlite3.Connection) -> str:
        row = connection.execute("PRAGMA user_version;").fetchone()
        return str(row[0] if row else 0)

    def _apply_sql(self, connection: sqlite3.Connection, migration: MigrationDefinition) -> None:
        sql = (DB_DIR / migration.sql_file).read_text(encoding="utf-8")
        connection.executescript(sql)

    def _build_backup_path(self, migration: MigrationDefinition) -> Path:
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return DB_DIR / f"{self.db_path.stem}.backup.{migration.version}.{timestamp}.db"

    def _backup_database(self, backup_path: Path) -> None:
        if self.db_path.exists():
            shutil.copy2(self.db_path, backup_path)

    def _log_audit(self, record: MigrationRecord) -> None:
        with self.audit_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(record), sort_keys=True))
            handle.write("\n")

    def _write_artifact(self, record: MigrationRecord) -> Path:
        artifact_path = self.log_dir / f"migration_{record.version}_{record.environment}.json"
        artifact_path.write_text(json.dumps(asdict(record), indent=2, sort_keys=True), encoding="utf-8")
        return artifact_path

    def _run_verification(self, connection: sqlite3.Connection, migration: MigrationDefinition) -> dict[str, Any]:
        table_results: dict[str, bool] = {}
        for table_name in migration.verification_tables:
            row = connection.execute(
                "SELECT COUNT(*) AS count FROM sqlite_master WHERE type='table' AND name = ?",
                (table_name,),
            ).fetchone()
            table_results[table_name] = bool(row and row["count"])

        smoke_results: list[dict[str, Any]] = []
        for query in migration.smoke_queries:
            row = connection.execute(query).fetchone()
            smoke_results.append({"query": query, "rows": dict(row) if row and isinstance(row, sqlite3.Row) else None})

        version_row = connection.execute("PRAGMA user_version;").fetchone()
        checksum = self._schema_checksum(migration)

        return {
            "version": str(version_row[0] if version_row else 0),
            "checksum": checksum,
            "tables": table_results,
            "smoke_queries": smoke_results,
        }

    def migrate(self, context: MigrationExecutionContext) -> list[MigrationRecord]:
        records: list[MigrationRecord] = []
        with self._connect() as connection:
            for migration in self.manifest:
                record = MigrationRecord(
                    version=migration.version,
                    name=migration.name,
                    environment=context.environment,
                    status=MigrationStatus.PENDING,
                    started_at=datetime.utcnow().isoformat(),
                    approver=context.approver,
                    rationale=context.rationale,
                    checksum=self._schema_checksum(migration),
                )

                lint_issues = self.lint_migration(migration)
                guardrail_issues = self.check_expand_contract_guardrails(migration)
                if lint_issues or guardrail_issues:
                    record.status = MigrationStatus.FAILED
                    record.error_message = "; ".join(lint_issues + guardrail_issues)
                    record.finished_at = datetime.utcnow().isoformat()
                    self._write_artifact(record)
                    self._log_audit(record)
                    raise MigrationSafetyError(record.error_message)

                if migration.requires_approval and not context.approver:
                    record.status = MigrationStatus.FAILED
                    record.error_message = "Production migration requires approver identity"
                    record.finished_at = datetime.utcnow().isoformat()
                    self._write_artifact(record)
                    self._log_audit(record)
                    raise MigrationSafetyError(record.error_message)

                backup_path = self._build_backup_path(migration)
                self._backup_database(backup_path)
                record.rollback_path = str(backup_path)

                try:
                    if not context.dry_run:
                        self._apply_sql(connection, migration)
                        connection.execute(f"PRAGMA user_version = {migration.version.split('.')[0]};")
                        connection.commit()
                        record.verification_result = self._run_verification(connection, migration)

                    record.status = MigrationStatus.APPLIED
                    record.finished_at = datetime.utcnow().isoformat()
                    record.duration_ms = self._duration_ms(record.started_at, record.finished_at)
                    record.artifact_path = str(self._write_artifact(record))
                    self._log_audit(record)
                    records.append(record)
                except Exception as exc:  # noqa: BLE001
                    connection.rollback()
                    record.status = MigrationStatus.FAILED
                    record.error_message = str(exc)
                    record.finished_at = datetime.utcnow().isoformat()
                    record.duration_ms = self._duration_ms(record.started_at, record.finished_at)
                    record.artifact_path = str(self._write_artifact(record))
                    self._log_audit(record)
                    raise

        return records

    def rollback_last(self, context: MigrationExecutionContext, backup_path: Path) -> MigrationRecord:
        if not backup_path.exists():
            raise FileNotFoundError(f"Rollback backup not found: {backup_path}")

        started_at = datetime.utcnow().isoformat()
        shutil.copy2(backup_path, self.db_path)
        record = MigrationRecord(
            version="rollback",
            name="emergency_restore",
            environment=context.environment,
            status=MigrationStatus.ROLLED_BACK,
            started_at=started_at,
            finished_at=datetime.utcnow().isoformat(),
            approver=context.approver,
            rationale=context.rationale,
            rollback_path=str(backup_path),
        )
        record.duration_ms = self._duration_ms(record.started_at, record.finished_at)
        record.artifact_path = str(self._write_artifact(record))
        self._log_audit(record)
        return record

    def verify_post_deploy(self, migration_version: str) -> dict[str, Any]:
        with self._connect() as connection:
            version_row = connection.execute("PRAGMA user_version;").fetchone()
            smoke_queries = [
                "SELECT COUNT(*) AS count FROM appointments;",
                "SELECT COUNT(*) AS count FROM patient_profiles;",
                "SELECT COUNT(*) AS count FROM calendar_sync_queue;",
            ]
            smoke_results = [dict(connection.execute(query).fetchone()) for query in smoke_queries]
            return {
                "expected_version": migration_version,
                "actual_version": str(version_row[0] if version_row else 0),
                "checksum": hashlib.sha256(SCHEMA_V1_PATH.read_bytes()).hexdigest(),
                "smoke_results": smoke_results,
                "tables_present": self._verification_tables_present(connection),
            }

    def _verification_tables_present(self, connection: sqlite3.Connection) -> dict[str, bool]:
        tables = [
            "specialties",
            "providers",
            "appointments",
            "patient_profiles",
            "appointment_reservations",
            "calendar_sync_queue",
        ]
        results: dict[str, bool] = {}
        for table_name in tables:
            row = connection.execute(
                "SELECT COUNT(*) AS count FROM sqlite_master WHERE type='table' AND name = ?",
                (table_name,),
            ).fetchone()
            results[table_name] = bool(row and row["count"])
        return results

    def _duration_ms(self, started_at: str, finished_at: str | None) -> float | None:
        if not finished_at:
            return None
        start = datetime.fromisoformat(started_at)
        finish = datetime.fromisoformat(finished_at)
        return round((finish - start).total_seconds() * 1000, 3)


def build_default_pipeline(db_path: Path | None = None) -> MigrationPipeline:
    return MigrationPipeline(db_path=db_path)


def load_migration_manifest() -> list[dict[str, Any]]:
    return json.loads(MIGRATION_MANIFEST_PATH.read_text(encoding="utf-8")).get("migrations", [])