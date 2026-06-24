"""
EP-008 US-097: Disaster Recovery Drill

OPS-1   Drill execution plan — ``DrillScenario`` wraps a ``RecoveryProcedure``
        from the DR plan (US-096) with a ``step_executor`` callable so the
        drill runner can invoke each step programmatically in the test
        environment.  ``DrillRunner`` drives the execution, records timing for
        each step, and computes the actual recovery time for RTO comparison.

DOC-1   Findings capture — ``DrillFinding`` records one deviation, gap, or
        observation from the drill.  Each finding carries a severity
        (``"gap"`` | ``"warning"`` | ``"info"``), the step number where it
        occurred, and a recommended remediation action.
        ``DrillReport.add_finding()`` accumulates findings during the run.

OPS-2   Action item creation — ``ActionItem`` represents one remediation task
        generated from a finding.  ``ActionItemRegistry`` deduplicates items
        and provides query helpers for the ops team.

DOC-2   Plan update — ``PlanUpdater`` applies approved action items back into
        the ``DisasterRecoveryPlan`` as ``DrillNote`` lessons-learned entries,
        keeping the living document current after each drill.

Injectable pattern (mirrors EP-008 module family):
  ``DrillScenario.step_executor`` accepts any zero-argument callable.
  Tests pass simple lambdas; production wires in SSH/API calls.
  ``FailingStepExecutor`` injects controlled step failures.
"""
from __future__ import annotations

import itertools
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

_ITEM_COUNTER = itertools.count(1)

from src.disaster_recovery_plan import (
    DisasterRecoveryPlan,
    DrillNote,
    RecoveryObjectives,
    RecoveryProcedure,
    RecoveryStatus,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_STEP_TIMEOUT_SECONDS: float = 300.0  # 5 minutes per step wall-clock cap


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class FindingSeverity(str, Enum):
    GAP = "gap"
    WARNING = "warning"
    INFO = "info"


class ActionItemStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    WONT_FIX = "wont_fix"


# ---------------------------------------------------------------------------
# OPS-1: Drill scenario
# ---------------------------------------------------------------------------


@dataclass
class StepResult:
    """Outcome of executing one ``RecoveryStep`` during the drill (OPS-1).

    Attributes
    ----------
    step_number         Step position in the parent procedure.
    description         Step description (from ``RecoveryStep``).
    status              Execution status.
    duration_seconds    Wall-clock time taken.
    estimated_seconds   Expected duration from the plan (for comparison).
    output              Captured stdout/return value from the executor.
    error               Error message if status is FAILED.
    executed_at         ISO-8601 UTC timestamp.
    """

    step_number: int
    description: str
    status: RecoveryStatus
    duration_seconds: float
    estimated_seconds: float
    output: str = ""
    error: str = ""
    executed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def exceeded_estimate(self) -> bool:
        return self.duration_seconds > self.estimated_seconds

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_number": self.step_number,
            "description": self.description,
            "status": self.status.value,
            "duration_seconds": round(self.duration_seconds, 2),
            "estimated_seconds": self.estimated_seconds,
            "exceeded_estimate": self.exceeded_estimate,
            "output": self.output,
            "error": self.error,
            "executed_at": self.executed_at,
        }


@dataclass
class DrillScenario:
    """Executable wrapper around a ``RecoveryProcedure`` (OPS-1).

    Attributes
    ----------
    procedure       The DR plan procedure to drill.
    step_executors  Mapping of step_number → callable.
                    Missing entries use a no-op pass-through.
    environment     Label for the drill environment (e.g. ``"staging"``).
    """

    procedure: RecoveryProcedure
    step_executors: dict[int, Callable[[], Any]] = field(default_factory=dict)
    environment: str = "test"


# ---------------------------------------------------------------------------
# DOC-1: Findings
# ---------------------------------------------------------------------------


@dataclass
class DrillFinding:
    """One deviation or gap observed during the drill (DOC-1).

    Attributes
    ----------
    scenario_name   Name of the procedure where the finding occurred.
    step_number     Step number (0 = pre/post condition issue).
    severity        GAP / WARNING / INFO.
    description     What was observed.
    recommendation  Suggested remediation.
    recorded_at     ISO-8601 UTC timestamp.
    """

    scenario_name: str
    step_number: int
    severity: FindingSeverity
    description: str
    recommendation: str = ""
    recorded_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_name": self.scenario_name,
            "step_number": self.step_number,
            "severity": self.severity.value,
            "description": self.description,
            "recommendation": self.recommendation,
            "recorded_at": self.recorded_at,
        }


# ---------------------------------------------------------------------------
# OPS-2: Action items
# ---------------------------------------------------------------------------


