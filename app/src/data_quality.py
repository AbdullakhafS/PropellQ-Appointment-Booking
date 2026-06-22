from __future__ import annotations

import argparse
import json
import re
import sqlite3
import statistics
import uuid
from collections import defaultdict
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from difflib import SequenceMatcher
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Iterable

from src.booking_service import parse_iso, to_iso, utc_now

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_DIR = BASE_DIR / "generated" / "data_quality"
DEFAULT_RUNBOOK_LINK = BASE_DIR / "db" / "data_quality_runbook.md"

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PHONE_PATTERN = re.compile(r"^\+?[0-9][0-9\-\s]{7,}$")
ISO_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ISO_TIME_PATTERN = re.compile(r"^\d{2}:\d{2}(:\d{2})?$")


class QualitySeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class EnforcementMode(str, Enum):
    OBSERVE = "observe"
    WARN = "warn"
    BLOCK = "block"


class RuleType(str, Enum):
    COMPLETENESS = "completeness"
    VALIDITY = "validity"
    DUPLICATE = "duplicate"
    CONSISTENCY = "consistency"
    REFERENTIAL = "referential"


@dataclass(frozen=True)
class QualityRule:
    rule_code: str
    domain_name: str
    rule_name: str
    rule_type: RuleType
    severity: QualitySeverity
    owner_team: str
    rationale: str
    version_label: str
    enforcement_mode: EnforcementMode = EnforcementMode.OBSERVE
    runbook_link: str = str(DEFAULT_RUNBOOK_LINK)
    is_active: bool = True


@dataclass(frozen=True)
class QualityViolation:
    rule_code: str
    domain_name: str
    record_key: str | None
    severity: QualitySeverity
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    owner_team: str = ""
    confidence: float = 1.0
    suggested_action: str = "triage"
    publish_blocking: bool = False


@dataclass(frozen=True)
class QualityRunSummary:
    run_id: str
    scope_name: str
    stage_name: str
    enforcement_mode: EnforcementMode
    status: str
    started_at: datetime
    completed_at: datetime | None
    evaluated_records: int
    violation_count: int
    warning_count: int
    critical_count: int
    blocked_count: int
    owner_team: str
    trend_date: str
    report_path: Path | None = None
    violations: list[QualityViolation] = field(default_factory=list)
    trend_metrics: dict[str, Any] = field(default_factory=dict)
    publish_blocked: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "runId": self.run_id,
            "scopeName": self.scope_name,
            "stageName": self.stage_name,
            "enforcementMode": self.enforcement_mode.value,
            "status": self.status,
            "startedAt": to_iso(self.started_at),
            "completedAt": to_iso(self.completed_at) if self.completed_at else None,
            "evaluatedRecords": self.evaluated_records,
            "violationCount": self.violation_count,
            "warningCount": self.warning_count,
            "criticalCount": self.critical_count,
            "blockedCount": self.blocked_count,
            "ownerTeam": self.owner_team,
            "trendDate": self.trend_date,
            "publishBlocked": self.publish_blocked,
            "reportPath": str(self.report_path) if self.report_path else None,
            "violations": [
                {
                    "ruleCode": violation.rule_code,
                    "domainName": violation.domain_name,
                    "recordKey": violation.record_key,
                    "severity": violation.severity.value,
                    "message": violation.message,
                    "details": violation.details,
                    "ownerTeam": violation.owner_team,
                    "confidence": violation.confidence,
                    "suggestedAction": violation.suggested_action,
                    "publishBlocking": violation.publish_blocking,
                }
                for violation in self.violations
            ],
            "trendMetrics": self.trend_metrics,
        }


@dataclass(frozen=True)
class PublishDecision:
    blocked: bool
    blocked_count: int
    quarantine_count: int
    report: QualityRunSummary


class QualityAlertSink:
    def emit(self, alert: dict[str, Any]) -> None:
        raise NotImplementedError


@dataclass
class InMemoryQualityAlertSink(QualityAlertSink):
    alerts: list[dict[str, Any]] = field(default_factory=list)

    def emit(self, alert: dict[str, Any]) -> None:
        self.alerts.append(alert)


