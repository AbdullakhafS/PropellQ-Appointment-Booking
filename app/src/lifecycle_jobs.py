from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Protocol
from zoneinfo import ZoneInfo
import sqlite3

from src.booking_service import parse_iso, to_iso, utc_now

BASE_DIR = Path(__file__).resolve().parents[1]
GENERATED_DIR = BASE_DIR / "generated" / "lifecycle"


class LifecycleAction(str, Enum):
    ARCHIVE = "archive"
    PURGE = "purge"


class LifecycleStatus(str, Enum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    PARTIAL = "partial"


class LifecycleEventType(str, Enum):
    ARCHIVE = "archive"
    PURGE = "purge"
    HOLD_SKIP = "hold_skip"
    IMMUTABILITY_BLOCK = "immutability_block"
    RETRIEVAL = "retrieval"
    RETRY = "retry"
    DEAD_LETTER = "dead_letter"
    ALERT = "alert"


class LifecycleAlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True)
class LifecyclePolicyVersion:
    policy_name: str
    dataset_name: str
    action_type: LifecycleAction
    retention_days: int
    archive_after_days: int
    immutable_retention_days: int
    timezone_name: str
    owner_email: str
    version_label: str
    effective_from: datetime
    approval_status: str = "approved"
    approved_by: str | None = None

    def is_approved(self) -> bool:
        return self.approval_status == "approved"


@dataclass(frozen=True)
class LifecycleSubject:
    dataset_name: str
    record_key: str
    payload: dict[str, Any]
    created_at: datetime
    archive_after_at: datetime
    purge_after_at: datetime
    immutable_until: datetime
    policy_version: str
    record_type: str = "record"
    legal_hold: bool = False
    hold_reason: str | None = None
    hold_expires_at: datetime | None = None
    created_by: str = "system"


@dataclass(frozen=True)
class LifecycleEvent:
    event_type: LifecycleEventType
    dataset_name: str
    record_key: str | None
    status: str
    reason: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LifecycleRunReport:
    run_id: str
    job_name: str
    dataset_name: str | None
    policy_version: str | None
    dry_run: bool
    status: LifecycleStatus
    started_at: datetime
    completed_at: datetime | None
    operator_identity: str
    archive_count: int
    purge_count: int
    skipped_count: int
    blocked_count: int
    retried_count: int
    dead_letter_count: int
    policy_versions: list[str] = field(default_factory=list)
    events: list[LifecycleEvent] = field(default_factory=list)
    alerts: list[dict[str, Any]] = field(default_factory=list)
    evidence_path: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "runId": self.run_id,
            "jobName": self.job_name,
            "datasetName": self.dataset_name,
            "policyVersion": self.policy_version,
            "dryRun": self.dry_run,
            "status": self.status.value,
            "startedAt": to_iso(self.started_at),
            "completedAt": to_iso(self.completed_at) if self.completed_at else None,
            "operatorIdentity": self.operator_identity,
            "counts": {
                "archived": self.archive_count,
                "purged": self.purge_count,
                "skipped": self.skipped_count,
                "blocked": self.blocked_count,
                "retried": self.retried_count,
                "deadLetter": self.dead_letter_count,
            },
            "policyVersions": self.policy_versions,
            "events": [
                {
                    "eventType": event.event_type.value,
                    "datasetName": event.dataset_name,
                    "recordKey": event.record_key,
                    "status": event.status,
                    "reason": event.reason,
                    "details": event.details,
                }
                for event in self.events
            ],
            "alerts": self.alerts,
            "evidencePath": str(self.evidence_path) if self.evidence_path else None,
        }


class LifecycleAlertSink(Protocol):
    def emit(self, alert: dict[str, Any]) -> None:
        ...


@dataclass
class InMemoryAlertSink:
    alerts: list[dict[str, Any]] = field(default_factory=list)

    def emit(self, alert: dict[str, Any]) -> None:
        self.alerts.append(alert)


