"""
EP-008 US-085: Automated Health Checks

BE-1   Liveness and readiness endpoints are already wired in web_app.py (US-083).
       This module provides the domain objects that back those endpoints.

BE-2   StartupGate — prevents readiness from passing until all registered
       critical dependencies have produced at least one passing probe result.
       The module-level ``_STARTUP_GATE`` singleton is imported by web_app.py;
       add dependency probes at application startup before serving traffic.

INFRA-1 Integration with LB is via the /health/ready HTTP response (503 when
        not ready); the LoadBalancerPool.run_health_checks() calls the endpoint
        and drives BackendInstance.mark_unhealthy().

OPS-1  HealthCheckAlerter — fires an alert after ``failure_threshold``
       consecutive failures for a named probe.  Wire an ``AlertSinkProtocol``
       implementation (PagerDuty, CloudWatch, Slack) in production.

DOC-1  See HEALTH_CHECK_ENDPOINTS.md for endpoint semantics and consumer guide.

--- Endpoint Behaviour Summary (DOC-1) ---

  GET /health/live
    ├─ Returns 200 always (as long as Python process can handle HTTP)
    ├─ Payload: {"status": "alive", "checked_at": "<iso8601>"}
    └─ Consumer: Container runtime / orchestrator liveness probe

  GET /health/ready
    ├─ Returns 200 when database and all StartupGate probes pass
    ├─ Returns 503 when any dependency is unavailable
    ├─ Payload: {"status": "ready"|"not_ready", "checks": {...}}
    └─ Consumer: Load balancer (removes instance from pool on 503)
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Protocol

# ---------------------------------------------------------------------------
# Constants (OPS-1)
# ---------------------------------------------------------------------------

HEALTH_CHECK_FAILURE_THRESHOLD: int = 3   # consecutive failures before alerting
HEALTH_CHECK_PROBE_TIMEOUT_MS: float = 2000.0  # max expected probe duration


# ---------------------------------------------------------------------------
# Probe status / result
# ---------------------------------------------------------------------------


class ProbeStatus(str, Enum):
    PASSING = "passing"
    FAILING = "failing"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a single health probe execution.

    Attributes
    ----------
    probe_name   Unique name identifying the probe.
    status       PASSING / FAILING / UNKNOWN.
    message      Human-readable detail (dependency name, error message, etc.).
    checked_at   ISO-8601 UTC timestamp when the probe ran.
    latency_ms   How long the probe took in milliseconds.
    """

    probe_name: str
    status: ProbeStatus
    message: str
    checked_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    latency_ms: float = 0.0

    @property
    def is_passing(self) -> bool:
        return self.status == ProbeStatus.PASSING


# ---------------------------------------------------------------------------
# Probe implementations
# ---------------------------------------------------------------------------


class HealthProbeProtocol(Protocol):
    """Injectable health probe interface.

    Implement this to define a custom readiness / liveness check.
    Production: database ping, cache ping, upstream service check.
    Tests: ``AlwaysPassingProbe``, ``AlwaysFailingProbe``, ``FunctionProbe``.
    """

    def run(self) -> HealthCheckResult:
        """Execute the check and return a result."""
        ...


class FunctionProbe:
    """Wraps a zero-argument callable ``() -> bool`` as a ``HealthProbeProtocol``.

    The callable should return True on success and False (or raise) on failure.
    Raised exceptions are caught and reported as FAILING.

    Example::

        db_probe = FunctionProbe("database", lambda: db_ping())
        registry.register("database", db_probe)
    """

    def __init__(
        self,
        name: str,
        fn: Callable[[], bool],
        ok_message: str = "ok",
        fail_message: str = "check failed",
    ) -> None:
        self.name = name
        self._fn = fn
        self._ok = ok_message
        self._fail = fail_message

    def run(self) -> HealthCheckResult:
        start = time.monotonic()
        try:
            ok = bool(self._fn())
            message = self._ok if ok else self._fail
        except Exception as exc:  # noqa: BLE001 — probe must never crash the caller
            ok = False
            message = str(exc)
        latency = (time.monotonic() - start) * 1000.0
        return HealthCheckResult(
            probe_name=self.name,
            status=ProbeStatus.PASSING if ok else ProbeStatus.FAILING,
            message=message,
            latency_ms=latency,
        )