class DataQualityEngine:
    def __init__(
        self,
        connection: sqlite3.Connection,
        report_dir: Path | None = None,
        alert_sink: QualityAlertSink | None = None,
    ) -> None:
        self.connection = connection
        self.connection.row_factory = sqlite3.Row
        self.report_dir = report_dir or DEFAULT_REPORT_DIR
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self.alert_sink = alert_sink or InMemoryQualityAlertSink()
        self.domain_owners = {
            "appointments": "clinical-operations",
            "patient_profiles": "patient-services",
            "appointment_reservations": "booking-engine",
            "booking_events": "booking-platform",
            "confirmation_deliveries": "booking-platform",
            "reminder_log": "booking-platform",
            "medications": "clinical-coding",
            "allergies": "clinical-coding",
            "coding": "coding-integrity",
        }
        self.default_rules = self._build_default_rules()
        self._seed_rule_catalog()

    def _build_default_rules(self) -> list[QualityRule]:
        rules = [
            QualityRule("DQ-APP-001", "appointments", "appointments_required_fields", RuleType.COMPLETENESS, QualitySeverity.CRITICAL, "clinical-operations", "Appointments require provider, specialty, date, time, location, and status.", "1.0"),
            QualityRule("DQ-APP-002", "appointments", "appointments_valid_values", RuleType.VALIDITY, QualitySeverity.CRITICAL, "clinical-operations", "Appointment date/time/status values must be valid.", "1.0"),
            QualityRule("DQ-APP-003", "appointments", "appointments_duplicate_slots", RuleType.DUPLICATE, QualitySeverity.WARNING, "clinical-operations", "Duplicate active appointment slots should be rare and reviewed.", "1.0"),
            QualityRule("DQ-PAT-001", "patient_profiles", "patient_required_fields", RuleType.COMPLETENESS, QualitySeverity.CRITICAL, "patient-services", "Patients require identity and contact fields.", "1.0"),
            QualityRule("DQ-PAT-002", "patient_profiles", "patient_contact_validity", RuleType.VALIDITY, QualitySeverity.CRITICAL, "patient-services", "Patient email and phone must be valid.", "1.0"),
            QualityRule("DQ-PAT-003", "patient_profiles", "patient_duplicates", RuleType.DUPLICATE, QualitySeverity.CRITICAL, "patient-services", "Duplicate patient identities must be flagged.", "1.0"),
            QualityRule("DQ-RES-001", "appointment_reservations", "reservation_required_fields", RuleType.COMPLETENESS, QualitySeverity.CRITICAL, "booking-engine", "Reservations require appointment, patient, token, status, and expiry.", "1.0"),
            QualityRule("DQ-RES-002", "appointment_reservations", "reservation_consistency", RuleType.CONSISTENCY, QualitySeverity.CRITICAL, "booking-engine", "Reservations must reference valid appointments and patients.", "1.0"),
            QualityRule("DQ-EVT-001", "booking_events", "booking_event_required_fields", RuleType.COMPLETENESS, QualitySeverity.WARNING, "booking-platform", "Booking events require appointment and correlation id.", "1.0"),
            QualityRule("DQ-DEL-001", "confirmation_deliveries", "delivery_consistency", RuleType.CONSISTENCY, QualitySeverity.WARNING, "booking-platform", "Confirmation deliveries must reference valid appointments.", "1.0"),
            QualityRule("DQ-REM-001", "reminder_log", "reminder_required_fields", RuleType.COMPLETENESS, QualitySeverity.WARNING, "booking-platform", "Reminder log requires appointment, patient, channel, and status.", "1.0"),
            QualityRule("DQ-MED-001", "medications", "medication_required_fields", RuleType.COMPLETENESS, QualitySeverity.CRITICAL, "clinical-coding", "Medication records require name, dosage, route, and status.", "1.0"),
            QualityRule("DQ-ALG-001", "allergies", "allergy_required_fields", RuleType.COMPLETENESS, QualitySeverity.CRITICAL, "clinical-coding", "Allergy records require allergen, severity, and recorded date.", "1.0"),
            QualityRule("DQ-COD-001", "coding", "coding_required_fields", RuleType.COMPLETENESS, QualitySeverity.CRITICAL, "coding-integrity", "Clinical coding records require code system, code, and description.", "1.0"),
        ]
        return rules

    def _seed_rule_catalog(self) -> None:
        existing = self.connection.execute("SELECT COUNT(*) AS count FROM data_quality_rules").fetchone()["count"]
        if existing:
            return
        for rule in self.default_rules:
            self.register_rule(rule)

    def register_rule(self, rule: QualityRule) -> None:
        self.connection.execute(
            """
            INSERT INTO data_quality_rules(
                rule_code,
                domain_name,
                rule_name,
                rule_type,
                severity,
                enforcement_mode,
                owner_team,
                rationale,
                version_label,
                runbook_link,
                is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(rule_code) DO UPDATE SET
                domain_name = excluded.domain_name,
                rule_name = excluded.rule_name,
                rule_type = excluded.rule_type,
                severity = excluded.severity,
                enforcement_mode = excluded.enforcement_mode,
                owner_team = excluded.owner_team,
                rationale = excluded.rationale,
                version_label = excluded.version_label,
                runbook_link = excluded.runbook_link,
                is_active = excluded.is_active,
                updated_at = CURRENT_TIMESTAMP
            """,
            [
                rule.rule_code,
                rule.domain_name,
                rule.rule_name,
                rule.rule_type.value,
                rule.severity.value,
                rule.enforcement_mode.value,
                rule.owner_team,
                rule.rationale,
                rule.version_label,
                rule.runbook_link,
                1 if rule.is_active else 0,
            ],
        )
        self.connection.commit()

    def validate_table_domain(
        self,
        domain_name: str,
        stage_name: str = "scheduled",
        enforcement_mode: EnforcementMode = EnforcementMode.OBSERVE,
        reference_time: datetime | None = None,
    ) -> QualityRunSummary:
        rows = self._load_domain_rows(domain_name)
        return self._run_validation(domain_name, rows, stage_name, enforcement_mode, reference_time)

    def validate_records(
        self,
        domain_name: str,
        records: Iterable[dict[str, Any]],
        stage_name: str = "publish",
        enforcement_mode: EnforcementMode = EnforcementMode.WARN,
        reference_time: datetime | None = None,
    ) -> QualityRunSummary:
        row_list = [dict(record) for record in records]
        return self._run_validation(domain_name, row_list, stage_name, enforcement_mode, reference_time)

    def validate_publish_batch(
        self,
        records_by_domain: dict[str, list[dict[str, Any]]],
        enforcement_mode: EnforcementMode = EnforcementMode.BLOCK,
        reference_time: datetime | None = None,
    ) -> PublishDecision:
        all_violations: list[QualityViolation] = []
        total_evaluated = 0
        blocked_count = 0
        quarantine_count = 0
        latest_report: QualityRunSummary | None = None

        for domain_name, records in records_by_domain.items():
            report = self.validate_records(domain_name, records, stage_name="publish", enforcement_mode=enforcement_mode, reference_time=reference_time)
            latest_report = report
            total_evaluated += report.evaluated_records
            blocked_count += report.blocked_count
            quarantine_count += self._quarantine_violations(report.run_id, report.violations)
            all_violations.extend(report.violations)

        blocked = blocked_count > 0 and enforcement_mode == EnforcementMode.BLOCK
        if latest_report is None:
            latest_report = self._empty_report("publish", enforcement_mode, reference_time)
        return PublishDecision(blocked=blocked, blocked_count=blocked_count, quarantine_count=quarantine_count, report=latest_report)

    def trend_report(self, days: int = 7) -> dict[str, Any]:
        rows = self.connection.execute(
            """
            SELECT trend_date, status, violation_count, warning_count, critical_count, blocked_count
            FROM data_quality_runs
            WHERE trend_date >= date('now', ?)
            ORDER BY trend_date
            """,
            [f"-{days} days"],
        ).fetchall()
        daily = defaultdict(lambda: {"runs": 0, "violations": 0, "warnings": 0, "criticals": 0, "blocked": 0})
        for row in rows:
            bucket = daily[row["trend_date"]]
            bucket["runs"] += 1
            bucket["violations"] += row["violation_count"]
            bucket["warnings"] += row["warning_count"]
            bucket["criticals"] += row["critical_count"]
            bucket["blocked"] += row["blocked_count"]

        resolved_rows = self.connection.execute(
            """
            SELECT detected_at, resolved_at
            FROM data_quality_violations
            WHERE resolved_at IS NOT NULL
              AND detected_at >= datetime('now', ?)
            """,
            [f"-{days} days"],
        ).fetchall()
        mttr_values: list[float] = []
        for row in resolved_rows:
            detected = parse_iso(row["detected_at"])
            resolved = parse_iso(row["resolved_at"])
            if detected and resolved:
                mttr_values.append((resolved - detected).total_seconds() / 60.0)

        return {
            "days": days,
            "daily": {day: metrics for day, metrics in sorted(daily.items())},
            "mttrMinutes": round(statistics.mean(mttr_values), 2) if mttr_values else None,
            "totalRuns": len(rows),
            "resolvedViolations": len(mttr_values),
        }

    def export_report(self, run_id: str) -> QualityRunSummary:
        summary = self._load_summary(run_id)
        summary = replace(summary, trend_metrics=self.trend_report())
        report_path = self.report_dir / f"quality_{run_id}.json"
        report_path.write_text(json.dumps(summary.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
        self.connection.execute(
            "UPDATE data_quality_runs SET report_path = ?, status = ? WHERE run_id = ?",
            [str(report_path), summary.status, run_id],
        )
        self.connection.commit()
        return replace(summary, report_path=report_path)

    def resolve_violation(self, violation_id: int, notes: str = "triaged") -> None:
        self.connection.execute(
            """
            UPDATE data_quality_violations
            SET status = 'resolved', resolved_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            [violation_id],
        )
        self.connection.execute(
            """
            UPDATE data_quality_quarantine
            SET quarantine_status = 'cleared', triaged_at = CURRENT_TIMESTAMP, triage_notes = ?
            WHERE id = ?
            """,
            [notes, violation_id],
        )
        self.connection.commit()

    def _load_domain_rows(self, domain_name: str) -> list[dict[str, Any]]:
        table_map = {
            "appointments": "appointments",
            "patient_profiles": "patient_profiles",
            "appointment_reservations": "appointment_reservations",
            "booking_events": "booking_events",
            "confirmation_deliveries": "confirmation_deliveries",
            "reminder_log": "reminder_log",
        }
        table_name = table_map.get(domain_name)
        if not table_name:
            return []
        rows = self.connection.execute(f"SELECT * FROM {table_name}").fetchall()
        return [dict(row) for row in rows]

    def _run_validation(
        self,
        domain_name: str,
        records: list[dict[str, Any]],
        stage_name: str,
        enforcement_mode: EnforcementMode,
        reference_time: datetime | None,
    ) -> QualityRunSummary:
        run_id = uuid.uuid4().hex
        started_at = reference_time or utc_now()
        trend_date = (reference_time or utc_now()).date().isoformat()
        owner_team = self.domain_owners.get(domain_name, "data-platform")
        self.connection.execute(
            """
            INSERT INTO data_quality_runs(
                run_id,
                scope_name,
                stage_name,
                enforcement_mode,
                status,
                started_at,
                trend_date,
                owner_team
            ) VALUES (?, ?, ?, ?, 'running', ?, ?, ?)
            """,
            [run_id, domain_name, stage_name, enforcement_mode.value, to_iso(started_at), trend_date, owner_team],
        )

        violations: list[QualityViolation] = []
        evaluated_records = 0
        for record in records:
            evaluated_records += 1
            violations.extend(self._validate_record(domain_name, record))

        duplicates = self._validate_duplicates(domain_name, records)
        violations.extend(duplicates)
        violations.extend(self._validate_consistency(domain_name, records))

        warning_count = sum(1 for violation in violations if violation.severity == QualitySeverity.WARNING)
        critical_count = sum(1 for violation in violations if violation.severity == QualitySeverity.CRITICAL)
        blocked_count = sum(1 for violation in violations if violation.publish_blocking)
        status = "completed"
        if blocked_count and enforcement_mode == EnforcementMode.BLOCK:
            status = "blocked"
        elif not records:
            status = "completed"

        completed_at = utc_now()
        self.connection.execute(
            """
            UPDATE data_quality_runs
            SET status = ?, completed_at = ?, evaluated_records = ?, violation_count = ?, warning_count = ?, critical_count = ?, blocked_count = ?
            WHERE run_id = ?
            """,
            [status, to_iso(completed_at), evaluated_records, len(violations), warning_count, critical_count, blocked_count, run_id],
        )

        for violation in violations:
            self._persist_violation(run_id, violation)
            self._route_alert(run_id, violation, stage_name, blocked=violation.publish_blocking and enforcement_mode == EnforcementMode.BLOCK)

        summary = QualityRunSummary(
            run_id=run_id,
            scope_name=domain_name,
            stage_name=stage_name,
            enforcement_mode=enforcement_mode,
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            evaluated_records=evaluated_records,
            violation_count=len(violations),
            warning_count=warning_count,
            critical_count=critical_count,
            blocked_count=blocked_count,
            owner_team=owner_team,
            trend_date=trend_date,
            violations=violations,
            trend_metrics={},
            publish_blocked=blocked_count > 0 and enforcement_mode == EnforcementMode.BLOCK,
        )
        report_path = self.report_dir / f"quality_{run_id}.json"
        summary = replace(summary, report_path=report_path)
        summary = replace(summary, trend_metrics=self.trend_report())
        report_path.write_text(json.dumps(summary.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
        self.connection.execute(
            "UPDATE data_quality_runs SET report_path = ?, status = ? WHERE run_id = ?",
            [str(report_path), summary.status, run_id],
        )
        self.connection.commit()
        return summary

    def _persist_violation(self, run_id: str, violation: QualityViolation) -> None:
        self.connection.execute(
            """
            INSERT INTO data_quality_violations(
                run_id,
                rule_code,
                domain_name,
                record_key,
                severity,
                message,
                details_json,
                owner_team,
                status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                run_id,
                violation.rule_code,
                violation.domain_name,
                violation.record_key,
                violation.severity.value,
                violation.message,
                json.dumps(violation.details, sort_keys=True),
                violation.owner_team,
                "open",
            ],
        )

    def _route_alert(self, run_id: str, violation: QualityViolation, stage_name: str, blocked: bool) -> None:
        alert = {
            "runId": run_id,
            "stage": stage_name,
            "ruleCode": violation.rule_code,
            "domain": violation.domain_name,
            "severity": violation.severity.value,
            "ownerTeam": violation.owner_team,
            "runbookLink": str(DEFAULT_RUNBOOK_LINK),
            "message": violation.message,
            "triageSlaMinutes": self._triage_sla_minutes(violation.severity),
            "blocked": blocked,
            "confidence": violation.confidence,
        }
        self.alert_sink.emit(alert)

    def _triage_sla_minutes(self, severity: QualitySeverity) -> int:
        return {QualitySeverity.INFO: 240, QualitySeverity.WARNING: 60, QualitySeverity.CRITICAL: 15}[severity]

    def _validate_record(self, domain_name: str, record: dict[str, Any]) -> list[QualityViolation]:
        validators: dict[str, Callable[[dict[str, Any]], list[QualityViolation]]] = {
            "appointments": self._validate_appointments,
            "patient_profiles": self._validate_patient_profiles,
            "appointment_reservations": self._validate_reservations,
            "booking_events": self._validate_booking_events,
            "confirmation_deliveries": self._validate_confirmation_deliveries,
            "reminder_log": self._validate_reminder_log,
            "medications": self._validate_medications,
            "allergies": self._validate_allergies,
            "coding": self._validate_coding,
        }
        return validators.get(domain_name, lambda _record: [])(record)

    def _validate_appointments(self, record: dict[str, Any]) -> list[QualityViolation]:
        violations: list[QualityViolation] = []
        required = ["provider_id", "specialty_id", "appointment_date", "start_time", "end_time", "location", "status", "duration_minutes", "appointment_timezone"]
        violations.extend(self._check_required("appointments", "DQ-APP-001", record, required, QualitySeverity.CRITICAL))
        violations.extend(self._check_choice("appointments", "DQ-APP-002", record, "status", {"available", "booked", "cancelled"}, QualitySeverity.CRITICAL))
        violations.extend(self._check_positive_int("appointments", "DQ-APP-002", record, "duration_minutes", QualitySeverity.CRITICAL))
        violations.extend(self._check_date("appointments", "DQ-APP-002", record, "appointment_date", QualitySeverity.CRITICAL))
        violations.extend(self._check_time("appointments", "DQ-APP-002", record, "start_time", QualitySeverity.CRITICAL))
        violations.extend(self._check_time("appointments", "DQ-APP-002", record, "end_time", QualitySeverity.CRITICAL))
        return violations

    def _validate_patient_profiles(self, record: dict[str, Any]) -> list[QualityViolation]:
        violations: list[QualityViolation] = []
        required = ["first_name", "last_name", "email", "phone", "preferred_timezone", "reminder_channels", "do_not_disturb"]
        violations.extend(self._check_required("patient_profiles", "DQ-PAT-001", record, required, QualitySeverity.CRITICAL))
        violations.extend(self._check_email("patient_profiles", "DQ-PAT-002", record, "email", QualitySeverity.CRITICAL))
        violations.extend(self._check_phone("patient_profiles", "DQ-PAT-002", record, "phone", QualitySeverity.CRITICAL))
        violations.extend(self._check_binary_flag("patient_profiles", "DQ-PAT-001", record, "do_not_disturb", QualitySeverity.CRITICAL))
        return violations

    def _validate_reservations(self, record: dict[str, Any]) -> list[QualityViolation]:
        violations: list[QualityViolation] = []
        required = ["appointment_id", "patient_profile_id", "reservation_token", "status", "expires_at"]
        violations.extend(self._check_required("appointment_reservations", "DQ-RES-001", record, required, QualitySeverity.CRITICAL))
        violations.extend(self._check_choice("appointment_reservations", "DQ-RES-001", record, "status", {"active", "expired", "confirmed", "cancelled"}, QualitySeverity.CRITICAL))
        violations.extend(self._check_datetime("appointment_reservations", "DQ-RES-001", record, "expires_at", QualitySeverity.CRITICAL))
        return violations

    def _validate_booking_events(self, record: dict[str, Any]) -> list[QualityViolation]:
        violations: list[QualityViolation] = []
        required = ["appointment_id", "event_type", "correlation_id"]
        violations.extend(self._check_required("booking_events", "DQ-EVT-001", record, required, QualitySeverity.WARNING))
        return violations

    def _validate_confirmation_deliveries(self, record: dict[str, Any]) -> list[QualityViolation]:
        violations: list[QualityViolation] = []
        required = ["appointment_id", "recipient_email", "status"]
        violations.extend(self._check_required("confirmation_deliveries", "DQ-DEL-001", record, required, QualitySeverity.WARNING))
        violations.extend(self._check_choice("confirmation_deliveries", "DQ-DEL-001", record, "status", {"queued", "sent", "failed"}, QualitySeverity.WARNING))
        violations.extend(self._check_email("confirmation_deliveries", "DQ-DEL-001", record, "recipient_email", QualitySeverity.WARNING))
        violations.extend(self._check_non_negative("confirmation_deliveries", "DQ-DEL-001", record, "retry_count", QualitySeverity.WARNING))
        return violations

    def _validate_reminder_log(self, record: dict[str, Any]) -> list[QualityViolation]:
        violations: list[QualityViolation] = []
        required = ["appointment_id", "patient_profile_id", "reminder_type", "channel", "delivery_status"]
        violations.extend(self._check_required("reminder_log", "DQ-REM-001", record, required, QualitySeverity.WARNING))
        violations.extend(self._check_choice("reminder_log", "DQ-REM-001", record, "channel", {"sms", "email"}, QualitySeverity.WARNING))
        violations.extend(self._check_choice("reminder_log", "DQ-REM-001", record, "delivery_status", {"queued", "sent", "failed", "skipped"}, QualitySeverity.WARNING))
        violations.extend(self._check_non_negative("reminder_log", "DQ-REM-001", record, "retry_count", QualitySeverity.WARNING))
        return violations

    def _validate_medications(self, record: dict[str, Any]) -> list[QualityViolation]:
        required = ["medication_name", "dosage", "route", "status"]
        violations = self._check_required("medications", "DQ-MED-001", record, required, QualitySeverity.CRITICAL)
        violations.extend(self._check_positive_float("medications", "DQ-MED-001", record, "dosage", QualitySeverity.CRITICAL))
        return violations

    def _validate_allergies(self, record: dict[str, Any]) -> list[QualityViolation]:
        required = ["allergen", "reaction_severity", "recorded_at"]
        violations = self._check_required("allergies", "DQ-ALG-001", record, required, QualitySeverity.CRITICAL)
        violations.extend(self._check_choice("allergies", "DQ-ALG-001", record, "reaction_severity", {"mild", "moderate", "severe"}, QualitySeverity.CRITICAL))
        violations.extend(self._check_datetime("allergies", "DQ-ALG-001", record, "recorded_at", QualitySeverity.CRITICAL))
        return violations

    def _validate_coding(self, record: dict[str, Any]) -> list[QualityViolation]:
        required = ["code_system", "code", "description", "effective_date"]
        violations = self._check_required("coding", "DQ-COD-001", record, required, QualitySeverity.CRITICAL)
        violations.extend(self._check_date("coding", "DQ-COD-001", record, "effective_date", QualitySeverity.CRITICAL))
        return violations

    def _validate_duplicates(self, domain_name: str, records: list[dict[str, Any]]) -> list[QualityViolation]:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for record in records:
            if domain_name == "appointments":
                key = self._normalize_key((record.get("provider_id"), record.get("appointment_date"), record.get("start_time"), record.get("status")))
            elif domain_name == "patient_profiles":
                key = self._normalize_key((record.get("email"), record.get("phone")))
            elif domain_name == "appointment_reservations":
                key = self._normalize_key((record.get("reservation_token"),))
            elif domain_name == "booking_events":
                key = self._normalize_key((record.get("correlation_id"),))
            elif domain_name == "confirmation_deliveries":
                key = self._normalize_key((record.get("appointment_id"), record.get("recipient_email"), record.get("template_version")))
            elif domain_name == "reminder_log":
                key = self._normalize_key((record.get("appointment_id"), record.get("patient_profile_id"), record.get("reminder_type"), record.get("channel")))
            else:
                key = self._normalize_key((record.get("id"),))
            grouped[key].append(record)

        violations: list[QualityViolation] = []
        for key, grouped_records in grouped.items():
            if len(grouped_records) < 2:
                continue
            confidence = 1.0
            if domain_name == "patient_profiles":
                confidence = self._duplicate_confidence(grouped_records)
            severity = QualitySeverity.CRITICAL if domain_name in {"patient_profiles", "appointment_reservations"} else QualitySeverity.WARNING
            violations.append(
                QualityViolation(
                    rule_code=self._duplicate_rule_code(domain_name),
                    domain_name=domain_name,
                    record_key=str(key),
                    severity=severity,
                    message=f"Duplicate {domain_name} records detected for business key {key}",
                    details={"duplicateCount": len(grouped_records), "businessKey": key},
                    owner_team=self.domain_owners.get(domain_name, "data-platform"),
                    confidence=confidence,
                    suggested_action="quarantine" if severity == QualitySeverity.CRITICAL else "review",
                    publish_blocking=severity == QualitySeverity.CRITICAL,
                )
            )
        return violations

    def _validate_consistency(self, domain_name: str, records: list[dict[str, Any]]) -> list[QualityViolation]:
        if domain_name not in {"appointments", "appointment_reservations", "booking_events", "confirmation_deliveries", "reminder_log"}:
            return []

        providers = {row["id"]: dict(row) for row in self.connection.execute("SELECT id, specialty_id FROM providers").fetchall()}
        specialties = {row["id"]: dict(row) for row in self.connection.execute("SELECT id FROM specialties").fetchall()}
        patients = {row["id"]: dict(row) for row in self.connection.execute("SELECT id, email, phone FROM patient_profiles").fetchall()}
        appointments = {row["id"]: dict(row) for row in self.connection.execute("SELECT id, provider_id, specialty_id, patient_email, patient_phone FROM appointments").fetchall()}
        reservations = {row["id"]: dict(row) for row in self.connection.execute("SELECT id, appointment_id, patient_profile_id FROM appointment_reservations").fetchall()}

        violations: list[QualityViolation] = []
        for record in records:
            record_key = str(record.get("id") or record.get("reservation_token") or record.get("correlation_id") or record.get("appointment_id") or "unknown")
            if domain_name == "appointments":
                provider_id = record.get("provider_id")
                specialty_id = record.get("specialty_id")
                if provider_id is None or provider_id not in providers:
                    violations.append(self._consistency_violation("DQ-APP-003", domain_name, record_key, "Appointment references a missing provider", {"providerId": provider_id}, QualitySeverity.CRITICAL, True))
                elif specialty_id is not None and providers[provider_id]["specialty_id"] != specialty_id:
                    violations.append(self._consistency_violation("DQ-APP-003", domain_name, record_key, "Appointment specialty does not match provider specialty", {"providerId": provider_id, "appointmentSpecialty": specialty_id, "providerSpecialty": providers[provider_id]["specialty_id"]}, QualitySeverity.CRITICAL, True))
                if specialty_id is not None and specialty_id not in specialties:
                    violations.append(self._consistency_violation("DQ-APP-003", domain_name, record_key, "Appointment references a missing specialty", {"specialtyId": specialty_id}, QualitySeverity.CRITICAL, True))
                if record.get("patient_email") and not EMAIL_PATTERN.match(str(record.get("patient_email"))):
                    violations.append(self._consistency_violation("DQ-APP-003", domain_name, record_key, "Patient email snapshot is invalid", {"patientEmail": record.get("patient_email")}, QualitySeverity.WARNING, False))
            elif domain_name == "appointment_reservations":
                appointment_id = record.get("appointment_id")
                patient_profile_id = record.get("patient_profile_id")
                if appointment_id not in appointments:
                    violations.append(self._consistency_violation("DQ-RES-002", domain_name, record_key, "Reservation references a missing appointment", {"appointmentId": appointment_id}, QualitySeverity.CRITICAL, True))
                if patient_profile_id not in patients:
                    violations.append(self._consistency_violation("DQ-RES-002", domain_name, record_key, "Reservation references a missing patient", {"patientProfileId": patient_profile_id}, QualitySeverity.CRITICAL, True))
            elif domain_name == "booking_events":
                appointment_id = record.get("appointment_id")
                reservation_id = record.get("reservation_id")
                if appointment_id not in appointments:
                    violations.append(self._consistency_violation("DQ-EVT-002", domain_name, record_key, "Booking event references a missing appointment", {"appointmentId": appointment_id}, QualitySeverity.WARNING, False))
                if reservation_id and reservation_id not in reservations:
                    violations.append(self._consistency_violation("DQ-EVT-002", domain_name, record_key, "Booking event references a missing reservation", {"reservationId": reservation_id}, QualitySeverity.WARNING, False))
            elif domain_name == "confirmation_deliveries":
                appointment_id = record.get("appointment_id")
                if appointment_id not in appointments:
                    violations.append(self._consistency_violation("DQ-DEL-002", domain_name, record_key, "Confirmation delivery references a missing appointment", {"appointmentId": appointment_id}, QualitySeverity.WARNING, False))
            elif domain_name == "reminder_log":
                appointment_id = record.get("appointment_id")
                patient_profile_id = record.get("patient_profile_id")
                if appointment_id not in appointments:
                    violations.append(self._consistency_violation("DQ-REM-002", domain_name, record_key, "Reminder references a missing appointment", {"appointmentId": appointment_id}, QualitySeverity.WARNING, False))
                if patient_profile_id not in patients:
                    violations.append(self._consistency_violation("DQ-REM-002", domain_name, record_key, "Reminder references a missing patient", {"patientProfileId": patient_profile_id}, QualitySeverity.WARNING, False))
        return violations

    def _consistency_violation(
        self,
        rule_code: str,
        domain_name: str,
        record_key: str,
        message: str,
        details: dict[str, Any],
        severity: QualitySeverity,
        publish_blocking: bool,
    ) -> QualityViolation:
        return QualityViolation(
            rule_code=rule_code,
            domain_name=domain_name,
            record_key=record_key,
            severity=severity,
            message=message,
            details=details,
            owner_team=self.domain_owners.get(domain_name, "data-platform"),
            confidence=1.0,
            suggested_action="quarantine" if publish_blocking else "review",
            publish_blocking=publish_blocking,
        )

    def _empty_report(self, stage_name: str, enforcement_mode: EnforcementMode, reference_time: datetime | None) -> QualityRunSummary:
        now_value = reference_time or utc_now()
        return QualityRunSummary(
            run_id=uuid.uuid4().hex,
            scope_name="none",
            stage_name=stage_name,
            enforcement_mode=enforcement_mode,
            status="completed",
            started_at=now_value,
            completed_at=now_value,
            evaluated_records=0,
            violation_count=0,
            warning_count=0,
            critical_count=0,
            blocked_count=0,
            owner_team="data-platform",
            trend_date=now_value.date().isoformat(),
            trend_metrics=self.trend_report(),
        )

    def _load_summary(self, run_id: str) -> QualityRunSummary:
        row = self.connection.execute("SELECT * FROM data_quality_runs WHERE run_id = ?", [run_id]).fetchone()
        if row is None:
            raise LookupError(f"Quality run not found: {run_id}")
        violations = self.connection.execute("SELECT * FROM data_quality_violations WHERE run_id = ? ORDER BY id", [run_id]).fetchall()
        violation_objects = [
            QualityViolation(
                rule_code=violation_row["rule_code"],
                domain_name=violation_row["domain_name"],
                record_key=violation_row["record_key"],
                severity=QualitySeverity(violation_row["severity"]),
                message=violation_row["message"],
                details=json.loads(violation_row["details_json"] or "{}"),
                owner_team=violation_row["owner_team"],
            )
            for violation_row in violations
        ]
        return QualityRunSummary(
            run_id=row["run_id"],
            scope_name=row["scope_name"],
            stage_name=row["stage_name"],
            enforcement_mode=EnforcementMode(row["enforcement_mode"]),
            status=row["status"],
            started_at=parse_iso(row["started_at"]) or utc_now(),
            completed_at=parse_iso(row["completed_at"]),
            evaluated_records=row["evaluated_records"],
            violation_count=row["violation_count"],
            warning_count=row["warning_count"],
            critical_count=row["critical_count"],
            blocked_count=row["blocked_count"],
            owner_team=row["owner_team"],
            trend_date=row["trend_date"],
            report_path=Path(row["report_path"]) if row["report_path"] else None,
            violations=violation_objects,
            trend_metrics=self.trend_report(),
            publish_blocked=row["status"] == "blocked",
        )

    def _quarantine_violations(self, run_id: str, violations: list[QualityViolation]) -> int:
        count = 0
        for violation in violations:
            if not violation.publish_blocking:
                continue
            self.connection.execute(
                """
                INSERT INTO data_quality_quarantine(
                    run_id,
                    domain_name,
                    record_key,
                    severity,
                    quarantine_status,
                    reason,
                    payload_json,
                    owner_team
                ) VALUES (?, ?, ?, ?, 'blocked', ?, ?, ?)
                """,
                [
                    run_id,
                    violation.domain_name,
                    violation.record_key,
                    violation.severity.value,
                    violation.message,
                    json.dumps(violation.details, sort_keys=True),
                    violation.owner_team,
                ],
            )
            count += 1
        if count:
            self.connection.commit()
        return count

    def _check_required(self, domain: str, rule_code: str, record: dict[str, Any], fields: list[str], severity: QualitySeverity) -> list[QualityViolation]:
        violations: list[QualityViolation] = []
        missing = [field_name for field_name in fields if record.get(field_name) in (None, "")]
        if missing:
            violations.append(self._violation(rule_code, domain, record, f"Missing required fields: {', '.join(missing)}", {"missingFields": missing}, severity, severity == QualitySeverity.CRITICAL))
        return violations

    def _check_choice(self, domain: str, rule_code: str, record: dict[str, Any], field_name: str, allowed: set[str], severity: QualitySeverity) -> list[QualityViolation]:
        value = record.get(field_name)
        if value is None:
            return []
        if str(value) not in allowed:
            return [self._violation(rule_code, domain, record, f"Invalid {field_name}: {value}", {field_name: value, "allowed": sorted(allowed)}, severity, severity == QualitySeverity.CRITICAL)]
        return []

    def _check_positive_int(self, domain: str, rule_code: str, record: dict[str, Any], field_name: str, severity: QualitySeverity) -> list[QualityViolation]:
        value = record.get(field_name)
        if value is None:
            return []
        try:
            if int(value) <= 0:
                raise ValueError
        except Exception:
            return [self._violation(rule_code, domain, record, f"{field_name} must be a positive integer", {field_name: value}, severity, severity == QualitySeverity.CRITICAL)]
        return []

    def _check_non_negative(self, domain: str, rule_code: str, record: dict[str, Any], field_name: str, severity: QualitySeverity) -> list[QualityViolation]:
        value = record.get(field_name, 0)
        try:
            if int(value) < 0:
                raise ValueError
        except Exception:
            return [self._violation(rule_code, domain, record, f"{field_name} must be non-negative", {field_name: value}, severity, severity == QualitySeverity.CRITICAL)]
        return []

    def _check_positive_float(self, domain: str, rule_code: str, record: dict[str, Any], field_name: str, severity: QualitySeverity) -> list[QualityViolation]:
        value = record.get(field_name)
        if value is None:
            return []
        try:
            if float(value) <= 0:
                raise ValueError
        except Exception:
            return [self._violation(rule_code, domain, record, f"{field_name} must be a positive number", {field_name: value}, severity, severity == QualitySeverity.CRITICAL)]
        return []

    def _check_date(self, domain: str, rule_code: str, record: dict[str, Any], field_name: str, severity: QualitySeverity) -> list[QualityViolation]:
        value = record.get(field_name)
        if value is None:
            return []
        if not ISO_DATE_PATTERN.match(str(value)):
            return [self._violation(rule_code, domain, record, f"{field_name} must be YYYY-MM-DD", {field_name: value}, severity, severity == QualitySeverity.CRITICAL)]
        return []

    def _check_time(self, domain: str, rule_code: str, record: dict[str, Any], field_name: str, severity: QualitySeverity) -> list[QualityViolation]:
        value = record.get(field_name)
        if value is None:
            return []
        if not ISO_TIME_PATTERN.match(str(value)):
            return [self._violation(rule_code, domain, record, f"{field_name} must be HH:MM[:SS]", {field_name: value}, severity, severity == QualitySeverity.CRITICAL)]
        return []

    def _check_datetime(self, domain: str, rule_code: str, record: dict[str, Any], field_name: str, severity: QualitySeverity) -> list[QualityViolation]:
        value = record.get(field_name)
        if value is None:
            return []
        try:
            parse_iso(str(value))
            return []
        except Exception:
            return [self._violation(rule_code, domain, record, f"{field_name} must be an ISO-8601 timestamp", {field_name: value}, severity, severity == QualitySeverity.CRITICAL)]

    def _check_email(self, domain: str, rule_code: str, record: dict[str, Any], field_name: str, severity: QualitySeverity) -> list[QualityViolation]:
        value = record.get(field_name)
        if value is None:
            return []
        if not EMAIL_PATTERN.match(str(value)):
            return [self._violation(rule_code, domain, record, f"{field_name} must be a valid email", {field_name: value}, severity, severity == QualitySeverity.CRITICAL)]
        return []

    def _check_phone(self, domain: str, rule_code: str, record: dict[str, Any], field_name: str, severity: QualitySeverity) -> list[QualityViolation]:
        value = record.get(field_name)
        if value is None:
            return []
        if not PHONE_PATTERN.match(str(value)):
            return [self._violation(rule_code, domain, record, f"{field_name} must be a valid phone number", {field_name: value}, severity, severity == QualitySeverity.CRITICAL)]
        return []

    def _check_binary_flag(self, domain: str, rule_code: str, record: dict[str, Any], field_name: str, severity: QualitySeverity) -> list[QualityViolation]:
        value = record.get(field_name)
        if value is None:
            return []
        if value not in (0, 1, True, False):
            return [self._violation(rule_code, domain, record, f"{field_name} must be binary", {field_name: value}, severity, severity == QualitySeverity.CRITICAL)]
        return []

    def _violation(
        self,
        rule_code: str,
        domain_name: str,
        record: dict[str, Any],
        message: str,
        details: dict[str, Any],
        severity: QualitySeverity,
        publish_blocking: bool,
    ) -> QualityViolation:
        record_key = str(record.get("id") or record.get("record_key") or record.get("reservation_token") or record.get("email") or record.get("correlation_id") or record.get("appointment_id") or "unknown")
        return QualityViolation(
            rule_code=rule_code,
            domain_name=domain_name,
            record_key=record_key,
            severity=severity,
            message=message,
            details=details,
            owner_team=self.domain_owners.get(domain_name, "data-platform"),
            confidence=1.0,
            suggested_action="quarantine" if publish_blocking else "review",
            publish_blocking=publish_blocking,
        )

    def _duplicate_rule_code(self, domain_name: str) -> str:
        return {
            "appointments": "DQ-APP-003",
            "patient_profiles": "DQ-PAT-003",
            "appointment_reservations": "DQ-RES-003",
            "booking_events": "DQ-EVT-003",
            "confirmation_deliveries": "DQ-DEL-003",
            "reminder_log": "DQ-REM-003",
        }.get(domain_name, "DQ-DUP-001")

    def _normalize_key(self, values: Iterable[Any]) -> str:
        return "|".join("" if value is None else str(value).strip().lower() for value in values)

    def _duplicate_confidence(self, records: list[dict[str, Any]]) -> float:
        if len(records) < 2:
            return 0.0
        first = records[0]
        second = records[1]
        name_a = f"{first.get('first_name', '')} {first.get('last_name', '')}".strip().lower()
        name_b = f"{second.get('first_name', '')} {second.get('last_name', '')}".strip().lower()
        similarity = SequenceMatcher(None, name_a, name_b).ratio()
        if first.get("email") == second.get("email") or first.get("phone") == second.get("phone"):
            return 0.99
        return round(min(0.95, max(0.75, similarity)), 2)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Data quality validation checks")
    parser.add_argument("--db", default=str(BASE_DIR / "db" / "appointments.db"), help="SQLite database path")
    parser.add_argument("--report-dir", default=None, help="Directory for quality reports")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan", help="Validate a database-backed domain")
    scan_parser.add_argument("--domain", required=True, help="Domain name, e.g. appointments")
    scan_parser.add_argument("--stage", default="scheduled", help="Validation stage")
    scan_parser.add_argument("--mode", choices=[item.value for item in EnforcementMode], default=EnforcementMode.OBSERVE.value)

    publish_parser = subparsers.add_parser("publish-gate", help="Validate a publish batch and quarantine severe failures")
    publish_parser.add_argument("--input", required=True, help="JSON file with records_by_domain payload")
    publish_parser.add_argument("--mode", choices=[item.value for item in EnforcementMode], default=EnforcementMode.BLOCK.value)

    report_parser = subparsers.add_parser("report", help="Export a quality run report")
    report_parser.add_argument("--run-id", required=True, help="Quality run identifier")

    subparsers.add_parser("rules", help="Print seeded rule catalog")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    from src import db

    db.initialize_database(Path(args.db))
    with db.get_connection(Path(args.db)) as connection:
        engine = DataQualityEngine(connection, report_dir=Path(args.report_dir) if args.report_dir else None)

        if args.command == "rules":
            print(json.dumps([engine_rule.__dict__ for engine_rule in engine.default_rules], indent=2, default=str))
            return 0

        if args.command == "scan":
            report = engine.validate_table_domain(args.domain, stage_name=args.stage, enforcement_mode=EnforcementMode(args.mode))
            print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
            return 0

        if args.command == "publish-gate":
            payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
            decision = engine.validate_publish_batch(payload, enforcement_mode=EnforcementMode(args.mode))
            print(json.dumps({
                "blocked": decision.blocked,
                "blockedCount": decision.blocked_count,
                "quarantineCount": decision.quarantine_count,
                "report": decision.report.to_dict(),
            }, indent=2, sort_keys=True))
            return 0

        if args.command == "report":
            report = engine.export_report(args.run_id)
            print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
            return 0

        parser.error("Unknown command")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
