"""
EP-008 US-096: Disaster Recovery Plan

DOC-1   Recovery procedure authoring — ``RecoveryProcedure`` describes one
        recovery scenario (e.g. "database_failover") with ordered
        ``RecoveryStep`` instructions.  Each step carries an estimated
        duration, the responsible role, and a verification command so the
        operator can confirm success before proceeding.

DOC-2   Drill usage notes and lessons-learned section — ``DrillNote`` records
        observations captured during a controlled recovery test; the
        ``DisasterRecoveryPlan`` exposes an append-only ``add_lesson()``
        interface so drill outcomes feed back into the living document.

DOC-3   RTO / RPO definition — ``RecoveryObjectives`` holds the committed
        Recovery Time Objective (maximum acceptable downtime) and Recovery
        Point Objective (maximum acceptable data loss window) per service.
        ``RecoveryObjectives.is_rto_met()`` and ``is_rpo_met()`` are used by
        the drill runner (US-097) to assert against measured outcomes.

DOC-4   Stakeholder review and approval — ``StakeholderApproval`` records who
        approved the plan, when, and whether any conditions were noted.
        ``DisasterRecoveryPlan.is_approved()`` returns True only when at least
        one unconditional approval exists.

The plan is layered into four recovery domains (QA-1):
  1. Infrastructure — compute, network, DNS failover
  2. Data           — database restore, replication re-sync
  3. Application    — service restart sequence, health gate
  4. Cache          — Redis flush / warm-up after failover

Injectable pattern:
  All state is in-memory.  In production the plan would be persisted to a
  runbook store or version control.  Tests exercise the domain objects directly.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Constants (DOC-3)
# ---------------------------------------------------------------------------

PROPELIQ_RTO_MINUTES: int = 60       # 1-hour RTO commitment
PROPELIQ_RPO_MINUTES: int = 15       # 15-minute RPO commitment
PROPELIQ_SLA_PERCENT: float = 99.9   # mirrored from uptime_monitoring


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class RecoveryDomain(str, Enum):
    INFRASTRUCTURE = "infrastructure"
    DATA = "data"
    APPLICATION = "application"
    CACHE = "cache"


class RecoveryStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ApprovalStatus(str, Enum):
    APPROVED = "approved"
    CONDITIONAL = "conditional"
    REJECTED = "rejected"


# ---------------------------------------------------------------------------
# DOC-3: Recovery objectives
# ---------------------------------------------------------------------------


@dataclass
class RecoveryObjectives:
    """RTO and RPO definition for a service tier (DOC-3).

    Attributes
    ----------
    service_name    Label for reporting (e.g. ``"PropelIQ API"``).
    rto_minutes     Maximum tolerable downtime in minutes.
    rpo_minutes     Maximum tolerable data loss window in minutes.
    sla_percent     Uptime SLA commitment (for cross-reference with OPS).
    """

    service_name: str = "PropelIQ API"
    rto_minutes: int = PROPELIQ_RTO_MINUTES
    rpo_minutes: int = PROPELIQ_RPO_MINUTES
    sla_percent: float = PROPELIQ_SLA_PERCENT

    def is_rto_met(self, actual_recovery_minutes: float) -> bool:
        return actual_recovery_minutes <= self.rto_minutes

    def is_rpo_met(self, actual_data_loss_minutes: float) -> bool:
        return actual_data_loss_minutes <= self.rpo_minutes

    def to_dict(self) -> dict[str, Any]:
        return {
            "service_name": self.service_name,
            "rto_minutes": self.rto_minutes,
            "rpo_minutes": self.rpo_minutes,
            "sla_percent": self.sla_percent,
        }


# ---------------------------------------------------------------------------
# DOC-1: Recovery steps and procedures
# ---------------------------------------------------------------------------


@dataclass
class RecoveryStep:
    """One action within a ``RecoveryProcedure`` (DOC-1).

    Attributes
    ----------
    step_number         Ordering within the parent procedure.
    description         What the operator must do.
    responsible_role    Who performs this step (e.g. ``"SRE on-call"``).
    estimated_minutes   Expected wall-clock duration.
    verification        Command or check that confirms step success.
    notes               Optional additional context.
    """

    step_number: int
    description: str
    responsible_role: str
    estimated_minutes: int = 5
    verification: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_number": self.step_number,
            "description": self.description,
            "responsible_role": self.responsible_role,
            "estimated_minutes": self.estimated_minutes,
            "verification": self.verification,
            "notes": self.notes,
        }


@dataclass
class RecoveryProcedure:
    """Ordered collection of steps for one recovery scenario (DOC-1).

    Attributes
    ----------
    scenario_name   Unique identifier (e.g. ``"database_failover"``).
    domain          ``RecoveryDomain`` this procedure belongs to.
    description     Human-readable scenario summary.
    steps           Ordered list of ``RecoveryStep`` objects.
    preconditions   What must be true before starting (e.g. backup verified).
    postconditions  What must be true after completion (e.g. health checks pass).
    """

    scenario_name: str
    domain: RecoveryDomain
    description: str = ""
    steps: list[RecoveryStep] = field(default_factory=list)
    preconditions: list[str] = field(default_factory=list)
    postconditions: list[str] = field(default_factory=list)

    def add_step(self, step: RecoveryStep) -> None:
        self.steps.append(step)

    def total_estimated_minutes(self) -> int:
        return sum(s.estimated_minutes for s in self.steps)

    def step_count(self) -> int:
        return len(self.steps)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_name": self.scenario_name,
            "domain": self.domain.value,
            "description": self.description,
            "step_count": self.step_count(),
            "total_estimated_minutes": self.total_estimated_minutes(),
            "preconditions": self.preconditions,
            "postconditions": self.postconditions,
            "steps": [s.to_dict() for s in self.steps],
        }


# ---------------------------------------------------------------------------
# DOC-2: Drill note (lessons-learned capture)
# ---------------------------------------------------------------------------


@dataclass
class DrillNote:
    """A lesson or observation captured during a DR drill (DOC-2).

    Attributes
    ----------
    procedure_name  Which recovery scenario the note relates to.
    observation     What was observed.
    severity        ``"info"`` | ``"warning"`` | ``"gap"``
    recorded_by     Author (name or role).
    recorded_at     ISO-8601 UTC timestamp.
    """

    procedure_name: str
    observation: str
    severity: str = "info"
    recorded_by: str = ""
    recorded_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "procedure_name": self.procedure_name,
            "observation": self.observation,
            "severity": self.severity,
            "recorded_by": self.recorded_by,
            "recorded_at": self.recorded_at,
        }


# ---------------------------------------------------------------------------
# DOC-4: Stakeholder approval
# ---------------------------------------------------------------------------


@dataclass
class StakeholderApproval:
    """Records stakeholder sign-off on the DR plan (DOC-4).

    Attributes
    ----------
    approver_name   Full name of the approver.
    approver_role   Organisational role (e.g. ``"Head of Engineering"``).
    status          APPROVED / CONDITIONAL / REJECTED.
    conditions      Non-empty when status is CONDITIONAL.
    approved_at     ISO-8601 UTC timestamp.
    """

    approver_name: str
    approver_role: str
    status: ApprovalStatus = ApprovalStatus.APPROVED
    conditions: str = ""
    approved_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def is_unconditional(self) -> bool:
        return self.status == ApprovalStatus.APPROVED and not self.conditions

    def to_dict(self) -> dict[str, Any]:
        return {
            "approver_name": self.approver_name,
            "approver_role": self.approver_role,
            "status": self.status.value,
            "conditions": self.conditions,
            "approved_at": self.approved_at,
            "is_unconditional": self.is_unconditional,
        }


# ---------------------------------------------------------------------------
# Main plan container
# ---------------------------------------------------------------------------


class DisasterRecoveryPlan:
    """Living disaster recovery plan for PropelIQ (DOC-1 / DOC-2 / DOC-3 / DOC-4).

    Usage::

        plan = DisasterRecoveryPlan(objectives=RecoveryObjectives())
        plan.add_procedure(db_failover_procedure)
        plan.add_lesson(DrillNote("database_failover", "Step 3 took 8 min — exceeded estimate"))
        plan.add_approval(StakeholderApproval("Alice", "Head of Engineering"))
        plan.is_approved()   # True
    """

    def __init__(
        self,
        objectives: RecoveryObjectives | None = None,
        version: str = "1.0.0",
    ) -> None:
        self._objectives = objectives or RecoveryObjectives()
        self._version = version
        self._procedures: dict[str, RecoveryProcedure] = {}
        self._lessons: list[DrillNote] = []
        self._approvals: list[StakeholderApproval] = []
        self._last_updated: str = datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------
    # DOC-1: Procedures
    # ------------------------------------------------------------------

    def add_procedure(self, procedure: RecoveryProcedure) -> None:
        self._procedures[procedure.scenario_name] = procedure
        self._touch()

    def get_procedure(self, scenario_name: str) -> RecoveryProcedure | None:
        return self._procedures.get(scenario_name)

    def procedures_for_domain(self, domain: RecoveryDomain) -> list[RecoveryProcedure]:
        return [p for p in self._procedures.values() if p.domain == domain]

    def all_procedures(self) -> list[RecoveryProcedure]:
        return list(self._procedures.values())

    def covers_domain(self, domain: RecoveryDomain) -> bool:
        return any(p.domain == domain for p in self._procedures.values())

    def covers_all_domains(self) -> bool:
        return all(self.covers_domain(d) for d in RecoveryDomain)

    # ------------------------------------------------------------------
    # DOC-2: Lessons learned
    # ------------------------------------------------------------------

    def add_lesson(self, note: DrillNote) -> None:
        self._lessons.append(note)
        self._touch()

    def lessons(self) -> list[DrillNote]:
        return list(self._lessons)

    def lessons_for_procedure(self, procedure_name: str) -> list[DrillNote]:
        return [n for n in self._lessons if n.procedure_name == procedure_name]

    def gap_count(self) -> int:
        return sum(1 for n in self._lessons if n.severity == "gap")

    # ------------------------------------------------------------------
    # DOC-3: Objectives
    # ------------------------------------------------------------------

    @property
    def objectives(self) -> RecoveryObjectives:
        return self._objectives

    # ------------------------------------------------------------------
    # DOC-4: Approvals
    # ------------------------------------------------------------------

    def add_approval(self, approval: StakeholderApproval) -> None:
        self._approvals.append(approval)
        self._touch()

    def approvals(self) -> list[StakeholderApproval]:
        return list(self._approvals)

    def is_approved(self) -> bool:
        return any(a.is_unconditional for a in self._approvals)

    # ------------------------------------------------------------------
    # Plan summary
    # ------------------------------------------------------------------

    def summary(self) -> dict[str, Any]:
        return {
            "version": self._version,
            "last_updated": self._last_updated,
            "objectives": self._objectives.to_dict(),
            "procedure_count": len(self._procedures),
            "covers_all_domains": self.covers_all_domains(),
            "lesson_count": len(self._lessons),
            "gap_count": self.gap_count(),
            "approval_count": len(self._approvals),
            "is_approved": self.is_approved(),
            "domains_covered": [d.value for d in RecoveryDomain if self.covers_domain(d)],
        }

    def _touch(self) -> None:
        self._last_updated = datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Built-in PropelIQ DR procedures
# ---------------------------------------------------------------------------


def build_propeliq_dr_plan() -> DisasterRecoveryPlan:
    """Return a pre-populated DR plan covering all four recovery domains."""
    plan = DisasterRecoveryPlan(
        objectives=RecoveryObjectives(
            service_name="PropelIQ API",
            rto_minutes=PROPELIQ_RTO_MINUTES,
            rpo_minutes=PROPELIQ_RPO_MINUTES,
        ),
        version="1.0.0",
    )

    # INFRASTRUCTURE: DNS/load-balancer failover
    infra = RecoveryProcedure(
        scenario_name="infrastructure_failover",
        domain=RecoveryDomain.INFRASTRUCTURE,
        description="Failover compute and network to secondary region.",
        preconditions=["Secondary region healthy", "DNS TTL ≤ 60s"],
        postconditions=["LB health checks pass", "Traffic flowing to secondary"],
    )
    infra.add_step(RecoveryStep(1, "Verify secondary region capacity", "SRE on-call", 5,
                                "aws ec2 describe-instances --region us-west-2"))
    infra.add_step(RecoveryStep(2, "Update DNS records to secondary region", "SRE on-call", 10,
                                "dig +short api.propeliq.com"))
    infra.add_step(RecoveryStep(3, "Confirm LB health checks pass in secondary", "SRE on-call", 5,
                                "curl -f https://api.propeliq.com/health/ready"))
    plan.add_procedure(infra)

    # DATA: Database restore from backup
    data = RecoveryProcedure(
        scenario_name="database_restore",
        domain=RecoveryDomain.DATA,
        description="Restore database from latest verified backup.",
        preconditions=["Backup integrity verified", "Target instance stopped"],
        postconditions=["Row counts within 1% of pre-failure", "Replication lag < 5s"],
    )
    data.add_step(RecoveryStep(1, "Identify last verified backup snapshot", "DBA on-call", 5,
                               "python backup.py list --verified"))
    data.add_step(RecoveryStep(2, "Restore snapshot to recovery instance", "DBA on-call", 20,
                               "python backup.py restore --snapshot <id>"))
    data.add_step(RecoveryStep(3, "Run restore verification suite", "DBA on-call", 10,
                               "python restore_verification.py --env recovery"))
    data.add_step(RecoveryStep(4, "Promote recovery instance to primary", "DBA on-call", 5,
                               "python replication_manager.py promote --instance recovery"))
    plan.add_procedure(data)

    # APPLICATION: Service restart sequence
    app = RecoveryProcedure(
        scenario_name="application_restart",
        domain=RecoveryDomain.APPLICATION,
        description="Restart API services in dependency order with health gate.",
        preconditions=["Database accepting connections", "Redis available"],
        postconditions=["All /health/ready endpoints return 200", "No error spike in logs"],
    )
    app.add_step(RecoveryStep(1, "Start background workers (reminder queue)", "SRE on-call", 3,
                              "systemctl start propeliq-worker"))
    app.add_step(RecoveryStep(2, "Start API servers (all instances)", "SRE on-call", 5,
                              "systemctl start propeliq-api@*"))
    app.add_step(RecoveryStep(3, "Validate health endpoints", "SRE on-call", 5,
                              "curl -f https://api.propeliq.com/health/ready"))
    app.add_step(RecoveryStep(4, "Re-enable LB traffic", "SRE on-call", 2,
                              "aws elbv2 register-targets …"))
    plan.add_procedure(app)

    # CACHE: Redis flush and warm-up
    cache = RecoveryProcedure(
        scenario_name="cache_recovery",
        domain=RecoveryDomain.CACHE,
        description="Flush stale cache and allow warm-up after failover.",
        preconditions=["New Redis instance healthy", "Application restarted"],
        postconditions=["Cache hit ratio recovering", "No stale data served"],
    )
    cache.add_step(RecoveryStep(1, "Flush Redis instance", "SRE on-call", 2,
                                "redis-cli FLUSHALL"))
    cache.add_step(RecoveryStep(2, "Restart API servers to reconnect", "SRE on-call", 5,
                                "systemctl restart propeliq-api@*"))
    cache.add_step(RecoveryStep(3, "Monitor cache hit ratio for 10 minutes", "SRE on-call", 10,
                                "redis-cli INFO stats | grep keyspace_hits"))
    plan.add_procedure(cache)

    return plan
