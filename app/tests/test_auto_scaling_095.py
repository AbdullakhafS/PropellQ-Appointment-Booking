"""
EP-008 US-095: Auto-Scaling Rules — Test Suite

QA-1  Scale-Up Tests         — resources scale up before user-facing degradation
QA-2  Scale-Down Tests       — safe contraction under lower traffic
QA-3  Stability Tests        — no oscillation under fluctuating load
QA-4  Policy Governance Tests — changes documented and version-controlled
"""
from __future__ import annotations

import pytest

from src.auto_scaling import (
    DEFAULT_MAX_INSTANCES,
    DEFAULT_MIN_INSTANCES,
    DEFAULT_SCALE_DOWN_COOLDOWN,
    DEFAULT_SCALE_UP_COOLDOWN,
    AutoScaler,
    FakeMetricsSource,
    PolicyRegistry,
    PolicySnapshot,
    ScaleAction,
    ScaleMetric,
    ScalingPolicy,
    make_test_scaler,
)


# ===========================================================================
# QA-1: Scale-Up Tests (INFRA-1)
# ===========================================================================


class TestScaleUp:
    """QA-1 — Resources scale up before user-facing degradation."""

    def test_scale_up_when_metric_exceeds_threshold(self):
        scaler, metrics = make_test_scaler(scale_up_threshold=70.0, current_instances=3)
        metrics.set(ScaleMetric.CPU_PERCENT, 85.0)
        decision = scaler.evaluate()
        assert decision.action == ScaleAction.SCALE_UP

    def test_scale_up_increments_instance_count(self):
        scaler, metrics = make_test_scaler(current_instances=3)
        metrics.set(ScaleMetric.CPU_PERCENT, 85.0)
        scaler.evaluate()
        assert scaler.current_instances == 4

    def test_scale_up_respects_max_instances(self):
        scaler, metrics = make_test_scaler(max_instances=4, current_instances=4)
        metrics.set(ScaleMetric.CPU_PERCENT, 90.0)
        decision = scaler.evaluate()
        assert decision.target_instances == 4  # capped at max

    def test_no_scale_when_metric_in_band(self):
        scaler, metrics = make_test_scaler(
            scale_up_threshold=70.0, scale_down_threshold=30.0, current_instances=3
        )
        metrics.set(ScaleMetric.CPU_PERCENT, 50.0)
        decision = scaler.evaluate()
        assert decision.action == ScaleAction.NO_CHANGE

    def test_scale_up_decision_contains_correct_fields(self):
        scaler, metrics = make_test_scaler(current_instances=3)
        metrics.set(ScaleMetric.CPU_PERCENT, 85.0)
        d = scaler.evaluate()
        assert d.current_instances == 3
        assert d.target_instances == 4
        assert d.metric_value == 85.0

    def test_scale_up_logged_in_decision_log(self):
        scaler, metrics = make_test_scaler()
        metrics.set(ScaleMetric.CPU_PERCENT, 85.0)
        scaler.evaluate()
        assert len(scaler.decision_log()) == 1

    def test_scale_up_decision_to_dict(self):
        scaler, metrics = make_test_scaler()
        metrics.set(ScaleMetric.CPU_PERCENT, 85.0)
        d = scaler.evaluate()
        dd = d.to_dict()
        assert all(k in dd for k in ["action", "current_instances", "target_instances", "metric_value", "reason"])

    def test_evaluation_periods_delays_action(self):
        scaler, metrics = make_test_scaler(evaluation_periods=2)
        metrics.set(ScaleMetric.CPU_PERCENT, 85.0)
        d1 = scaler.evaluate()   # breach 1 — no action yet
        assert d1.action == ScaleAction.NO_CHANGE
        d2 = scaler.evaluate()   # breach 2 — action taken
        assert d2.action == ScaleAction.SCALE_UP


# ===========================================================================
# QA-2: Scale-Down Tests (INFRA-2)
# ===========================================================================