class AlwaysPassingProbe:
    """Probe that always reports PASSING. Useful as a test double or placeholder."""

    def __init__(self, name: str) -> None:
        self.name = name

    def run(self) -> HealthCheckResult:
        return HealthCheckResult(
            probe_name=self.name,
            status=ProbeStatus.PASSING,
            message="always ok",
        )


class AlwaysFailingProbe:
    """Probe that always reports FAILING. Useful for testing alert thresholds."""

    def __init__(self, name: str, message: str = "always failing") -> None:
        self.name = name
        self._message = message

    def run(self) -> HealthCheckResult:
        return HealthCheckResult(
            probe_name=self.name,
            status=ProbeStatus.FAILING,
            message=self._message,
        )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class HealthProbeRegistry:
    """Manages a named set of health probes and executes them on demand.

    Each probe is identified by a unique string name.  Probes can be added
    or removed at runtime (e.g., as services come online during startup).

    Usage::

        registry = HealthProbeRegistry()
        registry.register("database", FunctionProbe("database", db_ping))
        results = registry.run_all()  # {"database": HealthCheckResult(...)}
    """

    def __init__(self) -> None:
        self._probes: dict[str, HealthProbeProtocol] = {}

    def register(self, name: str, probe: HealthProbeProtocol) -> None:
        """Register or replace a named probe."""
        self._probes[name] = probe

    def unregister(self, name: str) -> None:
        """Remove a probe by name. No-op if not registered."""
        self._probes.pop(name, None)

    def run_all(self) -> dict[str, HealthCheckResult]:
        """Execute every registered probe and return results keyed by name."""
        return {name: probe.run() for name, probe in self._probes.items()}

    def run_one(self, name: str) -> HealthCheckResult:
        """Execute a single named probe.

        Raises ``KeyError`` if the probe is not registered.
        """
        probe = self._probes.get(name)
        if probe is None:
            raise KeyError(f"No probe registered with name {name!r}")
        return probe.run()

    @property
    def probe_names(self) -> list[str]:
        return list(self._probes.keys())

    def __len__(self) -> int:
        return len(self._probes)


# ---------------------------------------------------------------------------
# BE-2: Startup gate
# ---------------------------------------------------------------------------


class StartupGate:
    """Prevents readiness from passing until all registered dependencies are available.

    Designed to be held as a module-level singleton (``_STARTUP_GATE``) that
    ``web_app.py`` checks on every ``GET /health/ready`` request.

    An empty gate (no probes registered) is always ready.  This allows the
    gate to be used as an opt-in extension without requiring every deployment
    to register probes upfront.

    Usage::

        _STARTUP_GATE.add_dependency("database", db_probe)
        _STARTUP_GATE.add_dependency("cache", cache_probe)

        if _STARTUP_GATE.is_ready():
            # serve traffic — all critical dependencies available
    """

    def __init__(self) -> None:
        self._probes: dict[str, HealthProbeProtocol] = {}
        self._last_results: dict[str, HealthCheckResult] = {}

    def add_dependency(self, name: str, probe: HealthProbeProtocol) -> None:
        """Register a critical dependency probe."""
        self._probes[name] = probe

    def remove_dependency(self, name: str) -> None:
        """Unregister a dependency probe. No-op if not present."""
        self._probes.pop(name, None)
        self._last_results.pop(name, None)

    def is_ready(self) -> bool:
        """Run all dependency probes; return True only if every probe passes.

        An empty gate returns True immediately (no probes = no blockers).
        """
        if not self._probes:
            return True
        all_pass = True
        for name, probe in self._probes.items():
            result = probe.run()
            self._last_results[name] = result
            if not result.is_passing:
                all_pass = False
        return all_pass

    def dependencies_status(self) -> dict[str, str]:
        """Return last recorded status value per dependency name."""
        return {name: r.status.value for name, r in self._last_results.items()}

    def check_results(self) -> dict[str, HealthCheckResult]:
        """Return a copy of last probe results."""
        return dict(self._last_results)

    def clear(self) -> None:
        """Remove all registered dependencies (useful between tests)."""
        self._probes.clear()
        self._last_results.clear()


