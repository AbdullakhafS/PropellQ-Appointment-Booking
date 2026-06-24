"""
EP-008 US-096: Disaster Recovery Plan — Test Suite

QA-1  Procedure Completeness Review — plan covers infra, data, app, and cache layers
QA-2  Drill Readiness Review        — plan is usable during a controlled recovery test
QA-3  Objective Review              — RTO/RPO are explicit and measurable
QA-4  Approval Review               — stakeholder sign-off captured
"""
from __future__ import annotations

import pytest

from src.disaster_recovery_plan import (
    PROPELIQ_RPO_MINUTES,
    PROPELIQ_RTO_MINUTES,
    ApprovalStatus,
    DisasterRecoveryPlan,
    DrillNote,
    RecoveryDomain,
    RecoveryObjectives,
    RecoveryProcedure,
    RecoveryStep,
    RecoveryStatus,
    StakeholderApproval,
    build_propeliq_dr_plan,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _simple_procedure(
    name: str = "test_scenario",
    domain: RecoveryDomain = RecoveryDomain.APPLICATION,
) -> RecoveryProcedure:
    proc = RecoveryProcedure(
        scenario_name=name,
        domain=domain,
        description="Test procedure",
    )
    proc.add_step(RecoveryStep(1, "Restart service", "SRE", 5, "systemctl status"))
    return proc


def _full_plan() -> DisasterRecoveryPlan:
    return build_propeliq_dr_plan()


# ===========================================================================
# QA-1: Procedure Completeness Review (DOC-1)
# ===========================================================================


class TestProcedureCompleteness:
    """QA-1 — Plan covers infrastructure, data, application, and cache layers."""

    def test_builtin_plan_covers_all_domains(self):
        plan = _full_plan()
        assert plan.covers_all_domains()

    def test_builtin_plan_has_infrastructure_procedure(self):
        assert _full_plan().covers_domain(RecoveryDomain.INFRASTRUCTURE)

    def test_builtin_plan_has_data_procedure(self):
        assert _full_plan().covers_domain(RecoveryDomain.DATA)

    def test_builtin_plan_has_application_procedure(self):
        assert _full_plan().covers_domain(RecoveryDomain.APPLICATION)

    def test_builtin_plan_has_cache_procedure(self):
        assert _full_plan().covers_domain(RecoveryDomain.CACHE)

    def test_plan_without_all_domains_fails_coverage(self):
        plan = DisasterRecoveryPlan()
        plan.add_procedure(_simple_procedure(domain=RecoveryDomain.APPLICATION))
        assert not plan.covers_all_domains()

    def test_recovery_procedure_has_steps(self):
        plan = _full_plan()
        for proc in plan.all_procedures():
            assert proc.step_count() > 0, f"{proc.scenario_name} has no steps"

    def test_recovery_procedure_has_preconditions(self):
        plan = _full_plan()
        for proc in plan.all_procedures():
            assert proc.preconditions, f"{proc.scenario_name} has no preconditions"

    def test_recovery_procedure_has_postconditions(self):
        plan = _full_plan()
        for proc in plan.all_procedures():
            assert proc.postconditions, f"{proc.scenario_name} has no postconditions"

    def test_step_has_verification_command(self):
        plan = _full_plan()
        for proc in plan.all_procedures():
            for step in proc.steps:
                assert step.verification, f"{proc.scenario_name} step {step.step_number} has no verification"

    def test_procedure_to_dict_has_expected_keys(self):
        d = _simple_procedure().to_dict()
        assert all(k in d for k in [
            "scenario_name", "domain", "step_count",
            "total_estimated_minutes", "preconditions", "postconditions", "steps"
        ])

    def test_step_to_dict_has_expected_keys(self):
        step = RecoveryStep(1, "Action", "SRE", 5, "check cmd")
        d = step.to_dict()
        assert all(k in d for k in [
            "step_number", "description", "responsible_role",
            "estimated_minutes", "verification"
        ])

    def test_plan_summary_domains_covered(self):
        plan = _full_plan()
        summary = plan.summary()
        assert "domains_covered" in summary
        assert len(summary["domains_covered"]) == 4


# ===========================================================================
# QA-2: Drill Readiness Review (DOC-2)
# ===========================================================================


class TestDrillReadiness:
    """QA-2 — Plan is usable during a controlled recovery test."""

    def test_add_procedure_stored(self):
        plan = DisasterRecoveryPlan()
        proc = _simple_procedure()
        plan.add_procedure(proc)
        assert plan.get_procedure("test_scenario") is proc

    def test_get_procedure_returns_none_for_unknown(self):
        assert DisasterRecoveryPlan().get_procedure("nonexistent") is None

    def test_procedures_for_domain_filter(self):
        plan = DisasterRecoveryPlan()
        plan.add_procedure(_simple_procedure("a", RecoveryDomain.APPLICATION))
        plan.add_procedure(_simple_procedure("b", RecoveryDomain.DATA))
        app_procs = plan.procedures_for_domain(RecoveryDomain.APPLICATION)
        assert len(app_procs) == 1
        assert app_procs[0].scenario_name == "a"

    def test_add_lesson_stored(self):
        plan = DisasterRecoveryPlan()
        note = DrillNote("test_scenario", "Step 2 took longer than expected", "warning")
        plan.add_lesson(note)
        assert len(plan.lessons()) == 1

    def test_lessons_for_procedure_filters_correctly(self):
        plan = DisasterRecoveryPlan()
        plan.add_lesson(DrillNote("proc_a", "obs 1"))
        plan.add_lesson(DrillNote("proc_b", "obs 2"))
        assert len(plan.lessons_for_procedure("proc_a")) == 1

    def test_gap_count_counted_correctly(self):
        plan = DisasterRecoveryPlan()
        plan.add_lesson(DrillNote("p", "gap obs", "gap"))
        plan.add_lesson(DrillNote("p", "info obs", "info"))
        assert plan.gap_count() == 1

    def test_drill_note_to_dict_has_expected_keys(self):
        note = DrillNote("proc", "observation", "warning", "Alice")
        d = note.to_dict()
        assert all(k in d for k in ["procedure_name", "observation", "severity", "recorded_by", "recorded_at"])

    def test_total_estimated_minutes_sums_steps(self):
        proc = RecoveryProcedure("test", RecoveryDomain.APPLICATION)
        proc.add_step(RecoveryStep(1, "a", "SRE", 5))
        proc.add_step(RecoveryStep(2, "b", "SRE", 10))
        assert proc.total_estimated_minutes() == 15


# ===========================================================================
# QA-3: Objective Review (DOC-3)
# ===========================================================================


class TestObjectiveReview:
    """QA-3 — RTO/RPO are explicit and measurable."""

    def test_builtin_rto_is_60_minutes(self):
        assert PROPELIQ_RTO_MINUTES == 60

    def test_builtin_rpo_is_15_minutes(self):
        assert PROPELIQ_RPO_MINUTES == 15

    def test_rto_met_when_actual_less_than_target(self):
        obj = RecoveryObjectives(rto_minutes=60)
        assert obj.is_rto_met(30.0)

    def test_rto_not_met_when_actual_exceeds_target(self):
        obj = RecoveryObjectives(rto_minutes=60)
        assert not obj.is_rto_met(90.0)

    def test_rto_met_at_exact_boundary(self):
        obj = RecoveryObjectives(rto_minutes=60)
        assert obj.is_rto_met(60.0)

    def test_rpo_met_when_actual_less_than_target(self):
        obj = RecoveryObjectives(rpo_minutes=15)
        assert obj.is_rpo_met(5.0)

    def test_rpo_not_met_when_actual_exceeds_target(self):
        obj = RecoveryObjectives(rpo_minutes=15)
        assert not obj.is_rpo_met(30.0)

    def test_objectives_to_dict_has_expected_keys(self):
        d = RecoveryObjectives().to_dict()
        assert all(k in d for k in ["service_name", "rto_minutes", "rpo_minutes", "sla_percent"])

    def test_builtin_plan_objectives_match_constants(self):
        plan = _full_plan()
        assert plan.objectives.rto_minutes == PROPELIQ_RTO_MINUTES
        assert plan.objectives.rpo_minutes == PROPELIQ_RPO_MINUTES

    def test_plan_summary_includes_objectives(self):
        plan = _full_plan()
        s = plan.summary()
        assert "objectives" in s
        assert s["objectives"]["rto_minutes"] == PROPELIQ_RTO_MINUTES


# ===========================================================================
# QA-4: Approval Review (DOC-4)
# ===========================================================================


class TestApprovalReview:
    """QA-4 — Stakeholder sign-off is captured and verified."""

    def test_plan_not_approved_before_any_approval(self):
        assert not DisasterRecoveryPlan().is_approved()

    def test_plan_approved_after_unconditional_approval(self):
        plan = DisasterRecoveryPlan()
        plan.add_approval(StakeholderApproval("Alice", "Head of Engineering"))
        assert plan.is_approved()

    def test_conditional_approval_not_sufficient(self):
        plan = DisasterRecoveryPlan()
        plan.add_approval(StakeholderApproval(
            "Bob", "CTO", ApprovalStatus.CONDITIONAL, "Pending DR drill completion"
        ))
        assert not plan.is_approved()

    def test_unconditional_approval_flag(self):
        a = StakeholderApproval("Alice", "Eng Lead")
        assert a.is_unconditional

    def test_conditional_approval_flag(self):
        a = StakeholderApproval("Bob", "CTO", ApprovalStatus.CONDITIONAL, "condition")
        assert not a.is_unconditional

    def test_approval_to_dict_has_expected_keys(self):
        d = StakeholderApproval("Alice", "Lead").to_dict()
        assert all(k in d for k in ["approver_name", "approver_role", "status", "approved_at"])

    def test_multiple_approvals_recorded(self):
        plan = DisasterRecoveryPlan()
        plan.add_approval(StakeholderApproval("Alice", "Eng Lead"))
        plan.add_approval(StakeholderApproval("Bob", "CTO"))
        assert len(plan.approvals()) == 2

    def test_summary_is_approved_reflects_state(self):
        plan = _full_plan()
        plan.add_approval(StakeholderApproval("Alice", "Eng Lead"))
        assert plan.summary()["is_approved"] is True
