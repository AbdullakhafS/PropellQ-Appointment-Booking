"""
EP-008 US-097: Disaster Recovery Drill — Test Suite

QA-1  Controlled Execution Review — team can execute plan in test environment
QA-2  Findings Review             — findings documented completely
QA-3  Action Item Review          — actionable remediation items created
QA-4  Plan Update Review          — DR plan updated after drill completion
"""
from __future__ import annotations

import pytest

from src.disaster_recovery_plan import (
    DisasterRecoveryPlan,
    RecoveryDomain,
    RecoveryObjectives,
    RecoveryProcedure,
    RecoveryStatus,
    RecoveryStep,
    build_propeliq_dr_plan,
)
from src.dr_drill import (
    ActionItem,
    ActionItemRegistry,
    ActionItemStatus,
    DrillFinding,
    DrillReport,
    DrillRunner,
    DrillScenario,
    FindingSeverity,
    PlanUpdater,
    StepResult,
    failing_executor,
    noop_executor,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _simple_procedure(name: str = "app_restart", steps: int = 3) -> RecoveryProcedure:
    proc = RecoveryProcedure(
        scenario_name=name,
        domain=RecoveryDomain.APPLICATION,
        description="Simple test procedure",
    )
    for i in range(1, steps + 1):
        proc.add_step(RecoveryStep(i, f"Step {i}", "SRE", estimated_minutes=1,
                                   verification=f"check {i}"))
    return proc


def _scenario(procedure: RecoveryProcedure, executors: dict | None = None) -> DrillScenario:
    return DrillScenario(
        procedure=procedure,
        step_executors=executors or {},
        environment="test",
    )


def _run(procedure: RecoveryProcedure, executors: dict | None = None) -> DrillReport:
    runner = DrillRunner()
    return runner.run(_scenario(procedure, executors))


# ===========================================================================
# QA-1: Controlled Execution Review (OPS-1)
# ===========================================================================


class TestControlledExecution:
    """QA-1 — Team can execute the plan in a controlled test environment."""

    def test_all_steps_executed_with_noop(self):
        proc = _simple_procedure(steps=4)
        report = _run(proc)
        assert len(report.step_results) == 4

    def test_drill_completes_with_status_completed(self):
        proc = _simple_procedure()
        report = _run(proc)
        assert report.status == RecoveryStatus.COMPLETED

    def test_step_result_has_completed_status(self):
        proc = _simple_procedure(steps=1)
        report = _run(proc)
        assert report.step_results[0].status == RecoveryStatus.COMPLETED

    def test_step_result_duration_recorded(self):
        proc = _simple_procedure(steps=1)
        report = _run(proc)
        assert report.step_results[0].duration_seconds >= 0

    def test_real_executors_invoked(self):
        proc = _simple_procedure(steps=2)
        called = []
        executors = {
            1: lambda: called.append(1),
            2: lambda: called.append(2),
        }
        _run(proc, executors)
        assert called == [1, 2]

    def test_drill_report_has_scenario_name(self):
        proc = _simple_procedure("my_scenario")
        report = _run(proc)
        assert report.scenario_name == "my_scenario"

    def test_drill_report_has_environment(self):
        proc = _simple_procedure()
        runner = DrillRunner()
        report = runner.run(DrillScenario(proc, {}, environment="staging"))
        assert report.environment == "staging"

    def test_total_duration_positive(self):
        proc = _simple_procedure(steps=2)
        report = _run(proc)
        assert report.total_duration_s >= 0

    def test_builtin_db_restore_procedure_executable(self):
        plan = build_propeliq_dr_plan()
        proc = plan.get_procedure("database_restore")
        assert proc is not None
        report = _run(proc)
        assert len(report.step_results) == proc.step_count()

    def test_stop_on_failure_aborts_after_first_failure(self):
        proc = _simple_procedure(steps=3)
        executors = {1: failing_executor("error")}
        runner = DrillRunner(stop_on_failure=True)
        report = runner.run(DrillScenario(proc, executors))
        # Only 1 step result since we stopped
        assert len(report.step_results) == 1

    def test_continue_on_failure_runs_all_steps(self):
        proc = _simple_procedure(steps=3)
        executors = {1: failing_executor("error")}
        runner = DrillRunner(stop_on_failure=False)
        report = runner.run(DrillScenario(proc, executors))
        assert len(report.step_results) == 3


# ===========================================================================
# QA-2: Findings Review (DOC-1)
# ===========================================================================


class TestFindingsReview:
    """QA-2 — Findings are documented completely."""

    def test_failed_step_generates_gap_finding(self):
        proc = _simple_procedure(steps=1)
        report = _run(proc, {1: failing_executor("disk full")})
        assert any(f.severity == FindingSeverity.GAP for f in report.findings)

    def test_gap_finding_contains_step_number(self):
        proc = _simple_procedure(steps=1)
        report = _run(proc, {1: failing_executor("err")})
        gap = report.findings[0]
        assert gap.step_number == 1

    def test_gap_finding_contains_scenario_name(self):
        proc = _simple_procedure("my_proc", steps=1)
        report = _run(proc, {1: failing_executor()})
        assert report.findings[0].scenario_name == "my_proc"

    def test_gap_finding_has_recommendation(self):
        proc = _simple_procedure(steps=1)
        report = _run(proc, {1: failing_executor()})
        assert report.findings[0].recommendation

    def test_clean_run_has_no_findings(self):
        proc = _simple_procedure(steps=3)
        report = _run(proc)
        assert report.finding_count() == 0

    def test_gap_count_counts_only_gaps(self):
        report = DrillReport("p", "test")
        report.add_finding(DrillFinding("p", 1, FindingSeverity.GAP, "gap1"))
        report.add_finding(DrillFinding("p", 2, FindingSeverity.WARNING, "warn1"))
        assert report.gap_count() == 1

    def test_finding_to_dict_has_expected_keys(self):
        f = DrillFinding("proc", 1, FindingSeverity.GAP, "desc", "fix it")
        d = f.to_dict()
        assert all(k in d for k in [
            "scenario_name", "step_number", "severity", "description",
            "recommendation", "recorded_at"
        ])

    def test_report_failed_steps_list(self):
        proc = _simple_procedure(steps=2)
        report = _run(proc, {1: failing_executor()})
        assert len(report.failed_steps()) == 1

    def test_step_result_error_captured(self):
        proc = _simple_procedure(steps=1)
        report = _run(proc, {1: failing_executor("specific error msg")})
        assert "specific error msg" in report.step_results[0].error

    def test_report_to_dict_has_expected_keys(self):
        report = _run(_simple_procedure())
        d = report.to_dict()
        assert all(k in d for k in [
            "scenario_name", "environment", "status", "total_duration_s",
            "rto_met", "finding_count", "gap_count", "step_results"
        ])


# ===========================================================================
# QA-3: Action Item Review (OPS-2)
# ===========================================================================


class TestActionItemReview:
    """QA-3 — Actionable remediation items are created from findings."""

    def test_action_items_created_from_gaps(self):
        proc = _simple_procedure(steps=1)
        report = _run(proc, {1: failing_executor()})
        plan = build_propeliq_dr_plan()
        registry = ActionItemRegistry()
        updater = PlanUpdater(plan)
        items = updater.apply(report, registry)
        assert len(items) >= 1

    def test_action_item_priority_critical_for_gap(self):
        proc = _simple_procedure(steps=1)
        report = _run(proc, {1: failing_executor()})
        plan = build_propeliq_dr_plan()
        registry = ActionItemRegistry()
        updater = PlanUpdater(plan)
        items = updater.apply(report, registry)
        gap_items = [i for i in items if i.priority == "critical"]
        assert len(gap_items) >= 1

    def test_action_item_priority_high_for_warning(self):
        report = DrillReport("proc", "test")
        report.add_finding(DrillFinding("proc", 1, FindingSeverity.WARNING, "slow step", "optimise"))
        plan = build_propeliq_dr_plan()
        registry = ActionItemRegistry()
        updater = PlanUpdater(plan)
        items = updater.apply(report, registry)
        warn_items = [i for i in items if i.priority == "high"]
        assert len(warn_items) >= 1

    def test_action_item_status_open_by_default(self):
        item = ActionItem("Fix step 1", "Step 1 failed")
        assert item.status == ActionItemStatus.OPEN

    def test_action_item_resolve(self):
        item = ActionItem("Fix", "desc")
        item.resolve()
        assert item.status == ActionItemStatus.RESOLVED

    def test_registry_stores_items(self):
        registry = ActionItemRegistry()
        registry.add(ActionItem("T1", "d1"))
        registry.add(ActionItem("T2", "d2"))
        assert registry.total_count() == 2

    def test_registry_open_items_filter(self):
        registry = ActionItemRegistry()
        item1 = ActionItem("T1", "d1")
        item2 = ActionItem("T2", "d2")
        item2.resolve()
        registry.add(item1)
        registry.add(item2)
        assert registry.open_count() == 1

    def test_registry_items_by_priority(self):
        registry = ActionItemRegistry()
        registry.add(ActionItem("T1", "d1", priority="critical"))
        registry.add(ActionItem("T2", "d2", priority="high"))
        assert len(registry.items_by_priority("critical")) == 1

    def test_action_item_to_dict_has_expected_keys(self):
        d = ActionItem("Fix step", "Description").to_dict()
        assert all(k in d for k in ["item_id", "title", "description", "priority", "status", "created_at"])

    def test_info_findings_do_not_generate_action_items(self):
        report = DrillReport("proc", "test")
        report.add_finding(DrillFinding("proc", 1, FindingSeverity.INFO, "observation"))
        plan = build_propeliq_dr_plan()
        registry = ActionItemRegistry()
        updater = PlanUpdater(plan)
        items = updater.apply(report, registry)
        assert len(items) == 0


# ===========================================================================
# QA-4: Plan Update Review (DOC-2)
# ===========================================================================


class TestPlanUpdateReview:
    """QA-4 — DR plan is updated after drill completion."""

    def test_apply_adds_lessons_to_plan(self):
        proc = _simple_procedure(steps=1)
        report = _run(proc, {1: failing_executor()})
        plan = build_propeliq_dr_plan()
        before_count = len(plan.lessons())
        PlanUpdater(plan).apply(report)
        assert len(plan.lessons()) > before_count

    def test_gap_lesson_severity_is_gap(self):
        proc = _simple_procedure(steps=1)
        report = _run(proc, {1: failing_executor()})
        plan = build_propeliq_dr_plan()
        PlanUpdater(plan).apply(report)
        gap_lessons = [n for n in plan.lessons() if n.severity == "gap"]
        assert len(gap_lessons) >= 1

    def test_plan_recorded_by_is_automated(self):
        proc = _simple_procedure(steps=1)
        report = _run(proc, {1: failing_executor()})
        plan = build_propeliq_dr_plan()
        PlanUpdater(plan).apply(report)
        automated_lessons = [n for n in plan.lessons() if "automated" in n.recorded_by.lower()]
        assert len(automated_lessons) >= 1

    def test_clean_drill_adds_no_lessons(self):
        proc = _simple_procedure(steps=3)
        report = _run(proc)
        plan = build_propeliq_dr_plan()
        PlanUpdater(plan).apply(report)
        assert len(plan.lessons()) == 0

    def test_plan_gap_count_updated_after_drill(self):
        proc = _simple_procedure(steps=1)
        report = _run(proc, {1: failing_executor()})
        plan = build_propeliq_dr_plan()
        PlanUpdater(plan).apply(report)
        assert plan.gap_count() >= 1

    def test_rto_measured_and_evaluated(self):
        proc = _simple_procedure(steps=2)
        runner = DrillRunner(objectives=RecoveryObjectives(rto_minutes=60))
        report = runner.run(DrillScenario(proc, {}))
        assert report.rto_met is True  # 2 noop steps complete in < 60 min

    def test_rto_not_met_when_exceeded(self):
        obj = RecoveryObjectives(rto_minutes=0)  # impossible RTO
        proc = _simple_procedure(steps=1)
        runner = DrillRunner(objectives=obj)
        report = runner.run(DrillScenario(proc, {}))
        assert report.rto_met is False

    def test_step_result_exceeded_estimate_flag(self):
        result = StepResult(
            step_number=1, description="slow step",
            status=RecoveryStatus.COMPLETED,
            duration_seconds=1000.0,
            estimated_seconds=10.0,
        )
        assert result.exceeded_estimate

    def test_step_result_within_estimate_flag(self):
        result = StepResult(
            step_number=1, description="fast step",
            status=RecoveryStatus.COMPLETED,
            duration_seconds=5.0,
            estimated_seconds=300.0,
        )
        assert not result.exceeded_estimate