# ---------------------------------------------------------------------------
# OPS-1: Alerting
# ---------------------------------------------------------------------------


class AlertSinkProtocol(Protocol):
    """Injectable sink for health check failure alerts.

    Production implementations push to PagerDuty, CloudWatch Alarms, or Slack.
    Tests and local development use ``InMemoryAlertSink``.
    """

    def emit_alert(
        self, probe_name: str, failure_count: int, last_result: HealthCheckResult
    ) -> None:
        """Receive and dispatch an alert for a probe that has reached its threshold."""
        ...


class InMemoryAlertSink:
    """Captures emitted alerts in a list for inspection in tests."""

    def __init__(self) -> None:
        self._alerts: list[dict[str, Any]] = []

    def emit_alert(
        self, probe_name: str, failure_count: int, last_result: HealthCheckResult
    ) -> None:
        self._alerts.append(
            {
                "probe_name": probe_name,
                "failure_count": failure_count,
                "status": last_result.status.value,
                "message": last_result.message,
                "alerted_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    @property
    def alerts(self) -> list[dict[str, Any]]:
        return list(self._alerts)

    def clear(self) -> None:
        self._alerts.clear()


class HealthCheckAlerter:
    """Tracks consecutive probe failures and fires alerts after a threshold (OPS-1).

    A single alert is fired when the failure count first reaches
    ``failure_threshold``, and again on each subsequent failure (not
    de-duplicated — each call to ``record_result`` with a failing result
    produces an alert once the threshold is reached).

    An alert is resolved (active flag cleared) when a passing result is
    recorded.  The failure counter also resets to 0 on resolution.

    Attributes
    ----------
    failure_threshold   Consecutive failures before an alert is emitted.
    sink                Destination for emitted alerts.
    """

    def __init__(
        self,
        failure_threshold: int = HEALTH_CHECK_FAILURE_THRESHOLD,
        sink: AlertSinkProtocol | None = None,
    ) -> None:
        self._threshold = failure_threshold
        self._sink: AlertSinkProtocol = sink or InMemoryAlertSink()
        self._failure_counts: dict[str, int] = {}
        self._active_alerts: dict[str, bool] = {}

    def record_result(self, probe_name: str, result: HealthCheckResult) -> bool:
        """Process a result; returns True if an alert was fired this call.

        Pass results from ``HealthProbeRegistry.run_all()`` or ``run_one()``
        to drive the alerting logic.
        """
        if result.is_passing:
            self._failure_counts[probe_name] = 0
            self._active_alerts[probe_name] = False
            return False

        count = self._failure_counts.get(probe_name, 0) + 1
        self._failure_counts[probe_name] = count
        if count >= self._threshold:
            self._active_alerts[probe_name] = True
            self._sink.emit_alert(probe_name, count, result)
            return True
        return False

    def get_active_alerts(self) -> list[str]:
        """Return names of probes with active (un-resolved) alerts."""
        return [name for name, active in self._active_alerts.items() if active]

    def failure_count(self, probe_name: str) -> int:
        """Return the current consecutive failure count for a probe."""
        return self._failure_counts.get(probe_name, 0)

    def clear_alert(self, probe_name: str) -> None:
        """Manually resolve an alert and reset its failure counter."""
        self._active_alerts[probe_name] = False
        self._failure_counts[probe_name] = 0

    @property
    def sink(self) -> AlertSinkProtocol:
        return self._sink


# ---------------------------------------------------------------------------
# Module-level singleton (BE-2)
# ---------------------------------------------------------------------------

_STARTUP_GATE: StartupGate = StartupGate()
"""Module-level startup gate imported by web_app.py.

Register critical dependencies at application startup before serving traffic::

    from src.health_checks import _STARTUP_GATE, FunctionProbe
    _STARTUP_GATE.add_dependency("database", FunctionProbe("database", check_db))

The empty default gate always returns True, so unmodified deployments are
unaffected.
"""
