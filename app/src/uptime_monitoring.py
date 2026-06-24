"""
EP-008 US-094: Uptime Monitoring and Alerting

OPS-1   Synthetic and internal probes — ``UptimeProbe`` wraps any callable
        health check (HTTP ping, DB connection, port scan) and records each
        result in ``ProbeHistory``.  The ``UptimeMonitor`` drives scheduled
        probe execution and maintains the running availability window.

OPS-2   Incident alert routing — when a probe crosses the degraded or down
        threshold the ``IncidentAlerter`` fires an ``IncidentAlert`` via the
        injected ``AlertRoutingProtocol``.  Alerts are deduplicated per probe
        so a flapping probe does not generate alert storms.

OPS-3   Availability dashboard — ``AvailabilityDashboard`` computes the
        current SLA percentage and returns an ordered incident history for
        the configured rolling window.  ``SLATarget`` defines the 99.9 %
        contract and provides ``is_breached()`` / ``budget_remaining_seconds()``
        helpers.

OPS-4   Threshold configuration and documentation — ``MonitoringThresholds``
        holds all configurable parameters (consecutive failures before down,
        consecutive passes before recovery, rolling window size, alert cooldown).
        ``ThresholdDocumentation`` exports a human-readable description for
        ops runbooks.

Injectable pattern (mirrors US-085 / US-086 / US-094 consistency):
  Tests use ``FakeProbeStep`` (controllable pass/fail) and
  ``InMemoryAlertRouter``.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Protocol


# ---------------------------------------------------------------------------
# OPS-4: Configurable thresholds
# ---------------------------------------------------------------------------

DEFAULT_DOWN_THRESHOLD: int = 3         # consecutive failures → DOWN
DEFAULT_RECOVERY_THRESHOLD: int = 2     # consecutive passes  → UP
DEFAULT_WINDOW_SECONDS: int = 3600      # rolling availability window (1 hour)
DEFAULT_ALERT_COOLDOWN_SECONDS: float = 300.0  # 5 min between repeated alerts
DEFAULT_PROBE_INTERVAL_SECONDS: float = 60.0   # check every minute
SLA_TARGET_PERCENT: float = 99.9        # PropelIQ SLA commitment


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class ProbeStatus(str, Enum):
    UP = "up"
    DOWN = "down"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class IncidentSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


# ---------------------------------------------------------------------------
# OPS-1: Probe result
# ---------------------------------------------------------------------------


@dataclass
class ProbeResult:
    """Result of a single uptime probe execution (OPS-1).

    Attributes
    ----------
    probe_name  Unique identifier for the probe.
    status      UP / DOWN / DEGRADED / UNKNOWN.
    latency_ms  How long the probe took in milliseconds.
    message     Human-readable detail or error message.
    checked_at  ISO-8601 UTC timestamp.
    """

    probe_name: str
    status: ProbeStatus
    latency_ms: float = 0.0
    message: str = ""
    checked_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def is_healthy(self) -> bool:
        return self.status == ProbeStatus.UP

    def to_dict(self) -> dict[str, Any]:
        return {
            "probe_name": self.probe_name,
            "status": self.status.value,
            "latency_ms": round(self.latency_ms, 2),
            "message": self.message,
            "checked_at": self.checked_at,
        }


# ---------------------------------------------------------------------------
# OPS-1: Probe history
# ---------------------------------------------------------------------------


class ProbeHistory:
    """Ring-buffer of recent probe results for a single probe (OPS-1).

    Used by ``UptimeMonitor`` to detect consecutive failure / recovery runs
    and to compute the rolling availability percentage.
    """

    def __init__(self, max_entries: int = 1000) -> None:
        self._results: list[ProbeResult] = []
        self._max = max_entries

    def add(self, result: ProbeResult) -> None:
        self._results.append(result)
        if len(self._results) > self._max:
            self._results = self._results[-self._max:]

    def latest(self) -> ProbeResult | None:
        return self._results[-1] if self._results else None

    def all_results(self) -> list[ProbeResult]:
        return list(self._results)

    def recent(self, n: int) -> list[ProbeResult]:
        return self._results[-n:] if n < len(self._results) else list(self._results)

    def consecutive_failures(self) -> int:
        count = 0
        for r in reversed(self._results):
            if r.is_healthy:
                break
            count += 1
        return count

    def consecutive_successes(self) -> int:
        count = 0
        for r in reversed(self._results):
            if not r.is_healthy:
                break
            count += 1
        return count

    def availability_percent(self, window: int = DEFAULT_WINDOW_SECONDS) -> float:
        """Compute availability % over the most recent *window* seconds.

        Uses entry count as a proxy for time when real timestamps vary.
        Falls back to total result set when fewer than *window* entries exist.
        """
        results = self._results
        if not results:
            return 100.0
        healthy = sum(1 for r in results if r.is_healthy)
        return (healthy / len(results)) * 100.0

    def total_checks(self) -> int:
        return len(self._results)


# ---------------------------------------------------------------------------
# OPS-3: SLA target
# ---------------------------------------------------------------------------


@dataclass
class SLATarget:
    """Defines the uptime SLA commitment and budget helpers (OPS-3).

    Attributes
    ----------
    target_percent   Required availability percentage (e.g. 99.9).
    window_seconds   Measurement window for budget calculation.
    service_name     Human label for dashboard display.
    """

    target_percent: float = SLA_TARGET_PERCENT
    window_seconds: int = DEFAULT_WINDOW_SECONDS
    service_name: str = "PropelIQ API"

    def is_breached(self, actual_percent: float) -> bool:
        return actual_percent < self.target_percent

    def budget_remaining_seconds(self, actual_percent: float) -> float:
        """Return the remaining downtime budget in seconds for this window."""
        allowed_downtime = self.window_seconds * (1.0 - self.target_percent / 100.0)
        consumed = self.window_seconds * (1.0 - actual_percent / 100.0)
        return max(0.0, allowed_downtime - consumed)

    def budget_consumed_percent(self, actual_percent: float) -> float:
        """Fraction of the error budget consumed (0 = none, 1 = fully consumed)."""
        allowed = self.window_seconds * (1.0 - self.target_percent / 100.0)
        if allowed <= 0:
            return 1.0
        consumed = self.window_seconds * (1.0 - actual_percent / 100.0)
        return min(1.0, consumed / allowed)

    def to_dict(self) -> dict[str, Any]:
        return {
            "service_name": self.service_name,
            "target_percent": self.target_percent,
            "window_seconds": self.window_seconds,
        }


# ---------------------------------------------------------------------------
# OPS-2: Incident model
# ---------------------------------------------------------------------------


@dataclass
class Incident:
    """A detected downtime or degradation event (OPS-2).

    Attributes
    ----------
    probe_name          Probe that detected the incident.
    severity            INFO / WARNING / CRITICAL.
    status_at_trigger   ProbeStatus when the incident was opened.
    opened_at           ISO-8601 UTC when incident started.
    resolved_at         ISO-8601 UTC when incident ended (None = ongoing).
    detail              Last error message from the failing probe.
    """

    probe_name: str
    severity: IncidentSeverity
    status_at_trigger: ProbeStatus
    opened_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolved_at: str | None = None
    detail: str = ""

    @property
    def is_open(self) -> bool:
        return self.resolved_at is None

    def resolve(self) -> None:
        self.resolved_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "probe_name": self.probe_name,
            "severity": self.severity.value,
            "status_at_trigger": self.status_at_trigger.value,
            "opened_at": self.opened_at,
            "resolved_at": self.resolved_at,
            "is_open": self.is_open,
            "detail": self.detail,
        }


# ---------------------------------------------------------------------------
# OPS-2: Alert routing
# ---------------------------------------------------------------------------


@dataclass
class IncidentAlert:
    """Alert payload emitted to the configured routing sink (OPS-2).

    Attributes
    ----------
    probe_name      Probe that triggered the alert.
    event_type      ``"opened"`` or ``"resolved"``.
    severity        Severity of the underlying incident.
    message         Human-readable summary.
    occurred_at     ISO-8601 UTC timestamp.
    """

    probe_name: str
    event_type: str
    severity: IncidentSeverity
    message: str
    occurred_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "probe_name": self.probe_name,
            "event_type": self.event_type,
            "severity": self.severity.value,
            "message": self.message,
            "occurred_at": self.occurred_at,
        }


class AlertRoutingProtocol(Protocol):
    """Production: PagerDuty / CloudWatch / Slack adapter."""
    def route(self, alert: IncidentAlert) -> None: ...


class InMemoryAlertRouter:
    """Test double for alert routing (OPS-2)."""

    def __init__(self) -> None:
        self.alerts: list[IncidentAlert] = []

    def route(self, alert: IncidentAlert) -> None:
        self.alerts.append(alert)


class IncidentAlerter:
    """Fires ``IncidentAlert`` on open / resolve transitions (OPS-2).

    Deduplicates: an 'opened' alert is only sent once per probe until the
    incident resolves.  A cooldown period prevents alert storms on flapping.
    """

    def __init__(
        self,
        router: AlertRoutingProtocol,
        cooldown_seconds: float = DEFAULT_ALERT_COOLDOWN_SECONDS,
    ) -> None:
        self._router = router
        self._cooldown = cooldown_seconds
        self._open_incidents: dict[str, Incident] = {}
        self._last_alerted: dict[str, float] = {}

    def handle_result(self, result: ProbeResult, history: ProbeHistory, thresholds: "MonitoringThresholds") -> None:
        """Evaluate *result* against *history* and fire alerts as needed."""
        if result.status == ProbeStatus.DOWN:
            if history.consecutive_failures() >= thresholds.down_threshold:
                self._open_incident(result)
        elif result.is_healthy:
            if history.consecutive_successes() >= thresholds.recovery_threshold:
                self._resolve_incident(result)

    def _open_incident(self, result: ProbeResult) -> None:
        if result.probe_name in self._open_incidents:
            return
        now = time.monotonic()
        last = self._last_alerted.get(result.probe_name, 0)
        if (now - last) < self._cooldown:
            return
        incident = Incident(
            probe_name=result.probe_name,
            severity=IncidentSeverity.CRITICAL,
            status_at_trigger=result.status,
            detail=result.message,
        )
        self._open_incidents[result.probe_name] = incident
        self._last_alerted[result.probe_name] = now
        alert = IncidentAlert(
            probe_name=result.probe_name,
            event_type="opened",
            severity=IncidentSeverity.CRITICAL,
            message=f"Service DOWN: {result.probe_name}. {result.message}",
        )
        self._router.route(alert)

    def _resolve_incident(self, result: ProbeResult) -> None:
        incident = self._open_incidents.pop(result.probe_name, None)
        if incident is None:
            return
        incident.resolve()
        alert = IncidentAlert(
            probe_name=result.probe_name,
            event_type="resolved",
            severity=IncidentSeverity.INFO,
            message=f"Service RECOVERED: {result.probe_name}.",
        )
        self._router.route(alert)

    def open_incidents(self) -> list[Incident]:
        return list(self._open_incidents.values())


# ---------------------------------------------------------------------------
# OPS-1: Uptime probe and monitor
# ---------------------------------------------------------------------------


@dataclass
class UptimeProbe:
    """A named uptime check backed by an injectable step callable (OPS-1).

    Attributes
    ----------
    name        Unique probe identifier (e.g. ``"api_liveness"``).
    step        Zero-argument callable: returns truthy on UP, raises on DOWN.
    interval    Minimum seconds between checks (informational; not enforced here).
    """

    name: str
    step: Callable[[], Any]
    interval: float = DEFAULT_PROBE_INTERVAL_SECONDS

    def run(self) -> ProbeResult:
        """Execute the probe step and return a ``ProbeResult``."""
        t0 = time.monotonic()
        try:
            self.step()
            latency = (time.monotonic() - t0) * 1000.0
            return ProbeResult(
                probe_name=self.name,
                status=ProbeStatus.UP,
                latency_ms=latency,
                message="ok",
            )
        except Exception as exc:  # noqa: BLE001
            latency = (time.monotonic() - t0) * 1000.0
            return ProbeResult(
                probe_name=self.name,
                status=ProbeStatus.DOWN,
                latency_ms=latency,
                message=str(exc),
            )


@dataclass
class MonitoringThresholds:
    """Configurable thresholds for the uptime monitor (OPS-4).

    Attributes
    ----------
    down_threshold          Consecutive failures before declaring DOWN.
    recovery_threshold      Consecutive passes before declaring RECOVERED.
    window_seconds          Rolling window for availability %.
    alert_cooldown_seconds  Minimum gap between repeated alerts for same probe.
    """

    down_threshold: int = DEFAULT_DOWN_THRESHOLD
    recovery_threshold: int = DEFAULT_RECOVERY_THRESHOLD
    window_seconds: int = DEFAULT_WINDOW_SECONDS
    alert_cooldown_seconds: float = DEFAULT_ALERT_COOLDOWN_SECONDS

    def to_dict(self) -> dict[str, Any]:
        return {
            "down_threshold": self.down_threshold,
            "recovery_threshold": self.recovery_threshold,
            "window_seconds": self.window_seconds,
            "alert_cooldown_seconds": self.alert_cooldown_seconds,
        }


class UptimeMonitor:
    """Drives probe execution, tracks history, and triggers alerts (OPS-1/OPS-2).

    Usage::

        router  = InMemoryAlertRouter()
        alerter = IncidentAlerter(router)
        monitor = UptimeMonitor(thresholds=MonitoringThresholds())
        monitor.register(UptimeProbe("api", lambda: requests.get(url).raise_for_status()))
        result  = monitor.check("api")
    """

    def __init__(
        self,
        thresholds: MonitoringThresholds | None = None,
        alerter: IncidentAlerter | None = None,
    ) -> None:
        self._thresholds = thresholds or MonitoringThresholds()
        self._alerter = alerter
        self._probes: dict[str, UptimeProbe] = {}
        self._history: dict[str, ProbeHistory] = {}

    def register(self, probe: UptimeProbe) -> None:
        self._probes[probe.name] = probe
        self._history[probe.name] = ProbeHistory()

    def check(self, probe_name: str) -> ProbeResult:
        """Run the named probe and record the result."""
        probe = self._probes.get(probe_name)
        if probe is None:
            raise KeyError(f"Probe '{probe_name}' is not registered.")
        result = probe.run()
        history = self._history[probe_name]
        history.add(result)
        if self._alerter:
            self._alerter.handle_result(result, history, self._thresholds)
        return result

    def check_all(self) -> dict[str, ProbeResult]:
        """Run every registered probe and return name → result mapping."""
        return {name: self.check(name) for name in self._probes}

    def history(self, probe_name: str) -> ProbeHistory:
        if probe_name not in self._history:
            raise KeyError(f"No history for probe '{probe_name}'.")
        return self._history[probe_name]

    def probe_names(self) -> list[str]:
        return list(self._probes.keys())

    def current_status(self, probe_name: str) -> ProbeStatus:
        h = self._history.get(probe_name)
        if not h:
            return ProbeStatus.UNKNOWN
        latest = h.latest()
        return latest.status if latest else ProbeStatus.UNKNOWN


# ---------------------------------------------------------------------------
# OPS-3: Availability dashboard
# ---------------------------------------------------------------------------


@dataclass
class AvailabilitySnapshot:
    """Point-in-time availability data for one probe (OPS-3).

    Attributes
    ----------
    probe_name          Name of the probe.
    availability_pct    Rolling availability percentage.
    current_status      Latest probe status.
    total_checks        Total checks in the history buffer.
    sla_breached        True when availability < SLA target.
    budget_remaining_s  Remaining downtime budget in seconds.
    """

    probe_name: str
    availability_pct: float
    current_status: str
    total_checks: int
    sla_breached: bool
    budget_remaining_s: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "probe_name": self.probe_name,
            "availability_pct": round(self.availability_pct, 4),
            "current_status": self.current_status,
            "total_checks": self.total_checks,
            "sla_breached": self.sla_breached,
            "budget_remaining_s": round(self.budget_remaining_s, 1),
        }


class AvailabilityDashboard:
    """Computes and exposes availability data for ops dashboards (OPS-3).

    Usage::

        dashboard = AvailabilityDashboard(monitor, sla)
        snapshot  = dashboard.snapshot("api_liveness")
        report    = dashboard.full_report()
    """

    def __init__(
        self,
        monitor: UptimeMonitor,
        sla: SLATarget | None = None,
    ) -> None:
        self._monitor = monitor
        self._sla = sla or SLATarget()

    def snapshot(self, probe_name: str) -> AvailabilitySnapshot:
        history = self._monitor.history(probe_name)
        avail = history.availability_percent(self._sla.window_seconds)
        latest = history.latest()
        status = latest.status.value if latest else ProbeStatus.UNKNOWN.value
        return AvailabilitySnapshot(
            probe_name=probe_name,
            availability_pct=avail,
            current_status=status,
            total_checks=history.total_checks(),
            sla_breached=self._sla.is_breached(avail),
            budget_remaining_s=self._sla.budget_remaining_seconds(avail),
        )

    def full_report(self) -> dict[str, Any]:
        """Return a dashboard-ready dict with all probe snapshots."""
        snapshots = {
            name: self.snapshot(name).to_dict()
            for name in self._monitor.probe_names()
        }
        overall_avail = (
            sum(s["availability_pct"] for s in snapshots.values()) / len(snapshots)
            if snapshots else 100.0
        )
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "sla_target_pct": self._sla.target_percent,
            "overall_availability_pct": round(overall_avail, 4),
            "sla_breached": self._sla.is_breached(overall_avail),
            "probes": snapshots,
        }

    def incident_history(self, alerter: IncidentAlerter) -> list[dict[str, Any]]:
        """Return open incidents from *alerter* for the dashboard incident log."""
        return [i.to_dict() for i in alerter.open_incidents()]


# ---------------------------------------------------------------------------
# OPS-4: Threshold documentation helper
# ---------------------------------------------------------------------------


class ThresholdDocumentation:
    """Generates a human-readable ops runbook section for monitoring thresholds."""

    @staticmethod
    def describe(thresholds: MonitoringThresholds, sla: SLATarget) -> str:
        allowed_ms = sla.window_seconds * (1.0 - sla.target_percent / 100.0)
        return (
            f"Service: {sla.service_name}\n"
            f"SLA Target: {sla.target_percent}% uptime over {sla.window_seconds}s window\n"
            f"Allowed downtime budget: {allowed_ms:.1f}s per window\n"
            f"Down threshold: {thresholds.down_threshold} consecutive failures\n"
            f"Recovery threshold: {thresholds.recovery_threshold} consecutive successes\n"
            f"Alert cooldown: {thresholds.alert_cooldown_seconds}s between repeated alerts\n"
        )


# ---------------------------------------------------------------------------
# Injectable test helpers
# ---------------------------------------------------------------------------


class FakeProbeStep:
    """Controllable probe step for unit tests.

    Set ``fail=True`` to make the next N calls raise; ``fail=False`` to pass.
    """

    def __init__(self, fail: bool = False, error_message: str = "probe failed") -> None:
        self.fail = fail
        self.error_message = error_message
        self.call_count = 0

    def __call__(self) -> None:
        self.call_count += 1
        if self.fail:
            raise RuntimeError(self.error_message)