class TestScaleDown:
    """QA-2 — Safe contraction under lower traffic."""

    def test_scale_down_when_metric_below_threshold(self):
        scaler, metrics = make_test_scaler(
            scale_down_threshold=30.0, current_instances=5
        )
        metrics.set(ScaleMetric.CPU_PERCENT, 15.0)
        decision = scaler.evaluate()
        assert decision.action == ScaleAction.SCALE_DOWN

    def test_scale_down_decrements_instance_count(self):
        scaler, metrics = make_test_scaler(current_instances=5)
        metrics.set(ScaleMetric.CPU_PERCENT, 15.0)
        scaler.evaluate()
        assert scaler.current_instances == 4

    def test_scale_down_respects_min_instances(self):
        scaler, metrics = make_test_scaler(min_instances=2, current_instances=2)
        metrics.set(ScaleMetric.CPU_PERCENT, 10.0)
        decision = scaler.evaluate()
        assert decision.target_instances == 2  # capped at min

    def test_scale_down_not_below_min(self):
        scaler, metrics = make_test_scaler(min_instances=2, current_instances=2)
        metrics.set(ScaleMetric.CPU_PERCENT, 5.0)
        scaler.evaluate()
        assert scaler.current_instances >= 2

    def test_scale_down_logged_in_decision_log(self):
        scaler, metrics = make_test_scaler(current_instances=5)
        metrics.set(ScaleMetric.CPU_PERCENT, 10.0)
        scaler.evaluate()
        assert any(d.action == ScaleAction.SCALE_DOWN for d in scaler.decision_log())

    def test_default_min_instances_constant(self):
        assert DEFAULT_MIN_INSTANCES == 2

    def test_default_max_instances_constant(self):
        assert DEFAULT_MAX_INSTANCES == 20


# ===========================================================================
# QA-3: Stability / Oscillation Tests (INFRA-3)
# ===========================================================================


class TestStabilityOscillation:
    """QA-3 — No oscillation under fluctuating load."""

    def test_scale_up_suppressed_during_cooldown(self):
        policy = ScalingPolicy(
            scale_up_threshold=70.0, scale_down_threshold=30.0,
            scale_up_cooldown=9999.0, scale_down_cooldown=0.0,
            evaluation_periods=1,
        )
        metrics = FakeMetricsSource({ScaleMetric.CPU_PERCENT: 85.0})
        scaler = AutoScaler(policy, metrics, current_instances=3)
        scaler.evaluate()          # first scale-up fires
        d = scaler.evaluate()      # should be suppressed
        assert d.suppressed is True

    def test_scale_down_suppressed_during_cooldown(self):
        policy = ScalingPolicy(
            scale_up_threshold=70.0, scale_down_threshold=30.0,
            scale_up_cooldown=0.0, scale_down_cooldown=9999.0,
            evaluation_periods=1,
        )
        metrics = FakeMetricsSource({ScaleMetric.CPU_PERCENT: 10.0})
        scaler = AutoScaler(policy, metrics, current_instances=5)
        scaler.evaluate()
        d = scaler.evaluate()      # should be suppressed
        assert d.suppressed is True

    def test_suppressed_decision_does_not_change_instance_count(self):
        policy = ScalingPolicy(
            scale_up_threshold=70.0, scale_down_threshold=30.0,
            scale_up_cooldown=9999.0, scale_down_cooldown=0.0,
            evaluation_periods=1,
        )
        metrics = FakeMetricsSource({ScaleMetric.CPU_PERCENT: 85.0})
        scaler = AutoScaler(policy, metrics, current_instances=3)
        scaler.evaluate()   # fires
        before = scaler.current_instances
        scaler.evaluate()   # suppressed
        assert scaler.current_instances == before

    def test_breach_counter_resets_after_normal_metric(self):
        scaler, metrics = make_test_scaler(evaluation_periods=3)
        metrics.set(ScaleMetric.CPU_PERCENT, 85.0)
        scaler.evaluate()  # breach 1
        scaler.evaluate()  # breach 2
        # Reset with normal metric
        metrics.set(ScaleMetric.CPU_PERCENT, 50.0)
        scaler.evaluate()  # counter resets
        # Now needs 3 consecutive breaches again
        metrics.set(ScaleMetric.CPU_PERCENT, 85.0)
        d = scaler.evaluate()  # breach 1 again
        assert d.action == ScaleAction.NO_CHANGE

    def test_evaluation_periods_prevents_single_spike_scale(self):
        scaler, metrics = make_test_scaler(evaluation_periods=3)
        metrics.set(ScaleMetric.CPU_PERCENT, 90.0)
        d1 = scaler.evaluate()
        d2 = scaler.evaluate()
        assert d1.action == ScaleAction.NO_CHANGE
        assert d2.action == ScaleAction.NO_CHANGE

    def test_stats_reflect_current_state(self):
        scaler, metrics = make_test_scaler(current_instances=5)
        s = scaler.stats()
        assert s["current_instances"] == 5
        assert "policy_name" in s

    def test_policy_validation_passes_on_valid(self):
        p = ScalingPolicy()
        assert p.validate() == []

    def test_policy_validation_fails_on_invalid_thresholds(self):
        p = ScalingPolicy(scale_up_threshold=20.0, scale_down_threshold=30.0)
        issues = p.validate()
        assert any("scale_up_threshold" in i for i in issues)

    def test_policy_validation_fails_on_invalid_min_max(self):
        p = ScalingPolicy(min_instances=10, max_instances=5)
        issues = p.validate()
        assert any("max_instances" in i for i in issues)