class LifecycleJobEngine:
    def __init__(
        self,
        connection: sqlite3.Connection,
        report_dir: Path | None = None,
        alert_sink: LifecycleAlertSink | None = None,
        max_attempts: int = 3,
        base_backoff_seconds: int = 2,
    ) -> None:
        self.connection = connection
        self.connection.row_factory = sqlite3.Row
        self.report_dir = report_dir or GENERATED_DIR
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self.alert_sink = alert_sink or InMemoryAlertSink()
        self.max_attempts = max_attempts
        self.base_backoff_seconds = base_backoff_seconds

    def register_policy(self, policy: LifecyclePolicyVersion) -> None:
        self.connection.execute(
            """
            INSERT INTO lifecycle_policy_versions(
                policy_name,
                dataset_name,
                action_type,
                retention_days,
                archive_after_days,
                immutable_retention_days,
                timezone_name,
                owner_email,
                approval_status,
                approved_by,
                effective_from,
                version_label
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(policy_name, version_label) DO UPDATE SET
                dataset_name = excluded.dataset_name,
                action_type = excluded.action_type,
                retention_days = excluded.retention_days,
                archive_after_days = excluded.archive_after_days,
                immutable_retention_days = excluded.immutable_retention_days,
                timezone_name = excluded.timezone_name,
                owner_email = excluded.owner_email,
                approval_status = excluded.approval_status,
                approved_by = excluded.approved_by,
                effective_from = excluded.effective_from,
                updated_at = CURRENT_TIMESTAMP
            """,
            [
                policy.policy_name,
                policy.dataset_name,
                policy.action_type.value,
                policy.retention_days,
                policy.archive_after_days,
                policy.immutable_retention_days,
                policy.timezone_name,
                policy.owner_email,
                policy.approval_status,
                policy.approved_by,
                to_iso(policy.effective_from),
                policy.version_label,
            ],
        )
        self.connection.commit()

    def register_subject(self, subject: LifecycleSubject) -> None:
        self.connection.execute(
            """
            INSERT INTO lifecycle_subjects(
                dataset_name,
                record_key,
                record_type,
                payload_json,
                created_at,
                archive_after_at,
                purge_after_at,
                immutable_until,
                archive_status,
                legal_hold,
                hold_reason,
                hold_expires_at,
                policy_version,
                created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?, ?, ?)
            ON CONFLICT(dataset_name, record_key) DO UPDATE SET
                record_type = excluded.record_type,
                payload_json = excluded.payload_json,
                created_at = excluded.created_at,
                archive_after_at = excluded.archive_after_at,
                purge_after_at = excluded.purge_after_at,
                immutable_until = excluded.immutable_until,
                legal_hold = excluded.legal_hold,
                hold_reason = excluded.hold_reason,
                hold_expires_at = excluded.hold_expires_at,
                policy_version = excluded.policy_version,
                created_by = excluded.created_by,
                updated_at = CURRENT_TIMESTAMP
            """,
            [
                subject.dataset_name,
                subject.record_key,
                subject.record_type,
                json.dumps(subject.payload, sort_keys=True),
                to_iso(subject.created_at),
                to_iso(subject.archive_after_at),
                to_iso(subject.purge_after_at),
                to_iso(subject.immutable_until),
                1 if subject.legal_hold else 0,
                subject.hold_reason,
                to_iso(subject.hold_expires_at) if subject.hold_expires_at else None,
                subject.policy_version,
                subject.created_by,
            ],
        )
        self.connection.commit()

    def run_archive(
        self,
        dataset_name: str | None = None,
        reference_time: datetime | None = None,
        dry_run: bool = False,
        operator_identity: str = "system",
    ) -> LifecycleRunReport:
        return self._run_job("archive", self._archive_work, dataset_name, reference_time, dry_run, operator_identity)

    def run_purge(
        self,
        dataset_name: str | None = None,
        reference_time: datetime | None = None,
        dry_run: bool = False,
        operator_identity: str = "system",
    ) -> LifecycleRunReport:
        return self._run_job("purge", self._purge_work, dataset_name, reference_time, dry_run, operator_identity)

    def retrieve_archived_record(
        self,
        dataset_name: str,
        record_key: str,
        requester_role: str,
        requester_identity: str = "system",
    ) -> dict[str, Any]:
        row = self.connection.execute(
            """
            SELECT *
            FROM lifecycle_archive_entries
            WHERE dataset_name = ? AND record_key = ?
            """,
            [dataset_name, record_key],
        ).fetchone()
        if row is None:
            raise LookupError(f"Archived record not found for {dataset_name}:{record_key}")

        allowed_roles = json.loads(row["retrieval_allowed_roles"])
        if requester_role not in allowed_roles:
            raise PermissionError(f"Role {requester_role} is not authorized to retrieve archived records")

        now_value = to_iso(utc_now())
        self.connection.execute(
            """
            UPDATE lifecycle_archive_entries
            SET retrieved_at = ?, retrieval_count = retrieval_count + 1
            WHERE dataset_name = ? AND record_key = ?
            """,
            [now_value, dataset_name, record_key],
        )
        self._record_event(
            run_id=f"retrieval-{uuid.uuid4().hex}",
            event_type=LifecycleEventType.RETRIEVAL,
            dataset_name=dataset_name,
            record_key=record_key,
            status="success",
            reason="Authorized archive retrieval",
            details={"requesterRole": requester_role, "requesterIdentity": requester_identity},
        )
        self.connection.commit()
        return json.loads(row["payload_json"])

    def latest_report(self, run_id: str) -> LifecycleRunReport:
        run_row = self.connection.execute(
            "SELECT * FROM lifecycle_execution_runs WHERE run_id = ?",
            [run_id],
        ).fetchone()
        if run_row is None:
            raise LookupError(f"Run not found: {run_id}")
        events = self._load_events(run_id)
        alerts = self._load_alerts(run_id)
        return self._build_report(run_row, events, alerts)

    def execute_with_retry(
        self,
        job_name: str,
        work: Callable[[str], tuple[int, int, int, int, int, int, list[LifecycleEvent]]],
        dataset_name: str | None,
        reference_time: datetime | None,
        dry_run: bool,
        operator_identity: str,
    ) -> LifecycleRunReport:
        return self._run_job(job_name, work, dataset_name, reference_time, dry_run, operator_identity)

    def _run_job(
        self,
        job_name: str,
        work: Callable[[str], tuple[int, int, int, int, int, int, list[LifecycleEvent]]],
        dataset_name: str | None,
        reference_time: datetime | None,
        dry_run: bool,
        operator_identity: str,
    ) -> LifecycleRunReport:
        run_id = uuid.uuid4().hex
        started_at = reference_time or utc_now()
        self._begin_run(run_id, job_name, dataset_name, dry_run, operator_identity, started_at)

        attempts = 0
        last_error: Exception | None = None
        while attempts < self.max_attempts:
            try:
                result = work(run_id)
                report = self._finalize_success(run_id, job_name, dataset_name, dry_run, operator_identity, started_at, result)
                self.connection.commit()
                return report
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                attempts += 1
                retry_delay = self.base_backoff_seconds * (2 ** (attempts - 1))
                self._record_run_event(
                    run_id=run_id,
                    event_type=LifecycleEventType.RETRY,
                    dataset_name=dataset_name or "all",
                    record_key=None,
                    status="retried",
                    reason=str(exc),
                    details={"attempt": attempts, "retryDelaySeconds": retry_delay},
                )
                self._insert_alert(
                    run_id=run_id,
                    severity=LifecycleAlertSeverity.WARNING if attempts < self.max_attempts else LifecycleAlertSeverity.CRITICAL,
                    alert_type="job_failure",
                    message=f"{job_name} failed on attempt {attempts}: {exc}",
                    backoff_seconds=retry_delay,
                    incident_target="on-call-lifecycle",
                    runbook_link=str(BASE_DIR / "db" / "lifecycle_runbook.md"),
                )
                if attempts >= self.max_attempts:
                    break

        self._record_run_failure(run_id, job_name, dataset_name, operator_identity, started_at, last_error)
        self.connection.commit()
        raise RuntimeError(f"{job_name} failed after {attempts} attempts") from last_error

    def _archive_work(
        self,
        run_id: str,
        dataset_name: str | None,
        reference_time: datetime | None,
        dry_run: bool,
    ) -> tuple[int, int, int, int, int, int, list[LifecycleEvent]]:
        now_value = reference_time or utc_now()
        events: list[LifecycleEvent] = []
        archived = skipped = blocked = retried = dead_letter = purged = 0
        for subject in self._due_subjects(
            action=LifecycleAction.ARCHIVE,
            dataset_name=dataset_name,
            reference_time=now_value,
        ):
            if subject["archive_status"] == "archived":
                skipped += 1
                events.append(
                    self._build_event(
                        LifecycleEventType.ARCHIVE,
                        subject,
                        "skipped",
                        "Record already archived",
                        {"dryRun": dry_run},
                    )
                )
                continue

            payload = json.loads(subject["payload_json"])
            archive_location = f"archive://{subject['dataset_name']}/{subject['record_key']}"
            archive_checksum = hashlib.sha256(subject["payload_json"].encode("utf-8")).hexdigest()

            if dry_run:
                skipped += 1
                events.append(
                    self._build_event(
                        LifecycleEventType.ARCHIVE,
                        subject,
                        "skipped",
                        "Dry run preview",
                        {"archiveLocation": archive_location, "checksum": archive_checksum, "payload": payload},
                    )
                )
                continue

            self.connection.execute(
                """
                INSERT INTO lifecycle_archive_entries(
                    dataset_name,
                    record_key,
                    policy_version,
                    payload_json,
                    archived_at,
                    retention_expires_at,
                    archive_checksum,
                    retrieval_allowed_roles
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(dataset_name, record_key) DO UPDATE SET
                    policy_version = excluded.policy_version,
                    payload_json = excluded.payload_json,
                    archived_at = excluded.archived_at,
                    retention_expires_at = excluded.retention_expires_at,
                    archive_checksum = excluded.archive_checksum,
                    retrieval_allowed_roles = excluded.retrieval_allowed_roles,
                    created_at = CURRENT_TIMESTAMP
                """,
                [
                    subject["dataset_name"],
                    subject["record_key"],
                    subject["policy_version"],
                    subject["payload_json"],
                    to_iso(now_value),
                    subject["purge_after_at"],
                    archive_checksum,
                    json.dumps(["compliance", "auditor", "records-management"]),
                ],
            )
            self.connection.execute(
                """
                UPDATE lifecycle_subjects
                SET archive_status = 'archived', archived_at = ?, archive_location = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                [to_iso(now_value), archive_location, subject["id"]],
            )
            archived += 1
            events.append(
                self._build_event(
                    LifecycleEventType.ARCHIVE,
                    subject,
                    "success",
                    "Archived for retention management",
                    {"archiveLocation": archive_location, "checksum": archive_checksum},
                )
            )

        return archived, 0, skipped, blocked, retried, dead_letter, events

    def _purge_work(
        self,
        run_id: str,
        dataset_name: str | None,
        reference_time: datetime | None,
        dry_run: bool,
    ) -> tuple[int, int, int, int, int, int, list[LifecycleEvent]]:
        now_value = reference_time or utc_now()
        events: list[LifecycleEvent] = []
        archived = skipped = blocked = retried = dead_letter = purged = 0
        for subject in self._due_subjects(
            action=LifecycleAction.PURGE,
            dataset_name=dataset_name,
            reference_time=now_value,
        ):
            if subject["legal_hold"]:
                skipped += 1
                events.append(
                    self._build_event(
                        LifecycleEventType.HOLD_SKIP,
                        subject,
                        "skipped",
                        subject["hold_reason"] or "Record is under legal hold",
                        {"holdReason": subject["hold_reason"]},
                    )
                )
                continue

            if parse_iso(subject["immutable_until"]) and parse_iso(subject["immutable_until"]) > now_value:
                blocked += 1
                events.append(
                    self._build_event(
                        LifecycleEventType.IMMUTABILITY_BLOCK,
                        subject,
                        "blocked",
                        "Immutable retention window has not expired",
                        {"immutableUntil": subject["immutable_until"]},
                    )
                )
                continue

            if dry_run:
                skipped += 1
                events.append(
                    self._build_event(
                        LifecycleEventType.PURGE,
                        subject,
                        "skipped",
                        "Dry run preview",
                        {"policyVersion": subject["policy_version"]},
                    )
                )
                continue

            tombstone = json.dumps(
                {
                    "datasetName": subject["dataset_name"],
                    "recordKey": subject["record_key"],
                    "purged": True,
                },
                sort_keys=True,
            )
            self.connection.execute(
                """
                UPDATE lifecycle_subjects
                SET archive_status = 'purged',
                    payload_json = ?,
                    purged_at = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                [tombstone, to_iso(now_value), subject["id"]],
            )
            purged += 1
            events.append(
                self._build_event(
                    LifecycleEventType.PURGE,
                    subject,
                    "success",
                    "Purged from operational storage",
                    {"policyVersion": subject["policy_version"]},
                )
            )

        return archived, purged, skipped, blocked, retried, dead_letter, events

    def _due_subjects(
        self,
        action: LifecycleAction,
        dataset_name: str | None,
        reference_time: datetime,
    ) -> list[sqlite3.Row]:
        rows = self.connection.execute(
            """
            SELECT *
            FROM lifecycle_subjects
            WHERE (? IS NULL OR dataset_name = ?)
              AND archive_status IN ('active', 'archived')
              AND (
                    (? = 'archive' AND archive_after_at <= ?)
                 OR (? = 'purge' AND purge_after_at <= ?)
              )
            ORDER BY dataset_name, record_key
            """,
            [dataset_name, dataset_name, action.value, to_iso(reference_time), action.value, to_iso(reference_time)],
        ).fetchall()
        return rows

    def _build_event(
        self,
        event_type: LifecycleEventType,
        subject_row: sqlite3.Row,
        status: str,
        reason: str,
        details: dict[str, Any] | None = None,
    ) -> LifecycleEvent:
        return LifecycleEvent(
            event_type=event_type,
            dataset_name=subject_row["dataset_name"],
            record_key=subject_row["record_key"],
            status=status,
            reason=reason,
            details=details or {},
        )

    def _begin_run(
        self,
        run_id: str,
        job_name: str,
        dataset_name: str | None,
        dry_run: bool,
        operator_identity: str,
        started_at: datetime,
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO lifecycle_execution_runs(
                run_id,
                job_name,
                dataset_name,
                dry_run,
                status,
                started_at,
                operator_identity,
                retries,
                backoff_seconds,
                details_json
            ) VALUES (?, ?, ?, ?, 'running', ?, ?, 0, 0, ?)
            """,
            [run_id, job_name, dataset_name, 1 if dry_run else 0, to_iso(started_at), operator_identity, json.dumps({"policyVersion": None})],
        )

    def _finalize_success(
        self,
        run_id: str,
        job_name: str,
        dataset_name: str | None,
        dry_run: bool,
        operator_identity: str,
        started_at: datetime,
        result: tuple[int, int, int, int, int, int, list[LifecycleEvent]],
    ) -> LifecycleRunReport:
        archive_count, purge_count, skipped_count, blocked_count, retried_count, dead_letter_count, events = result
        completed_at = utc_now()
        status = LifecycleStatus.SUCCEEDED if blocked_count == 0 else LifecycleStatus.PARTIAL
        self.connection.execute(
            """
            UPDATE lifecycle_execution_runs
            SET status = ?, completed_at = ?, details_json = ?
            WHERE run_id = ?
            """,
            [
                status.value,
                to_iso(completed_at),
                json.dumps(
                    {
                        "archiveCount": archive_count,
                        "purgeCount": purge_count,
                        "skippedCount": skipped_count,
                        "blockedCount": blocked_count,
                        "policyVersions": self._run_policy_versions(dataset_name),
                    }
                ),
                run_id,
            ],
        )
        for event in events:
            self._record_run_event(
                run_id=run_id,
                event_type=event.event_type,
                dataset_name=event.dataset_name,
                record_key=event.record_key,
                status=event.status,
                reason=event.reason,
                details=event.details,
            )
        alerts = self._load_alerts(run_id)
        report = LifecycleRunReport(
            run_id=run_id,
            job_name=job_name,
            dataset_name=dataset_name,
            policy_version=None,
            dry_run=dry_run,
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            operator_identity=operator_identity,
            archive_count=archive_count,
            purge_count=purge_count,
            skipped_count=skipped_count,
            blocked_count=blocked_count,
            retried_count=retried_count,
            dead_letter_count=dead_letter_count,
            policy_versions=self._run_policy_versions(dataset_name),
            events=events,
            alerts=alerts,
        )
        self._persist_report(report)
        return report

    def _record_run_failure(
        self,
        run_id: str,
        job_name: str,
        dataset_name: str | None,
        operator_identity: str,
        started_at: datetime,
        error: Exception | None,
    ) -> None:
        completed_at = utc_now()
        self.connection.execute(
            """
            UPDATE lifecycle_execution_runs
            SET status = 'failed', completed_at = ?, details_json = ?
            WHERE run_id = ?
            """,
            [to_iso(completed_at), json.dumps({"error": str(error) if error else "unknown"}), run_id],
        )
        self._record_run_event(
            run_id=run_id,
            event_type=LifecycleEventType.DEAD_LETTER,
            dataset_name=dataset_name or "all",
            record_key=None,
            status="failed",
            reason=str(error) if error else "Unknown failure",
            details={"jobName": job_name, "operatorIdentity": operator_identity},
        )

    def _record_event(
        self,
        run_id: str,
        event_type: LifecycleEventType,
        dataset_name: str,
        record_key: str | None,
        status: str,
        reason: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self._record_run_event(run_id, event_type, dataset_name, record_key, status, reason, details)

    def _record_run_event(
        self,
        run_id: str,
        event_type: LifecycleEventType,
        dataset_name: str,
        record_key: str | None,
        status: str,
        reason: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO lifecycle_execution_events(
                run_id,
                event_type,
                dataset_name,
                record_key,
                status,
                reason,
                details_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [run_id, event_type.value, dataset_name, record_key, status, reason, json.dumps(details or {})],
        )

    def _insert_alert(
        self,
        run_id: str,
        severity: LifecycleAlertSeverity,
        alert_type: str,
        message: str,
        backoff_seconds: int,
        incident_target: str | None,
        runbook_link: str | None,
    ) -> None:
        alert = {
            "runId": run_id,
            "severity": severity.value,
            "alertType": alert_type,
            "message": message,
            "backoffSeconds": backoff_seconds,
            "incidentTarget": incident_target,
            "runbookLink": runbook_link,
        }
        self.connection.execute(
            """
            INSERT INTO lifecycle_alerts(
                run_id,
                severity,
                alert_type,
                message,
                backoff_seconds,
                incident_target,
                runbook_link
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [run_id, severity.value, alert_type, message, backoff_seconds, incident_target, runbook_link],
        )
        self._record_run_event(
            run_id=run_id,
            event_type=LifecycleEventType.ALERT,
            dataset_name="all",
            record_key=None,
            status="failed",
            reason=message,
            details=alert,
        )
        self.alert_sink.emit(alert)

    def _load_events(self, run_id: str) -> list[LifecycleEvent]:
        rows = self.connection.execute(
            "SELECT * FROM lifecycle_execution_events WHERE run_id = ? ORDER BY id",
            [run_id],
        ).fetchall()
        events: list[LifecycleEvent] = []
        for row in rows:
            events.append(
                LifecycleEvent(
                    event_type=LifecycleEventType(row["event_type"]),
                    dataset_name=row["dataset_name"],
                    record_key=row["record_key"],
                    status=row["status"],
                    reason=row["reason"],
                    details=json.loads(row["details_json"] or "{}"),
                )
            )
        return events

    def _load_alerts(self, run_id: str) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT * FROM lifecycle_alerts WHERE run_id = ? ORDER BY id",
            [run_id],
        ).fetchall()
        return [
            {
                "runId": row["run_id"],
                "severity": row["severity"],
                "alertType": row["alert_type"],
                "message": row["message"],
                "backoffSeconds": row["backoff_seconds"],
                "incidentTarget": row["incident_target"],
                "runbookLink": row["runbook_link"],
            }
            for row in rows
        ]

    def _build_report(
        self,
        run_row: sqlite3.Row,
        events: list[LifecycleEvent],
        alerts: list[dict[str, Any]],
    ) -> LifecycleRunReport:
        details = json.loads(run_row["details_json"] or "{}")
        return LifecycleRunReport(
            run_id=run_row["run_id"],
            job_name=run_row["job_name"],
            dataset_name=run_row["dataset_name"],
            policy_version=run_row["policy_version"],
            dry_run=bool(run_row["dry_run"]),
            status=LifecycleStatus(run_row["status"]),
            started_at=parse_iso(run_row["started_at"]) or utc_now(),
            completed_at=parse_iso(run_row["completed_at"]),
            operator_identity=run_row["operator_identity"],
            archive_count=details.get("archiveCount", 0),
            purge_count=details.get("purgeCount", 0),
            skipped_count=details.get("skippedCount", 0),
            blocked_count=details.get("blockedCount", 0),
            retried_count=run_row["retries"],
            dead_letter_count=0,
            policy_versions=details.get("policyVersions", []),
            events=events,
            alerts=alerts,
        )

    def _persist_report(self, report: LifecycleRunReport) -> None:
        report_path = self.report_dir / f"{report.run_id}.json"
        report = replace(report, evidence_path=report_path)
        report_path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
        self.connection.execute(
            "UPDATE lifecycle_execution_runs SET details_json = ? WHERE run_id = ?",
            [
                json.dumps(
                    {
                        "archiveCount": report.archive_count,
                        "purgeCount": report.purge_count,
                        "skippedCount": report.skipped_count,
                        "blockedCount": report.blocked_count,
                        "policyVersions": report.policy_versions,
                        "evidencePath": str(report_path),
                    }
                ),
                report.run_id,
            ],
        )

    def _run_policy_versions(self, dataset_name: str | None) -> list[str]:
        rows = self.connection.execute(
            """
            SELECT DISTINCT policy_version
            FROM lifecycle_subjects
            WHERE (? IS NULL OR dataset_name = ?)
            ORDER BY policy_version
            """,
            [dataset_name, dataset_name],
        ).fetchall()
        return [row["policy_version"] for row in rows]


def create_subject(
    dataset_name: str,
    record_key: str,
    payload: dict[str, Any],
    created_at: datetime,
    policy: LifecyclePolicyVersion,
) -> LifecycleSubject:
    local_zone = ZoneInfo(policy.timezone_name)
    created_local = created_at.astimezone(local_zone)
    archive_after_at = datetime.combine(
        created_local.date() + timedelta(days=policy.archive_after_days),
        datetime.min.time(),
        tzinfo=local_zone,
    ).astimezone(timezone.utc)
    purge_after_at = datetime.combine(
        created_local.date() + timedelta(days=policy.retention_days),
        datetime.min.time(),
        tzinfo=local_zone,
    ).astimezone(timezone.utc)
    immutable_until = datetime.combine(
        created_local.date() + timedelta(days=policy.immutable_retention_days),
        datetime.min.time(),
        tzinfo=local_zone,
    ).astimezone(timezone.utc)
    return LifecycleSubject(
        dataset_name=dataset_name,
        record_key=record_key,
        payload=payload,
        created_at=created_at,
        archive_after_at=archive_after_at,
        purge_after_at=purge_after_at,
        immutable_until=immutable_until,
        policy_version=policy.version_label,
    )