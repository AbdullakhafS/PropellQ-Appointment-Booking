"""
EP-008 US-095: Auto-Scaling Rules

INFRA-1  Scale-up policy — ``ScalingPolicy`` defines the metric thresholds that
         trigger proactive scale-up.  When CPU utilisation, request rate, or
         queue depth exceeds the configured high-water mark the
         ``AutoScaler.evaluate()`` method returns a ``ScaleDecision`` with
         action ``"scale_up"``.

INFRA-2  Scale-down policy — ``ScalingPolicy`` also carries minimum capacity
         and low-water marks.  The autoscaler never scales below
         ``min_instances``; a scale-down decision requires the load to drop
         below the low-water mark for a full cooldown window.

INFRA-3  Oscillation prevention — ``AutoScaler`` tracks the last scale event
         timestamp for both scale-up and scale-down actions.  A new decision
         in the same direction is suppressed until the respective cooldown
         (``scale_up_cooldown_seconds`` / ``scale_down_cooldown_seconds``)
         has elapsed.  This is the standard hysteresis mechanism that prevents
         thrashing on metrics that straddle the threshold.

DOC-1    Version-controlled policy documentation — ``PolicySnapshot`` captures
         the full policy configuration with a semantic version, author, and
         ISO-8601 timestamp so every policy change is self-documenting.
         ``PolicyRegistry`` stores the history of snapshots; the most recent
         is always the active policy.  This provides the audit trail needed
         for change-review and GitOps workflows.

Injectable backend pattern (mirrors EP-008 module family):
  ``FakeMetricsSource`` drives unit tests without network I/O.
  ``AutoScaler`` accepts any ``MetricsSourceProtocol`` implementation.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Protocol


# ---------------------------------------------------------------------------
# Constants (INFRA-1 / INFRA-2 / INFRA-3)
# ---------------------------------------------------------------------------

DEFAULT_MIN_INSTANCES: int = 2
DEFAULT_MAX_INSTANCES: int = 20
DEFAULT_SCALE_UP_CPU_THRESHOLD: float = 70.0    # % CPU → scale up
DEFAULT_SCALE_DOWN_CPU_THRESHOLD: float = 30.0  # % CPU → scale down
DEFAULT_SCALE_UP_COOLDOWN: float = 120.0         # seconds before another scale-up
DEFAULT_SCALE_DOWN_COOLDOWN: float = 300.0       # seconds before a scale-down
DEFAULT_SCALE_STEP: int = 1                       # instances added / removed per event
DEFAULT_EVALUATION_PERIODS: int = 2              # consecutive breaches before action


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class ScaleAction(str, Enum):
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    NO_CHANGE = "no_change"


class ScaleMetric(str, Enum):
    CPU_PERCENT = "cpu_percent"
    REQUESTS_PER_SECOND = "requests_per_second"
    QUEUE_DEPTH = "queue_depth"
    MEMORY_PERCENT = "memory_percent"


# ---------------------------------------------------------------------------
# INFRA-1 / INFRA-2: Scaling policy
# ---------------------------------------------------------------------------


@dataclass
class ScalingPolicy:
    """Defines when and how to scale compute resources (INFRA-1 / INFRA-2).

    Attributes
    ----------
    name                    Human-readable policy name.
    min_instances           Floor: never scale below this count.
    max_instances           Ceiling: never scale above this count.
    scale_up_threshold      Metric value that triggers a scale-up evaluation.
    scale_down_threshold    Metric value that triggers a scale-down evaluation.
    primary_metric          Which ``ScaleMetric`` drives this policy.
    scale_up_cooldown       Seconds to wait after a scale-up before the next.
    scale_down_cooldown     Seconds to wait after a scale-down before the next.
    scale_up_step           Instances to add per scale-up event.
    scale_down_step         Instances to remove per scale-down event.
    evaluation_periods      Consecutive breaches required before acting (INFRA-3).
    """

    name: str = "propeliq_default"
    min_instances: int = DEFAULT_MIN_INSTANCES
    max_instances: int = DEFAULT_MAX_INSTANCES
    scale_up_threshold: float = DEFAULT_SCALE_UP_CPU_THRESHOLD
    scale_down_threshold: float = DEFAULT_SCALE_DOWN_CPU_THRESHOLD
    primary_metric: ScaleMetric = ScaleMetric.CPU_PERCENT
    scale_up_cooldown: float = DEFAULT_SCALE_UP_COOLDOWN
    scale_down_cooldown: float = DEFAULT_SCALE_DOWN_COOLDOWN
    scale_up_step: int = DEFAULT_SCALE_STEP
    scale_down_step: int = DEFAULT_SCALE_STEP
    evaluation_periods: int = DEFAULT_EVALUATION_PERIODS

    def validate(self) -> list[str]:
        """Return a list of configuration problems (empty = valid)."""
        issues: list[str] = []
        if self.min_instances < 1:
            issues.append("min_instances must be >= 1")
        if self.max_instances < self.min_instances:
            issues.append("max_instances must be >= min_instances")
        if self.scale_up_threshold <= self.scale_down_threshold:
            issues.append("scale_up_threshold must be > scale_down_threshold")
        if self.scale_up_cooldown < 0:
            issues.append("scale_up_cooldown must be >= 0")
        if self.scale_down_cooldown < 0:
            issues.append("scale_down_cooldown must be >= 0")
        if self.scale_up_step < 1:
            issues.append("scale_up_step must be >= 1")
        if self.scale_down_step < 1:
            issues.append("scale_down_step must be >= 1")
        if self.evaluation_periods < 1:
            issues.append("evaluation_periods must be >= 1")
        return issues

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "min_instances": self.min_instances,
            "max_instances": self.max_instances,
            "scale_up_threshold": self.scale_up_threshold,
            "scale_down_threshold": self.scale_down_threshold,
            "primary_metric": self.primary_metric.value,
            "scale_up_cooldown": self.scale_up_cooldown,
            "scale_down_cooldown": self.scale_down_cooldown,
            "scale_up_step": self.scale_up_step,
            "scale_down_step": self.scale_down_step,
            "evaluation_periods": self.evaluation_periods,
        }


# ---------------------------------------------------------------------------
# DOC-1: Policy snapshot (version-controlled policy record)
# ---------------------------------------------------------------------------


@dataclass
class PolicySnapshot:
    """Immutable snapshot of a ``ScalingPolicy`` at a point in time (DOC-1).

    Attributes
    ----------
    policy          The captured policy configuration.
    version         Semantic version string (e.g. ``"1.0.0"``).
    author          Identity of who applied the change (email or service account).
    change_reason   Brief description of why the policy was changed.
    applied_at      ISO-8601 UTC timestamp.
    """

    policy: ScalingPolicy
    version: str
    author: str
    change_reason: str = ""
    applied_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "author": self.author,
            "change_reason": self.change_reason,
            "applied_at": self.applied_at,
            "policy": self.policy.to_dict(),
        }


class PolicyRegistry:
    """Maintains an ordered history of policy snapshots (DOC-1).

    The most recently pushed snapshot is the active policy.  Earlier
    snapshots are retained for audit and rollback purposes.

    Usage::

        registry = PolicyRegistry()
        registry.push(PolicySnapshot(policy, "1.0.0", "sre-team@propeliq.com"))
        active = registry.active_policy()
    """

    def __init__(self) -> None:
        self._history: list[PolicySnapshot] = []

    def push(self, snapshot: PolicySnapshot) -> None:
        self._history.append(snapshot)

    def active_policy(self) -> ScalingPolicy | None:
        if not self._history:
            return None
        return self._history[-1].policy

    def active_snapshot(self) -> PolicySnapshot | None:
        return self._history[-1] if self._history else None

    def history(self) -> list[PolicySnapshot]:
        return list(self._history)

    def rollback(self) -> PolicySnapshot | None:
        """Remove and return the most recent snapshot (revert to previous)."""
        if not self._history:
            return None
        return self._history.pop()

    def version_count(self) -> int:
        return len(self._history)


# ---------------------------------------------------------------------------
# Metrics protocol and fake
# ---------------------------------------------------------------------------


@dataclass
class MetricSample:
    """A single metric reading at a point in time."""

    metric: ScaleMetric
    value: float
    sampled_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class MetricsSourceProtocol(Protocol):
    """Injectable metrics source (cloud watch, Prometheus, test fake)."""

    def current(self, metric: ScaleMetric) -> float: ...


class FakeMetricsSource:
    """Controllable metrics source for unit tests."""

    def __init__(self, values: dict[ScaleMetric, float] | None = None) -> None:
        self._values: dict[ScaleMetric, float] = values or {}

    def set(self, metric: ScaleMetric, value: float) -> None:
        self._values[metric] = value

    def current(self, metric: ScaleMetric) -> float:
        return self._values.get(metric, 0.0)


# ---------------------------------------------------------------------------
# Scale decision
# ---------------------------------------------------------------------------


@dataclass
class ScaleDecision:
    """Output of one ``AutoScaler.evaluate()`` call.

    Attributes
    ----------
    action              What the autoscaler decided to do.
    current_instances   Instance count at decision time.
    target_instances    Desired instance count after applying the decision.
    metric_value        The metric reading that drove the decision.
    reason              Human-readable explanation.
    suppressed          True when a scale event was warranted but held back
                        by the cooldown (INFRA-3).
    decided_at          ISO-8601 UTC timestamp.
    """

    action: ScaleAction
    current_instances: int
    target_instances: int
    metric_value: float
    reason: str
    suppressed: bool = False
    decided_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action.value,
            "current_instances": self.current_instances,
            "target_instances": self.target_instances,
            "metric_value": round(self.metric_value, 2),
            "reason": self.reason,
            "suppressed": self.suppressed,
            "decided_at": self.decided_at,
        }


# ---------------------------------------------------------------------------
# INFRA-1 / INFRA-2 / INFRA-3: AutoScaler
# ---------------------------------------------------------------------------


class AutoScaler:
    """Evaluates current metrics against policy and emits scaling decisions.

    Oscillation prevention (INFRA-3)
    ---------------------------------
    The autoscaler maintains a breach counter per direction.  An action is
    only triggered when the breach counter reaches ``policy.evaluation_periods``
    (multiple consecutive evaluations all breach the threshold).  This
    prevents a single spike from triggering unnecessary scaling.

    Cooldowns suppress the *action* (scale-up or scale-down) until the
    configured wall-clock wait has elapsed after the last event of that type.
    The decision is still returned but marked ``suppressed=True`` so callers
    can observe it without acting.

    Usage::

        metrics  = FakeMetricsSource({ScaleMetric.CPU_PERCENT: 85.0})
        scaler   = AutoScaler(policy, metrics, current_instances=3)
        decision = scaler.evaluate()   # → ScaleDecision(action=SCALE_UP, …)
    """

    def __init__(
        self,
        policy: ScalingPolicy,
        metrics: MetricsSourceProtocol,
        current_instances: int | None = None,
    ) -> None:
        self._policy = policy
        self._metrics = metrics
        self._instances = current_instances if current_instances is not None else policy.min_instances
        self._last_scale_up: float = 0.0
        self._last_scale_down: float = 0.0
        self._up_breach_count: int = 0
        self._down_breach_count: int = 0
        self._decision_log: list[ScaleDecision] = []

    @property
    def current_instances(self) -> int:
        return self._instances

    @property
    def policy(self) -> ScalingPolicy:
        return self._policy

    def update_policy(self, new_policy: ScalingPolicy) -> None:
        self._policy = new_policy

    def evaluate(self) -> ScaleDecision:
        """Read current metrics, apply policy, and return a scaling decision."""
        p = self._policy
        value = self._metrics.current(p.primary_metric)
        now = time.monotonic()

        if value >= p.scale_up_threshold:
            self._up_breach_count += 1
            self._down_breach_count = 0
            if self._up_breach_count >= p.evaluation_periods:
                return self._maybe_scale_up(value, now)
            return ScaleDecision(
                action=ScaleAction.NO_CHANGE,
                current_instances=self._instances,
                target_instances=self._instances,
                metric_value=value,
                reason=f"Breach {self._up_breach_count}/{p.evaluation_periods} — waiting for sustained breach",
            )

        elif value <= p.scale_down_threshold:
            self._down_breach_count += 1
            self._up_breach_count = 0
            if self._down_breach_count >= p.evaluation_periods:
                return self._maybe_scale_down(value, now)
            return ScaleDecision(
                action=ScaleAction.NO_CHANGE,
                current_instances=self._instances,
                target_instances=self._instances,
                metric_value=value,
                reason=f"Breach {self._down_breach_count}/{p.evaluation_periods} — waiting for sustained breach",
            )

        else:
            self._up_breach_count = 0
            self._down_breach_count = 0
            return ScaleDecision(
                action=ScaleAction.NO_CHANGE,
                current_instances=self._instances,
                target_instances=self._instances,
                metric_value=value,
                reason=f"Metric {value:.1f} within normal band [{p.scale_down_threshold}, {p.scale_up_threshold}]",
            )

    def _maybe_scale_up(self, value: float, now: float) -> ScaleDecision:
        p = self._policy
        target = min(self._instances + p.scale_up_step, p.max_instances)
        in_cooldown = (now - self._last_scale_up) < p.scale_up_cooldown
        if in_cooldown:
            return ScaleDecision(
                action=ScaleAction.SCALE_UP,
                current_instances=self._instances,
                target_instances=self._instances,
                metric_value=value,
                reason=f"Scale-up warranted but in cooldown ({p.scale_up_cooldown}s)",
                suppressed=True,
            )
        self._last_scale_up = now
        self._up_breach_count = 0
        self._instances = target
        d = ScaleDecision(
            action=ScaleAction.SCALE_UP,
            current_instances=self._instances - p.scale_up_step,
            target_instances=self._instances,
            metric_value=value,
            reason=f"CPU/metric {value:.1f} >= threshold {p.scale_up_threshold}",
        )
        self._decision_log.append(d)
        return d

    def _maybe_scale_down(self, value: float, now: float) -> ScaleDecision:
        p = self._policy
        target = max(self._instances - p.scale_down_step, p.min_instances)
        in_cooldown = (now - self._last_scale_down) < p.scale_down_cooldown
        if in_cooldown:
            return ScaleDecision(
                action=ScaleAction.SCALE_DOWN,
                current_instances=self._instances,
                target_instances=self._instances,
                metric_value=value,
                reason=f"Scale-down warranted but in cooldown ({p.scale_down_cooldown}s)",
                suppressed=True,
            )
        self._last_scale_down = now
        self._down_breach_count = 0
        self._instances = target
        d = ScaleDecision(
            action=ScaleAction.SCALE_DOWN,
            current_instances=self._instances + p.scale_down_step,
            target_instances=self._instances,
            metric_value=value,
            reason=f"CPU/metric {value:.1f} <= threshold {p.scale_down_threshold}",
        )
        self._decision_log.append(d)
        return d

    def decision_log(self) -> list[ScaleDecision]:
        """Return a copy of all actioned (non-suppressed) scaling decisions."""
        return list(self._decision_log)

    def stats(self) -> dict[str, Any]:
        return {
            "current_instances": self._instances,
            "policy_name": self._policy.name,
            "up_breach_count": self._up_breach_count,
            "down_breach_count": self._down_breach_count,
            "total_decisions": len(self._decision_log),
        }


# ---------------------------------------------------------------------------
# Convenience: build a no-cooldown test scaler
# ---------------------------------------------------------------------------


def make_test_scaler(
    min_instances: int = 2,
    max_instances: int = 10,
    scale_up_threshold: float = 70.0,
    scale_down_threshold: float = 30.0,
    evaluation_periods: int = 1,
    current_instances: int = 3,
) -> tuple[AutoScaler, FakeMetricsSource]:
    """Return a (scaler, metrics) pair suitable for unit tests.

    Cooldowns are set to 0 so tests don't need to sleep.
    Evaluation periods default to 1 for immediate decisions.
    """
    metrics = FakeMetricsSource()
    policy = ScalingPolicy(
        name="test_policy",
        min_instances=min_instances,
        max_instances=max_instances,
        scale_up_threshold=scale_up_threshold,
        scale_down_threshold=scale_down_threshold,
        scale_up_cooldown=0.0,
        scale_down_cooldown=0.0,
        evaluation_periods=evaluation_periods,
    )
    scaler = AutoScaler(policy, metrics, current_instances=current_instances)
    return scaler, metrics