# ===========================================================================
# QA-4: Policy Governance Tests (DOC-1)
# ===========================================================================


class TestPolicyGovernance:
    """QA-4 — Policy changes are documented and version-controlled."""

    def test_policy_registry_stores_snapshot(self):
        registry = PolicyRegistry()
        policy = ScalingPolicy()
        snap = PolicySnapshot(policy, "1.0.0", "sre@propeliq.com")
        registry.push(snap)
        assert registry.version_count() == 1

    def test_registry_active_policy_returns_latest(self):
        registry = PolicyRegistry()
        p1 = ScalingPolicy(name="v1", scale_up_threshold=70.0, scale_down_threshold=30.0)
        p2 = ScalingPolicy(name="v2", scale_up_threshold=80.0, scale_down_threshold=20.0)
        registry.push(PolicySnapshot(p1, "1.0.0", "alice"))
        registry.push(PolicySnapshot(p2, "2.0.0", "bob"))
        assert registry.active_policy().name == "v2"

    def test_registry_history_preserved(self):
        registry = PolicyRegistry()
        for v in ["1.0.0", "1.1.0", "2.0.0"]:
            registry.push(PolicySnapshot(ScalingPolicy(), v, "sre"))
        assert registry.version_count() == 3

    def test_registry_rollback_removes_latest(self):
        registry = PolicyRegistry()
        registry.push(PolicySnapshot(ScalingPolicy(name="v1"), "1.0.0", "sre"))
        registry.push(PolicySnapshot(ScalingPolicy(name="v2"), "2.0.0", "sre"))
        registry.rollback()
        assert registry.active_policy().name == "v1"

    def test_registry_empty_active_policy_returns_none(self):
        assert PolicyRegistry().active_policy() is None

    def test_snapshot_to_dict_has_expected_keys(self):
        snap = PolicySnapshot(ScalingPolicy(), "1.0.0", "alice", "Initial config")
        d = snap.to_dict()
        assert all(k in d for k in ["version", "author", "change_reason", "applied_at", "policy"])

    def test_policy_to_dict_has_expected_keys(self):
        d = ScalingPolicy().to_dict()
        assert all(k in d for k in [
            "name", "min_instances", "max_instances",
            "scale_up_threshold", "scale_down_threshold",
            "scale_up_cooldown", "scale_down_cooldown", "evaluation_periods",
        ])

    def test_snapshot_author_recorded(self):
        snap = PolicySnapshot(ScalingPolicy(), "1.0.0", "sre-team@propeliq.com")
        assert snap.author == "sre-team@propeliq.com"

    def test_scaler_update_policy_changes_thresholds(self):
        scaler, metrics = make_test_scaler(scale_up_threshold=70.0)
        new_policy = ScalingPolicy(
            scale_up_threshold=60.0, scale_down_threshold=20.0,
            scale_up_cooldown=0.0, scale_down_cooldown=0.0, evaluation_periods=1
        )
        scaler.update_policy(new_policy)
        metrics.set(ScaleMetric.CPU_PERCENT, 65.0)
        d = scaler.evaluate()
        assert d.action == ScaleAction.SCALE_UP

    def test_default_cooldown_constants(self):
        assert DEFAULT_SCALE_UP_COOLDOWN == 120.0
        assert DEFAULT_SCALE_DOWN_COOLDOWN == 300.0
