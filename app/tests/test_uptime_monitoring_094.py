"""
EP-008 US-094: Uptime Monitoring and Alerting — Test Suite

QA-1  Probe Tests      — uptime monitored continuously, results recorded
QA-2  Alert Tests      — outages generate alerts; recovery resolves them
QA-3  Dashboard Tests  — SLA % and incident history displayed correctly
QA-4  Threshold Tests  — threshold configuration controls alert and status behaviour
"""
from __future__ import annotations

import pytest

from src.uptime_monitoring import (
    DEFAULT_DOWN_THRESHOLD,
    DEFAULT_RECOVERY_THRESHOLD,
    SLA_TARGET_PERCENT,
    AvailabilityDashboard,
    AvailabilitySnapshot,
    FakeProbeStep,
    IncidentAlert,
    IncidentAlerter,
    IncidentSeverity,
    InMemoryAlertRouter,
    MonitoringThresholds,
    ProbeHistory,
    ProbeResult,
    ProbeStatus,
    SLATarget,
    ThresholdDocumentation,
    UptimeMonitor,
    UptimeProbe,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _monitor_with_alerter(
    down_threshold: int = 1,
    recovery_threshold: int = 1,
    cooldown: float = 0.0,
):
    router = InMemoryAlertRouter()
    thresholds = MonitoringThresholds(
        down_threshold=down_threshold,
        recovery_threshold=recovery_threshold,
        alert_cooldown_seconds=cooldown,
    )
    alerter = IncidentAlerter(router, cooldown_seconds=cooldown)
    monitor = UptimeMonitor(thresholds=thresholds, alerter=alerter)
    return monitor, alerter, router, thresholds


# ===========================================================================
# QA-1: Probe Tests (OPS-1)
# ===========================================================================


class TestProbeTests:
    """QA-1 — Uptime is monitored continuously and results are recorded."""

    def test_probe_records_up_on_success(self):
        step = FakeProbeStep(fail=False)
        probe = UptimeProbe("api", step)
        result = probe.run()
        assert result.status == ProbeStatus.UP

    def test_probe_records_down_on_failure(self):
        step = FakeProbeStep(fail=True)
        probe = UptimeProbe("api", step)
        result = probe.run()
        assert result.status == ProbeStatus.DOWN

    def test_probe_result_has_probe_name(self):
        result = UptimeProbe("my_probe", FakeProbeStep()).run()
        assert result.probe_name == "my_probe"

    def test_probe_result_has_latency(self):
        result = UptimeProbe("api", FakeProbeStep()).run()
        assert result.latency_ms >= 0

    def test_probe_result_down_contains_error_message(self):
        step = FakeProbeStep(fail=True, error_message="connection refused")
        result = UptimeProbe("api", step).run()
        assert "connection refused" in result.message

    def test_history_records_probe_result(self):
        monitor = UptimeMonitor()
        monitor.register(UptimeProbe("api", FakeProbeStep()))
        monitor.check("api")
        assert monitor.history("api").total_checks() == 1

    def test_check_all_runs_all_probes(self):
        monitor = UptimeMonitor()
        monitor.register(UptimeProbe("api", FakeProbeStep()))
        monitor.register(UptimeProbe("db", FakeProbeStep()))
        results = monitor.check_all()
        assert "api" in results
        assert "db" in results

    def test_consecutive_failures_counted(self):
        history = ProbeHistory()
        for _ in range(3):
            history.add(ProbeResult("probe", ProbeStatus.DOWN, message="err"))
        assert history.consecutive_failures() == 3

    def test_consecutive_successes_counted(self):
        history = ProbeHistory()
        history.add(ProbeResult("probe", ProbeStatus.DOWN, message="err"))
        for _ in range(2):
            history.add(ProbeResult("probe", ProbeStatus.UP, message="ok"))
        assert history.consecutive_successes() == 2
        assert history.consecutive_failures() == 0

    def test_unknown_probe_raises_key_error(self):
        monitor = UptimeMonitor()
        with pytest.raises(KeyError):
            monitor.check("nonexistent_probe")

    def test_current_status_unknown_before_any_check(self):
        monitor = UptimeMonitor()
        monitor.register(UptimeProbe("api", FakeProbeStep()))
        assert monitor.current_status("api") == ProbeStatus.UNKNOWN

    def test_current_status_up_after_success(self):
        monitor = UptimeMonitor()
        monitor.register(UptimeProbe("api", FakeProbeStep(fail=False)))
        monitor.check("api")
        assert monitor.current_status("api") == ProbeStatus.UP

    def test_probe_result_is_healthy(self):
        r = ProbeResult("x", ProbeStatus.UP)
        assert r.is_healthy
        r2 = ProbeResult("x", ProbeStatus.DOWN)
        assert not r2.is_healthy


# ===========================================================================
# QA-2: Alert Tests (OPS-2)
# ===========================================================================


class TestAlertTests:
    """QA-2 — Outages/degraded states generate alerts; recovery resolves them."""

    def test_alert_fired_after_down_threshold(self):
        monitor, alerter, router, _ = _monitor_with_alerter(down_threshold=2)
        step = FakeProbeStep(fail=True)
        monitor.register(UptimeProbe("api", step))
        monitor.check("api")   # fail 1
        monitor.check("api")   # fail 2 → alert
        opened = [a for a in router.alerts if a.event_type == "opened"]
        assert len(opened) == 1

    def test_no_alert_before_down_threshold(self):
        monitor, alerter, router, _ = _monitor_with_alerter(down_threshold=3)
        step = FakeProbeStep(fail=True)
        monitor.register(UptimeProbe("api", step))
        monitor.check("api")   # fail 1
        monitor.check("api")   # fail 2 — threshold not yet reached
        assert len(router.alerts) == 0

    def test_recovery_alert_fired_after_recovery_threshold(self):
        monitor, alerter, router, _ = _monitor_with_alerter(
            down_threshold=1, recovery_threshold=2
        )
        step = FakeProbeStep(fail=True)
        monitor.register(UptimeProbe("api", step))
        monitor.check("api")   # fail → open
        step.fail = False
        monitor.check("api")   # pass 1
        monitor.check("api")   # pass 2 → resolve
        resolved = [a for a in router.alerts if a.event_type == "resolved"]
        assert len(resolved) >= 1

    def test_alert_deduplication(self):
        monitor, alerter, router, _ = _monitor_with_alerter(down_threshold=1)
        step = FakeProbeStep(fail=True)
        monitor.register(UptimeProbe("api", step))
        for _ in range(5):
            monitor.check("api")
        opened = [a for a in router.alerts if a.event_type == "opened"]
        assert len(opened) == 1

    def test_alert_has_probe_name(self):
        monitor, alerter, router, _ = _monitor_with_alerter(down_threshold=1)
        monitor.register(UptimeProbe("db_check", FakeProbeStep(fail=True)))
        monitor.check("db_check")
        assert router.alerts[0].probe_name == "db_check"

    def test_alert_severity_is_critical_on_down(self):
        monitor, alerter, router, _ = _monitor_with_alerter(down_threshold=1)
        monitor.register(UptimeProbe("api", FakeProbeStep(fail=True)))
        monitor.check("api")
        assert router.alerts[0].severity == IncidentSeverity.CRITICAL

    def test_alert_to_dict_has_expected_keys(self):
        alert = IncidentAlert("api", "opened", IncidentSeverity.CRITICAL, "Service DOWN")
        d = alert.to_dict()
        assert all(k in d for k in ["probe_name", "event_type", "severity", "message", "occurred_at"])

    def test_open_incidents_tracked(self):
        monitor, alerter, router, _ = _monitor_with_alerter(down_threshold=1)
        monitor.register(UptimeProbe("api", FakeProbeStep(fail=True)))
        monitor.check("api")
        assert len(alerter.open_incidents()) == 1


# ===========================================================================
# QA-3: Dashboard Tests (OPS-3)
# ===========================================================================


class TestDashboardTests:
    """QA-3 — Dashboards display SLA % and incident history correctly."""

    def test_availability_100_on_all_passes(self):
        monitor = UptimeMonitor()
        monitor.register(UptimeProbe("api", FakeProbeStep(fail=False)))
        for _ in range(10):
            monitor.check("api")
        dashboard = AvailabilityDashboard(monitor)
        snap = dashboard.snapshot("api")
        assert snap.availability_pct == 100.0

    def test_availability_0_on_all_failures(self):
        monitor = UptimeMonitor()
        monitor.register(UptimeProbe("api", FakeProbeStep(fail=True)))
        for _ in range(5):
            monitor.check("api")
        dashboard = AvailabilityDashboard(monitor)
        snap = dashboard.snapshot("api")
        assert snap.availability_pct == 0.0

    def test_availability_50_on_half_failures(self):
        monitor = UptimeMonitor()
        step = FakeProbeStep(fail=False)
        monitor.register(UptimeProbe("api", step))
        for i in range(10):
            step.fail = (i % 2 == 0)
            monitor.check("api")
        dashboard = AvailabilityDashboard(monitor)
        snap = dashboard.snapshot("api")
        assert snap.availability_pct == pytest.approx(50.0, abs=5.0)

    def test_snapshot_has_expected_fields(self):
        monitor = UptimeMonitor()
        monitor.register(UptimeProbe("api", FakeProbeStep()))
        monitor.check("api")
        snap = AvailabilityDashboard(monitor).snapshot("api")
        assert hasattr(snap, "probe_name")
        assert hasattr(snap, "availability_pct")
        assert hasattr(snap, "sla_breached")
        assert hasattr(snap, "budget_remaining_s")

    def test_snapshot_to_dict_has_expected_keys(self):
        monitor = UptimeMonitor()
        monitor.register(UptimeProbe("api", FakeProbeStep()))
        monitor.check("api")
        d = AvailabilityDashboard(monitor).snapshot("api").to_dict()
        assert all(k in d for k in ["probe_name", "availability_pct", "current_status", "sla_breached"])

    def test_full_report_contains_all_probes(self):
        monitor = UptimeMonitor()
        monitor.register(UptimeProbe("api", FakeProbeStep()))
        monitor.register(UptimeProbe("db", FakeProbeStep()))
        monitor.check_all()
        report = AvailabilityDashboard(monitor).full_report()
        assert "api" in report["probes"]
        assert "db" in report["probes"]

    def test_full_report_has_sla_target(self):
        monitor = UptimeMonitor()
        monitor.register(UptimeProbe("api", FakeProbeStep()))
        monitor.check("api")
        report = AvailabilityDashboard(monitor).full_report()
        assert "sla_target_pct" in report

    def test_sla_not_breached_at_100_percent(self):
        sla = SLATarget(target_percent=99.9)
        assert not sla.is_breached(100.0)

    def test_sla_breached_below_target(self):
        sla = SLATarget(target_percent=99.9)
        assert sla.is_breached(99.0)

    def test_budget_remaining_positive_on_healthy(self):
        sla = SLATarget(target_percent=99.9, window_seconds=3600)
        remaining = sla.budget_remaining_seconds(100.0)
        assert remaining > 0

    def test_incident_history_from_alerter(self):
        monitor, alerter, router, _ = _monitor_with_alerter(down_threshold=1)
        monitor.register(UptimeProbe("api", FakeProbeStep(fail=True)))
        monitor.check("api")
        dashboard = AvailabilityDashboard(monitor)
        history = dashboard.incident_history(alerter)
        assert len(history) == 1

    def test_sla_target_constant(self):
        assert SLA_TARGET_PERCENT == 99.9


# ===========================================================================
# QA-4: Threshold Tests (OPS-4)
# ===========================================================================


class TestThresholdConfiguration:
    """QA-4 — Threshold configuration controls status and alert behaviour."""

    def test_default_down_threshold_constant(self):
        assert DEFAULT_DOWN_THRESHOLD == 3

    def test_default_recovery_threshold_constant(self):
        assert DEFAULT_RECOVERY_THRESHOLD == 2

    def test_custom_down_threshold_used(self):
        thresholds = MonitoringThresholds(down_threshold=5, recovery_threshold=1)
        assert thresholds.down_threshold == 5

    def test_thresholds_to_dict(self):
        t = MonitoringThresholds()
        d = t.to_dict()
        assert all(k in d for k in [
            "down_threshold", "recovery_threshold", "window_seconds", "alert_cooldown_seconds"
        ])

    def test_high_down_threshold_delays_alert(self):
        monitor, alerter, router, _ = _monitor_with_alerter(down_threshold=5)
        step = FakeProbeStep(fail=True)
        monitor.register(UptimeProbe("api", step))
        for _ in range(4):
            monitor.check("api")
        assert len(router.alerts) == 0

    def test_alert_fires_exactly_at_threshold(self):
        monitor, alerter, router, _ = _monitor_with_alerter(down_threshold=3)
        step = FakeProbeStep(fail=True)
        monitor.register(UptimeProbe("api", step))
        for _ in range(3):
            monitor.check("api")
        assert len([a for a in router.alerts if a.event_type == "opened"]) == 1

    def test_threshold_documentation_contains_sla(self):
        t = MonitoringThresholds()
        sla = SLATarget()
        doc = ThresholdDocumentation.describe(t, sla)
        assert "99.9" in doc

    def test_threshold_documentation_contains_down_threshold(self):
        t = MonitoringThresholds(down_threshold=4)
        doc = ThresholdDocumentation.describe(t, SLATarget())
        assert "4" in doc

    def test_probe_history_availability_full_history(self):
        h = ProbeHistory()
        for _ in range(9):
            h.add(ProbeResult("p", ProbeStatus.UP))
        h.add(ProbeResult("p", ProbeStatus.DOWN))
        avail = h.availability_percent()
        assert avail == pytest.approx(90.0)

    def test_probe_history_100_on_empty(self):
        assert ProbeHistory().availability_percent() == 100.0

    def test_sla_budget_consumed_increases_with_downtime(self):
        sla = SLATarget(target_percent=99.9, window_seconds=3600)
        consumed_at_100 = sla.budget_consumed_percent(100.0)
        consumed_at_99 = sla.budget_consumed_percent(99.0)
        assert consumed_at_99 > consumed_at_100