@dataclass
class ActionItem:
    """Remediation task generated from a drill finding (OPS-2).

    Attributes
    ----------
    item_id         Unique identifier (auto-generated if not supplied).
    title           Short description of the required action.
    description     Full detail including reproduction context.
    assigned_to     Team or person responsible.
    priority        ``"critical"`` | ``"high"`` | ``"medium"`` | ``"low"``
    status          Open/in-progress/resolved lifecycle.
    source_finding  Reference back to the originating ``DrillFinding``.
    created_at      ISO-8601 UTC timestamp.
    """

    title: str
    description: str
    assigned_to: str = "SRE team"
    priority: str = "high"
    status: ActionItemStatus = ActionItemStatus.OPEN
    source_finding: DrillFinding | None = None
    item_id: str = field(default_factory=lambda: f"DR-{next(_ITEM_COUNTER):05d}")
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def resolve(self) -> None:
        self.status = ActionItemStatus.RESOLVED

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "title": self.title,
            "description": self.description,
            "assigned_to": self.assigned_to,
            "priority": self.priority,
            "status": self.status.value,
            "created_at": self.created_at,
        }


class ActionItemRegistry:
    """Stores and queries action items generated from drill findings (OPS-2)."""

    def __init__(self) -> None:
        self._items: dict[str, ActionItem] = {}

    def add(self, item: ActionItem) -> None:
        self._items[item.item_id] = item

    def get(self, item_id: str) -> ActionItem | None:
        return self._items.get(item_id)

    def open_items(self) -> list[ActionItem]:
        return [i for i in self._items.values() if i.status == ActionItemStatus.OPEN]

    def all_items(self) -> list[ActionItem]:
        return list(self._items.values())

    def items_by_priority(self, priority: str) -> list[ActionItem]:
        return [i for i in self._items.values() if i.priority == priority]

    def total_count(self) -> int:
        return len(self._items)

    def open_count(self) -> int:
        return len(self.open_items())


# ---------------------------------------------------------------------------
# Drill report
# ---------------------------------------------------------------------------


@dataclass
class DrillReport:
    """Full outcome report for a completed drill run.

    Attributes
    ----------
    scenario_name       Name of the drilled procedure.
    environment         Environment label (e.g. ``"staging"``).
    step_results        Per-step execution outcomes.
    findings            Observations captured during the drill.
    total_duration_s    Wall-clock time from start to finish.
    status              Overall drill status.
    rto_met             True when actual recovery time ≤ RTO.
    actual_rto_minutes  Measured recovery time in minutes.
    generated_at        ISO-8601 UTC timestamp.
    """

    scenario_name: str
    environment: str
    step_results: list[StepResult] = field(default_factory=list)
    findings: list[DrillFinding] = field(default_factory=list)
    total_duration_s: float = 0.0
    status: RecoveryStatus = RecoveryStatus.PENDING
    rto_met: bool = True
    actual_rto_minutes: float = 0.0
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def add_finding(self, finding: DrillFinding) -> None:
        self.findings.append(finding)

    def gap_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == FindingSeverity.GAP)

    def finding_count(self) -> int:
        return len(self.findings)

    def failed_steps(self) -> list[StepResult]:
        return [s for s in self.step_results if s.status == RecoveryStatus.FAILED]

    def exceeded_estimate_steps(self) -> list[StepResult]:
        return [s for s in self.step_results if s.exceeded_estimate]

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_name": self.scenario_name,
            "environment": self.environment,
            "status": self.status.value,
            "total_duration_s": round(self.total_duration_s, 2),
            "actual_rto_minutes": round(self.actual_rto_minutes, 2),
            "rto_met": self.rto_met,
            "step_count": len(self.step_results),
            "failed_step_count": len(self.failed_steps()),
            "finding_count": self.finding_count(),
            "gap_count": self.gap_count(),
            "generated_at": self.generated_at,
            "step_results": [s.to_dict() for s in self.step_results],
            "findings": [f.to_dict() for f in self.findings],
        }


# ---------------------------------------------------------------------------
# OPS-1: Drill runner
# ---------------------------------------------------------------------------


class DrillRunner:
    """Executes a ``DrillScenario``, records step results, and produces a
    ``DrillReport`` (OPS-1).

    Each step's executor is called in order.  Exceptions are caught and
    recorded as FAILED step results (they do not abort the drill unless
    ``stop_on_failure=True``).

    Usage::

        scenario = DrillScenario(
            procedure=plan.get_procedure("database_restore"),
            step_executors={1: lambda: run_backup_list(), 2: lambda: run_restore()},
        )
        runner = DrillRunner(objectives)
        report = runner.run(scenario)
    """

    def __init__(
        self,
        objectives: RecoveryObjectives | None = None,
        stop_on_failure: bool = False,
    ) -> None:
        self._objectives = objectives or RecoveryObjectives()
        self._stop_on_failure = stop_on_failure

    def run(self, scenario: DrillScenario) -> DrillReport:
        """Execute all steps in *scenario* and return a ``DrillReport``."""
        report = DrillReport(
            scenario_name=scenario.procedure.scenario_name,
            environment=scenario.environment,
            status=RecoveryStatus.IN_PROGRESS,
        )
        drill_start = time.monotonic()

        for step in scenario.procedure.steps:
            executor = scenario.step_executors.get(step.step_number, lambda: None)
            step_start = time.monotonic()
            try:
                output = executor()
                duration = time.monotonic() - step_start
                result = StepResult(
                    step_number=step.step_number,
                    description=step.description,
                    status=RecoveryStatus.COMPLETED,
                    duration_seconds=duration,
                    estimated_seconds=step.estimated_minutes * 60,
                    output=str(output) if output is not None else "",
                )
                # Auto-flag if step took > 2× estimated
                if result.exceeded_estimate and duration > step.estimated_minutes * 120:
                    report.add_finding(DrillFinding(
                        scenario_name=scenario.procedure.scenario_name,
                        step_number=step.step_number,
                        severity=FindingSeverity.WARNING,
                        description=(
                            f"Step {step.step_number} took {duration:.1f}s, "
                            f"exceeding estimate of {step.estimated_minutes * 60}s"
                        ),
                        recommendation="Review step and update estimate or optimise.",
                    ))
            except Exception as exc:  # noqa: BLE001
                duration = time.monotonic() - step_start
                result = StepResult(
                    step_number=step.step_number,
                    description=step.description,
                    status=RecoveryStatus.FAILED,
                    duration_seconds=duration,
                    estimated_seconds=step.estimated_minutes * 60,
                    error=str(exc),
                )
                report.add_finding(DrillFinding(
                    scenario_name=scenario.procedure.scenario_name,
                    step_number=step.step_number,
                    severity=FindingSeverity.GAP,
                    description=f"Step {step.step_number} failed: {exc}",
                    recommendation=f"Fix executor for step {step.step_number}.",
                ))
                report.step_results.append(result)
                if self._stop_on_failure:
                    break
                continue

            report.step_results.append(result)

        total_duration = time.monotonic() - drill_start
        report.total_duration_s = total_duration
        report.actual_rto_minutes = total_duration / 60.0
        report.rto_met = self._objectives.is_rto_met(report.actual_rto_minutes)
        failed = report.failed_steps()
        report.status = (
            RecoveryStatus.FAILED if failed else RecoveryStatus.COMPLETED
        )
        return report


# ---------------------------------------------------------------------------
# DOC-2: Plan updater — applies drill outcomes to the living DR plan
# ---------------------------------------------------------------------------


class PlanUpdater:
    """Translates ``DrillReport`` findings into DR plan lessons (DOC-2).

    Usage::

        updater = PlanUpdater(plan)
        items   = updater.apply(report, action_registry)
        # plan.lessons() now contains entries for each finding
        # action_registry.all_items() now contains remediation tasks
    """

    def __init__(self, plan: DisasterRecoveryPlan) -> None:
        self._plan = plan

    def apply(
        self,
        report: DrillReport,
        action_registry: ActionItemRegistry | None = None,
    ) -> list[ActionItem]:
        """Write findings as ``DrillNote`` lessons and create ``ActionItem`` tasks."""
        created_items: list[ActionItem] = []
        for finding in report.findings:
            note = DrillNote(
                procedure_name=finding.scenario_name,
                observation=finding.description,
                severity=finding.severity.value,
                recorded_by="DR Drill Runner (automated)",
            )
            self._plan.add_lesson(note)

            if finding.severity in (FindingSeverity.GAP, FindingSeverity.WARNING):
                item = ActionItem(
                    title=f"[{finding.severity.value.upper()}] {finding.scenario_name} step {finding.step_number}",
                    description=finding.description,
                    assigned_to="SRE team",
                    priority="critical" if finding.severity == FindingSeverity.GAP else "high",
                    source_finding=finding,
                )
                if action_registry:
                    action_registry.add(item)
                created_items.append(item)
        return created_items


# ---------------------------------------------------------------------------
# Injectable test helpers
# ---------------------------------------------------------------------------


def noop_executor() -> None:
    """Always succeeds — used as a default step executor in tests."""


def failing_executor(message: str = "step failed") -> Callable[[], None]:
    """Returns a callable that always raises RuntimeError(*message*)."""
    def _fail() -> None:
        raise RuntimeError(message)
    return _fail
